"""
Motor TTS principal que usa providers intercambiables.
Ahora soporta múltiples engines (Edge, Google, etc.)
"""
import time
from typing import Optional
from .models import EdgeTTSConfig
from .tts import TTSProviderFactory


from core.provider_manager import ProviderManager

# Lock global para serializar la creación de providers TTS.
# gRPC (Google TTS) usa OpenSSL que NO es re-entrante si se inicializa
# desde múltiples threads al mismo tiempo en Windows → heap corruption.
#
# NOTA: el lock vive en core/tts_lock.py (módulo aparte, nunca recargado
# en caliente) para que su identidad sobreviva a
# importlib.reload(core.tts_engine) -- ver ese módulo para más detalle.
from .tts_lock import PROVIDER_CREATION_LOCK as _PROVIDER_CREATION_LOCK

# Reintentos ante fallos de red (DNS, gRPC UNAVAILABLE, etc.) antes de
# recurrir a Edge TTS como respaldo temporal para no perder el audio en vivo.
_MAX_SYNTH_RETRIES = 1
_RETRY_DELAY_SECONDS = 0.6

# Si el provider en la nube falla (tras refrescar conexión y reintentar) este
# número de mensajes SEGUIDOS, se degrada a Edge TTS de forma permanente en
# vez de seguir fallando en cada mensaje durante un corte prolongado.
_DEGRADE_AFTER_FAILURES = 3

class TTSEngine:
    def __init__(self, config: Optional[EdgeTTSConfig] = None, provider_name: str = None):
        """
        Args:
            config: Configuración del TTS
            provider_name: Nombre del proveedor (se sobrescribe si config tiene provider_name)
        """
        if config is None:
            config = EdgeTTSConfig()

        self.config = config

        # Usar provider_name del config si existe, sino usar parámetro
        self.provider_name = getattr(config, 'provider_name', provider_name or 'edge_tts')

        # Estado de resiliencia (ver _synthesize_with_resilience / update_config):
        # cuántos mensajes seguidos fallaron con el provider en la nube, y si
        # está actualmente degradado a Edge TTS tras fallos repetidos (guarda
        # el nombre del provider que falló, para saber cuál está bloqueado).
        self._consecutive_cloud_failures = 0
        self._degraded_from: Optional[str] = None

        # Obtener credenciales si es necesario
        self.provider_manager = ProviderManager()
        credentials_path = self.provider_manager.get_provider_credentials(self.provider_name)
        
        # Crear provider según tipo
        # NOTA: _PROVIDER_CREATION_LOCK evita inicializaciones concurrentes
        # de gRPC (Google TTS) que causan heap corruption en Windows.
        with _PROVIDER_CREATION_LOCK:
            if self.provider_name == "google_tts":
                from core.tts.google_provider import GoogleTTSConfig

                # Extraer language_code del voice_id
                voice_id = config.voice_id
                language_code = "-".join(voice_id.split("-")[:2]) if "-" in voice_id else "es-US"

                # Crear config de Google con credenciales
                google_config = GoogleTTSConfig(
                    voice_id=voice_id,
                    language_code=language_code,
                    rate=getattr(config, 'rate', '+0%'),
                    volume=getattr(config, 'volume_str', '+0%'),
                    pitch=getattr(config, 'pitch', 0),
                    credentials_path=credentials_path
                )
                self.provider = TTSProviderFactory.create("google_tts", google_config)
            elif self.provider_name == "azure_tts":
                from core.tts.azure_provider import AzureTTSConfig
                region = self.provider_manager.get_provider_region("azure_tts")
                azure_config = AzureTTSConfig(
                    voice_id=getattr(config, 'voice_id', 'es-MX-DaliaNeural'),
                    language_code=getattr(config, 'language_code', 'es-MX'),
                    speed=getattr(config, 'speed', 1.0),
                    pitch=getattr(config, 'pitch', 0),
                    volume=getattr(config, 'volume', 1.0),
                    subscription_key=getattr(config, 'subscription_key', None) or credentials_path or '',
                    region=getattr(config, 'region', None) or region,
                )
                self.provider = TTSProviderFactory.create("azure_tts", azure_config)
            else:
                # Edge TTS (default)
                self.provider = TTSProviderFactory.create("edge_tts", config)
    
    def update_config(self, config, user_initiated: bool = False):
        """
        Actualiza la configuración y cambia de provider si es necesario.

        Args:
            config: nueva configuración TTS
            user_initiated: True cuando el cambio viene de una acción explícita
                del usuario (seleccionar una voz en el desplegable, probar TTS
                en el diálogo de configuración, etc.), a diferencia de la
                reaplicación automática que hace la cola de audio antes de
                cada mensaje. Una acción manual siempre reintenta el provider
                pedido, incluso si estaba degradado a Edge TTS tras fallos
                repetidos (ver _synthesize_with_resilience); la reaplicación
                automática NO puede reactivar un provider degradado por sí
                sola, para no repetir el mismo error en cada mensaje durante
                un corte prolongado.
        """
        requested_provider_name = getattr(config, 'provider_name', 'edge_tts')

        if user_initiated:
            self._degraded_from = None
            self._consecutive_cloud_failures = 0
        elif self._degraded_from is not None and requested_provider_name == self._degraded_from:
            # Degradado tras fallos repetidos: ignorar la reaplicación
            # automática del provider que acaba de fallar. Se queda en
            # Edge TTS hasta reactivación manual.
            return

        self.config = config

        # Verificar qué provider necesitamos
        new_provider_name = requested_provider_name
        current_provider_name = self.provider.__class__.__name__.replace('TTSProvider', '').lower()
        
        # Mapeo de nombres de clase a nombres de provider
        provider_map = {
            'edge': 'edge_tts',
            'google': 'google_tts',
            'azure': 'azure_tts',
        }
        current_provider_name = provider_map.get(current_provider_name, current_provider_name)
        
        # Si es Google TTS, SIEMPRE crear GoogleTTSConfig
        if new_provider_name == "google_tts":
            from core.provider_manager import ProviderManager
            from core.tts.google_provider import GoogleTTSConfig
            
            pm = ProviderManager()
            credentials_path = pm.get_provider_credentials("google_tts")
            
            if not credentials_path:
                print("Google Cloud TTS no configurado, cambiando a Edge TTS")
                new_provider_name = "edge_tts"
                # Crear provider de Edge TTS (con lock para thread-safety)
                with _PROVIDER_CREATION_LOCK:
                    if new_provider_name != current_provider_name:
                        print(f"Cambiando provider: {current_provider_name} -> {new_provider_name}")
                        self.provider = TTSProviderFactory.create("edge_tts", config)
                    else:
                        self.provider.update_config(config)
                self.provider_name = new_provider_name
                return
            
            # Extraer language_code del voice_id
            voice_id = config.voice_id
            language_code = "-".join(voice_id.split("-")[:2]) if "-" in voice_id else "es-US"
            
            # Crear GoogleTTSConfig correcto
            google_config = GoogleTTSConfig(
                voice_id=voice_id,
                language_code=language_code,
                credentials_path=credentials_path,
                rate=getattr(config, 'rate', '+0%'),
                volume=getattr(config, 'volume_str', '+0%'),
                pitch=getattr(config, 'pitch', 0),
                sample_rate=getattr(config, 'sample_rate', 24000)
            )
            
            # Cambiar provider o actualizar config
            with _PROVIDER_CREATION_LOCK:
                if new_provider_name != current_provider_name:
                    print(f"Cambiando provider: {current_provider_name} -> {new_provider_name}")
                    self.provider = TTSProviderFactory.create("google_tts", google_config)
                else:
                    # Mismo provider, actualizar con GoogleTTSConfig (NO EdgeTTSConfig)
                    self.provider.update_config(google_config)

        elif new_provider_name == "azure_tts":
            from core.tts.azure_provider import AzureTTSConfig
            from core.provider_manager import ProviderManager

            pm = ProviderManager()
            credentials_path = pm.get_provider_credentials("azure_tts")

            azure_config = AzureTTSConfig(
                voice_id=getattr(config, 'voice_id', 'es-MX-DaliaNeural'),
                language_code=getattr(config, 'language_code', 'es-MX'),
                speed=getattr(config, 'speed', 1.0),
                pitch=getattr(config, 'pitch', 0),
                volume=getattr(config, 'volume', 1.0),
                subscription_key=getattr(config, 'subscription_key', None) or credentials_path or '',
                region=getattr(config, 'region', None) or pm.get_provider_region('azure_tts'),
            )

            with _PROVIDER_CREATION_LOCK:
                if new_provider_name != current_provider_name:
                    print(f"Cambiando provider: {current_provider_name} -> {new_provider_name}")
                    self.provider = TTSProviderFactory.create("azure_tts", azure_config)
                else:
                    self.provider.update_config(azure_config)

        else:
            # Edge TTS
            with _PROVIDER_CREATION_LOCK:
                if new_provider_name != current_provider_name:
                    print(f"Cambiando provider: {current_provider_name} -> {new_provider_name}")
                    self.provider = TTSProviderFactory.create("edge_tts", config)
                else:
                    # Mismo provider, actualizar config
                    self.provider.update_config(config)

        # IMPORTANTE: mantener self.provider_name sincronizado con el provider
        # real -- de lo contrario _synthesize_with_resilience() sigue leyendo
        # el provider con el que se construyó el engine la primera vez (p.ej.
        # "edge_tts") aunque self.provider ya se haya cambiado a otro (p.ej.
        # Google) por llamadas posteriores a update_config(), y el retry/
        # fallback/degradación de red quedaría deshabilitado en silencio.
        self.provider_name = new_provider_name

    def synthesize(self, text: str, config_override=None) -> str:
        """
        Sintetiza texto a audio.

        Args:
            text: Texto a convertir
            config_override: Configuración temporal para esta síntesis (opcional)

        Returns:
            Ruta al archivo WAV generado
        """
        if config_override:
            # Guardar config anterior
            original_config = self.provider.config
            self.provider.update_config(config_override)

            try:
                # Sintetizar (con reintento/fallback ante fallos de red)
                result = self._synthesize_with_resilience(text)
            finally:
                # Restaurar config
                self.provider.update_config(original_config)
            return result
        else:
            return self._synthesize_with_resilience(text)

    def _synthesize_with_resilience(self, text: str) -> str:
        """
        Sintetiza con el provider actual. Si falla (típicamente errores de
        red/DNS con providers en la nube como Google o Azure):

          1. Refresca el provider -- lo reconstruye desde cero, con un
             cliente/canal gRPC nuevo, por si la conexión anterior quedó en
             mal estado -- y reintenta una vez.
          2. Si ese reintento también falla, cuenta como un mensaje fallido
             seguido. Al llegar a _DEGRADE_AFTER_FAILURES mensajes seguidos,
             degrada esta voz a Edge TTS de forma PERMANENTE (no solo para
             este mensaje) para no repetir el mismo error en cada mensaje
             durante un corte prolongado -- se queda así hasta que el
             usuario reactive el provider manualmente (ver update_config).
          3. Si aún no se llegó a ese umbral, usa Edge TTS solo para ESTE
             mensaje y vuelve a intentar el provider configurado en el
             próximo.
        """
        if self.provider_name == 'edge_tts':
            return self.provider.synthesize(text)

        try:
            result = self.provider.synthesize(text)
            self._consecutive_cloud_failures = 0
            return result
        except Exception as e:
            self._consecutive_cloud_failures += 1
            print(f"[TTSEngine] Fallo en {self.provider_name} ({e}), refrescando conexión y reintentando...")

            try:
                with _PROVIDER_CREATION_LOCK:
                    self.provider = TTSProviderFactory.create(self.provider_name, self.provider.config)
            except Exception as refresh_err:
                print(f"[TTSEngine] No se pudo refrescar {self.provider_name}: {refresh_err}")

            time.sleep(_RETRY_DELAY_SECONDS)
            try:
                result = self.provider.synthesize(text)
                self._consecutive_cloud_failures = 0
                return result
            except Exception as e2:
                failing_provider = self.provider_name

                if self._consecutive_cloud_failures >= _DEGRADE_AFTER_FAILURES:
                    print(
                        f"[TTSEngine] {failing_provider} falló {self._consecutive_cloud_failures} "
                        "mensajes seguidos -- degradando a Edge TTS de forma permanente hasta "
                        "reactivarlo manualmente (p.ej. re-seleccionando la voz)."
                    )
                    self._degraded_from = failing_provider
                    self.provider_name = 'edge_tts'
                    self.provider = self._get_fallback_provider()
                    self._consecutive_cloud_failures = 0
                    return self.provider.synthesize(text)

                print(
                    f"[TTSEngine] {failing_provider} sigue sin responder ({e2}), "
                    "usando Edge TTS como respaldo temporal para este mensaje"
                )
                return self._get_fallback_provider().synthesize(text)

    def _get_fallback_provider(self):
        """Provider de Edge TTS reutilizable para respaldo ante fallos de red."""
        if not hasattr(self, '_fallback_edge_provider'):
            with _PROVIDER_CREATION_LOCK:
                self._fallback_edge_provider = TTSProviderFactory.create('edge_tts', EdgeTTSConfig())
        return self._fallback_edge_provider
    
    def get_available_voices(self) -> list[dict]:
        """Obtiene voces disponibles del provider actual"""
        return self.provider.get_available_voices()
    
    @staticmethod
    def get_available_providers() -> list[str]:
        """Obtiene lista de providers TTS disponibles"""
        return TTSProviderFactory.get_available_providers()
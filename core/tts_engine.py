"""
Motor TTS principal que usa providers intercambiables.
Ahora soporta múltiples engines (Edge, Google, etc.)
"""
import threading
from typing import Optional
from .models import EdgeTTSConfig
from .tts import TTSProviderFactory


from core.provider_manager import ProviderManager

# Lock global para serializar la creación de providers TTS.
# gRPC (Google TTS) usa OpenSSL que NO es re-entrante si se inicializa
# desde múltiples threads al mismo tiempo en Windows → heap corruption.
_PROVIDER_CREATION_LOCK = threading.Lock()

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
    
    def update_config(self, config):
        """Actualiza la configuración y cambia de provider si es necesario"""
        self.config = config
        
        # Verificar qué provider necesitamos
        new_provider_name = getattr(config, 'provider_name', 'edge_tts')
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
            
            # Sintetizar
            result = self.provider.synthesize(text)
            
            # Restaurar config
            self.provider.update_config(original_config)
            return result
        else:
            return self.provider.synthesize(text)
    
    def get_available_voices(self) -> list[dict]:
        """Obtiene voces disponibles del provider actual"""
        return self.provider.get_available_voices()
    
    @staticmethod
    def get_available_providers() -> list[str]:
        """Obtiene lista de providers TTS disponibles"""
        return TTSProviderFactory.get_available_providers()
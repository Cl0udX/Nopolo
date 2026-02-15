"""
Proveedor de Google Cloud Text-to-Speech API.
Requiere credenciales de Google Cloud.
"""
import os
import tempfile
from typing import Optional

from .base_provider import BaseTTSProvider

# Importación condicional (solo si está instalado)
try:
    from google.cloud import texttospeech
    GOOGLE_TTS_AVAILABLE = True
except ImportError:
    GOOGLE_TTS_AVAILABLE = False


class GoogleTTSConfig:
    """Configuración para Google Cloud TTS"""
    def __init__(
        self,
        voice_id: str = "es-US-Neural2-A",
        language_code: str = "es-US",
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: int = 0,
        sample_rate: int = 24000,
        credentials_path: Optional[str] = None
    ):
        self.provider_name = "google_tts" 
        self.voice_id = voice_id
        self.language_code = language_code
        self.rate = rate
        self.volume = volume
        self.pitch = pitch
        self.sample_rate = sample_rate
        self.credentials_path = credentials_path
    
    def to_dict(self):
        """Convierte a diccionario para serialización JSON"""
        return {
            'provider_name': self.provider_name,
            'voice_id': self.voice_id,
            'language_code': self.language_code,
            'rate': self.rate,
            'volume': self.volume,
            'pitch': self.pitch,
            'sample_rate': self.sample_rate,
            'credentials_path': self.credentials_path
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Crea instancia desde diccionario"""
        return cls(
            voice_id=data.get('voice_id', 'es-US-Neural2-A'),
            language_code=data.get('language_code', 'es-US'),
            rate=data.get('rate', '+0%'),
            volume=data.get('volume', '+0%'),
            pitch=data.get('pitch', 0),
            sample_rate=data.get('sample_rate', 24000),
            credentials_path=data.get('credentials_path')
        )


class GoogleTTSProvider(BaseTTSProvider):
    """Proveedor de Google Cloud Text-to-Speech"""
    
    def __init__(self, config: Optional[GoogleTTSConfig] = None):
        if not GOOGLE_TTS_AVAILABLE:
            raise ImportError(
                "Google Cloud TTS no está instalado. "
                "Instala con: pip install google-cloud-texttospeech"
            )
        
        if config is None:
            config = GoogleTTSConfig()
        
        super().__init__(config)
        
        # Configurar credenciales
        if config.credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = config.credentials_path
        
        # Crear cliente
        try:
            self.client = texttospeech.TextToSpeechClient()
            print("Google Cloud TTS inicializado")
        except Exception as e:
            raise RuntimeError(
                f"Error inicializando Google TTS: {e}\n"
                "Verifica tus credenciales de Google Cloud."
            )
    
    async def synthesize_async(self, text: str) -> str:
        """Sintetiza usando Google Cloud TTS"""
        
        # Configurar input
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Configurar voz (sin especificar género - deja que Google use el género natural de la voz)
        voice = texttospeech.VoiceSelectionParams(
            language_code=self.config.language_code,
            name=self.config.voice_id
        )
        
        # Intentar primero con pitch
        try:
            # Configurar audio con pitch
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.config.sample_rate,
                speaking_rate=self._parse_rate(self.config.rate),
                pitch=self.config.pitch / 10.0,  # Google usa rango -20.0 a 20.0
                volume_gain_db=self._parse_volume(self.config.volume)
            )
            
            # Sintetizar
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
        except Exception as e:
            # Si el error es que la voz no soporta pitch, reintentar sin pitch
            if "does not support pitch parameters" in str(e):
                print(f"Voz {self.config.voice_id} no soporta modificación de pitch, usando valor por defecto")
                
                # Configurar audio SIN pitch
                audio_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                    sample_rate_hertz=self.config.sample_rate,
                    speaking_rate=self._parse_rate(self.config.rate),
                    volume_gain_db=self._parse_volume(self.config.volume)
                )
                
                # Reintentar sin pitch
                response = self.client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice,
                    audio_config=audio_config
                )
            else:
                # Si es otro error, propagarlo
                raise
        
        # Guardar a archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(response.audio_content)
            return f.name
    
    def get_available_voices(self) -> list[dict]:
        """Obtiene voces disponibles de Google Cloud"""
        try:
            voices = self.client.list_voices()
            return [
                {
                    "id": voice.name,
                    "name": voice.name,
                    "language": voice.language_codes[0],
                    "gender": voice.ssml_gender.name
                }
                for voice in voices.voices
            ]
        except Exception as e:
            print(f"Error obteniendo voces de Google: {e}")
            return []
    
    def validate_config(self) -> bool:
        """Valida credenciales de Google Cloud"""
        try:
            self.client.list_voices()
            return True
        except Exception:
            return False
    
    def _parse_rate(self, rate_str: str) -> float:
        """Convierte '+50%' a 1.5"""
        rate = int(rate_str.replace('%', '').replace('+', ''))
        return 1.0 + (rate / 100.0)
    
    def _parse_volume(self, volume_str: str) -> float:
        """Convierte '+50%' a ganancia en dB"""
        volume = int(volume_str.replace('%', '').replace('+', ''))
        return volume / 10.0  # Aproximación simple
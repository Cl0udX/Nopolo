"""
Configuraciones base para Text-to-Speech engines.
Cada engine (EdgeTTS, Coqui, etc.) hereda de BaseTTSConfig.
"""
from dataclasses import dataclass, asdict
from typing import Optional
import json


@dataclass
class BaseTTSConfig:
    """Configuración base para cualquier TTS engine"""
    voice_id: str = "default"     # ID de la voz (ej: "es-MX-JorgeNeural")
    speed: float = 1.0            # Velocidad (0.5-2.0)
    pitch: int = 0                # Pitch en semitonos (-12 a +12)
    volume: float = 1.0           # Volumen (0.0-1.0)
    sample_rate: int = 44100      # Sample rate del audio
    
    def to_dict(self):
        """Convierte a diccionario"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        """Crea desde diccionario"""
        return cls(**data)
    
    def save(self, path: str):
        """Guarda configuración a JSON"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: str):
        """Carga configuración desde JSON"""
        with open(path, 'r', encoding='utf-8') as f:
            return cls.from_dict(json.load(f))


@dataclass
class EdgeTTSConfig(BaseTTSConfig):
    """Configuración específica para Edge TTS (Microsoft Azure)"""
    provider_name: str = "edge_tts"  # ← Solo provider_name, sin engine_type
    voice_id: str = "es-MX-JorgeNeural"
    
    # Parámetros específicos de Edge TTS
    rate: str = "+0%"      # Velocidad como string ("+0%", "+50%", "-20%")
    volume_str: str = "+0%"  # Volumen como string
    
    def __post_init__(self):
        """Convierte speed/volume a formato Edge TTS"""
        # Convertir speed (0.5-2.0) a rate string
        speed_percent = int((self.speed - 1.0) * 100)
        self.rate = f"{speed_percent:+d}%"
        
        # Convertir volume (0.0-1.0) a volume string
        volume_percent = int((self.volume - 1.0) * 100)
        self.volume_str = f"{volume_percent:+d}%"


@dataclass  
class CoquiTTSConfig(BaseTTSConfig):
    """Configuración para Coqui TTS (para futuro)"""
    engine_type: str = "coqui_tts"
    voice_id: str = "tts_models/es/css10/vits"
    model_name: str = "tts_models/es/css10/vits"
    use_cuda: bool = True
    
    # Parámetros específicos de Coqui
    emotion: Optional[str] = None
    speaker_idx: Optional[int] = None
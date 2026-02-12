"""
Modelos de configuración para el sistema de voces.
"""
from .base_tts_config import BaseTTSConfig, EdgeTTSConfig, CoquiTTSConfig
from .rvc_config import RVCConfig
from .voice_profile import VoiceProfile

__all__ = [
    'BaseTTSConfig',
    'EdgeTTSConfig', 
    'CoquiTTSConfig',
    'RVCConfig',
    'VoiceProfile'
]
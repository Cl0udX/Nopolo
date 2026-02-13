"""
Sistema de proveedores TTS multi-engine.
Soporta Edge TTS, Google Cloud TTS, y es extensible.
"""
from .base_provider import BaseTTSProvider
from .edge_provider import EdgeTTSProvider
from .provider_factory import TTSProviderFactory

__all__ = [
    'BaseTTSProvider',
    'EdgeTTSProvider',
    'TTSProviderFactory',
]
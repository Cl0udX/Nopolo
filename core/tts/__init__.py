"""
Sistema de proveedores TTS multi-engine.
Soporta Edge TTS, Google Cloud TTS, Azure Cognitive Services TTS, y es extensible.
"""
from .base_provider import BaseTTSProvider
from .edge_provider import EdgeTTSProvider
from .provider_factory import TTSProviderFactory

# Importaciones condicionales
try:
    from .google_provider import GoogleTTSProvider, GoogleTTSConfig
except ImportError:
    pass

try:
    from .azure_provider import AzureTTSProvider, AzureTTSConfig
except ImportError:
    pass

__all__ = [
    'BaseTTSProvider',
    'EdgeTTSProvider',
    'TTSProviderFactory',
    'AzureTTSProvider',
    'AzureTTSConfig',
]
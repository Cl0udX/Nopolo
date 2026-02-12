
"""
API REST para integración con Streamer.bot y otras aplicaciones externas.
"""
from .rest_server import TTSAPIServer, TTSRequest, TTSResponse

__all__ = ['TTSAPIServer', 'TTSRequest', 'TTSResponse']
"""
Factory para crear proveedores TTS dinámicamente.
Para agregar un nuevo TTS, solo registra su clase aquí.
"""
from typing import Dict, Type
from .base_provider import BaseTTSProvider
from .edge_provider import EdgeTTSProvider, EdgeTTSConfig

# Importación condicional de Google TTS
try:
    from .google_provider import GoogleTTSProvider, GoogleTTSConfig
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


class TTSProviderFactory:
    """Factory para crear proveedores TTS"""
    
    # Registro de providers disponibles
    _providers: Dict[str, Type[BaseTTSProvider]] = {
        'edge_tts': EdgeTTSProvider,
    }
    
    # Agregar Google si está disponible
    if GOOGLE_AVAILABLE:
        _providers['google_tts'] = GoogleTTSProvider
    
    @classmethod
    def create(cls, provider_name: str, config=None) -> BaseTTSProvider:
        """
        Crea un proveedor TTS.
        
        Args:
            provider_name: 'edge_tts', 'google_tts', etc.
            config: Configuración del proveedor (EdgeTTSConfig, GoogleTTSConfig, etc.)
            
        Returns:
            Instancia del proveedor TTS
            
        Raises:
            ValueError: Si el proveedor no existe
        """
        if provider_name not in cls._providers:
            available = ', '.join(cls._providers.keys())
            raise ValueError(
                f"Proveedor TTS '{provider_name}' no existe. "
                f"Disponibles: {available}"
            )
        
        provider_class = cls._providers[provider_name]
        return provider_class(config)
    
    @classmethod
    def get_available_providers(cls) -> list[str]:
        """
        Retorna lista de proveedores disponibles.
        
        Returns:
            Lista de nombres: ['edge_tts', 'google_tts', ...]
        """
        return list(cls._providers.keys())
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseTTSProvider]):
        """
        Registra un nuevo proveedor TTS (para extensiones futuras).
        
        Args:
            name: Identificador del proveedor (ej: 'elevenlabs')
            provider_class: Clase del proveedor (debe heredar de BaseTTSProvider)
        """
        if not issubclass(provider_class, BaseTTSProvider):
            raise TypeError(f"{provider_class} debe heredar de BaseTTSProvider")
        
        cls._providers[name] = provider_class
        print(f"Proveedor TTS '{name}' registrado")
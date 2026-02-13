"""
Interfaz base para proveedores de Text-to-Speech.
Todos los TTS (Edge, Google, Coqui, etc.) heredan de aquí.
"""
from abc import ABC, abstractmethod
from typing import Optional


class BaseTTSProvider(ABC):
    """
    Proveedor TTS abstracto.
    Todos los engines TTS deben implementar estos métodos.
    """
    
    def __init__(self, config):
        """
        Args:
            config: EdgeTTSConfig, GoogleTTSConfig, etc.
        """
        self.config = config
    
    @abstractmethod
    async def synthesize_async(self, text: str) -> str:
        """
        Sintetiza texto a audio (método asíncrono).
        
        Args:
            text: Texto a convertir
            
        Returns:
            Ruta al archivo WAV generado
        """
        pass
    
    def synthesize(self, text: str) -> str:
        """
        Sintetiza texto a audio (método síncrono).
        Por defecto llama a synthesize_async().
        
        Args:
            text: Texto a convertir
            
        Returns:
            Ruta al archivo WAV generado
        """
        import asyncio
        return asyncio.run(self.synthesize_async(text))
    
    @abstractmethod
    def get_available_voices(self) -> list[dict]:
        """
        Retorna lista de voces disponibles.
        
        Returns:
            Lista de diccionarios con info de voces:
            [
                {"id": "es-MX-DaliaNeural", "name": "Dalia", "language": "es-MX"},
                ...
            ]
        """
        pass
    
    def validate_config(self) -> bool:
        """
        Valida que la configuración sea correcta.
        
        Returns:
            True si es válida, False si no
        """
        return True  # Por defecto asume que es válida
    
    def update_config(self, config):
        """Actualiza la configuración del provider"""
        self.config = config
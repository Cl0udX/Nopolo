"""
VoiceProfile: Representa una voz completa (TTS base + RVC transformer).
Esta es la clase principal que combina ambos.
"""
from dataclasses import dataclass, asdict
from typing import Optional
import json
from .base_tts_config import BaseTTSConfig, EdgeTTSConfig
from .rvc_config import RVCConfig


@dataclass
class VoiceProfile:
    """
    Perfil completo de una voz.
    Combina:
    - TTS Config: Voz base neutral (Edge TTS, Coqui, etc.)
    - RVC Config: Transformación a personaje/carácter
    """
    
    # Identificación
    profile_id: str                  # ID único (ej: "homero_simpson")
    display_name: str                # Nombre para mostrar
    
    # Configuraciones
    tts_config: BaseTTSConfig        # Configuración del TTS base
    rvc_config: Optional[RVCConfig] = None  # Configuración RVC (None = sin transformar)
    
    # Metadatos
    enabled: bool = True             # Si está activo para uso
    tags: list[str] = None           # Tags para categorización
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def to_dict(self):
        """Serializa a diccionario"""
        data = {
            'profile_id': self.profile_id,
            'display_name': self.display_name,
            'enabled': self.enabled,
            'tags': self.tags,
            'tts_config': self.tts_config.to_dict(),
        }
        
        if self.rvc_config:
            data['rvc_config'] = self.rvc_config.to_dict()
        
        return data
    
    @classmethod
    def from_dict(cls, data: dict):
        """Deserializa desde diccionario"""
        # Reconstruir TTS config
        tts_data = data['tts_config']
        
        # Detectar el tipo de engine desde provider_name o engine_type
        provider_name = tts_data.get('provider_name', tts_data.get('engine_type', 'edge_tts'))
        
        if provider_name == 'edge_tts':
            tts_config = EdgeTTSConfig.from_dict(tts_data)
        elif provider_name == 'google_tts':
            # Para Google TTS, crear una instancia básica con los campos necesarios
            # GoogleTTSConfig no hereda de BaseTTSConfig, usa su propio constructor
            from core.tts.google_provider import GoogleTTSConfig
            tts_config = GoogleTTSConfig(
                voice_id=tts_data.get('voice_id', 'es-US-Standard-C'),
                language_code=tts_data.get('language_code', 'es-US'),
                rate=tts_data.get('rate', '+0%'),
                volume=tts_data.get('volume_str', '+0%'),
                pitch=tts_data.get('pitch', 0),
                sample_rate=tts_data.get('sample_rate', 24000),
                credentials_path=tts_data.get('credentials_path', None)
            )
        elif provider_name == 'azure_tts':
            from core.tts.azure_provider import AzureTTSConfig
            tts_config = AzureTTSConfig(
                voice_id=tts_data.get('voice_id', 'es-MX-DaliaNeural'),
                language_code=tts_data.get('language_code', 'es-MX'),
                speed=tts_data.get('speed', 1.0),
                pitch=tts_data.get('pitch', 0),
                volume=tts_data.get('volume', 1.0),
                subscription_key=tts_data.get('subscription_key', ''),
                region=tts_data.get('region', 'eastus'),
            )
        else:
            # Para otros engines, usar BaseTTSConfig con solo campos básicos
            tts_config = BaseTTSConfig(
                voice_id=tts_data.get('voice_id', 'default'),
                speed=tts_data.get('speed', 1.0),
                pitch=tts_data.get('pitch', 0),
                volume=tts_data.get('volume', 1.0),
                sample_rate=tts_data.get('sample_rate', 44100)
            )
        
        # Reconstruir RVC config
        rvc_config = None
        if 'rvc_config' in data and data['rvc_config']:
            rvc_config = RVCConfig.from_dict(data['rvc_config'])
        
        return cls(
            profile_id=data['profile_id'],
            display_name=data['display_name'],
            tts_config=tts_config,
            rvc_config=rvc_config,
            enabled=data.get('enabled', True),
            tags=data.get('tags', [])
        )
    
    def save(self, path: str):
        """Guarda profile a JSON"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, path: str):
        """Carga profile desde JSON"""
        with open(path, 'r', encoding='utf-8') as f:
            return cls.from_dict(json.load(f))
    
    def validate(self) -> bool:
        """Valida que todos los componentes estén correctos"""
        # Validar que profile_id y display_name no tengan espacios
        if ' ' in self.profile_id:
            raise ValueError(f"profile_id no puede contener espacios: '{self.profile_id}'")
        if ' ' in self.display_name:
            raise ValueError(f"display_name no puede contener espacios: '{self.display_name}'")
        
        # Validar RVC si existe
        if self.rvc_config:
            return self.rvc_config.validate()
        return True
    
    def is_transformer_voice(self) -> bool:
        """Retorna True si usa RVC transformer"""
        return self.rvc_config is not None
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
        engine_type = tts_data.get('engine_type', 'edge_tts')
        
        if engine_type == 'edge_tts':
            tts_config = EdgeTTSConfig.from_dict(tts_data)
        else:
            tts_config = BaseTTSConfig.from_dict(tts_data)
        
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
        if self.rvc_config:
            return self.rvc_config.validate()
        return True
    
    def is_transformer_voice(self) -> bool:
        """Retorna True si usa RVC transformer"""
        return self.rvc_config is not None
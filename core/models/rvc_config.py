"""
Configuración para modelos RVC (Retrieval-based Voice Conversion).
Define parámetros de transformación de voz.
"""
from dataclasses import dataclass, asdict
from typing import Optional
import json
import os


@dataclass
class RVCConfig:
    """Configuración de un modelo RVC transformer"""
    
    # Identificación
    model_id: str                    # ID único (ej: "homero", "marge")
    name: str                        # Nombre amigable
    model_path: str                  # Ruta al archivo .pth
    index_path: Optional[str] = None # Ruta al archivo .index (opcional)
    
    # Estado
    enabled: bool = True             # Si está habilitado para usar
    
    # Parámetros de conversión
    pitch_shift: int = 0             # Cambio de tono (-12 a +12 semitonos)
    index_rate: float = 0.75         # Influencia del índice (0.0-1.0)
    filter_radius: int = 3           # Radio del filtro mediano para harvest
    rms_mix_rate: float = 0.25       # Mix de RMS entre entrada y salida (0.0-1.0)
    protect: float = 0.33            # Protección de consonantes sin voz (0.0-0.5)
    
    # Parámetros avanzados
    f0_method: str = "rmvpe"         # Método de extracción F0: "pm", "harvest", "crepe", "rmvpe"
    resample_sr: int = 0             # Sample rate de salida (0 = usar original)
    
    # Metadatos
    gender: str = "male"             # "male", "female", "neutral"
    description: str = ""            # Descripción de la voz
    
    def __post_init__(self):
        """Validación y auto-detección de index"""
        # Auto-detectar index si no se especificó
        if self.index_path is None and self.model_path:
            model_dir = os.path.dirname(self.model_path)
            model_name = os.path.splitext(os.path.basename(self.model_path))[0]
            
            # Buscar archivo .index en el mismo directorio
            for file in os.listdir(model_dir) if os.path.exists(model_dir) else []:
                if file.endswith('.index') and model_name in file:
                    self.index_path = os.path.join(model_dir, file)
                    break
    
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
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, path: str):
        """Carga configuración desde JSON"""
        with open(path, 'r', encoding='utf-8') as f:
            return cls.from_dict(json.load(f))
    
    def validate(self) -> bool:
        """Valida que el modelo existe"""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Modelo RVC no encontrado: {self.model_path}")
        
        if self.index_path and not os.path.exists(self.index_path):
            print(f"Advertencia: Index no encontrado: {self.index_path}")
        
        return True
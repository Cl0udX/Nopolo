"""
Parser de mensajes con formato Mopolo.

Soporta:
- Voces: nombre: o id:
- Sonidos: (nombre_sonido) o (id)
- Filtros: nombre.filtro: o id.filtro:

Ejemplos:
  "dross: hola amigos (disparo) homero: doh!"
  "2: hola 5.r: con eco (45) enrique.p: llamada"
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class SegmentType(Enum):
    """Tipo de segmento en el mensaje"""
    VOICE = "voice"      # Texto con voz
    SOUND = "sound"      # Efecto de sonido
    PAUSE = "pause"      # Pausa (opcional)


class AudioFilter(Enum):
    """Filtros de audio disponibles"""
    REVERB = "r"         # Eco/reverberación
    PHONE = "p"          # Llamada telefónica
    PITCH_UP = "pu"      # Voz aguda
    PITCH_DOWN = "pd"    # Voz grave
    MUFFLED = "m"        # Voz apagada/afuera
    ROBOT = "a"          # Android/robot
    DISTORTION = "l"     # Saturada/distorsión
    BACKGROUND_A = "fa"  # Fondo A (ej: calle, tráfico)
    BACKGROUND_B = "fb"  # Fondo B (ej: lluvia, naturaleza)
    BACKGROUND_C = "fc"  # Fondo C (ej: multitud, restaurante)
    BACKGROUND_D = "fd"  # Fondo D (ej: viento, playa)
    BACKGROUND_E = "fe"  # Fondo E (personalizable)


@dataclass
class MessageSegment:
    """
    Representa un segmento del mensaje (voz o sonido).
    """
    type: SegmentType
    content: str                          # Texto a sintetizar o nombre de sonido
    voice: Optional[str] = None           # Nombre o ID de voz
    filters: List[AudioFilter] = None     # Filtros a aplicar
    
    def __post_init__(self):
        if self.filters is None:
            self.filters = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para JSON"""
        return {
            "type": self.type.value,
            "content": self.content,
            "voice": self.voice,
            "filters": [f.value for f in self.filters]
        }


class MessageParser:
    """
    Parser para mensajes con formato Mopolo.
    
    Formato:
    - Voces: "nombre:" o "id:" (sin espacios)
    - Sonidos: "(nombre)" o "(id)"
    - Filtros: "nombre.filtro:" o "id.filtro:"
    
    Ejemplos:
        "dross: hola amigos"
        "2: hola (disparo) 5: adios"
        "enrique.r: con eco (45) homero.p: llamada"
    """
    
    # Patrón para detectar voces con filtros: "nombre.filtro:" o "id.filtro:"
    # Soporta múltiples filtros: "nombre.filtro1.filtro2:"
    VOICE_PATTERN = re.compile(r'([\w.]+):\s*')
    
    # Patrón para detectar sonidos: "(nombre)" o "(id)"
    SOUND_PATTERN = re.compile(r'\(([^)]+)\)')
    
    def __init__(self, default_voice: str = "base_male"):
        """
        Inicializa el parser.
        
        Args:
            default_voice: Voz por defecto si no se especifica
        """
        self.default_voice = default_voice
    
    def parse(self, message: str) -> List[MessageSegment]:
        """
        Parsea un mensaje y retorna lista de segmentos.
        
        Args:
            message: Mensaje con formato Mopolo
            
        Returns:
            Lista de MessageSegment
            
        Ejemplo:
            >>> parser = MessageParser()
            >>> segments = parser.parse("dross: hola (disparo) homero: doh!")
            >>> len(segments)
            3
            >>> segments[0].type
            SegmentType.VOICE
            >>> segments[0].voice
            'dross'
            >>> segments[1].type
            SegmentType.SOUND
        """
        segments = []
        current_voice = self.default_voice
        current_filters = []
        
        # Posición actual en el string
        pos = 0
        
        while pos < len(message):
            # Buscar próxima voz o sonido
            voice_match = self.VOICE_PATTERN.search(message, pos)
            sound_match = self.SOUND_PATTERN.search(message, pos)
            
            # Determinar cuál viene primero
            next_match = None
            next_type = None
            
            if voice_match and sound_match:
                if voice_match.start() < sound_match.start():
                    next_match = voice_match
                    next_type = "voice"
                else:
                    next_match = sound_match
                    next_type = "sound"
            elif voice_match:
                next_match = voice_match
                next_type = "voice"
            elif sound_match:
                next_match = sound_match
                next_type = "sound"
            
            if not next_match:
                # No hay más matches, procesar resto como texto con voz actual
                remaining_text = message[pos:].strip()
                if remaining_text:
                    segments.append(MessageSegment(
                        type=SegmentType.VOICE,
                        content=remaining_text,
                        voice=current_voice,
                        filters=current_filters.copy()
                    ))
                break
            
            # Procesar texto antes del próximo match
            if next_match.start() > pos:
                text_before = message[pos:next_match.start()].strip()
                if text_before:
                    segments.append(MessageSegment(
                        type=SegmentType.VOICE,
                        content=text_before,
                        voice=current_voice,
                        filters=current_filters.copy()
                    ))
            
            # Procesar el match
            if next_type == "voice":
                # Cambiar voz actual y extraer múltiples filtros
                voice_full = voice_match.group(1)  # Ej: "homero.p.fc"
                parts = voice_full.split('.')       # ["homero", "p", "fc"]
                
                current_voice = parts[0]  # Primer elemento es la voz
                current_filters = []
                
                # Extraer todos los filtros (resto de elementos)
                for filter_id in parts[1:]:
                    try:
                        current_filters.append(AudioFilter(filter_id))
                    except ValueError:
                        print(f"Filtro desconocido: {filter_id}")
                
                pos = next_match.end()
                
            elif next_type == "sound":
                # Agregar sonido con múltiples filtros
                sound_full = sound_match.group(1)  # Ej: "330.fc.p"
                parts = sound_full.split('.')       # ["330", "fc", "p"]
                
                sound_id = parts[0]  # Primer elemento es el ID del sonido
                sound_filters = []
                
                # Extraer todos los filtros (resto de elementos)
                for filter_id in parts[1:]:
                    try:
                        sound_filters.append(AudioFilter(filter_id))
                    except ValueError:
                        print(f"Filtro desconocido en sonido: {filter_id}")
                
                segments.append(MessageSegment(
                    type=SegmentType.SOUND,
                    content=sound_id,
                    voice=None,
                    filters=sound_filters
                ))
                pos = next_match.end()
        
        return segments
    
    def validate_voice_name(self, name: str) -> bool:
        """
        Valida que un nombre de voz no tenga espacios ni caracteres inválidos.
        
        Args:
            name: Nombre de voz a validar
            
        Returns:
            True si es válido, False si no
        """
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', name))
    
    def parse_to_dict(self, message: str) -> Dict[str, Any]:
        """
        Parsea mensaje y retorna diccionario JSON-friendly.
        
        Args:
            message: Mensaje con formato Mopolo
            
        Returns:
            Diccionario con estructura:
            {
                "segments": [
                    {"type": "voice", "content": "texto", "voice": "nombre", "filters": []},
                    {"type": "sound", "content": "sonido_id", "voice": null, "filters": []},
                    ...
                ],
                "total_segments": 3,
                "voices_used": ["dross", "homero"],
                "sounds_used": ["disparo"]
            }
        """
        segments = self.parse(message)
        
        # Extraer estadísticas
        voices_used = list(set(
            s.voice for s in segments 
            if s.type == SegmentType.VOICE and s.voice
        ))
        sounds_used = list(set(
            s.content for s in segments 
            if s.type == SegmentType.SOUND
        ))
        
        return {
            "segments": [s.to_dict() for s in segments],
            "total_segments": len(segments),
            "voices_used": voices_used,
            "sounds_used": sounds_used
        }


# Ejemplo de uso
if __name__ == "__main__":
    parser = MessageParser()
    
    # Ejemplo 1: Básico
    msg1 = "enrique: hola, cómo estás? mia: te voy a disparar enrique (disparo2) enrique: ouch eso me dolió"
    result1 = parser.parse(msg1)
    print("Ejemplo 1:")
    for i, seg in enumerate(result1):
        print(f"  {i+1}. {seg.type.value}: '{seg.content}' (voz: {seg.voice})")
    
    # Ejemplo 2: Con filtros
    msg2 = "2.r: eco 2.p: llamada (explosion) 5: normal"
    result2 = parser.parse(msg2)
    print("\nEjemplo 2:")
    for i, seg in enumerate(result2):
        filters_str = f", filtros: {[f.value for f in seg.filters]}" if seg.filters else ""
        print(f"  {i+1}. {seg.type.value}: '{seg.content}' (voz: {seg.voice}{filters_str})")
    
    # Ejemplo 3: JSON
    msg3 = "dross: hola amigos (disparo) homero: doh!"
    result3 = parser.parse_to_dict(msg3)
    print("\nEjemplo 3 (JSON):")
    import json
    print(json.dumps(result3, indent=2, ensure_ascii=False))

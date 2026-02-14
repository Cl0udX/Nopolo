"""
Gestor de efectos de sonido.

Mapea IDs y nombres de sonidos a archivos de audio,
y proporciona funciones para reproducirlos.
"""

import os
import json
from typing import Dict, Optional, List
from pathlib import Path
import soundfile as sf
import numpy as np


class SoundManager:
    """
    Administra efectos de sonido para la aplicación.
    
    Estructura de sounds.json:
    {
        "sounds": [
            {
                "id": "1",
                "name": "disparo",
                "filename": "disparo.wav",
                "category": "weapons",
                "duration_ms": 500
            },
            ...
        ]
    }
    """
    
    def __init__(self, sounds_dir: str = "sounds", config_file: str = "config/sounds.json"):
        """
        Inicializa el gestor de sonidos.
        
        Args:
            sounds_dir: Directorio donde están los archivos de sonido
            config_file: Archivo JSON con la configuración de sonidos
        """
        self.sounds_dir = Path(sounds_dir)
        self.config_file = Path(config_file)
        
        # Mapas de ID -> info y nombre -> info
        self.sounds_by_id: Dict[str, Dict] = {}
        self.sounds_by_name: Dict[str, Dict] = {}
        
        # Crear directorio si no existe
        self.sounds_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar configuración
        self._load_config()
    
    def _load_config(self):
        """Carga la configuración de sonidos desde JSON"""
        if not self.config_file.exists():
            print(f"⚠️ Archivo de sonidos no encontrado: {self.config_file}")
            print("   Creando configuración vacía...")
            self._create_default_config()
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            sounds = data.get("sounds", [])
            
            for sound in sounds:
                sound_id = str(sound.get("id"))
                sound_name = sound.get("name")
                
                # Mapear por ID
                self.sounds_by_id[sound_id] = sound
                
                # Mapear por nombre
                if sound_name:
                    self.sounds_by_name[sound_name.lower()] = sound
            
            if sounds:
                print(f"✅ Cargados {len(sounds)} sonidos desde {self.config_file}")
            else:
                print(f"📝 Configuración de sonidos cargada (vacía) - usa 'Importar Sonidos' para agregar")
            
        except Exception as e:
            print(f"❌ Error cargando configuración de sonidos: {e}")
            self._create_default_config()
    
    def _create_default_config(self):
        """Crea una configuración vacía (sin sonidos de ejemplo)"""
        default_config = {
            "sounds": [],
            "info": {
                "description": "Configuración de efectos de sonido",
                "usage": "Usa el botón 'Importar Sonidos' para agregar archivos MP3/WAV automáticamente"
            }
        }
        
        # Crear directorio de config si no existe
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Guardar
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Configuración de sonidos creada: {self.config_file}")
        print(f"   � Archivo vacío - usa 'Importar Sonidos' para agregar archivos")
        
        # Limpiar índices (archivo vacío)
        self.sounds_by_id = {}
        self.sounds_by_name = {}        # Recargar
        self._load_config()
    
    def get_sound(self, identifier: str) -> Optional[Dict]:
        """
        Obtiene información de un sonido por ID o nombre.
        
        Args:
            identifier: ID o nombre del sonido
            
        Returns:
            Diccionario con info del sonido o None si no existe
        """
        # Buscar por ID primero
        if identifier in self.sounds_by_id:
            return self.sounds_by_id[identifier]
        
        # Buscar por nombre (case-insensitive)
        if identifier.lower() in self.sounds_by_name:
            return self.sounds_by_name[identifier.lower()]
        
        return None
    
    def get_sound_path(self, identifier: str) -> Optional[Path]:
        """
        Obtiene la ruta completa del archivo de sonido.
        
        Args:
            identifier: ID o nombre del sonido
            
        Returns:
            Path al archivo o None si no existe
        """
        sound_info = self.get_sound(identifier)
        if not sound_info:
            return None
        
        # Usar 'path' si existe (archivos importados), sino usar sounds_dir/filename
        if "path" in sound_info and sound_info["path"]:
            sound_path = Path(sound_info["path"])
        else:
            filename = sound_info.get("filename")
            if not filename:
                return None
            sound_path = self.sounds_dir / filename
        
        if not sound_path.exists():
            print(f"⚠️ Archivo de sonido no encontrado: {sound_path}")
            return None
        
        return sound_path
    
    def load_sound_audio(self, identifier: str) -> Optional[tuple]:
        """
        Carga el audio de un sonido.
        
        Args:
            identifier: ID o nombre del sonido
            
        Returns:
            Tupla (audio_data, sample_rate) o None si no existe
        """
        sound_path = self.get_sound_path(identifier)
        if not sound_path:
            return None
        
        try:
            audio_data, sample_rate = sf.read(str(sound_path), dtype='float32')
            return (audio_data, sample_rate)
        except Exception as e:
            print(f"❌ Error cargando sonido {identifier}: {e}")
            return None
    
    def list_sounds(self, category: Optional[str] = None) -> List[Dict]:
        """
        Lista todos los sonidos disponibles.
        
        Args:
            category: Filtrar por categoría (opcional)
            
        Returns:
            Lista de diccionarios con info de sonidos
        """
        sounds = list(self.sounds_by_id.values())
        
        if category:
            sounds = [s for s in sounds if s.get("category") == category]
        
        return sounds
    
    def add_sound(self, sound_id: str, name: str, filename: str, 
                  category: str = "other", duration_ms: int = 1000) -> bool:
        """
        Agrega un nuevo sonido a la configuración.
        
        Args:
            sound_id: ID único del sonido
            name: Nombre del sonido (sin espacios)
            filename: Nombre del archivo en sounds/
            category: Categoría del sonido
            duration_ms: Duración aproximada en milisegundos
            
        Returns:
            True si se agregó correctamente, False si ya existe
        """
        # Validar que el ID no exista
        if sound_id in self.sounds_by_id:
            print(f"❌ Ya existe un sonido con ID {sound_id}")
            return False
        
        # Validar que el nombre no tenga espacios
        if ' ' in name:
            print(f"❌ El nombre no puede tener espacios: {name}")
            return False
        
        # Cargar config actual
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Agregar nuevo sonido
        new_sound = {
            "id": sound_id,
            "name": name,
            "filename": filename,
            "category": category,
            "duration_ms": duration_ms
        }
        
        config["sounds"].append(new_sound)
        
        # Guardar
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # Recargar
        self._load_config()
        
        print(f"✅ Sonido agregado: {name} (ID: {sound_id})")
        return True
    
    def sound_exists(self, identifier: str) -> bool:
        """
        Verifica si un sonido existe.
        
        Args:
            identifier: ID o nombre del sonido
            
        Returns:
            True si existe, False si no
        """
        return self.get_sound(identifier) is not None
    
    def remove_sound(self, sound_id: str) -> bool:
        """
        Elimina un sonido de la configuración.
        
        Args:
            sound_id: ID del sonido a eliminar
            
        Returns:
            True si se eliminó correctamente, False si no
        """
        try:
            # Leer configuración actual
            if not self.config_file.exists():
                print(f"❌ No existe archivo de configuración: {self.config_file}")
                return False
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            sounds = config.get("sounds", [])
            original_len = len(sounds)
            
            # Filtrar el sonido a eliminar
            sounds = [s for s in sounds if str(s.get("id")) != str(sound_id)]
            
            if len(sounds) == original_len:
                print(f"⚠️ Sonido con ID '{sound_id}' no encontrado")
                return False
            
            # Guardar configuración actualizada
            config["sounds"] = sounds
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # Recargar configuración
            self._load_config()
            
            print(f"✅ Sonido '{sound_id}' eliminado correctamente")
            return True
            
        except Exception as e:
            print(f"❌ Error eliminando sonido: {e}")
            return False


# Ejemplo de uso
if __name__ == "__main__":
    manager = SoundManager()
    
    print("\n📢 Sonidos disponibles:")
    for sound in manager.list_sounds():
        print(f"  [{sound['id']}] {sound['name']} - {sound['filename']}")
    
    print("\n🔍 Buscar sonido 'disparo':")
    info = manager.get_sound("disparo")
    if info:
        print(f"  Encontrado: {info}")
    
    print("\n🔍 Buscar sonido por ID '2':")
    info = manager.get_sound("2")
    if info:
        print(f"  Encontrado: {info}")

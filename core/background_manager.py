"""
Gestor de fondos de audio.

Permite cargar y gestionar archivos de audio que se usan como fondos
para mezclarse con las voces. Similar a los efectos de sonido pero
se mezclan continuamente durante toda la frase.

Ejemplos de fondos:
- fa: calle con tráfico
- fb: lluvia
- fc: multitud en restaurante
- fd: viento, playa
- fe: personalizado
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
import numpy as np
from pydub import AudioSegment


class BackgroundManager:
    """Gestor de fondos de audio para mezclar con voces."""
    
    def __init__(self, config_path: str = "config/backgrounds.json"):
        """
        Inicializa el gestor de fondos.
        
        Args:
            config_path: Ruta al archivo de configuración de fondos
        """
        self.config_path = config_path
        self.backgrounds: Dict[str, Dict] = {}
        self.backgrounds_by_id: Dict[str, Dict] = {}
        self.backgrounds_by_name: Dict[str, Dict] = {}
        
        self._load_config()
    
    def _load_config(self):
        """Carga la configuración de fondos desde el archivo JSON."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.backgrounds = config.get('backgrounds', {})
                    
                    # Crear índices por ID y nombre
                    for bg_id, bg_data in self.backgrounds.items():
                        self.backgrounds_by_id[bg_id] = bg_data
                        name = bg_data.get('name', '').lower()
                        if name:
                            self.backgrounds_by_name[name] = bg_data
                    
                    if self.backgrounds:
                        print(f"Cargados {len(self.backgrounds)} fondos desde {self.config_path}")
                    else:
                        print(f"Configuración de fondos cargada (vacía) - usa 'Importar Fondos' para agregar")
            else:
                # Crear configuración por defecto
                print(f"Archivo de fondos no encontrado: {self.config_path}")
                print("   Creando configuración por defecto...")
                self._create_default_config()
        except Exception as e:
            print(f"Error cargando configuración de fondos: {e}")
            self._create_default_config()
    
    def _create_default_config(self):
        """Crea una configuración vacía (sin fondos de ejemplo)"""
        default_config = {
            "backgrounds": {},
            "info": {
                "description": "Configuración de fondos de audio",
                "volume_range": "0.0 - 1.0 (recomendado: 0.2 - 0.4)",
                "usage": "Usa el botón 'Importar Fondos' para agregar archivos MP3/WAV automáticamente"
            }
        }
        
        self.backgrounds = {}
        self.backgrounds_by_id = {}
        self.backgrounds_by_name = {}
        
        # Crear directorio de config si no existe
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # Guardar configuración vacía
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        print(f"Configuración de fondos creada: {self.config_path}")
        print(f"Archivo vacío - usa 'Importar Fondos' para agregar archivos")
    
    def _save_config(self):
        """Guarda la configuración actual en el archivo JSON."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            config = {
                "backgrounds": self.backgrounds,
                "info": {
                    "description": "Configuración de fondos de audio",
                    "volume_range": "0.0 - 1.0 (recomendado: 0.2 - 0.4)"
                }
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error guardando configuración de fondos: {e}")
    
    def get_background(self, identifier: str) -> Optional[Dict]:
        """
        Obtiene un fondo por ID o nombre.
        
        Args:
            identifier: ID (fa, fb, fc) o nombre (calle, lluvia)
            
        Returns:
            Diccionario con datos del fondo o None si no existe
        """
        # Buscar por ID
        if identifier in self.backgrounds_by_id:
            return self.backgrounds_by_id[identifier]
        
        # Buscar por nombre (case-insensitive)
        identifier_lower = identifier.lower()
        if identifier_lower in self.backgrounds_by_name:
            return self.backgrounds_by_name[identifier_lower]
        
        return None
    
    def get_background_path(self, identifier: str) -> Optional[str]:
        """
        Obtiene la ruta del archivo de un fondo.
        
        Args:
            identifier: ID o nombre del fondo
            
        Returns:
            Ruta al archivo o None si no existe
        """
        bg = self.get_background(identifier)
        if bg:
            return bg.get('path')
        return None
    
    def load_background_audio(self, identifier: str) -> Optional[Tuple[np.ndarray, int, float]]:
        """
        Carga el audio de un fondo.
        
        Args:
            identifier: ID o nombre del fondo
            
        Returns:
            Tupla (audio_data, sample_rate, volume) o None si no existe
        """
        bg = self.get_background(identifier)
        if not bg:
            print(f"Fondo '{identifier}' no encontrado")
            return None
        
        path = bg.get('path')
        volume = bg.get('volume', 0.3)
        
        if not path or not os.path.exists(path):
            print(f"Archivo de fondo no encontrado: {path}")
            return None
        
        try:
            # Usar pydub para soportar MP3, WAV, etc.
            audio = AudioSegment.from_file(path)
            
            # Convertir a mono si es estéreo
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Convertir a numpy array
            audio_data = np.array(audio.get_array_of_samples(), dtype=np.float32)
            
            # Normalizar de int16 a float32 (-1.0 a 1.0)
            audio_data = audio_data / 32768.0
            
            sample_rate = audio.frame_rate
            
            return audio_data, sample_rate, volume
            
        except Exception as e:
            print(f"Error cargando audio de fondo '{identifier}': {e}")
            return None
    
    def add_background(self, bg_id: str, name: str, path: str, 
                      description: str = "", volume: float = 0.3):
        """
        Agrega un nuevo fondo a la configuración.
        
        Args:
            bg_id: ID del fondo (ej: fa, fb)
            name: Nombre descriptivo
            path: Ruta al archivo de audio
            description: Descripción del fondo
            volume: Volumen por defecto (0.0 - 1.0)
        """
        background = {
            "id": bg_id,
            "name": name,
            "description": description,
            "path": path,
            "volume": max(0.0, min(1.0, volume))  # Clamp entre 0 y 1
        }
        
        self.backgrounds[bg_id] = background
        self.backgrounds_by_id[bg_id] = background
        self.backgrounds_by_name[name.lower()] = background
        
        self._save_config()
    
    def update_background_volume(self, identifier: str, volume: float):
        """
        Actualiza el volumen de un fondo.
        
        Args:
            identifier: ID o nombre del fondo
            volume: Nuevo volumen (0.0 - 1.0)
        """
        bg = self.get_background(identifier)
        if bg:
            bg_id = bg['id']
            self.backgrounds[bg_id]['volume'] = max(0.0, min(1.0, volume))
            self._save_config()
    
    def update_background(self, bg_id: str, name: str = None, path: str = None,
                         description: str = None, volume: float = None):
        """
        Actualiza un fondo existente.
        
        Args:
            bg_id: ID del fondo a actualizar
            name: Nuevo nombre (opcional)
            path: Nueva ruta (opcional)
            description: Nueva descripción (opcional)
            volume: Nuevo volumen (opcional)
        """
        if bg_id not in self.backgrounds:
            raise ValueError(f"Fondo '{bg_id}' no encontrado")
        
        bg = self.backgrounds[bg_id]
        
        # Actualizar campos proporcionados
        if name is not None:
            # Remover del índice por nombre anterior
            old_name = bg['name'].lower()
            if old_name in self.backgrounds_by_name:
                del self.backgrounds_by_name[old_name]
            # Actualizar nombre
            bg['name'] = name
            self.backgrounds_by_name[name.lower()] = bg
        
        if path is not None:
            bg['path'] = path
        
        if description is not None:
            bg['description'] = description
        
        if volume is not None:
            bg['volume'] = max(0.0, min(1.0, volume))
        
        # Guardar configuración
        self._save_config()
    
    def list_backgrounds(self) -> Dict[str, Dict]:
        """
        Lista todos los fondos disponibles.
        
        Returns:
            Diccionario con todos los fondos
        """
        return self.backgrounds.copy()
    
    def remove_background(self, bg_id: str) -> bool:
        """
        Elimina un fondo de la configuración.
        
        Args:
            bg_id: ID del fondo a eliminar
            
        Returns:
            True si se eliminó correctamente, False si no
        """
        try:
            if bg_id not in self.backgrounds:
                print(f"Fondo con ID '{bg_id}' no encontrado")
                return False
            
            # Obtener datos antes de eliminar
            bg_data = self.backgrounds[bg_id]
            name = bg_data.get('name', '').lower()
            
            # Eliminar de todos los índices
            del self.backgrounds[bg_id]
            
            if bg_id in self.backgrounds_by_id:
                del self.backgrounds_by_id[bg_id]
            
            if name and name in self.backgrounds_by_name:
                del self.backgrounds_by_name[name]
            
            # Guardar configuración
            self._save_config()
            
            print(f"Fondo '{bg_id}' eliminado correctamente")
            return True
            
        except Exception as e:
            print(f"Error eliminando fondo: {e}")
            return False


# Ejemplo de uso
if __name__ == "__main__":
    manager = BackgroundManager()
    
    print("Fondos disponibles:")
    for bg_id, bg_data in manager.list_backgrounds().items():
        print(f"  {bg_id}: {bg_data['name']} - {bg_data['description']}")
        print(f"      Archivo: {bg_data['path']}")
        print(f"      Volumen: {bg_data['volume']}")
    
    # Probar carga
    print("\nProbando carga de fondo 'calle':")
    result = manager.load_background_audio("calle")
    if result:
        audio, sr, vol = result
        print(f"  ✓ Audio cargado: {len(audio)} samples @ {sr}Hz, volumen {vol}")
    else:
        print("  ✗ Archivo no encontrado (esperado en fase de desarrollo)")

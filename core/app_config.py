"""
Gestor de configuración de la aplicación.
Guarda preferencias como dispositivo de audio, última voz usada, etc.
"""

import json
import os
from typing import Optional
from core.paths import get_app_settings_config


class AppConfig:
    """Gestor de configuración de la aplicación"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = str(get_app_settings_config())
        self.config_path = config_path
        self.settings = {}
        self._load()
    
    def _load(self):
        """Carga la configuración desde el archivo"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            except Exception as e:
                print(f"Error cargando configuración: {e}")
                self.settings = {}
        else:
            self.settings = {}
            self._save()
    
    def _save(self):
        """Guarda la configuración al archivo"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando configuración: {e}")
    
    def get(self, key: str, default=None):
        """Obtiene un valor de configuración"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value):
        """Establece un valor de configuración"""
        self.settings[key] = value
        self._save()
    
    def get_audio_device(self) -> Optional[int]:
        """Obtiene el ID del dispositivo de audio configurado"""
        device = self.settings.get('audio_output_device')
        # None significa usar el predeterminado del sistema
        return device
    
    def set_audio_device(self, device_id: Optional[int]):
        """Establece el dispositivo de audio"""
        self.settings['audio_output_device'] = device_id
        self._save()


# Instancia global
_app_config = None


def get_app_config() -> AppConfig:
    """Obtiene la instancia global de configuración"""
    global _app_config
    if _app_config is None:
        _app_config = AppConfig()
    return _app_config

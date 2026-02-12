"""
VoiceManager: Gestiona todas las voces disponibles del sistema.
Carga, guarda, y proporciona acceso a los perfiles de voz.
"""
import json
import os
from typing import Dict, List, Optional
from pathlib import Path
from .models import VoiceProfile, EdgeTTSConfig, RVCConfig


class VoiceManager:
    """Administrador central de voces"""
    
    def __init__(self, config_path: str = "config/voices.json"):
        self.config_path = config_path
        self.profiles: Dict[str, VoiceProfile] = {}
        self.default_voice_id: Optional[str] = None
        
        # Crear directorio de config si no existe
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Cargar configuración existente o crear default
        if os.path.exists(config_path):
            self.load_from_file()
        else:
            self._create_default_config()
            self.save_to_file()
    
    def _create_default_config(self):
        """Crea configuración por defecto con la voz Homero"""
        # Voz base masculina sin transformer
        base_male = VoiceProfile(
            profile_id="base_male",
            display_name="Voz Base Masculina",
            tts_config=EdgeTTSConfig(
                engine_type="edge_tts",
                voice_id="es-MX-JorgeNeural",
                speed=1.0,
                pitch=0
            ),
            rvc_config=None,
            tags=["base", "male"]
        )
        
        # Voz base femenina sin transformer
        base_female = VoiceProfile(
            profile_id="base_female",
            display_name="Voz Base Femenina",
            tts_config=EdgeTTSConfig(
                engine_type="edge_tts",
                voice_id="es-MX-DaliaNeural",
                speed=1.0,
                pitch=0
            ),
            rvc_config=None,
            tags=["base", "female"]
        )
        
        self.profiles = {
            "base_male": base_male,
            "base_female": base_female,
        }
        self.default_voice_id = "base_male"  # Cambiar de "homero" a "base_male"
    
    def add_profile(self, profile: VoiceProfile) -> bool:
        """Agrega un nuevo perfil de voz"""
        try:
            profile.validate()
            self.profiles[profile.profile_id] = profile
            self.save_to_file()
            return True
        except Exception as e:
            print(f"Error agregando perfil {profile.profile_id}: {e}")
            return False
    
    def remove_profile(self, profile_id: str) -> bool:
        """Elimina un perfil de voz"""
        if profile_id in self.profiles:
            del self.profiles[profile_id]
            if self.default_voice_id == profile_id:
                self.default_voice_id = next(iter(self.profiles.keys()), None)
            self.save_to_file()
            return True
        return False
    
    def get_profile(self, profile_id: str) -> Optional[VoiceProfile]:
        """Obtiene un perfil por ID"""
        return self.profiles.get(profile_id)
    
    def get_default_profile(self) -> Optional[VoiceProfile]:
        """Obtiene el perfil por defecto"""
        if self.default_voice_id:
            return self.profiles.get(self.default_voice_id)
        return next(iter(self.profiles.values()), None) if self.profiles else None
    
    def set_default(self, profile_id: str) -> bool:
        """Establece la voz por defecto"""
        if profile_id in self.profiles:
            self.default_voice_id = profile_id
            self.save_to_file()
            return True
        return False
    
    def list_profiles(self, enabled_only: bool = True) -> List[VoiceProfile]:
        """Lista todos los perfiles"""
        profiles = self.profiles.values()
        if enabled_only:
            profiles = [p for p in profiles if p.enabled]
        return list(profiles)
    
    def list_profile_ids(self, enabled_only: bool = True) -> List[str]:
        """Lista IDs de perfiles"""
        return [p.profile_id for p in self.list_profiles(enabled_only)]
    
    def get_profiles_by_tag(self, tag: str) -> List[VoiceProfile]:
        """Obtiene perfiles por tag"""
        return [p for p in self.profiles.values() if tag in p.tags]
    
    def save_to_file(self):
        """Guarda todas las voces a JSON"""
        data = {
            "default_voice": self.default_voice_id,
            "profiles": {
                pid: profile.to_dict() 
                for pid, profile in self.profiles.items()
            }
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Configuración guardada en {self.config_path}")
    
    def load_from_file(self):
        """Carga voces desde JSON"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.default_voice_id = data.get("default_voice")
            
            # Cargar perfiles
            self.profiles = {}
            for pid, profile_data in data.get("profiles", {}).items():
                try:
                    profile = VoiceProfile.from_dict(profile_data)
                    self.profiles[pid] = profile
                except Exception as e:
                    print(f"Error cargando perfil {pid}: {e}")
            
            print(f"{len(self.profiles)} voces cargadas desde {self.config_path}")
            
        except Exception as e:
            print(f"Error cargando configuración: {e}")
            self._create_default_config()
    
    def scan_rvc_models(self, voices_dir: str = "voices") -> List[str]:
        """
        Escanea el directorio voices/ en busca de nuevos modelos .pth
        que no estén registrados.
        """
        new_models = []
        
        if not os.path.exists(voices_dir):
            return new_models
        
        for root, dirs, files in os.walk(voices_dir):
            for file in files:
                if file.endswith('.pth'):
                    model_path = os.path.join(root, file)
                    model_name = os.path.splitext(file)[0]
                    
                    # Verificar si ya existe un perfil con este modelo
                    exists = any(
                        p.rvc_config and p.rvc_config.model_path == model_path
                        for p in self.profiles.values()
                    )
                    
                    if not exists:
                        new_models.append(model_path)
        
        return new_models
    
    def auto_add_rvc_model(self, model_path: str, gender: str = "male") -> Optional[str]:
        """
        Agrega automáticamente un modelo RVC encontrado.
        Retorna el profile_id creado o None si falla.
        """
        model_name = os.path.splitext(os.path.basename(model_path))[0]
        profile_id = model_name.lower().replace(" ", "_")
        
        # Determinar voz base según género
        base_voice = "es-MX-JorgeNeural" if gender == "male" else "es-MX-DaliaNeural"
        
        profile = VoiceProfile(
            profile_id=profile_id,
            display_name=model_name.title(),
            tts_config=EdgeTTSConfig(
                engine_type="edge_tts",
                voice_id=base_voice,
                speed=1.0,
                pitch=0
            ),
            rvc_config=RVCConfig(
                model_id=profile_id,
                name=model_name.title(),
                model_path=model_path,
                pitch_shift=0,
                index_rate=0.75,
                filter_radius=3,
                rms_mix_rate=0.25,
                protect=0.33,
                f0_method="rmvpe",
                gender=gender,
                description=f"Auto-detectado desde {model_path}"
            ),
            tags=["character", "auto-detected"]
        )
        
        if self.add_profile(profile):
            print(f"Modelo auto-agregado: {profile_id}")
            return profile_id
        return None
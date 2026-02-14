"""
Gestor de proveedores TTS instalados.
Administra credenciales, validación y estado de providers.
"""
import json
import os
from typing import Dict, Optional, List
from pathlib import Path


class ProviderManager:
    """Administra los proveedores TTS disponibles en la aplicación"""
    
    def __init__(self, config_path: str = "config/providers.json"):
        self.config_path = config_path
        self.providers: Dict[str, dict] = {}
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Cargar o crear configuración
        if os.path.exists(config_path):
            self.load_from_file()
        else:
            self._create_default_config()
            self.save_to_file()
    
    def _create_default_config(self):
        """Crea configuración por defecto (solo Edge TTS)"""
        self.providers = {
            "edge_tts": {
                "name": "Edge TTS (Microsoft)",
                "type": "edge_tts",
                "enabled": True,
                "requires_credentials": False,
                "credentials": None,
                "icon": "🔊"
            }
        }
    
    def add_provider(self, provider_type: str, credentials_path: Optional[str] = None) -> bool:
        """
        Agrega o actualiza un proveedor TTS.
        
        Args:
            provider_type: 'google_tts', 'elevenlabs', etc.
            credentials_path: Ruta al archivo de credenciales (JSON para Google)
            
        Returns:
            True si se agregó/actualizó exitosamente
        """
        # Si ya existe, actualizar credenciales
        is_update = provider_type in self.providers
        
        if is_update:
            provider_config = self.providers[provider_type]
        else:
            # Configuración según tipo
            provider_config = self._get_provider_template(provider_type)
            if not provider_config:
                print(f"Tipo de proveedor desconocido: {provider_type}")
                return False
        
        # Validar credenciales si es necesario
        if provider_config["requires_credentials"]:
            if not credentials_path or not os.path.exists(credentials_path):
                print(f"Se requiere archivo de credenciales para {provider_type}")
                return False
            
            # Validar credenciales
            if not self._validate_credentials(provider_type, credentials_path):
                print(f"Credenciales inválidas para {provider_type}")
                return False
            
            provider_config["credentials"] = credentials_path
            provider_config["enabled"] = True  # Habilitar al agregar credenciales
        
        # Agregar o actualizar provider
        self.providers[provider_type] = provider_config
        self.save_to_file()
        
        action = "actualizado" if is_update else "agregado"
        print(f"Proveedor {provider_config['name']} {action}")
        return True
    
    def remove_provider(self, provider_type: str) -> bool:
        """Elimina un proveedor (excepto Edge TTS que es default)"""
        if provider_type == "edge_tts":
            print("No se puede eliminar Edge TTS (proveedor por defecto)")
            return False
        
        if provider_type in self.providers:
            del self.providers[provider_type]
            self.save_to_file()
            print(f"Proveedor {provider_type} eliminado")
            return True
        
        return False
    
    def get_enabled_providers(self) -> List[dict]:
        """Retorna lista de providers habilitados"""
        return [
            {"type": ptype, **pdata}
            for ptype, pdata in self.providers.items()
            if pdata.get("enabled", True)
        ]
    
    def get_provider_credentials(self, provider_type: str) -> Optional[str]:
        """Obtiene ruta a credenciales de un provider"""
        provider = self.providers.get(provider_type)
        return provider.get("credentials") if provider else None
    
    def _get_provider_template(self, provider_type: str) -> Optional[dict]:
        """Retorna template de configuración según tipo de provider"""
        templates = {
            "google_tts": {
                "name": "Google Cloud TTS",
                "type": "google_tts",
                "enabled": True,
                "requires_credentials": True,
                "credentials": None,
                "icon": "🌐"
            },
            "elevenlabs": {
                "name": "ElevenLabs",
                "type": "elevenlabs",
                "enabled": True,
                "requires_credentials": True,
                "credentials": None,
                "icon": "🎙️"
            }
            # Aquí se agregan más providers en el futuro
        }
        
        return templates.get(provider_type)
    
    def _validate_credentials(self, provider_type: str, credentials_path: str) -> bool:
        """Valida credenciales de un provider"""
        if provider_type == "google_tts":
            try:
                # Verificar que es un JSON válido
                with open(credentials_path, 'r') as f:
                    creds = json.load(f)
                
                # Verificar campos requeridos de Google Cloud
                required_fields = ["type", "project_id", "private_key", "client_email"]
                if not all(field in creds for field in required_fields):
                    print("JSON de Google Cloud incompleto")
                    return False
                
                # Intentar inicializar cliente de Google
                try:
                    from core.tts.google_provider import GoogleTTSProvider, GoogleTTSConfig
                    config = GoogleTTSConfig(credentials_path=credentials_path)
                    provider = GoogleTTSProvider(config)
                    return provider.validate_config()
                except Exception as e:
                    print(f"Error validando Google TTS: {e}")
                    return False
                
            except json.JSONDecodeError:
                print("Archivo de credenciales no es un JSON válido")
                return False
            except Exception as e:
                print(f"Error leyendo credenciales: {e}")
                return False
        
        return True
    
    def save_to_file(self):
        """Guarda configuración a JSON"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump({"providers": self.providers}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando providers: {e}")
    
    def load_from_file(self):
        """Carga configuración desde JSON"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.providers = data.get("providers", {})
            print(f"{len(self.providers)} providers cargados")
            
        except Exception as e:
            print(f"Error cargando providers: {e}")
            self._create_default_config()
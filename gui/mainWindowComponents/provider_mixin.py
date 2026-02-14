"""
Mixin para gestión de providers TTS.
Contiene métodos para cargar y configurar providers (Edge TTS, Google TTS, etc).
"""
from PySide6.QtWidgets import QListWidgetItem
from gui.provider_settings_dialog import ProviderSettingsDialog


class ProviderMixin:
    """Mixin para gestión de providers TTS"""
    
    def _load_providers_list(self):
        """Carga providers en el panel lateral"""
        self.provider_list.clear()
        
        providers = self.provider_manager.get_enabled_providers()
        
        for provider in providers:
            icon = provider.get("icon", "🔊")
            name = provider["name"]
            
            item = QListWidgetItem(f"{icon} {name}")
            self.provider_list.addItem(item)
    
    def _open_provider_settings(self):
        """Abre diálogo de configuración de providers"""
        dialog = ProviderSettingsDialog(
            parent=self,
            provider_manager=self.provider_manager
        )
        
        if dialog.exec():
            # Recargar lista
            self._load_providers_list()
            print("Configuración de providers actualizada")

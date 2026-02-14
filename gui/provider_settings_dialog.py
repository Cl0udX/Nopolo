"""
Diálogo para configurar proveedores TTS.
Permite agregar Google Cloud TTS, ElevenLabs, etc.
"""
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QFileDialog, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt
from core.provider_manager import ProviderManager


class ProviderSettingsDialog(QDialog):
    """Diálogo para gestionar proveedores TTS"""
    
    def __init__(self, parent=None, provider_manager: ProviderManager = None):
        super().__init__(parent)
        self.provider_manager = provider_manager
        
        self.setWindowTitle("Configuración de Proveedores TTS")
        self.resize(500, 400)
        
        self._build_ui()
        self._load_providers()
    
    def _build_ui(self):
        """Construye la interfaz"""
        layout = QVBoxLayout()
        
        # Título
        title = QLabel("Proveedores TTS Instalados")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        
        # Lista de providers
        list_group = QGroupBox("Engines Disponibles")
        list_layout = QVBoxLayout()
        
        self.provider_list = QListWidget()
        self.provider_list.itemSelectionChanged.connect(self._on_selection_changed)
        list_layout.addWidget(self.provider_list)
        
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # Botones de acción
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Agregar Proveedor")
        self.add_btn.clicked.connect(self._show_add_menu)
        button_layout.addWidget(self.add_btn)
        
        self.remove_btn = QPushButton("🗑️ Eliminar")
        self.remove_btn.clicked.connect(self._remove_provider)
        self.remove_btn.setEnabled(False)
        button_layout.addWidget(self.remove_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _load_providers(self):
        """Carga providers en la lista"""
        self.provider_list.clear()
        
        providers = self.provider_manager.get_enabled_providers()
        
        for provider in providers:
            icon = provider.get("icon", "🔊")
            name = provider["name"]
            ptype = provider["type"]
            
            # Indicar si es default
            suffix = " (Por defecto)" if ptype == "edge_tts" else ""
            
            item = QListWidgetItem(f"{icon} {name}{suffix}")
            item.setData(Qt.UserRole, ptype)  # Guardar tipo
            
            self.provider_list.addItem(item)
    
    def _on_selection_changed(self):
        """Callback cuando cambia selección"""
        selected = self.provider_list.currentItem()
        if selected:
            provider_type = selected.data(Qt.UserRole)
            # No permitir eliminar Edge TTS
            self.remove_btn.setEnabled(provider_type != "edge_tts")
    
    def _show_add_menu(self):
        """Muestra menú para agregar provider"""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QCursor
        
        menu = QMenu(self)
        
        # Google Cloud TTS
        google_action = menu.addAction("🌐 Google Cloud TTS")
        google_action.triggered.connect(lambda: self._add_google_tts())
        
        # ElevenLabs (deshabilitado por ahora)
        eleven_action = menu.addAction("🎙️ ElevenLabs (Próximamente)")
        eleven_action.setEnabled(False)
        
        menu.exec(QCursor.pos())
    
    def _add_google_tts(self):
        """Agrega Google Cloud TTS"""
        # Pedir archivo de credenciales
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar credenciales de Google Cloud",
            "",
            "JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        # Intentar agregar/actualizar
        if self.provider_manager.add_provider("google_tts", file_path):
            QMessageBox.information(
                self,
                "Éxito",
                f"Google Cloud TTS configurado correctamente.\n\n"
                f"Credenciales: {os.path.basename(file_path)}\n"
                f"Ahora puedes usarlo en la configuración de voces."
            )
            self._load_providers()
        else:
            QMessageBox.critical(
                self,
                "Error",
                "No se pudo configurar Google Cloud TTS.\n"
                "Verifica que el archivo JSON sea válido y tenga los permisos correctos."
            )
    
    def _remove_provider(self):
        """Elimina provider seleccionado"""
        selected = self.provider_list.currentItem()
        if not selected:
            return
        
        provider_type = selected.data(Qt.UserRole)
        provider_name = selected.text()
        
        # Confirmar
        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar {provider_name}?\n\n"
            "Las voces que usen este proveedor dejarán de funcionar.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.provider_manager.remove_provider(provider_type):
                self._load_providers()
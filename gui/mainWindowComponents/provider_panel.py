"""
Panel de gestión de providers, control de audio y configuración.
Panel derecho de la aplicación.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QListWidget, QLabel
)
from PySide6.QtCore import Signal


class ProviderPanel(QWidget):
    """Panel de gestión de engines TTS, audio y configuración"""
    
    # Señales
    provider_settings_requested = Signal()
    stop_audio_requested = Signal()
    skip_audio_requested = Signal()
    audio_device_settings_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
    
    def _build_ui(self):
        """Construye la interfaz del panel"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # ========== Grupo de providers ==========
        provider_group = QGroupBox("Engines TTS")
        provider_layout = QVBoxLayout()
        
        # Lista de providers
        self.provider_list = QListWidget()
        self.provider_list.setMaximumHeight(150)
        provider_layout.addWidget(self.provider_list)
        
        # Botón de configuración
        self.settings_provider_btn = QPushButton("⚙️ Configurar")
        self.settings_provider_btn.clicked.connect(self.provider_settings_requested.emit)
        provider_layout.addWidget(self.settings_provider_btn)
        
        provider_group.setLayout(provider_layout)
        layout.addWidget(provider_group)
        
        # ========== Grupo de control de reproducción ==========
        playback_group = QGroupBox("Control de Audio")
        playback_layout = QVBoxLayout()
        
        # Botón silenciar
        self.stop_audio_btn = QPushButton("⏹ Silenciar")
        self.stop_audio_btn.clicked.connect(self.stop_audio_requested.emit)
        playback_layout.addWidget(self.stop_audio_btn)
        
        # Botón siguiente
        self.next_audio_btn = QPushButton("⏭ Siguiente")
        self.next_audio_btn.clicked.connect(self.skip_audio_requested.emit)
        playback_layout.addWidget(self.next_audio_btn)
        
        playback_group.setLayout(playback_layout)
        layout.addWidget(playback_group)
        
        # ========== Grupo de configuración de la aplicación ==========
        app_config_group = QGroupBox("Configuración")
        app_config_layout = QVBoxLayout()
        
        # Botón de configuración de audio
        self.audio_device_btn = QPushButton("🔊 Dispositivo de Salida")
        self.audio_device_btn.clicked.connect(self.audio_device_settings_requested.emit)
        app_config_layout.addWidget(self.audio_device_btn)
        
        # Indicador de conexión a internet
        connection_layout = QHBoxLayout()
        self.connection_indicator = QLabel("●")
        self.connection_indicator.setStyleSheet("color: gray; font-size: 16px;")
        self.connection_label = QLabel("Verificando...")
        connection_layout.addWidget(self.connection_indicator)
        connection_layout.addWidget(self.connection_label)
        connection_layout.addStretch()
        app_config_layout.addLayout(connection_layout)
        
        app_config_group.setLayout(app_config_layout)
        layout.addWidget(app_config_group)
        
        layout.addStretch()
        
        self.setLayout(layout)
    
    def load_providers(self, providers_dict):
        """
        Carga la lista de providers.
        providers_dict: {provider_id: provider_data}
        """
        self.provider_list.clear()
        for provider_id, provider_data in providers_dict.items():
            enabled = provider_data.get('enabled', False)
            display_name = provider_data.get('display_name', provider_id)
            status = "✅" if enabled else "⏸"
            self.provider_list.addItem(f"{status} {display_name}")
    
    def set_connection_status(self, connected: bool):
        """Establece el estado de conexión a internet"""
        if connected:
            self.connection_indicator.setStyleSheet("color: green; font-size: 16px;")
            self.connection_label.setText("Conectado")
        else:
            self.connection_indicator.setStyleSheet("color: red; font-size: 16px;")
            self.connection_label.setText("Sin conexión")

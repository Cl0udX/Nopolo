"""
Panel central de control de voz y síntesis.
Incluye selector de voz, entrada de texto y controles principales.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QComboBox, QPushButton, QCheckBox, QLineEdit
)
from PySide6.QtCore import Signal


class VoicePanel(QWidget):
    """Panel central para control de voces y síntesis"""
    
    # Señales
    voice_changed = Signal(str)  # Emite el profile_id de la voz seleccionada
    add_voice_requested = Signal()
    config_voice_requested = Signal()
    scan_models_requested = Signal()
    play_requested = Signal(str, bool)  # texto, is_multivoice
    multivoice_toggled = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
    
    def _build_ui(self):
        """Construye la interfaz del panel"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Sección de selección de voz ---
        voice_group = QGroupBox("Configuración de Voz")
        voice_layout = QHBoxLayout()
        
        voice_layout.addWidget(QLabel("Voz:"))
        self.voice_combo = QComboBox()
        self.voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        voice_layout.addWidget(self.voice_combo, 1)
        
        # Botón para agregar nueva voz
        self.add_voice_btn = QPushButton("➕")
        self.add_voice_btn.setMaximumWidth(40)
        self.add_voice_btn.setToolTip("Agregar nueva voz")
        self.add_voice_btn.clicked.connect(self.add_voice_requested.emit)
        voice_layout.addWidget(self.add_voice_btn)
        
        voice_group.setLayout(voice_layout)
        layout.addWidget(voice_group)
        
        # --- Información de la voz actual ---
        self.voice_info = QLabel("Selecciona una voz")
        self.voice_info.setStyleSheet("color: gray; font-size: 11px;")
        self.voice_info.setWordWrap(True)
        layout.addWidget(self.voice_info)
        
        # --- Sección de entrada de texto ---
        text_group = QGroupBox("Texto a Sintetizar")
        text_layout = QVBoxLayout()
        
        # Checkbox para modo Nopolo
        mode_layout = QHBoxLayout()
        self.multivoice_check = QCheckBox("Modo Nopolo")
        self.multivoice_check.setToolTip(
            "Activa el análisis de sintaxis Nopolo:\n"
            "- voz: texto\n"
            "- (sonido)\n"
            "- voz.filtro: texto\n"
            "- voz.fa: texto con fondo"
        )
        self.multivoice_check.toggled.connect(self.multivoice_toggled.emit)
        mode_layout.addWidget(self.multivoice_check)
        mode_layout.addStretch()
        text_layout.addLayout(mode_layout)
        
        self.input = QLineEdit()
        self.input.setPlaceholderText("Escribe el texto aquí...")
        self.input.returnPressed.connect(self._on_play)
        text_layout.addWidget(self.input)
        
        # Botón de reproducir
        self.button = QPushButton("▶ Reproducir")
        self.button.setMinimumHeight(40)
        self.button.clicked.connect(self._on_play)
        text_layout.addWidget(self.button)
        
        text_group.setLayout(text_layout)
        layout.addWidget(text_group)
        
        # --- Botones de gestión ---
        manage_layout = QHBoxLayout()
        
        self.config_btn = QPushButton("⚙️ Configurar Voz")
        self.config_btn.setToolTip("Editar configuración de la voz actual")
        self.config_btn.clicked.connect(self.config_voice_requested.emit)
        manage_layout.addWidget(self.config_btn)
        
        self.scan_btn = QPushButton("🔍 Escanear Modelos")
        self.scan_btn.setToolTip("Buscar nuevos modelos .pth en voices/")
        self.scan_btn.clicked.connect(self.scan_models_requested.emit)
        manage_layout.addWidget(self.scan_btn)
        
        layout.addLayout(manage_layout)
        
        # Espacio flexible
        layout.addStretch()
        
        self.setLayout(layout)
    
    def _on_voice_changed(self, index):
        """Cuando cambia la selección de voz"""
        profile_id = self.voice_combo.currentData()
        if profile_id:
            self.voice_changed.emit(profile_id)
    
    def _on_play(self):
        """Cuando se presiona reproducir"""
        text = self.input.text().strip()
        if text:
            is_multivoice = self.multivoice_check.isChecked()
            self.play_requested.emit(text, is_multivoice)
    
    def load_voices(self, voices_list):
        """
        Carga las voces en el combo box.
        voices_list: Lista de VoiceProfile
        """
        self.voice_combo.clear()
        for profile in voices_list:
            if profile.enabled:
                self.voice_combo.addItem(profile.display_name, profile.profile_id)
    
    def set_current_voice(self, profile_id):
        """Establece la voz actual por profile_id"""
        index = self.voice_combo.findData(profile_id)
        if index >= 0:
            self.voice_combo.setCurrentIndex(index)
    
    def get_current_voice_id(self):
        """Retorna el profile_id de la voz actual"""
        return self.voice_combo.currentData()
    
    def update_voice_info(self, info_text):
        """Actualiza el texto de información de la voz"""
        self.voice_info.setText(info_text)
    
    def clear_input(self):
        """Limpia el campo de entrada"""
        self.input.clear()
    
    def get_input_text(self):
        """Obtiene el texto ingresado"""
        return self.input.text().strip()
    
    def is_multivoice_mode(self):
        """Retorna True si está en modo multi-voz"""
        return self.multivoice_check.isChecked()

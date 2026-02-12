from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLineEdit, QPushButton, QComboBox, QLabel, QGroupBox
)
from PySide6.QtCore import Qt
from core.tts_engine import TTSEngine
from core.rvc_engine import RVCEngine
from core.audio_queue import AudioQueue
from core.voice_manager import VoiceManager
import sys


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nopolo - Voice Cloning TTS")
        self.resize(600, 250)
        
        # Inicializar VoiceManager
        self.voice_manager = VoiceManager()
        
        # Inicializar engines
        default_profile = self.voice_manager.get_default_profile()
        self.tts_engine = TTSEngine(default_profile.tts_config if default_profile else None)
        self.rvc_engine = RVCEngine()
        
        # Si hay perfil por defecto con RVC, cargarlo
        if default_profile and default_profile.is_transformer_voice():
            self.rvc_engine.load_model(default_profile.rvc_config)
        
        # Inicializar cola de audio
        self.audio_queue = AudioQueue(self.tts_engine, self.rvc_engine)
        
        # Construir UI
        self._build_ui()
        
        # Cargar voces en dropdown
        self._load_voices()
    
    def _build_ui(self):
        """Construye la interfaz de usuario"""
        main_layout = QVBoxLayout()
        
        # --- Sección de selección de voz ---
        voice_group = QGroupBox("Configuración de Voz")
        voice_layout = QHBoxLayout()
        
        voice_layout.addWidget(QLabel("Voz:"))
        self.voice_combo = QComboBox()
        self.voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        voice_layout.addWidget(self.voice_combo, 1)
        
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setMaximumWidth(40)
        self.refresh_btn.setToolTip("Recargar voces")
        self.refresh_btn.clicked.connect(self._refresh_voices)
        voice_layout.addWidget(self.refresh_btn)
        
        voice_group.setLayout(voice_layout)
        main_layout.addWidget(voice_group)
        
        # --- Información de la voz actual ---
        self.voice_info = QLabel("Selecciona una voz")
        self.voice_info.setStyleSheet("color: gray; font-size: 11px;")
        self.voice_info.setWordWrap(True)
        main_layout.addWidget(self.voice_info)
        
        # --- Sección de entrada de texto ---
        text_group = QGroupBox("Texto a Sintetizar")
        text_layout = QVBoxLayout()
        
        self.input = QLineEdit()
        self.input.setPlaceholderText("Escribe el texto aquí...")
        self.input.returnPressed.connect(self.play_text)
        text_layout.addWidget(self.input)
        
        # Botón de reproducir
        self.button = QPushButton("▶ Reproducir")
        self.button.setMinimumHeight(40)
        self.button.clicked.connect(self.play_text)
        text_layout.addWidget(self.button)
        
        text_group.setLayout(text_layout)
        main_layout.addWidget(text_group)
        
        # --- Botones de gestión ---
        manage_layout = QHBoxLayout()
        
        self.scan_btn = QPushButton("🔍 Escanear Modelos")
        self.scan_btn.setToolTip("Buscar nuevos modelos .pth en voices/")
        self.scan_btn.clicked.connect(self._scan_models)
        manage_layout.addWidget(self.scan_btn)
        
        self.config_btn = QPushButton("⚙️ Configurar Voz")
        self.config_btn.setToolTip("Abrir configuración de la voz actual")
        self.config_btn.clicked.connect(self._open_config)
        manage_layout.addWidget(self.config_btn)
        
        main_layout.addLayout(manage_layout)
        
        # Espacio flexible
        main_layout.addStretch()
        
        self.setLayout(main_layout)
    
    def _load_voices(self):
        """Carga las voces disponibles en el dropdown"""
        self.voice_combo.clear()
        
        profiles = self.voice_manager.list_profiles(enabled_only=True)
        
        for profile in profiles:
            # Emoji según tipo
            emoji = "🎭" if profile.is_transformer_voice() else "🔊"
            display_text = f"{emoji} {profile.display_name}"
            
            self.voice_combo.addItem(display_text, profile.profile_id)
        
        # Seleccionar por defecto
        default_id = self.voice_manager.default_voice_id
        if default_id:
            index = self.voice_combo.findData(default_id)
            if index >= 0:
                self.voice_combo.setCurrentIndex(index)
        
        print(f"{len(profiles)} voces cargadas en la interfaz")
    
    def _on_voice_changed(self, index):
        """Callback cuando cambia la voz seleccionada"""
        if index < 0:
            return
        
        profile_id = self.voice_combo.itemData(index)
        profile = self.voice_manager.get_profile(profile_id)
        
        if not profile:
            return
        
        # Actualizar información
        info_parts = []
        info_parts.append(f"<b>{profile.display_name}</b>")
        info_parts.append(f"TTS: {profile.tts_config.voice_id}")
        
        if profile.is_transformer_voice():
            info_parts.append(f"RVC: {profile.rvc_config.name}")
            info_parts.append(f"Pitch: {profile.rvc_config.pitch_shift:+d}")
        else:
            info_parts.append("Sin transformación RVC")
        
        if profile.tags:
            info_parts.append(f"Tags: {', '.join(profile.tags)}")
        
        self.voice_info.setText(" | ".join(info_parts))
        
        # Actualizar engine TTS
        self.tts_engine.update_config(profile.tts_config)
        
        # Cargar modelo RVC si es necesario
        if profile.is_transformer_voice():
            try:
                if (not self.rvc_engine.model_loaded or 
                    self.rvc_engine.config.model_id != profile.rvc_config.model_id):
                    self.rvc_engine.load_model(profile.rvc_config)
            except Exception as e:
                print(f"Error cargando modelo RVC: {e}")
    
    def _refresh_voices(self):
        """Recarga la lista de voces"""
        self.voice_manager.load_from_file()
        self._load_voices()
        print("🔄 Voces recargadas")
    
    def _scan_models(self):
        """Escanea y agrega automáticamente nuevos modelos"""
        new_models = self.voice_manager.scan_rvc_models()
        
        if not new_models:
            print("No se encontraron modelos nuevos")
            return
        
        print(f"{len(new_models)} modelos nuevos encontrados")
        
        for model_path in new_models:
            # Por ahora, asumimos masculino. Luego podemos agregar diálogo
            profile_id = self.voice_manager.auto_add_rvc_model(model_path, gender="male")
            if profile_id:
                print(f"{profile_id}")
        
        self._refresh_voices()
    
    def _open_config(self):
        """Abre ventana de configuración de la voz actual"""
        # TODO: Implementar ventana de configuración detallada
        print("Configuración de voz (próximamente)")
    
    def play_text(self):
        """Reproduce el texto con la voz seleccionada"""
        text = self.input.text().strip()
        if not text:
            return
        
        # Obtener perfil actual
        profile_id = self.voice_combo.currentData()
        profile = self.voice_manager.get_profile(profile_id)
        
        # Agregar a la cola
        self.audio_queue.add(text, profile)
        self.input.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
"""
Diálogo de configuración de voces.
Permite crear nuevas voces o editar existentes.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QComboBox, QSlider, QSpinBox, QDoubleSpinBox,
    QPushButton, QLabel, QFileDialog, QTextEdit, QCheckBox,
    QTabWidget, QWidget, QMessageBox
)
from PySide6.QtCore import Qt
from core.models import VoiceProfile, EdgeTTSConfig, RVCConfig
from core.edge_voices import get_popular_voices
from core.tts_engine import TTSEngine
from core.rvc_engine import RVCEngine
from core.audio_player import play_wav
import os


class VoiceConfigDialog(QDialog):
    """Diálogo para configurar/crear voces"""
    
    def __init__(self, parent=None, profile: VoiceProfile = None, voice_manager=None):
        super().__init__(parent)
        self.profile = profile  # None = modo crear, VoiceProfile = modo editar
        self.voice_manager = voice_manager
        self.is_edit_mode = profile is not None
        
        # Engines temporales para pruebas
        self.temp_tts_engine = None
        self.temp_rvc_engine = None
        
        self.setWindowTitle("Editar Voz" if self.is_edit_mode else "Agregar Nueva Voz")
        self.resize(700, 800)
        
        self._build_ui()
        
        # Si es modo editar, cargar datos
        if self.is_edit_mode:
            self._load_profile_data()
    
    def _build_ui(self):
        """Construye la interfaz"""
        main_layout = QVBoxLayout()
        
        # --- Información básica ---
        basic_group = QGroupBox("Información Básica")
        basic_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("ej: Homero Simpson")
        basic_layout.addRow("Nombre de la voz:", self.name_input)
        
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("ej: homero_simpson (sin espacios)")
        if self.is_edit_mode:
            self.id_input.setEnabled(False)  # No editable en modo editar
        basic_layout.addRow("ID único:", self.id_input)
        
        self.enabled_checkbox = QCheckBox("Voz habilitada")
        self.enabled_checkbox.setChecked(True)
        basic_layout.addRow("", self.enabled_checkbox)
        
        basic_group.setLayout(basic_layout)
        main_layout.addWidget(basic_group)
        
        # --- Tabs para TTS y RVC ---
        tabs = QTabWidget()
        
        # Tab 1: Configuración TTS Base
        tts_tab = self._build_tts_tab()
        tabs.addTab(tts_tab, "🔊 TTS Base (Voz Neutral)")
        
        # Tab 2: Configuración RVC Transformer
        rvc_tab = self._build_rvc_tab()
        tabs.addTab(rvc_tab, "🎭 RVC Transformer (Opcional)")
        
        main_layout.addWidget(tabs)
        
        # --- Área de prueba ---
        test_group = QGroupBox("Probar Configuración")
        test_layout = QVBoxLayout()
        
        self.test_input = QTextEdit()
        self.test_input.setPlaceholderText("Escribe texto para probar la voz...")
        self.test_input.setMaximumHeight(80)
        test_layout.addWidget(self.test_input)
        
        test_buttons = QHBoxLayout()
        
        self.test_tts_btn = QPushButton("🔊 Probar Solo TTS")
        self.test_tts_btn.clicked.connect(self._test_tts_only)
        test_buttons.addWidget(self.test_tts_btn)
        
        self.test_full_btn = QPushButton("🎭 Probar TTS + RVC")
        self.test_full_btn.clicked.connect(self._test_full)
        test_buttons.addWidget(self.test_full_btn)
        
        test_layout.addLayout(test_buttons)
        test_group.setLayout(test_layout)
        main_layout.addWidget(test_group)
        
        # --- Botones de acción ---
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Guardar" if self.is_edit_mode else "➕ Agregar Voz")
        self.save_btn.clicked.connect(self._save)
        self.save_btn.setDefault(True)
        button_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("❌ Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def _build_tts_tab(self):
        """Construye el tab de configuración TTS"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Selector de voz
        voice_group = QGroupBox("Selección de Voz Base")
        voice_layout = QVBoxLayout()
        
        # ComboBox organizado por categorías
        self.voice_combo = QComboBox()
        self.voice_combo.currentTextChanged.connect(self._on_tts_voice_changed)
        
        # Cargar voces organizadas
        popular_voices = get_popular_voices()
        for category, voices in popular_voices.items():
            self.voice_combo.addItem(f"── {category} ──", None)  # Separador
            for voice_id in voices:
                display_name = voice_id.split('-')[-1].replace('Neural', '')
                self.voice_combo.addItem(f"   {display_name}", voice_id)
        
        voice_layout.addWidget(QLabel("Voz:"))
        voice_layout.addWidget(self.voice_combo)
        voice_group.setLayout(voice_layout)
        layout.addWidget(voice_group)
        
        # Configuración de parámetros
        config_group = QGroupBox("Parámetros de TTS")
        config_layout = QFormLayout()
        
        # Velocidad
        speed_layout = QHBoxLayout()
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(50)   # 0.5x
        self.speed_slider.setMaximum(200)  # 2.0x
        self.speed_slider.setValue(100)    # 1.0x
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setTickInterval(25)
        self.speed_label = QLabel("1.0x")
        self.speed_slider.valueChanged.connect(
            lambda v: self.speed_label.setText(f"{v/100:.2f}x")
        )
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_label)
        config_layout.addRow("Velocidad:", speed_layout)
        
        # Pitch
        pitch_layout = QHBoxLayout()
        self.pitch_spinbox = QSpinBox()
        self.pitch_spinbox.setMinimum(-12)
        self.pitch_spinbox.setMaximum(12)
        self.pitch_spinbox.setValue(0)
        self.pitch_spinbox.setSuffix(" semitonos")
        pitch_layout.addWidget(self.pitch_spinbox)
        pitch_layout.addStretch()
        config_layout.addRow("Tono (Pitch):", pitch_layout)
        
        # Volumen
        volume_layout = QHBoxLayout()
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMinimum(0)    # 0%
        self.volume_slider.setMaximum(150)  # 150%
        self.volume_slider.setValue(100)    # 100%
        self.volume_slider.setTickPosition(QSlider.TicksBelow)
        self.volume_slider.setTickInterval(25)
        self.volume_label = QLabel("100%")
        self.volume_slider.valueChanged.connect(
            lambda v: self.volume_label.setText(f"{v}%")
        )
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_label)
        config_layout.addRow("Volumen:", volume_layout)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def _build_rvc_tab(self):
        """Construye el tab de configuración RVC"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Checkbox para habilitar RVC
        self.use_rvc_checkbox = QCheckBox("Usar transformación RVC")
        self.use_rvc_checkbox.stateChanged.connect(self._on_rvc_toggle)
        layout.addWidget(self.use_rvc_checkbox)
        
        # Contenedor para config RVC (se habilita/deshabilita)
        self.rvc_config_widget = QWidget()
        rvc_layout = QVBoxLayout()
        
        # Selector de archivo .pth
        model_group = QGroupBox("Archivo del Modelo")
        model_layout = QHBoxLayout()
        
        self.model_path_input = QLineEdit()
        self.model_path_input.setPlaceholderText("Selecciona un archivo .pth...")
        self.model_path_input.setReadOnly(True)
        model_layout.addWidget(self.model_path_input)
        
        self.browse_btn = QPushButton("📁 Buscar")
        self.browse_btn.clicked.connect(self._browse_model)
        model_layout.addWidget(self.browse_btn)
        
        model_group.setLayout(model_layout)
        rvc_layout.addWidget(model_group)
        
        # Configuración de parámetros RVC
        rvc_params_group = QGroupBox("Parámetros de Conversión")
        rvc_params_layout = QFormLayout()
        
        # Pitch Shift
        pitch_shift_layout = QHBoxLayout()
        self.pitch_shift_spinbox = QSpinBox()
        self.pitch_shift_spinbox.setMinimum(-12)
        self.pitch_shift_spinbox.setMaximum(12)
        self.pitch_shift_spinbox.setValue(0)
        self.pitch_shift_spinbox.setSuffix(" semitonos")
        pitch_shift_layout.addWidget(self.pitch_shift_spinbox)
        pitch_shift_layout.addWidget(QLabel("(ajusta el tono del resultado)"))
        rvc_params_layout.addRow("Pitch Shift:", pitch_shift_layout)
        
        # Index Rate
        index_rate_layout = QHBoxLayout()
        self.index_rate_slider = QSlider(Qt.Horizontal)
        self.index_rate_slider.setMinimum(0)
        self.index_rate_slider.setMaximum(100)
        self.index_rate_slider.setValue(75)
        self.index_rate_label = QLabel("0.75")
        self.index_rate_slider.valueChanged.connect(
            lambda v: self.index_rate_label.setText(f"{v/100:.2f}")
        )
        index_rate_layout.addWidget(self.index_rate_slider)
        index_rate_layout.addWidget(self.index_rate_label)
        rvc_params_layout.addRow("Index Rate:", index_rate_layout)
        
        # Filter Radius
        filter_layout = QHBoxLayout()
        self.filter_spinbox = QSpinBox()
        self.filter_spinbox.setMinimum(0)
        self.filter_spinbox.setMaximum(7)
        self.filter_spinbox.setValue(3)
        filter_layout.addWidget(self.filter_spinbox)
        filter_layout.addWidget(QLabel("(reduce respiración, >=3 recomendado)"))
        rvc_params_layout.addRow("Filter Radius:", filter_layout)
        
        # RMS Mix Rate
        rms_layout = QHBoxLayout()
        self.rms_slider = QSlider(Qt.Horizontal)
        self.rms_slider.setMinimum(0)
        self.rms_slider.setMaximum(100)
        self.rms_slider.setValue(25)
        self.rms_label = QLabel("0.25")
        self.rms_slider.valueChanged.connect(
            lambda v: self.rms_label.setText(f"{v/100:.2f}")
        )
        rms_layout.addWidget(self.rms_slider)
        rms_layout.addWidget(self.rms_label)
        rvc_params_layout.addRow("RMS Mix Rate:", rms_layout)
        
        # Protect
        protect_layout = QHBoxLayout()
        self.protect_slider = QSlider(Qt.Horizontal)
        self.protect_slider.setMinimum(0)
        self.protect_slider.setMaximum(50)
        self.protect_slider.setValue(33)
        self.protect_label = QLabel("0.33")
        self.protect_slider.valueChanged.connect(
            lambda v: self.protect_label.setText(f"{v/100:.2f}")
        )
        protect_layout.addWidget(self.protect_slider)
        protect_layout.addWidget(self.protect_label)
        rvc_params_layout.addRow("Protect:", protect_layout)
        
        # F0 Method
        f0_layout = QHBoxLayout()
        self.f0_combo = QComboBox()
        self.f0_combo.addItems(["rmvpe", "pm", "harvest", "crepe"])
        f0_layout.addWidget(self.f0_combo)
        f0_layout.addWidget(QLabel("(rmvpe recomendado)"))
        rvc_params_layout.addRow("F0 Method:", f0_layout)
        
        # Gender
        gender_layout = QHBoxLayout()
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["male", "female", "neutral"])
        gender_layout.addWidget(self.gender_combo)
        rvc_params_layout.addRow("Género:", gender_layout)
        
        rvc_params_group.setLayout(rvc_params_layout)
        rvc_layout.addWidget(rvc_params_group)
        
        self.rvc_config_widget.setLayout(rvc_layout)
        self.rvc_config_widget.setEnabled(False)  # Deshabilitado por defecto
        layout.addWidget(self.rvc_config_widget)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def _on_tts_voice_changed(self, voice_text):
        """Callback cuando cambia la voz TTS seleccionada"""
        # Aplicar configuración por defecto al cambiar voz
        # Por ahora solo reseteamos valores
        pass
    
    def _on_rvc_toggle(self, state):
        """Habilita/deshabilita configuración RVC"""
        self.rvc_config_widget.setEnabled(self.use_rvc_checkbox.isChecked())
        print(f"RVC habilitado: {self.use_rvc_checkbox.isChecked()}")
    
    def _browse_model(self):
        """Abre diálogo para seleccionar archivo .pth"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Modelo RVC",
            "voices/",
            "Modelos RVC (*.pth)"
        )
        
        if file_path:
            self.model_path_input.setText(file_path)
            
            # Auto-detectar index
            model_dir = os.path.dirname(file_path)
            model_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Buscar .index
            for file in os.listdir(model_dir):
                if file.endswith('.index') and model_name in file:
                    print(f"Index auto-detectado: {file}")
                    break
    
    def _load_profile_data(self):
        """Carga datos del perfil en modo editar"""
        if not self.profile:
            return
        
        # Información básica
        self.name_input.setText(self.profile.display_name)
        self.id_input.setText(self.profile.profile_id)
        self.enabled_checkbox.setChecked(self.profile.enabled)
        
        # TTS Config
        tts = self.profile.tts_config
        # Buscar y seleccionar la voz
        index = self.voice_combo.findData(tts.voice_id)
        if index >= 0:
            self.voice_combo.setCurrentIndex(index)
        
        self.speed_slider.setValue(int(tts.speed * 100))
        self.pitch_spinbox.setValue(tts.pitch)
        self.volume_slider.setValue(int(tts.volume * 100))
        
        # RVC Config - HABILITAR CHECKBOX PRIMERO
        if self.profile.rvc_config:
            self.use_rvc_checkbox.setChecked(True)  # ← ESTO HABILITA EL WIDGET
            rvc = self.profile.rvc_config
            
            self.model_path_input.setText(rvc.model_path)
            self.pitch_shift_spinbox.setValue(rvc.pitch_shift)
            self.index_rate_slider.setValue(int(rvc.index_rate * 100))
            self.filter_spinbox.setValue(rvc.filter_radius)
            self.rms_slider.setValue(int(rvc.rms_mix_rate * 100))
            self.protect_slider.setValue(int(rvc.protect * 100))
            
            f0_index = self.f0_combo.findText(rvc.f0_method)
            if f0_index >= 0:
                self.f0_combo.setCurrentIndex(f0_index)
            
            gender_index = self.gender_combo.findText(rvc.gender)
            if gender_index >= 0:
                self.gender_combo.setCurrentIndex(gender_index)
    
    def _build_tts_config(self) -> EdgeTTSConfig:
        """Construye EdgeTTSConfig desde la UI"""
        voice_id = self.voice_combo.currentData()
        if not voice_id:  # Es un separador
            # Buscar siguiente item válido
            for i in range(self.voice_combo.currentIndex() + 1, self.voice_combo.count()):
                if self.voice_combo.itemData(i):
                    voice_id = self.voice_combo.itemData(i)
                    break
        
        return EdgeTTSConfig(
            voice_id=voice_id or "es-MX-JorgeNeural",
            speed=self.speed_slider.value() / 100.0,
            pitch=self.pitch_spinbox.value(),
            volume=self.volume_slider.value() / 100.0
        )
    
    def _build_rvc_config(self) -> RVCConfig:
        """Construye RVCConfig desde la UI"""
        if not self.use_rvc_checkbox.isChecked():
            return None
        
        model_path = self.model_path_input.text()
        if not model_path:
            return None
        
        model_id = os.path.splitext(os.path.basename(model_path))[0]
        
        return RVCConfig(
            model_id=model_id,
            name=self.name_input.text(),
            model_path=model_path,
            pitch_shift=self.pitch_shift_spinbox.value(),
            index_rate=self.index_rate_slider.value() / 100.0,
            filter_radius=self.filter_spinbox.value(),
            rms_mix_rate=self.rms_slider.value() / 100.0,
            protect=self.protect_slider.value() / 100.0,
            f0_method=self.f0_combo.currentText(),
            gender=self.gender_combo.currentText()
        )
    
    def _test_tts_only(self):
        """Prueba solo TTS sin RVC"""
        text = self.test_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Texto vacío", "Escribe algo para probar")
            return
        
        try:
            # Crear engine temporal con config actual
            tts_config = self._build_tts_config()
            if not self.temp_tts_engine:
                self.temp_tts_engine = TTSEngine(tts_config)
            else:
                self.temp_tts_engine.update_config(tts_config)
            
            # Sintetizar
            print("Probando TTS...")
            wav_path = self.temp_tts_engine.synthesize(text)
            
            # Reproducir
            import scipy.io.wavfile as wavfile
            rate, data = wavfile.read(wav_path)
            play_wav((data.astype('float32') / 32768.0, rate))
            
            # Limpiar
            os.unlink(wav_path)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error probando TTS:\n{e}")
            import traceback
            traceback.print_exc()
    
    def _test_full(self):
        """Prueba TTS + RVC completo"""
        text = self.test_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Texto vacío", "Escribe algo para probar")
            return
        
        if not self.use_rvc_checkbox.isChecked():
            QMessageBox.warning(self, "RVC no habilitado", "Habilita RVC primero o usa 'Probar Solo TTS'")
            return
        
        try:
            # TTS
            tts_config = self._build_tts_config()
            if not self.temp_tts_engine:
                self.temp_tts_engine = TTSEngine(tts_config)
            else:
                self.temp_tts_engine.update_config(tts_config)
            
            print("Generando TTS...")
            wav_path = self.temp_tts_engine.synthesize(text)
            
            # RVC
            rvc_config = self._build_rvc_config()
            if not rvc_config:
                QMessageBox.warning(self, "Config incompleta", "Selecciona un modelo .pth")
                os.unlink(wav_path)
                return
            
            if not self.temp_rvc_engine:
                self.temp_rvc_engine = RVCEngine()
            
            self.temp_rvc_engine.load_model(rvc_config)
            
            print("Aplicando RVC...")
            converted_audio = self.temp_rvc_engine.convert(wav_path, rvc_config)
            
            # Reproducir
            play_wav(converted_audio)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error probando voz completa:\n{e}")
            import traceback
            traceback.print_exc()
    
    def _save(self):
        """Guarda o crea el perfil"""
        # Validar
        name = self.name_input.text().strip()
        profile_id = self.id_input.text().strip()
        
        if not name or not profile_id:
            QMessageBox.warning(self, "Campos vacíos", "Completa el nombre y el ID")
            return
        
        # Construir configs
        tts_config = self._build_tts_config()
        rvc_config = self._build_rvc_config()
        
        # Crear perfil
        new_profile = VoiceProfile(
            profile_id=profile_id,
            display_name=name,
            tts_config=tts_config,
            rvc_config=rvc_config,
            enabled=self.enabled_checkbox.isChecked(),
            tags=["custom"] if not self.is_edit_mode else self.profile.tags
        )
        
        # Validar RVC si está habilitado
        try:
            if rvc_config:
                rvc_config.validate()
        except Exception as e:
            QMessageBox.critical(self, "Error en RVC", f"Configuración RVC inválida:\n{e}")
            return
        
        # Guardar
        if self.voice_manager:
            self.voice_manager.add_profile(new_profile)
        
        self.profile = new_profile
        self.accept()
    
    def get_profile(self) -> VoiceProfile:
        """Retorna el perfil creado/editado"""
        return self.profile
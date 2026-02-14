from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLineEdit, QPushButton, QComboBox, QLabel, QGroupBox,
    QListWidget, QListWidgetItem, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QTabWidget, QSplitter  # ← Pestañas y divisor
)
from PySide6.QtCore import Qt
from core.tts_engine import TTSEngine
from core.rvc_engine import RVCEngine
from core.audio_queue import AudioQueue
from core.voice_manager import VoiceManager
from core.provider_manager import ProviderManager  # ← NUEVO
from core.advanced_processor import AdvancedAudioProcessor  # ← NUEVO
from core.sound_manager import SoundManager  # ← NUEVO
from core.background_manager import BackgroundManager  # ← NUEVO
from gui.voice_config_dialog import VoiceConfigDialog
from gui.provider_settings_dialog import ProviderSettingsDialog  # ← NUEVO
from gui.effects_manager_dialog import EffectsManagerDialog, EffectEditorDialog  # ← NUEVO
import sys
import os
import json


class MainWindow(QWidget):
    def __init__(self, enable_api=False, api_host="0.0.0.0", api_port=8000):
        super().__init__()
        self.setWindowTitle("Nopolo - Voice Cloning TTS")
        self.resize(1200, 600)  # ← Más ancho y alto para 3 paneles
        
        # Configuración de API
        self.enable_api = enable_api
        self.api_host = api_host
        self.api_port = api_port
        self.api_server = None
        
        # Inicializar managers
        self.provider_manager = ProviderManager()  # ← NUEVO
        self.voice_manager = VoiceManager()
        self.sound_manager = SoundManager()  # ← NUEVO
        self.background_manager = BackgroundManager()  # ← NUEVO
        
        # Inicializar engines
        default_profile = self.voice_manager.get_default_profile()
        self.tts_engine = TTSEngine(default_profile.tts_config if default_profile else None)
        self.rvc_engine = RVCEngine()
        
        # Si hay perfil por defecto con RVC, cargarlo
        if default_profile and default_profile.is_transformer_voice():
            self.rvc_engine.load_model(default_profile.rvc_config)
        
        # Inicializar cola de audio
        self.audio_queue = AudioQueue(self.tts_engine, self.rvc_engine)
        
        # Inicializar procesador avanzado (multi-voz)
        self.advanced_processor = AdvancedAudioProcessor(
            voice_manager=self.voice_manager,
            tts_engine=self.tts_engine,
            rvc_engine=self.rvc_engine
        )
        
        # Construir UI
        self._build_ui()
        
        # Cargar voces en dropdown
        self._load_voices()
        
        # Iniciar API si está habilitado
        if self.enable_api:
            self._start_api_server()
    
    def _build_ui(self):
        """Construye la interfaz de usuario"""
        # Layout principal HORIZONTAL con SPLITTER para redimensionar
        main_layout = QHBoxLayout()
        
        # Crear splitter horizontal (permite redimensionar)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # ========== PANEL IZQUIERDO: EFECTOS Y FONDOS (con pestañas) ==========
        left_widget = self._build_effects_panel()
        
        # ========== PANEL CENTRAL: FUNCIONALIDAD PRINCIPAL ==========
        center_widget = QWidget()
        center_panel = QVBoxLayout(center_widget)
        center_panel.setContentsMargins(0, 0, 0, 0)
        
        # --- Sección de API (si está habilitada) ---
        if self.enable_api:
            api_group = QGroupBox("🌐 Servidor REST API")
            api_layout = QHBoxLayout()
            
            self.api_status = QLabel(f"⏳ Iniciando en {self.api_host}:{self.api_port}...")
            self.api_status.setStyleSheet("color: orange;")
            api_layout.addWidget(self.api_status, 1)
            
            self.api_toggle_btn = QPushButton("🛑 Detener")
            self.api_toggle_btn.clicked.connect(self._toggle_api)
            self.api_toggle_btn.setEnabled(False)
            api_layout.addWidget(self.api_toggle_btn)
            
            api_group.setLayout(api_layout)
            center_panel.addWidget(api_group)
        
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
        self.add_voice_btn.clicked.connect(self._add_voice)
        voice_layout.addWidget(self.add_voice_btn)
        
        voice_group.setLayout(voice_layout)
        center_panel.addWidget(voice_group)
        
        # --- Información de la voz actual ---
        self.voice_info = QLabel("Selecciona una voz")
        self.voice_info.setStyleSheet("color: gray; font-size: 11px;")
        self.voice_info.setWordWrap(True)
        center_panel.addWidget(self.voice_info)
        
        # --- Sección de entrada de texto ---
        text_group = QGroupBox("Texto a Sintetizar")
        text_layout = QVBoxLayout()
        
        # Checkbox para modo multi-voz
        mode_layout = QHBoxLayout()
        self.multivoice_check = QCheckBox("Modo Multi-Voz")
        self.multivoice_check.setToolTip(
            "Activa el análisis de sintaxis Mopolo:\n"
            "- voz: texto\n"
            "- (sonido)\n"
            "- voz.filtro: texto\n"
            "- voz.fa: texto con fondo"
        )
        self.multivoice_check.toggled.connect(self._on_multivoice_toggled)
        mode_layout.addWidget(self.multivoice_check)
        mode_layout.addStretch()
        text_layout.addLayout(mode_layout)
        
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
        center_panel.addWidget(text_group)
        
        # --- Botones de gestión ---
        manage_layout = QHBoxLayout()
        
        self.config_btn = QPushButton("⚙️ Configurar Voz")
        self.config_btn.setToolTip("Editar configuración de la voz actual")
        self.config_btn.clicked.connect(self._edit_voice)
        manage_layout.addWidget(self.config_btn)
        
        self.scan_btn = QPushButton("🔍 Escanear Modelos")
        self.scan_btn.setToolTip("Buscar nuevos modelos .pth en voices/")
        self.scan_btn.clicked.connect(self._scan_models)
        manage_layout.addWidget(self.scan_btn)
        
        center_panel.addLayout(manage_layout)
        
        # Espacio flexible
        center_panel.addStretch()
        
        # ========== PANEL DERECHO (gestión de providers) ==========
        right_widget = QWidget()
        right_layout = self._build_provider_panel()
        right_widget.setLayout(right_layout)
        
        # ========== Agregar widgets al splitter ==========
        splitter.addWidget(left_widget)
        splitter.addWidget(center_widget)
        splitter.addWidget(right_widget)
        
        # Tamaños iniciales (proporciones: 25% | 60% | 15%)
        splitter.setStretchFactor(0, 25)  # Efectos/fondos
        splitter.setStretchFactor(1, 60)  # Panel principal
        splitter.setStretchFactor(2, 15)  # Providers
        
        # Agregar splitter al layout principal
        main_layout.addWidget(splitter)
        
        self.setLayout(main_layout)
    

    def _build_provider_panel(self) -> QVBoxLayout:
        """Construye panel de gestión de providers TTS"""
        panel = QVBoxLayout()
        
        # Grupo de providers
        provider_group = QGroupBox("🔌 Engines TTS")
        provider_layout = QVBoxLayout()
        
        # Lista de providers
        self.provider_list = QListWidget()
        self.provider_list.setMaximumHeight(150)
        provider_layout.addWidget(self.provider_list)
        
        # Botones
        btn_layout = QVBoxLayout()
        
        self.add_provider_btn = QPushButton("➕ Agregar")
        self.add_provider_btn.clicked.connect(self._open_provider_settings)
        btn_layout.addWidget(self.add_provider_btn)
        
        self.settings_provider_btn = QPushButton("⚙️ Configurar")
        self.settings_provider_btn.clicked.connect(self._open_provider_settings)
        btn_layout.addWidget(self.settings_provider_btn)
        
        provider_layout.addLayout(btn_layout)
        provider_group.setLayout(provider_layout)
        panel.addWidget(provider_group)
        
        panel.addStretch()
        
        # Cargar providers en lista
        self._load_providers_list()
        
        return panel
    
    def _build_effects_panel(self) -> QWidget:
        """Construye panel de gestión de efectos y fondos CON PESTAÑAS"""
        # Widget contenedor
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Crear widget de pestañas
        tabs = QTabWidget()
        
        # ========== PESTAÑA 1: FILTROS ==========
        filters_widget = QWidget()
        filters_layout = QVBoxLayout(filters_widget)
        
        # Tabla de filtros (SIN editar/eliminar)
        self.filters_table = QTableWidget()
        self.filters_table.setColumnCount(5)  # ID, Nombre, Descripción, Vol, ▶️
        self.filters_table.setHorizontalHeaderLabels([
            "ID", "Nombre", "Descripción", "Vol", "▶️"
        ])
        
        # Configurar tabla de filtros
        header = self.filters_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        filters_layout.addWidget(self.filters_table)
        # NO agregar botón "Agregar" para filtros (son predefinidos)
        
        tabs.addTab(filters_widget, "🎚️ Filtros")
        
        # ========== PESTAÑA 2: SONIDOS ==========
        sounds_widget = QWidget()
        sounds_layout = QVBoxLayout(sounds_widget)
        
        # Tabla de sonidos
        self.sounds_table = QTableWidget()
        self.sounds_table.setColumnCount(7)
        self.sounds_table.setHorizontalHeaderLabels([
            "ID", "Nombre", "Tipo", "Vol", "▶️", "✏️", "🗑️"
        ])
        
        # Configurar tabla de sonidos
        header = self.sounds_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        sounds_layout.addWidget(self.sounds_table)
        
        # Botones para sonidos (agregar + importar)
        sounds_btn_layout = QHBoxLayout()
        self.add_sound_btn = QPushButton("➕ Agregar Sonido")
        self.add_sound_btn.clicked.connect(lambda: self._add_effect("sound"))
        sounds_btn_layout.addWidget(self.add_sound_btn)
        
        self.import_sounds_btn = QPushButton("📥 Importar Sonidos")
        self.import_sounds_btn.clicked.connect(lambda: self._import_audio_files("sound"))
        sounds_btn_layout.addWidget(self.import_sounds_btn)
        sounds_layout.addLayout(sounds_btn_layout)
        
        tabs.addTab(sounds_widget, "🔊 Sonidos")
        
        # ========== PESTAÑA 3: FONDOS ==========
        backgrounds_widget = QWidget()
        backgrounds_layout = QVBoxLayout(backgrounds_widget)
        
        # Tabla de fondos
        self.backgrounds_table = QTableWidget()
        self.backgrounds_table.setColumnCount(7)
        self.backgrounds_table.setHorizontalHeaderLabels([
            "ID", "Nombre", "Tipo", "Vol", "▶️", "✏️", "🗑️"
        ])
        
        # Configurar tabla de fondos
        header = self.backgrounds_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        backgrounds_layout.addWidget(self.backgrounds_table)
        
        # Botones para fondos (agregar + importar)
        backgrounds_btn_layout = QHBoxLayout()
        self.add_background_btn = QPushButton("➕ Agregar Fondo")
        self.add_background_btn.clicked.connect(lambda: self._add_effect("background"))
        backgrounds_btn_layout.addWidget(self.add_background_btn)
        
        self.import_backgrounds_btn = QPushButton("📥 Importar Fondos")
        self.import_backgrounds_btn.clicked.connect(lambda: self._import_audio_files("background"))
        backgrounds_btn_layout.addWidget(self.import_backgrounds_btn)
        backgrounds_layout.addLayout(backgrounds_btn_layout)
        
        tabs.addTab(backgrounds_widget, "🎵 Fondos")
        
        # Agregar tabs al contenedor
        container_layout.addWidget(tabs)
        
        # Cargar datos en las 3 tablas
        self._load_filters_table()
        self._load_sounds_table()
        self._load_backgrounds_table()
        
        return container
    
    def _load_filters_table(self):
        """Carga SOLO los filtros integrados (predefinidos)"""
        self.filters_table.setRowCount(0)
        
        # Filtros integrados (no editables, no eliminables)
        integrated_filters = [
            ('r', 'Eco/Reverberación', 'Agrega eco y reverberación'),
            ('p', 'Llamada', 'Efecto de llamada telefónica'),
            ('pu', 'Aguda', 'Aumenta el pitch (chipmunk)'),
            ('pd', 'Grave', 'Reduce el pitch (monstruo)'),
            ('m', 'Apagada', 'Voz amortiguada (desde afuera)'),
            ('a', 'Robot', 'Efecto de voz sintética/android'),
            ('l', 'Saturada', 'Distorsión/saturación'),
        ]
        
        for filter_id, name, description in integrated_filters:
            self._add_filter_row(filter_id, name, description)
    
    def _load_sounds_table(self):
        """Carga SOLO los sonidos personalizados"""
        self.sounds_table.setRowCount(0)
        
        # Cargar sonidos desde SoundManager
        sounds = self.sound_manager.list_sounds()
        for sound_data in sounds:
            self._add_sound_row(sound_data)
    
    def _load_backgrounds_table(self):
        """Carga SOLO los fondos personalizados"""
        self.backgrounds_table.setRowCount(0)
        
        # Cargar fondos desde BackgroundManager
        backgrounds = self.background_manager.list_backgrounds()
        for bg_id, bg_data in backgrounds.items():
            self._add_background_row(bg_id, bg_data)
    
    def _add_filter_row(self, filter_id, name, description):
        """Agrega un filtro integrado (solo preview, NO editable ni eliminable)"""
        row = self.filters_table.rowCount()
        self.filters_table.insertRow(row)
        
        # ID
        id_item = QTableWidgetItem(str(filter_id))
        self.filters_table.setItem(row, 0, id_item)
        
        # Nombre
        name_item = QTableWidgetItem(name)
        self.filters_table.setItem(row, 1, name_item)
        
        # Descripción
        desc_item = QTableWidgetItem(description)
        self.filters_table.setItem(row, 2, desc_item)
        
        # Volumen (no aplica para filtros)
        vol_item = QTableWidgetItem('-')
        self.filters_table.setItem(row, 3, vol_item)
        
        # Botón preview (test con voz actual)
        btn_preview = QPushButton("▶️")
        btn_preview.setToolTip(f"Probar filtro '{filter_id}' con la voz actual")
        btn_preview.setMaximumWidth(40)
        btn_preview.clicked.connect(lambda: self._test_integrated_filter(filter_id, name))
        self.filters_table.setCellWidget(row, 4, btn_preview)
    
    def _add_sound_row(self, sound_data):
        """Agrega un sonido personalizado (con editar/eliminar)"""
        row = self.sounds_table.rowCount()
        self.sounds_table.insertRow(row)
        
        sound_id = sound_data.get('id', '')
        name = sound_data.get('name', '')
        
        # ID
        id_item = QTableWidgetItem(str(sound_id))
        self.sounds_table.setItem(row, 0, id_item)
        
        # Nombre
        name_item = QTableWidgetItem(name)
        self.sounds_table.setItem(row, 1, name_item)
        
        # Tipo
        type_item = QTableWidgetItem('Sonido')
        self.sounds_table.setItem(row, 2, type_item)
        
        # Volumen
        vol_item = QTableWidgetItem('-')
        self.sounds_table.setItem(row, 3, vol_item)
        
        # Botón preview
        btn_preview = QPushButton("▶️")
        btn_preview.setToolTip("Reproducir sonido")
        btn_preview.setMaximumWidth(40)
        btn_preview.clicked.connect(lambda: self._play_sound_preview(sound_id))
        self.sounds_table.setCellWidget(row, 4, btn_preview)
        
        # Botón editar
        btn_edit = QPushButton("✏️")
        btn_edit.setToolTip("Editar sonido")
        btn_edit.setMaximumWidth(40)
        btn_edit.clicked.connect(lambda: self._edit_sound(sound_id, sound_data))
        self.sounds_table.setCellWidget(row, 5, btn_edit)
        
        # Botón eliminar
        btn_delete = QPushButton("🗑️")
        btn_delete.setToolTip("Eliminar sonido")
        btn_delete.setMaximumWidth(40)
        btn_delete.clicked.connect(lambda: self._delete_sound(sound_id))
        self.sounds_table.setCellWidget(row, 6, btn_delete)
    
    def _add_background_row(self, bg_id, bg_data):
        """Agrega un fondo personalizado (con editar/eliminar)"""
        row = self.backgrounds_table.rowCount()
        self.backgrounds_table.insertRow(row)
        
        name = bg_data.get('name', '')
        volume = bg_data.get('volume', 0.3)
        
        # ID
        id_item = QTableWidgetItem(str(bg_id))
        self.backgrounds_table.setItem(row, 0, id_item)
        
        # Nombre
        name_item = QTableWidgetItem(name)
        self.backgrounds_table.setItem(row, 1, name_item)
        
        # Tipo
        type_item = QTableWidgetItem('Fondo')
        self.backgrounds_table.setItem(row, 2, type_item)
        
        # Volumen
        vol_item = QTableWidgetItem(f"{volume:.2f}")
        self.backgrounds_table.setItem(row, 3, vol_item)
        
        # Botón preview
        btn_preview = QPushButton("▶️")
        btn_preview.setToolTip("Reproducir fondo")
        btn_preview.setMaximumWidth(40)
        btn_preview.clicked.connect(lambda: self._play_background_preview(bg_id))
        self.backgrounds_table.setCellWidget(row, 4, btn_preview)
        
        # Botón editar
        btn_edit = QPushButton("✏️")
        btn_edit.setToolTip("Editar fondo")
        btn_edit.setMaximumWidth(40)
        btn_edit.clicked.connect(lambda: self._edit_background(bg_id, bg_data))
        self.backgrounds_table.setCellWidget(row, 5, btn_edit)
        
        # Botón eliminar
        btn_delete = QPushButton("🗑️")
        btn_delete.setToolTip("Eliminar fondo")
        btn_delete.setMaximumWidth(40)
        btn_delete.clicked.connect(lambda: self._delete_background(bg_id))
        self.backgrounds_table.setCellWidget(row, 6, btn_delete)
    
    def _add_effect(self, effect_type="sound"):
        """Abre diálogo para agregar efecto/fondo"""
        dialog = EffectEditorDialog(self, is_new=True, effect_type=effect_type)
        if dialog.exec():
            # Recargar solo la tabla correspondiente
            if effect_type == "sound":
                self._load_sounds_table()
            elif effect_type == "background":
                self._load_backgrounds_table()
    
    def _edit_sound(self, sound_id, sound_data):
        """Edita un sonido existente"""
        dialog = EffectEditorDialog(self, is_new=False, effect_data=sound_data, effect_type="sound")
        if dialog.exec():
            self._load_sounds_table()
    
    def _edit_background(self, bg_id, bg_data):
        """Edita un fondo existente"""
        dialog = EffectEditorDialog(self, is_new=False, effect_data=bg_data, effect_type="background")
        if dialog.exec():
            self._load_backgrounds_table()
    
    def _delete_sound(self, sound_id):
        """Elimina un sonido"""
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, 
            'Confirmar eliminación',
            f'¿Eliminar sonido ID {sound_id}?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.sound_manager.remove_sound(sound_id)
            self._load_sounds_table()
    
    def _delete_background(self, bg_id):
        """Elimina un fondo"""
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, 
            'Confirmar eliminación',
            f'¿Eliminar fondo "{bg_id}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.background_manager.remove_background(bg_id)
            self._load_backgrounds_table()
    
    def _import_audio_files(self, audio_type="sound"):
        """Importa múltiples archivos de audio (MP3/WAV) de forma masiva
        
        IMPORTANTE: No copia archivos, solo guarda la ruta donde el usuario los tiene.
        El usuario gestiona sus archivos en su propia ubicación.
        
        Args:
            audio_type: "sound" o "background"
        """
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import os
        
        # Abrir diálogo para seleccionar múltiples archivos
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("Audio Files (*.mp3 *.wav)")
        file_dialog.setWindowTitle(f"Importar {'Sonidos' if audio_type == 'sound' else 'Fondos'}")
        
        if not file_dialog.exec():
            return
        
        selected_files = file_dialog.selectedFiles()
        if not selected_files:
            return
        
        # Obtener el siguiente ID disponible
        next_id = self._get_next_available_id(audio_type)
        
        imported_count = 0
        errors = []
        
        for file_path in selected_files:
            try:
                # Obtener nombre del archivo sin extensión
                file_name = os.path.basename(file_path)
                name_without_ext = os.path.splitext(file_name)[0]
                
                # NO copiamos el archivo, solo guardamos la ruta original
                # El usuario gestiona sus archivos donde quiera
                
                # Agregar a la configuración con la ruta ORIGINAL
                if audio_type == "sound":
                    self._add_sound_to_config(
                        sound_id=str(next_id),
                        name=name_without_ext,
                        filename=file_name,
                        path=file_path  # Ruta ORIGINAL del usuario
                    )
                else:  # background
                    self._add_background_to_config(
                        bg_id=f"f{chr(96 + next_id)}" if next_id <= 26 else f"bg{next_id}",
                        name=name_without_ext,
                        path=file_path,  # Ruta ORIGINAL del usuario
                        volume=0.3
                    )
                
                next_id += 1
                imported_count += 1
                
            except Exception as e:
                errors.append(f"{file_name}: {str(e)}")
        
        # Recargar tabla
        if audio_type == "sound":
            self._load_sounds_table()
        else:
            self._load_backgrounds_table()
        
        # Mostrar resumen
        summary = f"✅ Importados {imported_count} archivos exitosamente"
        if errors:
            summary += f"\n\n⚠️ Errores ({len(errors)}):\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                summary += f"\n... y {len(errors) - 5} errores más"
        
        QMessageBox.information(self, "Importación Completa", summary)
    
    def _get_next_available_id(self, audio_type):
        """Obtiene el siguiente ID disponible para sonidos o fondos"""
        if audio_type == "sound":
            sounds = self.sound_manager.list_sounds()
            if not sounds:
                return 1
            # Obtener IDs numéricos y encontrar el máximo
            ids = [int(s.get('id', 0)) for s in sounds if s.get('id', '').isdigit()]
            return max(ids) + 1 if ids else 1
        else:  # background
            backgrounds = self.background_manager.list_backgrounds()
            if not backgrounds:
                return 1
            # Contar cuántos fondos hay
            return len(backgrounds) + 1
    
    def _add_sound_to_config(self, sound_id, name, filename, path):
        """Agrega un sonido al archivo de configuración"""
        import json
        
        config_path = "config/sounds.json"
        
        # Cargar configuración actual
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {"sounds": []}
        
        # Agregar nuevo sonido
        new_sound = {
            "id": sound_id,
            "name": name,
            "filename": filename,
            "path": path,
            "category": "imported",
            "description": ""
        }
        
        config["sounds"].append(new_sound)
        
        # Guardar
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # Recargar manager
        self.sound_manager._load_config()
    
    def _add_background_to_config(self, bg_id, name, path, volume):
        """Agrega un fondo al archivo de configuración"""
        import json
        
        config_path = "config/backgrounds.json"
        
        # Cargar configuración actual
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {"backgrounds": {}}
        
        # Agregar nuevo fondo
        config["backgrounds"][bg_id] = {
            "id": bg_id,
            "name": name,
            "description": "",
            "path": path,
            "volume": volume
        }
        
        # Guardar
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # Recargar manager
        self.background_manager._load_config()
    
    def _play_sound_preview(self, sound_id):
        """Reproduce preview de un sonido"""
        from core.audio_player import play_wav
        import soundfile as sf
        
        sound_data = self.sound_manager.get_sound(sound_id)
        if sound_data and 'path' in sound_data:
            try:
                # Cargar y reproducir el archivo de audio
                audio, sr = sf.read(sound_data['path'], dtype='float32')
                play_wav((audio, sr))
            except Exception as e:
                print(f"⚠️ Error reproduciendo sonido {sound_id}: {e}")
        else:
            print(f"⚠️ No se encontró el sonido {sound_id}")
    
    def _play_background_preview(self, bg_id):
        """Reproduce preview de un fondo (solo 5 segundos)"""
        from core.audio_player import play_wav
        import soundfile as sf
        
        bg_data = self.background_manager.get_background(bg_id)
        if bg_data and 'path' in bg_data:
            try:
                # Cargar audio
                audio, sr = sf.read(bg_data['path'], dtype='float32')
                
                # Reproducir solo 5 segundos para preview
                max_samples = sr * 5
                preview_audio = audio[:max_samples] if len(audio) > max_samples else audio
                
                play_wav((preview_audio, sr))
            except Exception as e:
                print(f"⚠️ Error reproduciendo fondo {bg_id}: {e}")
        else:
            print(f"⚠️ No se encontró el fondo {bg_id}")
    
    def _test_integrated_filter(self, filter_id, filter_name):
        """Ejecuta un test de un filtro integrado con voz de prueba"""
        from PySide6.QtWidgets import QMessageBox
        
        # Obtener ID de voz actual (profile_id, no display_name)
        voice_id = self.voice_combo.currentData()
        if not voice_id:
            QMessageBox.warning(self, "Advertencia", "Selecciona una voz primero")
            return
        
        # Texto de prueba con el filtro (usando profile_id)
        test_text = f"{voice_id}.{filter_id}: Hola como estas, esto es una prueba del filtro {filter_name}. Esto debería sonar con el efecto aplicado."
        
        print(f"🧪 Testing filtro '{filter_id}' ({filter_name})")
        print(f"📝 Texto: {test_text}")
        
        # Usar el modo multi-voz para procesar con el filtro
        try:
            was_multivoice = self.multivoice_check.isChecked()
            
            # Activar temporalmente modo multi-voz si no está activo
            if not was_multivoice:
                self.multivoice_check.setChecked(True)
            
            # Guardar texto actual
            original_text = self.input.text()
            
            # Establecer texto de prueba
            self.input.setText(test_text)
            
            # Reproducir
            self.play_text()
            
            # Restaurar texto original después de un momento
            # (se restaura inmediatamente porque play_text es asíncrono)
            self.input.setText(original_text)
            
            # Restaurar estado de multi-voz
            if not was_multivoice:
                self.multivoice_check.setChecked(False)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al probar filtro: {e}")
            print(f"❌ Error: {e}")
    
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
            print("✅ Configuración de providers actualizada")

    def _start_api_server(self):
        """Inicia el servidor REST API"""
        try:
            from api.rest_server import TTSAPIServer
            
            self.api_server = TTSAPIServer(
                voice_manager=self.voice_manager,
                audio_queue=self.audio_queue,
                host=self.api_host,
                port=self.api_port
            )
            
            self.api_server.start()
            
            # Actualizar UI
            if hasattr(self, 'api_status'):
                self.api_status.setText(f"✅ API corriendo en http://{self.api_host}:{self.api_port}")
                self.api_status.setStyleSheet("color: green;")
                self.api_toggle_btn.setEnabled(True)
            
            print(f"API REST iniciada en http://{self.api_host}:{self.api_port}")
            print(f"Documentación: http://localhost:{self.api_port}/docs")
            
        except ImportError:
            print("No se pudo importar api.rest_server")
            print("Instala las dependencias: pip install fastapi uvicorn")
            if hasattr(self, 'api_status'):
                self.api_status.setText("❌ Error: Falta instalar FastAPI")
                self.api_status.setStyleSheet("color: red;")
        except Exception as e:
            print(f"Error iniciando API: {e}")
            if hasattr(self, 'api_status'):
                self.api_status.setText(f"❌ Error: {e}")
                self.api_status.setStyleSheet("color: red;")
    
    def _toggle_api(self):
        """Inicia/detiene el servidor API"""
        if self.api_server and self.api_server.is_running:
            self.api_server.stop()
            self.api_status.setText(f"🛑 API detenida")
            self.api_status.setStyleSheet("color: gray;")
            self.api_toggle_btn.setText("▶️ Iniciar")
        else:
            self._start_api_server()
            self.api_toggle_btn.setText("🛑 Detener")
    
    def _load_voices(self):
        """Carga las voces disponibles en el dropdown"""
        current_id = self.voice_combo.currentData()
        self.voice_combo.clear()
        
        profiles = self.voice_manager.list_profiles(enabled_only=True)
        
        for profile in profiles:
            # Emoji según tipo
            emoji = "🎭" if profile.is_transformer_voice() else "🔊"
            display_text = f"{emoji} {profile.display_name}"
            
            self.voice_combo.addItem(display_text, profile.profile_id)
        
        # Restaurar selección o usar default
        if current_id:
            index = self.voice_combo.findData(current_id)
            if index >= 0:
                self.voice_combo.setCurrentIndex(index)
        else:
            default_id = self.voice_manager.default_voice_id
            if default_id:
                index = self.voice_combo.findData(default_id)
                if index >= 0:
                    self.voice_combo.setCurrentIndex(index)
        
        print(f"{len(profiles)} voces cargadas")
    
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
    
    def _add_voice(self):
        """Abre diálogo para agregar nueva voz"""
        dialog = VoiceConfigDialog(
            parent=self,
            profile=None,  # Modo crear
            voice_manager=self.voice_manager
        )
        
        if dialog.exec():
            # Voz agregada exitosamente
            print(f"Voz agregada: {dialog.get_profile().display_name}")
            self._load_voices()
            
            # Seleccionar la nueva voz
            new_id = dialog.get_profile().profile_id
            index = self.voice_combo.findData(new_id)
            if index >= 0:
                self.voice_combo.setCurrentIndex(index)
    
    def _edit_voice(self):
        """Abre diálogo para editar voz actual"""
        profile_id = self.voice_combo.currentData()
        if not profile_id:
            return
        
        profile = self.voice_manager.get_profile(profile_id)
        if not profile:
            return
        
        dialog = VoiceConfigDialog(
            parent=self,
            profile=profile,  # Modo editar
            voice_manager=self.voice_manager
        )
        
        if dialog.exec():
            # Voz editada exitosamente
            print(f"Voz actualizada: {dialog.get_profile().display_name}")
            self._load_voices()
    
    def _scan_models(self):
        """Escanea y agrega automáticamente nuevos modelos"""
        new_models = self.voice_manager.scan_rvc_models()
        
        if not new_models:
            print("No se encontraron modelos nuevos")
            return
        
        print(f"{len(new_models)} modelos nuevos encontrados")
        
        for model_path in new_models:
            profile_id = self.voice_manager.auto_add_rvc_model(model_path, gender="male")
            if profile_id:
                print(f"{profile_id}")
        
        self._load_voices()
    
    def _on_multivoice_toggled(self, checked):
        """Callback cuando se activa/desactiva el modo multi-voz."""
        if checked:
            self.input.setPlaceholderText("Ej: dross: hola (disparo) homero: doh!")
        else:
            self.input.setPlaceholderText("Escribe el texto aquí...")
    
    def play_text(self):
        """Reproduce el texto con la voz seleccionada o modo multi-voz"""
        text = self.input.text().strip()
        if not text:
            return
        
        # Verificar modo multi-voz
        if self.multivoice_check.isChecked():
            # Modo multi-voz: procesar con AdvancedProcessor
            try:
                import soundfile as sf
                import sounddevice as sd
                import tempfile
                
                # Procesar mensaje
                audio_data, sample_rate = self.advanced_processor.process_message(text)
                
                # Guardar temporalmente
                temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                temp_file.close()
                sf.write(temp_file.name, audio_data, sample_rate)
                
                # Reproducir
                sd.play(audio_data, sample_rate)
                sd.wait()
                
                # Limpiar archivo temporal
                import os
                os.unlink(temp_file.name)
                
            except Exception as e:
                print(f"Error en modo multi-voz: {e}")
                import traceback
                traceback.print_exc()
        else:
            # Modo tradicional: usar cola de audio
            profile_id = self.voice_combo.currentData()
            profile = self.voice_manager.get_profile(profile_id)
            
            # Agregar a la cola
            self.audio_queue.add(text, profile)
        
        self.input.clear()
    
    def closeEvent(self, event):
        """Limpieza al cerrar la ventana"""
        if self.api_server and self.api_server.is_running:
            print("Deteniendo API Server...")
            self.api_server.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
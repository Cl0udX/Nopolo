"""
Mixin para construcción de la interfaz de usuario.
Contiene todos los métodos de creación de paneles y widgets.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, 
    QLabel, QGroupBox, QListWidget, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QTabWidget, QSplitter, QTextEdit,
    QLineEdit
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QFont, QPixmap, QCursor, QDesktopServices
import sys
import os


class ConsoleRedirector:
    """Redirige stdout/stderr a la consola de la GUI"""
    def __init__(self, console_widget):
        self.console_widget = console_widget
        self.terminal = sys.__stdout__  # Mantener referencia a terminal original
    
    def write(self, text):
        """Escribe en la consola y en la terminal"""
        if text.strip():  # Ignorar líneas vacías
            # Escribir en consola GUI
            self.console_widget.append(text.rstrip())
            # Auto-scroll
            scrollbar = self.console_widget.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
            # También escribir en terminal
            self.terminal.write(text)
            self.terminal.flush()
    
    def flush(self):
        """Flush para compatibilidad"""
        self.terminal.flush()
    
    def isatty(self):
        """Retorna False para indicar que no es una terminal TTY"""
        return False


class ClickableLabel(QLabel):
    """Label clicable que abre una URL en el navegador"""
    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("QLabel:hover { opacity: 0.8; }")
    
    def mousePressEvent(self, event):
        """Abre la URL cuando se hace click"""
        if event.button() == Qt.MouseButton.LeftButton:
            QDesktopServices.openUrl(QUrl(self.url))
        super().mousePressEvent(event)


class UIBuilderMixin:
    """Mixin para construcción de la interfaz de usuario"""
    
    def _build_ui(self):
        """Construye la interfaz de usuario"""
        # Layout principal VERTICAL (para tener paneles arriba y consola abajo)
        main_layout = QVBoxLayout()
        
        # Crear splitter horizontal para los 3 paneles principales
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
        
        # Botón para eliminar voz actual
        self.delete_voice_btn = QPushButton("🗑️")
        self.delete_voice_btn.setMaximumWidth(40)
        self.delete_voice_btn.setToolTip("Eliminar voz seleccionada")
        self.delete_voice_btn.clicked.connect(self._delete_voice)
        voice_layout.addWidget(self.delete_voice_btn)
        
        # Botón para recargar voces desde JSON
        self.reload_voices_btn = QPushButton("🔄")
        self.reload_voices_btn.setMaximumWidth(40)
        self.reload_voices_btn.setToolTip("Recargar voces desde archivo")
        self.reload_voices_btn.clicked.connect(self._reload_voices)
        voice_layout.addWidget(self.reload_voices_btn)
        
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
        
        # Panel de Overlay para OBS (desde OverlayMixin)
        if hasattr(self, '_build_overlay_panel'):
            overlay_panel = self._build_overlay_panel()
            center_panel.addWidget(overlay_panel)
        
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
        
        # Tamaños iniciales (proporciones: 30% | 55% | 15%)
        splitter.setStretchFactor(0, 30)  # Efectos/fondos (más ancho)
        splitter.setStretchFactor(1, 55)  # Panel principal
        splitter.setStretchFactor(2, 15)  # Providers
        
        # Agregar splitter al layout principal
        main_layout.addWidget(splitter)
        
        # ========== CONSOLA DESPLEGABLE ==========
        # Botón para mostrar/ocultar consola
        console_toggle_layout = QHBoxLayout()
        self.console_toggle_btn = QPushButton("▼ Mostrar Consola")
        self.console_toggle_btn.setMaximumHeight(25)
        self.console_toggle_btn.clicked.connect(self._toggle_console)
        console_toggle_layout.addStretch()
        console_toggle_layout.addWidget(self.console_toggle_btn)
        console_toggle_layout.addStretch()
        main_layout.addLayout(console_toggle_layout)
        
        # Widget de consola (inicialmente oculto)
        self.console_widget = QTextEdit()
        self.console_widget.setReadOnly(True)
        self.console_widget.setMaximumHeight(200)
        self.console_widget.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid #3e3e3e;
            }
        """)
        self.console_widget.setPlaceholderText("Los logs de la aplicación aparecerán aquí...")
        self.console_widget.hide()  # Oculto por defecto
        main_layout.addWidget(self.console_widget)
        
        # Redirigir stdout a la consola
        sys.stdout = ConsoleRedirector(self.console_widget)
        
        self.setLayout(main_layout)
    
    def _build_provider_panel(self) -> QVBoxLayout:
        """Construye panel de gestión de providers TTS"""
        panel = QVBoxLayout()
        
        # Grupo de providers
        provider_group = QGroupBox("Engines TTS")
        provider_layout = QVBoxLayout()
        
        # Lista de providers
        self.provider_list = QListWidget()
        self.provider_list.setMaximumHeight(150)
        provider_layout.addWidget(self.provider_list)
        
        # Botón de configuración
        self.settings_provider_btn = QPushButton("⚙️ Configurar")
        self.settings_provider_btn.clicked.connect(self._open_provider_settings)
        provider_layout.addWidget(self.settings_provider_btn)
        
        provider_group.setLayout(provider_layout)
        panel.addWidget(provider_group)
        
        # Grupo de control de reproducción
        playback_group = QGroupBox("Control de Audio")
        playback_layout = QVBoxLayout()
        
        # Botón silenciar
        self.stop_audio_btn = QPushButton("⏹ Silenciar")
        self.stop_audio_btn.clicked.connect(self._stop_audio)
        playback_layout.addWidget(self.stop_audio_btn)
        
        # Botón siguiente
        self.next_audio_btn = QPushButton("⏭ Siguiente")
        self.next_audio_btn.clicked.connect(self._skip_audio)
        playback_layout.addWidget(self.next_audio_btn)
        
        playback_group.setLayout(playback_layout)
        panel.addWidget(playback_group)
        
        # Grupo de configuración de la aplicación
        app_config_group = QGroupBox("Configuración")
        app_config_layout = QVBoxLayout()
        
        # Botón de configuración de audio
        self.audio_device_btn = QPushButton("🔊 Dispositivo de Salida")
        self.audio_device_btn.clicked.connect(self._open_audio_device_settings)
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
        panel.addWidget(app_config_group)
        
        # ========== SECCIÓN DE APOYO Y REDES SOCIALES ==========
        social_group = QGroupBox("Apoya el Proyecto")
        social_layout = QVBoxLayout()
        social_layout.setSpacing(10)
        
        # Banner "Nopolo powered by PostInCloud" - clicable a Ko-fi
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
        
        nopolo_banner = ClickableLabel("https://ko-fi.com/postincloud")
        banner_path = os.path.join(assets_dir, "nopolo_powerby.png")
        if os.path.exists(banner_path):
            pixmap = QPixmap(banner_path)
            # Escalar a un ancho apropiado manteniendo proporción
            scaled_pixmap = pixmap.scaledToWidth(200, Qt.TransformationMode.SmoothTransformation)
            nopolo_banner.setPixmap(scaled_pixmap)
            nopolo_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
            nopolo_banner.setToolTip("Apoya en Ko-fi")
        social_layout.addWidget(nopolo_banner)
        
        # Botones de redes sociales (YouTube y Twitch)
        social_buttons_layout = QHBoxLayout()
        social_buttons_layout.addStretch()
        
        # Botón YouTube
        youtube_btn = ClickableLabel("https://www.youtube.com/@postincloud1")
        youtube_path = os.path.join(assets_dir, "youtube.png")
        if os.path.exists(youtube_path):
            pixmap = QPixmap(youtube_path)
            scaled_pixmap = pixmap.scaledToWidth(60, Qt.TransformationMode.SmoothTransformation)
            youtube_btn.setPixmap(scaled_pixmap)
            youtube_btn.setToolTip("YouTube: @postincloud1")
        social_buttons_layout.addWidget(youtube_btn)
        
        # Botón Twitch
        twitch_btn = ClickableLabel("https://www.twitch.tv/postincloud")
        twitch_path = os.path.join(assets_dir, "twitch.png")
        if os.path.exists(twitch_path):
            pixmap = QPixmap(twitch_path)
            scaled_pixmap = pixmap.scaledToWidth(60, Qt.TransformationMode.SmoothTransformation)
            twitch_btn.setPixmap(scaled_pixmap)
            twitch_btn.setToolTip("Twitch: postincloud")
        social_buttons_layout.addWidget(twitch_btn)
        
        social_buttons_layout.addStretch()
        social_layout.addLayout(social_buttons_layout)
        
        # Texto de apoyo con enlace a Ko-fi
        kofi_label = ClickableLabel("https://ko-fi.com/postincloud")
        kofi_label.setText("☕ Si quieres apoyar al creador\ny mantenimiento, dame un café")
        kofi_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kofi_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 11px;
                padding: 5px;
            }
            QLabel:hover {
                color: #ff5e5b;
                text-decoration: underline;
            }
        """)
        kofi_label.setWordWrap(True)
        kofi_label.setToolTip("Haz click para apoyar en Ko-fi")
        social_layout.addWidget(kofi_label)
        
        social_group.setLayout(social_layout)
        panel.addWidget(social_group)
        
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
        header.setDefaultSectionSize(80)  # Ancho mínimo de columnas
        header.setMinimumSectionSize(40)  # Mínimo absoluto
        header.setFont(QFont("Arial", 11, QFont.Weight.Bold))  # Headers más grandes y bold
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        # Ocultar números de fila
        self.filters_table.verticalHeader().setVisible(False)
        
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
        header.setDefaultSectionSize(80)
        header.setMinimumSectionSize(40)
        header.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        # Ocultar números de fila
        self.sounds_table.verticalHeader().setVisible(False)
        
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
        header.setDefaultSectionSize(80)
        header.setMinimumSectionSize(40)
        header.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        # Ocultar números de fila
        self.backgrounds_table.verticalHeader().setVisible(False)
        
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

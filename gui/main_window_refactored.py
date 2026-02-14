"""
Ventana principal de Nopolo - Versión Refactorizada
Orquesta los componentes modulares para crear la interfaz completa.
"""

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QSplitter, QMessageBox,
    QDialog, QFormLayout, QListWidget, QListWidgetItem, QLabel,
    QPushButton, QHBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

# Componentes modulares
from gui.mainWindowComponents import (
    ConsolePanel, VoicePanel, ProviderPanel, APIPanel
)

# Managers y engines
from core.tts_engine import TTSEngine
from core.rvc_engine import RVCEngine
from core.audio_queue import AudioQueue
from core.voice_manager import VoiceManager
from core.provider_manager import ProviderManager
from core.advanced_processor import AdvancedAudioProcessor
from core.sound_manager import SoundManager
from core.background_manager import BackgroundManager

# Diálogos
from gui.voice_config_dialog import VoiceConfigDialog
from gui.provider_settings_dialog import ProviderSettingsDialog
from gui.effects_manager_dialog import EffectsManagerDialog

import sys
import os
import threading


class MainWindow(QWidget):
    """Ventana principal - Orquestador de componentes"""
    
    def __init__(self, enable_api=False, api_host="0.0.0.0", api_port=8000):
        super().__init__()
        self.setWindowTitle("Nopolo - Voice Cloning TTS")
        self.resize(1400, 550)
        
        # Configuración de API
        self.enable_api = enable_api
        self.api_host = api_host
        self.api_port = api_port
        self.api_server = None
        
        # Inicializar managers
        self._init_managers()
        
        # Construir UI con componentes
        self._build_ui()
        
        # Conectar señales
        self._connect_signals()
        
        # Cargar datos iniciales
        self._load_initial_data()
        
        # Verificar conexión a internet
        self._check_internet_connection()
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self._check_internet_connection)
        self.connection_timer.start(30000)  # Cada 30s
        
        # Iniciar API si está habilitado
        if self.enable_api:
            self._start_api_server()
    
    def _init_managers(self):
        """Inicializa todos los managers y engines"""
        self.provider_manager = ProviderManager()
        self.voice_manager = VoiceManager()
        self.sound_manager = SoundManager()
        self.background_manager = BackgroundManager()
        
        # Engines
        default_profile = self.voice_manager.get_default_profile()
        self.tts_engine = TTSEngine(default_profile.tts_config if default_profile else None)
        self.rvc_engine = RVCEngine()
        
        if default_profile and default_profile.is_transformer_voice():
            self.rvc_engine.load_model(default_profile.rvc_config)
        
        # Cola de audio
        self.audio_queue = AudioQueue(self.tts_engine, self.rvc_engine)
        
        # Procesador avanzado
        self.advanced_processor = AdvancedAudioProcessor(
            voice_manager=self.voice_manager,
            tts_engine=self.tts_engine,
            rvc_engine=self.rvc_engine
        )
    
    def _build_ui(self):
        """Construye la interfaz usando componentes modulares"""
        main_layout = QVBoxLayout()
        
        # Splitter para los 3 paneles principales
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Panel izquierdo: Efectos y Fondos
        self.effects_panel = self._build_effects_panel()
        
        # Panel central: Voz y texto (usando componente)
        self.voice_panel = VoicePanel()
        
        # Panel derecho: Providers y configuración (usando componente)
        self.provider_panel = ProviderPanel()
        
        # Agregar paneles al splitter
        splitter.addWidget(self.effects_panel)
        
        # Si hay API, agregar panel de API al centro
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        
        if self.enable_api:
            self.api_panel = APIPanel(self.api_host, self.api_port)
            center_layout.addWidget(self.api_panel)
        
        center_layout.addWidget(self.voice_panel)
        splitter.addWidget(center_container)
        
        splitter.addWidget(self.provider_panel)
        
        # Proporciones del splitter
        splitter.setStretchFactor(0, 30)
        splitter.setStretchFactor(1, 55)
        splitter.setStretchFactor(2, 15)
        
        main_layout.addWidget(splitter)
        
        # Panel de consola (usando componente)
        self.console_panel = ConsolePanel()
        main_layout.addWidget(self.console_panel)
        
        # Redirigir stdout a la consola
        sys.stdout = self.console_panel.get_redirector()
        
        self.setLayout(main_layout)
    
    def _build_effects_panel(self):
        """Construye panel de efectos y fondos (temporal - luego se modulariza)"""
        from PySide6.QtWidgets import QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        tabs = QTabWidget()
        
        # Tab de efectos
        effects_tab = QWidget()
        effects_layout = QVBoxLayout(effects_tab)
        
        self.effects_table = QTableWidget()
        self.effects_table.setColumnCount(2)
        self.effects_table.setHorizontalHeaderLabels(["ID", "Nombre"])
        
        # Estilo de headers
        header_font = QFont("Arial", 11, QFont.Bold)
        self.effects_table.horizontalHeader().setFont(header_font)
        
        self.effects_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.effects_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        effects_layout.addWidget(self.effects_table)
        
        # Botones
        effects_btn_layout = QVBoxLayout()
        import_effects_btn = QPushButton("Importar Sonidos")
        import_effects_btn.clicked.connect(self._import_sounds)
        effects_btn_layout.addWidget(import_effects_btn)
        
        edit_effect_btn = QPushButton("Editar")
        edit_effect_btn.clicked.connect(self._edit_effect)
        effects_btn_layout.addWidget(edit_effect_btn)
        
        delete_effect_btn = QPushButton("Eliminar")
        delete_effect_btn.clicked.connect(self._delete_effect)
        effects_btn_layout.addWidget(delete_effect_btn)
        
        effects_layout.addLayout(effects_btn_layout)
        
        # Tab de fondos
        backgrounds_tab = QWidget()
        backgrounds_layout = QVBoxLayout(backgrounds_tab)
        
        self.backgrounds_table = QTableWidget()
        self.backgrounds_table.setColumnCount(3)
        self.backgrounds_table.setHorizontalHeaderLabels(["ID", "Nombre", "Volumen"])
        
        self.backgrounds_table.horizontalHeader().setFont(header_font)
        self.backgrounds_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.backgrounds_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.backgrounds_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        backgrounds_layout.addWidget(self.backgrounds_table)
        
        # Botones
        bg_btn_layout = QVBoxLayout()
        import_bg_btn = QPushButton("Importar Fondos")
        import_bg_btn.clicked.connect(self._import_backgrounds)
        bg_btn_layout.addWidget(import_bg_btn)
        
        edit_bg_btn = QPushButton("Editar")
        edit_bg_btn.clicked.connect(self._edit_background)
        bg_btn_layout.addWidget(edit_bg_btn)
        
        delete_bg_btn = QPushButton("Eliminar")
        delete_bg_btn.clicked.connect(self._delete_background)
        bg_btn_layout.addWidget(delete_bg_btn)
        
        backgrounds_layout.addLayout(bg_btn_layout)
        
        tabs.addTab(effects_tab, "Efectos de Audio")
        tabs.addTab(backgrounds_tab, "Fondos de Audio")
        
        layout.addWidget(tabs)
        
        # Cargar datos
        self._load_effects_table()
        self._load_backgrounds_table()
        
        return container
    
    def _connect_signals(self):
        """Conecta las señales de los componentes a los métodos"""
        # Señales del VoicePanel
        self.voice_panel.voice_changed.connect(self._on_voice_changed)
        self.voice_panel.add_voice_requested.connect(self._add_voice)
        self.voice_panel.config_voice_requested.connect(self._edit_voice)
        self.voice_panel.scan_models_requested.connect(self._scan_models)
        self.voice_panel.play_requested.connect(self._play_text)
        self.voice_panel.multivoice_toggled.connect(self._on_multivoice_toggled)
        
        # Señales del ProviderPanel
        self.provider_panel.provider_settings_requested.connect(self._open_provider_settings)
        self.provider_panel.stop_audio_requested.connect(self._stop_audio)
        self.provider_panel.skip_audio_requested.connect(self._skip_audio)
        self.provider_panel.audio_device_settings_requested.connect(self._open_audio_device_settings)
        
        # Señales del APIPanel (si existe)
        if self.enable_api:
            self.api_panel.toggle_requested.connect(self._toggle_api)
    
    def _load_initial_data(self):
        """Carga datos iniciales en los componentes"""
        # Cargar voces en el panel
        profiles = self.voice_manager.list_profiles()
        self.voice_panel.load_voices(profiles)
        
        # Establecer voz por defecto
        default_id = self.voice_manager.get_default_voice_id()
        if default_id:
            self.voice_panel.set_current_voice(default_id)
            self._update_voice_info(default_id)
        
        # Cargar providers
        providers = self.provider_manager.list_providers()
        self.provider_panel.load_providers(providers)
    
    # ========== Métodos de coordinación ==========
    
    def _on_voice_changed(self, profile_id):
        """Cuando cambia la voz seleccionada"""
        self._update_voice_info(profile_id)
        profile = self.voice_manager.get_profile(profile_id)
        
        if profile:
            # Cambiar engine TTS
            self.tts_engine.set_config(profile.tts_config)
            
            # Cargar modelo RVC si es necesario
            if profile.is_transformer_voice():
                self.rvc_engine.load_model(profile.rvc_config)
    
    def _update_voice_info(self, profile_id):
        """Actualiza la información de la voz"""
        profile = self.voice_manager.get_profile(profile_id)
        if profile:
            info_parts = [f"Engine: {profile.tts_config.provider_name}"]
            if profile.is_transformer_voice():
                info_parts.append(f"RVC: {profile.rvc_config.name}")
            info_text = " | ".join(info_parts)
            self.voice_panel.update_voice_info(info_text)
    
    def _on_multivoice_toggled(self, enabled):
        """Cuando se activa/desactiva modo multi-voz"""
        if enabled:
            self.console_panel.log("Modo Nopolo activado - Sintaxis multi-voz habilitada")
        else:
            self.console_panel.log("Modo simple - Una sola voz")
    
    def _play_text(self, text, is_multivoice):
        """Reproduce el texto"""
        if not text:
            return
        
        if is_multivoice:
            # Modo multi-voz en thread separado
            thread = threading.Thread(target=self._play_multivoice, args=(text,), daemon=True)
            thread.start()
        else:
            # Modo simple - usar cola
            profile_id = self.voice_panel.get_current_voice_id()
            profile = self.voice_manager.get_profile(profile_id)
            self.audio_queue.add(text, profile)
    
    def _play_multivoice(self, text):
        """Procesa y reproduce audio multi-voz"""
        try:
            import sounddevice as sd
            audio_data, sample_rate = self.advanced_processor.process_message(text)
            sd.play(audio_data, sample_rate)
            sd.wait()
        except Exception as e:
            print(f"Error en modo multi-voz: {e}")
            import traceback
            traceback.print_exc()
    
    def _stop_audio(self):
        """Detiene el audio actual"""
        self.audio_queue.stop_current()
        print("Audio detenido")
    
    def _skip_audio(self):
        """Salta al siguiente audio"""
        self.audio_queue.skip_to_next()
        queue_size = self.audio_queue.get_queue_size()
        print(f"Saltando al siguiente (quedan {queue_size} en cola)")
    
    def _add_voice(self):
        """Abre diálogo para agregar voz"""
        dialog = VoiceConfigDialog(self, voice_manager=self.voice_manager)
        if dialog.exec():
            self._load_initial_data()
    
    def _edit_voice(self):
        """Abre diálogo para editar voz actual"""
        profile_id = self.voice_panel.get_current_voice_id()
        profile = self.voice_manager.get_profile(profile_id)
        
        if profile:
            dialog = VoiceConfigDialog(self, profile=profile, voice_manager=self.voice_manager)
            if dialog.exec():
                self._load_initial_data()
    
    def _scan_models(self):
        """Escanea modelos RVC en voices/"""
        new_count = self.voice_manager.scan_and_register_models()
        QMessageBox.information(
            self,
            "Escaneo Completo",
            f"Se encontraron {new_count} modelo(s) nuevo(s)"
        )
        self._load_initial_data()
    
    def _open_provider_settings(self):
        """Abre configuración de providers"""
        dialog = ProviderSettingsDialog(self, self.provider_manager)
        if dialog.exec():
            providers = self.provider_manager.list_providers()
            self.provider_panel.load_providers(providers)
    
    def _check_internet_connection(self):
        """Verifica conexión a internet"""
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            self.provider_panel.set_connection_status(True)
            return True
        except OSError:
            self.provider_panel.set_connection_status(False)
            return False
    
    def _open_audio_device_settings(self):
        """Abre configuración de dispositivo de audio"""
        try:
            import sounddevice as sd
            
            devices = sd.query_devices()
            output_devices = [(i, device['name']) for i, device in enumerate(devices) if device['max_output_channels'] > 0]
            current_device = sd.default.device[1]
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Configuración de Dispositivo de Audio")
            dialog.resize(500, 300)
            
            layout = QVBoxLayout()
            layout.addWidget(QLabel("Selecciona el dispositivo de salida de audio:"))
            
            device_list = QListWidget()
            for idx, name in output_devices:
                item = QListWidgetItem(f"{name}")
                item.setData(Qt.UserRole, idx)
                device_list.addItem(item)
                if idx == current_device:
                    device_list.setCurrentItem(item)
            
            layout.addWidget(device_list)
            
            button_layout = QHBoxLayout()
            
            default_btn = QPushButton("Usar Predeterminado del Sistema")
            default_btn.clicked.connect(lambda: self._set_audio_device(None, dialog))
            button_layout.addWidget(default_btn)
            
            apply_btn = QPushButton("Aplicar")
            apply_btn.clicked.connect(lambda: self._set_audio_device(
                device_list.currentItem().data(Qt.UserRole) if device_list.currentItem() else None,
                dialog
            ))
            button_layout.addWidget(apply_btn)
            
            cancel_btn = QPushButton("Cancelar")
            cancel_btn.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_btn)
            
            layout.addLayout(button_layout)
            dialog.setLayout(layout)
            dialog.exec()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cargar dispositivos de audio:\n{str(e)}")
    
    def _set_audio_device(self, device_id, dialog):
        """Establece el dispositivo de audio"""
        try:
            import sounddevice as sd
            
            if device_id is None:
                sd.default.device = sd.default.device[0], None
                self.console_panel.log("Dispositivo de audio: Predeterminado del sistema")
            else:
                sd.default.device = sd.default.device[0], device_id
                devices = sd.query_devices()
                device_name = devices[device_id]['name']
                self.console_panel.log(f"Dispositivo de audio: {device_name}")
            
            dialog.accept()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cambiar dispositivo:\n{str(e)}")
    
    # ========== Métodos de efectos/fondos (temporal) ==========
    
    def _load_effects_table(self):
        """Carga tabla de efectos"""
        sounds = self.sound_manager.list_sounds()
        self.effects_table.setRowCount(len(sounds))
        
        for row, (sound_id, sound_data) in enumerate(sounds.items()):
            self.effects_table.setItem(row, 0, QTableWidgetItem(sound_id))
            self.effects_table.setItem(row, 1, QTableWidgetItem(sound_data.get('name', sound_id)))
    
    def _load_backgrounds_table(self):
        """Carga tabla de fondos"""
        backgrounds = self.background_manager.list_backgrounds()
        self.backgrounds_table.setRowCount(len(backgrounds))
        
        for row, (bg_id, bg_data) in enumerate(backgrounds.items()):
            self.backgrounds_table.setItem(row, 0, QTableWidgetItem(bg_id))
            self.backgrounds_table.setItem(row, 1, QTableWidgetItem(bg_data.get('name', bg_id)))
            self.backgrounds_table.setItem(row, 2, QTableWidgetItem(f"{bg_data.get('volume', 0.3):.2f}"))
    
    def _import_sounds(self):
        """Importa sonidos"""
        dialog = EffectsManagerDialog(self, self.sound_manager)
        if dialog.exec():
            self._load_effects_table()
    
    def _edit_effect(self):
        """Edita efecto seleccionado"""
        # Por ahora solo mensaje
        QMessageBox.information(self, "Editar", "Funcionalidad de edición próximamente")
    
    def _delete_effect(self):
        """Elimina efecto seleccionado"""
        # Por ahora solo mensaje
        QMessageBox.information(self, "Eliminar", "Funcionalidad de eliminación próximamente")
    
    def _import_backgrounds(self):
        """Importa fondos"""
        dialog = EffectsManagerDialog(self, self.background_manager)
        if dialog.exec():
            self._load_backgrounds_table()
    
    def _edit_background(self):
        """Edita fondo seleccionado"""
        QMessageBox.information(self, "Editar", "Funcionalidad de edición próximamente")
    
    def _delete_background(self):
        """Elimina fondo seleccionado"""
        QMessageBox.information(self, "Eliminar", "Funcionalidad de eliminación próximamente")
    
    # ========== API Server ==========
    
    def _start_api_server(self):
        """Inicia el servidor API"""
        try:
            from api.rest_server import APIServer
            
            self.api_server = APIServer(
                self.api_host,
                self.api_port,
                self.voice_manager,
                self.audio_queue,
                self.advanced_processor
            )
            
            self.api_server.start()
            
            if self.enable_api:
                self.api_panel.set_running()
            
            print(f"API REST iniciado en http://{self.api_host}:{self.api_port}")
            print(f"Documentación: http://localhost:{self.api_port}/docs")
            
        except Exception as e:
            print(f"Error al iniciar API: {e}")
            if self.enable_api:
                self.api_panel.set_error(str(e))
    
    def _toggle_api(self):
        """Inicia/detiene el servidor API"""
        if self.api_server and self.api_server.is_running:
            self.api_server.stop()
            self.api_panel.set_stopped()
        else:
            self._start_api_server()
    
    def closeEvent(self, event):
        """Limpieza al cerrar"""
        if self.api_server and self.api_server.is_running:
            print("Deteniendo API Server...")
            self.api_server.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

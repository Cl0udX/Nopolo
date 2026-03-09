"""
Ventana principal de Nopolo - Voice Cloning TTS.
Utiliza mixins para organizar la funcionalidad en componentes modulares.
"""
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QIcon, QPixmap
from core.tts_engine import TTSEngine
from core.rvc_engine import RVCEngine
from core.audio_queue import AudioQueue
from core.voice_manager import VoiceManager
from core.provider_manager import ProviderManager
from core.advanced_processor import AdvancedAudioProcessor
from core.sound_manager import SoundManager
from core.background_manager import BackgroundManager
from gui.mainWindowComponents import (
    UIBuilderMixin,
    TableManagerMixin,
    EffectsManagerMixin,
    ImportManagerMixin,
    ProviderMixin,
    APIMixin,
    VoiceMixin,
    PlaybackMixin,
    ControlsMixin,
    SystemConfigMixin,
    OverlayMixin,
    UpdateMixin,
)
import sys


class MainWindow(
    UIBuilderMixin,
    TableManagerMixin,
    EffectsManagerMixin,
    ImportManagerMixin,
    ProviderMixin,
    APIMixin,
    VoiceMixin,
    PlaybackMixin,
    ControlsMixin,
    SystemConfigMixin,
    OverlayMixin,
    UpdateMixin,
    QWidget
):
    """Ventana principal de la aplicación Nopolo"""
    
    def __init__(self, enable_api=False, api_host="0.0.0.0", api_port=8000):
        super().__init__()
        self.setWindowTitle("Nopolo")
        self.resize(1400, 550)  # Más ancho y altura moderada para la consola
        
        # Establecer icono de ventana con múltiples tamaños
        import os
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "nopolo_icon.png")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            pixmap = QPixmap(icon_path)
            # Añadir múltiples tamaños para mejor compatibilidad con Windows taskbar
            icon.addPixmap(pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            icon.addPixmap(pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            icon.addPixmap(pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            icon.addPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            icon.addPixmap(pixmap.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            icon.addPixmap(pixmap.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.setWindowIcon(icon)
        
        # Configuración de API
        self.enable_api = enable_api
        self.api_host = api_host
        self.api_port = api_port
        self.api_server = None
        
        # Inicializar managers
        self.provider_manager = ProviderManager()
        self.voice_manager = VoiceManager()
        self.sound_manager = SoundManager()
        self.background_manager = BackgroundManager()
        
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
        
        # Construir UI (definido en UIBuilderMixin)
        self._build_ui()
        
        # Cargar voces en dropdown (definido en VoiceMixin)
        self._load_voices()
        
        # Iniciar verificación de conexión a internet (definido en SystemConfigMixin)
        self._check_internet_connection()
        
        # Cargar configuración de dispositivo de audio (definido en SystemConfigMixin)
        self._load_audio_device_config()
        
        # Timer para verificar conexión periódicamente (cada 30 segundos)
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self._check_internet_connection)
        self.connection_timer.start(30000)  # 30 segundos
        
        # Iniciar API si está habilitado (definido en APIMixin)
        if self.enable_api:
            self._start_api_server()

        # Verificar actualizaciones en segundo plano (definido en UpdateMixin)
        self._schedule_update_check(delay_ms=5000)
    
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
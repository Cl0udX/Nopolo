# main.py
import sys
import os
import builtins
if not hasattr(builtins, 'help'):
    def help_placeholder(*args, **kwargs):
        pass
    builtins.help = help_placeholder
import argparse

from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt

# Cargar variables de entorno
load_dotenv()

def get_env_bool(key: str, default: bool = False) -> bool:
    """Helper para leer booleanos del .env"""
    value = os.getenv(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')

def get_env_int(key: str, default: int) -> int:
    """Helper para leer enteros del .env"""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default

def setup_windows_taskbar_icon():
    """Configura el icono para la barra de tareas de Windows"""
    if sys.platform == 'win32':
        try:
            import ctypes
            # Establecer App User Model ID para que Windows reconozca la app
            myappid = 'nopolo.voicestudio.app.1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except:
            pass  # Si falla, continuar sin icono en taskbar

def setup_app_icon(app: QApplication):
    """Configura el icono de la aplicación"""
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "nopolo_icon.png")
    if os.path.exists(icon_path):
        icon = QIcon(icon_path)
        pixmap = QPixmap(icon_path)
        # Añadir múltiples tamaños al icono para mejor compatibilidad con Windows
        icon.addPixmap(pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        icon.addPixmap(pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        icon.addPixmap(pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        icon.addPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        icon.addPixmap(pixmap.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        icon.addPixmap(pixmap.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        app.setWindowIcon(icon)

def setup_signal_handlers():
    """Configura manejadores de señales para limpieza de emergencia"""
    import signal
    import sys
    
    def emergency_shutdown(signum, frame):
        """Limpieza de emergencia antes de cerrar"""
        print("\n" + "="*50)
        print("SEÑAL DE CIERRE RECIBIDA - Ejecutando limpieza de emergencia...")
        print("="*50)
        
        try:
            # Intentar limpiar el motor RVC si existe
            from gui.main_window import MainWindow
            if hasattr(MainWindow, '_instance') and MainWindow._instance:
                if hasattr(MainWindow._instance, 'audio_queue') and MainWindow._instance.audio_queue:
                    if hasattr(MainWindow._instance.audio_queue, 'rvc_engine') and MainWindow._instance.audio_queue.rvc_engine:
                        MainWindow._instance.audio_queue.rvc_engine.emergency_cleanup()
        except Exception as e:
            print(f"Error en limpieza de emergencia: {e}")
        
        print("Limpieza completada. Cerrando programa...")
        sys.exit(0)
    
    # Registrar manejadores para señales comunes
    signal.signal(signal.SIGINT, emergency_shutdown)   # Ctrl+C
    signal.signal(signal.SIGTERM, emergency_shutdown)  # Termination signal
    
    # En macOS, también manejar SIGUSR1 para debugging
    if sys.platform == "darwin":
        signal.signal(signal.SIGUSR1, emergency_shutdown)


def main():
    # Configurar manejadores de señales ANTES de crear QApplication
    setup_signal_handlers()
    
    parser = argparse.ArgumentParser(
        description="Nopolo TTS - Text to Speech con RVC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modos de ejecución:
  1. GUI + API Server (Predeterminado): python main.py
  2. Solo GUI:                          python main.py --only-gui
  3. Solo API Server:                   python main.py --no-gui
  
Configuración en .env para personalizar rutas y puertos.
        """
    )
    
    # Nuevos argumentos con lógica invertida
    parser.add_argument(
        "--only-gui",
        action="store_true",
        help="Inicia solo la interfaz gráfica sin el servidor API"
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Inicia solo el servidor API sin interfaz gráfica"
    )
    parser.add_argument(
        "--api-port",
        type=int,
        default=get_env_int("API_PORT", 8000),
        help=f"Puerto del servidor API (default desde .env: {os.getenv('API_PORT', '8000')})"
    )
    parser.add_argument(
        "--api-host",
        default=os.getenv("API_HOST", "0.0.0.0"),
        help=f"Host del servidor API (default desde .env: {os.getenv('API_HOST', '0.0.0.0')})"
    )
    
    args = parser.parse_args()
    
    # DETERMINAR MODO DE EJECUCIÓN (Lógica actualizada)
    if args.no_gui:
        run_mode = "api_only"
    elif args.only_gui:
        run_mode = "gui_only"
    else:
        # Por defecto, o si se fuerza por .env, arranca ambos
        run_mode = "gui_with_api"
    
    # Ejecutar según modo
    print("=" * 70)
    print("Nopolo TTS - Text to Speech con transformadores de voz RVC")
    print("=" * 70)
    
    if run_mode == "api_only":
        print("Modo: API Server (sin GUI)")
        print(f"Host: {args.api_host}:{args.api_port}")
        print("=" * 70)
        from run_api import main as run_api_main
        sys.argv = [
            "run_api.py",
            "--host", args.api_host,
            "--port", str(args.api_port)
        ]
        run_api_main()
    
    elif run_mode == "gui_with_api":
        print("Modo: GUI + API Server")
        print(f"API Server: http://{args.api_host}:{args.api_port}")
        print(f"Documentación: http://localhost:{args.api_port}/docs")
        print("=" * 70)
        
        # Configurar icono de taskbar ANTES de crear QApplication
        setup_windows_taskbar_icon()
        
        # Importar solo el splash screen primero (es ligero)
        from gui.splash_screen import SplashScreen
        from PySide6.QtCore import QTimer
        
        app = QApplication(sys.argv)
        setup_app_icon(app)
        
        # Mostrar splash screen INMEDIATAMENTE
        splash = SplashScreen()
        splash.show()
        app.processEvents()  # Asegurar que el splash se dibuje
        
        # Variables para almacenar la ventana
        window = None
        
        def load_main_window():
            """Carga la ventana principal después de que el splash se haya renderizado"""
            nonlocal window
            
            # AHORA importar MainWindow (pesado - tarda varios segundos)
            # Mientras tanto, el timer del splash sigue actualizando la animación
            from gui.main_window import MainWindow
            
            # Procesar eventos durante la creación de la ventana
            app.processEvents()
            
            # Crear ventana principal mientras el splash está visible
            window = MainWindow(
                enable_api=True,
                api_host=args.api_host,
                api_port=args.api_port
            )
            
            # Cuando el splash termine, mostrar la ventana principal
            def show_main_window():
                window.show()
            
            splash.loading_finished.connect(show_main_window)
        
        # Dar un pequeño delay para que el splash se renderice completamente
        # antes de empezar la carga pesada
        QTimer.singleShot(100, load_main_window)
        
        sys.exit(app.exec())
    
    else:  # gui_only
        print("Modo: Solo GUI")
        print("Tip: Usa --with-api para habilitar el servidor REST")
        print("=" * 70)
        
        # Configurar icono de taskbar ANTES de crear QApplication
        setup_windows_taskbar_icon()
        
        # Importar solo el splash screen primero (es ligero)
        from gui.splash_screen import SplashScreen
        from PySide6.QtCore import QTimer
        
        app = QApplication(sys.argv)
        setup_app_icon(app)
        
        # Mostrar splash screen INMEDIATAMENTE
        splash = SplashScreen()
        splash.show()
        app.processEvents()  # Asegurar que el splash se dibuje
        
        # Variables para almacenar la ventana
        window = None
        
        def load_main_window():
            """Carga la ventana principal después de que el splash se haya renderizado"""
            nonlocal window
            
            # AHORA importar MainWindow (pesado - tarda varios segundos)
            # Mientras tanto, el timer del splash sigue actualizando la animación
            from gui.main_window import MainWindow
            
            # Procesar eventos durante la creación de la ventana
            app.processEvents()
            
            # Crear ventana principal mientras el splash está visible
            window = MainWindow()
            
            # Cuando el splash termine, mostrar la ventana principal
            def show_main_window():
                window.show()
            
            splash.loading_finished.connect(show_main_window)
        
        # Dar un pequeño delay para que el splash se renderice completamente
        # antes de empezar la carga pesada
        QTimer.singleShot(100, load_main_window)
        
        sys.exit(app.exec())

if __name__ == "__main__":
    main()
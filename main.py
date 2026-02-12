# main.py
import sys
import argparse
import os
from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication

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

def main():
    parser = argparse.ArgumentParser(
        description="Nopolo TTS - Text to Speech con RVC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modos de ejecución:
  1. Solo GUI:           python main.py
  2. Solo API Server:    python main.py --no-gui
  3. GUI + API Server:   python main.py --with-api
  
Configuración en .env para personalizar rutas y puertos.
        """
    )
    
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Solo API Server sin interfaz gráfica"
    )
    parser.add_argument(
        "--with-api",
        action="store_true",
        help="GUI + API Server simultáneamente"
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
    
    # Determinar modo de ejecución
    if args.no_gui:
        run_mode = "api_only"
    elif args.with_api or get_env_bool("GUI_AUTO_START_API"):
        run_mode = "gui_with_api"
    else:
        run_mode = "gui_only"
    
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
        
        from gui.main_window import MainWindow
        app = QApplication(sys.argv)
        window = MainWindow(
            enable_api=True,
            api_host=args.api_host,
            api_port=args.api_port
        )
        window.show()
        sys.exit(app.exec())
    
    else:  # gui_only
        print("Modo: Solo GUI")
        print("Tip: Usa --with-api para habilitar el servidor REST")
        print("=" * 70)
        
        from gui.main_window import MainWindow
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())

if __name__ == "__main__":
    main()
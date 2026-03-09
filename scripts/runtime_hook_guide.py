"""
Runtime hook de PyInstaller para Generar_Guia_Nopolo.
Se ejecuta ANTES que cualquier código del programa.

Parchea get_base_path() para que apunte a la carpeta de datos del usuario
en lugar de la carpeta donde vive el ejecutable.

Rutas de datos del usuario por sistema:
  macOS   : ~/Library/Application Support/Nopolo/
  Windows : %APPDATA%\\Nopolo\\
  Linux   : ~/.local/share/Nopolo/
"""
import os
import sys
from pathlib import Path


def _get_nopolo_user_data_dir() -> Path:
    """Devuelve la carpeta de datos de usuario de Nopolo según el SO."""
    if sys.platform == "win32":
        appdata = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(appdata) / "Nopolo"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Nopolo"
    else:
        xdg = os.getenv("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        return Path(xdg) / "Nopolo"


# Inyectar la variable de entorno que generate_guide.py leerá
os.environ["NOPOLO_GUIDE_DATA_DIR"] = str(_get_nopolo_user_data_dir())

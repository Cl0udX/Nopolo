"""
Módulo central de rutas de Nopolo.

Detecta si la aplicación corre en modo BUILD (ejecutable compilado)
o en modo DEV (directorio de proyecto).

- En modo BUILD:
    - Windows : %APPDATA%\\Nopolo\\
    - macOS   : ~/Library/Application Support/Nopolo/
    - Linux   : ~/.local/share/Nopolo/

- En modo DEV:
    - Usa directamente las carpetas del proyecto (comportamiento anterior).

La variable de entorno NOPOLO_ENV puede forzar el modo:
    NOPOLO_ENV=build  → fuerza modo build (útil para testing)
    NOPOLO_ENV=dev    → fuerza modo dev   (valor por defecto en desarrollo)

Las carpetas de usuario que se gestionan son:
    backgrounds/, voices/, sounds/, overlay/, config/
"""

import os
import sys
import shutil
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Detección del modo de ejecución
# ──────────────────────────────────────────────

def _is_frozen() -> bool:
    """Devuelve True cuando se ejecuta como ejecutable PyInstaller."""
    return getattr(sys, "frozen", False)


def get_run_mode() -> str:
    """
    Devuelve 'build' o 'dev' según el entorno de ejecución.

    Orden de prioridad:
      1. Variable de entorno NOPOLO_ENV
      2. Detección automática (frozen → build, script → dev)
    """
    env_override = os.getenv("NOPOLO_ENV", "").strip().lower()
    if env_override in ("build", "dev"):
        return env_override
    return "build" if _is_frozen() else "dev"


# ──────────────────────────────────────────────
# Directorio base de la aplicación (binarios / código fuente)
# ──────────────────────────────────────────────

def get_app_base_dir() -> Path:
    """
    Directorio donde están los archivos de la aplicación (lectura).
    - build : _MEIPASS (internal de PyInstaller)
    - dev   : raíz del repositorio
    """
    if _is_frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ──────────────────────────────────────────────
# Directorio de datos de usuario (lectura/escritura)
# ──────────────────────────────────────────────

def get_user_data_dir() -> Path:
    """
    Directorio donde se guardan los datos editables del usuario.

    - build/Windows : %APPDATA%\\Nopolo
    - build/macOS   : ~/Library/Application Support/Nopolo
    - build/Linux   : ~/.local/share/Nopolo
    - dev           : raíz del proyecto (igual que antes)
    """
    if get_run_mode() == "dev":
        return get_app_base_dir()

    # ── Modo build ──
    platform = sys.platform
    if platform == "win32":
        appdata = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(appdata) / "Nopolo"
    elif platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Nopolo"
    else:  # Linux y otros
        xdg = os.getenv("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        return Path(xdg) / "Nopolo"


# ──────────────────────────────────────────────
# Rutas de carpetas específicas
# ──────────────────────────────────────────────

def get_voices_dir() -> Path:
    return get_user_data_dir() / "voices"

def get_backgrounds_dir() -> Path:
    return get_user_data_dir() / "backgrounds"

def get_sounds_dir() -> Path:
    return get_user_data_dir() / "sounds"

def get_overlay_dir() -> Path:
    return get_user_data_dir() / "overlay"

def get_config_dir() -> Path:
    return get_user_data_dir() / "config"

# Rutas de archivos de configuración específicos
def get_voices_config() -> Path:
    return get_config_dir() / "voices.json"

def get_backgrounds_config() -> Path:
    return get_config_dir() / "backgrounds.json"

def get_sounds_config() -> Path:
    return get_config_dir() / "sounds.json"

def get_providers_config() -> Path:
    return get_config_dir() / "providers.json"

def get_app_settings_config() -> Path:
    return get_config_dir() / "app_settings.json"

def get_edge_voices_config() -> Path:
    return get_config_dir() / "edge_voices.json"

def get_overlay_html() -> Path:
    return get_overlay_dir() / "overlay.html"


# ──────────────────────────────────────────────
# Lista de carpetas de usuario gestionadas
# ──────────────────────────────────────────────

# (nombre_en_bundle, ruta_destino_en_user_data)
USER_DATA_FOLDERS = [
    "backgrounds",
    "voices",
    "sounds",
    "overlay",
    "config",
]


# ──────────────────────────────────────────────
# Inicialización: copiar archivos del bundle → user data
# ──────────────────────────────────────────────

def _copy_folder_defaults(src: Path, dst: Path) -> None:
    """
    Copia de src a dst de forma incremental:
    - Si dst no existe → copiar todo.
    - Si dst existe → copiar solo archivos que NO existan en dst.
    No sobreescribe archivos que el usuario ya tenga.
    """
    if not src.exists():
        logger.warning(f"[paths] Carpeta fuente no encontrada: {src}")
        return

    dst.mkdir(parents=True, exist_ok=True)

    for item in src.rglob("*"):
        relative = item.relative_to(src)
        dest_item = dst / relative

        if item.is_dir():
            dest_item.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            if not dest_item.exists():
                dest_item.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_item)
                logger.debug(f"[paths] Copiado: {relative}")
            # Si ya existe → no tocar (preservar cambios del usuario)


def initialize_user_data() -> None:
    """
    Punto de entrada principal.
    Llama a esto desde main.py al arrancar la aplicación.

    - En modo dev: no hace nada (usa archivos del proyecto).
    - En modo build: copia las carpetas del bundle a user_data_dir si no existen.
    """
    mode = get_run_mode()
    user_dir = get_user_data_dir()
    app_dir  = get_app_base_dir()

    logger.info(f"[paths] Modo: {mode}")
    logger.info(f"[paths] Directorio usuario: {user_dir}")
    logger.info(f"[paths] Directorio app:     {app_dir}")

    if mode == "dev":
        logger.info("[paths] Modo DEV — usando archivos del proyecto directamente.")
        return

    # Modo build: asegurar que las carpetas de usuario existen
    user_dir.mkdir(parents=True, exist_ok=True)

    for folder in USER_DATA_FOLDERS:
        src = app_dir / folder
        dst = user_dir / folder
        logger.info(f"[paths] Verificando carpeta '{folder}'...")
        _copy_folder_defaults(src, dst)

    logger.info("[paths] Inicialización de datos de usuario completada.")


# ──────────────────────────────────────────────
# Utilidad de diagnóstico
# ──────────────────────────────────────────────

def print_paths_info() -> None:
    """Imprime en consola las rutas activas para diagnóstico."""
    print("=" * 55)
    print(f"  NOPOLO PATHS  |  Modo: {get_run_mode().upper()}")
    print("=" * 55)
    print(f"  App base dir : {get_app_base_dir()}")
    print(f"  User data dir: {get_user_data_dir()}")
    print(f"  voices/      : {get_voices_dir()}")
    print(f"  backgrounds/ : {get_backgrounds_dir()}")
    print(f"  sounds/      : {get_sounds_dir()}")
    print(f"  overlay/     : {get_overlay_dir()}")
    print(f"  config/      : {get_config_dir()}")
    print("=" * 55)

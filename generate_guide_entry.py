#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Punto de entrada compilado para Generar_Guia_Nopolo.

Parchea get_base_path() para que use la carpeta de datos del usuario
(~/Library/Application Support/Nopolo/ en macOS, %APPDATA%\\Nopolo en Windows)
en lugar del directorio del ejecutable.

Este archivo SÍ se puede modificar. generate_guide.py NO se toca.
"""

import os
import sys
from pathlib import Path


def _get_nopolo_user_data_dir() -> Path:
    """Devuelve la carpeta de datos de usuario de Nopolo según el SO."""
    # El runtime hook ya la pone en la variable de entorno
    env_dir = os.environ.get("NOPOLO_GUIDE_DATA_DIR", "")
    if env_dir:
        return Path(env_dir)

    # Fallback por si el hook no corrió (ejecución directa del .py)
    if sys.platform == "win32":
        appdata = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(appdata) / "Nopolo"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Nopolo"
    else:
        xdg = os.getenv("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        return Path(xdg) / "Nopolo"


# ── Parchear get_base_path() ANTES de importar generate_guide ────────────────
import generate_guide as _guide

_user_data_dir = _get_nopolo_user_data_dir()
_guide.get_base_path = lambda: _user_data_dir
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _guide.generate_html_guide()
    input("\nPresiona ENTER para salir...")

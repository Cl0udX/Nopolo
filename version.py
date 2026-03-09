"""
Versión centralizada de Nopolo.
Lee los valores desde version.json para mantener una única fuente de verdad.
Modificar version.json para actualizar la versión en todo el proyecto.
"""
import json
import os

_VERSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version.json")

def _load_version() -> dict:
    try:
        with open(_VERSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "version": "0.0.0",
            "app_name": "Nopolo",
            "author": "Cl0udX",
            "description": ""
        }

_data = _load_version()

__version__     = _data["version"]
__app_name__    = _data["app_name"]
__author__      = _data["author"]
__description__ = _data["description"]

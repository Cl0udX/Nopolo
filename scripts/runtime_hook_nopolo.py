"""
Runtime hook de PyInstaller para Nopolo.
Se ejecuta ANTES que cualquier código del programa al arrancar el ejecutable.
Establece NOPOLO_ENV=build para que core/paths.py use el directorio
de AppData/Library en vez del directorio de la aplicación.
"""
import os
os.environ.setdefault("NOPOLO_ENV", "build")

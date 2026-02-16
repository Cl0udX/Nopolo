# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file para Nopolo
Genera un ejecutable standalone para Windows
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Recopilar todos los submódulos necesarios
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtWidgets',
    'PySide6.QtGui',
    'sounddevice',
    'numpy',
    'scipy',
    'pydub',
    'edge_tts',
    'soundfile',
    'librosa',
    'parselmouth',
    'pyworld',
    'torchcrepe',
    'faiss',
    'dotenv',
    'av',
    'fastapi',
    'uvicorn',
    'pydantic',
    'aiohttp',
    'tensorboardX',
    'google.cloud.texttospeech',
    'fairseq',
    'torch',
    'torchvision',
    'torchaudio',
]

# Agregar todos los submódulos de los paquetes principales
hiddenimports += collect_submodules('PySide6')
hiddenimports += collect_submodules('fastapi')
hiddenimports += collect_submodules('uvicorn')
hiddenimports += collect_submodules('torch')
hiddenimports += collect_submodules('fairseq')

# Datos adicionales a incluir
datas = []
datas += collect_data_files('edge_tts')
datas += collect_data_files('fairseq')
datas += collect_data_files('librosa')

# Agregar archivos propios del proyecto
datas += [
    ('assets', 'assets'),
    ('config', 'config'),
    ('gui', 'gui'),
    ('core', 'core'),
    ('rvc', 'rvc'),
    ('scripts', 'scripts'),
    ('.env.example', '.'),
    ('README.md', '.'),
    ('LICENSE', '.'),
]

# Binarios adicionales (opcional)
binaries = []

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'PIL',
        'pytest',
        'IPython',
        'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Nopolo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Mostrar consola para debug
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/nopolo_icon.png',  # Icono de la aplicación
    version_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Nopolo',
)

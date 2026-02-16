# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file para Nopolo
Genera un ejecutable standalone para Windows
"""
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Importar la versión del proyecto
sys.path.insert(0, os.path.abspath('.'))
from version import __version__, __app_name__

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

# Incluir todos los submódulos de fairseq y sus dependencias
hiddenimports += collect_submodules('fairseq')
hiddenimports += collect_submodules('fairseq.models')
hiddenimports += collect_submodules('fairseq.data')
hiddenimports += collect_submodules('fairseq.tasks')
hiddenimports += collect_submodules('fairseq.modules')
hiddenimports += collect_submodules('fairseq.optim')
hiddenimports += collect_submodules('fairseq.criterions')
hiddenimports += collect_submodules('fairseq.logging')

datas = []

import fairseq
fairseq_path = os.path.dirname(fairseq.__file__)

# Lista de todas las carpetas internas que fairseq escanea dinámicamente
fairseq_subfolders = [
    'criterions', 
    'models', 
    'tasks', 
    'modules', 
    'optim', 
    'data', 
    'dataclass',
    'scoring',
    'benchmark'
]

for folder in fairseq_subfolders:
    folder_full_path = os.path.join(fairseq_path, folder)
    if os.path.exists(folder_full_path):
        datas.append((folder_full_path, os.path.join('fairseq', folder)))

# Por si acaso, incluimos cualquier archivo .py suelto en la raíz de fairseq
datas.append((fairseq_path, 'fairseq'))

# Datos adicionales a incluir
datas += collect_data_files('edge_tts')
datas += collect_data_files('librosa')

# FUNCIÓN CORREGIDA para copiar carpetas
def copytree_for_bundle(src, dst):
    """
    Copia recursivamente una carpeta manteniendo la estructura correcta
    """
    if not os.path.exists(src):
        print(f"WARNING: Carpeta {src} no existe, omitiendo")
        return
    
    for root, dirs, files in os.walk(src):
        # Calcular ruta relativa desde src
        rel_dir = os.path.relpath(root, src)
        
        for file in files:
            # Ruta completa del archivo fuente
            src_file = os.path.join(root, file)
            
            # Ruta destino correcta
            if rel_dir == '.':
                # Archivo en raíz de src
                dst_file = os.path.join(dst, file)
            else:
                # Archivo en subcarpeta
                dst_file = os.path.join(dst, rel_dir, file)
            
            # Agregar a datas
            datas.append((src_file, os.path.dirname(dst_file)))
            print(f"  → Agregando: {src_file} → {dst_file}")

# Copiar carpetas que irán a _internal (luego el script las mueve)
print("\n📦 Copiando carpetas al bundle...")
copytree_for_bundle('backgrounds', 'backgrounds')
copytree_for_bundle('voices', 'voices')
copytree_for_bundle('sounds', 'sounds')
copytree_for_bundle('overlay', 'overlay')

# Copiar .env si existe
if os.path.exists('.env'):
    datas.append(('.env', '.'))
    print("  → Agregando: .env")

# Copiar carpetas del código fuente
datas += [
    ('assets', 'assets'),
    ('config', 'config'),
    ('gui', 'gui'),
    ('core', 'core'),
    ('rvc', 'rvc'),
    ('scripts', 'scripts'),
    ('version.py', '.'),
]

# Binarios adicionales (DLLs de CUDA/Torch)
binaries = []
try:
    from PyInstaller.utils.hooks import collect_dynamic_libs
    binaries += collect_dynamic_libs('torch')
    print("\n✅ DLLs de Torch recolectadas con éxito.")
except Exception as e:
    print(f"\n⚠ WARNING: No se pudieron recolectar librerías dinámicas de Torch: {e}")

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
    name=f'{__app_name__}-{__version__}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/nopolo_icon.png',
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
    name=f'{__app_name__}-{__version__}',
)

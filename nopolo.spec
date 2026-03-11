# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file para Nopolo
Genera un ejecutable standalone para Windows
"""
import sys
import os
import json
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Importar la versión del proyecto desde version.json
sys.path.insert(0, os.path.abspath('.'))
with open(os.path.join(os.path.abspath('.'), 'version.json'), 'r', encoding='utf-8') as _vf:
    _vdata = json.load(_vf)
__version__ = _vdata['version']
__app_name__ = _vdata['app_name']

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

# Copiar carpetas que irán al bundle interno (_internal)
# En modo BUILD estas carpetas se copian a AppData/Library del usuario
# al primer inicio (ver core/paths.py - initialize_user_data)
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
    ('version.json', '.'),    # Fuente de verdad de versión
]

# Binarios adicionales (DLLs de CUDA/Torch)
binaries = []
try:
    from PyInstaller.utils.hooks import collect_dynamic_libs
    binaries += collect_dynamic_libs('torch')
    print("\n✅ DLLs de Torch recolectadas con éxito.")
except Exception as e:
    print(f"\n⚠ WARNING: No se pudieron recolectar librerías dinámicas de Torch: {e}")

# En Windows: incluir python.exe dentro de _internal/ para que el worker
# subprocess use exactamente la misma versión que compiló el bundle.
# Sin esto, si el usuario tiene Python 3.12 en el PATH se produce:
#   ImportError: Module use of python310.dll conflicts with this version of Python
import platform as _build_platform, shutil as _build_shutil
if _build_platform.system() == "Windows":
    _py_exe = _build_shutil.which("python.exe") or sys.executable
    if _py_exe and os.path.isfile(_py_exe):
        binaries.append((_py_exe, "."))
        print(f"\n✅ python.exe incluido en bundle: {_py_exe}")
    else:
        print("\n⚠ WARNING: No se encontró python.exe para incluir en el bundle.")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['scripts/runtime_hook_nopolo.py'],
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

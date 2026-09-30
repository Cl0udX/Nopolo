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
# torchfcpe (método F0 "fcpe" de RVC) y su cadena de dependencias, ninguna
# detectada por PyInstaller porque solo se importan dinámicamente dentro de
# una función (rvc/rvc/modules/vc/pipeline.py), nunca en un import de nivel
# superior en el código propio: torchfcpe -> einops + local_attention;
# local_attention -> einops + hyper_connections; hyper_connections -> einops.
# Todas son puro Python, sin binarios que compilar.
hiddenimports += collect_submodules('torchfcpe')
hiddenimports += collect_submodules('einops')
hiddenimports += collect_submodules('local_attention')
hiddenimports += collect_submodules('hyper_connections')

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
# torchfcpe: método F0 "fcpe" de RVC. Se importa dinámicamente dentro de una
# función (rvc/rvc/modules/vc/pipeline.py) por lo que PyInstaller no lo
# detecta solo -- sin esto, "ModuleNotFoundError: No module named 'torchfcpe'"
# al usar una voz configurada con Método F0 = fcpe. También trae un modelo
# (.pt) que hay que incluir como dato, no como módulo.
datas += collect_data_files('torchfcpe')

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
    print("\nDLLs de Torch recolectadas con éxito.")
except Exception as e:
    print(f"\n⚠ WARNING: No se pudieron recolectar librerías dinámicas de Torch: {e}")

# Bundlear ffmpeg y ffprobe para que pydub funcione sin instalación externa
import shutil as _build_shutil2
for _ff_bin in ("ffmpeg", "ffprobe", "ffmpeg.exe", "ffprobe.exe"):
    _ff_path = _build_shutil2.which(_ff_bin)
    if _ff_path and os.path.isfile(_ff_path):
        binaries.append((_ff_path, "."))
        print(f"\n{_ff_bin} incluido en bundle: {_ff_path}")
        break  # solo necesitamos uno por tipo
for _ff_bin in ("ffprobe", "ffprobe.exe"):
    _ff_path = _build_shutil2.which(_ff_bin)
    if _ff_path and os.path.isfile(_ff_path):
        binaries.append((_ff_path, "."))
        print(f"\nffprobe incluido en bundle: {_ff_path}")
        break

# En Windows: incluir un Python STANDALONE dentro de _internal/pyworker/
# para que el worker subprocess (RVC/multi-voz) tenga un intérprete que
# funcione en una máquina limpia sin Python instalado.
#
# IMPORTANTE -- por qué NO alcanza con copiar solo python.exe:
# shutil.which("python.exe") encuentra el .venv ACTIVADO (ej.
# .venv\Scripts\python.exe), que es apenas un lanzador -- depende de un
# pyvenv.cfg que apunta a la instalación real de Python (home=C:\PythonXXX)
# para encontrar su Lib/ y DLLs/. Esa instalación real NO existe en la PC
# del usuario final, así que ese python.exe copiado solo falla al arrancar
# con "No pyvenv.cfg file" y el worker de RVC/multi-voz nunca funciona
# (aunque el resto de la app sí, porque el modo normal no usa este
# subprocess).
#
# La solución: usar sys.base_prefix (la instalación REAL de Python, no el
# venv activado) y copiar el .exe + su DLL principal + Lib/ + DLLs/ juntos
# a _internal/pyworker/. Con Lib/ y DLLs/ al lado del .exe, Python se
# autodescubre por "landmark search" (busca Lib/os.py junto al ejecutable)
# sin necesitar pyvenv.cfg -- exactamente como una distribución de Python
# portable. Ver core/rvc_subprocess_persistent.py::_find_python_executable.
#
# En macOS: incluir python3 también — macOS moderno (Ventura+) NO viene con
# Python3 instalado por defecto. Sin esto el worker falla en Macs limpias.
import platform as _build_platform, shutil as _build_shutil
if _build_platform.system() == "Windows":
    _py_base = sys.base_prefix  # instalación REAL, no self.prefix (el venv)
    _py_major, _py_minor = sys.version_info.major, sys.version_info.minor

    _pyworker_bins = [
        os.path.join(_py_base, "python.exe"),
        os.path.join(_py_base, f"python{_py_major}.dll"),
        os.path.join(_py_base, f"python{_py_major}{_py_minor}.dll"),
    ]
    _pyworker_ok = True
    for _pf in _pyworker_bins:
        if os.path.isfile(_pf):
            binaries.append((_pf, "pyworker"))
            print(f"\npyworker: incluido {_pf}")
        else:
            _pyworker_ok = False
            print(f"\n⚠ WARNING: No se encontró {_pf} para el pyworker standalone.")

    def _copy_pystdlib_for_pyworker(src_dir, dest_subdir):
        """
        Copia Lib/ o DLLs/ de la instalación BASE de Python (sys.base_prefix)
        a _internal/pyworker/<dest_subdir>, excluyendo __pycache__ y paquetes
        que el worker no necesita, para no inflar el tamaño del bundle.

        CRÍTICO: excluir "site-packages" -- si la instalación base tiene
        paquetes instalados globalmente (torch, etc. -- puede pasar si
        alguna vez se corrió pip install fuera de un venv), site-packages
        puede pesar VARIOS GB. El worker no lo necesita: los paquetes de
        terceros (torch, core/, rvc/, ...) ya están en _internal/ (bundleados
        aparte por PyInstaller) y el worker los encuentra ahí via sys.path
        (ver el script embebido más abajo: sys.path.insert(0, base_dir)).
        Aquí solo hace falta la librería estándar pura para que el
        intérprete arranque.
        """
        if not os.path.isdir(src_dir):
            print(f"\n⚠ WARNING: {src_dir} no existe -- el pyworker standalone puede fallar.")
            return
        count = 0
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d not in
                       ("__pycache__", "test", "tests", "idlelib", "tkinter",
                        "site-packages", "turtledemo", "msilib", "ensurepip", "lib2to3")]
            rel = os.path.relpath(root, src_dir)
            dest_root = os.path.join("pyworker", dest_subdir)
            dest_dir = dest_root if rel == "." else os.path.join(dest_root, rel)
            for f in files:
                datas.append((os.path.join(root, f), dest_dir))
                count += 1
        print(f"\npyworker: {count} archivos de {os.path.basename(src_dir)} incluidos en pyworker/{dest_subdir}/")

    if _pyworker_ok:
        _copy_pystdlib_for_pyworker(os.path.join(_py_base, "Lib"), "Lib")
        _copy_pystdlib_for_pyworker(os.path.join(_py_base, "DLLs"), "DLLs")

    # Se deja además el .exe suelto en _internal/ (comportamiento previo)
    # como fallback si por algo pyworker/ no se armó bien -- ver paso 2b en
    # _find_python_executable(). No soluciona el bug por sí solo, pero no
    # hace daño tenerlo.
    _py_exe = _build_shutil.which("python.exe") or sys.executable
    if _py_exe and os.path.isfile(_py_exe):
        binaries.append((_py_exe, "."))
        print(f"\npython.exe (fallback suelto) incluido en bundle: {_py_exe}")
elif _build_platform.system() == "Darwin":
    _py_exe = _build_shutil.which("python3") or _build_shutil.which("python")
    if _py_exe and os.path.isfile(_py_exe):
        binaries.append((_py_exe, "."))
        print(f"\npython3 incluido en bundle: {_py_exe}")
    else:
        print("\n⚠ WARNING: No se encontró python3 para incluir en el bundle.")

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

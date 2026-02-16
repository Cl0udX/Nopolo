#!/usr/bin/env python3
"""
Script automatizado para generar ejecutable de Nopolo con PyInstaller
Soporta: Windows (.exe), macOS (.app), Linux (binario)
"""

import sys
import os
import platform
import subprocess
import shutil
import argparse
from pathlib import Path

# Colores para terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    print("=" * 70)
    print(f"{Colors.HEADER}{Colors.BOLD}  NOPOLO - Build Executable{Colors.ENDC}")
    print("  Generador de ejecutable standalone")
    print("=" * 70)
    print()

def detect_system():
    """Detecta el sistema operativo"""
    system = platform.system()
    arch = platform.machine()
    
    if system == "Windows":
        return "windows", arch
    elif system == "Darwin":
        return "macos", arch
    elif system == "Linux":
        return "linux", arch
    else:
        return "unknown", arch

def check_pyinstaller():
    """Verifica que PyInstaller esté instalado"""
    try:
        import PyInstaller
        print(f"{Colors.OKGREEN}✅ PyInstaller detectado: {PyInstaller.__version__}{Colors.ENDC}")
        return True
    except ImportError:
        print(f"{Colors.FAIL}❌ PyInstaller no está instalado{Colors.ENDC}")
        print(f"{Colors.WARNING}   Instálalo con: pip install pyinstaller{Colors.ENDC}")
        return False

def clean_build_dirs():
    """Limpia directorios de builds anteriores"""
    print("\n🧹 Limpiando builds anteriores...")
    
    dirs_to_clean = ['build', 'dist', '__pycache__']
    files_to_clean = ['*.spec~']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"   Eliminado: {dir_name}/")
    
    print(f"{Colors.OKGREEN}✅ Limpieza completada{Colors.ENDC}")

def create_version_file(system_name):
    """Crea archivo de versión para Windows"""
    if system_name != "windows":
        return None
    
    version_file = """# UTF-8
#
# Version info para Nopolo Windows
#
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [
            StringStruct(u'CompanyName', u'PostInCloud'),
            StringStruct(u'FileDescription', u'Nopolo Voice Studio - TTS con RVC'),
            StringStruct(u'FileVersion', u'1.0.0.0'),
            StringStruct(u'InternalName', u'Nopolo'),
            StringStruct(u'LegalCopyright', u'Copyright (c) 2026 PostInCloud'),
            StringStruct(u'OriginalFilename', u'Nopolo.exe'),
            StringStruct(u'ProductName', u'Nopolo Voice Studio'),
            StringStruct(u'ProductVersion', u'1.0.0.0')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    
    with open('version.txt', 'w', encoding='utf-8') as f:
        f.write(version_file)
    
    return 'version.txt'

def move_folders_outside_internal():
    """
    IMPORTANTE: Mueve carpetas de _internal/ al mismo nivel que el .exe
    PyInstaller siempre mete todo en _internal/, pero necesitamos estas carpetas fuera.
    """
    print(f"\n📁 Moviendo carpetas fuera de _internal...")
    
    dist_path = Path('dist/Nopolo')
    internal_path = dist_path / '_internal'
    
    if not dist_path.exists():
        print(f"{Colors.FAIL}❌ No se encontró dist/Nopolo{Colors.ENDC}")
        return False
    
    if not internal_path.exists():
        print(f"{Colors.WARNING}⚠ No se encontró _internal/ (build antiguo?){Colors.ENDC}")
        return False
    
    # Carpetas que deben estar al mismo nivel que el .exe
    folders_to_move = ['backgrounds', 'voices', 'sounds', 'overlay', 'config']
    
    for folder_name in folders_to_move:
        source = internal_path / folder_name
        destination = dist_path / folder_name
        
        if source.exists():
            # Si ya existe en destino, eliminarlo primero
            if destination.exists():
                shutil.rmtree(destination)
            
            # Mover carpeta fuera de _internal
            shutil.move(str(source), str(destination))
            print(f"{Colors.OKGREEN}   ✓ Movido: {folder_name}/ → dist/Nopolo/{folder_name}/{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}   ⚠ No encontrado en _internal: {folder_name}/{Colors.ENDC}")
    
    # Mover archivo .env si existe
    env_source = internal_path / '.env'
    env_destination = dist_path / '.env'
    
    if env_source.exists():
        if env_destination.exists():
            env_destination.unlink()
        shutil.move(str(env_source), str(env_destination))
        print(f"{Colors.OKGREEN}   ✓ Movido: .env → dist/Nopolo/.env{Colors.ENDC}")
    else:
        print(f"{Colors.WARNING}   ⚠ No encontrado: .env (esto es normal si usas .env.example){Colors.ENDC}")
    
    print(f"{Colors.OKGREEN}✅ Carpetas reorganizadas correctamente{Colors.ENDC}")
    return True

def copy_additional_files():
    """Copia archivos adicionales necesarios para la distribución"""
    print(f"\n📄 Copiando archivos adicionales...")
    
    dist_path = Path('dist/Nopolo')
    
    if not dist_path.exists():
        print(f"{Colors.FAIL}❌ No se encontró dist/Nopolo{Colors.ENDC}")
        return False
    
    # Archivos a copiar desde el proyecto a dist/Nopolo/
    files_to_copy = {
        'README.md': 'README.md',
        'LICENSE': 'LICENSE',
        '.env.example': '.env.example',
    }
    
    for src_file, dst_file in files_to_copy.items():
        src = Path(src_file)
        dst = dist_path / dst_file
        
        if src.exists():
            shutil.copy2(src, dst)
            print(f"{Colors.OKGREEN}   ✓ Copiado: {src_file}{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}   ⚠ No encontrado: {src_file}{Colors.ENDC}")
    
    # Crear README en voices/ si no existe
    voices_path = dist_path / 'voices'
    if voices_path.exists():
        voices_readme = voices_path / 'README.txt'
        if not voices_readme.exists():
            readme_content = """🎤 INSTRUCCIONES PARA AGREGAR VOCES RVC

Para agregar tus propios modelos de voz:

1. Crea una carpeta con el nombre de la voz dentro de "voices/"
2. Coloca los archivos .pth y .index dentro de esa carpeta
3. Los archivos deben tener el mismo nombre que la carpeta

Ejemplo:
voices/
├── homero/
│   ├── homero.pth
│   └── homero.index
└── marge/
    ├── marge.pth
    └── marge.index

4. Abre Nopolo y haz clic en "Escanear Voces"
5. ¡Listo! Tu voz aparecerá en la lista

Para más información, consulta el README.md principal.
"""
            with open(voices_readme, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            print(f"{Colors.OKGREEN}   ✓ Creado: voices/README.txt{Colors.ENDC}")
    
    print(f"{Colors.OKGREEN}✅ Archivos adicionales copiados{Colors.ENDC}")
    return True

def build_executable(system_name, arch):
    """Ejecuta PyInstaller para generar el ejecutable"""
    print(f"\n📦 Generando ejecutable para {system_name} ({arch})...")
    print(f"{Colors.WARNING}⏳ Esto puede tardar varios minutos...{Colors.ENDC}\n")
    
    # Crear archivo de versión si es Windows
    version_file = create_version_file(system_name)
    
    # Comando base de PyInstaller
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        'nopolo.spec'
    ]
    
    try:
        # Ejecutar PyInstaller
        result = subprocess.run(cmd, check=True, capture_output=False)
        
        print(f"\n{Colors.OKGREEN}✅ Build completado exitosamente!{Colors.ENDC}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n{Colors.FAIL}❌ Error durante el build:{Colors.ENDC}")
        print(f"   {e}")
        return False
    finally:
        # Limpiar archivo de versión
        if version_file and os.path.exists(version_file):
            os.remove(version_file)

def show_output_info(system_name):
    """Muestra información sobre el ejecutable generado"""
    print("\n" + "=" * 70)
    print(f"{Colors.OKGREEN}{Colors.BOLD}🎉 ¡Build Completado!{Colors.ENDC}")
    print("=" * 70)
    
    dist_path = Path('dist/Nopolo')
    
    if system_name == "windows":
        exe_path = dist_path / 'Nopolo.exe'
        print(f"\n📁 Ejecutable generado en:")
        print(f"   {exe_path.absolute()}")
        
        print(f"\n📦 Estructura final:")
        print(f"   dist/Nopolo/")
        print(f"   ├── Nopolo.exe          ← Ejecutable principal")
        print(f"   ├── _internal/          ← Librerías Python")
        print(f"   ├── backgrounds/        ← Fondos (nivel raíz)")
        print(f"   ├── voices/             ← Modelos RVC (nivel raíz)")
        print(f"   ├── sounds/             ← Efectos de sonido (nivel raíz)")
        print(f"   ├── overlay/            ← Overlay files (nivel raíz)")
        print(f"   ├── config/             ← Configuración (nivel raíz)")
        print(f"   ├── .env                ← Variables de entorno (si existe)")
        print(f"   ├── .env.example        ← Ejemplo de configuración")
        print(f"   ├── README.md           ← Documentación")
        print(f"   └── LICENSE             ← Licencia")
        
        print(f"\n▶️  Para ejecutar:")
        print(f"   1. Navega a: dist\\Nopolo\\")
        print(f"   2. Doble click en: Nopolo.exe")
        print(f"\n📦 Para distribuir:")
        print(f"   Comprime la carpeta 'dist/Nopolo' completa en ZIP")
        
    elif system_name == "macos":
        app_path = dist_path / 'Nopolo.app'
        print(f"\n📁 Aplicación generada en:")
        print(f"   {app_path.absolute()}")
        print(f"\n▶️  Para ejecutar:")
        print(f"   1. Navega a: dist/Nopolo/")
        print(f"   2. Doble click en: Nopolo.app")
        print(f"\n📦 Para distribuir:")
        print(f"   Crea un .dmg con create-dmg o comprime en ZIP")
        
    else:  # Linux
        bin_path = dist_path / 'Nopolo'
        print(f"\n📁 Binario generado en:")
        print(f"   {bin_path.absolute()}")
        print(f"\n▶️  Para ejecutar:")
        print(f"   ./dist/Nopolo/Nopolo")
        print(f"\n📦 Para distribuir:")
        print(f"   Crea un AppImage o comprime en tar.gz")
    
    # Tamaño del build
    if dist_path.exists():
        total_size = sum(f.stat().st_size for f in dist_path.rglob('*') if f.is_file())
        size_mb = total_size / (1024 * 1024)
        print(f"\n💾 Tamaño total: {size_mb:.1f} MB")
    
    print("\n" + "=" * 70)

def main():
    # Parsear argumentos
    parser = argparse.ArgumentParser(description='Generar ejecutable de Nopolo con PyInstaller')
    parser.add_argument('-y', '--yes', action='store_true', 
                        help='Omitir confirmación y proceder automáticamente')
    args = parser.parse_args()
    
    print_banner()
    
    # Detectar sistema
    system_name, arch = detect_system()
    print(f"🖥️  Sistema operativo: {system_name} ({arch})")
    
    if system_name == "unknown":
        print(f"{Colors.FAIL}❌ Sistema operativo no soportado{Colors.ENDC}")
        sys.exit(1)
    
    # Verificar PyInstaller
    if not check_pyinstaller():
        print(f"\n{Colors.WARNING}Instalando PyInstaller...{Colors.ENDC}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
    
    # Confirmar
    print("\n" + "=" * 70)
    print(f"📋 Configuración del Build:")
    print(f"   Plataforma: {system_name}")
    print(f"   Arquitectura: {arch}")
    print(f"   Spec file: nopolo.spec")
    print("=" * 70)
    
    if not args.yes:
        confirm = input(f"\n¿Proceder con el build? [s/N]: ").strip().lower()
        if confirm not in ['s', 'si', 'yes', 'y']:
            print(f"{Colors.WARNING}❌ Build cancelado{Colors.ENDC}")
            sys.exit(0)
    else:
        print(f"\n{Colors.OKGREEN}✅ Procediendo automáticamente (--yes){Colors.ENDC}")
    
    # Limpiar builds anteriores
    clean_build_dirs()
    
    # Generar ejecutable
    if not build_executable(system_name, arch):
        print(f"\n{Colors.FAIL}❌ Build falló. Revisa los errores arriba.{Colors.ENDC}")
        sys.exit(1)
    
    # IMPORTANTE: Mover carpetas fuera de _internal/
    if not move_folders_outside_internal():
        print(f"{Colors.WARNING}⚠ Advertencia: No se pudieron mover todas las carpetas{Colors.ENDC}")
    
    # Copiar archivos adicionales
    if not copy_additional_files():
        print(f"{Colors.WARNING}⚠ Advertencia: No se pudieron copiar todos los archivos{Colors.ENDC}")
    
    # Mostrar información final
    show_output_info(system_name)
    
    sys.exit(0)

if __name__ == "__main__":
    main()

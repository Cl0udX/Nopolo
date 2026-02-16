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

# Importar versión
try:
    from version import __version__, __app_name__
except ImportError:
    __version__ = "1.0.0"
    __app_name__ = "Nopolo"

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
    print(f"{Colors.HEADER}{Colors.BOLD}  NOPOLO - Build Executable v{__version__}{Colors.ENDC}")
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
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"   Eliminado: {dir_name}/")
    
    print(f"{Colors.OKGREEN}✅ Limpieza completada{Colors.ENDC}")

def find_dist_folder():
    """
    Busca la carpeta dist generada por PyInstaller
    Puede ser dist/Nopolo o dist/Nopolo-1.0.0
    """
    possible_names = [
        f'{__app_name__}-{__version__}',
        __app_name__,
    ]
    
    for name in possible_names:
        path = Path('dist') / name
        if path.exists():
            return path
    
    return None

def move_folders_outside_internal():
    """
    CRÍTICO: Mueve carpetas de _internal/ al mismo nivel que el .exe
    PyInstaller siempre mete todo en _internal/, pero necesitamos estas carpetas fuera.
    """
    print(f"\n📁 Moviendo carpetas fuera de _internal...")
    
    # Buscar carpeta dist
    dist_path = find_dist_folder()
    
    if not dist_path:
        print(f"{Colors.FAIL}❌ No se encontró carpeta de distribución{Colors.ENDC}")
        print(f"   Buscando: dist/{__app_name__}-{__version__}/ o dist/{__app_name__}/")
        return False
    
    print(f"{Colors.OKCYAN}   Encontrado: {dist_path}{Colors.ENDC}")
    
    internal_path = dist_path / '_internal'
    
    if not internal_path.exists():
        print(f"{Colors.WARNING}⚠ No se encontró _internal/ (build antiguo?){Colors.ENDC}")
        return False
    
    # Carpetas que deben estar al mismo nivel que el .exe
    folders_to_move = ['backgrounds', 'voices', 'sounds', 'overlay', 'config']
    
    moved_count = 0
    for folder_name in folders_to_move:
        source = internal_path / folder_name
        destination = dist_path / folder_name
        
        if source.exists():
            # Si ya existe en destino, eliminarlo primero
            if destination.exists():
                shutil.rmtree(destination)
            
            # Mover carpeta fuera de _internal
            shutil.move(str(source), str(destination))
            print(f"{Colors.OKGREEN}   ✓ Movido: {folder_name}/ → {dist_path.name}/{folder_name}/{Colors.ENDC}")
            moved_count += 1
        else:
            print(f"{Colors.WARNING}   ⚠ No encontrado en _internal: {folder_name}/{Colors.ENDC}")
    
    # Mover archivo .env si existe
    env_source = internal_path / '.env'
    env_destination = dist_path / '.env'
    
    if env_source.exists():
        if env_destination.exists():
            env_destination.unlink()
        shutil.move(str(env_source), str(env_destination))
        print(f"{Colors.OKGREEN}   ✓ Movido: .env → {dist_path.name}/.env{Colors.ENDC}")
        moved_count += 1
    
    if moved_count > 0:
        print(f"{Colors.OKGREEN}✅ {moved_count} carpetas/archivos reorganizados correctamente{Colors.ENDC}")
        return True
    else:
        print(f"{Colors.WARNING}⚠ No se movió ninguna carpeta{Colors.ENDC}")
        return False

def copy_additional_files():
    """Copia archivos adicionales necesarios para la distribución"""
    print(f"\n📄 Copiando archivos adicionales...")
    
    # Buscar carpeta dist
    dist_path = find_dist_folder()
    
    if not dist_path:
        print(f"{Colors.FAIL}❌ No se encontró carpeta de distribución{Colors.ENDC}")
        return False
    
    print(f"{Colors.OKCYAN}   Trabajando en: {dist_path}{Colors.ENDC}")
    
    # Archivos a copiar desde el proyecto a dist/
    files_to_copy = {
        'README.md': 'README.md',
        'LICENSE': 'LICENSE',
        '.env.example': '.env.example',
    }
    
    copied_count = 0
    for src_file, dst_file in files_to_copy.items():
        src = Path(src_file)
        dst = dist_path / dst_file
        
        if src.exists():
            shutil.copy2(src, dst)
            print(f"{Colors.OKGREEN}   ✓ Copiado: {src_file}{Colors.ENDC}")
            copied_count += 1
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
            copied_count += 1
    
    if copied_count > 0:
        print(f"{Colors.OKGREEN}✅ {copied_count} archivos copiados{Colors.ENDC}")
        return True
    else:
        print(f"{Colors.WARNING}⚠ No se copió ningún archivo{Colors.ENDC}")
        return False

def build_executable(system_name, arch):
    """Ejecuta PyInstaller para generar el ejecutable"""
    print(f"\n📦 Generando ejecutable para {system_name} ({arch})...")
    print(f"{Colors.WARNING}⏳ Esto puede tardar varios minutos...{Colors.ENDC}\n")
    
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

def show_output_info(system_name):
    """Muestra información sobre el ejecutable generado"""
    print("\n" + "=" * 70)
    print(f"{Colors.OKGREEN}{Colors.BOLD}🎉 ¡Build Completado!{Colors.ENDC}")
    print("=" * 70)
    
    # Buscar carpeta dist
    dist_path = find_dist_folder()
    
    if not dist_path:
        print(f"{Colors.FAIL}❌ No se pudo verificar la salida{Colors.ENDC}")
        return
    
    if system_name == "windows":
        exe_name = f'{__app_name__}-{__version__}.exe'
        exe_path = dist_path / exe_name
        
        # Fallback
        if not exe_path.exists():
            exe_name = f'{__app_name__}.exe'
            exe_path = dist_path / exe_name
        
        print(f"\n📁 Ejecutable generado en:")
        print(f"   {exe_path.absolute()}")
        
        print(f"\n📦 Estructura final:")
        print(f"   {dist_path}/")
        print(f"   ├── {exe_name}          ← Ejecutable principal")
        print(f"   ├── _internal/          ← Librerías Python")
        print(f"   ├── backgrounds/        ← Fondos (nivel raíz) ✅")
        print(f"   ├── voices/             ← Modelos RVC (nivel raíz) ✅")
        print(f"   ├── sounds/             ← Efectos de sonido (nivel raíz) ✅")
        print(f"   ├── overlay/            ← Overlay files (nivel raíz) ✅")
        print(f"   ├── config/             ← Configuración (nivel raíz) ✅")
        print(f"   ├── .env                ← Variables de entorno (si existe)")
        print(f"   ├── .env.example        ← Ejemplo de configuración")
        print(f"   ├── README.md           ← Documentación")
        print(f"   └── LICENSE             ← Licencia")
        
        print(f"\n▶️  Para ejecutar:")
        print(f"   1. Navega a: dist\\{dist_path.name}\\")
        print(f"   2. Doble click en: {exe_name}")
        
        print(f"\n📦 Para distribuir:")
        print(f"   Comprime la carpeta 'dist/{dist_path.name}' completa en ZIP")
    
    # Tamaño del build
    if dist_path.exists():
        total_size = sum(f.stat().st_size for f in dist_path.rglob('*') if f.is_file())
        size_mb = total_size / (1024 * 1024)
        print(f"\n💾 Tamaño total: {size_mb:.1f} MB")
    
    print("\n" + "=" * 70)

def main():
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
    print(f"   Versión: {__version__}")
    print(f"   Carpeta salida: dist/{__app_name__}-{__version__}/")
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
    move_folders_outside_internal()
    
    # Copiar archivos adicionales
    copy_additional_files()
    
    # Mostrar información final
    show_output_info(system_name)
    
    print(f"\n{Colors.OKCYAN}💡 NOTA SOBRE GPU:{Colors.ENDC}")
    print(f"   Si no detecta tu GPU RTX 5070 Ti:")
    print(f"   1. Verifica que torch con CUDA esté instalado en el entorno")
    print(f"   2. Las DLLs de CUDA deben estar en _internal/")
    print(f"   3. Prueba ejecutar desde el código fuente primero")
    
    sys.exit(0)

if __name__ == "__main__":
    main()

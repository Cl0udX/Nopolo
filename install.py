#!/usr/bin/env python3
"""
Script de instalación automatizada para Nopolo
Instala dependencias en el orden correcto para evitar conflictos
"""

import sys
import subprocess
import platform
from pathlib import Path

class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    CYAN = '\033[96m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def run_command(cmd, description):
    """Ejecuta un comando y muestra el resultado"""
    print(f"\n{Colors.CYAN}→ {description}...{Colors.ENDC}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=False, shell=True)
        print_success(f"{description} completado")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"{description} falló")
        return False

def check_venv():
    """Verifica si estamos en un entorno virtual"""
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    if not in_venv:
        print_warning("No estás en un entorno virtual")
        print("Recomendación:")
        print("  python -m venv .venv")
        if platform.system() == "Windows":
            print("  .venv\\Scripts\\activate")
        else:
            print("  source .venv/bin/activate")
        
        response = input("\n¿Continuar de todos modos? [s/N]: ").strip().lower()
        if response not in ['s', 'si', 'yes', 'y']:
            sys.exit(0)
    else:
        print_success("Entorno virtual detectado")

def select_gpu():
    """Pregunta al usuario qué GPU tiene"""
    print("\n" + "="*70)
    print("Selecciona tu configuración de hardware:")
    print("="*70)
    print("\n1. GPU NVIDIA RTX 50xx (CUDA 12.8 - Experimental)")
    print("2. GPU NVIDIA RTX 40xx/30xx (CUDA 12.4 - Estable)")
    print("3. GPU NVIDIA RTX 20xx/GTX 16xx (CUDA 12.1)")
    print("4. Sin GPU (CPU only)")
    
    while True:
        choice = input("\nOpción [1-4]: ").strip()
        
        if choice == '1':
            return 'cuda128', '--pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128'
        elif choice == '2':
            return 'cuda124', 'torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124'
        elif choice == '3':
            return 'cuda121', 'torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121'
        elif choice == '4':
            return 'cpu', 'torch torchvision torchaudio'
        else:
            print_error("Opción inválida. Intenta de nuevo.")

def main():
    print_header("NOPOLO - Instalación de Dependencias")
    
    # 1. Verificar entorno virtual
    check_venv()
    
    # 2. Seleccionar GPU
    gpu_type, torch_cmd = select_gpu()
    
    print(f"\n{Colors.CYAN}Configuración seleccionada: {gpu_type.upper()}{Colors.ENDC}")
    
    # Confirmar
    response = input("\n¿Proceder con la instalación? [s/N]: ").strip().lower()
    if response not in ['s', 'si', 'yes', 'y']:
        print_warning("Instalación cancelada")
        sys.exit(0)
    
    # 3. Actualizar pip
    print_header("Paso 1/5: Actualizando pip")
    if not run_command(f"{sys.executable} -m pip install --upgrade pip", "Actualizar pip"):
        sys.exit(1)
    
    # 4. Instalar PyTorch PRIMERO
    print_header("Paso 2/5: Instalando PyTorch")
    print(f"{Colors.WARNING}⚠ IMPORTANTE: Instalando PyTorch PRIMERO para evitar conflictos{Colors.ENDC}")
    
    if not run_command(f"pip install {torch_cmd} --force-reinstall --no-cache-dir", "Instalar PyTorch"):
        print_error("Error instalando PyTorch")
        sys.exit(1)
    
    # 5. Verificar PyTorch
    print("\n" + "="*70)
    print("Verificando instalación de PyTorch...")
    print("="*70)
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        cuda_version = torch.version.cuda if cuda_available else "N/A"
        torch_version = torch.__version__
        
        print(f"\n{Colors.CYAN}PyTorch instalado:{Colors.ENDC}")
        print(f"  Versión: {torch_version}")
        print(f"  CUDA disponible: {cuda_available}")
        print(f"  Versión CUDA: {cuda_version}")
        
        if gpu_type.startswith('cuda') and not cuda_available:
            print_error("GPU no detectada. Verifica tus drivers NVIDIA.")
            response = input("\n¿Continuar de todos modos? [s/N]: ").strip().lower()
            if response not in ['s', 'si', 'yes', 'y']:
                sys.exit(1)
    except ImportError:
        print_error("No se pudo importar PyTorch")
        sys.exit(1)
    
    # 6. Instalar FAISS según GPU
    print_header("Paso 3/5: Instalando FAISS")
    if gpu_type.startswith('cuda'):
        faiss_pkg = 'faiss-gpu'
    else:
        faiss_pkg = 'faiss-cpu'
    
    if not run_command(f"pip install {faiss_pkg}", f"Instalar {faiss_pkg}"):
        print_warning(f"Error instalando {faiss_pkg}, continuando...")
    
    # 7. Instalar dependencias base
    print_header("Paso 4/5: Instalando dependencias base")
    
    if not Path('requirements-base.txt').exists():
        print_error("No se encontró requirements-base.txt")
        sys.exit(1)
    
    if not run_command("pip install -r requirements-base.txt", "Instalar dependencias base"):
        print_error("Error instalando dependencias base")
        sys.exit(1)
    
    # 8. Instalar Fairseq
    print_header("Paso 5/5: Instalando Fairseq")
    print(f"{Colors.WARNING}⚠ Esto puede tardar varios minutos...{Colors.ENDC}")
    
    if platform.system() == "Windows":
        print(f"{Colors.WARNING}⚠ Windows: Si falla, ejecuta PowerShell como Administrador{Colors.ENDC}")
    
    if not run_command("pip install git+https://github.com/Tps-F/fairseq.git@main", "Instalar Fairseq"):
        print_error("Error instalando Fairseq")
        print("\nIntenta manualmente:")
        print("  git clone https://github.com/Tps-F/fairseq.git")
        print("  cd fairseq")
        print("  pip install -e .")
        sys.exit(1)
    
    # 9. Resumen final
    print("\n" + "="*70)
    print_success("INSTALACIÓN COMPLETADA")
    print("="*70)
    
    print(f"\n{Colors.CYAN}Resumen:{Colors.ENDC}")
    print(f"  • PyTorch: {torch_version} ({'GPU' if cuda_available else 'CPU'})")
    print(f"  • FAISS: {faiss_pkg}")
    print(f"  • Dependencias base: Instaladas")
    print(f"  • Fairseq: Instalado")
    
    print(f"\n{Colors.CYAN}Siguiente paso:{Colors.ENDC}")
    print("  python main.py")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_warning("\n\nInstalación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\nError inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

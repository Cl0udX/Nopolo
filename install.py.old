#!/usr/bin/env python3
"""
Script de instalación interactivo para Nopolo
Detecta el sistema operativo y guía la instalación de dependencias
"""
import sys
import platform
import subprocess
import os

def print_banner():
    print("=" * 70)
    print("  NOPOLO - Instalador Interactivo")
    print("  Voice Studio TTS con conversión RVC")
    print("=" * 70)
    print()

def detect_system():
    """Detecta el sistema operativo"""
    system = platform.system()
    if system == "Darwin":
        return "macOS"
    elif system == "Windows":
        return "Windows"
    elif system == "Linux":
        return "Linux"
    else:
        return "Unknown"

def check_python_version():
    """Verifica que Python sea 3.10.x o 3.11.x"""
    version = sys.version_info
    if version.major == 3 and (version.minor == 10 or version.minor == 11):
        print(f"Python {version.major}.{version.minor}.{version.micro} detectado")
        return True
    else:
        print(f"Python {version.major}.{version.minor}.{version.micro} detectado")
        print("Nopolo requiere Python 3.10.x o 3.11.x")
        print("Descarga: https://www.python.org/downloads/")
        return False

def install_base_requirements():
    """Instala las dependencias base"""
    print("\nInstalando dependencias base...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements-base.txt"])
        print("Dependencias base instaladas correctamente")
        return True
    except subprocess.CalledProcessError:
        print("Error al instalar dependencias base")
        return False

def install_torch(config):
    """Instala PyTorch según la configuración"""
    print(f"\nInstalando PyTorch para {config}...")
    
    commands = {
        "cuda124": [sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio", 
                    "--index-url", "https://download.pytorch.org/whl/cu124"],
        "cuda128": [sys.executable, "-m", "pip", "install", "--pre", "torch", "torchvision", "torchaudio",
                    "--index-url", "https://download.pytorch.org/whl/nightly/cu128"],
        "cpu": [sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio"],
        "mac": [sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio"]
    }
    
    try:
        subprocess.check_call(commands[config])
        print(f"PyTorch instalado correctamente ({config})")
        return True
    except subprocess.CalledProcessError:
        print(f"Error al instalar PyTorch ({config})")
        return False

def install_fairseq():
    """Instala Fairseq"""
    print("\nInstalando Fairseq (puede tardar varios minutos)...")
    system = detect_system()
    
    if system == "Windows":
        print("En Windows, esto puede requerir permisos de administrador")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", 
                             "git+https://github.com/Tps-F/fairseq.git@main"])
        print("Fairseq instalado correctamente")
        return True
    except subprocess.CalledProcessError:
        print("Error al instalar Fairseq")
        print("   Intenta ejecutar como administrador o instalar manualmente:")
        print("   git clone https://github.com/Tps-F/fairseq.git")
        print("   cd fairseq && pip install -e .")
        return False

def main():
    print_banner()
    
    # Verificar Python
    if not check_python_version():
        sys.exit(1)
    
    # Detectar sistema
    system = detect_system()
    print(f"Sistema operativo: {system}")
    
    # Seleccionar configuración de hardware
    print("\n" + "=" * 70)
    print("Selecciona tu configuración de hardware:")
    print("=" * 70)
    
    if system == "macOS":
        print("1. macOS con Apple Silicon (M1/M2/M3)")
        print("2. macOS con Intel")
        choice = input("\nOpción [1-2]: ").strip()
        
        if choice in ["1", "2"]:
            torch_config = "mac"
        else:
            print("Opción inválida")
            sys.exit(1)
    
    else:  # Windows o Linux
        print("1. CPU solamente (sin GPU NVIDIA)")
        print("2. GPU NVIDIA RTX 30xx/40xx (CUDA 12.4)")
        print("3. GPU NVIDIA RTX 50xx Blackwell (CUDA 12.8 - EXPERIMENTAL)")
        choice = input("\nOpción [1-3]: ").strip()
        
        config_map = {
            "1": "cpu",
            "2": "cuda124",
            "3": "cuda128"
        }
        
        if choice in config_map:
            torch_config = config_map[choice]
        else:
            print("Opción inválida")
            sys.exit(1)
    
    # Confirmar instalación
    print("\n" + "=" * 70)
    print(f"Configuración seleccionada: {torch_config}")
    print("=" * 70)
    confirm = input("\n¿Proceder con la instalación? [s/N]: ").strip().lower()
    
    if confirm not in ["s", "si", "yes", "y"]:
        print("Instalación cancelada")
        sys.exit(0)
    
    # Proceso de instalación
    print("\n" + "=" * 70)
    print("Iniciando instalación...")
    print("=" * 70)
    
    # 1. Instalar dependencias base
    if not install_base_requirements():
        sys.exit(1)
    
    # 2. Instalar PyTorch
    if not install_torch(torch_config):
        sys.exit(1)
    
    # 3. Instalar Fairseq
    if not install_fairseq():
        print("Fairseq falló, pero puedes intentar instalarlo manualmente después")
    
    # Instrucciones finales
    print("\n" + "=" * 70)
    print("¡Instalación completada!")
    print("=" * 70)
    
    if system == "macOS":
        print("\nSiguiente paso:")
        print("   Ejecuta Nopolo con: ./run_nopolo_full.sh")
        print("   (O usa run_nopolo_gui.sh para solo interfaz)")
    else:
        print("\nSiguiente paso:")
        print("   Ejecuta Nopolo con: python main.py --with-api")
        print("   (O usa python main.py para solo interfaz)")
    
    print("\nDocumentación completa en README.md")
    print("Soporte: https://github.com/tu-usuario/nopolo/issues")
    print()

if __name__ == "__main__":
    main()

# 📦 Guía de Instalación - Nopolo v1.0.0

Esta guía cubre la instalación de Nopolo en diferentes sistemas operativos y configuraciones de hardware.

## 📋 Requisitos Previos

### Todos los Sistemas
- **Python 3.10.11 o 3.11.x** (recomendado 3.10.11)
- **FFmpeg** instalado en el sistema
- Conexión a internet (para edge-tts y descarga de dependencias)

### Windows
- **Chocolatey** (gestor de paquetes)
- **Visual C++ Build Tools** (para compilar algunas dependencias)

### macOS
- **Homebrew** (gestor de paquetes)
- **Xcode Command Line Tools** (`xcode-select --install`)

### Linux
- **apt/yum/pacman** (según distribución)
- **build-essential** y dependencias de desarrollo

---

## 🚀 Instalación Rápida (Recomendado)

### Método Automático con Script Interactivo

```bash
# 1. Clonar repositorio
git clone https://github.com/tu-usuario/nopolo.git
cd nopolo

# 2. Crear entorno virtual
python3.10 -m venv .venv

# Windows:
.venv\Scripts\activate

# macOS/Linux:
source .venv/bin/activate

# 3. Ejecutar instalador interactivo
python install.py
```

El script detectará tu sistema operativo y te guiará en la selección de la configuración apropiada.

---

## 🔧 Instalación Manual

### 1. Instalar Dependencias del Sistema

#### Windows (PowerShell como Administrador)

```powershell
# Instalar Chocolatey (si no está instalado)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Instalar FFmpeg
choco install ffmpeg

# Instalar Visual C++ Build Tools
choco install visualstudio2022buildtools --package-parameters "--add Microsoft.VisualStudio.Workload.VCTools"
```

#### macOS

```bash
# Instalar Homebrew (si no está instalado)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Instalar FFmpeg
brew install ffmpeg

# Instalar Command Line Tools
xcode-select --install
```

#### Linux (Ubuntu/Debian)

```bash
# Actualizar repositorios
sudo apt update

# Instalar FFmpeg y dependencias de desarrollo
sudo apt install ffmpeg build-essential python3-dev portaudio19-dev

# Instalar eSpeak NG (opcional, para Coqui TTS)
sudo apt install espeak-ng
```

### 2. Crear Entorno Virtual

```bash
# Navegar al directorio del proyecto
cd nopolo

# Crear entorno virtual con Python 3.10
python3.10 -m venv .venv

# Activar entorno virtual
# Windows:
.venv\Scripts\activate

# macOS/Linux:
source .venv/bin/activate
```

### 3. Instalar Dependencias Python

Selecciona la configuración que corresponda a tu hardware:

#### Opción A: Windows/Linux con GPU NVIDIA RTX 30xx/40xx (CUDA 12.4)

```bash
# Instalar dependencias base
pip install -r requirements-base.txt

# Instalar PyTorch con CUDA 12.4
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Instalar Fairseq (como administrador en Windows)
pip install git+https://github.com/Tps-F/fairseq.git@main
```

#### Opción B: Windows/Linux con GPU NVIDIA RTX 50xx (CUDA 12.8 - EXPERIMENTAL)

```bash
# Instalar dependencias base
pip install -r requirements-base.txt

# Instalar PyTorch nightly con CUDA 12.8
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128

# Instalar Fairseq
pip install git+https://github.com/Tps-F/fairseq.git@main
```

**⚠️ Nota:** CUDA 12.8 es experimental y puede tener problemas de estabilidad. Si experimentas errores, usa CUDA 12.4.

#### Opción C: Windows/Linux con CPU (sin GPU)

```bash
# Instalar dependencias base
pip install -r requirements-base.txt

# Instalar PyTorch CPU
pip install torch torchvision torchaudio

# Instalar Fairseq
pip install git+https://github.com/Tps-F/fairseq.git@main
```

#### Opción D: macOS (Apple Silicon M1/M2/M3)

```bash
# Instalar dependencias base
pip install -r requirements-base.txt

# Instalar PyTorch para Mac
pip install torch torchvision torchaudio

# Instalar Fairseq
pip install git+https://github.com/Tps-F/fairseq.git@main
```

---

## ▶️ Ejecución

### Windows/Linux

```bash
# Solo interfaz gráfica
python main.py

# Solo servidor API REST
python main.py --no-gui

# Interfaz + API simultáneamente (recomendado)
python main.py --with-api
```

### macOS

```bash
# Usar scripts que establecen variables de entorno necesarias

# Solo interfaz gráfica
./run_nopolo_gui.sh

# Solo servidor API
./run_nopolo_api.sh

# Interfaz + API (recomendado)
./run_nopolo_full.sh
```

**Importante para Mac:** Los scripts `.sh` establecen `PYTORCH_ENABLE_MPS_FALLBACK=1` que es necesario para evitar errores con Apple Silicon.

---

## ✅ Verificar Instalación

### 1. Verificar PyTorch

```python
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA disponible: {torch.cuda.is_available()}')"
```

**Salida esperada (GPU NVIDIA):**
```
PyTorch: 2.1.0+cu124
CUDA disponible: True
```

**Salida esperada (CPU/Mac):**
```
PyTorch: 2.1.0
CUDA disponible: False
```

### 2. Verificar Fairseq

```python
python -c "import fairseq; print('Fairseq OK')"
```

### 3. Ejecutar Test de Audio

```bash
python -c "import sounddevice as sd; import numpy as np; sd.play(np.random.randn(44100), 44100); sd.wait()"
```

Deberías escuchar un segundo de ruido blanco.

---

## 🐛 Solución de Problemas

### Error: "No module named 'fairseq'"

**Solución:** Fairseq requiere instalación con permisos elevados:

```bash
# Windows (PowerShell como Administrador)
pip install git+https://github.com/Tps-F/fairseq.git@main

# Linux/macOS
sudo pip install git+https://github.com/Tps-F/fairseq.git@main

# Alternativa (instalación local)
git clone https://github.com/Tps-F/fairseq.git
cd fairseq
pip install -e .
```

### Error: "CUDA out of memory" (GPU)

**Solución:** Reduce el batch size o usa CPU:
1. Cierra otras aplicaciones que usen GPU
2. En `config/.env`, ajusta parámetros de memoria
3. Considera cambiar a modo CPU si persiste

### Error: "MPS backend not available" (macOS)

**Solución:** Usa los scripts `run_nopolo_*.sh` que configuran el entorno correctamente.

Si ejecutas directamente con Python:
```bash
export PYTORCH_ENABLE_MPS_FALLBACK=1
python main.py --with-api
```

### Error: "espeak-ng not found"

**Solución (Windows):**
1. Instala eSpeak NG: `choco install espeak-ng`
2. Agrega a PATH: `C:\Program Files\eSpeak NG`
3. Reinicia la terminal

**Solución (Linux):**
```bash
sudo apt install espeak-ng
```

**Solución (macOS):**
```bash
brew install espeak-ng
```

### PyTorch no detecta GPU NVIDIA

**Verificar instalación:**
```bash
nvidia-smi  # Debe mostrar tu GPU
nvcc --version  # Debe mostrar CUDA toolkit
```

**Reinstalar PyTorch con CUDA:**
```bash
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

---

## 📚 Recursos Adicionales

- **Documentación completa:** [README.md](README.md)
- **Configuración de voces:** `config/voices.json`
- **Configuración de efectos:** `config/sounds.json`
- **API Documentation:** Ejecuta la app y ve a http://localhost:8000/docs

---

## 🆘 Soporte

Si encuentras problemas:

1. Revisa la sección "Solución de Problemas" arriba
2. Consulta [Issues en GitHub](https://github.com/tu-usuario/nopolo/issues)
3. Únete a [Discord/Comunidad]
4. Apoya el proyecto en [Ko-fi](https://ko-fi.com/postincloud)

---

## 📝 Notas de Versión

### v1.0.0 - Primera Release Estable

**Características:**
- ✅ Soporte multiplataforma (Windows, Linux, macOS)
- ✅ Detección automática de GPU/CPU
- ✅ API REST con documentación Swagger
- ✅ Multi-provider TTS (Edge TTS + Google Cloud)
- ✅ Sistema de sintaxis Mopolo para mensajes complejos
- ✅ Filtros de audio y efectos de sonido
- ✅ Splash screen animado
- ✅ Instalador interactivo

**Configuraciones soportadas:**
- Windows/Linux CPU
- Windows/Linux GPU NVIDIA CUDA 12.4 (RTX 30xx/40xx)
- Windows/Linux GPU NVIDIA CUDA 12.8 (RTX 50xx - experimental)
- macOS Apple Silicon (M1/M2/M3)
- macOS Intel

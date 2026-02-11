# Nopolo

El proyecto actualmente está hecho en Windows, aunque se puede adaptar a otros sistemas operativos. Este README se enfoca en la instalación en Windows.

Si solo quieres **usar el proyecto**, ve a los releases y descarga el ejecutable. Si quieres clonar el proyecto y ejecutarlo desde el código fuente, sigue las instrucciones a continuación.


Nopolo es una herramienta open source, local/dedicada, pensada para creadores de contenido que quieren dar vida a sus streams, videos o bots mediante síntesis de voz avanzada y conversión de personajes en tiempo real.

El proyecto nace como una alternativa libre a herramientas de pago como Mopolo TTS, ofreciendo un sistema modular, extensible y ejecutado completamente en el equipo del usuario, sin depender de servicios cerrados ni suscripciones.

---

🚀 ¿Qué hace StreamTTS?

StreamTTS permite transformar texto en audio usando voces naturales y luego convertir ese audio a voces de personajes mediante modelos de conversión de voz.

Actualmente el flujo es:
```
Texto
 → TTS (voz natural)
 → Conversión de voz (RVC)
 → Reproducción de audio
```

El objetivo es que cada mensaje pueda reproducirse con múltiples voces, aplicar efectos de sonido, y reaccionar a eventos (por ejemplo, mensajes de chat o alertas de stream).

---

✨ Características

    🔊 Text-to-Speech con voces naturales

    🎭 Conversión de voz a personajes (ej. Homero Simpson)

    🧠 Uso de modelos entrenados (.pth / .index)

    💻 Ejecución completamente local (CPU / GPU)

    ⚡ Aceleración por GPU (CUDA)

    🧩 Arquitectura modular (TTS, RVC, cola de audio)

    🖥️ Interfaz gráfica simple (Qt / PySide6)

    🔓 Open source y extensible

---

🎯 Enfoque del proyecto

StreamTTS está diseñado como una herramienta para creadores de contenido, pero también como una base sólida para:

Bots de streaming

Integración con herramientas como Streamer.bot

Automatización de eventos

Proyectos experimentales de voz

El proyecto se mantiene open source porque actualmente la mayoría de herramientas similares son de pago o limitan fuertemente el uso gratuito.

---

🛠️ Tecnologías usadas

Python 3.10

PySide6 (interfaz gráfica)

edge-tts (síntesis de voz)

RVC (Retrieval-based Voice Conversion)

PyTorch + CUDA

sounddevice / pydub

---

📂 Estructura del proyecto
```
StreamTTS/
├─ main.py
├─ core/
│  ├─ tts_engine.py
│  ├─ rvc_engine.py
│  ├─ audio_queue.py
│  └─ audio_player.py
├─ gui/
│  └─ main_window.py
├─ rvc/                  # RVC clonado
├─ voices/               # Modelos de voz (.pth / .index)
├─ assets/
└─ README.md
```
---
🔮 Próximos pasos

Soporte para múltiples voces por mensaje

Sistema de efectos de sonido

Integración directa con Streamer.bot

Configuración avanzada desde la interfaz

Optimización de latencia

Soporte para Linux

---

⚠️ Estado del proyecto

Este proyecto se encuentra en desarrollo activo.
Algunas partes pueden cambiar y no todo está optimizado aún.

Si quieres contribuir, probar o proponer ideas, eres bienvenido.


---

## Requisitos del Sistema

- **Python 3.10.11** (recomendado)
- **Chocolatey** (para instalar dependencias del sistema WIN)
- **Homebrew** (para instalar dependencias del sistema macOS)
- Conexión a internet (edge-tts usa servicios en línea de Microsoft)

---

## Instalación

### 1. Instalar Chocolatey o Homebrew

Ejecuta PowerShell como **administrador** y sigue las instrucciones en:

https://chocolatey.org/install

O si estás en macOS, instala Homebrew siguiendo las instrucciones en:

https://brew.sh/


### 2. Instalar FFmpeg

En la misma consola de PowerShell (como administrador):

```powershell
# Windows
choco install ffmpeg
# O en macOS:
brew install ffmpeg
```

### 3. Crear Entorno Virtual

En el directorio del proyecto:

```bash
python3.10 -m venv .venv
.venv\Scripts\activate
```

### 4. Instalar Dependencias de Python

Con el entorno virtual activado:

```bash
pip install PySide6 sounddevice numpy scipy pydub edge-tts soundfile librosa
pip install  praat-parselmouth pyworld torchcrepe faiss-cpu python-dotenv av
-- Nvidia
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 (para GPU NVIDIA con CUDA 12.4)
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128 (para GPU NVIDIA con CUDA 12.8 esto es experimental y puede ser inestable)
-- Mac o sin GPU
pip install torch torchvision torchaudio

pip install git+https://github.com/Tps-F/fairseq.git@main (Como administrador)
```

---

## Configuración Actual

El proyecto usa **edge-tts** (Microsoft Azure TTS):
- ✅ Sin necesidad de GPU
- ✅ Calidad de voz excelente
- ✅ Rápido y eficiente
- ✅ Soporte para múltiples voces en español
- ❌ Requiere conexión a internet

Voz por defecto: `es-MX-JorgeNeural` (español mexicano, masculina)

Otras voces disponibles:
- `es-ES-AlvaroNeural` - Español España (masculina)
- `es-AR-TomasNeural` - Español Argentina (masculina)
- `es-MX-DaliaNeural` - Español México (femenina)

---

## Alternativa: Coqui TTS (Avanzado)

Si prefieres usar **Coqui TTS** con clonación de voz (offline, más lento):

### Requisitos Adicionales:

1. **eSpeak-NG:**
   ```powershell
   choco install espeak-ng
   o
   brew install espeak-ng
   ```

2. **Microsoft Visual C++ Build Tools:**
   - Descarga de: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - Selecciona "Desktop development with C++"
   - Instala (~6-7 GB)

3. **Dependencias adicionales:**
   ```bash
   pip install TTS
   
   # Solo CPU:
   pip install torch==2.1.0 torchaudio==2.1.0
   
   # GPU NVIDIA (CUDA 12.1):
   pip install torch==2.1.0+cu121 torchaudio==2.1.0+cu121 --index-url https://download.pytorch.org/whl/cu121
   
   # ⚠️ GPU Blackwell (RTX 50xx series): Actualmente incompatible con Coqui TTS
   # Requiere Python 3.12+ pero Coqui TTS solo soporta ≤3.11
   ```

4. **Nota sobre eSpeak-NG:**
   Si la consola no encuentra `espeak-ng`, agrega manualmente a PATH:
   - Ruta típica: `C:\Program Files\eSpeak NG`
   - Reinicia la consola/sistema después de agregar al PATH

### Modelos Recomendados:
- **Pesado (mejor calidad):** `tts_models/multilingual/multi-dataset/xtts_v2`
- **Ligero (más rápido):** `tts_models/es/mai/tacotron2-DDC`

---

## Ejecución

```bash
python main.py
```
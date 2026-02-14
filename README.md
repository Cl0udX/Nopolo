# Nopolo

![Logo](assets/logo.png "Logo del proyecto Nopolo")

**Nopolo** es una herramienta open source de síntesis de voz (TTS) con conversión de personajes mediante RVC, diseñada para creadores de contenido que quieren dar vida a sus streams, videos o bots.

El proyecto funciona **completamente local** en tu equipo, sin depender de servicios cerrados ni suscripciones. Es una alternativa libre a herramientas de pago como Mopolo TTS.

---

## 🌐 Compatibilidad Multiplataforma

| Sistema | Estado | Device | Método F0 | Notas |
|---------|--------|--------|-----------|-------|
| **Windows + NVIDIA** | ✅ Completo | CUDA | RMVPE | Máximo rendimiento |
| **Linux + NVIDIA** | ✅ Completo | CUDA | RMVPE | Máximo rendimiento |
| **macOS (M1/M2/M3)** | ✅ Optimizado | CPU | Parselmouth | Estable, ligeramente más lento |
| **Windows/Linux sin GPU** | ✅ Funcional | CPU | RMVPE | Más lento pero funcional |

> **Nota para usuarios de Mac:** Nopolo detecta automáticamente macOS y ajusta el procesamiento para evitar problemas con MPS. Usa el script `./run_nopolo_gui.sh` para mejor rendimiento.

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
## 🔮 Próximos pasos

- [x] Soporte multiplataforma (Windows, Linux, macOS)
- [x] API REST con documentación interactiva
- [x] Multi-provider TTS (Edge TTS + Google Cloud TTS)
- [x] Soporte para múltiples voces por mensaje (sintaxis Mopolo)
- [x] Sistema de efectos de sonido integrado
- [x] Filtros de audio (reverb, phone, pitch, robot, etc.)
- [x] Filtros de fondo (ambiente/contexto durante la voz)
- [ ] Endpoint API `/synthesize/advanced` para mensajes complejos
- [ ] Integración directa con Streamer.bot
- [ ] Configuración avanzada desde la interfaz
- [ ] Optimización de latencia

---

## 🎭 Mensajes Multi-Voz (Formato Mopolo)

Nopolo soporta mensajes complejos con múltiples voces, efectos de sonido y filtros de audio usando la sintaxis de Mopolo TTS.

### Sintaxis Básica

**Voces:**
```
nombre: texto a decir
id: texto a decir
```

**Sonidos:**
```
(nombre_sonido)
(id_sonido)
```

**Filtros de Audio:**
```
nombre.filtro: texto con filtro
nombre.filtro1.filtro2: texto con múltiples filtros
```

### Filtros Disponibles

| ID  | Nombre      | Descripción                    | Ejemplo                |
|-----|-------------|--------------------------------|------------------------|
| r   | Reverb      | Eco/reverberación              | `dross.r: con eco`     |
| p   | Phone       | Llamada telefónica             | `enrique.p: alló`      |
| pu  | Pitch Up    | Voz más aguda (+5 semitonos)   | `homero.pu: chiflado`  |
| pd  | Pitch Down  | Voz más grave (-5 semitonos)   | `dross.pd: profundo`   |
| m   | Muffled     | Voz apagada/de lejos           | `5.m: desde afuera`    |
| a   | Robot       | Voz robótica/android           | `robot.a: beep boop`   |
| l   | Distortion  | Voz saturada/distorsionada     | `metal.l: gritando`    |

### Filtros de Fondo

Mezclan un audio de ambiente/contexto **durante** toda la frase:

| ID  | Nombre        | Descripción                    | Ejemplo                        |
|-----|---------------|--------------------------------|--------------------------------|
| fa  | Calle         | Tráfico y ambiente urbano      | `dross.fa: en la calle`        |
| fb  | Lluvia        | Sonido de lluvia               | `narrador.fb: bajo la lluvia`  |
| fc  | Multitud      | Restaurante/lugar público      | `streamer.fc: en el evento`    |
| fd  | Naturaleza    | Viento, playa, pájaros         | `5.fd: en la playa`            |
| fe  | Personalizado | Definido por el usuario        | `voz.fe: con fondo custom`     |

**Nota:** Los archivos de fondo se configuran en `config/backgrounds.json` y se colocan en la carpeta `backgrounds/`.

### Ejemplos Completos

**Conversación simple:**
```
dross: hola amigos (disparo) homero: doh!
```

**Con filtros:**
```
enrique.p: alló, te puedo escuchar? dross.r: si, con eco
```

**Con fondos:**
```
reportero.fa: estamos en vivo desde la calle principal (sirena) testigo.m: escuche todo desde adentro
```

**Combinando todo:**
```
dross: bienvenidos al video (aplauso) narrador.fb.r: era una noche lluviosa homero.pu: doh! (risa)
```

### Configuración de Efectos de Sonido y Sonidos de fondo

Para configurar ambos, es necesario editar los archivos `config/sounds.json` y `config/backgrounds.json`.
O la mejor opción es usar la interfaz gráfica de configuración.

Puede usar el siguiente enlace para descargar contenido para Nopolo (Audios y Fondos):
[Descargar contenido para Nopolo (Google Drive)](https://drive.google.com/drive/folders/1rBW0eycWrFqZbRiXQYjJFG-CNH-ej5MU?usp=sharing)

### Scripts de Prueba

**Generar fondos de prueba:**
```bash
python test_background_filters.py
```
Este script genera:
- Archivos de audio de fondo sintéticos (calle, lluvia, multitud, naturaleza)
- Ejemplos de voz mezclada con cada fondo
- Todos los archivos en `test_backgrounds/` y `backgrounds/`

**Ver ejemplos de uso:**
```bash
python example_backgrounds.py
```
Muestra la sintaxis completa y ejemplos de mensajes multi-voz con fondos.

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

pip install fastapi uvicorn pydantic python-dotenv aiohttp

pip install google-cloud-texttospeech
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

## 🚀 Ejecución

### Método 1: Scripts de Lanzamiento (Recomendado para Mac)

```bash
# Solo interfaz gráfica (GUI)
./run_nopolo_gui.sh

# Solo servidor API REST (sin GUI)
./run_nopolo_api.sh

# GUI + API Server simultáneamente
./run_nopolo_full.sh
```

> **Importante:** Los scripts `.sh` establecen variables de entorno necesarias para Mac. En Windows/Linux puedes usarlos o ejecutar directamente con Python.

### Método 2: Ejecución Directa con Python

```bash
# Activar entorno virtual primero
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# Modos de ejecución:
python main.py              # Solo GUI
python main.py --no-gui     # Solo API Server
python main.py --with-api   # GUI + API Server
```

### Acceso a la API REST

Cuando ejecutas con API habilitada:
- **Documentación interactiva:** http://localhost:8000/docs
- **API alternativa:** http://localhost:8000/redoc
- **Endpoint ejemplo:** `POST http://localhost:8000/synthesize`

---

---

## Ejecución

```bash
python main.py
```
# Nopolo

El proyecto actualmente está hecho en Windows, aunque se puede adaptar a otros sistemas operativos. Este README se enfoca en la instalación en Windows.

Si solo quieres **usar el proyecto**, ve a los releases y descarga el ejecutable. Si quieres clonar el proyecto y ejecutarlo desde el código fuente, sigue las instrucciones a continuación.

---

## Requisitos del Sistema

- **Python 3.10.11** (recomendado)
- **Chocolatey** (para instalar dependencias del sistema)
- Conexión a internet (edge-tts usa servicios en línea de Microsoft)

---

## Instalación

### 1. Instalar Chocolatey

Ejecuta PowerShell como **administrador** y sigue las instrucciones en:

https://chocolatey.org/install

### 2. Instalar FFmpeg

En la misma consola de PowerShell (como administrador):

```powershell
choco install ffmpeg
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
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 (para GPU NVIDIA con CUDA 12.4)
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128 (para GPU NVIDIA con CUDA 12.8 esto es experimental y puede ser inestable)
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
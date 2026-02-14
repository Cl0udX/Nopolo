# 🎯 Guía Rápida - Filtros de Fondo

## ✅ ¿Qué se implementó?

Sistema completo de **filtros de fondo** que permite mezclar audio de ambiente durante la reproducción de voces.

**Sintaxis:**
```
voz.fa: texto con fondo de calle
voz.fb: texto con fondo de lluvia
voz.fc: texto con fondo de multitud
voz.fd: texto con fondo de naturaleza
voz.fe: texto con fondo personalizado
```

**Ejemplo real:**
```
reportero.fa: estamos en vivo desde la calle (sirena) testigo.m.fc: yo estaba en el café
```
→ Reportero con fondo de calle + sirena + testigo amortiguado con fondo de café

---

## 🚀 Cómo Empezar

### 1. Generar fondos de prueba

```bash
python test_background_filters.py
```

Esto crea:
- ✅ `backgrounds/calle.wav` (tráfico sintético)
- ✅ `backgrounds/lluvia.wav` (gotas)
- ✅ `backgrounds/multitud.wav` (conversaciones)
- ✅ `backgrounds/naturaleza.wav` (pájaros)
- ✅ `test_backgrounds/voice_with_*.wav` (ejemplos de mezcla)

### 2. Ver ejemplos de sintaxis

```bash
python example_backgrounds.py
```

Muestra la guía completa de uso con 6 ejemplos prácticos.

### 3. Usar en tu código

```python
from core.advanced_processor import AdvancedAudioProcessor
from core.voice_manager import VoiceManager
from core.tts_engine import TTSEngine
from core.rvc_engine import RVCEngine

# Inicializar
voice_manager = VoiceManager()
tts_engine = TTSEngine()
rvc_engine = RVCEngine()

processor = AdvancedAudioProcessor(
    voice_manager=voice_manager,
    tts_engine=tts_engine,
    rvc_engine=rvc_engine
)

# Procesar mensaje con fondo
audio, sr = processor.process_message("dross.fa: hola desde la calle")

# Guardar
import soundfile as sf
sf.write("output.wav", audio, sr)
```

---

## 📋 Filtros Disponibles

### Filtros de Audio Normales
| ID  | Nombre      | Ejemplo                |
|-----|-------------|------------------------|
| r   | Reverb      | `dross.r: con eco`     |
| p   | Phone       | `enrique.p: llamada`   |
| pu  | Pitch Up    | `homero.pu: agudo`     |
| pd  | Pitch Down  | `dross.pd: grave`      |
| m   | Muffled     | `5.m: de lejos`        |
| a   | Robot       | `robot.a: beep`        |
| l   | Distortion  | `metal.l: saturado`    |

### Filtros de Fondo (NUEVO ✨)
| ID  | Nombre        | Ejemplo                    |
|-----|---------------|----------------------------|
| fa  | Calle         | `dross.fa: en la calle`    |
| fb  | Lluvia        | `narrador.fb: lloviendo`   |
| fc  | Multitud      | `streamer.fc: en evento`   |
| fd  | Naturaleza    | `guia.fd: en la playa`     |
| fe  | Personalizado | `voz.fe: custom`           |

---

## 🎨 Ejemplos de Uso

### Básico
```
dross.fa: hola amigos, estoy en la calle
→ Voz de dross con sonido de tráfico de fondo
```

### Con filtro adicional
```
detective.r.fb: era una noche lluviosa
→ Voz con eco + sonido de lluvia
```

### Escena completa
```
reportero.fa: que paso aqui? (sirena) testigo.m.fc: yo estaba en el café policia.p: ya vamos para allá
→ 3 voces diferentes, fondo de calle y café, sirena, llamada telefónica
```

---

## 📁 Archivos Importantes

### Configuración
- `config/backgrounds.json` - Configuración de fondos
- `config/sounds.json` - Configuración de efectos de sonido

### Archivos de Audio
- `backgrounds/*.wav` - Archivos de fondo
- `sounds/*.wav` - Efectos de sonido puntuales

### Código
- `core/background_manager.py` - Gestor de fondos
- `core/audio_filters.py` - Aplicación de filtros
- `core/advanced_processor.py` - Orquestador principal
- `core/message_parser.py` - Parser de sintaxis

### Documentación
- `README.md` - Documentación general
- `backgrounds/README.md` - Guía de fondos
- `docs/BACKGROUND_FILTERS.md` - Documentación técnica completa
- `docs/BACKGROUND_IMPLEMENTATION.md` - Resumen de implementación

---

## ⚙️ Configuración

### Ajustar volumen de un fondo

Edita `config/backgrounds.json`:

```json
{
  "fa": {
    "id": "fa",
    "name": "calle",
    "path": "backgrounds/calle.wav",
    "volume": 0.3  ← Cambia esto (0.2-0.4 recomendado)
  }
}
```

**Guía de volumen:**
- `0.2-0.25`: Muy sutil
- `0.25-0.30`: Presente pero no molesto ✅
- `0.30-0.40`: Prominente
- `>0.40`: Puede tapar la voz ❌

### Agregar un fondo nuevo

1. Coloca el archivo en `backgrounds/nuevo_fondo.wav`
2. Edita `config/backgrounds.json`:

```json
{
  "backgrounds": {
    "fe": {
      "id": "fe",
      "name": "nuevo_fondo",
      "description": "Descripción",
      "path": "backgrounds/nuevo_fondo.wav",
      "volume": 0.3
    }
  }
}
```

3. Úsalo: `dross.fe: con mi nuevo fondo`

---

## 🔍 Troubleshooting

### ❌ Fondo no se escucha
- Verifica que el archivo existe en `backgrounds/`
- Aumenta `volume` en la configuración (0.3-0.4)
- Verifica que el archivo tiene audio audible

### ❌ Fondo tapa la voz
- Reduce `volume` en la configuración (0.2-0.25)
- Normaliza el archivo de fondo antes de usarlo

### ❌ Error al cargar fondo
- Verifica la ruta en `config/backgrounds.json`
- Usa formato WAV (MP3 puede tener problemas)
- Verifica permisos de lectura del archivo

---

## 🎯 Próximos Pasos

1. **Generar fondos de prueba** ← Empieza aquí
   ```bash
   python test_background_filters.py
   ```

2. **Probar la sintaxis**
   ```bash
   python example_backgrounds.py
   ```

3. **Reemplazar fondos sintéticos** con audio real
   - Descargar de Freesound.org, YouTube Audio Library, etc.
   - Colocar en `backgrounds/`
   - Actualizar rutas en `config/backgrounds.json`

4. **Implementar endpoint API** `/synthesize/advanced`
   - Exponer el procesador vía REST
   - Permitir uso desde Streamer.bot u otros servicios

5. **Crear UI** para gestión de fondos
   - Subir archivos desde la GUI
   - Ajustar volúmenes visualmente
   - Preview de mezclas

---

## 📚 Recursos

### Dónde conseguir fondos
- **Freesound.org** - Biblioteca gratuita de efectos
- **YouTube Audio Library** - Efectos sin copyright
- **BBC Sound Effects** - Archivos de la BBC
- **Zapsplat** - Efectos con atribución

### Documentación
- `docs/BACKGROUND_FILTERS.md` - Documentación técnica completa
- `docs/BACKGROUND_IMPLEMENTATION.md` - Resumen de implementación
- `backgrounds/README.md` - Guía de fondos

---

## ❓ FAQ

**Q: ¿Cuál es la diferencia entre un fondo y un efecto de sonido?**  
A: Los efectos (`(disparo)`) se insertan puntualmente, los fondos (`.fa:`) se mezclan durante toda la voz.

**Q: ¿Puedo combinar múltiples fondos?**  
A: Actualmente solo un fondo por segmento de voz. Para mezclar múltiples fondos, hazlo en el archivo de audio directamente.

**Q: ¿Qué formato de audio es mejor?**  
A: WAV sin comprimir para mejor calidad. MP3 funciona pero puede tener artifacts.

**Q: ¿Puedo usar fondos estéreo?**  
A: Sí, pero se convertirán automáticamente a mono. Para mejor control, convierte a mono antes.

**Q: ¿Los fondos afectan el performance?**  
A: Impacto mínimo (~50-200ms extra). El resampleo es la parte más costosa.

---

**¡Listo para crear escenas de audio inmersivas! 🎬🎙️**

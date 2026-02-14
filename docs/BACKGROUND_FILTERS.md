# 🎭 Sistema Multi-Voz con Fondos - Documentación Técnica

## Resumen

El sistema de fondos permite mezclar audio de ambiente/contexto **durante** la reproducción de una voz, creando escenas más inmersivas y realistas.

## Arquitectura

```
Mensaje: "dross.fa: hola amigos"
           │    │    └─ Texto a sintetizar
           │    └────── Filtro de fondo (calle)
           └─────────── Voz a usar

Pipeline de Procesamiento:
┌─────────────────────────────────────────────────────────────┐
│ 1. MessageParser                                            │
│    └─ Parsea "dross.fa: hola amigos"                       │
│       └─ voice: "dross"                                     │
│       └─ filters: [AudioFilter.BACKGROUND_A]                │
│       └─ content: "hola amigos"                             │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. AdvancedProcessor._process_voice_segment()              │
│    a. TTS → "hola amigos" con voz base                     │
│    b. RVC → Conversión a voz "dross"                       │
│    c. Filtros Normales → Aplicar r, p, pu, pd, m, a, l    │
│    d. Filtros de Fondo → Mezclar con fa, fb, fc, fd, fe   │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. BackgroundManager.load_background_audio("fa")           │
│    └─ Carga backgrounds/calle.wav                          │
│    └─ Retorna (audio, sample_rate, volume)                 │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. AudioFilters.apply_background()                         │
│    a. Resamplear fondo si es necesario (16kHz)             │
│    b. Loop o recortar fondo al tamaño de la voz            │
│    c. Normalizar ambos audios                              │
│    d. Mezclar: voz*0.8 + fondo*volume                      │
│    e. Normalizar resultado final                           │
└─────────────────────────────────────────────────────────────┘
                            ▼
                   Audio Final Mezclado
```

## Componentes

### 1. MessageParser (`core/message_parser.py`)

**Responsabilidad:** Parsear mensajes con sintaxis Mopolo y detectar filtros de fondo.

**Enum AudioFilter:**
```python
class AudioFilter(Enum):
    # ... filtros normales ...
    BACKGROUND_A = "fa"  # Fondo A (calle)
    BACKGROUND_B = "fb"  # Fondo B (lluvia)
    BACKGROUND_C = "fc"  # Fondo C (multitud)
    BACKGROUND_D = "fd"  # Fondo D (naturaleza)
    BACKGROUND_E = "fe"  # Fondo E (personalizado)
```

**Método parse():**
- Detecta patrones `voz.filtro:` usando regex
- Separa filtros en lista
- Crea MessageSegment con filtros detectados

### 2. BackgroundManager (`core/background_manager.py`)

**Responsabilidad:** Gestionar archivos de audio de fondo.

**Métodos principales:**
- `load_background_audio(id)` → Carga audio de fondo
- `get_background(id)` → Obtiene configuración
- `add_background()` → Agrega nuevo fondo
- `update_background_volume()` → Ajusta volumen

**Configuración** (`config/backgrounds.json`):
```json
{
  "fa": {
    "id": "fa",
    "name": "calle",
    "path": "backgrounds/calle.wav",
    "volume": 0.3
  }
}
```

### 3. AudioFilters (`core/audio_filters.py`)

**Responsabilidad:** Aplicar efectos de audio y mezclar con fondos.

**Método apply_background():**
```python
def apply_background(
    audio: np.ndarray,           # Voz principal
    sr: int,                     # Sample rate voz
    background_audio: np.ndarray, # Audio de fondo
    background_sr: int,          # Sample rate fondo
    background_volume: float     # Volumen fondo (0.0-1.0)
) -> np.ndarray:
    # 1. Resamplear si es necesario
    # 2. Loop/recortar al tamaño de la voz
    # 3. Normalizar ambos
    # 4. Mezclar: voz*0.8 + fondo*volume
    # 5. Normalizar resultado
```

**Algoritmo de mezcla:**
1. Si fondo es más corto → Loop hasta cubrir toda la voz
2. Si fondo es más largo → Recortar al tamaño de la voz
3. Normalizar voz: `audio / max(abs(audio))`
4. Normalizar fondo: `bg / max(abs(bg))`
5. Mezclar: `voz_norm * 0.8 + bg_norm * volume`
6. Normalizar resultado: `mixed / max(abs(mixed)) * 0.95`

### 4. AdvancedProcessor (`core/advanced_processor.py`)

**Responsabilidad:** Orquestar todo el pipeline de procesamiento.

**Método _process_voice_segment():**
```python
# Separar filtros normales de filtros de fondo
normal_filters = [f for f in filters if not f.value.startswith('f')]
background_filters = [f for f in filters if f.value.startswith('f')]

# Aplicar filtros normales (r, p, pu, pd, m, a, l)
for filter in normal_filters:
    audio = AudioFilters.apply_filter(audio, sr, filter.value)

# Aplicar filtros de fondo (fa, fb, fc, fd, fe)
for bg_filter in background_filters:
    bg_data = BackgroundManager.load_background_audio(bg_filter.value)
    if bg_data:
        bg_audio, bg_sr, bg_volume = bg_data
        audio = AudioFilters.apply_background(
            audio, sr, bg_audio, bg_sr, bg_volume
        )
```

## Flujo de Datos

### Ejemplo: `"reportero.fa.r: estamos en vivo"`

```
1. Parser detecta:
   - voice: "reportero"
   - filters: [AudioFilter.BACKGROUND_A, AudioFilter.REVERB]
   - content: "estamos en vivo"

2. TTS genera audio neutral: "estamos en vivo" (3.5s @ 16kHz)

3. RVC convierte a voz "reportero"

4. Separar filtros:
   - normal_filters: [AudioFilter.REVERB]
   - background_filters: [AudioFilter.BACKGROUND_A]

5. Aplicar reverb:
   audio = AudioFilters.apply_reverb(audio, 16000)

6. Cargar fondo "calle":
   bg_audio, bg_sr, bg_vol = BackgroundManager.load("fa")
   # bg_audio: 10s @ 44100Hz
   # bg_sr: 44100
   # bg_vol: 0.3

7. Aplicar fondo:
   a. Resamplear fondo: 44100Hz → 16000Hz
   b. Loop fondo: 10s → 3.5s (recortar)
   c. Mezclar: audio*0.8 + fondo*0.3

8. Resultado: Audio con voz + eco + sonido de calle
```

## Diferencia con Efectos de Sonido

| Aspecto | Efecto de Sonido | Filtro de Fondo |
|---------|------------------|-----------------|
| **Sintaxis** | `(disparo)` | `.fa:` |
| **Posición** | Puntual (inserta entre voces) | Durante toda la voz |
| **Procesamiento** | Cargar archivo completo | Cargar, loop, mezclar |
| **Duración** | Duración del archivo | Duración de la voz |
| **Volumen** | 100% (archivo original) | Configurable (0.2-0.4) |
| **Ejemplo** | `dross: hola (disparo)` | `dross.fa: hola` |

## Configuración

### Archivo: `config/backgrounds.json`

```json
{
  "backgrounds": {
    "fa": {
      "id": "fa",
      "name": "calle",
      "description": "Tráfico urbano",
      "path": "backgrounds/calle.wav",
      "volume": 0.3
    },
    "fb": {
      "id": "fb",
      "name": "lluvia",
      "description": "Lluvia suave",
      "path": "backgrounds/lluvia.wav",
      "volume": 0.25
    }
  },
  "info": {
    "volume_range": "0.0 - 1.0 (recomendado: 0.2 - 0.4)"
  }
}
```

### Parámetros

- **id**: Identificador único (fa, fb, fc, fd, fe)
- **name**: Nombre descriptivo (para búsqueda por nombre)
- **description**: Descripción del ambiente
- **path**: Ruta al archivo de audio
- **volume**: Volumen de mezcla (0.0-1.0)
  - 0.2-0.3: Fondo sutil
  - 0.3-0.4: Fondo presente
  - >0.4: Puede tapar la voz

## Archivos de Audio

### Requisitos

- **Formato**: WAV (recomendado), MP3
- **Sample Rate**: Cualquiera (se resamplea a 16kHz)
- **Canales**: Mono o Estéreo (se convierte a mono)
- **Duración**: 10-30 segundos (óptimo para loops)
- **Contenido**: Evitar voces prominentes

### Fuentes Recomendadas

1. **Freesound.org** - Biblioteca gratuita
2. **YouTube Audio Library** - Sin copyright
3. **BBC Sound Effects** - Archivos de la BBC
4. **Zapsplat** - Con atribución

## Ejemplos de Uso

### Básico
```
reportero.fa: estamos en vivo desde la calle
→ Voz de reportero con fondo de tráfico
```

### Con filtro adicional
```
detective.r.fb: era una noche lluviosa
→ Voz con eco + fondo de lluvia
```

### Múltiples voces con fondos
```
reportero.fa: que paso aqui? testigo.m: yo lo vi todo
→ Reportero en la calle + testigo con voz amortiguada
```

### Combinación completa
```
reportero.fa: en vivo (sirena) testigo.m.fc: estaba en el cafe
→ Reportero en calle, sirena, testigo amortiguado en café
```

## Testing

### Generar fondos de prueba
```bash
python test_background_filters.py
```

Genera:
- `backgrounds/calle.wav` - Tráfico sintético
- `backgrounds/lluvia.wav` - Gotas de agua
- `backgrounds/multitud.wav` - Conversaciones
- `backgrounds/naturaleza.wav` - Pájaros y viento
- `test_backgrounds/voice_with_*.wav` - Mezclas de prueba

### Ver ejemplos
```bash
python example_backgrounds.py
```

Muestra:
- Guía de sintaxis completa
- Ejemplos de mensajes complejos
- Casos de uso reales

## Troubleshooting

### Fondo no se escucha
- Verificar que el archivo existe en `backgrounds/`
- Aumentar `volume` en `config/backgrounds.json` (0.3-0.4)
- Verificar que el audio de fondo tiene contenido audible

### Fondo tapa la voz
- Reducir `volume` en configuración (0.2-0.25)
- Verificar que el archivo de fondo no tiene picos muy altos
- Normalizar el archivo de fondo antes de usarlo

### Error al cargar fondo
- Verificar ruta en `config/backgrounds.json`
- Verificar formato de archivo (WAV preferido)
- Revisar permisos de lectura del archivo

## Performance

### Optimizaciones implementadas
- Loop eficiente usando `np.tile()`
- Resampleo solo si es necesario
- Normalización vectorizada con numpy
- Cache de archivos en memoria (futuro)

### Métricas típicas
- Carga de fondo: ~10-50ms
- Resampleo: ~20-100ms (si es necesario)
- Mezcla: ~5-20ms
- **Total**: ~50-200ms por segmento

## Próximas Mejoras

- [ ] Cache de fondos en memoria
- [ ] Crossfade entre segmentos con fondos diferentes
- [ ] Filtros de ecualización para fondos
- [ ] Generación procedural de fondos
- [ ] Soporte para fondos estéreo
- [ ] UI para configurar fondos desde la interfaz

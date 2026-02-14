# 📋 Resumen de Implementación - Filtros de Fondo

## ✅ Archivos Creados

### Core Components
1. **`core/background_manager.py`** (267 líneas)
   - Gestor de archivos de audio de fondo
   - Carga y gestión de configuración desde `config/backgrounds.json`
   - Métodos para cargar, agregar y actualizar fondos
   - Soporte para búsqueda por ID y nombre

2. **`core/message_parser.py`** (actualizado)
   - Agregados filtros de fondo al enum `AudioFilter`
   - `BACKGROUND_A` (fa), `BACKGROUND_B` (fb), `BACKGROUND_C` (fc), `BACKGROUND_D` (fd), `BACKGROUND_E` (fe)

3. **`core/audio_filters.py`** (actualizado)
   - Nueva función `apply_background()` para mezclar voz con fondo
   - Resampleo automático
   - Loop/recorte de fondo al tamaño de la voz
   - Mezcla con volumen configurable

4. **`core/advanced_processor.py`** (actualizado)
   - Integración de `BackgroundManager`
   - Separación de filtros normales vs filtros de fondo
   - Pipeline: filtros normales → filtros de fondo

### Configuration
5. **`config/backgrounds.json`** (nuevo)
   - Configuración de 5 fondos por defecto (fa-fe)
   - Metadata: id, name, description, path, volume

### Documentation
6. **`backgrounds/README.md`** (nuevo)
   - Guía de uso de fondos
   - Requisitos de archivos
   - Recomendaciones de volumen
   - Fuentes de audio gratuitas

7. **`docs/BACKGROUND_FILTERS.md`** (nuevo)
   - Documentación técnica completa
   - Arquitectura del sistema
   - Flujo de datos
   - Ejemplos de uso
   - Troubleshooting

### Testing & Examples
8. **`test_background_filters.py`** (nuevo, ejecutable)
   - Genera fondos de prueba sintéticos
   - Crea ejemplos de mezcla voz + fondo
   - Útil para validar el sistema

9. **`example_backgrounds.py`** (nuevo, ejecutable)
   - Ejemplos completos de uso
   - Guía de sintaxis
   - Casos de uso reales

10. **`README.md`** (actualizado)
    - Sección completa sobre mensajes multi-voz
    - Tabla de filtros de fondo
    - Ejemplos de sintaxis
    - Scripts de prueba

## 🎯 Funcionalidad Implementada

### Sintaxis
```
voz.fa: texto con fondo de calle
voz.fb: texto con fondo de lluvia
voz.fc: texto con fondo de multitud
voz.fd: texto con fondo de naturaleza
voz.fe: texto con fondo personalizado
```

### Combinaciones
```
voz.filtro.fondo: texto
→ dross.r.fa: hola con eco y fondo de calle

voz.fondo.filtro: texto
→ dross.fa.p: hola en la calle por teléfono

voz.filtro1.filtro2.fondo: texto
→ dross.r.p.fb: múltiples filtros + lluvia
```

### Fondos por Defecto
| ID  | Nombre        | Descripción                  | Volumen |
|-----|---------------|------------------------------|---------|
| fa  | calle         | Tráfico y ambiente urbano    | 0.30    |
| fb  | lluvia        | Sonido de lluvia             | 0.25    |
| fc  | multitud      | Restaurante o lugar público  | 0.30    |
| fd  | naturaleza    | Viento, playa, pájaros       | 0.25    |
| fe  | personalizado | Definido por el usuario      | 0.30    |

## 🔧 Pipeline de Procesamiento

```
Mensaje: "dross.fa.r: hola amigos"

1. MessageParser
   └─ voice: "dross"
   └─ filters: [AudioFilter.BACKGROUND_A, AudioFilter.REVERB]
   └─ content: "hola amigos"

2. AdvancedProcessor._process_voice_segment()
   └─ TTS → Audio neutral
   └─ RVC → Voz "dross"
   └─ Separar filtros:
      ├─ normal_filters: [REVERB]
      └─ background_filters: [BACKGROUND_A]
   └─ Aplicar reverb
   └─ Aplicar fondo:
      ├─ Cargar backgrounds/calle.wav
      ├─ Resamplear si es necesario
      ├─ Loop/recortar al tamaño de la voz
      └─ Mezclar: voz*0.8 + fondo*volume

3. Resultado
   └─ Audio con voz + reverb + fondo de calle
```

## 📊 Diferencia con Efectos de Sonido

| Característica | Efecto de Sonido | Filtro de Fondo |
|----------------|------------------|-----------------|
| **Sintaxis** | `(nombre)` | `voz.fa:` |
| **Duración** | Puntual | Durante toda la voz |
| **Ejemplo** | `dross: hola (disparo)` | `dross.fa: hola` |
| **Uso** | Eventos específicos | Ambiente/contexto |
| **Volumen** | 100% | Configurable (0.2-0.4) |

## 🧪 Testing

### Generar fondos de prueba
```bash
python test_background_filters.py
```

**Genera:**
- `backgrounds/calle.wav` (tráfico sintético)
- `backgrounds/lluvia.wav` (gotas)
- `backgrounds/multitud.wav` (conversaciones)
- `backgrounds/naturaleza.wav` (pájaros)
- `test_backgrounds/voice_with_*.wav` (mezclas)

### Ver ejemplos
```bash
python example_backgrounds.py
```

**Muestra:**
- Guía completa de sintaxis
- 6 ejemplos de mensajes complejos
- Casos de uso reales

## 📝 Ejemplos de Uso

### Básico
```python
from core.advanced_processor import AdvancedAudioProcessor

processor = AdvancedAudioProcessor(...)
audio, sr = processor.process_message("dross.fa: hola amigos")
```

### Casos de Uso

**1. Reportero en la calle:**
```
reportero.fa: estamos en vivo (sirena) testigo.m: yo lo vi
```

**2. Escena bajo la lluvia:**
```
narrador.fb.r: era una noche lluviosa (trueno) detective: investiguemos
```

**3. Evento con multitud:**
```
streamer.fc: hola a todos (aplauso) fan.pu: te amoooo!
```

**4. Playa tranquila:**
```
guia.fd: bienvenidos a este paraiso persona: que hermoso!
```

**5. Llamada desde la calle:**
```
persona1.p.fa: alló? persona2.p: apenas se oye el tráfico
```

## 🎨 Recomendaciones de Uso

### Volumen
- **0.2-0.25**: Fondo muy sutil
- **0.25-0.30**: Fondo presente pero no molesto ✅ (recomendado)
- **0.30-0.40**: Fondo prominente
- **>0.40**: Puede tapar la voz ❌

### Archivos de Audio
- **Duración**: 10-30 segundos (óptimo para loops)
- **Formato**: WAV (mejor calidad)
- **Sample Rate**: Cualquiera (se resamplea automáticamente)
- **Contenido**: Evitar voces o música prominente

### Fuentes Gratuitas
- Freesound.org
- YouTube Audio Library
- BBC Sound Effects
- Zapsplat

## 🔄 Próximos Pasos

Ahora que los filtros de fondo están implementados, lo siguiente es:

1. **API Endpoint** `/synthesize/advanced`
   - Exponer el procesador avanzado vía REST
   - Soportar mensajes complejos con fondos
   - Retornar audio generado

2. **Archivos de Audio Reales**
   - Descargar/crear fondos de calidad
   - Reemplazar los sintéticos de prueba
   - Agregar más variedad (oficina, bosque, etc.)

3. **UI para Gestión de Fondos**
   - Agregar pestaña en la GUI
   - Permitir subir archivos de fondo
   - Ajustar volúmenes visualmente
   - Preview de mezclas

4. **Optimizaciones**
   - Cache de fondos en memoria
   - Crossfade entre segmentos
   - Filtros de ecualización

## ✨ Impacto

Este sistema permite crear **escenas de audio inmersivas** con contexto ambiental, ideal para:

- 🎙️ **Streamers**: Crear contenido dinámico y entretenido
- 🎬 **Creadores**: Producir audio narrativo complejo
- 🎮 **Gaming**: Simular ambientes y escenarios
- 📻 **Podcasters**: Agregar contexto a las historias
- 🤖 **Bots**: Respuestas más realistas y contextuales

**Ejemplo de uso real:**
```
reportero.fa: estamos en el centro de la ciudad (sirena) 
testigo.m.fc: yo estaba en el café cuando paso 
detective.r: las pistas me llevaron aquí
(disparo)
sospechoso.p.pu: yo no fui!
```

Esto genera una **escena completa** con:
- Reportero en la calle con tráfico
- Sirena de policía
- Testigo con voz amortiguada en café con multitud
- Detective con eco
- Disparo
- Sospechoso por teléfono con voz aguda (nervioso)

🚀 **¡Todo con un solo mensaje de texto!**

# Fondos de Audio

Esta carpeta contiene los archivos de audio que se usan como fondos para mezclar con las voces.

## 🎯 ¿Qué son los Filtros de Fondo?

Los filtros de fondo **mezclan** un audio de ambiente/contexto **durante** toda la frase, a diferencia de los efectos de sonido que se insertan puntualmente.

**Ejemplo:**
```
dross.fa: hola amigos, estoy en la calle
```
Aquí `fa` es el filtro de fondo "calle", que mezcla sonido de tráfico **durante** toda la frase "hola amigos, estoy en la calle".

## 🎬 Diferencia con Efectos de Sonido

| Característica | Efecto de Sonido | Filtro de Fondo |
|----------------|------------------|-----------------|
| **Sintaxis** | `(nombre)` | `voz.fa:` |
| **Duración** | Puntual (se inserta y termina) | Continuo (durante toda la voz) |
| **Ejemplo** | `dross: hola (disparo)` | `dross.fa: hola` |
| **Uso** | Eventos específicos | Ambiente/contexto |

## Fondos Disponibles

| ID  | Nombre        | Descripción                  | Volumen |
|-----|---------------|------------------------------|---------|
| fa  | calle         | Tráfico y ambiente urbano    | 0.30    |
| fb  | lluvia        | Sonido de lluvia             | 0.25    |
| fc  | multitud      | Restaurante o lugar público  | 0.30    |
| fd  | naturaleza    | Viento, playa, pájaros       | 0.25    |
| fe  | personalizado | Definido por el usuario      | 0.30    |

## Requisitos de Archivos

- **Formato**: WAV (recomendado) o MP3
- **Sample Rate**: Cualquiera (se resampleará automáticamente a 16kHz)
- **Canales**: Mono o Estéreo (se convertirá a mono)
- **Duración**: Preferiblemente 10-30 segundos (se reproducirá en loop)
- **Volumen**: Normalizado (el volumen se ajusta en la configuración)

## Cómo Agregar un Fondo

1. **Coloca el archivo de audio** en esta carpeta con un nombre descriptivo:
   ```
   backgrounds/calle.wav
   backgrounds/lluvia.wav
   backgrounds/cafe.wav
   ```

2. **Actualiza la configuración** en `config/backgrounds.json`:
   ```json
   {
     "fa": {
       "id": "fa",
       "name": "calle",
       "description": "Sonido de calle con tráfico",
       "path": "backgrounds/calle.wav",
       "volume": 0.3
     }
   }
   ```

3. **Úsalo en tus mensajes**:
   ```
   dross.fa: hola amigos, estoy en la calle
   ```

## Recomendaciones

- **Volumen**: Mantén entre 0.2-0.4 para que no tape la voz
- **Duración**: Loops de 10-30s funcionan mejor que archivos muy largos
- **Contenido**: Evita fondos con voces o música muy prominente
- **Calidad**: Archivos de al menos 44.1kHz para mejor calidad

## Dónde Conseguir Fondos

- **Freesound.org**: Biblioteca gratuita de efectos de sonido
- **YouTube Audio Library**: Efectos gratuitos sin copyright
- **BBC Sound Effects**: Archivos gratuitos de la BBC
- **Zapsplat**: Efectos gratuitos con atribución

## Notas Técnicas

El sistema:
- Resamplea automáticamente al sample rate de la voz (16kHz por defecto)
- Convierte estéreo a mono si es necesario
- Reproduce en loop si el fondo es más corto que la voz
- Recorta si el fondo es más largo
- Mezcla con 80% voz + volumen_configurado% fondo
- Normaliza el resultado para evitar clipping

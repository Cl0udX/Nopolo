# Nopolo TTS - Integración con Streamer.bot

Scripts C# para integrar Nopolo TTS con Streamer.bot

## 📋 Requisitos

1. **Nopolo TTS corriendo** con API habilitada:
    ```bash
    ./run_nopolo_full.sh
    # O manualmente:
    python main.py --with-api
    ```

2. **Referencias en Streamer.bot:**
    - Ubicación: `C:\Windows\Microsoft.NET\Framework64\vx.x.xxxx\`
    - Archivos necesarios:
      - `System.dll`
      - `System.Net.Sockets.dll`

## 🚀 Scripts Disponibles

### 1. TTS_Simple.cs ⭐ RECOMENDADO PARA PRINCIPIANTES
- **Comando:** `!tts <mensaje>`
- **Función:** Envía texto al TTS con voz por defecto
- **Ejemplo:** `!tts Hola chat, ¿cómo están?`
- **Nivel:** Básico

### 2. TTS_ConVoz.cs
- **Comando:** `!tts <voz> <mensaje>`
- **Función:** Usa una voz específica
- **Ejemplos:** 
  - `!tts goku Hola, soy Goku`
  - `!tts homero D'oh!`
- **Nivel:** Básico

### 3. TTS_NopoloMultiVoz.cs 🎭 NUEVO - MODO AVANZADO
- **Comando:** Usa la sintaxis completa de Nopolo
- **Función:** Múltiples voces, efectos y sonidos en un solo mensaje
- **Sintaxis:**
  ```
  voz: texto                  → Usar una voz
  voz.filtro: texto          → Voz + efecto (r, p, pu, pd, m, a, l)
  voz.fondo: texto           → Voz + música de fondo
  (sonido)                   → Reproducir sonido
  ```
- **Ejemplos:**
  ```
  homero: Hola (aplausos) dross: Gracias
  homero.r: Hola con eco
  homero.fa: Hola con fondo de ambiente
  ```
- **Filtros disponibles:**
  - `r` = Eco/Reverberación
  - `p` = Llamada telefónica  
  - `pu` = Voz aguda (chipmunk)
  - `pd` = Voz grave (monstruo)
  - `m` = Voz apagada
  - `a` = Robot
  - `l` = Saturada
- **Nivel:** Avanzado

### 4. TTS_ListarVoces.cs
- **Comando:** `!voces`
- **Función:** Muestra las voces disponibles en los logs
- **Nivel:** Básico

### 5. TTS_EstadoCola.cs
- **Comando:** `!cola`
- **Función:** Muestra cuántos mensajes hay en cola
- **Nivel:** Básico

## 📝 Instalación en Streamer.bot

### Para principiantes (Recomendado):

1. **Ir a Actions:**
    - Click derecho → Add
    - Nombre: `TTS Command`
    - Agregar Execute C# Code

2. **Agregar Sub-Action:**
    - Execute Code → Execute C# Code
    - Copiar el código de **TTS_Simple.cs**
    - Click **Compile**
    - Si compila sin errores, ¡listo!

3. **Crear Comando:**
    - Ir a Commands
    - Crear comando `!tts`
    - Vincular a la Action creada

### Para usuarios avanzados:

Usa **TTS_NopoloMultiVoz.cs** para acceder a todas las funcionalidades:
- Múltiples voces en un mensaje
- Efectos de audio en tiempo real
- Música de fondo
- Sonidos personalizados

3. **Agregar Referencias:**
    - En Settings (dentro del código C#)
    - Click Add Reference
    - Navegar a: `C:\Windows\Microsoft.NET\Framework64\vx.x.xxxx\`
    - Seleccionar `System.dll` y `System.Net.Sockets.dll`

4. **Crear Command:**
    - Ir a Commands
    - Click derecho → Add
    - Command: `!tts`
    - Location: Start
    - Enabled: ✅
    - Arrastrar el Action creado

## ⚙️ Configuración de Voces

Las voces se configuran en la interfaz de Nopolo (`python main.py`).

**Voces por defecto:**
- `base_male` - Voz masculina base
- `base_female` - Voz femenina base

## 🔧 Solución de Problemas

| Error | Solución |
|-------|----------|
| "No se pudo conectar al servidor TTS" | Verifica que Nopolo esté corriendo en puerto 8000. Revisa `.env` |
| Error de compilación | Asegúrate de agregar referencias correctas en `C:\Windows\Microsoft.NET\Framework64\vx.x.xxxx\` |
| Voz no encontrada | Lista voces disponibles con `!voces`. Verifica el ID en la interfaz de Nopolo |


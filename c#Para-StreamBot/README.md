# Nopolo TTS - Integración con Streamer.bot

Scripts C# para integrar Nopolo TTS con Streamer.bot

## 📋 Requisitos

1. **Nopolo TTS corriendo** con API habilitada:
    ```bash
    python main.py --with-api
    ```

2. **Referencias en Streamer.bot:**
    - Ubicación: `C:\Windows\Microsoft.NET\Framework64\vx.x.xxxx\`
    - Archivos necesarios:
      - `System.dll`
      - `System.Net.Sockets.dll`

## 🚀 Scripts Disponibles

### 1. TTS_Simple.cs
- **Comando:** `!tts <mensaje>`
- **Función:** Envía texto al TTS con voz por defecto
- **Ejemplo:** `!tts Hola chat, ¿cómo están?`

### 2. TTS_ConVoz.cs
- **Comando:** `!tts <voz> <mensaje>`
- **Función:** Usa una voz específica
- **Ejemplos:** 
  - `!tts goku Hola, soy Goku`
  - `!tts homero D'oh!`

### 3. TTS_ListarVoces.cs
- **Comando:** `!voces`
- **Función:** Muestra las voces disponibles en los logs

### 4. TTS_EstadoCola.cs
- **Comando:** `!cola`
- **Función:** Muestra cuántos mensajes hay en cola

## 📝 Instalación en Streamer.bot

1. **Ir a Actions:**
    - Click derecho → Add
    - Nombre: `TTS Command`
    - Agregar Execute C# Code

2. **Agregar Sub-Action:**
    - Execute Code → Execute C# Code
    - Pegar el código del script deseado
    - Click Compile

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


# 🐛 Debugging del Overlay - Guía de Casos de Uso

Este documento explica cómo verificar que el overlay funciona correctamente en los 4 casos principales.

---

## 📊 Casos de Uso y Comportamiento Esperado

### ✅ Caso 1: Modo Normal desde GUI

**Configuración:**
- Checkbox "Modo Nopolo" → **DESACTIVADO** ❌
- Ejecutar desde la GUI principal

**Entrada:**
```
Hola mundo, este es un mensaje simple
```

**Comportamiento Esperado:**
```
[Consola]
🔊 Modo normal activado (GUI)
[Audio Queue] Procesando modo normal con voz: VozBaseMasculina
[Audio Queue] Enviando evento overlay con is_nopolo=False

[Overlay]
📺 Mostrando TTS: is_nopolo=false, voice="VozBaseMasculina"
📝 Modo Normal: texto limpio
→ Muestra: "Hola mundo, este es un mensaje simple"
```

---

### ✅ Caso 2: Modo Nopolo desde GUI

**Configuración:**
- Checkbox "Modo Nopolo" → **ACTIVADO** ✅
- Ejecutar desde la GUI principal

**Entrada:**
```
9: un millon de años mas tarde (22)
```

**Comportamiento Esperado:**
```
[Consola]
🎭 Modo multi-voz activado (GUI)
[Multi-Voz GUI] Iniciando procesamiento...
[Multi-Voz GUI] Enviando evento overlay con is_nopolo=True

[Overlay]
📺 Mostrando TTS: is_nopolo=true, voice="Multi-Voz (GUI)"
✨ Modo Nopolo: resaltando sintaxis
→ Muestra: "9: un millon de años mas tarde (22)" [CON COLORES]
   - "9:" en azul (voz)
   - "(22)" en rojo (sonido)
```

---

### ✅ Caso 3: Modo Normal desde Endpoint

**Request:**
```bash
curl -X POST http://localhost:8000/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hola desde el endpoint", "voice_id": "homero"}'
```

**Comportamiento Esperado:**
```
[Consola]
[Audio Queue] Procesando modo normal con voz: Homero
[Audio Queue] Enviando evento overlay con is_nopolo=False

[Overlay]
📺 Mostrando TTS: is_nopolo=false, voice="Homero"
📝 Modo Normal: texto limpio
→ Muestra: "Hola desde el endpoint"
```

---

### ✅ Caso 4: Modo Nopolo desde Endpoint

**Request:**
```bash
curl -X POST http://localhost:8000/api/tts/multivoice \
  -H "Content-Type: application/json" \
  -d '{"text": "goku: vegeta te necesito vegeta: no kakarato"}'
```

**Comportamiento Esperado:**
```
[Consola]
[Worker Multi-Voz] Procesando desde endpoint: goku: vegeta te necesito...
[Worker Multi-Voz] Enviando evento overlay con is_nopolo=True, display="Multi-Voz (API)"

[Overlay]
📺 Mostrando TTS: is_nopolo=true, voice="Multi-Voz (API)"
✨ Modo Nopolo: resaltando sintaxis
→ Muestra: "goku: vegeta te necesito vegeta: no kakarato" [CON COLORES]
   - "goku:" en azul
   - "vegeta:" en azul
```

---

## 🐞 Problemas Comunes y Soluciones

### Problema 1: "Se ven dos vistas superpuestas"

**Causa:** Eventos overlay enviándose demasiado rápido sin limpiar el anterior.

**Solución Implementada:**
- El overlay ahora limpia completamente el contenido antes de mostrar nuevo texto
- Hay un delay de 50ms para forzar re-render
- Los timeouts previos se cancelan automáticamente

**Verificar:**
Abre la consola del navegador (F12 en OBS Browser Source) y busca:
```
📺 Mostrando TTS: is_nopolo=true...
🚫 Ocultando overlay
```

---

### Problema 2: "A veces muestra sintaxis y a veces no"

**Causa:** Confusión entre endpoints `/api/tts` (normal) vs `/api/tts/multivoice` (nopolo).

**Solución:**
- Si tienes sintaxis Nopolo (`voz: texto`), debes usar `/api/tts/multivoice`
- Si solo quieres una voz, usa `/api/tts`

**Scripts C#:**
- `TTS_Simple.cs` → `/api/tts` (modo normal)
- `TTS_ConVoz.cs` → `/api/tts` (modo normal con voz específica)
- `TTS_NopoloMultiVoz.cs` → `/api/tts/multivoice` (modo nopolo)

---

### Problema 3: "El overlay no muestra nada"

**Checklist:**
1. ✅ Servidor overlay iniciado (botón "▶️ Iniciar Servidor Overlay")
2. ✅ Estado muestra "🟢 Conectado"
3. ✅ Checkboxes de modo activados:
   - "📝 Solo texto (limpio)" → Para modo normal
   - "🎨 Mostrar modo Nopolo" → Para sintaxis resaltada
4. ✅ URL correcta en OBS Browser Source
5. ✅ Consola del navegador muestra "✅ Conectado al servidor Nopolo TTS"

---

## 🔍 Debugging con Consola del Navegador

### Activar consola en OBS:
1. Haz clic derecho en el Browser Source del overlay
2. Selecciona "Interact"
3. Presiona F12 para abrir Dev Tools

### Logs que debes ver:

**Al conectar:**
```
🎙️ Nopolo TTS Overlay iniciado
📺 Modo: normal
🔌 WebSocket: ws://localhost:8765/ws
✅ Conectado al servidor Nopolo TTS
```

**Al recibir evento (modo normal):**
```
📺 Mostrando TTS: is_nopolo=false, voice="Homero", text="Hola desde..."
📝 Modo Normal: texto limpio
```

**Al recibir evento (modo nopolo):**
```
📺 Mostrando TTS: is_nopolo=true, voice="Multi-Voz (API)", text="goku: hola..."
✨ Modo Nopolo: resaltando sintaxis
```

**Al ocultar:**
```
🚫 Ocultando overlay
```

---

## 🧪 Test Rápido

### Desde GUI:

1. **Test Modo Normal:**
   - Desactivar checkbox "Modo Nopolo"
   - Escribir: `Hola mundo`
   - Presionar Reproducir
   - Overlay debe mostrar: "Hola mundo" (sin sintaxis)

2. **Test Modo Nopolo:**
   - Activar checkbox "Modo Nopolo"
   - Escribir: `homero: doh! (risas)`
   - Presionar Reproducir
   - Overlay debe mostrar: "homero: doh! (risas)" (con colores)

### Desde Endpoint:

1. **Test Normal:**
```bash
curl -X POST http://localhost:8000/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Prueba normal"}'
```
Overlay: "Prueba normal" (texto limpio)

2. **Test Nopolo:**
```bash
curl -X POST http://localhost:8000/api/tts/multivoice \
  -H "Content-Type: application/json" \
  -d '{"text": "goku: hola vegeta: hola"}'
```
Overlay: "goku: hola vegeta: hola" (con sintaxis resaltada)

---

## 📝 Resumen de Cambios

### Overlay (overlay.html)
- ✅ Cancelación de timeouts pendientes
- ✅ Limpieza completa de contenido antes de mostrar nuevo
- ✅ Delay de 50ms para forzar re-render
- ✅ Logs detallados en consola para debugging

### Backend
- ✅ Logs mejorados que identifican origen (GUI/API)
- ✅ Clarificación de is_nopolo en cada evento
- ✅ Display names diferenciados:
  - "Multi-Voz (GUI)" → Desde interfaz
  - "Multi-Voz (API)" → Desde endpoint
  - "[Nombre de voz]" → Modo normal

---

## 💡 Tips

1. **Siempre verifica los logs** en la consola de Python para saber qué modo se activó
2. **Usa la consola del navegador** (F12) para ver exactamente qué recibe el overlay
3. **Si algo falla**, revisa que el checkbox "Modo Nopolo" esté en el estado correcto
4. **Para streams**, usa el endpoint correcto según tu necesidad:
   - `/api/tts` → Una sola voz
   - `/api/tts/multivoice` → Múltiples voces con efectos

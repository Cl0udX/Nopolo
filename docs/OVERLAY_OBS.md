# 📺 Overlay de OBS para Nopolo TTS

El overlay de OBS muestra el texto en tiempo real mientras se reproduce el TTS, perfecto para streamers que quieren que sus espectadores vean lo que está diciendo el TTS.

---

## 🚀 Cómo Usar

### 1. Iniciar el Servidor Overlay

En la interfaz de Nopolo:
1. Ve a la sección **"📺 Overlay para OBS"**
2. Haz clic en **"▶️ Iniciar Servidor Overlay"**
3. Espera a que el estado cambie a **"🟢 Conectado"**

### 2. Configurar el Modo de Visualización

Elige cómo quieres que se muestre el texto:

- **Solo texto (limpio)**: Muestra únicamente el texto sin sintaxis ni nombre de voz
- **Texto + Voz**: Muestra el texto y el nombre de la voz que lo está diciendo
- **Sintaxis Nopolo (resaltada)**: Muestra el texto con la sintaxis Nopolo coloreada (voces en azul, sonidos en rojo)

### 3. Agregar a OBS

1. En OBS, agrega una nueva fuente de tipo **"Navegador"**
2. Copia la URL que aparece en Nopolo (puedes usar el botón **"📋 Copiar URL"**)
3. Pégala en el campo **"URL"** de OBS
4. Configura las dimensiones:
   - **Ancho**: 800px (o el que prefieras)
   - **Alto**: 200px (ajusta según necesites)
5. ✅ Marca **"Actualizar el navegador cuando se hace visible"**
6. ✅ Marca **"Apagar fuente cuando no es visible"** (opcional, ahorra recursos)

### 4. Posicionar en Tu Escena

- Arrastra y redimensiona el overlay en tu escena de OBS
- El texto aparecerá automáticamente cuando se reproduzca el TTS
- Se ocultará automáticamente cuando termine

---

## 🎨 Personalizar el Estilo

### Método 1: Desde la Interfaz

1. Haz clic en **"🎨 Editar Estilo del Overlay (CSS)"**
2. Se abrirá el archivo `overlay/overlay.css` en tu editor predeterminado
3. Modifica los estilos como prefieras
4. Guarda el archivo
5. En OBS, **clic derecho en la fuente → Actualizar** para ver los cambios

### Método 2: Editar Directamente

Abre el archivo `overlay/overlay.css` en cualquier editor de texto.

#### Ejemplos de Personalización

**Cambiar el color de fondo:**
```css
#tts-container {
    background: rgba(255, 0, 0, 0.85); /* Fondo rojo semi-transparente */
}
```

**Cambiar el tamaño del texto:**
```css
#text-content {
    font-size: 36px; /* Texto más grande */
}
```

**Cambiar la fuente:**
```css
body {
    font-family: 'Comic Sans MS', cursive; /* Cambia la fuente */
}
```

**Usar un tema diferente:**

El archivo CSS incluye varios temas comentados que puedes activar:
- Tema Minimalista (fondo blanco limpio)
- Tema Neón (estilo cyberpunk con brillos)
- Tema Retro Gaming (estilo terminal verde)

Para activarlos, descomenta el que prefieras (quita los `/*` y `*/`).

---

## 🧪 Probar el Overlay

Usa el botón **"🧪 Probar Overlay"** para enviar un mensaje de prueba y verificar que todo funciona correctamente.

El mensaje de prueba durará 5 segundos y luego desaparecerá automáticamente.

---

## 🌐 Abrir en Navegador

Puedes usar el botón **"🌐 Abrir en Navegador"** para ver cómo se ve el overlay fuera de OBS. Útil para:
- Verificar que está funcionando
- Probar diferentes estilos
- Debugging

---

## ⚙️ Configuración Avanzada

### Parámetros URL

Puedes personalizar el overlay mediante parámetros en la URL:

- `?mode=normal` - Solo texto limpio
- `?mode=voice` - Texto + nombre de voz
- `?mode=nopolo` - Sintaxis Nopolo resaltada
- `?port=8765` - Puerto del WebSocket (cambiar solo si modificaste el puerto)

**Ejemplo:**
```
http://localhost:8765/overlay?mode=voice
```

### Múltiples Overlays

Puedes agregar múltiples fuentes de navegador en OBS con diferentes modos:
- Una para texto limpio
- Otra para sintaxis Nopolo
- Otra para mostrar la voz

Solo cambia el parámetro `mode` en cada URL.

---

## 🔧 Solución de Problemas

### El overlay no se muestra en OBS

1. ✅ Verifica que el servidor esté iniciado (debe decir **"🟢 Conectado"**)
2. ✅ Asegúrate de que la URL esté copiada correctamente
3. ✅ En OBS, haz clic derecho en la fuente → **Actualizar**
4. ✅ Verifica que la fuente esté visible en tu escena

### El texto no aparece cuando reproduzco TTS

1. ✅ Usa el botón **"🧪 Probar Overlay"** para verificar la conexión
2. ✅ Revisa la consola de Nopolo para ver si hay errores
3. ✅ En OBS, abre **Herramientas → Consola del navegador** para ver errores de JavaScript

### El texto aparece pero no se ve bien

1. 🎨 Edita el archivo `overlay/overlay.css`
2. 🔄 Recarga la fuente en OBS (clic derecho → Actualizar)
3. 📐 Ajusta las dimensiones de la fuente en OBS

### Los cambios de CSS no se aplican

1. ✅ Guarda el archivo CSS
2. 🔄 Recarga la fuente en OBS
3. 🧹 Si persiste, cierra y vuelve a agregar la fuente

---

## 📝 Notas Técnicas

- El overlay usa **WebSocket** para comunicación en tiempo real
- El servidor corre en el puerto **8765** por defecto
- Es completamente local (no requiere internet)
- Usa **aiohttp** para el servidor WebSocket
- Compatible con Chrome/Chromium (que usa OBS internamente)

---

## 💡 Ideas de Uso

- **Subtítulos en vivo** para streams
- **Mostrar comandos de chat** siendo procesados
- **Feedback visual** de lo que dice el TTS
- **Modo karaoke** para viewers
- **Overlay temático** según el juego/contenido

---

¿Necesitas ayuda? Abre un issue en GitHub o revisa la documentación completa del proyecto.

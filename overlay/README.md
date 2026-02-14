# 🎨 Archivos del Overlay de OBS

Esta carpeta contiene los archivos que componen el overlay para OBS.

## 📁 Archivos

### `overlay.html`
El archivo HTML principal del overlay. **No es necesario modificarlo** a menos que quieras cambiar la estructura o funcionalidad.

### `overlay.css` ⭐
**Este es el archivo que debes modificar** para personalizar la apariencia del overlay.

Aquí puedes cambiar:
- Colores de fondo
- Tamaño y fuente del texto
- Animaciones
- Bordes y sombras
- Posición de elementos
- Y mucho más...

## 🎨 Cómo Personalizar

1. Abre `overlay.css` en cualquier editor de texto
2. Modifica los estilos CSS según tus preferencias
3. Guarda el archivo
4. En OBS, haz clic derecho en la fuente del overlay → **Actualizar**
5. ¡Los cambios se aplicarán inmediatamente!

## 💡 Temas Incluidos

El archivo `overlay.css` incluye varios temas pre-configurados (comentados):

### Tema por Defecto
- Fondo oscuro semi-transparente
- Texto blanco con sombra
- Bordes morados con efecto de brillo
- Animaciones suaves

### Tema Minimalista
- Fondo blanco limpio
- Texto oscuro sin sombra
- Sin efectos especiales

### Tema Neón
- Fondo oscuro
- Bordes cyan brillantes
- Texto con efecto de neón
- Estilo cyberpunk

### Tema Retro Gaming
- Fondo negro
- Bordes verdes estilo terminal
- Fuente monoespaciada
- Estilo retro

Para activar un tema alternativo:
1. Busca el tema en `overlay.css` (están comentados con `/* ... */`)
2. Quita los comentarios `/*` y `*/` del tema que quieras
3. Guarda y recarga en OBS

## 📝 Ejemplos Rápidos

### Cambiar el color del texto
```css
#text-content {
    color: #ff0000; /* Rojo */
}
```

### Hacer el fondo completamente opaco
```css
#tts-container {
    background: rgba(0, 0, 0, 1); /* Opacidad al 100% */
}
```

### Aumentar el tamaño del texto
```css
#text-content {
    font-size: 36px; /* Más grande */
}
```

### Cambiar la fuente
```css
body {
    font-family: 'Arial', sans-serif;
}
```

## ⚠️ Importante

- **NO modifiques** `overlay.html` a menos que sepas lo que estás haciendo
- Siempre haz una **copia de seguridad** de `overlay.css` antes de hacer cambios grandes
- Si algo se rompe, puedes restaurar el CSS original desde el repositorio de GitHub

## 🔗 Más Información

Lee la documentación completa en [`docs/OVERLAY_OBS.md`](../docs/OVERLAY_OBS.md)

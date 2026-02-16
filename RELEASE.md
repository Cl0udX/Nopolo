# 🚀 Guía para Crear un Release

## Preparación Pre-Release

### 1. Verificar que todo funciona

```bash
# Probar en diferentes configuraciones
python main.py --with-api  # Windows/Linux
./run_nopolo_full.sh       # macOS

# Verificar API
curl http://localhost:8000/health

# Probar síntesis de voz
# Usa la interfaz para sintetizar varios mensajes
```

### 2. Limpiar archivos temporales

```bash
# Eliminar caches de Python
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Eliminar archivos de desarrollo
rm -rf .pytest_cache/
rm -rf .venv/  # No incluir en el release
```

### 3. Actualizar archivos de documentación

- [x] README.md - Información general y guía rápida
- [x] INSTALL.md - Instrucciones detalladas de instalación
- [x] CHANGELOG.md - Historial de cambios (crear si no existe)

### 4. Crear archivo .gitignore actualizado

Asegurar que `.gitignore` incluya:
```
.venv/
__pycache__/
*.pyc
*.pyo
.env
voices/*.pth
voices/*.index
outputs/
logs/
```

---

## Crear Release en GitHub

### 1. Crear Tag de Versión

```bash
# Hacer commit de todos los cambios
git add .
git commit -m "Release v1.0.0 - Primera versión estable"

# Crear tag
git tag -a v1.0.0 -m "Nopolo v1.0.0 - Primera Release Estable"

# Subir tag al repositorio
git push origin main
git push origin v1.0.0
```

### 2. Crear Release en GitHub Web

1. Ve a tu repositorio en GitHub
2. Click en "Releases" → "Draft a new release"
3. Selecciona el tag `v1.0.0`
4. Título: `Nopolo v1.0.0 - Primera Release Estable`

### 3. Descripción del Release (Markdown)

```markdown
# 🎉 Nopolo v1.0.0 - Primera Release Estable

¡Primera versión estable de Nopolo! Text-to-Speech con conversión RVC, completamente open source y multiplataforma.

## ✨ Características Principales

- 🌐 **Multiplataforma:** Windows, Linux, macOS (Intel y Apple Silicon)
- 🎙️ **Multi-provider TTS:** Edge TTS + Google Cloud TTS
- 🎭 **Conversión RVC:** Transforma voces a personajes
- 🎵 **Efectos de audio:** Reverb, phone, pitch, robot, y más
- 📡 **API REST:** Documentación Swagger interactiva
- 🖥️ **Interfaz gráfica:** Qt6 moderna y responsive
- 📝 **Sintaxis Mopolo:** Mensajes complejos con múltiples voces

## 🔧 Configuraciones Soportadas

| Plataforma | Hardware | CUDA | Estado |
|------------|----------|------|--------|
| Windows/Linux | CPU | - | ✅ Estable |
| Windows/Linux | NVIDIA RTX 30xx/40xx | 12.4 | ✅ Estable |
| Windows/Linux | NVIDIA RTX 50xx | 12.8 | ⚠️ Experimental |
| macOS | Apple Silicon M1/M2/M3 | - | ✅ Estable |
| macOS | Intel | - | ✅ Estable |

## 📦 Instalación

### Método Rápido (Instalador Interactivo)

```bash
git clone https://github.com/tu-usuario/nopolo.git
cd nopolo
python3.10 -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
python install.py
```

### Instalación Manual

Ver [INSTALL.md](INSTALL.md) para instrucciones detalladas según tu plataforma y hardware.

## 🚀 Inicio Rápido

**Windows/Linux:**
```bash
python main.py --with-api
```

**macOS:**
```bash
./run_nopolo_full.sh
```

Accede a la API en: http://localhost:8000/docs

## 📚 Documentación

- [README.md](README.md) - Guía general y características
- [INSTALL.md](INSTALL.md) - Instalación detallada por plataforma
- [API Docs](http://localhost:8000/docs) - Documentación interactiva (cuando la app esté corriendo)

## 🐛 Problemas Conocidos

- **RTX 50xx (CUDA 12.8):** Requiere PyTorch nightly, puede ser inestable. Usa CUDA 12.4 si encuentras problemas.
- **macOS MPS:** Algunos operadores de PyTorch no soportados. Los scripts `.sh` configuran el fallback automáticamente.
- **Fairseq en Windows:** Puede requerir permisos de administrador para instalación.

## 🙏 Agradecimientos

- Comunidad RVC por los modelos de conversión de voz
- Microsoft Edge TTS por las voces naturales
- Todos los contribuidores y testers

## ☕ Apoya el Proyecto

Si Nopolo te resulta útil, considera apoyar el desarrollo:

[![Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/postincloud)

- YouTube: [@postincloud1](https://www.youtube.com/@postincloud1)
- Twitch: [postincloud](https://www.twitch.tv/postincloud)

## 📝 Changelog Completo

### Agregado
- Soporte multiplataforma (Windows, Linux, macOS)
- Instalador interactivo `install.py`
- API REST con FastAPI y documentación Swagger
- Multi-provider TTS (Edge TTS + Google Cloud)
- Sistema de sintaxis Mopolo para mensajes complejos
- Filtros de audio: reverb, phone, pitch up/down, muffled, robot, distortion
- Filtros de fondo: calle, lluvia, multitud, naturaleza
- Efectos de sonido personalizables
- Splash screen animado con loading
- Scripts de ejecución para macOS
- Detección automática de GPU/CPU
- Soporte para CUDA 12.4 y 12.8 (experimental)

### Mejorado
- Gestión de voces con interfaz gráfica
- Cola de reproducción de audio
- Manejo de errores y logs
- Configuración mediante archivos JSON
- Performance en Apple Silicon

### Corregido
- Problemas de MPS en macOS
- Latencia en síntesis de voz
- Gestión de recursos de GPU
- Compatibilidad con RTX 50xx series
```

### 4. Adjuntar Archivos al Release

**Archivos recomendados para incluir:**

1. **Código fuente (automático):** GitHub genera `Source code (zip)` y `Source code (tar.gz)`

2. **Archivos adicionales opcionales:**
   - `nopolo-v1.0.0-quickstart.zip` - Configuración básica + archivos de ejemplo
   - `nopolo-v1.0.0-models-sample.zip` - Modelos RVC de ejemplo (si tienes permiso)
   - `install-requirements.zip` - Todos los requirements-*.txt empaquetados

### 5. Marcar como Release

- ✅ Check "Set as the latest release"
- ✅ Check "Create a discussion for this release" (opcional)
- ❌ NO marcar "This is a pre-release" (ya que es v1.0.0 estable)

---

## Post-Release

### 1. Anunciar en Redes Sociales

**Twitter/X:**
```
🎉 Nopolo v1.0.0 está aquí!

Primera versión estable de nuestra herramienta de TTS con conversión RVC.

✅ Multiplataforma
✅ Open Source
✅ Sin suscripciones
✅ GPU/CPU

Descarga: [link]
#OpenSource #TTS #VoiceSynthesis
```

**YouTube/Twitch:**
- Video demostrando las características principales
- Tutorial de instalación
- Ejemplos de uso en streams

### 2. Crear Discusión en GitHub

Crear un GitHub Discussion con:
- Anuncio del release
- Invitación a reportar bugs
- Espacio para feedback de usuarios

### 3. Actualizar Documentación Web

Si tienes una página web o wiki:
- Actualizar versión actual
- Agregar capturas de pantalla
- Actualizar guías de instalación

### 4. Monitorear Issues

Estar atento a:
- Issues de instalación en diferentes configuraciones
- Bugs reportados
- Feature requests de la comunidad

---

## Checklist Pre-Release

- [ ] Todas las pruebas pasan
- [ ] Documentación actualizada (README.md, INSTALL.md)
- [ ] Versiones de dependencias fijadas
- [ ] .gitignore actualizado
- [ ] Archivos requirements-*.txt creados
- [ ] Script install.py probado en diferentes sistemas
- [ ] Scripts run_nopolo_*.sh funcionan en macOS
- [ ] API REST funcional
- [ ] Splash screen se muestra correctamente
- [ ] No hay archivos sensibles (.env, API keys)
- [ ] Changelog creado
- [ ] Tag de versión creado
- [ ] Release notes escritos
- [ ] Archivos adjuntos preparados

---

## Después del Release

### Seguimiento de Métricas

- Descargas del release
- Stars/Forks en GitHub
- Issues abiertos vs cerrados
- Feedback en redes sociales

### Plan de Actualizaciones

**v1.0.1 (Hotfix):** Corrección de bugs críticos
**v1.1.0 (Minor):** Nuevas características pequeñas
**v2.0.0 (Major):** Cambios significativos de arquitectura

---

¡Buena suerte con el release! 🚀

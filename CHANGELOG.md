# Changelog

Todos los cambios notables de Nopolo se documentarán en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [1.0.0] - 2026-02-15

### Agregado
- 🌐 Soporte multiplataforma completo (Windows, Linux, macOS)
- 🤖 Instalador interactivo `install.py` con detección automática de sistema
- 📡 API REST con FastAPI y documentación Swagger interactiva
- 🎙️ Multi-provider TTS: Edge TTS (Microsoft) y Google Cloud TTS
- 📝 Sistema de sintaxis Mopolo para mensajes multi-voz
- 🎵 Filtros de audio:
  - Reverb (eco/reverberación)
  - Phone (llamada telefónica)
  - Pitch Up (+5 semitonos)
  - Pitch Down (-5 semitonos)
  - Muffled (voz apagada)
  - Robot (voz robótica)
  - Distortion (saturación)
- 🌳 Filtros de fondo:
  - Calle (tráfico urbano)
  - Lluvia
  - Multitud (restaurante/público)
  - Naturaleza (viento/playa)
  - Personalizado (definido por usuario)
- 🔊 Sistema de efectos de sonido integrado
- 💻 Interfaz gráfica con PySide6/Qt6
- 🎨 Splash screen animado con:
  - Logo personalizado
  - Barra de progreso
  - Etapas de carga
  - Texto con contorno blanco
- 🍎 Scripts optimizados para macOS (.sh):
  - `run_nopolo_gui.sh` (solo interfaz)
  - `run_nopolo_api.sh` (solo API)
  - `run_nopolo_full.sh` (GUI + API)
- 🎮 Detección automática de GPU/CPU
- 🔥 Soporte para NVIDIA RTX:
  - RTX 30xx/40xx (CUDA 12.4)
  - RTX 50xx Blackwell (CUDA 12.8 experimental)
- 📦 Archivos requirements separados por configuración:
  - `requirements-base.txt` (común)
  - `requirements-cuda124.txt` (RTX 30xx/40xx)
  - `requirements-cuda128.txt` (RTX 50xx)
  - `requirements-cpu.txt` (sin GPU)
  - `requirements-mac.txt` (macOS)
- 📖 Documentación completa:
  - README.md actualizado
  - INSTALL.md con guías detalladas
  - RELEASE.md con instrucciones de release
- 🎭 Gestión de voces mediante interfaz:
  - Agregar/eliminar voces
  - Editar configuración
  - Escanear modelos RVC automáticamente
- 🔌 Soporte para proveedores TTS configurable
- ⚙️ Configuración mediante archivos JSON:
  - `config/voices.json`
  - `config/sounds.json`
  - `config/backgrounds.json`
  - `config/filters.json`
  - `.env` para variables de entorno
- 🎯 Overlay para OBS (texto en tiempo real)

### Mejorado
- ⚡ Optimización para Apple Silicon (M1/M2/M3)
- 🎵 Performance de cola de audio
- 📊 Manejo de errores con logs detallados
- 🖥️ Interfaz reorganizada con pestañas:
  - Filtros
  - Sonidos
  - Fondos
- 🔊 Control de volumen independiente para efectos
- 🎨 Iconos personalizados (ventana y taskbar)
- 📱 Sección de redes sociales en GUI:
  - Ko-fi (banner clicable)
  - YouTube
  - Twitch

### Corregido
- 🐛 Problemas con MPS backend en macOS
- 🐛 Latencia en síntesis de voz
- 🐛 Gestión de memoria en GPU
- 🐛 Compatibilidad con PyTorch en diferentes versiones de CUDA
- 🐛 Icono no aparecía en barra de tareas de Windows
- 🐛 Splash screen aparecía después de cargar componentes
- 🐛 Errores de importación en macOS con fairseq
- 🐛 Problemas de encoding en archivos JSON
- 🐛 Cola de audio bloqueaba GUI

### Seguridad
- 🔒 Credenciales de Google Cloud en .env (no en código)
- 🔒 .gitignore actualizado para excluir archivos sensibles
- 🔒 Validación de entrada en API REST

## [Unreleased]

### Planeado para v1.1.0
- [ ] Módulo de entrenamiento de modelos RVC personalizados
- [ ] Optimización de latencia en síntesis
- [ ] Traducción a otros idiomas (inglés, portugués)
- [ ] Integración directa con Streamer.bot
- [ ] Configuración avanzada desde la interfaz
- [ ] Mejoramiento en entonación y naturalidad de las voces TTS
- [ ] Soporte para más providers TTS (Azure, Amazon Polly)
- [ ] Sistema de plugins para extensibilidad
- [ ] Modo offline completo (sin requerir internet)
- [ ] Compilación a binarios standalone (.exe, .app, .appimage)

### Planeado para v2.0.0
- [ ] Rediseño completo de la interfaz
- [ ] Sistema de temas personalizables
- [ ] Soporte para streaming en tiempo real
- [ ] Machine learning para mejora automática de voces
- [ ] Marketplace de voces de la comunidad
- [ ] Sincronización labial automática
- [ ] Editor de audio integrado

---

## Formato de Versiones

Este proyecto usa [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.x.x): Cambios incompatibles con versiones anteriores
- **MINOR** (x.1.x): Nueva funcionalidad compatible con versiones anteriores
- **PATCH** (x.x.1): Correcciones de bugs compatibles con versiones anteriores

## Tipos de Cambios

- **Agregado**: para nuevas características
- **Cambiado**: para cambios en funcionalidad existente
- **Obsoleto**: para características que serán eliminadas
- **Eliminado**: para características eliminadas
- **Corregido**: para corrección de bugs
- **Seguridad**: en caso de vulnerabilidades

[1.0.0]: https://github.com/tu-usuario/nopolo/releases/tag/v1.0.0

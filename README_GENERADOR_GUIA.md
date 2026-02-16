# 📖 Generador de Guía HTML - Nopolo TTS

Este generador crea automáticamente una guía HTML interactiva con todas tus voces, sonidos y fondos configurados.

## 🚀 Uso Rápido

### Opción 1: Ejecutable Standalone (Recomendado)

1. **Doble clic en:** `Generar_Guia_Nopolo.exe`
2. ¡Listo! Se generará `guia_nopolo.html` automáticamente

✅ **No requiere Python instalado**
✅ **Funciona en cualquier PC con Windows**
✅ **Se abre automáticamente en el navegador**

---

### Opción 2: Script Python

Si tienes Python instalado:

```bash
python generate_guide.py
```

---

## 📦 Compilar el Ejecutable

Si no tienes el `.exe` o quieres recompilarlo:

```bash
# Ejecutar el script de compilación
compile_guide_generator.bat

# El .exe se generará en: dist/Generar_Guia_Nopolo.exe
```

---

## 📁 Requisitos

El generador busca estos archivos:

```
proyecto/
├── Generar_Guia_Nopolo.exe  ← Ejecutable
├── config/
│   ├── voices.json          ← Configuración de voces
│   ├── sounds.json          ← Configuración de sonidos
│   └── backgrounds.json     ← Configuración de fondos
└── guia_nopolo.html         ← Se genera aquí
```

---

## ✨ Características

- 🎤 Lista todas las voces configuradas
- 🔊 Muestra todos los sonidos disponibles
- 🎵 Enumera los fondos musicales
- 📝 Sintaxis de uso con ejemplos
- 🔍 Búsqueda en tiempo real
- 🎨 Diseño moderno y responsive
- 🌐 Se abre automáticamente en el navegador

---

## 🐛 Solución de Problemas

### "No se encontró la carpeta config"

**Solución:** El `.exe` debe estar en la carpeta raíz del proyecto, al mismo nivel que la carpeta `config/`.

```
✅ Correcto:
Nopolo/
├── Generar_Guia_Nopolo.exe
└── config/

❌ Incorrecto:
Nopolo/
├── dist/
│   └── Generar_Guia_Nopolo.exe
└── config/
```

### "Error al leer JSON"

**Solución:** Verifica que los archivos JSON estén correctamente formateados:
- `config/voices.json`
- `config/sounds.json`
- `config/backgrounds.json`

### El ejecutable no se abre

**Solución:** Windows puede bloquearlo. Click derecho → Propiedades → Desbloquear

---

## 📝 Notas

- El generador lee la configuración actual de Nopolo
- Se debe ejecutar cada vez que cambien las voces/sonidos
- El archivo HTML es standalone (no requiere conexión a internet)
- Puedes compartir el HTML generado con tu comunidad

---

## 🔄 Actualizar

Si actualizas tus voces o sonidos:

1. Ejecuta de nuevo `Generar_Guia_Nopolo.exe`
2. El archivo HTML se sobreescribirá con los datos actualizados

---

**Fecha:** 2026-02-16
**Versión:** 1.0.0

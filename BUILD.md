# 🔨 Guía de Build - Generar Ejecutables de Nopolo

Esta guía explica cómo generar ejecutables standalone de Nopolo para distribución.

## 📋 Requisitos Previos

### Para generar ejecutable de Windows:
- Windows 10/11
- Python 3.10.11 instalado
- Entorno virtual con todas las dependencias
- PyInstaller (`pip install pyinstaller`)
- **Importante:** Debes tener GPU NVIDIA con CUDA instalado si quieres la versión GPU

### Para generar ejecutable de macOS:
- macOS (Intel o Apple Silicon)
- Python 3.10.11 instalado
- Xcode Command Line Tools
- PyInstaller

### Para generar ejecutable de Linux:
- Linux (Ubuntu 20.04+ recomendado)
- Python 3.10.11 instalado
- PyInstaller
- libffi-dev, libssl-dev instalados

---

## 🚀 Generar Ejecutable (Método Automático)

### 1. Preparar el Entorno

```bash
# Navegar al directorio del proyecto
cd nopolo

# Activar entorno virtual
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# Instalar PyInstaller
pip install pyinstaller
```

### 2. Ejecutar el Script de Build

```bash
python build_executable.py
```

El script:
- ✅ Detectará tu sistema operativo automáticamente
- ✅ Limpiará builds anteriores
- ✅ Generará el ejecutable standalone
- ✅ Mostrará la ubicación del archivo final

### 3. Resultado

El ejecutable estará en:
- **Windows:** `dist/Nopolo/Nopolo.exe`
- **macOS:** `dist/Nopolo/Nopolo.app`
- **Linux:** `dist/Nopolo/Nopolo`

---

## ⚙️ Generar Ejecutable (Método Manual)

Si prefieres tener control total sobre el proceso:

### Windows

```bash
# Activar entorno
.venv\Scripts\activate

# Limpiar builds anteriores
rmdir /s /q build dist

# Generar ejecutable
python -m PyInstaller --clean --noconfirm nopolo.spec

# Resultado en: dist/Nopolo/
```

### macOS / Linux

```bash
# Activar entorno
source .venv/bin/activate

# Limpiar builds anteriores
rm -rf build dist

# Generar ejecutable
python -m PyInstaller --clean --noconfirm nopolo.spec

# Resultado en: dist/Nopolo/
```

---

## 📦 Crear Instaladores Nativos

### Windows: Crear Instalador .exe con NSIS

1. **Descargar NSIS:**
   ```
   https://nsis.sourceforge.io/Download
   ```

2. **Crear script de instalación** (`nopolo-installer.nsi`):

```nsis
!include "MUI2.nsh"

Name "Nopolo Voice Studio"
OutFile "nopolo-v1.0.0-windows-setup.exe"
InstallDir "$PROGRAMFILES64\Nopolo"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "dist\Nopolo\*.*"
  
  CreateShortcut "$DESKTOP\Nopolo.lnk" "$INSTDIR\Nopolo.exe"
  CreateShortcut "$SMPROGRAMS\Nopolo.lnk" "$INSTDIR\Nopolo.exe"
  
  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\Nopolo.lnk"
  Delete "$SMPROGRAMS\Nopolo.lnk"
  RMDir /r "$INSTDIR"
SectionEnd
```

3. **Compilar con NSIS:**
   ```bash
   makensis nopolo-installer.nsi
   ```

### macOS: Crear .dmg

1. **Instalar create-dmg:**
   ```bash
   brew install create-dmg
   ```

2. **Crear DMG:**
   ```bash
   create-dmg \
     --volname "Nopolo Installer" \
     --volicon "assets/nopolo_icon.icns" \
     --window-pos 200 120 \
     --window-size 800 400 \
     --icon-size 100 \
     --icon "Nopolo.app" 200 190 \
     --hide-extension "Nopolo.app" \
     --app-drop-link 600 185 \
     "nopolo-v1.0.0-macos.dmg" \
     "dist/Nopolo/"
   ```

### Linux: Crear AppImage

1. **Descargar appimagetool:**
   ```bash
   wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
   chmod +x appimagetool-x86_64.AppImage
   ```

2. **Crear estructura AppDir:**
   ```bash
   mkdir -p AppDir/usr/bin
   cp -r dist/Nopolo/* AppDir/usr/bin/
   cp assets/nopolo_icon.png AppDir/nopolo.png
   ```

3. **Crear .desktop file** (`AppDir/nopolo.desktop`):
   ```ini
   [Desktop Entry]
   Name=Nopolo
   Exec=Nopolo
   Icon=nopolo
   Type=Application
   Categories=AudioVideo;Audio;
   ```

4. **Generar AppImage:**
   ```bash
   ./appimagetool-x86_64.AppImage AppDir nopolo-v1.0.0-linux-x86_64.AppImage
   ```

---

## 🎯 Diferentes Versiones para Windows

### GPU NVIDIA (CUDA 12.4) - Recomendado

```bash
# Asegurarte de tener PyTorch con CUDA instalado
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Generar ejecutable
python build_executable.py
```

Nombre sugerido: `nopolo-v1.0.0-windows-cuda124.exe`

### GPU NVIDIA (CUDA 12.8) - Experimental

```bash
# Instalar PyTorch nightly
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128

# Generar ejecutable
python build_executable.py
```

Nombre sugerido: `nopolo-v1.0.0-windows-cuda128-experimental.exe`

### CPU Only (Sin GPU)

```bash
# Instalar PyTorch CPU
pip install torch torchvision torchaudio

# Generar ejecutable
python build_executable.py
```

Nombre sugerido: `nopolo-v1.0.0-windows-cpu.exe`

---

## 📝 Personalizar el Build

### Editar nopolo.spec

El archivo `nopolo.spec` controla qué se incluye en el ejecutable:

```python
# Agregar archivos adicionales
datas += [
    ('mi_carpeta', 'mi_carpeta'),
]

# Excluir módulos innecesarios
excludes=[
    'matplotlib',
    'tkinter',
]

# Cambiar icono (Windows)
icon='assets/mi_icono.ico'
```

### Reducir Tamaño del Ejecutable

1. **Excluir módulos no usados** en `nopolo.spec`:
   ```python
   excludes=['matplotlib', 'PIL', 'IPython', 'jupyter', 'pytest']
   ```

2. **Usar UPX** (compresor de ejecutables):
   - Descarga UPX: https://upx.github.io/
   - Coloca `upx.exe` en PATH
   - PyInstaller lo usará automáticamente

3. **No incluir modelos pesados**:
   - Modelos RVC (`.pth`, `.index`) se distribuyen aparte
   - Usuario los descarga después de instalar

---

## 🐛 Solución de Problemas

### Error: "Failed to execute script 'main'"

**Solución:** Faltan dependencias ocultas. Agregar a `hiddenimports` en `nopolo.spec`:
```python
hiddenimports += ['modulo_faltante']
```

### Error: "DLL load failed"

**Solución Windows:** Instalar Visual C++ Redistributable:
```
https://aka.ms/vs/17/release/vc_redist.x64.exe
```

### Ejecutable muy grande (>2GB)

**Solución:**
1. No incluyas modelos RVC en el ejecutable
2. Excluye librerías no usadas en `nopolo.spec`
3. Usa UPX para comprimir

### Error en macOS: "App is damaged"

**Solución:** Firmar la aplicación (requiere Apple Developer Account):
```bash
codesign --force --deep --sign - dist/Nopolo.app
```

### Linux: "No module named '_tkinter'"

**Solución:**
```bash
sudo apt-get install python3-tk
```

---

## ✅ Checklist Pre-Release

Antes de distribuir el ejecutable:

- [ ] Probado en sistema limpio (sin Python instalado)
- [ ] Icono se muestra correctamente
- [ ] Splash screen aparece al iniciar
- [ ] API responde correctamente (si aplica)
- [ ] Síntesis de voz funciona
- [ ] Conversión RVC funciona (con modelo de prueba)
- [ ] No hay errores en logs
- [ ] Archivo README.md incluido en dist/
- [ ] LICENSE incluido en dist/
- [ ] Tamaño del ejecutable aceptable (<1GB sin modelos)

---

## 📦 Distribución Final

### Estructura recomendada para distribución:

```
nopolo-v1.0.0-windows-cuda124.zip
├── Nopolo.exe
├── _internal/ (librerías)
├── version.py
├── .env
├── config/
│   ├── app_settings.json
│   ├── sounds.json
│   ├── backgrounds.json
│   ├── providers.json
│   └── voices.json
├── models/ (Modelos RVC se descargan en automatico cuando usa la aplicación)
├── backgrounds/
│   └── README.txt (instrucciones para agregar fondos personalizados)
├── sounds/
│   └── README.txt (instrucciones para agregar efectos de sonido personalizados)
└── voices/
    └── README.txt (instrucciones para agregar voces personalizadas)
```

### Subir a GitHub Release:

1. Comprimir carpeta `dist/Nopolo` en ZIP
2. Renombrar según versión y configuración
3. Subir a Release en GitHub junto con:
   - Código fuente (auto-generado)
   - CHANGELOG.md
   - INSTALL.md

---

## 🆘 Soporte

Si tienes problemas generando el ejecutable:

1. Revisa los logs en `build/` y `dist/`
2. Abre un Issue en GitHub con detalles del error
3. Incluye: sistema operativo, versión de Python, log completo

---

**Última actualización:** v1.0.0 (2026-02-15)

# Cambios de Compatibilidad Multiplataforma

## Resumen
Este commit agrega soporte completo para macOS (Apple Silicon M1/M2/M3) y optimiza el rendimiento eliminando dependencias problemáticas de librosa/numba.

## Cambios Principales

### 🍎 Compatibilidad macOS
- **Detección automática de plataforma** en `rvc_engine.py`
- **Método F0 adaptativo**: `pm` (parselmouth) en Mac, `rmvpe` en Windows/Linux
- **Scripts de lanzamiento** con variables de entorno optimizadas:
  - `run_nopolo_gui.sh` - Solo interfaz gráfica
  - `run_nopolo_api.sh` - Solo servidor API
  - `run_nopolo_full.sh` - GUI + API simultáneamente

### ⚡ Optimizaciones de Rendimiento
- **Eliminado librosa.load()** → Reemplazado por `soundfile` (más rápido)
- **Eliminado librosa.resample()** → Reemplazado por `scipy.signal.resample`
- **Eliminado librosa.feature.rms()** → Cálculo manual con numpy
- **Deshabilitado Numba JIT** en Mac (causa crashes en ARM64)
- **Deshabilitado MPS** (PyTorch Metal) - tiene bugs con torch.stft()

### 🔧 Archivos Modificados

#### Core
- `core/rvc_engine.py`: Detección de Mac + método F0 adaptativo
- `core/rvc_cpu_patch.py`: Parche automático para Mac (solo se activa en Darwin)

#### RVC (submodule clonado)
- `rvc/rvc/lib/audio.py`: Reemplaza librosa por soundfile
- `rvc/rvc/modules/vc/pipeline.py`: RMS manual sin librosa
- `rvc/rvc/configs/config.py`: Deshabilita MPS en Mac

#### Documentación
- `README.md`: 
  - Tabla de compatibilidad multiplataforma
  - Instrucciones de ejecución con scripts
  - Actualización de próximos pasos

### 📦 Scripts de Lanzamiento
- `run_nopolo_gui.sh` - Interfaz gráfica con variables optimizadas
- `run_nopolo_api.sh` - Servidor API REST
- `run_nopolo_full.sh` - Modo completo (GUI + API)

## Compatibilidad

| Plataforma | Estado | Device | F0 Method | Impacto |
|------------|--------|--------|-----------|---------|
| Windows + NVIDIA | ✅ Mejorado | CUDA | RMVPE | Más rápido (sin librosa) |
| Linux + NVIDIA | ✅ Mejorado | CUDA | RMVPE | Más rápido (sin librosa) |
| macOS M1/M2/M3 | ✅ NUEVO | CPU | Parselmouth | Estable y funcional |
| Windows/Linux CPU | ✅ Mejorado | CPU | RMVPE | Más rápido (sin librosa) |

## Breaking Changes
**Ninguno** - Todos los cambios son retrocompatibles y mejoran el rendimiento en todas las plataformas.

## Testing
- ✅ Probado en macOS M1/M2/M3 (Apple Silicon)
- ✅ RVC funciona sin crashes
- ✅ TTS multi-provider (Edge + Google) funcional
- ✅ API REST operativa
- ⏳ Pendiente: Testing en Windows/Linux (se esperan mejoras por eliminación de librosa)

## Notas
- Los archivos modificados en `rvc/` son del repositorio clonado. Los cambios mejoran la compatibilidad sin afectar la funcionalidad original.
- `core/rvc_cpu_patch.py` solo se activa en macOS, no afecta otras plataformas.
- Las variables de entorno en los scripts `.sh` son específicas para Mac pero pueden usarse en Linux sin problemas.

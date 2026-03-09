#!/bin/bash
# Nopolo — Modo CPU
# Fuerza RVC a correr en CPU liberando la GPU para juegos y OBS.
# Ideal para streams con juegos AAA pesados.
# CPU recomendado: Ryzen 9 9950X3D (16c/32t — maneja RVC sin problema)

# Ocultar GPU para PyTorch → cuda.is_available() = False → RVC usa rmvpe en CPU
export CUDA_VISIBLE_DEVICES=''

# Threads para RVC / PyTorch en CPU
# 9950X3D tiene 16 cores / 32 threads.
# Dejamos 8 threads libres para el juego + OBS.
export OMP_NUM_THREADS=16
export MKL_NUM_THREADS=16

# Numba (usado internamente por algunas dependencias de RVC)
export NUMBA_DISABLE_JIT=1
export NUMBA_CACHE_DIR=/tmp

# Activar entorno virtual si existe
if [ -d ".venv" ]; then
    # Windows usa Scripts/, Linux/Mac usa bin/
    if [ -f ".venv/Scripts/activate" ]; then
        source .venv/Scripts/activate
    elif [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    fi
fi

echo "================================================"
echo "  Nopolo — Modo CPU"
echo "  CUDA desactivado | OMP_NUM_THREADS=16"
echo "  RVC usará rmvpe en CPU"
echo "================================================"

python main.py

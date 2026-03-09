#!/bin/bash
# Nopolo API Server Launcher
# Ejecuta solo el servidor REST API (sin interfaz gráfica)

# Variables de entorno para Mac (evitan problemas con MPS y Numba)
export NUMBA_DISABLE_JIT=1
export NUMBA_CACHE_DIR=/tmp
export PYTORCH_ENABLE_MPS_FALLBACK=0
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4

# Activar entorno virtual si existe
if [ -d ".venv" ]; then
    if [ -f ".venv/Scripts/activate" ]; then
        source .venv/Scripts/activate
    elif [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    fi
fi

# Ejecutar solo API Server
echo "=================================================="
echo "Nopolo API Server"
echo "Documentación: http://localhost:8000/docs"
echo "=================================================="
python3 main.py --no-gui

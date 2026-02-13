#!/bin/bash
# Nopolo Full Launcher
# Ejecuta GUI + API Server simultáneamente

# Variables de entorno para Mac (evitan problemas con MPS y Numba)
export NUMBA_DISABLE_JIT=1
export NUMBA_CACHE_DIR=/tmp
export PYTORCH_ENABLE_MPS_FALLBACK=0
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4

# Activar entorno virtual si existe
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Ejecutar GUI + API Server
echo "=================================================="
echo "Nopolo - Modo Completo (GUI + API)"
echo "Documentación API: http://localhost:8000/docs"
echo "=================================================="
python3 main.py --with-api

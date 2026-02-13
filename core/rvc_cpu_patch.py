"""
Parche CRÍTICO para forzar CPU y deshabilitar funciones problemáticas en Mac.
DEBE importarse ANTES que cualquier módulo de RVC.

Problemas en Mac ARM64 (M1/M2/M3):
1. PyTorch MPS tiene bugs con torch.stft() → segfault
2. Numba JIT compilation crashea en fairseq → segfault
3. Hubert model loading con MPS → inestable

Soluciones:
1. Forzar CPU para PyTorch
2. Deshabilitar Numba JIT
3. Variables de entorno para estabilidad
"""

import os
import sys

def force_cpu_for_rvc():
    """
    Fuerza CPU y deshabilita optimizaciones problemáticas.
    Debe llamarse ANTES de importar rvc, torch, fairseq.
    """
    
    # 1. Deshabilitar Numba JIT (causa segfault en Mac ARM64)
    os.environ['NUMBA_DISABLE_JIT'] = '1'
    os.environ['NUMBA_CACHE_DIR'] = '/tmp'
    print("🔧 Numba JIT deshabilitado (evita segfault en Mac)")
    
    # 2. Variables de entorno para PyTorch
    os.environ['CUDA_VISIBLE_DEVICES'] = ''  # Sin CUDA
    os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '0'  # Deshabilitar MPS
    os.environ['OMP_NUM_THREADS'] = '1'  # Single thread para estabilidad
    
    # 3. Forzar device='cpu' en PyTorch
    import torch
    
    # Deshabilitar MPS completamente
    if hasattr(torch.backends, 'mps'):
        # Monkey-patch para que is_available() siempre retorne False
        torch.backends.mps.is_available = lambda: False
        print("🔧 MPS deshabilitado - RVC usará CPU")
    
    # 4. Establecer device por defecto
    torch.set_default_device('cpu')
    torch.set_default_dtype(torch.float32)
    
    # 5. Deshabilitar warnings molestos
    import warnings
    warnings.filterwarnings('ignore', category=FutureWarning)
    warnings.filterwarnings('ignore', category=UserWarning)
    
    print("✅ CPU forzado para RVC (Mac optimizado)")

# Ejecutar automáticamente al importar este módulo
force_cpu_for_rvc()

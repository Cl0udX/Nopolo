import sys
import os
import tempfile
import numpy as np

# CRÍTICO: Importar parche ANTES de torch, fairseq, RVC
# Esto deshabilita Numba JIT y MPS que causan segfault en Mac
import platform
if platform.system() == "Darwin":  # Solo en Mac
    from . import rvc_cpu_patch

import torch
import librosa
import soundfile as sf
from pathlib import Path
from scipy.io import wavfile
from typing import Optional

# Agregar RVC al path de Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'rvc'))

from rvc.modules.vc.modules import VC
from .models import RVCConfig


class RVCEngine:
    """
    Motor RVC configurable para transformación de voces.
    Soporta múltiples modelos y configuraciones.
    """
    
    def __init__(self, config: Optional[RVCConfig] = None):
        """
        Inicializa el engine RVC.
        
        Args:
            config: Configuración del modelo RVC. Si es None, se debe cargar después.
        """
        # Configurar variables de entorno para RVC
        os.environ['index_root'] = 'voices'
        os.environ['weight_root'] = 'voices'
        
        # Descargar y configurar modelos base (Hubert, RMVPE)
        self.hubert_path = self._setup_hubert()
        os.environ['hubert_path'] = self.hubert_path
        
        self.rmvpe_path = self._setup_rmvpe()
        os.environ['rmvpe_root'] = os.path.dirname(self.rmvpe_path)
        
        # Inicializar VC (ya usa CPU por el parche en imports)
        self.vc = VC()
        
        self.config: Optional[RVCConfig] = None
        self.model_loaded = False
        self.index_path = None
        
        # Cargar modelo si se proporcionó config
        if config:
            self.load_model(config)
    
    def load_model(self, config: RVCConfig):
        """Carga un modelo RVC específico usando get_vc()"""
        print(f"🎙️ Cargando modelo RVC: {config.name}...")
        
        self.config = config
        
        # get_vc() carga el modelo internamente en self.vc
        # Solo necesitamos pasarle la ruta del modelo
        self.vc.get_vc(config.model_path)
        
        # Guardar index_path (convertir a absoluto si es relativo)
        if config.index_path:
            index_path = config.index_path
            print(f"📋 Index path del config: {index_path}")
            
            if not os.path.isabs(index_path):
                index_path = os.path.abspath(index_path)
                print(f"📋 Convertido a absoluto: {index_path}")
            
            if os.path.exists(index_path):
                self.index_path = index_path
                print(f"✅ Index encontrado: {os.path.basename(index_path)}")
            else:
                self.index_path = None
                print(f"⚠️ Index no encontrado en: {index_path}")
        else:
            self.index_path = None
            print("ℹ️ Sin index (config.index_path es None o vacío)")
        
        self.model_loaded = True
        
        print(f"✅ Modelo RVC cargado: {config.name}")
    
    def _setup_hubert(self):
        """Descargar modelo Hubert si no existe"""
        hubert_dir = "models"
        hubert_path = os.path.join(hubert_dir, "hubert_base.pt")
        
        if os.path.exists(hubert_path):
            print("Modelo Hubert encontrado")
            return hubert_path
        
        os.makedirs(hubert_dir, exist_ok=True)
        
        print("Descargando modelo Hubert (tamaño ~200MB)...")
        import urllib.request
        url = "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/hubert_base.pt"
        
        try:
            urllib.request.urlretrieve(url, hubert_path)
            print("Modelo Hubert descargado")
            return hubert_path
        except Exception as e:
            print(f"Error descargando Hubert: {e}")
            raise
    
    def _setup_rmvpe(self):
        """Descargar modelo RMVPE si no existe (solo si no es Mac)"""
        import platform
        
        # En Mac usamos 'pm' en lugar de RMVPE
        if platform.system() == "Darwin":
            print("🍎 Mac detectado - RMVPE no necesario (se usará 'pm')")
            # Crear directorio vacío para que RVC no falle
            os.makedirs("models", exist_ok=True)
            return os.path.join("models", "rmvpe_dummy.pt")  # Path dummy
        
        rmvpe_dir = "models"
        rmvpe_path = os.path.join(rmvpe_dir, "rmvpe.pt")
        
        if os.path.exists(rmvpe_path):
            print("Modelo RMVPE encontrado")
            return rmvpe_path
        
        os.makedirs(rmvpe_dir, exist_ok=True)
        
        print("Descargando modelo RMVPE (tamaño ~60MB)...")
        import urllib.request
        url = "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/rmvpe.pt"
        
        try:
            urllib.request.urlretrieve(url, rmvpe_path)
            print("Modelo RMVPE descargado")
            return rmvpe_path
        except Exception as e:
            print(f"Error descargando RMVPE: {e}")
            raise
    
    def convert(self, input_wav_path: str, config_override: Optional[RVCConfig] = None) -> tuple:
        """
        Convierte audio usando el modelo RVC cargado.
        
        Args:
            input_wav_path: Ruta al archivo WAV de entrada
            config_override: Configuración temporal (opcional)
        
        Returns:
            Tupla (audio_data, sample_rate)
        """
        if not self.model_loaded:
            raise RuntimeError("No hay modelo RVC cargado. Usa load_model() primero.")
        
        config = config_override or self.config
        
        try:
            print(f"🔄 Convirtiendo voz con RVC ({config.name})...")
            
            # Preparar index path (usar self.index_path que ya fue validado en load_model)
            index_file = self.index_path if self.index_path else None
            
            if index_file:
                print(f"📋 Usando index: {os.path.basename(index_file)}")
            else:
                print("ℹ️ Sin index file")
            
            # IMPORTANTE: Detectar plataforma y elegir método F0 apropiado
            # RMVPE tiene bugs en MPS (Mac), usamos 'pm' (parselmouth) en su lugar
            import platform
            f0_method = "pm" if platform.system() == "Darwin" else "rmvpe"
            
            if platform.system() == "Darwin":
                print("🍎 Mac detectado - usando 'pm' en lugar de 'rmvpe' (más estable)")
            
            # Usar el método vc_inference con keyword arguments para mayor claridad
            tgt_sr, audio_opt, times, _ = self.vc.vc_inference(
                sid=1,  # speaker id
                input_audio_path=input_wav_path,
                f0_up_key=config.pitch_shift,
                f0_method=f0_method,  # 'pm' en Mac, 'rmvpe' en otros
                f0_file=None,  # No usamos archivo F0 externo
                index_file=index_file,  # Path al index o None
                index_rate=config.index_rate,
                filter_radius=config.filter_radius,
                rms_mix_rate=config.rms_mix_rate,
                protect=config.protect
            )
            
            # Validar resultado
            if audio_opt is None or tgt_sr is None:
                raise RuntimeError("RVC retornó None - revisar configuración de pitch/modelo")
            
            total_time = sum(times.values()) if times else 0
            print(f"✅ Conversión RVC exitosa ({total_time:.2f}s, SR: {tgt_sr} Hz)")
            
            # Limpiar cache de MPS después de procesar
            self._cleanup_memory()
            
            # Retornar como tupla (wav_data, rate)
            return (audio_opt.astype(np.float32) / 32768.0, tgt_sr)
            
        except Exception as e:
            print(f"❌ Error en conversión RVC: {e}")
            print(f"   Tipo: {type(e).__name__}")
            
            # Limpiar memoria
            self._cleanup_memory(force=True)
            
            # Re-lanzar la excepción
            raise
            
        finally:
            # Limpiar archivo temporal creado por edge-tts
            if os.path.exists(input_wav_path):
                try:
                    os.unlink(input_wav_path)
                except:
                    pass  # Ignorar si no se puede eliminar
    
    def _cleanup_memory(self, force=False):
        """
        Limpia cache de GPU/MPS después de cada conversión.
        
        Args:
            force: Si es True, hace limpieza agresiva (gc.collect + empty_cache)
        """
        try:
            # Limpiar cache de MPS (Apple Silicon)
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
                if force:
                    print("🧹 Limpieza agresiva de cache MPS")
                else:
                    print("🧹 Cache MPS limpiado")
            
            # Limpiar cache de CUDA (si existe)
            elif torch.cuda.is_available():
                torch.cuda.empty_cache()
                if force:
                    print("🧹 Limpieza agresiva de cache CUDA")
                else:
                    print("🧹 Cache CUDA limpiado")
            
            # Recolección de basura forzada si se pidió
            if force:
                import gc
                gc.collect()
                print("🧹 Garbage collector ejecutado")
                
        except Exception as e:
            # No fallar si la limpieza falla
            print(f"⚠️ Error limpiando memoria (no crítico): {e}")
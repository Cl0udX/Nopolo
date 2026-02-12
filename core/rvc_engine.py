import sys
import os
import tempfile
import numpy as np
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
        
        # Inicializar VC
        self.vc = VC()
        self.config: Optional[RVCConfig] = None
        self.model_loaded = False
        
        # Cargar modelo si se proporcionó config
        if config:
            self.load_model(config)
    
    def load_model(self, config: RVCConfig):
        """
        Carga un modelo RVC específico.
        
        Args:
            config: Configuración del modelo a cargar
        """
        try:
            config.validate()
            print(f"Cargando modelo RVC: {config.name}...")
            self.vc.get_vc(config.model_path)
            self.config = config
            self.model_loaded = True
            print(f"Modelo RVC cargado: {config.name}")
        except Exception as e:
            print(f"Error cargando modelo RVC: {e}")
            raise
    
    def _setup_hubert(self):
        """Descargar modelo Hubert si no existe"""
        hubert_dir = "models"
        hubert_path = os.path.join(hubert_dir, "hubert_base.pt")
        
        if os.path.exists(hubert_path):
            print("✅ Modelo Hubert encontrado")
            return hubert_path
        
        os.makedirs(hubert_dir, exist_ok=True)
        
        print("📥 Descargando modelo Hubert (tamaño ~200MB)...")
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
        """Descargar modelo RMVPE si no existe"""
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
            print(f"Convirtiendo voz con RVC ({config.name})...")
            
            tgt_sr, audio_opt, times, _ = self.vc.vc_inference(
                sid=1,
                input_audio_path=input_wav_path,
                f0_up_key=config.pitch_shift,
                f0_method=config.f0_method,
                index_file=config.index_path,
                index_rate=config.index_rate,
                filter_radius=config.filter_radius,
                resample_sr=config.resample_sr,
                rms_mix_rate=config.rms_mix_rate,
                protect=config.protect
            )
            
            total_time = sum(times.values()) if times else 0
            print(f"Conversión RVC exitosa ({total_time:.2f}s)")
            
            # Retornar como tupla (wav_data, rate)
            return (audio_opt.astype(np.float32) / 32768.0, tgt_sr)
            
        finally:
            # Limpiar archivo temporal creado por edge-tts
            if os.path.exists(input_wav_path):
                os.unlink(input_wav_path)
import sys
import os
import tempfile
import numpy as np
from pathlib import Path
from scipy.io import wavfile

# Agregar RVC al path de Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'rvc'))

from rvc.modules.vc.modules import VC

class RVCEngine:
    def __init__(self):
        # Configurar variables de entorno para RVC
        os.environ['index_root'] = 'voices'
        os.environ['weight_root'] = 'voices'
        
        # Descargar y configurar modelos
        self.hubert_path = self._setup_hubert()
        os.environ['hubert_path'] = self.hubert_path
        
        self.rmvpe_path = self._setup_rmvpe()
        os.environ['rmvpe_root'] = os.path.dirname(self.rmvpe_path)
        
        self.model_path = "voices/homero/homero.pth"
        self.vc = VC()
        print("🎙️ Cargando modelo RVC...")
        self.vc.get_vc(self.model_path)
        print("✅ Modelo RVC cargado")
    
    def _setup_hubert(self):
        """Descargar modelo Hubert si no existe"""
        hubert_dir = "models"
        hubert_path = os.path.join(hubert_dir, "hubert_base.pt")
        
        if os.path.exists(hubert_path):
            print("✅ Modelo Hubert encontrado")
            return hubert_path
        
        # Crear directorio si no existe
        os.makedirs(hubert_dir, exist_ok=True)
        
        # Descargar desde HuggingFace
        print("📥 Descargando modelo Hubert (tamaño ~200MB)...")
        import urllib.request
        url = "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/hubert_base.pt"
        
        try:
            urllib.request.urlretrieve(url, hubert_path)
            print("✅ Modelo Hubert descargado")
            return hubert_path
        except Exception as e:
            print(f"❌ Error descargando Hubert: {e}")
            raise
    
    def _setup_rmvpe(self):
        """Descargar modelo RMVPE si no existe"""
        rmvpe_dir = "models"
        rmvpe_path = os.path.join(rmvpe_dir, "rmvpe.pt")
        
        if os.path.exists(rmvpe_path):
            print("✅ Modelo RMVPE encontrado")
            return rmvpe_path
        
        # Crear directorio si no existe
        os.makedirs(rmvpe_dir, exist_ok=True)
        
        # Descargar desde HuggingFace
        print("📥 Descargando modelo RMVPE (tamaño ~60MB)...")
        import urllib.request
        url = "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/rmvpe.pt"
        
        try:
            urllib.request.urlretrieve(url, rmvpe_path)
            print("✅ Modelo RMVPE descargado")
            return rmvpe_path
        except Exception as e:
            print(f"❌ Error descargando RMVPE: {e}")
            raise

    def convert(self, input_wav_path):
        # input_wav_path es la ruta del archivo WAV generado por edge-tts
        try:
            # Ejecutar inferencia RVC directamente con el archivo
            print("🔄 Convirtiendo voz con RVC...")
            tgt_sr, audio_opt, times, _ = self.vc.vc_inference(
                1,  # sid (speaker id, generalmente 0 o 1)
                input_wav_path  # Pasar string directamente, no Path()
            )
            total_time = sum(times.values()) if times else 0
            print(f"✅ Conversión RVC exitosa ({total_time:.2f}s)")
            
            # Retornar como tupla (wav_data, rate) para mantener compatibilidad
            return (audio_opt.astype(np.float32) / 32768.0, tgt_sr)
            
        finally:
            # Limpiar archivo temporal creado por edge-tts
            if os.path.exists(input_wav_path):
                os.unlink(input_wav_path)

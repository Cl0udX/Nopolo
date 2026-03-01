"""
RVC Engine aislado en proceso separado para evitar heap corruption.

El problema: RVC usa librerías nativas (FAISS, PyTorch, CUDA) que pueden
corromper el heap de Windows cuando se usan desde múltiples threads.

La solución: Ejecutar cada conversión RVC en un proceso separado que tiene
su propio espacio de memoria aislado.
"""
import multiprocessing as mp
import numpy as np
import os
import tempfile
import soundfile as sf
from typing import Optional, Tuple
import json


def _process_message_isolated(message: str, voices_config: dict) -> Tuple[Optional[bytes], Optional[int]]:
    """
    Procesa un mensaje completo en un proceso SEPARADO.
    
    Esto incluye TTS + RVC + filtros, todo aislado del proceso principal.
    Al terminar, TODA la memoria (incluyendo CUDA) se libera automáticamente.
    
    Args:
        message: Mensaje con formato Mopolo
        voices_config: Configuración de voces serializada (JSON)
        
    Returns:
        Tupla (audio_bytes, sample_rate) o (None, None) si falla
        NOTA: Retorna bytes para evitar problemas con numpy arrays compartidos
    """
    try:
        import sys
        import os
        import gc
        import io
        
        # Configurar paths
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, base_dir)
        
        # Configurar variables de entorno para RVC
        os.environ['index_root'] = os.path.join(base_dir, 'voices')
        os.environ['weight_root'] = os.path.join(base_dir, 'voices')
        
        # Importar módulos DENTRO del proceso hijo
        from core.voice_manager import VoiceManager
        from core.tts_engine import TTSEngine
        from core.rvc_engine import RVCEngine
        from core.advanced_processor import AdvancedAudioProcessor
        from core.models import EdgeTTSConfig
        import soundfile as sf
        
        print(f"[Isolated Process] Procesando: {message[:50]}...")
        
        # Crear VoiceManager
        voice_manager = VoiceManager()
        
        # Crear engines
        edge_config = EdgeTTSConfig()
        tts_engine = TTSEngine(config=edge_config, provider_name='edge_tts')
        rvc_engine = RVCEngine()
        
        # Crear procesador
        processor = AdvancedAudioProcessor(
            voice_manager=voice_manager,
            tts_engine=tts_engine,
            rvc_engine=rvc_engine
        )
        
        # Procesar mensaje
        audio_data, sample_rate = processor.process_message(message)
        
        # Serializar a bytes (WAV) para evitar problemas con numpy arrays
        buffer = io.BytesIO()
        sf.write(buffer, audio_data, sample_rate, format='WAV')
        audio_bytes = buffer.getvalue()
        
        # Limpiar referencias grandes
        del audio_data
        del processor
        del rvc_engine
        del tts_engine
        del voice_manager
        
        # Limpiar CUDA
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
        except:
            pass
        
        # GC final
        gc.collect()
        
        print(f"[Isolated Process] Audio generado: {len(audio_bytes)} bytes")
        
        return (audio_bytes, sample_rate)
        
    except Exception as e:
        print(f"[Isolated Process] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return (None, None)


def _rvc_convert_in_process(model_path: str, index_path: str, input_wav_path: str,
                            pitch_shift: int, index_rate: float, 
                            filter_radius: int, rms_mix_rate: float,
                            protect: float) -> Tuple[Optional[np.ndarray], Optional[int]]:
    """
    Función que se ejecuta en un proceso SEPARADO para convertir audio con RVC.
    
    Al estar en un proceso separado, toda la memoria usada por RVC (FAISS, PyTorch, CUDA)
    se libera completamente cuando el proceso termina.
    """
    try:
        # Importar DENTRO del proceso hijo
        import sys
        import os
        
        # Configurar variables de entorno para RVC
        os.environ['index_root'] = 'voices'
        os.environ['weight_root'] = 'voices'
        
        # Agregar RVC al path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'rvc'))
        
        from rvc.modules.vc.modules import VC
        import torch
        import platform
        
        # Detectar método F0 (igual que rvc_engine.py)
        if platform.system() == 'Darwin':
            f0_method = 'pm'
        elif torch.cuda.is_available():
            f0_method = 'fcpe'
        else:
            f0_method = 'rmvpe'
        
        # Crear VC
        vc = VC()
        
        # Cargar modelo
        vc.get_vc(model_path)
        
        # Convertir
        tgt_sr, audio_opt, times, _ = vc.vc_inference(
            sid=1,
            input_audio_path=input_wav_path,
            f0_up_key=pitch_shift,
            f0_method=f0_method,
            f0_file=None,
            index_file=index_path if index_path and os.path.exists(index_path) else None,
            index_rate=index_rate,
            filter_radius=filter_radius,
            rms_mix_rate=rms_mix_rate,
            protect=protect
        )
        
        # Limpiar CUDA
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        
        # Retornar audio
        if audio_opt is not None and tgt_sr is not None:
            return (audio_opt.astype(np.float32) / 32768.0, tgt_sr)
        else:
            return (None, None)
            
    except Exception as e:
        print(f"[RVC Isolated] Error: {e}")
        return (None, None)


class RVCIsolatedEngine:
    """
    Motor RVC que ejecuta cada conversión en un proceso separado.
    
    Esto previene heap corruption porque:
    1. Cada conversión tiene su propio espacio de memoria
    2. Al terminar el proceso, TODA la memoria se libera (incluyendo CUDA)
    3. No hay acumulación de recursos entre conversiones
    """
    
    def __init__(self):
        self.model_path = None
        self.index_path = None
        self.config = None
        self.model_loaded = False
    
    def load_model(self, config):
        """Guarda la configuración del modelo (no carga nada todavía)"""
        self.config = config
        self.model_path = config.model_path
        self.index_path = config.index_path
        self.model_loaded = True
        print(f"[RVC Isolated] Configuración guardada: {config.name}")
    
    def convert(self, input_wav_path: str) -> Tuple[np.ndarray, int]:
        """
        Convierte audio ejecutando RVC en un proceso separado.
        
        Returns:
            Tupla (audio_data, sample_rate)
        """
        if not self.model_loaded:
            raise RuntimeError("No hay modelo RVC configurado")
        
        print(f"[RVC Isolated] Iniciando conversión en proceso separado...")
        
        # Crear un pool con 1 worker
        ctx = mp.get_context('spawn')  # Usar spawn para Windows
        with ctx.Pool(processes=1) as pool:
            # Ejecutar en proceso separado
            result = pool.apply(
                _rvc_convert_in_process,
                args=(
                    self.model_path,
                    self.index_path,
                    input_wav_path,
                    self.config.pitch_shift,
                    self.config.index_rate,
                    self.config.filter_radius,
                    self.config.rms_mix_rate,
                    self.config.protect
                )
            )
        
        audio_data, sample_rate = result
        
        if audio_data is None:
            raise RuntimeError("RVC falló - revisar configuración")
        
        print(f"[RVC Isolated] Conversión exitosa (SR: {sample_rate} Hz)")
        
        return (audio_data, sample_rate)
    
    def emergency_cleanup(self):
        """No necesita cleanup - cada proceso se limpia solo"""
        print("[RVC Isolated] Cleanup no necesario (procesos aislados)")


class IsolatedProcessor:
    """
    Procesador que ejecuta TODO el procesamiento de mensajes en un proceso separado.
    
    Esto incluye: TTS + RVC + Filtros + Sonidos
    
    Ventajas:
    1. Aislamiento COMPLETO - el proceso principal nunca toca RVC/CUDA
    2. Memoria liberada automáticamente al terminar cada solicitud
    3. Un crash en RVC no afecta el proceso principal
    """
    
    def __init__(self, voice_manager):
        """
        Args:
            voice_manager: VoiceManager del proceso principal (solo para referencia)
        """
        self.voice_manager = voice_manager
    
    def process_message(self, message: str) -> Tuple[np.ndarray, int]:
        """
        Procesa un mensaje en un proceso SEPARADO.
        
        Args:
            message: Mensaje con formato Mopolo
            
        Returns:
            Tupla (audio_data, sample_rate)
        """
        import io
        
        print(f"[IsolatedProcessor] Iniciando procesamiento aislado...")
        
        # Serializar configuración de voces (si es necesario)
        voices_config = {}  # Por ahora vacío, VoiceManager se crea en el proceso hijo
        
        # Crear pool con 1 worker
        ctx = mp.get_context('spawn')
        with ctx.Pool(processes=1) as pool:
            result = pool.apply(
                _process_message_isolated,
                args=(message, voices_config)
            )
        
        audio_bytes, sample_rate = result
        
        if audio_bytes is None:
            raise RuntimeError("Procesamiento aislado falló")
        
        # Deserializar bytes a numpy array
        buffer = io.BytesIO(audio_bytes)
        audio_data, sr = sf.read(buffer, dtype='float32')
        
        print(f"[IsolatedProcessor] Audio recibido: {len(audio_data)/sr:.2f}s")
        
        return (audio_data, sr)

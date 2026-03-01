"""
Procesador RVC usando subprocess para aislamiento COMPLETO.

A diferencia de multiprocessing, subprocess crea un proceso completamente
nuevo con su propio intérprete Python, sin compartir NINGÚN recurso
con el proceso padre.
"""
import subprocess
import sys
import os
import json
import tempfile
import numpy as np
import soundfile as sf
from typing import Tuple, Optional
import io


# Script que se ejecuta en el subproceso
SUBPROCESS_SCRIPT = '''
import sys
import os
import json
import io
import gc

# Configurar paths
base_dir = sys.argv[1]
sys.path.insert(0, base_dir)

# Configurar variables de entorno para RVC
os.environ['index_root'] = os.path.join(base_dir, 'voices')
os.environ['weight_root'] = os.path.join(base_dir, 'voices')

# Importar módulos
from core.voice_manager import VoiceManager
from core.tts_engine import TTSEngine
from core.rvc_engine import RVCEngine
from core.advanced_processor import AdvancedAudioProcessor
from core.models import EdgeTTSConfig
import soundfile as sf
import numpy as np

# Leer mensaje de stdin
message = sys.argv[2]

print(f"[Subprocess] Procesando: {message[:50]}...", flush=True)

try:
    # Crear componentes
    voice_manager = VoiceManager()
    edge_config = EdgeTTSConfig()
    tts_engine = TTSEngine(config=edge_config, provider_name='edge_tts')
    rvc_engine = RVCEngine()
    
    processor = AdvancedAudioProcessor(
        voice_manager=voice_manager,
        tts_engine=tts_engine,
        rvc_engine=rvc_engine
    )
    
    # Procesar mensaje
    audio_data, sample_rate = processor.process_message(message)
    
    # Verificar que el audio no esté vacío
    max_val = np.max(np.abs(audio_data))
    print(f"[Subprocess] Audio max amplitude: {max_val}", flush=True)
    
    if max_val < 0.01:
        print(f"[Subprocess] WARNING: Audio muy bajo o silencioso!", flush=True)
    
    # Serializar a WAV bytes
    buffer = io.BytesIO()
    sf.write(buffer, audio_data, sample_rate, format='WAV')
    audio_bytes = buffer.getvalue()
    
    # Limpiar
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
    
    gc.collect()
    
    # Escribir resultado a stdout como JSON
    result = {
        'success': True,
        'sample_rate': sample_rate,
        'audio_size': len(audio_bytes)
    }
    print(f"[Subprocess] Audio generado: {len(audio_bytes)} bytes, SR: {sample_rate}", flush=True)
    
    # Escribir audio a archivo temporal
    temp_file = sys.argv[3]
    with open(temp_file, 'wb') as f:
        f.write(audio_bytes)
    
    # Señal de éxito
    print("SUBPROCESS_SUCCESS", flush=True)
    
except Exception as e:
    import traceback
    print(f"[Subprocess] ERROR: {e}", flush=True)
    traceback.print_exc()
    print("SUBPROCESS_ERROR", flush=True)
    sys.exit(1)
'''


class SubprocessProcessor:
    """
    Procesador que ejecuta TODO en un subproceso completamente aislado.
    
    Usa subprocess en lugar de multiprocessing para garantizar que
    NINGÚN recurso se comparte entre procesos.
    """
    
    def __init__(self, voice_manager=None):
        """
        Args:
            voice_manager: VoiceManager (no se usa, solo para compatibilidad)
        """
        self.voice_manager = voice_manager
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def process_message(self, message: str) -> Tuple[np.ndarray, int]:
        """
        Procesa un mensaje en un subproceso completamente aislado.
        
        Args:
            message: Mensaje con formato Mopolo
            
        Returns:
            Tupla (audio_data, sample_rate)
        """
        print(f"[SubprocessProcessor] Iniciando procesamiento aislado...")
        
        # Crear archivo temporal para el audio
        temp_fd, temp_path = tempfile.mkstemp(suffix='.wav')
        os.close(temp_fd)
        
        try:
            # Ejecutar subproceso
            result = subprocess.run(
                [sys.executable, '-c', SUBPROCESS_SCRIPT, 
                 self.base_dir, message, temp_path],
                capture_output=True,
                text=True,
                timeout=120  # 2 minutos máximo
            )
            
            # Mostrar logs del subproceso
            if result.stdout:
                print(f"[SubprocessProcessor] STDOUT:\n{result.stdout}")
            if result.stderr:
                print(f"[SubprocessProcessor] STDERR:\n{result.stderr}")
            
            # Verificar resultado
            if result.returncode != 0 or 'SUBPROCESS_SUCCESS' not in result.stdout:
                raise RuntimeError("Procesamiento en subproceso falló")
            
            # Leer audio del archivo temporal
            audio_data, sample_rate = sf.read(temp_path, dtype='float32')
            
            # Verificar amplitud
            import numpy as np
            max_val = np.max(np.abs(audio_data))
            print(f"[SubprocessProcessor] Audio: {len(audio_data)/sample_rate:.2f}s, max amplitude: {max_val}")
            
            if max_val < 0.01:
                print(f"[SubprocessProcessor] WARNING: Audio muy bajo!")
            
            return (audio_data, sample_rate)
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Timeout en subproceso")
        finally:
            # Limpiar archivo temporal
            try:
                os.unlink(temp_path)
            except:
                pass
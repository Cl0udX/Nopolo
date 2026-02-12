import threading
import queue
from typing import Optional
from .tts_engine import TTSEngine
from .rvc_engine import RVCEngine
from .audio_player import play_wav
from .models import VoiceProfile


class AudioQueue:
    """
    Cola de procesamiento de audio con soporte para voces configurables.
    """
    
    def __init__(self, tts_engine: TTSEngine, rvc_engine: RVCEngine):
        self.tts_engine = tts_engine
        self.rvc_engine = rvc_engine
        self.queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        print("Cola de audio iniciada")
    
    def add(self, text: str, voice_profile: Optional[VoiceProfile] = None):
        """
        Agrega texto a la cola para procesamiento.
        
        Args:
            text: Texto a sintetizar
            voice_profile: Perfil de voz a usar (opcional)
        """
        self.queue.put((text, voice_profile))
    
    def _worker(self):
        """Worker thread que procesa la cola"""
        while True:
            text, voice_profile = self.queue.get()
            
            try:
                # Paso 1: TTS (voz neutral)
                tts_config = voice_profile.tts_config if voice_profile else None
                neutral_wav = self.tts_engine.synthesize(text, tts_config)
                
                # Paso 2: RVC (transformación opcional)
                if voice_profile and voice_profile.is_transformer_voice():
                    # Cargar modelo si es diferente
                    if (not self.rvc_engine.model_loaded or 
                        self.rvc_engine.config.model_id != voice_profile.rvc_config.model_id):
                        self.rvc_engine.load_model(voice_profile.rvc_config)
                    
                    converted_wav = self.rvc_engine.convert(neutral_wav)
                else:
                    # Sin transformación, leer el WAV generado
                    import scipy.io.wavfile as wavfile
                    rate, data = wavfile.read(neutral_wav)
                    converted_wav = (data.astype('float32') / 32768.0, rate)
                    import os
                    os.unlink(neutral_wav)  # Limpiar temporal
                
                # Paso 3: Reproducir
                play_wav(converted_wav)
                
            except Exception as e:
                print(f"Error en cola de audio: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.queue.task_done()
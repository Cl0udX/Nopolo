import threading
import queue
from typing import Optional
from .tts_engine import TTSEngine
from .rvc_engine import RVCEngine
from .audio_player import play_wav, stop_audio
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
    
    def add(self, text: str, voice_profile: Optional[VoiceProfile] = None, voice_name: str = "", main_window=None):
        """
        Agrega texto a la cola para procesamiento.
        
        Args:
            text: Texto a sintetizar
            voice_profile: Perfil de voz a usar (opcional)
            voice_name: Nombre de la voz para el overlay
            main_window: Referencia a la ventana principal para enviar eventos overlay
        """
        self.queue.put((text, voice_profile, voice_name, main_window))
    
    def stop_current(self):
        """Detiene el audio que está sonando actualmente"""
        stop_audio()
    
    def skip_to_next(self):
        """Salta al siguiente en la cola (detiene el actual)"""
        stop_audio()
    
    def clear_queue(self):
        """Limpia toda la cola de audios pendientes"""
        # Vaciar la cola
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except queue.Empty:
                break
        # Detener el actual
        stop_audio()
    
    def get_queue_size(self):
        """Retorna el número de items en la cola"""
        return self.queue.qsize()
    
    def _worker(self):
        """Worker thread que procesa la cola"""
        while True:
            text, voice_profile, voice_name, main_window = self.queue.get()
            
            try:
                # Enviar evento de inicio al overlay (modo normal = is_nopolo False)
                if main_window and hasattr(main_window, '_send_overlay_event'):
                    main_window._send_overlay_event(text, voice_name, is_nopolo=False)
                
                # Paso 1: TTS (voz neutral)
                if voice_profile and voice_profile.tts_config:
                    # Actualizar config del engine (esto cambia provider si es necesario)
                    self.tts_engine.update_config(voice_profile.tts_config)
                
                neutral_wav = self.tts_engine.synthesize(text)
                
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
                
                # Enviar evento de fin al overlay
                if main_window and hasattr(main_window, '_clear_overlay'):
                    main_window._clear_overlay()
                
            except Exception as e:
                print(f"Error en cola de audio: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.queue.task_done()
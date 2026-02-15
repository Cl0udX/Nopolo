import sounddevice as sd
import numpy as np
import platform
import time
import threading

# Variable global para controlar la reproducción
_current_stream = None
_stop_flag = False
_playback_lock = threading.Lock()  # Lock para evitar reproducciones simultáneas

def stop_audio():
    """Detiene el audio que está sonando actualmente"""
    global _stop_flag, _current_stream
    _stop_flag = True
    sd.stop()

def play_wav(wav_tuple):
    """
    Reproduce audio desde una tupla (wav_data, sample_rate)
    wav_data: numpy array normalizado en float32 (-1.0 a 1.0)
    sample_rate: frecuencia de muestreo en Hz
    """
    global _stop_flag, _current_stream, _playback_lock
    
    # Usar lock para evitar reproducciones simultáneas (previene crashes)
    with _playback_lock:
        # Resetear flag al inicio
        _stop_flag = False
        
        if isinstance(wav_tuple, tuple):
            data, sr = wav_tuple
        else:
            # Retrocompatibilidad si recibe path
            import soundfile as sf
            data, sr = sf.read(wav_tuple, dtype="float32")
        
        # Validar que el audio no tenga NaN o infinitos (prevenir crashes)
        if not np.isfinite(data).all():
            print("Advertencia: Audio contiene NaN o infinitos, limpiando...")
            data = np.nan_to_num(data, nan=0.0, posinf=1.0, neginf=-1.0)
        
        # Validar que el audio no esté vacío
        if len(data) == 0:
            print("Advertencia: Audio vacío, saltando reproducción")
            return
        
        # Fix para macOS: asegurar que el audio sea mono o estéreo correctamente
        if len(data.shape) == 1:
            data = data.reshape(-1, 1)
        
        # Reproducir y esperar, pero permitir detener
        try:
            sd.play(data, sr)
            _current_stream = True
            
            # Esperar mientras el audio está activo
            while sd.get_stream().active:
                if _stop_flag:
                    sd.stop()
                    break
                time.sleep(0.1)  # Dormir 100ms entre verificaciones
                
        except Exception as e:
            # Si falla get_stream(), usar wait() tradicional pero revisar stop_flag
            try:
                duration = len(data) / sr
                elapsed = 0
                while elapsed < duration:
                    if _stop_flag:
                        sd.stop()
                        break
                    time.sleep(0.1)
                    elapsed += 0.1
            except:
                sd.wait()
        finally:
            _current_stream = None
            _stop_flag = False
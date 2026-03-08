import sounddevice as sd
import numpy as np
import platform
import time
import threading

# Variable global para controlar la reproducción
_current_stream = None
_stop_flag = False
_playback_lock = threading.Lock()  # Lock para evitar reproducciones simultáneas
_volume: float = 1.0  # Volumen global (0.0 – 1.0)


def set_volume(vol: float):
    """Ajusta el volumen global de reproducción (0.0 – 1.0)."""
    global _volume
    _volume = max(0.0, min(1.0, float(vol)))


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

        # Aplicar volumen global
        if _volume != 1.0:
            data = data * _volume
        
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


# ── Reproducción con detección de peaks para avatar ──────────────────────────

def play_wav_with_peaks(wav_tuple, on_peak=None,
                        peak_interval_ms: int = 40,
                        peak_threshold: float = 0.05):
    """
    Como play_wav() pero dispara on_peak(is_talking: bool) cada peak_interval_ms
    sincronizado con la reproducción real.

    Args:
        wav_tuple: (numpy_array_float32, sample_rate) o ruta a archivo WAV
        on_peak: callable(bool) — True = boca abierta, False = cerrada
        peak_interval_ms: intervalo de análisis (ms)
        peak_threshold: RMS mínimo para considerar "hablando"
    """
    global _stop_flag, _current_stream, _playback_lock

    with _playback_lock:
        _stop_flag = False

        if isinstance(wav_tuple, tuple):
            data, sr = wav_tuple
        else:
            import soundfile as sf
            data, sr = sf.read(wav_tuple, dtype='float32')

        if not np.isfinite(data).all():
            data = np.nan_to_num(data, nan=0.0, posinf=1.0, neginf=-1.0)

        if len(data) == 0:
            return

        if _volume != 1.0:
            data = data * _volume

        if len(data.shape) == 1:
            data = data.reshape(-1, 1)

        # Pre-computar eventos de peak desde los datos de audio
        stop_peak = threading.Event()

        def _peak_driver():
            if on_peak is None:
                return
            chunk_size = max(1, int(sr * peak_interval_ms / 1000))
            flat = data.flatten()
            start = time.time()
            chunk_idx = 0
            while chunk_idx < len(flat):
                if stop_peak.is_set():
                    break
                chunk = flat[chunk_idx: chunk_idx + chunk_size]
                rms = float(np.sqrt(np.mean(chunk ** 2))) if len(chunk) > 0 else 0.0
                try:
                    on_peak(rms > peak_threshold)
                except Exception:
                    pass
                chunk_idx += chunk_size
                # Dormir hasta que corresponda el siguiente chunk
                expected_t = chunk_idx / sr
                sleep_t = expected_t - (time.time() - start)
                if sleep_t > 0.005:
                    time.sleep(sleep_t)
            # Cerrar boca siempre al terminar
            try:
                on_peak(False)
            except Exception:
                pass

        peak_thread = threading.Thread(target=_peak_driver, daemon=True)

        try:
            sd.play(data, sr)
            peak_thread.start()
            _current_stream = True

            while sd.get_stream().active:
                if _stop_flag:
                    sd.stop()
                    break
                time.sleep(0.05)

        except Exception:
            try:
                duration = len(data) / sr
                elapsed = 0
                while elapsed < duration:
                    if _stop_flag:
                        sd.stop()
                        break
                    time.sleep(0.05)
                    elapsed += 0.05
            except Exception:
                sd.wait()
        finally:
            stop_peak.set()
            _current_stream = None
            _stop_flag = False
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
    # Detener OutputStream activo si existe
    if hasattr(_current_stream, 'stop'):
        try:
            _current_stream.stop()
        except Exception:
            pass
    # Fallback para sd.play() legacy
    try:
        sd.stop()
    except Exception:
        pass

def play_wav(wav_tuple, on_before_play=None, on_after_play=None):
    """
    Reproduce audio desde una tupla (wav_data, sample_rate)
    wav_data: numpy array normalizado en float32 (-1.0 a 1.0)
    sample_rate: frecuencia de muestreo en Hz
    on_before_play: callback invocado dentro del lock ANTES de sd.play()
    on_after_play:  callback invocado dentro del lock DESPUÉS de reproducir
    """
    global _stop_flag, _current_stream, _playback_lock
    
    # Usar lock para evitar reproducciones simultáneas (previene crashes)
    with _playback_lock:
        # Notificar al caller que la reproducción está comenzando (dentro del lock)
        if on_before_play:
            try:
                on_before_play()
            except Exception:
                pass
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

        channels = data.shape[1]
        position = [0]

        def _callback(outdata, frames, time_info, status):
            if _stop_flag:
                outdata[:] = 0
                raise sd.CallbackStop()
            remaining = len(data) - position[0]
            n = min(frames, remaining)
            outdata[:n] = data[position[0]:position[0] + n] * _volume
            if n < frames:
                outdata[n:] = 0
                raise sd.CallbackStop()
            position[0] += n

        try:
            stream = sd.OutputStream(
                samplerate=sr,
                channels=channels,
                dtype='float32',
                callback=_callback,
            )
            _current_stream = stream
            with stream:
                while stream.active and not _stop_flag:
                    time.sleep(0.05)
        except Exception:
            # Fallback: sd.play con volumen estático snapshot
            try:
                sd.play(data * _volume, sr)
                _current_stream = True
                while sd.get_stream().active:
                    if _stop_flag:
                        sd.stop()
                        break
                    time.sleep(0.1)
            except Exception:
                sd.wait()
        finally:
            _current_stream = None
            _stop_flag = False
            if on_after_play:
                try:
                    on_after_play()
                except Exception:
                    pass


# ── Reproducción con detección de peaks para avatar ──────────────────────────

def play_wav_with_peaks(wav_tuple, on_peak=None,
                        peak_interval_ms: int = 40,
                        peak_threshold: float = 0.05,
                        on_before_play=None, on_after_play=None):
    """
    Como play_wav() pero dispara on_peak(is_talking: bool) cada peak_interval_ms
    sincronizado con la reproducción real.

    Args:
        wav_tuple: (numpy_array_float32, sample_rate) o ruta a archivo WAV
        on_peak: callable(bool) — True = boca abierta, False = cerrada
        peak_interval_ms: intervalo de análisis (ms)
        peak_threshold: RMS mínimo para considerar "hablando"
        on_before_play: callback invocado dentro del lock ANTES de sd.play()
        on_after_play:  callback invocado dentro del lock DESPUÉS de reproducir
    """
    global _stop_flag, _current_stream, _playback_lock

    with _playback_lock:
        # Notificar al caller que la reproducción está comenzando (dentro del lock)
        if on_before_play:
            try:
                on_before_play()
            except Exception:
                pass
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

        if len(data.shape) == 1:
            data = data.reshape(-1, 1)

        channels = data.shape[1]

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

        position = [0]

        def _callback(outdata, frames, time_info, status):
            if _stop_flag:
                outdata[:] = 0
                raise sd.CallbackStop()
            remaining = len(data) - position[0]
            n = min(frames, remaining)
            outdata[:n] = data[position[0]:position[0] + n] * _volume
            if n < frames:
                outdata[n:] = 0
                raise sd.CallbackStop()
            position[0] += n

        try:
            stream = sd.OutputStream(
                samplerate=sr,
                channels=channels,
                dtype='float32',
                callback=_callback,
            )
            _current_stream = stream
            with stream:
                peak_thread.start()
                while stream.active and not _stop_flag:
                    time.sleep(0.05)
        except Exception:
            # Fallback: sd.play con volumen estático snapshot
            try:
                sd.play(data * _volume, sr)
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
            if on_after_play:
                try:
                    on_after_play()
                except Exception:
                    pass
import sounddevice as sd
import numpy as np

def play_wav(wav_tuple):
    """
    Reproduce audio desde una tupla (wav_data, sample_rate)
    wav_data: numpy array normalizado en float32 (-1.0 a 1.0)
    sample_rate: frecuencia de muestreo en Hz
    """
    if isinstance(wav_tuple, tuple):
        data, sr = wav_tuple
    else:
        # Retrocompatibilidad si recibe path
        import soundfile as sf
        data, sr = sf.read(wav_tuple, dtype="float32")
    
    sd.play(data, sr)
    sd.wait()

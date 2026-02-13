import os
import traceback
from io import BytesIO

import av
import librosa
import numpy as np


def wav2(i, o, format):
    inp = av.open(i, "rb")
    if format == "m4a":
        format = "mp4"
    out = av.open(o, "wb", format=format)
    if format == "ogg":
        format = "libvorbis"
    if format == "mp4":
        format = "aac"

    ostream = out.add_stream(format)

    for frame in inp.decode(audio=0):
        for p in ostream.encode(frame):
            out.mux(p)

    for p in ostream.encode(None):
        out.mux(p)

    out.close()
    inp.close()


def audio2(i, o, format, sr):
    inp = av.open(i, "r")  # Cambiar "rb" a "r" para PyAV nuevo
    out = av.open(o, "w", format=format)  # Cambiar "wb" a "w"
    if format == "ogg":
        format = "libvorbis"
    if format == "f32le":
        format = "pcm_f32le"

    ostream = out.add_stream(format, channels=1)
    ostream.sample_rate = sr

    for frame in inp.decode(audio=0):
        for p in ostream.encode(frame):
            out.mux(p)

    out.close()
    inp.close()


def load_audio(file, sr):
    if not os.path.exists(file):
        raise RuntimeError(
            "You input a wrong audio path that does not exists, please fix it!"
        )
    try:
        # PATCH: Usar soundfile en lugar de librosa (evita problemas con numba en Mac)
        import soundfile as sf
        from scipy import signal
        
        audio, orig_sr = sf.read(file, dtype='float32')
        
        # Convertir a mono si es estéreo
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        
        # Resample si es necesario
        if orig_sr != sr:
            # Usar scipy.signal.resample que es puro numpy (sin numba)
            num_samples = int(len(audio) * sr / orig_sr)
            audio = signal.resample(audio, num_samples)
        
        return audio.flatten().astype('float32')
    except Exception:
        raise RuntimeError(traceback.format_exc())

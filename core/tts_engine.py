from TTS.api import TTS
import sounddevice as sd
import numpy as np
import os

class TTSEngine:
    def __init__(self):
        self.tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False, gpu=False)
        self.speaker_wav = "assets/speech.wav"

    def synthesize(self, text):
        wav = self.tts.tts(
            text=text,
            language="es",
            speaker_wav=self.speaker_wav
        )
        return wav

    def play(self, wav):
        if isinstance(wav, list):
            wav = np.array(wav)
        if wav.ndim > 1:
            wav = wav[:,0]
        sd.play(wav, samplerate=24000)
        sd.wait()
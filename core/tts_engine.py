import asyncio
import edge_tts
import sounddevice as sd
import numpy as np
import tempfile
import os
from pydub import AudioSegment

class TTSEngine:
    def __init__(self):
        self.voice = "es-MX-JorgeNeural"  # Voz masculina mexicana natural
        print("✅ Usando edge-tts (Microsoft Azure)")
        
    def synthesize(self, text):
        asyncio.run(self._generate(text))
        return None

    async def _generate(self, text):
        communicate = edge_tts.Communicate(text, self.voice)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp_path = tmp.name
        
        await communicate.save(tmp_path)
        
        # Convertir MP3 a WAV usando pydub
        audio = AudioSegment.from_mp3(tmp_path)
        wav_data = np.array(audio.get_array_of_samples())
        
        # Convertir a float y normalizar
        if audio.sample_width == 2:  # 16-bit
            wav_data = wav_data.astype(np.float32) / 32768.0
        
        # Si es estéreo, convertir a mono
        if audio.channels == 2:
            wav_data = wav_data.reshape((-1, 2)).mean(axis=1)
        
        sd.play(wav_data, samplerate=audio.frame_rate)
        sd.wait()
        
        os.unlink(tmp_path)

    def play(self, wav):
        pass  # No se usa con edge-tts
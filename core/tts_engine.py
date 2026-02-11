import asyncio
import edge_tts
import tempfile
import os
from pydub import AudioSegment

class TTSEngine:
    def __init__(self):
        self.voice = "es-MX-JorgeNeural"
        print("✅ Usando edge-tts")

    def synthesize(self, text) -> str:
        return asyncio.run(self._generate(text))

    async def _generate(self, text) -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as mp3_tmp:
            mp3_path = mp3_tmp.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as wav_tmp:
            wav_path = wav_tmp.name

        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(mp3_path)

        audio = AudioSegment.from_mp3(mp3_path)
        audio = audio.set_channels(1).set_frame_rate(44100)
        audio.export(wav_path, format="wav")

        os.unlink(mp3_path)
        return wav_path

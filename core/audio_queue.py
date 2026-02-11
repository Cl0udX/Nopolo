import queue
import threading

from core.audio_player import play_wav

class AudioQueue:
    def __init__(self, tts_engine, rvc_engine):
        self.q = queue.Queue()
        self.tts = tts_engine
        self.rvc = rvc_engine
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        while True:
            text = self.q.get()
            if text is None:
                break

            # TTS genera tupla (wav_data, rate)
            neutral_wav = self.tts.synthesize(text)
            
            # RVC convierte y retorna tupla (wav_data, rate)
            converted_wav = self.rvc.convert(neutral_wav)

            # Reproducir
            play_wav(converted_wav)

            self.q.task_done()

    def add(self, text):
        self.q.put(text)

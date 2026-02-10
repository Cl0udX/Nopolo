import queue
import threading

class AudioQueue:
    def __init__(self, tts_engine):
        self.q = queue.Queue()
        self.tts_engine = tts_engine
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        while True:
            text = self.q.get()
            if text is None:
                break
            wav = self.tts_engine.synthesize(text)
            self.tts_engine.play(wav)
            self.q.task_done()

    def add(self, text):
        self.q.put(text)

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton
from core.tts_engine import TTSEngine
from core.rvc_engine import RVCEngine
from core.audio_queue import AudioQueue
import sys

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StreamTTS MVP")
        self.resize(400,150)

        layout = QVBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Escribe texto...")
        self.button = QPushButton("Reproducir")
        layout.addWidget(self.input)
        layout.addWidget(self.button)
        self.setLayout(layout)

        # ✅ Inicializar engines
        self.tts_engine = TTSEngine()
        self.rvc_engine = RVCEngine()

        # ✅ Pasar ambos engines a AudioQueue
        self.audio_queue = AudioQueue(self.tts_engine, self.rvc_engine)

        self.button.clicked.connect(self.play_text)

    def play_text(self):
        text = self.input.text().strip()
        if text:
            self.audio_queue.add(text)
            self.input.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

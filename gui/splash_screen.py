"""
Pantalla de carga (Splash Screen) para Nopolo.
Se muestra mientras la aplicación inicializa sus componentes.
"""
from PySide6.QtWidgets import QSplashScreen, QVBoxLayout, QWidget, QProgressBar, QLabel
from PySide6.QtCore import Qt, QTimer, Signal, QRect
from PySide6.QtGui import QPixmap, QFont, QPainter, QPen, QColor
import os
import time


class OutlinedLabel(QLabel):
    """QLabel personalizado con contorno blanco en el texto"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.outline_color = QColor(255, 255, 255)
        self.outline_width = 2
    
    def paintEvent(self, event):
        """Dibuja el texto con contorno"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setFont(self.font())
        
        text = self.text()
        
        rect = self.rect()
        
        pen = QPen(self.outline_color)
        pen.setWidth(self.outline_width)
        painter.setPen(pen)
        
        offsets = [
            (-1, -1), (0, -1), (1, -1),
            (-1, 0),           (1, 0),
            (-1, 1),  (0, 1),  (1, 1)
        ]
        
        for dx, dy in offsets:
            offset_rect = rect.adjusted(dx, dy, dx, dy)
            painter.drawText(offset_rect, int(self.alignment()), text)
        
        painter.setPen(QPen(self.palette().color(self.foregroundRole())))
        painter.drawText(rect, int(self.alignment()), text)
        
        painter.end()


class SplashScreen(QSplashScreen):
    """Pantalla de carga con logo y barra de progreso"""
    
    loading_finished = Signal()
    
    def __init__(self):
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        logo_path = os.path.join(assets_dir, "nopolo_powerby.png")
        
        splash_width = 700
        image_height = 220
        bars_height = 140
        splash_height = image_height + bars_height
        
        pixmap = QPixmap(splash_width, splash_height)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path)
            logo_scaled = logo_pixmap.scaled(splash_width, image_height, 
                                            Qt.AspectRatioMode.KeepAspectRatio, 
                                            Qt.TransformationMode.SmoothTransformation)
            x_offset = (splash_width - logo_scaled.width()) // 2
            y_offset = 0
            painter.drawPixmap(x_offset, y_offset, logo_scaled)
        
        painter.end()
        
        super().__init__(pixmap, Qt.WindowType.WindowStaysOnTopHint)
        
        self.bars_start_y = image_height
        
        self.progress = 0
        self.start_time = time.time()
        self.min_display_time = 3.0
        self.current_stage = 0
        
        self.loading_stages = [
            (0, 15, "Cargando sistema..."),
            (15, 30, "Inicializando componentes..."),
            (30, 45, "Cargando TTS Engine..."),
            (45, 60, "Cargando RVC Engine..."),
            (60, 75, "Verificando conexión a internet..."),
            (75, 90, "Preparando interfaz..."),
            (90, 100, "¡Listo!")
        ]
        
        self._create_progress_widget()
        
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self._simulate_loading)
        self.loading_timer.start(80)
    
    def _create_progress_widget(self):
        """Crea el widget con la barra de progreso y mensajes"""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 15, 40, 20)
        layout.setSpacing(10)
        
        self.status_label = OutlinedLabel("Iniciando Nopolo...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #333;
                font-size: 13px;
                font-weight: bold;
                padding: 5px;
                background-color: transparent;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ccc;
                border-radius: 10px;
                background-color: rgba(255, 255, 255, 230);
                text-align: center;
                height: 30px;
                font-size: 12px;
                font-weight: bold;
                color: #333;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FFD700,
                    stop:0.5 #FFA500,
                    stop:1 #FF8C00
                );
                border-radius: 8px;
                margin: 1px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        credits_label = OutlinedLabel("Version: 1.0.0")
        credits_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credits_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 10px;
                font-style: italic;
                padding: 3px;
                background-color: transparent;
            }
        """)
        layout.addWidget(credits_label)
        
        bars_height = 140
        container.setGeometry(0, self.bars_start_y, self.width(), bars_height)
    
    def _simulate_loading(self):
        """Simula el proceso de carga con diferentes etapas"""
        if self.progress < 100:
            increment = 3 if self.progress < 70 else 2
            self.progress += increment
            self.progress = min(100, self.progress)
            self.progress_bar.setValue(self.progress)
            
            for idx, (start, end, message) in enumerate(self.loading_stages):
                if start <= self.progress < end:
                    if idx != self.current_stage:
                        self.current_stage = idx
                        self.status_label.setText(message)
                    break
                elif self.progress >= end and idx == len(self.loading_stages) - 1:
                    if idx != self.current_stage:
                        self.current_stage = idx
                        self.status_label.setText(message)
        
        elapsed_time = time.time() - self.start_time
        if self.progress >= 100 and elapsed_time >= self.min_display_time:
            self.loading_timer.stop()
            QTimer.singleShot(400, self._finish_loading)
    
    def _finish_loading(self):
        """Finaliza la pantalla de carga"""
        self.loading_finished.emit()
        self.close()
    
    def set_progress(self, value: int, message: str = ""):
        """
        Permite establecer el progreso manualmente desde fuera.
        Útil si se quiere sincronizar con carga real de componentes.
        
        Args:
            value: Valor de progreso (0-100)
            message: Mensaje a mostrar
        """
        self.progress = max(0, min(100, value))
        self.progress_bar.setValue(self.progress)
        if message:
            self.status_label.setText(message)
    
    def drawContents(self, painter: QPainter):
        """Override para personalizar el dibujo del splash"""
        super().drawContents(painter)

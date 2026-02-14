"""
Panel de control del servidor API REST.
Muestra estado y permite iniciar/detener el servidor.
"""

from PySide6.QtWidgets import QWidget, QGroupBox, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Signal


class APIPanel(QWidget):
    """Panel de control del API REST"""
    
    # Señales
    toggle_requested = Signal()  # Emitida cuando se presiona el botón toggle
    
    def __init__(self, host="0.0.0.0", port=8000, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self._build_ui()
    
    def _build_ui(self):
        """Construye la interfaz del panel"""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Grupo de API
        group = QGroupBox("🌐 Servidor REST API")
        group_layout = QHBoxLayout()
        
        # Estado del servidor
        self.status_label = QLabel(f"⏳ Iniciando en {self.host}:{self.port}...")
        self.status_label.setStyleSheet("color: orange;")
        group_layout.addWidget(self.status_label, 1)
        
        # Botón toggle
        self.toggle_btn = QPushButton("🛑 Detener")
        self.toggle_btn.clicked.connect(self.toggle_requested.emit)
        self.toggle_btn.setEnabled(False)
        group_layout.addWidget(self.toggle_btn)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
        
        self.setLayout(layout)
    
    def set_running(self):
        """Marca el servidor como ejecutándose"""
        self.status_label.setText(f"✅ Ejecutándose en http://{self.host}:{self.port}")
        self.status_label.setStyleSheet("color: green;")
        self.toggle_btn.setText("🛑 Detener")
        self.toggle_btn.setEnabled(True)
    
    def set_stopped(self):
        """Marca el servidor como detenido"""
        self.status_label.setText(f"⏹ Detenido")
        self.status_label.setStyleSheet("color: gray;")
        self.toggle_btn.setText("▶ Iniciar")
        self.toggle_btn.setEnabled(True)
    
    def set_error(self, error_msg):
        """Marca el servidor con error"""
        self.status_label.setText(f"❌ Error: {error_msg}")
        self.status_label.setStyleSheet("color: red;")
        self.toggle_btn.setText("▶ Reintentar")
        self.toggle_btn.setEnabled(True)

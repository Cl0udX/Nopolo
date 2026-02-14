"""
Panel de consola desplegable para logs de la aplicación.
Incluye redirección de stdout para capturar prints.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit
from PySide6.QtCore import Qt
import sys


class ConsoleRedirector:
    """Redirige stdout/stderr a la consola de la GUI"""
    def __init__(self, console_widget):
        self.console_widget = console_widget
        self.terminal = sys.__stdout__  # Mantener referencia a terminal original
    
    def write(self, text):
        """Escribe en la consola y en la terminal"""
        if text.strip():  # Ignorar líneas vacías
            # Escribir en consola GUI
            self.console_widget.append(text.rstrip())
            # Auto-scroll
            scrollbar = self.console_widget.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
            # También escribir en terminal
            self.terminal.write(text)
            self.terminal.flush()
    
    def flush(self):
        """Flush para compatibilidad"""
        self.terminal.flush()
    
    def isatty(self):
        """Retorna False para indicar que no es una terminal TTY"""
        return False


class ConsolePanel(QWidget):
    """Panel desplegable con consola de logs"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
    
    def _build_ui(self):
        """Construye la interfaz del panel"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Botón para mostrar/ocultar consola
        toggle_layout = QHBoxLayout()
        self.toggle_btn = QPushButton("▼ Mostrar Consola")
        self.toggle_btn.setMaximumHeight(25)
        self.toggle_btn.clicked.connect(self._toggle_console)
        toggle_layout.addStretch()
        toggle_layout.addWidget(self.toggle_btn)
        toggle_layout.addStretch()
        layout.addLayout(toggle_layout)
        
        # Widget de consola (inicialmente oculto)
        self.console_widget = QTextEdit()
        self.console_widget.setReadOnly(True)
        self.console_widget.setMaximumHeight(200)
        self.console_widget.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid #3e3e3e;
            }
        """)
        self.console_widget.setPlaceholderText("Los logs de la aplicación aparecerán aquí...")
        self.console_widget.hide()  # Oculto por defecto
        layout.addWidget(self.console_widget)
        
        self.setLayout(layout)
    
    def _toggle_console(self):
        """Muestra/oculta la consola de logs"""
        if self.console_widget.isVisible():
            self.console_widget.hide()
            self.toggle_btn.setText("▼ Mostrar Consola")
        else:
            self.console_widget.show()
            self.toggle_btn.setText("▲ Ocultar Consola")
    
    def log(self, message: str):
        """Agrega un mensaje a la consola"""
        self.console_widget.append(message)
        # Auto-scroll al final
        scrollbar = self.console_widget.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def get_redirector(self):
        """Retorna un ConsoleRedirector para redirigir stdout"""
        return ConsoleRedirector(self.console_widget)

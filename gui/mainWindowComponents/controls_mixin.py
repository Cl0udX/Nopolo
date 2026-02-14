"""
Mixin para controles de reproducción y UI.
Contiene métodos para stop, skip y toggle de consola.
"""


class ControlsMixin:
    """Mixin para controles de reproducción y UI"""
    
    def _stop_audio(self):
        """Detiene todo el audio que está sonando"""
        self.audio_queue.stop_current()
        print("Audio detenido")
    
    def _skip_audio(self):
        """Salta al siguiente en la cola"""
        self.audio_queue.skip_to_next()
        queue_size = self.audio_queue.get_queue_size()
        print(f"Saltando al siguiente (quedan {queue_size} en cola)")
        
        self.input.clear()
    
    def _toggle_console(self):
        """Muestra/oculta la consola de logs"""
        if self.console_widget.isVisible():
            self.console_widget.hide()
            self.console_toggle_btn.setText("▼ Mostrar Consola")
        else:
            self.console_widget.show()
            self.console_toggle_btn.setText("▲ Ocultar Consola")
    
    def log_to_console(self, message: str):
        """Agrega un mensaje a la consola"""
        self.console_widget.append(message)
        # Auto-scroll al final
        scrollbar = self.console_widget.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

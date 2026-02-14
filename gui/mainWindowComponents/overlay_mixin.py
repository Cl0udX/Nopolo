"""
Mixin para gestión del Overlay de OBS (WebSocket Server)
"""

from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QLineEdit,
                               QCheckBox, QMessageBox, QApplication)
from PySide6.QtCore import Qt
import asyncio
import threading


class OverlayMixin:
    """Mixin para gestionar el servidor WebSocket y overlay de OBS"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.overlay_server_running = False
        self.ws_server = None
        self.overlay_event_loop = None
        self.overlay_thread = None
        self.show_normal_mode = True  # Filtro: mostrar modo normal (API/voz única)
        self.show_nopolo_mode = True  # Filtro: mostrar modo Nopolo (multi-voz)
    
    def _build_overlay_panel(self):
        """Construye el panel de configuración del overlay"""
        overlay_group = QGroupBox("📺 Overlay para OBS")
        overlay_layout = QVBoxLayout()
        
        status_layout = QHBoxLayout()
        self.overlay_status_label = QLabel("🔴 Desconectado")
        self.overlay_status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        status_layout.addWidget(self.overlay_status_label)
        status_layout.addStretch()
        overlay_layout.addLayout(status_layout)
        
        self.overlay_toggle_btn = QPushButton("▶️ Iniciar Servidor Overlay")
        self.overlay_toggle_btn.clicked.connect(self._toggle_overlay_server)
        overlay_layout.addWidget(self.overlay_toggle_btn)
        
        modes_label = QLabel("Filtros de visualización:")
        modes_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        overlay_layout.addWidget(modes_label)
        
        self.overlay_normal_check = QCheckBox("💬 Mostrar modo normal (API / voz única)")
        self.overlay_normal_check.setToolTip("Muestra mensajes que llegan desde la API con una sola voz")
        self.overlay_normal_check.setChecked(True)
        self.overlay_normal_check.toggled.connect(self._on_overlay_mode_changed)
        overlay_layout.addWidget(self.overlay_normal_check)
        
        self.overlay_nopolo_check = QCheckBox("🎨 Mostrar modo Nopolo (sintaxis multi-voz)")
        self.overlay_nopolo_check.setToolTip("Muestra mensajes con sintaxis Nopolo: voz.fd: texto (sonido)")
        self.overlay_nopolo_check.setChecked(True)
        self.overlay_nopolo_check.toggled.connect(self._on_overlay_mode_changed)
        overlay_layout.addWidget(self.overlay_nopolo_check)
        
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL para OBS:"))
        self.overlay_url_field = QLineEdit()
        self.overlay_url_field.setReadOnly(True)
        self.overlay_url_field.setPlaceholderText("Inicia el servidor para obtener la URL")
        url_layout.addWidget(self.overlay_url_field)
        overlay_layout.addLayout(url_layout)
        
        actions_layout = QHBoxLayout()
        
        self.copy_url_btn = QPushButton("📋 Copiar URL")
        self.copy_url_btn.clicked.connect(self._copy_overlay_url)
        self.copy_url_btn.setEnabled(False)
        actions_layout.addWidget(self.copy_url_btn)
        
        self.test_overlay_btn = QPushButton("🧪 Probar Overlay")
        self.test_overlay_btn.clicked.connect(self._test_overlay)
        self.test_overlay_btn.setEnabled(False)
        actions_layout.addWidget(self.test_overlay_btn)
        
        self.open_overlay_btn = QPushButton("🌐 Abrir en Navegador")
        self.open_overlay_btn.clicked.connect(self._open_overlay_browser)
        self.open_overlay_btn.setEnabled(False)
        actions_layout.addWidget(self.open_overlay_btn)
        
        overlay_layout.addLayout(actions_layout)
        
        info_label = QLabel("ℹ️ El overlay muestra el texto en tiempo real mientras se reproduce el TTS.")
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        info_label.setWordWrap(True)
        overlay_layout.addWidget(info_label)
        
        self.edit_css_btn = QPushButton("🎨 Editar Estilo del Overlay (CSS)")
        self.edit_css_btn.clicked.connect(self._open_css_editor)
        overlay_layout.addWidget(self.edit_css_btn)
        
        overlay_group.setLayout(overlay_layout)
        return overlay_group
    
    def _on_overlay_mode_changed(self):
        self.show_normal_mode = self.overlay_normal_check.isChecked()
        self.show_nopolo_mode = self.overlay_nopolo_check.isChecked()
        if self.overlay_server_running:
            self._update_overlay_url()
    
    def _update_overlay_url(self):
        # URL siempre la misma, los filtros se manejan en el backend
        url = f"http://localhost:8765/overlay"
        self.overlay_url_field.setText(url)
    
    def _toggle_overlay_server(self):
        if self.overlay_server_running:
            self._stop_overlay_server()
        else:
            self._start_overlay_server()
    
    def _start_overlay_server(self):
        try:
            from core.websocket_server import get_websocket_server
            
            def run_server():
                self.overlay_event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.overlay_event_loop)
                self.ws_server = get_websocket_server()
                self.overlay_event_loop.run_until_complete(self.ws_server.start())
                self.overlay_event_loop.run_forever()
            
            self.overlay_thread = threading.Thread(target=run_server, daemon=True)
            self.overlay_thread.start()
            
            self.overlay_server_running = True
            self.overlay_status_label.setText("🟢 Conectado")
            self.overlay_status_label.setStyleSheet("color: #28a745; font-weight: bold;")
            self.overlay_toggle_btn.setText("⏹️ Detener Servidor Overlay")
            
            self._update_overlay_url()
            
            self.copy_url_btn.setEnabled(True)
            self.test_overlay_btn.setEnabled(True)
            self.open_overlay_btn.setEnabled(True)
            
            self.log_to_console("✅ Servidor Overlay iniciado en http://localhost:8765")
            
        except Exception as e:
            self.log_to_console(f"❌ Error al iniciar servidor Overlay: {e}")
            QMessageBox.critical(self, "Error", f"No se pudo iniciar el servidor Overlay:\n{e}")
    
    def _stop_overlay_server(self):
        try:
            if self.overlay_event_loop and self.ws_server:
                asyncio.run_coroutine_threadsafe(self.ws_server.stop(), self.overlay_event_loop)
                self.overlay_event_loop.call_soon_threadsafe(self.overlay_event_loop.stop)
            
            self.overlay_server_running = False
            self.overlay_status_label.setText("🔴 Desconectado")
            self.overlay_status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
            self.overlay_toggle_btn.setText("▶️ Iniciar Servidor Overlay")
            
            self.copy_url_btn.setEnabled(False)
            self.test_overlay_btn.setEnabled(False)
            self.open_overlay_btn.setEnabled(False)
            self.overlay_url_field.clear()
            
            self.log_to_console("🛑 Servidor Overlay detenido")
            
        except Exception as e:
            self.log_to_console(f"❌ Error al detener servidor Overlay: {e}")
    
    def _copy_overlay_url(self):
        url = self.overlay_url_field.text()
        if url:
            clipboard = QApplication.clipboard()
            clipboard.setText(url)
            self.log_to_console(f"📋 URL copiada al portapapeles: {url}")
            QMessageBox.information(self, "Copiado", "URL copiada al portapapeles ✅")
    
    def _test_overlay(self):
        if self.ws_server and self.overlay_event_loop:
            # Probar con modo Nopolo si está activado
            if self.show_nopolo_mode:
                test_text = "homero.fd: ¡Hola! (risas.fd) Este es un texto de prueba"
                is_nopolo = True
            else:
                test_text = "¡Hola! Este es un texto de prueba para el overlay de OBS"
                is_nopolo = False
            
            asyncio.run_coroutine_threadsafe(
                self.ws_server.send_tts_start(test_text, "Homero Simpson", is_nopolo),
                self.overlay_event_loop
            )
            
            self.log_to_console("🧪 Mensaje de prueba enviado al overlay")
            
            def hide_after_delay():
                import time
                time.sleep(5)
                if self.ws_server and self.overlay_event_loop:
                    asyncio.run_coroutine_threadsafe(
                        self.ws_server.send_tts_stop(),
                        self.overlay_event_loop
                    )
            
            threading.Thread(target=hide_after_delay, daemon=True).start()
    
    def _open_overlay_browser(self):
        url = self.overlay_url_field.text()
        if url:
            import webbrowser
            webbrowser.open(url)
            self.log_to_console(f"🌐 Abriendo overlay en navegador: {url}")
    
    def _open_css_editor(self):
        import os, subprocess, platform
        
        css_path = os.path.join(os.getcwd(), 'overlay', 'overlay.css')
        
        try:
            if platform.system() == 'Darwin':
                subprocess.run(['open', css_path])
            elif platform.system() == 'Windows':
                os.startfile(css_path)
            else:
                subprocess.run(['xdg-open', css_path])
            
            self.log_to_console(f"🎨 Abriendo editor de CSS: {css_path}")
            QMessageBox.information(self, "Editor CSS", "Se ha abierto el archivo CSS del overlay.")
        except Exception as e:
            self.log_to_console(f"❌ Error al abrir CSS: {e}")
            QMessageBox.warning(self, "Error", f"No se pudo abrir el archivo CSS:\n{e}")
    
    def _send_overlay_event(self, text: str, voice: str = "", is_nopolo: bool = False):
        """
        Envía un evento al overlay cuando se reproduce TTS
        
        Args:
            text: El texto a mostrar
            voice: Nombre de la voz
            is_nopolo: True si es modo Nopolo (multi-voz), False si es modo normal (API/voz única)
        """
        if self.ws_server and self.overlay_event_loop and self.overlay_server_running:
            # Filtrar según los checkboxes
            if is_nopolo and not self.show_nopolo_mode:
                return  # Modo Nopolo pero filtro desactivado
            if not is_nopolo and not self.show_normal_mode:
                return  # Modo normal pero filtro desactivado
            
            asyncio.run_coroutine_threadsafe(
                self.ws_server.send_tts_start(text, voice, is_nopolo),
                self.overlay_event_loop
            )
    
    def _clear_overlay(self):
        if self.ws_server and self.overlay_event_loop and self.overlay_server_running:
            asyncio.run_coroutine_threadsafe(
                self.ws_server.send_tts_stop(),
                self.overlay_event_loop
            )

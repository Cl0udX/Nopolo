"""
Mixin para gestión del servidor API REST.
Permite iniciar, detener y controlar el servidor API.
"""


class APIMixin:
    """Mixin para gestión del servidor API REST"""
    
    def _start_api_server(self):
        """Inicia el servidor REST API"""
        try:
            from api.rest_server import TTSAPIServer
            
            self.api_server = TTSAPIServer(
                voice_manager=self.voice_manager,
                audio_queue=self.audio_queue,
                host=self.api_host,
                port=self.api_port,
                main_window=self
            )
            
            self.api_server.start()
            
            # Actualizar UI
            if hasattr(self, 'api_status'):
                self.api_status.setText(f"✅ API corriendo en http://{self.api_host}:{self.api_port}")
                self.api_status.setStyleSheet("color: green;")
                self.api_toggle_btn.setEnabled(True)
            
            print(f"API REST iniciada en http://{self.api_host}:{self.api_port}")
            print(f"Documentación: http://localhost:{self.api_port}/docs")
            
        except ImportError:
            print("No se pudo importar api.rest_server")
            print("Instala las dependencias: pip install fastapi uvicorn")
            if hasattr(self, 'api_status'):
                self.api_status.setText("❌ Error: Falta instalar FastAPI")
                self.api_status.setStyleSheet("color: red;")
        except Exception as e:
            print(f"Error iniciando API: {e}")
            if hasattr(self, 'api_status'):
                self.api_status.setText(f"❌ Error: {e}")
                self.api_status.setStyleSheet("color: red;")
    
    def _toggle_api(self):
        """Inicia/detiene el servidor API"""
        if self.api_server and self.api_server.is_running:
            self.api_server.stop()
            self.api_status.setText(f"🛑 API detenida")
            self.api_status.setStyleSheet("color: gray;")
            self.api_toggle_btn.setText("▶️ Iniciar")
        else:
            self._start_api_server()
            self.api_toggle_btn.setText("🛑 Detener")

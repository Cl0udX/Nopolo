"""
Mixin para reproducción de audio (TTS + RVC).
Contiene los métodos principales de síntesis y reproducción.
"""


class PlaybackMixin:
    """Mixin para reproducción de audio"""
    
    def play_text(self):
        """Reproduce el texto con la voz seleccionada o modo multi-voz"""
        text = self.input.text().strip()
        if not text:
            return
        
        # Verificar modo multi-voz
        if self.multivoice_check.isChecked():
            # Modo multi-voz: procesar con AdvancedProcessor en thread separado
            import threading
            thread = threading.Thread(target=self._play_multivoice, args=(text,), daemon=True)
            thread.start()
        else:
            # Modo tradicional: usar cola de audio (ya es no bloqueante)
            profile_id = self.voice_combo.currentData()
            profile = self.voice_manager.get_profile(profile_id)
            
            # Agregar a la cola
            self.audio_queue.add(text, profile)
    
    def _play_multivoice(self, text: str):
        """Procesa y reproduce audio multi-voz en thread separado"""
        try:
            import soundfile as sf
            import sounddevice as sd
            import tempfile
            
            # Procesar mensaje
            audio_data, sample_rate = self.advanced_processor.process_message(text)
            
            # Guardar temporalmente
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_file.close()
            sf.write(temp_file.name, audio_data, sample_rate)
            
            # Reproducir
            sd.play(audio_data, sample_rate)
            sd.wait()
            
            # Limpiar archivo temporal
            import os
            os.unlink(temp_file.name)
            
        except Exception as e:
            print(f"Error en modo multi-voz: {e}")
            import traceback
            traceback.print_exc()

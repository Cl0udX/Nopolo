"""
Mixin para gestión de efectos (sonidos, fondos, filtros).
Contiene métodos para agregar, editar, eliminar y reproducir efectos.
"""
from PySide6.QtWidgets import QMessageBox
from gui.effects_manager_dialog import EffectEditorDialog


class EffectsManagerMixin:
    """Mixin para gestión de sonidos, fondos y filtros"""
    
    def _add_effect(self, effect_type="sound"):
        """Abre diálogo para agregar efecto/fondo"""
        dialog = EffectEditorDialog(self, is_new=True, effect_type=effect_type)
        if dialog.exec():
            # Recargar managers desde archivo
            self.sound_manager.reload()
            self.background_manager.reload()
            # Recargar solo la tabla correspondiente
            if effect_type == "sound":
                self._load_sounds_table()
            elif effect_type == "background":
                self._load_backgrounds_table()
    
    def _edit_sound(self, sound_id, sound_data):
        """Edita un sonido existente"""
        dialog = EffectEditorDialog(self, is_new=False, effect_data=sound_data, effect_type="sound")
        if dialog.exec():
            # Recargar manager desde archivo antes de actualizar tabla
            self.sound_manager.reload()
            self._load_sounds_table()
    
    def _edit_background(self, bg_id, bg_data):
        """Edita un fondo existente"""
        dialog = EffectEditorDialog(self, is_new=False, effect_data=bg_data, effect_type="background")
        if dialog.exec():
            # Recargar manager desde archivo antes de actualizar tabla
            self.background_manager.reload()
            self._load_backgrounds_table()
    
    def _delete_sound(self, sound_id):
        """Elimina un sonido"""
        reply = QMessageBox.question(
            self, 
            'Confirmar eliminación',
            f'¿Eliminar sonido ID {sound_id}?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.sound_manager.remove_sound(sound_id)
            self.sound_manager.reload()
            self._load_sounds_table()
    
    def _delete_background(self, bg_id):
        """Elimina un fondo"""
        reply = QMessageBox.question(
            self, 
            'Confirmar eliminación',
            f'¿Eliminar fondo "{bg_id}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.background_manager.remove_background(bg_id)
            self.background_manager.reload()
            self._load_backgrounds_table()
    
    def _play_sound_preview(self, sound_id):
        """Reproduce preview de un sonido"""
        from core.audio_player import play_wav
        import soundfile as sf
        
        sound_data = self.sound_manager.get_sound(sound_id)
        if sound_data and 'path' in sound_data:
            try:
                # Cargar y reproducir el archivo de audio
                audio, sr = sf.read(sound_data['path'], dtype='float32')
                play_wav((audio, sr))
            except Exception as e:
                print(f"Error reproduciendo sonido {sound_id}: {e}")
        else:
            print(f"No se encontró el sonido {sound_id}")
    
    def _play_background_preview(self, bg_id):
        """Reproduce preview de un fondo (solo 5 segundos)"""
        from core.audio_player import play_wav
        import soundfile as sf
        
        bg_data = self.background_manager.get_background(bg_id)
        if bg_data and 'path' in bg_data:
            try:
                # Cargar audio
                audio, sr = sf.read(bg_data['path'], dtype='float32')
                
                # Reproducir solo 5 segundos para preview
                max_samples = sr * 5
                preview_audio = audio[:max_samples] if len(audio) > max_samples else audio
                
                play_wav((preview_audio, sr))
            except Exception as e:
                print(f"Error reproduciendo fondo {bg_id}: {e}")
        else:
            print(f"No se encontró el fondo {bg_id}")
    
    def _test_integrated_filter(self, filter_id, filter_name):
        """Ejecuta un test de un filtro integrado con voz de prueba"""
        # Obtener ID de voz actual (profile_id, no display_name)
        voice_id = self.voice_combo.currentData()
        if not voice_id:
            QMessageBox.warning(self, "Advertencia", "Selecciona una voz primero")
            return
        
        # Texto de prueba con el filtro (usando profile_id)
        test_text = f"{voice_id}.{filter_id}: Hola como estas, esto es una prueba del filtro {filter_name}. Esto debería sonar con el efecto aplicado."
        
        print(f"Testing filtro '{filter_id}' ({filter_name})")
        print(f"Texto: {test_text}")
        
        # Usar el modo multi-voz para procesar con el filtro
        try:
            was_multivoice = self.multivoice_check.isChecked()
            
            # Activar temporalmente modo multi-voz si no está activo
            if not was_multivoice:
                self.multivoice_check.setChecked(True)
            
            # Guardar texto actual
            original_text = self.input.text()
            
            # Establecer texto de prueba
            self.input.setText(test_text)
            
            # Reproducir
            self.play_text()
            
            # Restaurar texto original después de un momento
            # (se restaura inmediatamente porque play_text es asíncrono)
            self.input.setText(original_text)
            
            # Restaurar estado de multi-voz
            if not was_multivoice:
                self.multivoice_check.setChecked(False)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al probar filtro: {e}")
            print(f"Error: {e}")

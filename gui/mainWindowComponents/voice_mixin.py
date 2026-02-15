"""
Mixin para gestión de voces.
Contiene métodos para cargar, agregar, editar y escanear voces.
"""
import os
from gui.voice_config_dialog import VoiceConfigDialog


class VoiceMixin:
    """Mixin para gestión de voces"""
    
    def _load_voices(self):
        """Carga las voces disponibles en el dropdown"""
        current_id = self.voice_combo.currentData()
        self.voice_combo.clear()
        
        profiles = self.voice_manager.list_profiles(enabled_only=True)
        
        for profile in profiles:
            # Emoji según tipo
            emoji = "🎭" if profile.is_transformer_voice() else "🔊"
            display_text = f"{emoji} {profile.display_name}"
            
            self.voice_combo.addItem(display_text, profile.profile_id)
        
        # Restaurar selección o usar default
        if current_id:
            index = self.voice_combo.findData(current_id)
            if index >= 0:
                self.voice_combo.setCurrentIndex(index)
        else:
            default_id = self.voice_manager.default_voice_id
            if default_id:
                index = self.voice_combo.findData(default_id)
                if index >= 0:
                    self.voice_combo.setCurrentIndex(index)
        
        self.log_to_console(f"{len(profiles)} voces cargadas")
    
    def _on_voice_changed(self, index):
        """Callback cuando cambia la voz seleccionada"""
        if index < 0:
            return
        
        profile_id = self.voice_combo.itemData(index)
        profile = self.voice_manager.get_profile(profile_id)
        
        if not profile:
            return
        
        # Actualizar información
        info_parts = []
        info_parts.append(f"<b>{profile.display_name}</b>")
        info_parts.append(f"TTS: {profile.tts_config.voice_id}")
        
        if profile.is_transformer_voice():
            info_parts.append(f"RVC: {profile.rvc_config.name}")
            info_parts.append(f"Pitch: {profile.rvc_config.pitch_shift:+d}")
        else:
            info_parts.append("Sin transformación RVC")
        
        if profile.tags:
            info_parts.append(f"Tags: {', '.join(profile.tags)}")
        
        self.voice_info.setText(" | ".join(info_parts))
        
        # Actualizar engine TTS
        self.tts_engine.update_config(profile.tts_config)
        
        # Cargar modelo RVC si es necesario
        if profile.is_transformer_voice():
            try:
                if (not self.rvc_engine.model_loaded or 
                    self.rvc_engine.config.model_id != profile.rvc_config.model_id):
                    self.rvc_engine.load_model(profile.rvc_config)
            except Exception as e:
                self.log_to_console(f"Error cargando modelo RVC: {e}")
    
    def _add_voice(self):
        """Abre diálogo para agregar nueva voz"""
        dialog = VoiceConfigDialog(
            parent=self,
            profile=None,  # Modo crear
            voice_manager=self.voice_manager
        )
        
        if dialog.exec():
            # Voz agregada exitosamente
            self.log_to_console(f"Voz agregada: {dialog.get_profile().display_name}")
            self._load_voices()
            
            # Seleccionar la nueva voz
            new_id = dialog.get_profile().profile_id
            index = self.voice_combo.findData(new_id)
            if index >= 0:
                self.voice_combo.setCurrentIndex(index)
    
    def _edit_voice(self):
        """Abre diálogo para editar voz actual"""
        profile_id = self.voice_combo.currentData()
        if not profile_id:
            return
        
        profile = self.voice_manager.get_profile(profile_id)
        if not profile:
            return
        
        dialog = VoiceConfigDialog(
            parent=self,
            profile=profile,  # Modo editar
            voice_manager=self.voice_manager
        )
        
        if dialog.exec():
            # Voz editada exitosamente
            self.log_to_console(f"Voz actualizada: {dialog.get_profile().display_name}")
            self._load_voices()
    
    def _scan_models(self):
        """Escanea y agrega automáticamente nuevos modelos"""
        new_models = self.voice_manager.scan_rvc_models()
        
        if not new_models:
            self.log_to_console("No se encontraron modelos nuevos")
            return
        
        self.log_to_console(f"{len(new_models)} modelos nuevos encontrados")
        
        added_count = 0
        for model_path in new_models:
            folder_name = os.path.basename(os.path.dirname(model_path))
            profile_id = self.voice_manager.auto_add_rvc_model(model_path, gender="male")
            if profile_id:
                added_count += 1
        
        self.log_to_console(f"Se agregaron {added_count}/{len(new_models)} modelos")
        
        # Recargar lista de voces en la GUI
        self._load_voices()
    
    def _delete_voice(self):
        """Elimina la voz seleccionada"""
        from PySide6.QtWidgets import QMessageBox
        
        # Obtener voz actual
        profile_id = self.voice_combo.currentData()
        if not profile_id:
            QMessageBox.warning(self, "Sin selección", "Selecciona una voz para eliminar")
            return
        
        profile = self.voice_manager.get_profile(profile_id)
        if not profile:
            QMessageBox.warning(self, "Error", "No se pudo obtener información de la voz")
            return
        
        # Confirmación
        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Estás seguro de eliminar la voz?\n\n"
            f"Nombre: {profile.display_name}\n"
            f"ID: {profile.profile_id}\n"
            f"Tipo: {'Con RVC' if profile.is_transformer_voice() else 'Solo TTS'}\n\n"
            f"Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Eliminar del voice manager (esto actualiza el JSON automáticamente)
            if self.voice_manager.remove_profile(profile_id):
                self.log_to_console(f"Voz eliminada: {profile.display_name}")
                # Recargar lista
                self._load_voices()
            else:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar la voz {profile.display_name}")
    
    def _reload_voices(self):
        """Recarga las voces desde el archivo JSON"""
        from PySide6.QtWidgets import QMessageBox
        
        try:
            # Recargar configuración desde archivo
            self.voice_manager._load_config()
            
            # Recargar lista en la GUI
            self._load_voices()
            
            self.log_to_console("Voces recargadas desde archivo")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error al recargar voces:\n{str(e)}"
            )
            self.log_to_console(f"Error recargando voces: {e}")
    
    def _on_multivoice_toggled(self, checked):
        """Callback cuando se activa/desactiva el modo multi-voz."""
        if checked:
            self.input.setPlaceholderText("Ej: dross: hola (disparo) homero: doh!")
        else:
            self.input.setPlaceholderText("Escribe el texto aquí...")

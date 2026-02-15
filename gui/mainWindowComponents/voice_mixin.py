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
        
        print(f"{len(profiles)} voces cargadas")
    
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
                print(f"Error cargando modelo RVC: {e}")
    
    def _add_voice(self):
        """Abre diálogo para agregar nueva voz"""
        dialog = VoiceConfigDialog(
            parent=self,
            profile=None,  # Modo crear
            voice_manager=self.voice_manager
        )
        
        if dialog.exec():
            # Voz agregada exitosamente
            print(f"Voz agregada: {dialog.get_profile().display_name}")
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
            print(f"Voz actualizada: {dialog.get_profile().display_name}")
            self._load_voices()
    
    def _scan_models(self):
        """Escanea y agrega automáticamente nuevos modelos"""
        print("\n🔍 Iniciando escaneo de modelos...")
        new_models = self.voice_manager.scan_rvc_models()
        
        if not new_models:
            print("✓ No se encontraron modelos nuevos")
            return
        
        print(f"🎙️ {len(new_models)} modelos nuevos encontrados:")
        
        added_count = 0
        for model_path in new_models:
            folder_name = os.path.basename(os.path.dirname(model_path))
            print(f"   → Agregando: {folder_name}")
            profile_id = self.voice_manager.auto_add_rvc_model(model_path, gender="male")
            if profile_id:
                print(f"      ✅ Perfil creado con ID: {profile_id}")
                added_count += 1
            else:
                print(f"      ❌ Error al crear perfil")
        
        print(f"\n✅ Se agregaron {added_count}/{len(new_models)} modelos")
        print(f"📁 Guardado en: {self.voice_manager.config_path}")
        
        # Recargar lista de voces en la GUI
        self._load_voices()
        print("🔄 GUI actualizada\n")
    
    def _on_multivoice_toggled(self, checked):
        """Callback cuando se activa/desactiva el modo multi-voz."""
        if checked:
            self.input.setPlaceholderText("Ej: dross: hola (disparo) homero: doh!")
        else:
            self.input.setPlaceholderText("Escribe el texto aquí...")

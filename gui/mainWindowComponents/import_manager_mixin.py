"""
Mixin para importación masiva de archivos de audio.
Permite importar múltiples sonidos y fondos de una sola vez.
"""
from PySide6.QtWidgets import QFileDialog, QMessageBox
import os
import json


class ImportManagerMixin:
    """Mixin para importación masiva de archivos de audio"""
    
    def _import_audio_files(self, audio_type="sound"):
        """Importa múltiples archivos de audio (MP3/WAV) de forma masiva
        
        IMPORTANTE: No copia archivos, solo guarda la ruta donde el usuario los tiene.
        El usuario gestiona sus archivos en su propia ubicación.
        
        Args:
            audio_type: "sound" o "background"
        """
        # Abrir diálogo para seleccionar múltiples archivos
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("Audio Files (*.mp3 *.wav)")
        file_dialog.setWindowTitle(f"Importar {'Sonidos' if audio_type == 'sound' else 'Fondos'}")
        
        if not file_dialog.exec():
            return
        
        selected_files = file_dialog.selectedFiles()
        if not selected_files:
            return
        
        # Obtener el siguiente ID disponible
        next_id = self._get_next_available_id(audio_type)
        
        imported_count = 0
        errors = []
        
        for file_path in selected_files:
            try:
                # Obtener nombre del archivo sin extensión
                file_name = os.path.basename(file_path)
                name_without_ext = os.path.splitext(file_name)[0]
                
                # NO copiamos el archivo, solo guardamos la ruta original
                # El usuario gestiona sus archivos donde quiera
                
                # Agregar a la configuración con la ruta ORIGINAL
                if audio_type == "sound":
                    self._add_sound_to_config(
                        sound_id=str(next_id),
                        name=name_without_ext,
                        filename=file_name,
                        path=file_path  # Ruta ORIGINAL del usuario
                    )
                else:  # background
                    self._add_background_to_config(
                        bg_id=f"f{chr(96 + next_id)}" if next_id <= 26 else f"bg{next_id}",
                        name=name_without_ext,
                        path=file_path,  # Ruta ORIGINAL del usuario
                        volume=0.3
                    )
                
                next_id += 1
                imported_count += 1
                
            except Exception as e:
                errors.append(f"{file_name}: {str(e)}")
        
        # Recargar tabla
        if audio_type == "sound":
            self._load_sounds_table()
        else:
            self._load_backgrounds_table()
        
        # Mostrar resumen
        summary = f"✅ Importados {imported_count} archivos exitosamente"
        if errors:
            summary += f"\n\n⚠️ Errores ({len(errors)}):\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                summary += f"\n... y {len(errors) - 5} errores más"
        
        QMessageBox.information(self, "Importación Completa", summary)
    
    def _get_next_available_id(self, audio_type):
        """Obtiene el siguiente ID disponible para sonidos o fondos"""
        if audio_type == "sound":
            sounds = self.sound_manager.list_sounds()
            if not sounds:
                return 1
            # Obtener IDs numéricos y encontrar el máximo
            ids = [int(s.get('id', 0)) for s in sounds if s.get('id', '').isdigit()]
            return max(ids) + 1 if ids else 1
        else:  # background
            backgrounds = self.background_manager.list_backgrounds()
            if not backgrounds:
                return 1
            # Contar cuántos fondos hay
            return len(backgrounds) + 1
    
    def _add_sound_to_config(self, sound_id, name, filename, path):
        """Agrega un sonido al archivo de configuración"""
        config_path = "config/sounds.json"
        
        # Cargar configuración actual
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {"sounds": []}
        
        # Agregar nuevo sonido
        new_sound = {
            "id": sound_id,
            "name": name,
            "filename": filename,
            "path": path,
            "category": "imported",
            "description": ""
        }
        
        config["sounds"].append(new_sound)
        
        # Guardar
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # Recargar manager
        self.sound_manager._load_config()
    
    def _add_background_to_config(self, bg_id, name, path, volume):
        """Agrega un fondo al archivo de configuración"""
        config_path = "config/backgrounds.json"
        
        # Cargar configuración actual
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {"backgrounds": {}}
        
        # Agregar nuevo fondo
        config["backgrounds"][bg_id] = {
            "id": bg_id,
            "name": name,
            "description": "",
            "path": path,
            "volume": volume
        }
        
        # Guardar
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # Recargar manager
        self.background_manager._load_config()

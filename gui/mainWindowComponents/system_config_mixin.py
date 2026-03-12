"""
Mixin para configuración del sistema y utilidades.
Contiene métodos para verificar conexión a internet y configurar dispositivos de audio.
"""
import os
import sys
import subprocess
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QMessageBox, QTextEdit, QGroupBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from core.app_config import get_app_config


class SystemConfigMixin:
    """Mixin para configuración del sistema"""
    
    def _check_internet_connection(self):
        """Verifica la conexión a internet"""
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            self.connection_indicator.setStyleSheet("color: green; font-size: 16px;")
            self.connection_label.setText("Conectado")
            return True
        except OSError:
            self.connection_indicator.setStyleSheet("color: red; font-size: 16px;")
            self.connection_label.setText("Sin conexión")
            return False
    
    def _open_audio_device_settings(self):
        """Abre diálogo para seleccionar dispositivo de salida de audio"""
        try:
            import sounddevice as sd
            
            # Obtener configuración guardada
            app_config = get_app_config()
            saved_device = app_config.get_audio_device()
            
            # Obtener lista de dispositivos
            devices = sd.query_devices()
            output_devices = []
            
            for i, device in enumerate(devices):
                if device['max_output_channels'] > 0:
                    output_devices.append((i, device['name']))
            
            # Obtener dispositivo actual en uso
            current_device = sd.default.device[1]  # [input, output]
            
            # Crear diálogo
            dialog = QDialog(self)
            dialog.setWindowTitle("Configuración de Dispositivo de Audio")
            dialog.resize(550, 350)
            
            layout = QVBoxLayout()
            
            # Mostrar dispositivo configurado
            if saved_device is None:
                config_text = "Dispositivo configurado: <b>Predeterminado del Sistema</b>"
            else:
                try:
                    device_name = devices[saved_device]['name']
                    config_text = f"Dispositivo configurado: <b>{device_name}</b>"
                except:
                    config_text = "Dispositivo configurado: <b>Desconocido (verificar)</b>"
            
            config_label = QLabel(config_text)
            config_label.setStyleSheet("padding: 10px; background-color: #e3f2fd; border-radius: 5px; margin-bottom: 10px; color: #000;")
            layout.addWidget(config_label)
            
            # Información
            info_label = QLabel("Selecciona el dispositivo de salida de audio:")
            layout.addWidget(info_label)
            
            # Lista de dispositivos
            device_list = QListWidget()
            
            for idx, name in output_devices:
                # Marcar con emoji si es el dispositivo guardado
                display_text = name
                if idx == saved_device:
                    display_text = f"✓ {name} (Configurado)"
                elif idx == current_device and saved_device is None:
                    display_text = f"⭐ {name} (Sistema)"
                
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, idx)
                device_list.addItem(item)
                
                # Seleccionar el dispositivo configurado o el actual
                if idx == (saved_device if saved_device is not None else current_device):
                    device_list.setCurrentItem(item)
                    # Hacer el texto en bold
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
            
            layout.addWidget(device_list)
            
            # Botones
            button_layout = QHBoxLayout()
            
            default_btn = QPushButton("🔄 Usar Predeterminado del Sistema")
            default_btn.clicked.connect(lambda: self._set_audio_device(None, dialog))
            button_layout.addWidget(default_btn)
            
            apply_btn = QPushButton("✅ Aplicar")
            apply_btn.clicked.connect(lambda: self._set_audio_device(
                device_list.currentItem().data(Qt.UserRole) if device_list.currentItem() else None,
                dialog
            ))
            button_layout.addWidget(apply_btn)
            
            cancel_btn = QPushButton("❌ Cancelar")
            cancel_btn.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_btn)
            
            layout.addLayout(button_layout)
            dialog.setLayout(layout)
            dialog.exec()
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Error al cargar dispositivos de audio:\n{str(e)}"
            )
    
    def _update_audio_device_btn_text(self, device_id):
        """Actualiza el texto del botón de dispositivo de audio con el nombre del dispositivo."""
        if not hasattr(self, 'audio_device_btn'):
            return
        try:
            import sounddevice as sd
            if device_id is None:
                self.audio_device_btn.setText("🔊 Dispositivo de Salida")
            else:
                name = sd.query_devices()[device_id]['name']
                short_name = (name[:24] + "…") if len(name) > 25 else name
                self.audio_device_btn.setText(f"🔊 {short_name}")
        except Exception:
            pass

    def _set_audio_device(self, device_id, dialog):
        """Establece el dispositivo de audio"""
        try:
            import sounddevice as sd
            from core.app_config import get_app_config
            
            # Guardar configuración
            app_config = get_app_config()
            app_config.set_audio_device(device_id)
            
            # Aplicar cambio inmediatamente
            if device_id is None:
                # Usar predeterminado del sistema
                sd.default.device = sd.default.device[0], None  # [input, default output]
                self.log_to_console("✅ Dispositivo de audio: Predeterminado del sistema")
            else:
                # Usar dispositivo específico
                sd.default.device = sd.default.device[0], device_id
                devices = sd.query_devices()
                device_name = devices[device_id]['name']
                self.log_to_console(f"✅ Dispositivo de audio: {device_name}")
            
            self._update_audio_device_btn_text(device_id)
            dialog.accept()
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Error al cambiar dispositivo de audio:\n{str(e)}"
            )
    
    def _load_audio_device_config(self):
        """Carga la configuración del dispositivo de audio al iniciar"""
        try:
            import sounddevice as sd
            from core.app_config import get_app_config
            
            
            app_config = get_app_config()
            device_id = app_config.get_audio_device()
            
            if device_id is None:
                self.log_to_console("🔊 Dispositivo de audio: Predeterminado del sistema")
            else:
                try:
                    devices = sd.query_devices()
                    device_name = devices[device_id]['name']
                    sd.default.device = sd.default.device[0], device_id
                    self.log_to_console(f"🔊 Dispositivo de audio: {device_name}")
                    self._update_audio_device_btn_text(device_id)
                except Exception as e:
                    self.log_to_console(f"⚠️ Error cargando dispositivo de audio configurado: {e}")
                    self.log_to_console("🔊 Usando dispositivo predeterminado del sistema")
                    
        except Exception as e:
            self.log_to_console(f"Error cargando configuración de audio: {e}")

    def _open_user_data_folder(self):
        """Abre el explorador de archivos en la carpeta de datos del usuario."""
        try:
            from core.paths import get_user_data_dir
            user_dir = get_user_data_dir()
            user_dir.mkdir(parents=True, exist_ok=True)
            path_str = str(user_dir)

            if sys.platform == "win32":
                os.startfile(path_str)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path_str])
            else:
                subprocess.Popen(["xdg-open", path_str])

            self.log_to_console(f"📂 Abriendo carpeta de usuario: {path_str}")
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"No se pudo abrir la carpeta de usuario:\n{str(e)}"
            )

    def show_overlay_conflicts(self, conflicts: list) -> None:
        """
        Muestra un diálogo informando que algunos archivos del overlay
        fueron actualizados pero el usuario tenía versiones editadas.
        La versión del usuario se guardó como .old para que no pierda su trabajo.
        """
        if not conflicts:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("🔄 Actualización del Overlay")
        dialog.resize(580, 420)
        layout = QVBoxLayout()

        # ── Encabezado ──────────────────────────────────────────────────────
        title = QLabel("📦 Nopolo se ha actualizado")
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QLabel(
            "Se detectaron cambios en los archivos del overlay que tú también habías editado.\n"
            "Tu versión fue guardada con extensión <b>.old</b> y se instaló la versión nueva."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #ccc; margin-bottom: 8px;")
        layout.addWidget(subtitle)

        # ── Lista de archivos afectados ─────────────────────────────────────
        group = QGroupBox("Archivos con conflicto")
        group_layout = QVBoxLayout()

        for conflict in conflicts:
            reason_html = (
                f"<br><span style='color:#f5c842; font-size:11px;'>💡 {conflict.reason}</span>"
                if conflict.reason else ""
            )
            item_label = QLabel(
                f"  📄 <b>{conflict.filename}</b>"
                f"{reason_html}<br>"
                f"  <span style='color:#aaa; font-size:11px;'>"
                f"Tu versión guardada: {conflict.old_path.name}"
                f"</span>"
            )
            item_label.setStyleSheet(
                "padding: 6px 10px; "
                "background: #2a2a2a; "
                "border-radius: 4px; "
                "margin: 2px 0;"
            )
            item_label.setTextFormat(Qt.TextFormat.RichText)
            group_layout.addWidget(item_label)

        group.setLayout(group_layout)
        layout.addWidget(group)

        # ── Mensaje de ayuda ────────────────────────────────────────────────
        help_text = QLabel(
            "💡 <b>¿Qué hacer?</b><br>"
            "• Puedes abrir tu carpeta de usuario para comparar los archivos.<br>"
            "• Si quieres restaurar tu versión, renombra el <code>.old</code> "
            "de vuelta al nombre original.<br>"
            "• Si prefieres la versión nueva, simplemente elimina el <code>.old</code>."
        )
        help_text.setWordWrap(True)
        help_text.setTextFormat(Qt.TextFormat.RichText)
        help_text.setStyleSheet(
            "background: #1e3a1e; border: 1px solid #2e6b2e; "
            "border-radius: 6px; padding: 10px; color: #aee8ae;"
        )
        layout.addWidget(help_text)

        # ── Botones ─────────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()

        open_folder_btn = QPushButton("📂 Abrir Carpeta de Usuario")
        open_folder_btn.clicked.connect(lambda: (self._open_user_data_folder(), dialog.accept()))
        btn_layout.addWidget(open_folder_btn)

        ok_btn = QPushButton("✅ Entendido")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)
        dialog.setLayout(layout)

        # Log en consola también
        for conflict in conflicts:
            self.log_to_console(
                f"⚠️ Overlay actualizado: {conflict.filename} "
                f"(tu versión guardada como {conflict.old_path.name})"
            )

        dialog.exec()

"""
Mixin para configuración del sistema y utilidades.
Contiene métodos para verificar conexión a internet y configurar dispositivos de audio.
"""
import os
import sys
import subprocess
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QMessageBox
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

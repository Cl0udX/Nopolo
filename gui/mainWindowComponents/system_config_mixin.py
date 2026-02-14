"""
Mixin para configuración del sistema y utilidades.
Contiene métodos para verificar conexión a internet y configurar dispositivos de audio.
"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QMessageBox
from PySide6.QtCore import Qt


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
            
            # Obtener lista de dispositivos
            devices = sd.query_devices()
            output_devices = []
            
            for i, device in enumerate(devices):
                if device['max_output_channels'] > 0:
                    output_devices.append((i, device['name']))
            
            # Obtener dispositivo actual
            current_device = sd.default.device[1]  # [input, output]
            
            # Crear diálogo
            dialog = QDialog(self)
            dialog.setWindowTitle("Configuración de Dispositivo de Audio")
            dialog.resize(500, 300)
            
            layout = QVBoxLayout()
            
            # Información
            info_label = QLabel("Selecciona el dispositivo de salida de audio:")
            layout.addWidget(info_label)
            
            # Lista de dispositivos
            device_list = QListWidget()
            
            for idx, name in output_devices:
                item = QListWidgetItem(f"{name}")
                item.setData(Qt.UserRole, idx)
                device_list.addItem(item)
                
                # Seleccionar el dispositivo actual
                if idx == current_device:
                    device_list.setCurrentItem(item)
            
            layout.addWidget(device_list)
            
            # Botones
            button_layout = QHBoxLayout()
            
            default_btn = QPushButton("Usar Predeterminado del Sistema")
            default_btn.clicked.connect(lambda: self._set_audio_device(None, dialog))
            button_layout.addWidget(default_btn)
            
            apply_btn = QPushButton("Aplicar")
            apply_btn.clicked.connect(lambda: self._set_audio_device(
                device_list.currentItem().data(Qt.UserRole) if device_list.currentItem() else None,
                dialog
            ))
            button_layout.addWidget(apply_btn)
            
            cancel_btn = QPushButton("Cancelar")
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
            
            if device_id is None:
                # Usar predeterminado del sistema
                sd.default.device = sd.default.device[0], None  # [input, default output]
                self.log_to_console("Dispositivo de audio: Predeterminado del sistema")
            else:
                # Usar dispositivo específico
                sd.default.device = sd.default.device[0], device_id
                devices = sd.query_devices()
                device_name = devices[device_id]['name']
                self.log_to_console(f"Dispositivo de audio: {device_name}")
            
            dialog.accept()
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Error al cambiar dispositivo de audio:\n{str(e)}"
            )

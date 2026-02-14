"""
Diálogo de gestión de efectos de sonido y fondos.

Permite:
- Ver lista de efectos y fondos en formato tabla
- Agregar nuevos efectos/fondos
- Editar existentes
- Eliminar (solo efectos/fondos, no filtros integrados)
- Probar reproducción
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QCheckBox, QLineEdit, QLabel, QFileDialog,
                               QSlider, QDoubleSpinBox, QTextEdit, QMessageBox,
                               QComboBox, QWidget, QGroupBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
import os

from core.sound_manager import SoundManager
from core.background_manager import BackgroundManager


class EffectsManagerDialog(QDialog):
    """Diálogo para gestionar efectos de sonido y fondos."""
    
    effects_updated = Signal()  # Señal cuando se actualiza la lista
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestor de Efectos y Fondos")
        self.resize(900, 600)
        
        # Managers
        self.sound_manager = SoundManager()
        self.background_manager = BackgroundManager()
        
        # Setup UI
        self._setup_ui()
        self._load_effects_table()
    
    def _setup_ui(self):
        """Configura la interfaz."""
        layout = QVBoxLayout(self)
        
        # Título
        title = QLabel("Gestión de Efectos de Sonido y Fondos")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Tabla de efectos
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Nombre", "Tipo", "Volumen", "Acciones", "Preview"
        ])
        
        # Configurar tabla
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.table)
        
        # Botón agregar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_add = QPushButton("➕ Agregar Nuevo")
        self.btn_add.clicked.connect(self._show_add_dialog)
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        btn_layout.addWidget(self.btn_add)
        
        layout.addLayout(btn_layout)
    
    def _load_effects_table(self):
        """Carga todos los efectos en la tabla."""
        self.table.setRowCount(0)
        
        # Cargar sonidos
        sounds = self.sound_manager.list_sounds()
        for sound_data in sounds:
            self._add_table_row(
                sound_data.get('id', ''),
                sound_data.get('name', ''),
                'Sonido',
                1.0,  # Los sonidos no tienen volumen configurable
                sound_data.get('filename', ''),
                sound_data.get('category', '')
            )
        
        # Cargar fondos
        backgrounds = self.background_manager.list_backgrounds()
        for bg_id, bg_data in backgrounds.items():
            self._add_table_row(
                bg_id,
                bg_data.get('name', ''),
                'Fondo',
                bg_data.get('volume', 0.3),
                bg_data.get('path', ''),
                bg_data.get('description', '')
            )
    
    def _add_table_row(self, effect_id, name, effect_type, volume, path, description):
        """Agrega una fila a la tabla."""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # ID
        self.table.setItem(row, 0, QTableWidgetItem(str(effect_id)))
        
        # Nombre
        self.table.setItem(row, 1, QTableWidgetItem(name))
        
        # Tipo
        self.table.setItem(row, 2, QTableWidgetItem(effect_type))
        
        # Volumen
        vol_text = "-" if effect_type == "Sonido" else f"{volume:.2f}"
        self.table.setItem(row, 3, QTableWidgetItem(vol_text))
        
        # Botones de acción
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(5, 2, 5, 2)
        
        # Botón editar
        btn_edit = QPushButton("✏️")
        btn_edit.setToolTip("Editar")
        btn_edit.setMaximumWidth(40)
        btn_edit.clicked.connect(lambda: self._edit_effect(effect_id, effect_type))
        actions_layout.addWidget(btn_edit)
        
        # Botón eliminar (solo para efectos/fondos, no filtros integrados)
        btn_delete = QPushButton("🗑️")
        btn_delete.setToolTip("Eliminar")
        btn_delete.setMaximumWidth(40)
        btn_delete.clicked.connect(lambda: self._delete_effect(effect_id, effect_type))
        actions_layout.addWidget(btn_delete)
        
        self.table.setCellWidget(row, 4, actions_widget)
        
        # Botón preview
        btn_preview = QPushButton("▶️")
        btn_preview.setToolTip("Reproducir preview")
        btn_preview.setMaximumWidth(40)
        btn_preview.clicked.connect(lambda: self._play_preview(effect_id, effect_type))
        self.table.setCellWidget(row, 5, btn_preview)
    
    def _show_add_dialog(self):
        """Muestra el diálogo para agregar un nuevo efecto."""
        dialog = EffectEditorDialog(self, is_new=True)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_effects_table()
            self.effects_updated.emit()
    
    def _edit_effect(self, effect_id, effect_type):
        """Edita un efecto existente."""
        # Cargar datos del efecto
        if effect_type == "Sonido":
            data = self.sound_manager.get_sound(effect_id)
        else:
            data = self.background_manager.get_background(effect_id)
        
        if data:
            dialog = EffectEditorDialog(self, is_new=False, effect_data=data, effect_type=effect_type)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._load_effects_table()
                self.effects_updated.emit()
    
    def _delete_effect(self, effect_id, effect_type):
        """Elimina un efecto."""
        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Estás seguro de eliminar el {effect_type.lower()} '{effect_id}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # TODO: Implementar eliminación en los managers
            QMessageBox.information(self, "Info", "Funcionalidad de eliminación próximamente")
            # self._load_effects_table()
            # self.effects_updated.emit()
    
    def _play_preview(self, effect_id, effect_type):
        """Reproduce un preview del efecto."""
        try:
            import soundfile as sf
            import sounddevice as sd
            
            if effect_type == "Sonido":
                result = self.sound_manager.load_sound_audio(effect_id)
                if result:
                    audio, sr = result
                    sd.play(audio, sr)
                    sd.wait()
            else:
                result = self.background_manager.load_background_audio(effect_id)
                if result:
                    audio, sr, volume = result
                    # Reproducir solo 3 segundos del fondo
                    duration = min(len(audio), sr * 3)
                    sd.play(audio[:duration], sr)
                    sd.wait()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo reproducir: {e}")


class EffectEditorDialog(QDialog):
    """Diálogo para agregar/editar un efecto."""
    
    def __init__(self, parent=None, is_new=True, effect_data=None, effect_type="Sonido"):
        super().__init__(parent)
        self.is_new = is_new
        self.effect_data = effect_data or {}
        self.effect_type = effect_type
        
        self.setWindowTitle("Agregar Efecto" if is_new else "Editar Efecto")
        self.resize(500, 400)
        
        self.sound_manager = SoundManager()
        self.background_manager = BackgroundManager()
        
        self._setup_ui()
        
        if not is_new and effect_data:
            self._load_data()
    
    def _setup_ui(self):
        """Configura la interfaz del editor."""
        layout = QVBoxLayout(self)
        
        # Selector de tipo (solo para nuevos)
        if self.is_new:
            type_group = QGroupBox("Tipo de Efecto")
            type_layout = QVBoxLayout()
            
            self.radio_sound = QCheckBox("Sonido (se inserta entre voces)")
            self.radio_background = QCheckBox("Fondo (se mezcla con las voces)")
            
            # Solo uno puede estar marcado
            self.radio_sound.toggled.connect(lambda checked: self.radio_background.setChecked(not checked) if checked else None)
            self.radio_background.toggled.connect(lambda checked: self.radio_sound.setChecked(not checked) if checked else None)
            
            self.radio_sound.setChecked(True)
            
            type_layout.addWidget(self.radio_sound)
            type_layout.addWidget(self.radio_background)
            type_group.setLayout(type_layout)
            layout.addWidget(type_group)
        
        # ID
        id_layout = QHBoxLayout()
        id_layout.addWidget(QLabel("ID:"))
        self.input_id = QLineEdit()
        self.input_id.setPlaceholderText("Ej: disparo, fa, fb (opcional, se asigna automático)")
        if not self.is_new:
            self.input_id.setEnabled(False)
        id_layout.addWidget(self.input_id)
        layout.addLayout(id_layout)
        
        # Nombre
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nombre:"))
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Ej: Disparo, Calle, Lluvia")
        name_layout.addWidget(self.input_name)
        layout.addLayout(name_layout)
        
        # Archivo
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Archivo:"))
        self.input_file = QLineEdit()
        self.input_file.setReadOnly(True)
        file_layout.addWidget(self.input_file)
        
        self.btn_browse = QPushButton("Examinar...")
        self.btn_browse.clicked.connect(self._browse_file)
        file_layout.addWidget(self.btn_browse)
        layout.addLayout(file_layout)
        
        # Volumen (solo para fondos)
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("Volumen:"))
        
        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setMinimum(0)
        self.slider_volume.setMaximum(100)
        self.slider_volume.setValue(30)
        self.slider_volume.valueChanged.connect(self._update_volume_spinbox)
        volume_layout.addWidget(self.slider_volume)
        
        self.spinbox_volume = QDoubleSpinBox()
        self.spinbox_volume.setMinimum(0.0)
        self.spinbox_volume.setMaximum(1.0)
        self.spinbox_volume.setSingleStep(0.01)
        self.spinbox_volume.setValue(0.3)
        self.spinbox_volume.valueChanged.connect(self._update_volume_slider)
        volume_layout.addWidget(self.spinbox_volume)
        
        layout.addLayout(volume_layout)
        self.volume_widgets = [self.slider_volume, self.spinbox_volume, volume_layout.itemAt(0).widget()]
        
        # Descripción
        layout.addWidget(QLabel("Descripción:"))
        self.input_description = QTextEdit()
        self.input_description.setMaximumHeight(80)
        self.input_description.setPlaceholderText("Descripción opcional del efecto")
        layout.addWidget(self.input_description)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        
        self.btn_save = QPushButton("Guardar")
        self.btn_save.clicked.connect(self._save_effect)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        btn_layout.addWidget(self.btn_save)
        
        layout.addLayout(btn_layout)
        
        # Actualizar visibilidad de volumen
        if self.is_new:
            self.radio_sound.toggled.connect(self._update_volume_visibility)
            self._update_volume_visibility()
    
    def _update_volume_visibility(self):
        """Muestra/oculta controles de volumen según el tipo."""
        is_background = self.radio_background.isChecked() if self.is_new else self.effect_type == "Fondo"
        for widget in self.volume_widgets:
            widget.setVisible(is_background)
    
    def _update_volume_slider(self, value):
        """Actualiza el slider cuando cambia el spinbox."""
        self.slider_volume.blockSignals(True)
        self.slider_volume.setValue(int(value * 100))
        self.slider_volume.blockSignals(False)
    
    def _update_volume_spinbox(self, value):
        """Actualiza el spinbox cuando cambia el slider."""
        self.spinbox_volume.blockSignals(True)
        self.spinbox_volume.setValue(value / 100.0)
        self.spinbox_volume.blockSignals(False)
    
    def _browse_file(self):
        """Abre diálogo para seleccionar archivo de audio."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de audio",
            "",
            "Archivos de audio (*.wav *.mp3 *.flac *.ogg);;Todos los archivos (*.*)"
        )
        
        if file_path:
            self.input_file.setText(file_path)
    
    def _load_data(self):
        """Carga datos existentes en el formulario."""
        self.input_id.setText(self.effect_data.get('id', ''))
        self.input_name.setText(self.effect_data.get('name', ''))
        self.input_file.setText(self.effect_data.get('path', ''))
        self.input_description.setText(self.effect_data.get('description', ''))
        
        if self.effect_type == "Fondo":
            volume = self.effect_data.get('volume', 0.3)
            self.spinbox_volume.setValue(volume)
            self.slider_volume.setValue(int(volume * 100))
    
    def _save_effect(self):
        """Guarda el efecto."""
        # Validar datos
        name = self.input_name.text().strip()
        file_path = self.input_file.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", "El nombre es requerido")
            return
        
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Error", "Debes seleccionar un archivo válido")
            return
        
        # Determinar tipo
        if self.is_new:
            is_background = self.radio_background.isChecked()
        else:
            is_background = self.effect_type == "Fondo"
        
        # Generar ID si no se proporcionó
        effect_id = self.input_id.text().strip()
        if not effect_id:
            if is_background:
                # Generar ID para fondo (fa, fb, fc, ...)
                existing_ids = list(self.background_manager.backgrounds_by_id.keys())
                for letter in 'abcdefghijklmnopqrstuvwxyz':
                    candidate = f'f{letter}'
                    if candidate not in existing_ids:
                        effect_id = candidate
                        break
            else:
                # Generar ID numérico para sonido
                existing_ids = [int(sid) for sid in self.sound_manager.sounds_by_id.keys() if sid.isdigit()]
                effect_id = str(max(existing_ids) + 1) if existing_ids else "1"
        
        description = self.input_description.toPlainText().strip()
        
        try:
            if is_background:
                volume = self.spinbox_volume.value()
                
                if self.is_new:
                    # Crear nuevo fondo
                    self.background_manager.add_background(
                        bg_id=effect_id,
                        name=name,
                        path=file_path,
                        description=description,
                        volume=volume
                    )
                else:
                    # Actualizar fondo existente
                    self.background_manager.update_background(
                        bg_id=effect_id,
                        name=name,
                        path=file_path,
                        description=description,
                        volume=volume
                    )
            else:
                # Para sonidos, usar solo el nombre del archivo
                filename = os.path.basename(file_path)
                
                if self.is_new:
                    # Crear nuevo sonido
                    self.sound_manager.add_sound(
                        sound_id=effect_id,
                        name=name,
                        filename=filename,
                        category=description or "custom"
                    )
                else:
                    # Actualizar sonido existente
                    self.sound_manager.update_sound(
                        sound_id=effect_id,
                        name=name,
                        filename=filename,
                        category=description or "custom"
                    )
            
            QMessageBox.information(self, "Éxito", f"{'Fondo' if is_background else 'Sonido'} guardado correctamente")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar: {e}")

"""
Mixin para gestión de tablas (filtros, sonidos, fondos).
Contiene métodos para cargar y popular las tablas de la UI.
"""
from PySide6.QtWidgets import QPushButton, QTableWidgetItem


class TableManagerMixin:
    """Mixin para gestión de tablas de efectos y fondos"""
    
    def _load_filters_table(self):
        """Carga SOLO los filtros integrados (predefinidos)"""
        self.filters_table.setRowCount(0)
        
        # Filtros integrados (no editables, no eliminables)
        integrated_filters = [
            ('r', 'Eco/Reverberación', 'Agrega eco y reverberación'),
            ('p', 'Llamada', 'Efecto de llamada telefónica'),
            ('pu', 'Aguda', 'Aumenta el pitch (chipmunk)'),
            ('pd', 'Grave', 'Reduce el pitch (monstruo)'),
            ('m', 'Apagada', 'Voz amortiguada (desde afuera)'),
            ('a', 'Robot', 'Efecto de voz sintética/android'),
            ('l', 'Saturada', 'Distorsión/saturación'),
        ]
        
        for filter_id, name, description in integrated_filters:
            self._add_filter_row(filter_id, name, description)
    
    def _load_sounds_table(self):
        """Carga SOLO los sonidos personalizados"""
        self.sounds_table.setRowCount(0)
        
        # Cargar sonidos desde SoundManager
        sounds = self.sound_manager.list_sounds()
        for sound_data in sounds:
            self._add_sound_row(sound_data)
    
    def _load_backgrounds_table(self):
        """Carga SOLO los fondos personalizados"""
        self.backgrounds_table.setRowCount(0)
        
        # Cargar fondos desde BackgroundManager
        backgrounds = self.background_manager.list_backgrounds()
        for bg_id, bg_data in backgrounds.items():
            self._add_background_row(bg_id, bg_data)
    
    def _add_filter_row(self, filter_id, name, description):
        """Agrega un filtro integrado (solo preview, NO editable ni eliminable)"""
        row = self.filters_table.rowCount()
        self.filters_table.insertRow(row)
        
        # ID
        id_item = QTableWidgetItem(str(filter_id))
        self.filters_table.setItem(row, 0, id_item)
        
        # Nombre
        name_item = QTableWidgetItem(name)
        self.filters_table.setItem(row, 1, name_item)
        
        # Descripción
        desc_item = QTableWidgetItem(description)
        self.filters_table.setItem(row, 2, desc_item)
        
        # Volumen (no aplica para filtros)
        vol_item = QTableWidgetItem('-')
        self.filters_table.setItem(row, 3, vol_item)
        
        # Botón preview (test con voz actual)
        btn_preview = QPushButton("▶️")
        btn_preview.setToolTip(f"Probar filtro '{filter_id}' con la voz actual")
        btn_preview.setMaximumWidth(40)
        btn_preview.clicked.connect(lambda: self._test_integrated_filter(filter_id, name))
        self.filters_table.setCellWidget(row, 4, btn_preview)
    
    def _add_sound_row(self, sound_data):
        """Agrega un sonido personalizado (con editar/eliminar)"""
        row = self.sounds_table.rowCount()
        self.sounds_table.insertRow(row)
        
        sound_id = sound_data.get('id', '')
        name = sound_data.get('name', '')
        
        # ID
        id_item = QTableWidgetItem(str(sound_id))
        self.sounds_table.setItem(row, 0, id_item)
        
        # Nombre
        name_item = QTableWidgetItem(name)
        self.sounds_table.setItem(row, 1, name_item)
        
        # Tipo
        type_item = QTableWidgetItem('Sonido')
        self.sounds_table.setItem(row, 2, type_item)
        
        # Volumen
        vol_item = QTableWidgetItem('-')
        self.sounds_table.setItem(row, 3, vol_item)
        
        # Botón preview
        btn_preview = QPushButton("▶️")
        btn_preview.setToolTip("Reproducir sonido")
        btn_preview.setMaximumWidth(40)
        btn_preview.clicked.connect(lambda: self._play_sound_preview(sound_id))
        self.sounds_table.setCellWidget(row, 4, btn_preview)
        
        # Botón editar
        btn_edit = QPushButton("✏️")
        btn_edit.setToolTip("Editar sonido")
        btn_edit.setMaximumWidth(40)
        btn_edit.clicked.connect(lambda: self._edit_sound(sound_id, sound_data))
        self.sounds_table.setCellWidget(row, 5, btn_edit)
        
        # Botón eliminar
        btn_delete = QPushButton("🗑️")
        btn_delete.setToolTip("Eliminar sonido")
        btn_delete.setMaximumWidth(40)
        btn_delete.clicked.connect(lambda: self._delete_sound(sound_id))
        self.sounds_table.setCellWidget(row, 6, btn_delete)
    
    def _add_background_row(self, bg_id, bg_data):
        """Agrega un fondo personalizado (con editar/eliminar)"""
        row = self.backgrounds_table.rowCount()
        self.backgrounds_table.insertRow(row)
        
        name = bg_data.get('name', '')
        volume = bg_data.get('volume', 0.3)
        
        # ID
        id_item = QTableWidgetItem(str(bg_id))
        self.backgrounds_table.setItem(row, 0, id_item)
        
        # Nombre
        name_item = QTableWidgetItem(name)
        self.backgrounds_table.setItem(row, 1, name_item)
        
        # Tipo
        type_item = QTableWidgetItem('Fondo')
        self.backgrounds_table.setItem(row, 2, type_item)
        
        # Volumen
        vol_item = QTableWidgetItem(f"{volume:.2f}")
        self.backgrounds_table.setItem(row, 3, vol_item)
        
        # Botón preview
        btn_preview = QPushButton("▶️")
        btn_preview.setToolTip("Reproducir fondo")
        btn_preview.setMaximumWidth(40)
        btn_preview.clicked.connect(lambda: self._play_background_preview(bg_id))
        self.backgrounds_table.setCellWidget(row, 4, btn_preview)
        
        # Botón editar
        btn_edit = QPushButton("✏️")
        btn_edit.setToolTip("Editar fondo")
        btn_edit.setMaximumWidth(40)
        btn_edit.clicked.connect(lambda: self._edit_background(bg_id, bg_data))
        self.backgrounds_table.setCellWidget(row, 5, btn_edit)
        
        # Botón eliminar
        btn_delete = QPushButton("🗑️")
        btn_delete.setToolTip("Eliminar fondo")
        btn_delete.setMaximumWidth(40)
        btn_delete.clicked.connect(lambda: self._delete_background(bg_id))
        self.backgrounds_table.setCellWidget(row, 6, btn_delete)

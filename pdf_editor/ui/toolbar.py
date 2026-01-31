"""
Barra de herramientas del editor de PDF.
"""

from PyQt5.QtWidgets import (
    QToolBar, QAction, QComboBox, QLabel, QWidget, QHBoxLayout,
    QSpinBox, QToolButton, QMenu, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QKeySequence, QFont


class EditorToolBar(QToolBar):
    """Barra de herramientas principal del editor."""
    
    # Señales
    openFile = pyqtSignal()
    saveFile = pyqtSignal()
    saveFileAs = pyqtSignal()
    closeFile = pyqtSignal()  # Nueva señal para cerrar PDF
    
    zoomIn = pyqtSignal()
    zoomOut = pyqtSignal()
    zoomChanged = pyqtSignal(float)
    fitWidth = pyqtSignal()
    fitPage = pyqtSignal()
    
    toolSelected = pyqtSignal(str)  # 'select', 'highlight', 'delete', 'edit'
    
    undoAction = pyqtSignal()
    redoAction = pyqtSignal()
    
    pageChanged = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__("Herramientas", parent)
        
        self.setMovable(False)
        self.setFloatable(False)
        self.setIconSize(QSize(24, 24))
        
        # Estilo mejorado
        self.setStyleSheet("""
            QToolBar {
                background-color: #2d2d30;
                border: none;
                spacing: 8px;
                padding: 8px;
            }
            QToolBar::separator {
                background-color: #555;
                width: 1px;
                margin: 5px 10px;
            }
        """)
        
        self.current_tool = 'select'
        self.tool_actions = {}
        
        self.setup_actions()
    
    def setup_actions(self):
        """Configura todas las acciones de la barra."""
        
        # === Sección Archivo ===
        self.action_open = QAction("📂 Abrir", self)
        self.action_open.setShortcut(QKeySequence.Open)
        self.action_open.setToolTip("Abrir archivo PDF (Ctrl+O)")
        self.action_open.triggered.connect(self.openFile.emit)
        self.addAction(self.action_open)
        
        self.action_save = QAction("💾 Guardar", self)
        self.action_save.setShortcut(QKeySequence.Save)
        self.action_save.setToolTip("Guardar cambios (Ctrl+S)")
        self.action_save.triggered.connect(self.saveFile.emit)
        self.action_save.setEnabled(False)
        self.addAction(self.action_save)
        
        self.action_save_as = QAction("💾 Guardar como...", self)
        self.action_save_as.setShortcut(QKeySequence.SaveAs)
        self.action_save_as.setToolTip("Guardar como nuevo archivo (Ctrl+Shift+S)")
        self.action_save_as.triggered.connect(self.saveFileAs.emit)
        self.action_save_as.setEnabled(False)
        self.addAction(self.action_save_as)
        
        # Botón para cerrar PDF y abrir otro
        self.action_close = QAction("❌ Cerrar PDF", self)
        self.action_close.setShortcut("Ctrl+W")
        self.action_close.setToolTip("Cerrar PDF actual para abrir otro (Ctrl+W)")
        self.action_close.triggered.connect(self.closeFile.emit)
        self.action_close.setEnabled(False)
        self.addAction(self.action_close)
        
        self.addSeparator()
        
        # === Sección Deshacer/Rehacer ===
        self.action_undo = QAction("↩️ Deshacer", self)
        self.action_undo.setShortcut(QKeySequence.Undo)
        self.action_undo.setToolTip("Deshacer última acción (Ctrl+Z)")
        self.action_undo.triggered.connect(self.undoAction.emit)
        self.action_undo.setEnabled(False)
        self.addAction(self.action_undo)
        
        self.action_redo = QAction("↪️ Rehacer", self)
        self.action_redo.setShortcut(QKeySequence.Redo)
        self.action_redo.setToolTip("Rehacer acción (Ctrl+Y)")
        self.action_redo.triggered.connect(self.redoAction.emit)
        self.action_redo.setEnabled(False)
        self.addAction(self.action_redo)
        
        self.addSeparator()
        
        # === Sección Herramientas de Edición (MÁS PROMINENTES) ===
        
        # Espaciador
        spacer1 = QWidget()
        spacer1.setFixedWidth(10)
        self.addWidget(spacer1)
        
        # BOTÓN DE ELIMINAR MÁS PROMINENTE (HERRAMIENTA PRINCIPAL)
        self.action_delete = QAction("🗑️ ELIMINAR", self)
        self.action_delete.setToolTip("Arrastra sobre el contenido para eliminarlo permanentemente")
        self.action_delete.setCheckable(True)
        self.action_delete.setChecked(True)  # Por defecto activo
        self.action_delete.triggered.connect(lambda: self.set_tool('delete'))
        self.addAction(self.action_delete)
        self.tool_actions['delete'] = self.action_delete
        
        self.action_edit = QAction("✏️ EDITAR", self)
        self.action_edit.setToolTip("Click para editar texto o añadir texto nuevo")
        self.action_edit.setCheckable(True)
        self.action_edit.triggered.connect(lambda: self.set_tool('edit'))
        self.addAction(self.action_edit)
        self.tool_actions['edit'] = self.action_edit
        
        self.action_highlight = QAction("🖍️ Resaltar", self)
        self.action_highlight.setToolTip("Herramienta de resaltado")
        self.action_highlight.setCheckable(True)
        self.action_highlight.triggered.connect(lambda: self.set_tool('highlight'))
        self.addAction(self.action_highlight)
        self.tool_actions['highlight'] = self.action_highlight
        
        # Espaciador
        spacer2 = QWidget()
        spacer2.setFixedWidth(10)
        self.addWidget(spacer2)
        
        self.addSeparator()
        
        # === Sección Zoom ===
        self.action_zoom_out = QAction("🔍- Alejar", self)
        self.action_zoom_out.setToolTip("Alejar (Ctrl+-)")
        self.action_zoom_out.setShortcut("Ctrl+-")
        self.action_zoom_out.triggered.connect(self.zoomOut.emit)
        self.addAction(self.action_zoom_out)
        
        # Combo de zoom
        self.zoom_combo = QComboBox()
        self.zoom_combo.setEditable(True)
        self.zoom_combo.setFixedWidth(80)
        zoom_levels = ['25%', '50%', '75%', '100%', '125%', '150%', '200%', '300%', '400%']
        self.zoom_combo.addItems(zoom_levels)
        self.zoom_combo.setCurrentText('100%')
        self.zoom_combo.currentTextChanged.connect(self.on_zoom_changed)
        self.addWidget(self.zoom_combo)
        
        self.action_zoom_in = QAction("🔍+ Acercar", self)
        self.action_zoom_in.setToolTip("Acercar (Ctrl++)")
        self.action_zoom_in.setShortcut("Ctrl++")
        self.action_zoom_in.triggered.connect(self.zoomIn.emit)
        self.addAction(self.action_zoom_in)
        
        self.action_fit_width = QAction("↔️ Ajustar ancho", self)
        self.action_fit_width.setToolTip("Ajustar al ancho de la ventana")
        self.action_fit_width.triggered.connect(self.fitWidth.emit)
        self.addAction(self.action_fit_width)
        
        self.action_fit_page = QAction("📄 Ajustar página", self)
        self.action_fit_page.setToolTip("Ver página completa")
        self.action_fit_page.triggered.connect(self.fitPage.emit)
        self.addAction(self.action_fit_page)
        
        self.addSeparator()
        
        # === Sección Navegación ===
        self.action_prev_page = QAction("◀️ Anterior", self)
        self.action_prev_page.setToolTip("Página anterior (Page Up)")
        self.action_prev_page.setShortcut(QKeySequence.MoveToPreviousPage)
        self.action_prev_page.triggered.connect(self.go_prev_page)
        self.addAction(self.action_prev_page)
        
        # Indicador de página
        self.page_widget = QWidget()
        page_layout = QHBoxLayout(self.page_widget)
        page_layout.setContentsMargins(5, 0, 5, 0)
        
        self.page_label = QLabel("Página:")
        page_layout.addWidget(self.page_label)
        
        self.page_spinbox = QSpinBox()
        self.page_spinbox.setMinimum(1)
        self.page_spinbox.setMaximum(1)
        self.page_spinbox.setFixedWidth(60)
        self.page_spinbox.valueChanged.connect(self.on_page_changed)
        page_layout.addWidget(self.page_spinbox)
        
        self.total_pages_label = QLabel("de 0")
        page_layout.addWidget(self.total_pages_label)
        
        self.addWidget(self.page_widget)
        
        self.action_next_page = QAction("▶️ Siguiente", self)
        self.action_next_page.setToolTip("Página siguiente (Page Down)")
        self.action_next_page.setShortcut(QKeySequence.MoveToNextPage)
        self.action_next_page.triggered.connect(self.go_next_page)
        self.addAction(self.action_next_page)
    
    def set_tool(self, tool: str):
        """Establece la herramienta actual."""
        self.current_tool = tool
        
        # Actualizar estado de los botones
        for name, action in self.tool_actions.items():
            action.setChecked(name == tool)
        
        self.toolSelected.emit(tool)
    
    def on_zoom_changed(self, text: str):
        """Maneja el cambio de zoom desde el combo."""
        try:
            zoom = float(text.replace('%', '')) / 100.0
            self.zoomChanged.emit(zoom)
        except ValueError:
            pass
    
    def update_zoom_display(self, zoom: float):
        """Actualiza el display del zoom."""
        self.zoom_combo.setCurrentText(f'{int(zoom * 100)}%')
    
    def on_page_changed(self, page: int):
        """Maneja el cambio de página desde el spinbox."""
        self.pageChanged.emit(page - 1)  # Convertir a índice base 0
    
    def go_prev_page(self):
        """Va a la página anterior."""
        current = self.page_spinbox.value()
        if current > 1:
            self.page_spinbox.setValue(current - 1)
    
    def go_next_page(self):
        """Va a la página siguiente."""
        current = self.page_spinbox.value()
        if current < self.page_spinbox.maximum():
            self.page_spinbox.setValue(current + 1)
    
    def set_page_count(self, count: int):
        """Establece el número total de páginas."""
        self.page_spinbox.setMaximum(max(1, count))
        self.total_pages_label.setText(f"de {count}")
    
    def set_current_page(self, page: int):
        """Establece la página actual (índice base 0)."""
        self.page_spinbox.blockSignals(True)
        self.page_spinbox.setValue(page + 1)
        self.page_spinbox.blockSignals(False)
    
    def set_document_loaded(self, loaded: bool):
        """Actualiza el estado de las acciones según si hay documento cargado."""
        self.action_save.setEnabled(loaded)
        self.action_save_as.setEnabled(loaded)
        self.action_close.setEnabled(loaded)
        
        for action in self.tool_actions.values():
            action.setEnabled(loaded)
        
        self.action_zoom_in.setEnabled(loaded)
        self.action_zoom_out.setEnabled(loaded)
        self.zoom_combo.setEnabled(loaded)
        self.action_fit_width.setEnabled(loaded)
        self.action_fit_page.setEnabled(loaded)
        
        self.action_prev_page.setEnabled(loaded)
        self.action_next_page.setEnabled(loaded)
        self.page_spinbox.setEnabled(loaded)
    
    def update_undo_redo(self, can_undo: bool, can_redo: bool):
        """Actualiza el estado de deshacer/rehacer."""
        self.action_undo.setEnabled(can_undo)
        self.action_redo.setEnabled(can_redo)

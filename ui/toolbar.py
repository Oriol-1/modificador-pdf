"""
Barra de herramientas del editor de PDF con FlowLayout responsive.
Los botones se redistribuyen en múltiples filas cuando la ventana se hace pequeña.
"""

from PyQt5.QtWidgets import (
    QAction, QComboBox, QLabel, QWidget, QHBoxLayout,
    QSpinBox, QToolButton, QMenu, QSizePolicy, QLayout, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QRect, QPoint
from PyQt5.QtGui import QKeySequence

from ui.theme_manager import ThemeColor


class FlowLayout(QLayout):
    """Layout que distribuye widgets en filas, bajando a la siguiente cuando no caben."""

    def __init__(self, parent=None, margin=8, h_spacing=4, v_spacing=4):
        super().__init__(parent)
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self._items = []
        if margin >= 0:
            self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only):
        margins = self.contentsMargins()
        effective = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x = effective.x()
        y = effective.y()
        row_height = 0

        for item in self._items:
            widget = item.widget()
            if widget and not widget.isVisible():
                continue
            item_size = item.sizeHint()
            next_x = x + item_size.width() + self._h_spacing
            if next_x - self._h_spacing > effective.right() + 1 and row_height > 0:
                x = effective.x()
                y += row_height + self._v_spacing
                next_x = x + item_size.width() + self._h_spacing
                row_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item_size))
            x = next_x
            row_height = max(row_height, item_size.height())

        return y + row_height - rect.y() + margins.bottom()


class _ToolbarSeparator(QFrame):
    """Separador visual vertical para la toolbar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.VLine)
        self.setFixedWidth(2)
        self.setFixedHeight(28)
        self.setStyleSheet(f"color: {ThemeColor.BORDER_LIGHT};")


# Estilo base compartido por todos los QToolButton de la toolbar
_BUTTON_STYLE = f"""
    QToolButton {{
        background-color: transparent;
        color: white;
        border: none;
        padding: 4px 8px;
        font-size: 13px;
        border-radius: 3px;
    }}
    QToolButton:hover {{
        background-color: {ThemeColor.BG_HOVER};
    }}
    QToolButton:checked {{
        background-color: {ThemeColor.ACCENT};
        color: white;
    }}
    QToolButton:disabled {{
        color: #666666;
    }}
    QToolButton::menu-indicator {{
        image: none;
        width: 0px;
    }}
"""


def _make_button(action, parent=None):
    """Crea un QToolButton vinculado a una QAction."""
    btn = QToolButton(parent)
    btn.setDefaultAction(action)
    btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
    btn.setStyleSheet(_BUTTON_STYLE)
    btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    return btn


class EditorToolBar(QWidget):
    """Barra de herramientas principal del editor con reflow automático."""

    # Señales (API idéntica a la versión anterior)
    openFile = pyqtSignal()
    insertPdf = pyqtSignal()
    saveFile = pyqtSignal()
    saveFileAs = pyqtSignal()
    closeFile = pyqtSignal()

    zoomIn = pyqtSignal()
    zoomOut = pyqtSignal()
    zoomChanged = pyqtSignal(float)
    fitWidth = pyqtSignal()

    toolSelected = pyqtSignal(str)

    undoAction = pyqtSignal()
    redoAction = pyqtSignal()

    rotatePageRequested = pyqtSignal(int)

    compressRequested = pyqtSignal()
    pageManagerRequested = pyqtSignal()

    pageChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {ThemeColor.BG_SECONDARY};")

        self._flow = FlowLayout(self, margin=6, h_spacing=2, v_spacing=2)

        # Size policy: la toolbar usa heightForWidth para ajustar su alto
        sp = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sp.setHeightForWidth(True)
        self.setSizePolicy(sp)

        self.current_tool = 'select'
        self.tool_actions = {}

        self._setup_actions()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._flow.heightForWidth(width)

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------

    def _setup_actions(self):
        """Configura todas las acciones y botones."""

        # === Archivo ===
        self.action_open = QAction("📂 Abrir", self)
        self.action_open.setShortcut(QKeySequence.Open)
        self.action_open.setToolTip("Abrir archivo PDF (Ctrl+O)")
        self.action_open.triggered.connect(self.openFile.emit)
        self._flow.addWidget(_make_button(self.action_open, self))

        self.action_insert_pdf = QAction("📄 Insertar PDF", self)
        self.action_insert_pdf.setShortcut("Ctrl+Shift+I")
        self.action_insert_pdf.setToolTip("Insertar otro PDF en el documento actual (Ctrl+Shift+I)")
        self.action_insert_pdf.triggered.connect(self.insertPdf.emit)
        self.action_insert_pdf.setEnabled(False)
        self._flow.addWidget(_make_button(self.action_insert_pdf, self))

        self.action_save = QAction("💾 Guardar", self)
        self.action_save.setShortcut(QKeySequence.Save)
        self.action_save.setToolTip("Guardar cambios (Ctrl+S)")
        self.action_save.triggered.connect(self.saveFile.emit)
        self.action_save.setEnabled(False)
        self._flow.addWidget(_make_button(self.action_save, self))

        self.action_save_as = QAction("💾 Guardar como...", self)
        self.action_save_as.setShortcut(QKeySequence.SaveAs)
        self.action_save_as.setToolTip("Guardar como nuevo archivo (Ctrl+Shift+S)")
        self.action_save_as.triggered.connect(self.saveFileAs.emit)
        self.action_save_as.setEnabled(False)
        self._flow.addWidget(_make_button(self.action_save_as, self))

        self.action_close = QAction("❌ Cerrar PDF", self)
        self.action_close.setShortcut("Ctrl+W")
        self.action_close.setToolTip("Cerrar PDF actual para abrir otro (Ctrl+W)")
        self.action_close.triggered.connect(self.closeFile.emit)
        self.action_close.setEnabled(False)
        self._flow.addWidget(_make_button(self.action_close, self))

        self._flow.addWidget(_ToolbarSeparator(self))

        # === Deshacer / Rehacer ===
        self.action_undo = QAction("↩️ Deshacer", self)
        self.action_undo.setShortcut(QKeySequence.Undo)
        self.action_undo.setToolTip("Deshacer última acción (Ctrl+Z)")
        self.action_undo.triggered.connect(self.undoAction.emit)
        self.action_undo.setEnabled(False)
        self._flow.addWidget(_make_button(self.action_undo, self))

        self.action_redo = QAction("↪️ Rehacer", self)
        self.action_redo.setShortcut(QKeySequence.Redo)
        self.action_redo.setToolTip("Rehacer acción (Ctrl+Y)")
        self.action_redo.triggered.connect(self.redoAction.emit)
        self.action_redo.setEnabled(False)
        self._flow.addWidget(_make_button(self.action_redo, self))

        self._flow.addWidget(_ToolbarSeparator(self))

        # === Herramientas de edición ===
        self.action_edit = QAction("✏️ EDITAR", self)
        self.action_edit.setToolTip("Click para editar texto o añadir texto nuevo")
        self.action_edit.setCheckable(True)
        self.action_edit.setChecked(True)
        self.action_edit.triggered.connect(lambda: self.set_tool('edit'))
        self._flow.addWidget(_make_button(self.action_edit, self))
        self.tool_actions['edit'] = self.action_edit

        self.action_delete = QAction("🗑️ ELIMINAR", self)
        self.action_delete.setToolTip("Arrastra sobre el contenido para eliminarlo permanentemente")
        self.action_delete.setCheckable(True)
        self.action_delete.triggered.connect(lambda: self.set_tool('delete'))
        self._flow.addWidget(_make_button(self.action_delete, self))
        self.tool_actions['delete'] = self.action_delete

        self.action_highlight = QAction("🖍️ Resaltar", self)
        self.action_highlight.setToolTip("Herramienta de resaltado")
        self.action_highlight.setCheckable(True)
        self.action_highlight.triggered.connect(lambda: self.set_tool('highlight'))
        self._flow.addWidget(_make_button(self.action_highlight, self))
        self.tool_actions['highlight'] = self.action_highlight

        # Rotar (con submenú)
        self.action_rotate = QAction("🔄 Rotar", self)
        self.action_rotate.setToolTip("Rotar la página actual")
        self.action_rotate.setEnabled(False)
        rotate_menu = QMenu(self)
        rotate_menu.addAction("↻ Rotar 90° derecha").triggered.connect(
            lambda: self.rotatePageRequested.emit(90))
        rotate_menu.addAction("↺ Rotar 90° izquierda").triggered.connect(
            lambda: self.rotatePageRequested.emit(270))
        rotate_menu.addAction("🔃 Rotar 180°").triggered.connect(
            lambda: self.rotatePageRequested.emit(180))
        self.action_rotate.setMenu(rotate_menu)
        rotate_btn = QToolButton(self)
        rotate_btn.setDefaultAction(self.action_rotate)
        rotate_btn.setPopupMode(QToolButton.InstantPopup)
        rotate_btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        rotate_btn.setStyleSheet(_BUTTON_STYLE)
        rotate_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._flow.addWidget(rotate_btn)

        # Comprimir
        self.action_compress = QAction("🗜️ Comprimir", self)
        self.action_compress.setToolTip("Comprimir PDF para reducir tamaño")
        self.action_compress.triggered.connect(self.compressRequested.emit)
        self.action_compress.setEnabled(False)
        self._flow.addWidget(_make_button(self.action_compress, self))

        # Páginas
        self.action_page_manager = QAction("📑 Páginas", self)
        self.action_page_manager.setToolTip("Unir, dividir, extraer, eliminar y reordenar páginas")
        self.action_page_manager.triggered.connect(self.pageManagerRequested.emit)
        self.action_page_manager.setEnabled(False)
        self._flow.addWidget(_make_button(self.action_page_manager, self))

        self._flow.addWidget(_ToolbarSeparator(self))

        # === Zoom ===
        self.action_zoom_out = QAction("🔍- Alejar", self)
        self.action_zoom_out.setToolTip("Alejar (Ctrl+-)")
        self.action_zoom_out.setShortcut("Ctrl+-")
        self.action_zoom_out.triggered.connect(self.zoomOut.emit)
        self._flow.addWidget(_make_button(self.action_zoom_out, self))

        self.zoom_combo = QComboBox(self)
        self.zoom_combo.setEditable(True)
        self.zoom_combo.setFixedWidth(80)
        self.zoom_combo.setFixedHeight(28)
        zoom_levels = ['25%', '50%', '75%', '100%', '125%', '150%', '200%', '300%', '400%']
        self.zoom_combo.addItems(zoom_levels)
        self.zoom_combo.setCurrentText('100%')
        self.zoom_combo.currentTextChanged.connect(self.on_zoom_changed)
        self._flow.addWidget(self.zoom_combo)

        self.action_zoom_in = QAction("🔍+ Acercar", self)
        self.action_zoom_in.setToolTip("Acercar (Ctrl++)")
        self.action_zoom_in.setShortcut("Ctrl++")
        self.action_zoom_in.triggered.connect(self.zoomIn.emit)
        self._flow.addWidget(_make_button(self.action_zoom_in, self))

        self.action_fit_width = QAction("↔️ Ajustar ancho", self)
        self.action_fit_width.setToolTip("Ajustar al ancho de la ventana")
        self.action_fit_width.triggered.connect(self.fitWidth.emit)
        self._flow.addWidget(_make_button(self.action_fit_width, self))

        self._flow.addWidget(_ToolbarSeparator(self))

        # === Navegación ===
        self.action_prev_page = QAction("◀️ Anterior", self)
        self.action_prev_page.setToolTip("Página anterior (Page Up)")
        self.action_prev_page.setShortcut(QKeySequence.MoveToPreviousPage)
        self.action_prev_page.triggered.connect(self.go_prev_page)
        self._flow.addWidget(_make_button(self.action_prev_page, self))

        # Indicador de página
        self.page_widget = QWidget(self)
        page_layout = QHBoxLayout(self.page_widget)
        page_layout.setContentsMargins(5, 0, 5, 0)
        page_layout.setSpacing(4)

        self.page_label = QLabel("Página:")
        self.page_label.setStyleSheet("color: white; background: transparent;")
        page_layout.addWidget(self.page_label)

        self.page_spinbox = QSpinBox()
        self.page_spinbox.setMinimum(1)
        self.page_spinbox.setMaximum(1)
        self.page_spinbox.setFixedWidth(60)
        self.page_spinbox.valueChanged.connect(self.on_page_changed)
        page_layout.addWidget(self.page_spinbox)

        self.total_pages_label = QLabel("de 0")
        self.total_pages_label.setStyleSheet("color: white; background: transparent;")
        page_layout.addWidget(self.total_pages_label)

        self._flow.addWidget(self.page_widget)

        self.action_next_page = QAction("▶️ Siguiente", self)
        self.action_next_page.setToolTip("Página siguiente (Page Down)")
        self.action_next_page.setShortcut(QKeySequence.MoveToNextPage)
        self.action_next_page.triggered.connect(self.go_next_page)
        self._flow.addWidget(_make_button(self.action_next_page, self))

        # Registrar acciones con atajo en el widget para que funcionen los shortcuts
        for action in self.findChildren(QAction):
            if not action.shortcut().isEmpty():
                super().addAction(action)

    # ------------------------------------------------------------------
    # Compatibilidad: addSeparator / addWidget (usado por main_window)
    # ------------------------------------------------------------------

    def addSeparator(self):
        """Añade un separador visual al flow layout."""
        self._flow.addWidget(_ToolbarSeparator(self))

    def addWidget(self, widget):
        """Añade un widget al flow layout."""
        widget.setParent(self)
        self._flow.addWidget(widget)

    # ------------------------------------------------------------------
    # Métodos públicos (API idéntica)
    # ------------------------------------------------------------------

    def set_tool(self, tool: str):
        """Establece la herramienta actual."""
        self.current_tool = tool
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
        self.pageChanged.emit(page - 1)

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
        self.action_insert_pdf.setEnabled(loaded)

        for action in self.tool_actions.values():
            action.setEnabled(loaded)

        self.action_zoom_in.setEnabled(loaded)
        self.action_zoom_out.setEnabled(loaded)
        self.zoom_combo.setEnabled(loaded)
        self.action_fit_width.setEnabled(loaded)

        self.action_rotate.setEnabled(loaded)
        self.action_compress.setEnabled(loaded)
        self.action_page_manager.setEnabled(loaded)

        self.action_prev_page.setEnabled(loaded)
        self.action_next_page.setEnabled(loaded)
        self.page_spinbox.setEnabled(loaded)

    def update_undo_redo(self, can_undo: bool, can_redo: bool):
        """Actualiza el estado de deshacer/rehacer."""
        self.action_undo.setEnabled(can_undo)
        self.action_redo.setEnabled(can_redo)

"""Panel de Buscar y Reemplazar para PDF Editor Pro.

Barra flotante estilo VS Code que aparece sobre el visor PDF.
Soporta búsqueda con resaltado, navegación entre resultados,
y reemplazo individual o masivo.
"""
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import fitz
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit,
    QPushButton, QLabel, QCheckBox, QToolButton, QSizePolicy
)
from PyQt5.QtCore import pyqtSignal, Qt, QRectF
from PyQt5.QtGui import QColor, QKeySequence, QIcon

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Resultado individual de búsqueda.
    
    Attributes:
        page_num: Número de página (0-based).
        rect: Rectángulo del texto encontrado en coordenadas PDF.
    """
    page_num: int
    rect: fitz.Rect

    def to_dict(self) -> dict:
        """Serializa a diccionario."""
        return {
            'page_num': self.page_num,
            'rect': [self.rect.x0, self.rect.y0, self.rect.x1, self.rect.y1],
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SearchResult':
        """Deserializa desde diccionario."""
        return cls(
            page_num=data['page_num'],
            rect=fitz.Rect(data['rect']),
        )


class SearchReplacePanel(QWidget):
    """Panel flotante de buscar y reemplazar.
    
    Se sitúa en la parte superior derecha del visor PDF.
    Emite señales para que el visor resalte los resultados
    y navegue entre páginas.
    
    Signals:
        searchRequested: Emitida con (texto, case_sensitive) al buscar.
        replaceRequested: Emitida con (old_text, new_text, page_num, rect).
        replaceAllRequested: Emitida con (old_text, new_text).
        navigateToResult: Emitida con (page_num, rect) al navegar.
        closed: Emitida al cerrar el panel.
        highlightsChanged: Emitida con lista de SearchResult para resaltar.
    """
    searchRequested = pyqtSignal(str, bool)
    replaceRequested = pyqtSignal(str, str, int, object)
    replaceAllRequested = pyqtSignal(str, str)
    navigateToResult = pyqtSignal(int, object)
    closed = pyqtSignal()
    highlightsChanged = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._results: List[SearchResult] = []
        self._current_index: int = -1
        self._replace_visible: bool = False
        self._init_ui()
        self._connect_signals()
        self._apply_theme()
        self.hide()

    def _init_ui(self):
        """Construye la interfaz del panel."""
        self.setFixedHeight(40)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 4)
        main_layout.setSpacing(4)

        # Botón expandir reemplazo
        self.btn_toggle_replace = QToolButton()
        self.btn_toggle_replace.setText("▶")
        self.btn_toggle_replace.setFixedSize(20, 24)
        self.btn_toggle_replace.setToolTip("Mostrar Reemplazar")
        main_layout.addWidget(self.btn_toggle_replace)

        # Contenedor vertical (búsqueda + reemplazo)
        self._rows_layout = QVBoxLayout()
        self._rows_layout.setSpacing(4)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)

        # === Fila de búsqueda ===
        search_row = QHBoxLayout()
        search_row.setSpacing(4)

        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Buscar en PDF...")
        self.input_search.setMinimumWidth(200)
        self.input_search.setClearButtonEnabled(True)
        search_row.addWidget(self.input_search)

        self.chk_case = QCheckBox("Aa")
        self.chk_case.setToolTip("Distinguir mayúsculas/minúsculas")
        search_row.addWidget(self.chk_case)

        self.lbl_count = QLabel("Sin resultados")
        self.lbl_count.setFixedWidth(110)
        self.lbl_count.setAlignment(Qt.AlignCenter)
        search_row.addWidget(self.lbl_count)

        self.btn_prev = QToolButton()
        self.btn_prev.setText("▲")
        self.btn_prev.setToolTip("Resultado anterior (Shift+F3)")
        self.btn_prev.setFixedSize(24, 24)
        search_row.addWidget(self.btn_prev)

        self.btn_next = QToolButton()
        self.btn_next.setText("▼")
        self.btn_next.setToolTip("Siguiente resultado (F3)")
        self.btn_next.setFixedSize(24, 24)
        search_row.addWidget(self.btn_next)

        self.btn_close = QToolButton()
        self.btn_close.setText("✕")
        self.btn_close.setToolTip("Cerrar (Escape)")
        self.btn_close.setFixedSize(24, 24)
        search_row.addWidget(self.btn_close)

        self._rows_layout.addLayout(search_row)

        # === Fila de reemplazo (oculta por defecto) ===
        self._replace_row = QWidget()
        replace_layout = QHBoxLayout(self._replace_row)
        replace_layout.setSpacing(4)
        replace_layout.setContentsMargins(0, 0, 0, 0)

        self.input_replace = QLineEdit()
        self.input_replace.setPlaceholderText("Reemplazar con...")
        self.input_replace.setMinimumWidth(200)
        replace_layout.addWidget(self.input_replace)

        self.btn_replace = QPushButton("Reemplazar")
        self.btn_replace.setToolTip("Reemplazar coincidencia actual")
        self.btn_replace.setFixedWidth(90)
        replace_layout.addWidget(self.btn_replace)

        self.btn_replace_all = QPushButton("Reemplazar todo")
        self.btn_replace_all.setToolTip("Reemplazar todas las coincidencias")
        self.btn_replace_all.setFixedWidth(110)
        replace_layout.addWidget(self.btn_replace_all)

        replace_layout.addStretch()

        self._replace_row.hide()
        self._rows_layout.addWidget(self._replace_row)

        main_layout.addLayout(self._rows_layout)
        main_layout.addStretch()

    def _connect_signals(self):
        """Conecta señales internas."""
        self.input_search.textChanged.connect(self._on_search_text_changed)
        self.input_search.returnPressed.connect(self._on_next_clicked)
        self.chk_case.toggled.connect(self._on_search_text_changed)
        self.btn_next.clicked.connect(self._on_next_clicked)
        self.btn_prev.clicked.connect(self._on_prev_clicked)
        self.btn_close.clicked.connect(self._on_close_clicked)
        self.btn_toggle_replace.clicked.connect(self._on_toggle_replace)
        self.btn_replace.clicked.connect(self._on_replace_clicked)
        self.btn_replace_all.clicked.connect(self._on_replace_all_clicked)
        self.input_replace.returnPressed.connect(self._on_replace_clicked)

    def _apply_theme(self):
        """Aplica tema oscuro al panel."""
        self.setStyleSheet("""
            SearchReplacePanel {
                background-color: #252526;
                border-bottom: 1px solid #3e3e42;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                padding: 2px 6px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
            QCheckBox {
                color: #cccccc;
                font-size: 11px;
                spacing: 2px;
            }
            QLabel {
                color: #cccccc;
                font-size: 11px;
            }
            QToolButton {
                background: transparent;
                color: #cccccc;
                border: none;
                border-radius: 3px;
                font-size: 12px;
            }
            QToolButton:hover {
                background-color: #3e3e42;
            }
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1a8ad4;
            }
            QPushButton:disabled {
                background-color: #3e3e42;
                color: #666666;
            }
        """)

    # --- Acciones públicas ---

    def show_search(self):
        """Muestra el panel en modo búsqueda (Ctrl+F)."""
        self._replace_visible = False
        self._replace_row.hide()
        self.btn_toggle_replace.setText("▶")
        self.setFixedHeight(40)
        self.show()
        self.input_search.setFocus()
        self.input_search.selectAll()

    def show_replace(self):
        """Muestra el panel en modo búsqueda y reemplazo (Ctrl+H)."""
        self._replace_visible = True
        self._replace_row.show()
        self.btn_toggle_replace.setText("▼")
        self.setFixedHeight(72)
        self.show()
        self.input_search.setFocus()
        self.input_search.selectAll()

    def set_results(self, results: List[SearchResult]):
        """Establece los resultados de búsqueda.
        
        Args:
            results: Lista de SearchResult encontrados.
        """
        self._results = results
        if results:
            self._current_index = 0
        else:
            self._current_index = -1
        self._update_count_label()
        self._update_buttons()
        self.highlightsChanged.emit(results)
        if results:
            self._navigate_to_current()

    def clear_results(self):
        """Limpia todos los resultados."""
        self._results = []
        self._current_index = -1
        self._update_count_label()
        self._update_buttons()
        self.highlightsChanged.emit([])

    @property
    def current_result(self) -> Optional[SearchResult]:
        """Resultado actualmente seleccionado."""
        if 0 <= self._current_index < len(self._results):
            return self._results[self._current_index]
        return None

    @property
    def search_text(self) -> str:
        """Texto de búsqueda actual."""
        return self.input_search.text()

    @property
    def replace_text(self) -> str:
        """Texto de reemplazo actual."""
        return self.input_replace.text()

    @property
    def case_sensitive(self) -> bool:
        """Si la búsqueda distingue mayúsculas."""
        return self.chk_case.isChecked()

    # --- Slots privados ---

    def _on_search_text_changed(self, *_args):
        """Ejecuta búsqueda al cambiar el texto."""
        text = self.input_search.text().strip()
        if len(text) >= 2:
            self.searchRequested.emit(text, self.case_sensitive)
        else:
            self.clear_results()

    def _on_next_clicked(self):
        """Navega al siguiente resultado."""
        if not self._results:
            return
        self._current_index = (self._current_index + 1) % len(self._results)
        self._update_count_label()
        self._navigate_to_current()

    def _on_prev_clicked(self):
        """Navega al resultado anterior."""
        if not self._results:
            return
        self._current_index = (self._current_index - 1) % len(self._results)
        self._update_count_label()
        self._navigate_to_current()

    def _on_close_clicked(self):
        """Cierra el panel."""
        self.clear_results()
        self.hide()
        self.closed.emit()

    def _on_toggle_replace(self):
        """Alterna visibilidad de la fila de reemplazo."""
        if self._replace_visible:
            self.show_search()
        else:
            self.show_replace()

    def _on_replace_clicked(self):
        """Reemplaza la coincidencia actual."""
        result = self.current_result
        if not result:
            return
        old_text = self.input_search.text()
        new_text = self.input_replace.text()
        if not old_text:
            return
        self.replaceRequested.emit(old_text, new_text, result.page_num, result.rect)

    def _on_replace_all_clicked(self):
        """Reemplaza todas las coincidencias."""
        old_text = self.input_search.text()
        new_text = self.input_replace.text()
        if not old_text:
            return
        self.replaceAllRequested.emit(old_text, new_text)

    # --- Helpers privados ---

    def _navigate_to_current(self):
        """Navega al resultado actual."""
        result = self.current_result
        if result:
            self.navigateToResult.emit(result.page_num, result.rect)
            self.highlightsChanged.emit(self._results)

    def _update_count_label(self):
        """Actualiza la etiqueta de conteo."""
        total = len(self._results)
        if total == 0:
            text = self.input_search.text().strip()
            if len(text) >= 2:
                self.lbl_count.setText("Sin resultados")
            else:
                self.lbl_count.setText("")
        else:
            self.lbl_count.setText(f"{self._current_index + 1} de {total}")

    def _update_buttons(self):
        """Actualiza estado de botones."""
        has_results = len(self._results) > 0
        self.btn_next.setEnabled(has_results)
        self.btn_prev.setEnabled(has_results)
        self.btn_replace.setEnabled(has_results)
        self.btn_replace_all.setEnabled(has_results)

    def keyPressEvent(self, event):
        """Maneja atajos de teclado."""
        if event.key() == Qt.Key_Escape:
            self._on_close_clicked()
        elif event.key() == Qt.Key_F3:
            if event.modifiers() & Qt.ShiftModifier:
                self._on_prev_clicked()
            else:
                self._on_next_clicked()
        else:
            super().keyPressEvent(event)

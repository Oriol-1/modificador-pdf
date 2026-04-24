"""Tests para nudge con flechas y cancelación de drag con Esc.

Extras del MOVE puro de overlays editables:

- ``Esc`` durante un drag de texto restaura la posición inicial y NO escribe
  en el PDF.
- Flechas (Left/Right/Up/Down) en modo ``edit`` con un texto seleccionado
  desplazan 1 px (10 px con Shift). Solo traslación, nunca redimensionan.
- Las flechas aplican clamp y delegan en ``_update_text_in_pdf`` (mismo path
  que el drag de ratón).
"""

from unittest.mock import MagicMock

import fitz
import pytest
from PyQt5.QtCore import QEvent, QPointF, QRectF, Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QApplication

from ui.graphics_items import EditableTextItem
from ui.pdf_viewer import PDFPageView


@pytest.fixture(scope="session", autouse=True)
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def viewer():
    v = PDFPageView()
    v.zoom_level = 1.0
    v.current_page = 0
    page = MagicMock()
    page.rect.width = 612
    page.rect.height = 792
    v.pdf_doc = MagicMock()
    v.pdf_doc.get_page.return_value = page
    v.pdf_doc.is_open.return_value = True
    return v


@pytest.fixture
def text_item():
    item = EditableTextItem(
        rect=QRectF(0, 0, 80, 20),
        text="hola",
        font_size=12.0,
        color=(0, 0, 0),
        page_num=0,
        font_name="ArialMT",
        is_bold=False,
        zoom_level=1.0,
        line_spacing=14.0,
    )
    item.is_overlay = True
    item.pending_write = False
    item.pdf_rect = fitz.Rect(50, 60, 130, 80)
    item.original_pdf_rect = fitz.Rect(50, 60, 130, 80)
    item.internal_pdf_rect = None
    item.needs_erase = False
    item.text_runs = None
    item.has_mixed_styles = False
    item.lock_bounds()
    item._bounds_finalized = True
    return item


def _seed(viewer, item):
    data = {
        "text": item.text,
        "font_size": item.font_size,
        "font_name": item.font_name,
        "is_bold": item.is_bold,
        "color": item.text_color,
        "pdf_rect": fitz.Rect(item.pdf_rect),
        "view_rect": QRectF(50, 60, 80, 20),
        "original_pdf_rect": fitz.Rect(item.original_pdf_rect),
        "internal_pdf_rect": None,
        "needs_erase": False,
        "is_overlay": True,
        "pending_write": False,
        "text_runs": None,
        "has_mixed_styles": False,
        "line_spacing": item.line_spacing,
    }
    page_data = viewer.editable_texts_data.setdefault(viewer._current_page_key(), [])
    page_data.append(data)
    item.data_index = len(page_data) - 1
    return data


def _key(key, modifiers=Qt.NoModifier):
    return QKeyEvent(QEvent.KeyPress, key, modifiers)


# ---------------------------------------------------------------------------
# Esc cancela drag
# ---------------------------------------------------------------------------


class TestEscCancelaDrag:
    def test_esc_restaura_posicion_inicial(self, viewer, text_item):
        viewer.scene.addItem(text_item)
        _seed(viewer, text_item)
        viewer.tool_mode = "edit"
        viewer.selected_text_item = text_item

        # Simular drag en curso
        initial = QPointF(text_item.pos())
        viewer.dragging_text = True
        viewer._text_drag_start_item_pos = initial
        viewer.text_was_moved = True
        text_item.setPos(initial + QPointF(40, 30))
        text_item.pending_write = True

        viewer.keyPressEvent(_key(Qt.Key_Escape))

        assert text_item.pos() == initial
        assert text_item.pending_write is False
        assert viewer.dragging_text is False
        assert viewer.text_was_moved is False
        assert viewer._text_drag_start_item_pos is None

    def test_esc_sin_drag_no_hace_nada(self, viewer, text_item):
        viewer.scene.addItem(text_item)
        viewer.tool_mode = "edit"
        viewer.selected_text_item = text_item
        viewer.dragging_text = False
        pos_antes = QPointF(text_item.pos())

        viewer.keyPressEvent(_key(Qt.Key_Escape))

        assert text_item.pos() == pos_antes


# ---------------------------------------------------------------------------
# Flechas: nudge por píxel
# ---------------------------------------------------------------------------


class TestFlechasNudge:
    def _setup_selected(self, viewer, text_item):
        viewer.scene.addItem(text_item)
        _seed(viewer, text_item)
        viewer.tool_mode = "edit"
        viewer.selected_text_item = text_item
        viewer.dragging_text = False
        # Posición inicial bien dentro de la página para que ±1 px nunca
        # toque el clamp del MediaBox.
        text_item.setPos(100, 100)
        # Stub para no tocar el PDF real.
        viewer._update_text_in_pdf = MagicMock()

    def test_flecha_derecha_mueve_1px(self, viewer, text_item):
        self._setup_selected(viewer, text_item)
        pos_antes = QPointF(text_item.pos())
        viewer.keyPressEvent(_key(Qt.Key_Right))
        assert text_item.pos().x() == pytest.approx(pos_antes.x() + 1.0)
        assert text_item.pos().y() == pytest.approx(pos_antes.y())
        assert text_item.pending_write is True
        viewer._update_text_in_pdf.assert_called_once_with(text_item)

    def test_flecha_izquierda_mueve_1px(self, viewer, text_item):
        self._setup_selected(viewer, text_item)
        pos_antes = QPointF(text_item.pos())
        viewer.keyPressEvent(_key(Qt.Key_Left))
        assert text_item.pos().x() == pytest.approx(pos_antes.x() - 1.0)

    def test_flecha_arriba_mueve_1px(self, viewer, text_item):
        self._setup_selected(viewer, text_item)
        pos_antes = QPointF(text_item.pos())
        viewer.keyPressEvent(_key(Qt.Key_Up))
        assert text_item.pos().y() == pytest.approx(pos_antes.y() - 1.0)

    def test_flecha_abajo_mueve_1px(self, viewer, text_item):
        self._setup_selected(viewer, text_item)
        pos_antes = QPointF(text_item.pos())
        viewer.keyPressEvent(_key(Qt.Key_Down))
        assert text_item.pos().y() == pytest.approx(pos_antes.y() + 1.0)

    def test_shift_flecha_mueve_10px(self, viewer, text_item):
        self._setup_selected(viewer, text_item)
        pos_antes = QPointF(text_item.pos())
        viewer.keyPressEvent(_key(Qt.Key_Right, Qt.ShiftModifier))
        assert text_item.pos().x() == pytest.approx(pos_antes.x() + 10.0)

    def test_flecha_no_redimensiona_item(self, viewer, text_item):
        self._setup_selected(viewer, text_item)
        rect_antes = QRectF(text_item.rect())
        viewer.keyPressEvent(_key(Qt.Key_Right, Qt.ShiftModifier))
        viewer.keyPressEvent(_key(Qt.Key_Down, Qt.ShiftModifier))
        assert text_item.rect() == rect_antes

    def test_flecha_durante_drag_no_actua(self, viewer, text_item):
        self._setup_selected(viewer, text_item)
        viewer.dragging_text = True
        pos_antes = QPointF(text_item.pos())
        viewer.keyPressEvent(_key(Qt.Key_Right))
        assert text_item.pos() == pos_antes
        viewer._update_text_in_pdf.assert_not_called()

    def test_flecha_sin_seleccion_no_actua(self, viewer, text_item):
        viewer.scene.addItem(text_item)
        viewer.tool_mode = "edit"
        viewer.selected_text_item = None
        viewer._update_text_in_pdf = MagicMock()
        pos_antes = QPointF(text_item.pos())
        viewer.keyPressEvent(_key(Qt.Key_Right))
        assert text_item.pos() == pos_antes
        viewer._update_text_in_pdf.assert_not_called()

    def test_flecha_fuera_de_modo_edit_no_actua(self, viewer, text_item):
        self._setup_selected(viewer, text_item)
        viewer.tool_mode = "select"
        pos_antes = QPointF(text_item.pos())
        viewer.keyPressEvent(_key(Qt.Key_Right))
        assert text_item.pos() == pos_antes
        viewer._update_text_in_pdf.assert_not_called()

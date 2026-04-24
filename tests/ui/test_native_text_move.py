"""Tests para la materialización de texto NATIVO del PDF como overlay arrastrable.

Cuando el usuario hace press sobre un texto original del PDF en modo edit y
arrastra superando ``MOVE_THRESHOLD_PX``, el texto debe convertirse en un
``EditableTextItem`` overlay preservando runs, line_spacing, fuente y color.
Si el press no supera el umbral, debe delegarse en ``handle_edit_click`` (no
materializar overlay).
"""

from unittest.mock import MagicMock

import fitz
import pytest
from PyQt5.QtCore import QEvent, QPointF, QPoint, Qt
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QApplication

from ui.graphics_items import EditableTextItem
from ui.pdf_viewer import PDFPageView


@pytest.fixture(scope="session", autouse=True)
def qapp():
    return QApplication.instance() or QApplication([])


def _make_block(text="hola mundo", rect=(50, 60, 150, 80)):
    block = MagicMock()
    block.text = text
    block.rect = fitz.Rect(*rect)
    block.font_size = 12.0
    block.font_name = "ArialMT"
    block.color = (0.0, 0.0, 0.0)
    block.is_bold = False
    return block


@pytest.fixture
def viewer():
    v = PDFPageView()
    v.zoom_level = 1.0
    v.current_page = 0
    v.tool_mode = "edit"
    # pdf_doc mockeado: página 612x792, find_text_at_point devuelve un block.
    page = MagicMock()
    page.rect.width = 612
    page.rect.height = 792
    v.pdf_doc = MagicMock()
    v.pdf_doc.is_open.return_value = True
    v.pdf_doc.get_page.return_value = page
    v.pdf_doc.find_text_at_point.return_value = _make_block()
    # No usado en estos tests (no llegamos a save/render real).
    v.pdf_doc.get_text_spans_in_rect.return_value = []
    v.pdf_doc.is_image_based_pdf.return_value = False
    return v


# ---------------------------------------------------------------------------
# Helper directo: _materialize_pdf_text_as_overlay
# ---------------------------------------------------------------------------


class TestMaterializeHelper:
    def test_devuelve_none_sin_block(self, viewer):
        assert viewer._materialize_pdf_text_as_overlay(None) is None

    def test_devuelve_none_con_texto_vacio(self, viewer):
        assert viewer._materialize_pdf_text_as_overlay(_make_block(text="")) is None
        assert viewer._materialize_pdf_text_as_overlay(_make_block(text="   ")) is None

    def test_crea_overlay_con_needs_erase(self, viewer):
        block = _make_block(text="texto original")
        item = viewer._materialize_pdf_text_as_overlay(block)
        assert item is not None
        assert isinstance(item, EditableTextItem)
        assert item.text == "texto original"
        assert item.needs_erase is True
        assert item.is_overlay is False
        # El item se añade a editable_text_items y editable_texts_data.
        assert item in viewer.editable_text_items
        page_data = viewer.editable_texts_data[viewer._current_page_key()]
        assert any(d.get("text") == "texto original" for d in page_data)
        # original_pdf_rect preservado.
        assert item.original_pdf_rect == block.rect

    def test_preserva_font_size_color_y_fuente(self, viewer):
        block = _make_block()
        block.font_size = 14.5
        block.font_name = "TimesNewRoman"
        block.color = (0.2, 0.3, 0.4)
        item = viewer._materialize_pdf_text_as_overlay(block)
        assert item.font_size == 14.5
        assert item.font_name == "TimesNewRoman"
        assert item.text_color == (0.2, 0.3, 0.4)


# ---------------------------------------------------------------------------
# Press sobre texto nativo: estado pendiente
# ---------------------------------------------------------------------------


def _press(viewer, scene_pos: QPointF) -> QMouseEvent:
    view_pos = viewer.mapFromScene(scene_pos)
    return QMouseEvent(
        QEvent.MouseButtonPress, QPoint(view_pos), Qt.LeftButton,
        Qt.LeftButton, Qt.NoModifier,
    )


def _move(viewer, scene_pos: QPointF) -> QMouseEvent:
    view_pos = viewer.mapFromScene(scene_pos)
    return QMouseEvent(
        QEvent.MouseMove, QPoint(view_pos), Qt.NoButton,
        Qt.LeftButton, Qt.NoModifier,
    )


def _release(viewer, scene_pos: QPointF) -> QMouseEvent:
    view_pos = viewer.mapFromScene(scene_pos)
    return QMouseEvent(
        QEvent.MouseButtonRelease, QPoint(view_pos), Qt.LeftButton,
        Qt.NoButton, Qt.NoModifier,
    )


class TestPressNativeText:
    def test_press_sobre_texto_nativo_arma_pending(self, viewer):
        # Sin overlays → cae al chequeo de texto nativo.
        viewer.mousePressEvent(_press(viewer, QPointF(80, 70)))
        assert viewer._pending_native_drag is not None
        assert viewer._pending_native_drag["block"].text == "hola mundo"
        # No activa drag aún (esperamos el umbral en mouseMoveEvent).
        assert viewer.dragging_text is False

    def test_press_sin_block_no_arma_pending(self, viewer):
        viewer.pdf_doc.find_text_at_point.return_value = None
        viewer.mousePressEvent(_press(viewer, QPointF(80, 70)))
        assert viewer._pending_native_drag is None


# ---------------------------------------------------------------------------
# Drag completo: press → move (supera umbral) → materializa y arrastra
# ---------------------------------------------------------------------------


class TestDragNativeText:
    def test_move_supera_umbral_materializa_y_drag(self, viewer):
        viewer.mousePressEvent(_press(viewer, QPointF(80, 70)))
        # Mover muy poco: NO debe materializar todavía.
        viewer.mouseMoveEvent(_move(viewer, QPointF(81, 70)))
        assert viewer._pending_native_drag is not None
        assert viewer.dragging_text is False
        assert viewer.selected_text_item is None

        # Ahora superar umbral (3 px): debe materializar y entrar en drag.
        viewer.mouseMoveEvent(_move(viewer, QPointF(95, 90)))
        assert viewer._pending_native_drag is None
        assert viewer.dragging_text is True
        assert viewer.selected_text_item is not None
        assert viewer.text_was_moved is True
        assert viewer.selected_text_item.is_overlay is False
        assert viewer.selected_text_item.needs_erase is True
        # El item está desplazado del original.
        assert viewer.selected_text_item.pos() != QPointF(50, 60)


# ---------------------------------------------------------------------------
# Click puro sobre texto nativo: NO materializa, delega en handle_edit_click
# ---------------------------------------------------------------------------


class TestClickPuroNoMaterializa:
    def test_release_sin_movimiento_delega_en_handle_edit_click(self, viewer):
        viewer.handle_edit_click = MagicMock()
        viewer.mousePressEvent(_press(viewer, QPointF(80, 70)))
        # Release sin haber movido nada (release exactamente en la misma pos).
        viewer.mouseReleaseEvent(_release(viewer, QPointF(80, 70)))
        # handle_edit_click se llamó con la posición del press.
        viewer.handle_edit_click.assert_called_once()
        call_pos = viewer.handle_edit_click.call_args[0][0]
        assert call_pos == QPointF(80, 70)
        # No se materializó ningún overlay.
        assert viewer._pending_native_drag is None
        assert viewer.dragging_text is False
        assert viewer.selected_text_item is None
        # editable_text_items NO crece por un click puro sobre texto nativo.
        assert viewer.editable_text_items == []

"""Tests para EditableImageItem — imagen editable con movimiento, redimensión y z-order."""

import pytest
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QRectF, QPointF, Qt
from PyQt5.QtGui import QPixmap, QColor

from ui.graphics_items import EditableImageItem, ResizeHandle


# --- QApplication ---

@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Crea QApplication para tests."""
    app = QApplication.instance() or QApplication([])
    return app


# --- Fixtures ---

@pytest.fixture
def sample_pixmap():
    """Pixmap de prueba 200x100."""
    pixmap = QPixmap(200, 100)
    pixmap.fill(QColor(255, 0, 0))
    return pixmap


@pytest.fixture
def image_item(sample_pixmap):
    """EditableImageItem básico para tests."""
    rect = QRectF(0, 0, 200, 100)
    item = EditableImageItem(
        rect=rect,
        pixmap=sample_pixmap,
        page_num=0,
        image_path="/tmp/test.png",
        keep_proportion=True,
        overlay_mode=True,
        zoom_level=1.0,
    )
    return item


@pytest.fixture
def image_item_no_proportion(sample_pixmap):
    """EditableImageItem sin mantener proporción."""
    rect = QRectF(0, 0, 200, 100)
    return EditableImageItem(
        rect=rect,
        pixmap=sample_pixmap,
        keep_proportion=False,
        overlay_mode=False,
        zoom_level=1.5,
    )


# --- Tests de creación ---

class TestEditableImageItemCreation:
    """Tests de creación e inicialización."""

    def test_creation_basic(self, image_item):
        """Verifica creación básica con valores correctos."""
        assert image_item.module_id > 0
        assert image_item.page_num == 0
        assert image_item.image_path == "/tmp/test.png"
        assert image_item.keep_proportion is True
        assert image_item.overlay_mode is True

    def test_creation_sets_overlay_flags(self, image_item):
        """Nuevas imágenes son overlay y pending_write por defecto."""
        assert image_item.is_overlay is True
        assert image_item.pending_write is True

    def test_creation_unique_ids(self, sample_pixmap):
        """Cada imagen tiene un ID único."""
        item1 = EditableImageItem(QRectF(0, 0, 50, 50), sample_pixmap)
        item2 = EditableImageItem(QRectF(0, 0, 50, 50), sample_pixmap)
        assert item1.module_id != item2.module_id

    def test_creation_aspect_ratio(self, image_item):
        """Se calcula la proporción a partir del pixmap."""
        assert image_item._aspect_ratio == pytest.approx(2.0, rel=0.01)

    def test_creation_z_value_overlay(self, image_item):
        """overlay_mode=True → z=160."""
        assert image_item.zValue() == 160

    def test_creation_z_value_below(self, image_item_no_proportion):
        """overlay_mode=False → z=140."""
        assert image_item_no_proportion.zValue() == 140

    def test_creation_with_zoom(self, image_item_no_proportion):
        """Verifica zoom_level almacenado."""
        assert image_item_no_proportion.zoom_level == 1.5

    def test_rect_normalized(self, image_item):
        """El rect comienza en (0,0)."""
        rect = image_item.rect()
        assert rect.x() == 0
        assert rect.y() == 0
        assert rect.width() == 200
        assert rect.height() == 100

    def test_flags_set(self, image_item):
        """Flags de interacción configurados."""
        assert image_item.flags() & image_item.ItemIsSelectable
        assert image_item.flags() & image_item.ItemIsMovable
        assert image_item.flags() & image_item.ItemSendsGeometryChanges


# --- Tests de estado visual ---

class TestVisualState:
    """Tests de selección y hover."""

    def test_set_selected(self, image_item):
        """set_selected cambia el estado."""
        image_item.set_selected(True)
        assert image_item.is_selected is True
        image_item.set_selected(False)
        assert image_item.is_selected is False

    def test_selected_pen_color(self, image_item):
        """Seleccionado tiene borde azul sólido."""
        image_item.set_selected(True)
        pen = image_item.pen()
        assert pen.color() == QColor(0, 120, 215)
        assert pen.style() == Qt.SolidLine

    def test_hover_pen_style(self, image_item):
        """Hover tiene borde azul punteado."""
        image_item.is_hovered = True
        image_item._update_visual()
        pen = image_item.pen()
        assert pen.style() == Qt.DashLine

    def test_normal_invisible(self, image_item):
        """Estado normal tiene borde invisible."""
        image_item.is_selected = False
        image_item.is_hovered = False
        image_item._update_visual()
        pen = image_item.pen()
        assert pen.style() == Qt.NoPen


# --- Tests de handles de redimensión ---

class TestResizeHandles:
    """Tests de los 8 handles de resize."""

    def test_get_handle_rects_returns_8(self, image_item):
        """Hay 8 handles."""
        handles = image_item._get_handle_rects()
        assert len(handles) == 8

    def test_handle_at_corner(self, image_item):
        """Detecta handle en la esquina inferior derecha."""
        image_item.set_selected(True)
        # El handle bottom-right está centrado en (200, 100)
        handle = image_item._handle_at(QPointF(200, 100))
        assert handle == ResizeHandle.BOTTOM_RIGHT

    def test_handle_at_empty_area(self, image_item):
        """No detecta handle en el centro de la imagen."""
        image_item.set_selected(True)
        handle = image_item._handle_at(QPointF(100, 50))
        assert handle is None

    def test_handle_at_not_selected(self, image_item):
        """No detecta handles si no está seleccionada."""
        image_item.set_selected(False)
        handle = image_item._handle_at(QPointF(0, 0))
        assert handle is None

    def test_handle_top_left(self, image_item):
        """Handle top-left en esquina (0, 0)."""
        image_item.set_selected(True)
        handle = image_item._handle_at(QPointF(0, 0))
        assert handle == ResizeHandle.TOP_LEFT


# --- Tests de redimensión ---

class TestResize:
    """Tests de operaciones de redimensión con coordenadas de escena."""

    def test_do_resize_changes_rect(self, image_item):
        """_do_resize modifica el rect."""
        image_item._active_handle = ResizeHandle.BOTTOM_RIGHT
        image_item._resize_start_scene_pos = QPointF(200, 100)
        image_item._resize_start_rect = QRectF(image_item.rect())
        image_item._resize_start_item_pos = QPointF(image_item.pos())

        image_item._do_resize(QPointF(250, 130))
        rect = image_item.rect()
        assert rect.width() > 200 or rect.height() > 100

    def test_do_resize_min_size(self, image_item):
        """No se puede redimensionar por debajo del tamaño mínimo."""
        image_item._active_handle = ResizeHandle.BOTTOM_RIGHT
        image_item._resize_start_scene_pos = QPointF(200, 100)
        image_item._resize_start_rect = QRectF(image_item.rect())
        image_item._resize_start_item_pos = QPointF(image_item.pos())

        image_item._do_resize(QPointF(5, 5))
        rect = image_item.rect()
        assert rect.width() >= EditableImageItem.MIN_SIZE
        assert rect.height() >= EditableImageItem.MIN_SIZE

    def test_do_resize_keeps_proportion(self, image_item):
        """Con keep_proportion, la proporción se mantiene en esquinas."""
        image_item._active_handle = ResizeHandle.BOTTOM_RIGHT
        image_item._resize_start_scene_pos = QPointF(200, 100)
        image_item._resize_start_rect = QRectF(image_item.rect())
        image_item._resize_start_item_pos = QPointF(image_item.pos())

        image_item._do_resize(QPointF(300, 150))
        rect = image_item.rect()
        ratio = rect.width() / rect.height()
        assert ratio == pytest.approx(2.0, rel=0.1)

    def test_do_resize_free_proportion(self, image_item_no_proportion):
        """Sin keep_proportion, el ratio puede cambiar."""
        item = image_item_no_proportion
        item._active_handle = ResizeHandle.BOTTOM_RIGHT
        item._resize_start_scene_pos = QPointF(200, 100)
        item._resize_start_rect = QRectF(item.rect())
        item._resize_start_item_pos = QPointF(item.pos())

        item._do_resize(QPointF(250, 200))
        rect = item.rect()
        # No se fuerza proporción, así que width y height cambian libremente
        assert rect.width() > 0
        assert rect.height() > 0

    def test_all_corner_handles_resize_consistently(self, image_item):
        """Todos los handles de esquina producen resize proporcional."""
        corners = [
            ResizeHandle.TOP_LEFT, ResizeHandle.TOP_RIGHT,
            ResizeHandle.BOTTOM_LEFT, ResizeHandle.BOTTOM_RIGHT,
        ]
        original_ratio = 200.0 / 100.0  # 2.0

        for handle in corners:
            item = EditableImageItem(
                rect=QRectF(0, 0, 200, 100),
                pixmap=image_item.pixmap,
                keep_proportion=True,
            )
            item.setPos(50, 50)
            item._active_handle = handle
            item._resize_start_scene_pos = QPointF(150, 100)
            item._resize_start_rect = QRectF(item.rect())
            item._resize_start_item_pos = QPointF(item.pos())

            item._do_resize(QPointF(180, 130))
            rect = item.rect()
            assert rect.width() >= EditableImageItem.MIN_SIZE
            assert rect.height() >= EditableImageItem.MIN_SIZE
            ratio = rect.width() / rect.height()
            assert ratio == pytest.approx(original_ratio, rel=0.15), (
                f"Handle {handle.name}: ratio {ratio:.2f} != {original_ratio}"
            )

    def test_lateral_handles_keep_proportion(self, image_item):
        """Handles laterales también mantienen proporción."""
        laterals = [
            ResizeHandle.MIDDLE_LEFT, ResizeHandle.MIDDLE_RIGHT,
            ResizeHandle.TOP_CENTER, ResizeHandle.BOTTOM_CENTER,
        ]
        original_ratio = 200.0 / 100.0

        for handle in laterals:
            item = EditableImageItem(
                rect=QRectF(0, 0, 200, 100),
                pixmap=image_item.pixmap,
                keep_proportion=True,
            )
            item.setPos(50, 50)
            item._active_handle = handle
            item._resize_start_scene_pos = QPointF(150, 100)
            item._resize_start_rect = QRectF(item.rect())
            item._resize_start_item_pos = QPointF(item.pos())

            item._do_resize(QPointF(180, 130))
            rect = item.rect()
            ratio = rect.width() / rect.height()
            assert ratio == pytest.approx(original_ratio, rel=0.15), (
                f"Handle {handle.name}: ratio {ratio:.2f} != {original_ratio}"
            )

    def test_resize_anchor_stays_fixed(self):
        """Al redimensionar desde BOTTOM_RIGHT, el top-left no se mueve."""
        pixmap = QPixmap(200, 100)
        pixmap.fill(QColor(0, 0, 255))
        item = EditableImageItem(
            rect=QRectF(0, 0, 200, 100),
            pixmap=pixmap,
            keep_proportion=False,
        )
        item.setPos(100, 100)
        original_pos = QPointF(item.pos())

        item._active_handle = ResizeHandle.BOTTOM_RIGHT
        item._resize_start_scene_pos = QPointF(300, 200)
        item._resize_start_rect = QRectF(item.rect())
        item._resize_start_item_pos = QPointF(item.pos())

        item._do_resize(QPointF(350, 250))
        # Top-left corner (pos) should not change
        assert item.pos().x() == pytest.approx(original_pos.x(), abs=0.1)
        assert item.pos().y() == pytest.approx(original_pos.y(), abs=0.1)

    def test_resize_from_top_left_moves_pos(self):
        """Al redimensionar desde TOP_LEFT, la posición se desplaza."""
        pixmap = QPixmap(200, 100)
        pixmap.fill(QColor(0, 0, 255))
        item = EditableImageItem(
            rect=QRectF(0, 0, 200, 100),
            pixmap=pixmap,
            keep_proportion=False,
        )
        item.setPos(100, 100)

        item._active_handle = ResizeHandle.TOP_LEFT
        item._resize_start_scene_pos = QPointF(100, 100)
        item._resize_start_rect = QRectF(item.rect())
        item._resize_start_item_pos = QPointF(item.pos())

        # Mover top-left 20px hacia arriba-izquierda → imagen más grande
        item._do_resize(QPointF(80, 80))
        assert item.pos().x() == pytest.approx(80, abs=0.1)
        assert item.pos().y() == pytest.approx(80, abs=0.1)
        assert item.rect().width() == pytest.approx(220, abs=1)


# --- Tests de serialización ---

class TestSerialization:
    """Tests de to_dict / from_dict."""

    def test_to_dict(self, image_item):
        """to_dict retorna los campos esperados."""
        image_item.setPos(50, 60)
        image_item.pdf_rect = (10, 20, 210, 120)
        d = image_item.to_dict()

        assert d['module_id'] == image_item.module_id
        assert d['x'] == 50
        assert d['y'] == 60
        assert d['width'] == 200
        assert d['height'] == 100
        assert d['image_path'] == "/tmp/test.png"
        assert d['keep_proportion'] is True
        assert d['overlay_mode'] is True
        assert d['is_overlay'] is True
        assert d['pending_write'] is True
        assert d['pdf_rect'] == [10, 20, 210, 120]

    def test_to_dict_no_pdf_rect(self, image_item):
        """to_dict funciona sin pdf_rect."""
        d = image_item.to_dict()
        assert d['pdf_rect'] is None

    def test_from_dict_roundtrip(self, sample_pixmap, image_item):
        """from_dict reconstruye el item correctamente."""
        image_item.setPos(30, 40)
        image_item.pdf_rect = (5, 10, 205, 110)
        d = image_item.to_dict()

        restored = EditableImageItem.from_dict(d, sample_pixmap, zoom_level=1.0)
        assert restored.module_id == image_item.module_id
        assert restored.pos().x() == 30
        assert restored.pos().y() == 40
        assert restored.rect().width() == 200
        assert restored.rect().height() == 100
        assert restored.pdf_rect == (5, 10, 205, 110)

    def test_from_dict_defaults(self, sample_pixmap):
        """from_dict usa valores por defecto correctos."""
        d = {'x': 0, 'y': 0, 'width': 100, 'height': 100}
        item = EditableImageItem.from_dict(d, sample_pixmap)
        assert item.keep_proportion is True
        assert item.overlay_mode is True
        assert item.is_overlay is True
        assert item.pending_write is True


# --- Tests de bounding rect ---

class TestBoundingRect:
    """Tests del bounding rect expandido."""

    def test_bounding_rect_larger_than_rect(self, image_item):
        """El bounding rect incluye margen para los handles."""
        br = image_item.boundingRect()
        r = image_item.rect()
        margin = EditableImageItem.HANDLE_SIZE
        assert br.left() < r.left()
        assert br.top() < r.top()
        assert br.right() > r.right()
        assert br.bottom() > r.bottom()


# --- Tests del enum ResizeHandle ---

class TestResizeHandleEnum:
    """Tests del enum de handles."""

    def test_all_values(self):
        """Hay 8 handles con valores 0-7."""
        assert len(ResizeHandle) == 8
        assert ResizeHandle.TOP_LEFT == 0
        assert ResizeHandle.BOTTOM_RIGHT == 7

    def test_int_enum(self):
        """ResizeHandle es IntEnum."""
        assert int(ResizeHandle.MIDDLE_LEFT) == 3

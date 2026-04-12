"""
Tests para el módulo TextSelectionOverlay.

Pruebas de selección de texto con visualización de métricas.
Tarea 3C-04 del Phase 3 PDF Text Engine.
"""

import sys
import os

# Asegurar que el directorio raíz esté en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import MagicMock
from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QColor

from ui.text_selection_overlay import (   # noqa: E402
    TextSelectionOverlay,
    SelectionMode,
    SelectionStyle,
    SelectionConfig,
    MetricIndicator,
    SpanSelectionItem,
    LineSelectionItem,
    CharSpacingIndicator,
    create_selection_overlay,
    create_dark_theme_style,
    create_light_theme_style,
)


# ================== Helpers ==================


def create_test_span_data(
    span_id: str = "test_span_1",
    text: str = "Test Text",
    bbox: tuple = (100, 200, 200, 220),
    baseline_y: float = 215.0,
    origin: tuple = (100, 215),
    ascender: float = 12.0,
    descender: float = 3.0,
    font_name: str = "Arial",
    font_size: float = 12.0,
) -> dict:
    """Crear datos de span de prueba."""
    return {
        'span_id': span_id,
        'text': text,
        'bbox': bbox,
        'baseline_y': baseline_y,
        'origin': origin,
        'ascender': ascender,
        'descender': descender,
        'font_name': font_name,
        'font_size': font_size,
    }


def create_test_line_data(
    line_id: str = "test_line_1",
    text: str = "Test Line Text",
    bbox: tuple = (50, 200, 300, 225),
    baseline_y: float = 220.0,
) -> dict:
    """Crear datos de línea de prueba."""
    return {
        'line_id': line_id,
        'text': text,
        'bbox': bbox,
        'baseline_y': baseline_y,
    }


@pytest.fixture
def mock_scene():
    """Crear una escena mock."""
    scene = MagicMock()
    scene.addItem = MagicMock()
    scene.removeItem = MagicMock()
    return scene


@pytest.fixture
def overlay(mock_scene):
    """Crear un overlay con escena mock."""
    return TextSelectionOverlay(scene=mock_scene)


# ================== Tests para SelectionMode ==================


class TestSelectionMode:
    """Tests para el enum SelectionMode."""
    
    def test_span_mode_exists(self):
        assert SelectionMode.SPAN.value == "span"
    
    def test_line_mode_exists(self):
        assert SelectionMode.LINE.value == "line"
    
    def test_paragraph_mode_exists(self):
        assert SelectionMode.PARAGRAPH.value == "paragraph"
    
    def test_character_mode_exists(self):
        assert SelectionMode.CHARACTER.value == "character"
    
    def test_all_modes_enumerated(self):
        modes = list(SelectionMode)
        assert len(modes) == 4


# ================== Tests para MetricIndicator ==================


class TestMetricIndicator:
    """Tests para el enum MetricIndicator."""
    
    def test_bbox_indicator(self):
        assert MetricIndicator.BBOX.value == "bbox"
    
    def test_baseline_indicator(self):
        assert MetricIndicator.BASELINE.value == "baseline"
    
    def test_ascender_indicator(self):
        assert MetricIndicator.ASCENDER.value == "ascender"
    
    def test_descender_indicator(self):
        assert MetricIndicator.DESCENDER.value == "descender"
    
    def test_char_spacing_indicator(self):
        assert MetricIndicator.CHAR_SPACING.value == "char_spacing"
    
    def test_word_spacing_indicator(self):
        assert MetricIndicator.WORD_SPACING.value == "word_spacing"
    
    def test_origin_indicator(self):
        assert MetricIndicator.ORIGIN.value == "origin"


# ================== Tests para SelectionStyle ==================


class TestSelectionStyle:
    """Tests para la clase SelectionStyle."""
    
    def test_default_style_creation(self):
        style = SelectionStyle()
        assert style.fill_color is not None
        assert style.stroke_color is not None
        assert style.stroke_width == 1.5
    
    def test_default_show_flags(self):
        style = SelectionStyle()
        assert style.show_bbox is True
        assert style.show_baseline is True
        assert style.show_ascender is False
        assert style.show_descender is False
    
    def test_custom_colors(self):
        fill = QColor(255, 0, 0, 100)
        stroke = QColor(0, 255, 0, 200)
        style = SelectionStyle(fill_color=fill, stroke_color=stroke)
        assert style.fill_color == fill
        assert style.stroke_color == stroke
    
    def test_metric_colors(self):
        style = SelectionStyle()
        assert style.baseline_color is not None
        assert style.ascender_color is not None
        assert style.descender_color is not None
        assert style.origin_color is not None


# ================== Tests para SelectionConfig ==================


class TestSelectionConfig:
    """Tests para la clase SelectionConfig."""
    
    def test_default_config(self):
        config = SelectionConfig()
        assert config.mode == SelectionMode.SPAN
        assert config.multi_select is True
        assert config.z_value == 100.0
    
    def test_custom_mode(self):
        config = SelectionConfig(mode=SelectionMode.LINE)
        assert config.mode == SelectionMode.LINE
    
    def test_custom_multi_select(self):
        config = SelectionConfig(multi_select=False)
        assert config.multi_select is False
    
    def test_stroke_width_limits(self):
        config = SelectionConfig()
        assert config.base_stroke_width == 1.5
        assert config.min_stroke_width == 0.5
        assert config.max_stroke_width == 4.0


# ================== Tests para SpanSelectionItem ==================


class TestSpanSelectionItem:
    """Tests para la clase SpanSelectionItem."""
    
    def test_creation(self):
        span_data = create_test_span_data()
        style = SelectionStyle()
        item = SpanSelectionItem(span_data, style)
        
        assert item is not None
        assert item.span_data == span_data
    
    def test_span_id_property(self):
        span_data = create_test_span_data(span_id="my_span")
        item = SpanSelectionItem(span_data, SelectionStyle())
        
        assert item.span_id == "my_span"
    
    def test_rect_from_bbox(self):
        bbox = (10, 20, 110, 40)
        span_data = create_test_span_data(bbox=bbox)
        item = SpanSelectionItem(span_data, SelectionStyle())
        
        rect = item.rect()
        assert rect.x() == 10
        assert rect.y() == 20
        assert rect.width() == 100
        assert rect.height() == 20
    
    def test_hover_state(self):
        item = SpanSelectionItem(create_test_span_data(), SelectionStyle())
        
        assert item._is_hovered is False
        item.set_hovered(True)
        assert item._is_hovered is True
        item.set_hovered(False)
        assert item._is_hovered is False


# ================== Tests para LineSelectionItem ==================


class TestLineSelectionItem:
    """Tests para la clase LineSelectionItem."""
    
    def test_creation(self):
        line_data = create_test_line_data()
        style = SelectionStyle()
        item = LineSelectionItem(line_data, style)
        
        assert item is not None
        assert item.line_data == line_data
    
    def test_line_id_property(self):
        line_data = create_test_line_data(line_id="my_line")
        item = LineSelectionItem(line_data, SelectionStyle())
        
        assert item.line_id == "my_line"
    
    def test_rect_from_bbox(self):
        bbox = (50, 100, 350, 125)
        line_data = create_test_line_data(bbox=bbox)
        item = LineSelectionItem(line_data, SelectionStyle())
        
        rect = item.rect()
        assert rect.x() == 50
        assert rect.y() == 100
        assert rect.width() == 300
        assert rect.height() == 25


# ================== Tests para TextSelectionOverlay - Creación ==================


class TestTextSelectionOverlayCreation:
    """Tests para la creación del overlay."""
    
    def test_creation_without_scene(self):
        overlay = TextSelectionOverlay()
        assert overlay is not None
        assert overlay.scene is None
    
    def test_creation_with_scene(self, mock_scene):
        overlay = TextSelectionOverlay(scene=mock_scene)
        assert overlay.scene == mock_scene
    
    def test_creation_with_config(self):
        config = SelectionConfig(mode=SelectionMode.LINE)
        overlay = TextSelectionOverlay(config=config)
        assert overlay.config.mode == SelectionMode.LINE
    
    def test_default_enabled(self):
        overlay = TextSelectionOverlay()
        assert overlay.enabled is True
    
    def test_default_no_selection(self):
        overlay = TextSelectionOverlay()
        assert overlay.has_selection is False
        assert overlay.selection_count == 0


# ================== Tests para TextSelectionOverlay - Selección de Span ==================


class TestTextSelectionOverlaySpanSelection:
    """Tests para la selección de spans."""
    
    def test_select_span(self, overlay, mock_scene):
        span_data = create_test_span_data()
        result = overlay.select_span(span_data)
        
        assert result is True
        assert overlay.has_selection is True
        assert mock_scene.addItem.called
    
    def test_select_span_without_scene(self):
        overlay = TextSelectionOverlay(scene=None)
        span_data = create_test_span_data()
        result = overlay.select_span(span_data)
        
        assert result is False
    
    def test_select_span_when_disabled(self, overlay):
        overlay.enabled = False
        span_data = create_test_span_data()
        result = overlay.select_span(span_data)
        
        assert result is False
    
    def test_deselect_span(self, overlay, mock_scene):
        span_data = create_test_span_data(span_id="span_1")
        overlay.select_span(span_data)
        
        result = overlay.deselect_span("span_1")
        
        assert result is True
        assert overlay.has_selection is False
    
    def test_deselect_nonexistent_span(self, overlay):
        result = overlay.deselect_span("nonexistent")
        assert result is False
    
    def test_toggle_span_selection_on(self, overlay, mock_scene):
        span_data = create_test_span_data()
        result = overlay.toggle_span_selection(span_data)
        
        assert result is True  # Quedó seleccionado
        assert overlay.has_selection is True
    
    def test_toggle_span_selection_off(self, overlay, mock_scene):
        span_data = create_test_span_data(span_id="toggle_span")
        overlay.select_span(span_data)
        
        result = overlay.toggle_span_selection(span_data)
        
        assert result is False  # Se deseleccionó
        assert overlay.has_selection is False
    
    def test_multi_select_spans(self, overlay, mock_scene):
        span1 = create_test_span_data(span_id="span_1")
        span2 = create_test_span_data(span_id="span_2")
        
        overlay.select_span(span1, add_to_selection=False)
        overlay.select_span(span2, add_to_selection=True)
        
        assert overlay.selection_count == 2
    
    def test_single_select_clears_previous(self, overlay, mock_scene):
        span1 = create_test_span_data(span_id="span_1")
        span2 = create_test_span_data(span_id="span_2")
        
        overlay.select_span(span1)
        overlay.select_span(span2, add_to_selection=False)
        
        assert overlay.selection_count == 1
        assert "span_2" in overlay.selected_span_ids
    
    def test_select_multiple_spans(self, overlay, mock_scene):
        spans = [
            create_test_span_data(span_id=f"span_{i}")
            for i in range(5)
        ]
        
        count = overlay.select_spans(spans)
        
        assert count == 5
        assert overlay.selection_count == 5
    
    def test_is_span_selected(self, overlay, mock_scene):
        span_data = create_test_span_data(span_id="check_span")
        
        assert overlay.is_span_selected("check_span") is False
        
        overlay.select_span(span_data)
        
        assert overlay.is_span_selected("check_span") is True


# ================== Tests para TextSelectionOverlay - Selección de Línea ==================


class TestTextSelectionOverlayLineSelection:
    """Tests para la selección de líneas."""
    
    def test_select_line(self, overlay, mock_scene):
        line_data = create_test_line_data()
        result = overlay.select_line(line_data)
        
        assert result is True
        assert overlay.has_selection is True
    
    def test_deselect_line(self, overlay, mock_scene):
        line_data = create_test_line_data(line_id="line_1")
        overlay.select_line(line_data)
        
        result = overlay.deselect_line("line_1")
        
        assert result is True
        assert overlay.has_selection is False
    
    def test_is_line_selected(self, overlay, mock_scene):
        line_data = create_test_line_data(line_id="check_line")
        
        assert overlay.is_line_selected("check_line") is False
        
        overlay.select_line(line_data)
        
        assert overlay.is_line_selected("check_line") is True


# ================== Tests para TextSelectionOverlay - Hover ==================


class TestTextSelectionOverlayHover:
    """Tests para el hover sobre elementos."""
    
    def test_set_hover_span(self, overlay, mock_scene):
        span_data = create_test_span_data()
        overlay.set_hover_span(span_data)
        
        assert overlay._hover_item is not None
    
    def test_clear_hover(self, overlay, mock_scene):
        span_data = create_test_span_data()
        overlay.set_hover_span(span_data)
        overlay.clear_hover()
        
        assert overlay._hover_item is None
    
    def test_hover_none_clears(self, overlay, mock_scene):
        span_data = create_test_span_data()
        overlay.set_hover_span(span_data)
        overlay.set_hover_span(None)
        
        assert overlay._hover_item is None
    
    def test_hover_not_shown_when_selected(self, overlay, mock_scene):
        span_data = create_test_span_data(span_id="selected_span")
        overlay.select_span(span_data)
        
        # Intentar hover sobre el mismo span
        overlay.set_hover_span(span_data)
        
        # No debería crear hover item si ya está seleccionado
        assert overlay._hover_item is None


# ================== Tests para TextSelectionOverlay - Limpieza ==================


class TestTextSelectionOverlayClear:
    """Tests para la limpieza de selección."""
    
    def test_clear_spans(self, overlay, mock_scene):
        span1 = create_test_span_data(span_id="span_1")
        span2 = create_test_span_data(span_id="span_2")
        overlay.select_span(span1, add_to_selection=True)
        overlay.select_span(span2, add_to_selection=True)
        
        overlay.clear_spans()
        
        assert len(overlay._selected_spans) == 0
    
    def test_clear_lines(self, overlay, mock_scene):
        line1 = create_test_line_data(line_id="line_1")
        line2 = create_test_line_data(line_id="line_2")
        overlay.select_line(line1, add_to_selection=True)
        overlay.select_line(line2, add_to_selection=True)
        
        overlay.clear_lines()
        
        assert len(overlay._selected_lines) == 0
    
    def test_clear_all(self, overlay, mock_scene):
        span = create_test_span_data()
        line = create_test_line_data()
        
        overlay.select_span(span, add_to_selection=True)
        overlay.select_line(line, add_to_selection=True)
        overlay.set_hover_span(create_test_span_data(span_id="hover"))
        
        overlay.clear_all()
        
        assert overlay.has_selection is False
        assert overlay._hover_item is None


# ================== Tests para TextSelectionOverlay - Métricas ==================


class TestTextSelectionOverlayMetrics:
    """Tests para la configuración de métricas."""
    
    def test_set_metric_visibility_bbox(self, overlay):
        overlay.set_metric_visibility(MetricIndicator.BBOX, False)
        assert overlay.style.show_bbox is False
        
        overlay.set_metric_visibility(MetricIndicator.BBOX, True)
        assert overlay.style.show_bbox is True
    
    def test_set_metric_visibility_baseline(self, overlay):
        overlay.set_metric_visibility(MetricIndicator.BASELINE, False)
        assert overlay.style.show_baseline is False
    
    def test_set_metric_visibility_ascender(self, overlay):
        overlay.set_metric_visibility(MetricIndicator.ASCENDER, True)
        assert overlay.style.show_ascender is True
    
    def test_metrics_preset_minimal(self, overlay):
        overlay.set_metrics_preset('minimal')
        
        assert overlay.style.show_bbox is True
        assert overlay.style.show_baseline is False
        assert overlay.style.show_ascender is False
    
    def test_metrics_preset_standard(self, overlay):
        overlay.set_metrics_preset('standard')
        
        assert overlay.style.show_bbox is True
        assert overlay.style.show_baseline is True
        assert overlay.style.show_ascender is False
    
    def test_metrics_preset_detailed(self, overlay):
        overlay.set_metrics_preset('detailed')
        
        assert overlay.style.show_bbox is True
        assert overlay.style.show_baseline is True
        assert overlay.style.show_ascender is True
        assert overlay.style.show_descender is True
        assert overlay.style.show_origin is True
    
    def test_metrics_preset_all(self, overlay):
        overlay.set_metrics_preset('all')
        
        assert overlay.style.show_bbox is True
        assert overlay.style.show_baseline is True
        assert overlay.style.show_ascender is True
        assert overlay.style.show_descender is True
        assert overlay.style.show_char_spacing is True
        assert overlay.style.show_word_spacing is True
        assert overlay.style.show_origin is True
    
    def test_get_active_metrics(self, overlay):
        overlay.set_metrics_preset('standard')
        
        active = overlay.get_active_metrics()
        
        assert MetricIndicator.BBOX in active
        assert MetricIndicator.BASELINE in active
        assert MetricIndicator.ASCENDER not in active


# ================== Tests para TextSelectionOverlay - Zoom ==================


class TestTextSelectionOverlayZoom:
    """Tests para el manejo de zoom."""
    
    def test_set_zoom(self, overlay):
        overlay.set_zoom(2.0)
        assert overlay._zoom == 2.0
    
    def test_set_zoom_minimum(self, overlay):
        overlay.set_zoom(0.05)
        assert overlay._zoom == 0.1  # Mínimo
    
    def test_zoom_updates_stroke_width(self, overlay):
        initial_width = overlay.style.stroke_width
        overlay.set_zoom(2.0)
        # El ancho debería ajustarse
        assert overlay.style.stroke_width != initial_width


# ================== Tests para TextSelectionOverlay - Consultas ==================


class TestTextSelectionOverlayQueries:
    """Tests para consultas de selección."""
    
    def test_get_selected_spans_data(self, overlay, mock_scene):
        span1 = create_test_span_data(span_id="span_1", text="Text 1")
        span2 = create_test_span_data(span_id="span_2", text="Text 2")
        overlay.select_span(span1, add_to_selection=True)
        overlay.select_span(span2, add_to_selection=True)
        
        data = overlay.get_selected_spans_data()
        
        assert len(data) == 2
        texts = [d['text'] for d in data]
        assert "Text 1" in texts
        assert "Text 2" in texts
    
    def test_get_selected_lines_data(self, overlay, mock_scene):
        line = create_test_line_data(line_id="line_1", text="Line Text")
        overlay.select_line(line)
        
        data = overlay.get_selected_lines_data()
        
        assert len(data) == 1
        assert data[0]['text'] == "Line Text"
    
    def test_get_selection_bounds_empty(self, overlay):
        bounds = overlay.get_selection_bounds()
        assert bounds is None
    
    def test_get_selection_bounds_single_span(self, overlay, mock_scene):
        span = create_test_span_data(bbox=(10, 20, 110, 40))
        overlay.select_span(span)
        
        bounds = overlay.get_selection_bounds()
        
        assert bounds is not None
        assert bounds.x() == 10
        assert bounds.y() == 20
    
    def test_selected_span_ids(self, overlay, mock_scene):
        span1 = create_test_span_data(span_id="id_1")
        span2 = create_test_span_data(span_id="id_2")
        overlay.select_span(span1, add_to_selection=True)
        overlay.select_span(span2, add_to_selection=True)
        
        ids = overlay.selected_span_ids
        
        assert "id_1" in ids
        assert "id_2" in ids


# ================== Tests para TextSelectionOverlay - Modo de Selección ==================


class TestTextSelectionOverlayMode:
    """Tests para cambio de modo de selección."""
    
    def test_default_mode_is_span(self, overlay):
        assert overlay.selection_mode == SelectionMode.SPAN
    
    def test_change_mode_clears_selection(self, overlay, mock_scene):
        span = create_test_span_data()
        overlay.select_span(span)
        
        overlay.selection_mode = SelectionMode.LINE
        
        assert overlay.has_selection is False
        assert overlay.selection_mode == SelectionMode.LINE
    
    def test_change_mode_same_no_clear(self, overlay, mock_scene):
        span = create_test_span_data()
        overlay.select_span(span)
        
        # Asignar el mismo modo no debería limpiar
        overlay.selection_mode = SelectionMode.SPAN
        
        assert overlay.has_selection is True


# ================== Tests para Factory Functions ==================


class TestFactoryFunctions:
    """Tests para las funciones factory."""
    
    def test_create_selection_overlay_basic(self):
        overlay = create_selection_overlay()
        
        assert overlay is not None
        assert isinstance(overlay, TextSelectionOverlay)
    
    def test_create_selection_overlay_with_mode(self):
        overlay = create_selection_overlay(mode=SelectionMode.LINE)
        
        assert overlay.selection_mode == SelectionMode.LINE
    
    def test_create_selection_overlay_with_preset(self):
        overlay = create_selection_overlay(preset='detailed')
        
        assert overlay.style.show_ascender is True
        assert overlay.style.show_descender is True
    
    def test_create_dark_theme_style(self):
        style = create_dark_theme_style()
        
        assert style is not None
        assert isinstance(style, SelectionStyle)
        # El tema oscuro debería tener colores más brillantes
        assert style.fill_color.alpha() > 0
    
    def test_create_light_theme_style(self):
        style = create_light_theme_style()
        
        assert style is not None
        assert isinstance(style, SelectionStyle)
        # El tema claro debería tener colores más oscuros
        assert style.fill_color.alpha() > 0


# ================== Tests para Señales ==================


class TestTextSelectionOverlaySignals:
    """Tests para las señales del overlay."""
    
    def test_selection_changed_signal(self, overlay, mock_scene):
        signal_received = []
        overlay.selectionChanged.connect(lambda: signal_received.append(True))
        
        overlay.select_span(create_test_span_data())
        
        assert len(signal_received) > 0
    
    def test_span_selected_signal(self, overlay, mock_scene):
        received_data = []
        overlay.spanSelected.connect(lambda d: received_data.append(d))
        
        span_data = create_test_span_data(text="Signal Test")
        overlay.select_span(span_data)
        
        assert len(received_data) == 1
        assert received_data[0]['text'] == "Signal Test"
    
    def test_line_selected_signal(self, overlay, mock_scene):
        received_data = []
        overlay.lineSelected.connect(lambda d: received_data.append(d))
        
        line_data = create_test_line_data(text="Line Signal Test")
        overlay.select_line(line_data)
        
        assert len(received_data) == 1
        assert received_data[0]['text'] == "Line Signal Test"
    
    def test_metrics_updated_signal(self, overlay):
        received_metrics = []
        overlay.metricsUpdated.connect(lambda m: received_metrics.append(m))
        
        overlay.set_metrics_preset('detailed')
        
        assert len(received_metrics) > 0
        assert MetricIndicator.BASELINE in received_metrics[0]


# ================== Tests para CharSpacingIndicator ==================


class TestCharSpacingIndicator:
    """Tests para el indicador de espaciado de caracteres."""
    
    def test_creation(self):
        positions = [10.0, 20.0, 30.0]
        indicator = CharSpacingIndicator(
            positions=positions,
            y=100.0,
            height=15.0,
            color=QColor(255, 200, 0)
        )
        
        assert indicator is not None
    
    def test_bounding_rect_empty(self):
        indicator = CharSpacingIndicator([], 100.0, 15.0, QColor(255, 200, 0))
        rect = indicator.boundingRect()
        
        assert rect.isEmpty() or rect == QRectF()
    
    def test_bounding_rect_with_positions(self):
        positions = [10.0, 50.0, 90.0]
        indicator = CharSpacingIndicator(positions, 100.0, 15.0, QColor(255, 200, 0))
        rect = indicator.boundingRect()
        
        assert rect.width() >= 80  # min a max


# ================== Tests de Integración ==================


class TestTextSelectionOverlayIntegration:
    """Tests de integración."""
    
    def test_full_selection_workflow(self, mock_scene):
        # Crear overlay
        overlay = create_selection_overlay(
            scene=mock_scene,
            mode=SelectionMode.SPAN,
            preset='standard'
        )
        
        # Seleccionar varios spans
        spans = [create_test_span_data(span_id=f"span_{i}") for i in range(3)]
        for span in spans:
            overlay.select_span(span, add_to_selection=True)
        
        # Verificar selección
        assert overlay.selection_count == 3
        assert overlay.has_selection is True
        
        # Deseleccionar uno
        overlay.deselect_span("span_1")
        assert overlay.selection_count == 2
        
        # Limpiar todo
        overlay.clear_all()
        assert overlay.has_selection is False
    
    def test_hover_and_selection_workflow(self, mock_scene):
        overlay = create_selection_overlay(scene=mock_scene)
        
        # Hover sobre un span
        hover_span = create_test_span_data(span_id="hover_span")
        overlay.set_hover_span(hover_span)
        assert overlay._hover_item is not None
        
        # Seleccionar ese span (debería limpiar hover)
        overlay.select_span(hover_span)
        assert overlay.has_selection is True
        
        # Hover sobre el seleccionado no debería crear nuevo hover item
        overlay.set_hover_span(hover_span)
        assert overlay._hover_item is None
    
    def test_mode_switching_workflow(self, mock_scene):
        overlay = create_selection_overlay(scene=mock_scene)
        
        # Seleccionar span
        overlay.select_span(create_test_span_data())
        assert overlay.selection_count == 1
        
        # Cambiar a modo línea
        overlay.selection_mode = SelectionMode.LINE
        assert overlay.selection_count == 0  # Se limpió
        
        # Seleccionar línea
        overlay.select_line(create_test_line_data())
        assert overlay.selection_count == 1


# ================== Tests de Edge Cases ==================


class TestTextSelectionOverlayEdgeCases:
    """Tests para casos límite."""
    
    def test_select_same_span_twice(self, overlay, mock_scene):
        span = create_test_span_data(span_id="same_span")
        
        overlay.select_span(span)
        overlay.select_span(span)  # Mismo span de nuevo
        
        assert overlay.selection_count == 1
    
    def test_span_without_id(self, overlay, mock_scene):
        span_data = {'bbox': (0, 0, 100, 20), 'text': 'No ID'}
        # Sin span_id, debería generar uno automáticamente
        
        result = overlay.select_span(span_data)
        assert result is True
        assert overlay.has_selection is True
    
    def test_span_with_zero_size_bbox(self, overlay, mock_scene):
        span = create_test_span_data(bbox=(100, 200, 100, 200))  # Zero size
        result = overlay.select_span(span)
        
        assert result is True  # Debería aceptarse
    
    def test_disabled_overlay_clears_on_disable(self, mock_scene):
        overlay = create_selection_overlay(scene=mock_scene)
        overlay.select_span(create_test_span_data())
        
        overlay.enabled = False
        
        assert overlay.has_selection is False
    
    def test_scene_change_clears_selection(self, mock_scene):
        overlay = create_selection_overlay(scene=mock_scene)
        overlay.select_span(create_test_span_data())
        
        new_scene = MagicMock()
        new_scene.addItem = MagicMock()
        new_scene.removeItem = MagicMock()
        overlay.scene = new_scene
        
        assert overlay.has_selection is False


# ================== Tests de Performance ==================


class TestTextSelectionOverlayPerformance:
    """Tests de rendimiento."""
    
    def test_select_many_spans(self, mock_scene):
        overlay = create_selection_overlay(scene=mock_scene)
        
        # Seleccionar 100 spans
        spans = [create_test_span_data(span_id=f"perf_span_{i}") for i in range(100)]
        
        import time
        start = time.time()
        count = overlay.select_spans(spans)
        elapsed = time.time() - start
        
        assert count == 100
        assert elapsed < 1.0  # Debería ser rápido
    
    def test_clear_many_selections(self, mock_scene):
        overlay = create_selection_overlay(scene=mock_scene)
        spans = [create_test_span_data(span_id=f"clear_span_{i}") for i in range(50)]
        overlay.select_spans(spans)
        
        import time
        start = time.time()
        overlay.clear_all()
        elapsed = time.time() - start
        
        assert overlay.has_selection is False
        assert elapsed < 0.5

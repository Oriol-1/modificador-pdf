"""
Tests para el módulo text_properties_tooltip.

PHASE3-3C03: Tooltip de propiedades al hover

Tests comprehensivos para:
- TooltipConfig configuración
- TooltipStyle enum
- format_span_tooltip() formateo
- format_line_tooltip() formateo
- TextPropertiesTooltip clase principal
- Integración con PDFPageView
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import Mock

from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import QTimer

from ui.text_properties_tooltip import (
    TooltipStyle,
    TooltipConfig,
    format_span_tooltip,
    format_line_tooltip,
    TextPropertiesTooltip,
    create_text_properties_tooltip,
    _escape_html,
    _tooltip_row,
    _format_embedding_status,
    TEXT_ENGINE_AVAILABLE,
)


# Fixture para QApplication
@pytest.fixture(scope="module")
def qapp():
    """Crea una QApplication para los tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

# Import text_engine si disponible
if TEXT_ENGINE_AVAILABLE:
    from core.text_engine import (
        TextSpanMetrics,
        TextLine,
        FontEmbeddingStatus,
    )


def create_test_span(
    text: str = "Test",
    page_num: int = 0,
    font_name: str = "Arial",
    font_size: float = 12.0,
    is_bold: bool = False,
    is_italic: bool = False,
    fill_color: str = "#000000",
    bbox: tuple = (0, 0, 100, 20),
    char_spacing: float = 0.0,
    word_spacing: float = 0.0,
    baseline_y: float = 0.0,
    embedding_status=None,
    was_fallback: bool = False,
    fallback_from: str = None,
) -> 'TextSpanMetrics':
    """Helper para crear spans de prueba con parámetros simplificados."""
    if not TEXT_ENGINE_AVAILABLE:
        return None
    
    kwargs = {
        'text': text,
        'page_num': page_num,
        'font_name': font_name,
        'font_size': font_size,
        'is_bold': is_bold,
        'is_italic': is_italic,
        'fill_color': fill_color,
        'bbox': bbox,
        'char_spacing': char_spacing,
        'word_spacing': word_spacing,
        'baseline_y': baseline_y,
        'was_fallback': was_fallback,
    }
    
    if embedding_status is not None:
        kwargs['embedding_status'] = embedding_status
    
    if fallback_from is not None:
        kwargs['fallback_from'] = fallback_from
    
    return TextSpanMetrics(**kwargs)


# ===========================================================================
# Tests para TooltipStyle
# ===========================================================================

class TestTooltipStyle:
    """Tests para el enum TooltipStyle."""
    
    def test_compact_style_exists(self):
        """Verificar que existe estilo COMPACT."""
        assert TooltipStyle.COMPACT.value == "compact"
    
    def test_standard_style_exists(self):
        """Verificar que existe estilo STANDARD."""
        assert TooltipStyle.STANDARD.value == "standard"
    
    def test_detailed_style_exists(self):
        """Verificar que existe estilo DETAILED."""
        assert TooltipStyle.DETAILED.value == "detailed"
    
    def test_all_styles_enumerated(self):
        """Verificar que hay exactamente 3 estilos."""
        styles = list(TooltipStyle)
        assert len(styles) == 3


# ===========================================================================
# Tests para TooltipConfig
# ===========================================================================

class TestTooltipConfig:
    """Tests para la configuración del tooltip."""
    
    def test_default_config(self):
        """Verificar configuración por defecto."""
        config = TooltipConfig()
        assert config.style == TooltipStyle.STANDARD
        assert config.show_delay_ms == 300
        assert config.hide_delay_ms == 100
        assert config.max_text_preview == 30
        assert config.show_color_swatch is True
        assert config.show_spacing is True
        assert config.show_embedding is True
        assert config.show_geometry is False
        assert config.dark_theme is True
    
    def test_custom_config(self):
        """Verificar configuración personalizada."""
        config = TooltipConfig(
            style=TooltipStyle.DETAILED,
            show_delay_ms=500,
            hide_delay_ms=50,
            max_text_preview=50,
            show_color_swatch=False,
            dark_theme=False
        )
        assert config.style == TooltipStyle.DETAILED
        assert config.show_delay_ms == 500
        assert config.hide_delay_ms == 50
        assert config.max_text_preview == 50
        assert config.show_color_swatch is False
        assert config.dark_theme is False
    
    def test_config_compact_style(self):
        """Verificar configuración con estilo compacto."""
        config = TooltipConfig(style=TooltipStyle.COMPACT)
        assert config.style == TooltipStyle.COMPACT


# ===========================================================================
# Tests para funciones auxiliares
# ===========================================================================

class TestHelperFunctions:
    """Tests para funciones auxiliares."""
    
    def test_escape_html_ampersand(self):
        """Escapar ampersand."""
        assert _escape_html("A & B") == "A &amp; B"
    
    def test_escape_html_less_than(self):
        """Escapar menor que."""
        assert _escape_html("A < B") == "A &lt; B"
    
    def test_escape_html_greater_than(self):
        """Escapar mayor que."""
        assert _escape_html("A > B") == "A &gt; B"
    
    def test_escape_html_quotes(self):
        """Escapar comillas dobles."""
        assert _escape_html('A "B" C') == "A &quot;B&quot; C"
    
    def test_escape_html_combined(self):
        """Escapar múltiples caracteres."""
        result = _escape_html('<div class="test">&</div>')
        assert "&lt;" in result
        assert "&gt;" in result
        assert "&amp;" in result
        assert "&quot;" in result
    
    def test_tooltip_row_format(self):
        """Verificar formato de fila de tooltip."""
        row = _tooltip_row("Fuente", "Arial", "#666666")
        assert "<tr>" in row
        assert "</tr>" in row
        assert "Fuente:" in row
        assert "Arial" in row
        assert "#666666" in row
    
    @pytest.mark.skipif(not TEXT_ENGINE_AVAILABLE, reason="text_engine no disponible")
    def test_format_embedding_fully_embedded(self):
        """Verificar formato de estado embebido completo."""
        result = _format_embedding_status(FontEmbeddingStatus.FULLY_EMBEDDED)
        assert "Embebida" in result or "✓" in result
    
    @pytest.mark.skipif(not TEXT_ENGINE_AVAILABLE, reason="text_engine no disponible")
    def test_format_embedding_subset(self):
        """Verificar formato de estado subset."""
        result = _format_embedding_status(FontEmbeddingStatus.SUBSET)
        assert "Subset" in result or "⊂" in result
    
    @pytest.mark.skipif(not TEXT_ENGINE_AVAILABLE, reason="text_engine no disponible")
    def test_format_embedding_not_embedded(self):
        """Verificar formato de estado no embebido."""
        result = _format_embedding_status(FontEmbeddingStatus.NOT_EMBEDDED)
        assert "No embebida" in result or "✗" in result
    
    def test_format_embedding_none(self):
        """Verificar formato cuando status es None."""
        result = _format_embedding_status(None)
        assert "Desconocido" in result


# ===========================================================================
# Tests para format_span_tooltip
# ===========================================================================

class TestFormatSpanTooltip:
    """Tests para la función format_span_tooltip."""
    
    def test_returns_empty_for_none(self):
        """Retorna cadena vacía si span es None."""
        result = format_span_tooltip(None)
        assert result == ""
    
    @pytest.mark.skipif(not TEXT_ENGINE_AVAILABLE, reason="text_engine no disponible")
    def test_basic_span_format(self):
        """Formatear span básico."""
        span = create_test_span(
            text="Hola mundo",
            font_name="Arial",
            font_size=12.0,
            fill_color="#000000",
            bbox=(0, 0, 100, 20)
        )
        
        result = format_span_tooltip(span)
        
        assert "Hola mundo" in result
        assert "Arial" in result
        assert "12" in result
        assert "#000000" in result
    
    @pytest.mark.skipif(not TEXT_ENGINE_AVAILABLE, reason="text_engine no disponible")
    def test_bold_style_shown(self):
        """Mostrar estilo bold."""
        span = create_test_span(
            text="Texto bold",
            font_name="Arial-Bold",
            is_bold=True
        )
        
        result = format_span_tooltip(span)
        assert "Bold" in result
    
    @pytest.mark.skipif(not TEXT_ENGINE_AVAILABLE, reason="text_engine no disponible")
    def test_italic_style_shown(self):
        """Mostrar estilo italic."""
        span = create_test_span(
            text="Texto italic",
            font_name="Arial-Italic",
            is_italic=True
        )
        
        result = format_span_tooltip(span)
        assert "Italic" in result
    
    @pytest.mark.skipif(not TEXT_ENGINE_AVAILABLE, reason="text_engine no disponible")
    def test_text_preview_truncation(self):
        """Truncar texto preview largo."""
        long_text = "A" * 100
        span = create_test_span(text=long_text)
        
        config = TooltipConfig(max_text_preview=30)
        result = format_span_tooltip(span, config)
        
        # Verificar que hay ellipsis
        assert "…" in result
        # No debería incluir todo el texto
        assert long_text not in result
    
    @pytest.mark.skipif(not TEXT_ENGINE_AVAILABLE, reason="text_engine no disponible")
    def test_dark_theme_colors(self):
        """Verificar colores de tema oscuro."""
        span = create_test_span()
        
        config = TooltipConfig(dark_theme=True)
        result = format_span_tooltip(span, config)
        
        assert "#2d2d2d" in result  # background oscuro
    
    @pytest.mark.skipif(not TEXT_ENGINE_AVAILABLE, reason="text_engine no disponible")
    def test_light_theme_colors(self):
        """Verificar colores de tema claro."""
        span = create_test_span()
        
        config = TooltipConfig(dark_theme=False)
        result = format_span_tooltip(span, config)
        
        assert "#ffffff" in result  # background claro
    
    @pytest.mark.skipif(not TEXT_ENGINE_AVAILABLE, reason="text_engine no disponible")
    def test_compact_style_minimal(self):
        """Estilo compacto muestra información mínima."""
        span = create_test_span(
            char_spacing=0.5,
            word_spacing=1.0
        )
        
        config = TooltipConfig(style=TooltipStyle.COMPACT)
        result = format_span_tooltip(span, config)
        
        # Compact no debería mostrar espaciado
        assert "Tc" not in result
    
    @pytest.mark.skipif(not TEXT_ENGINE_AVAILABLE, reason="text_engine no disponible")
    def test_detailed_style_full(self):
        """Estilo detallado muestra toda la información."""
        span = create_test_span(
            bbox=(10, 20, 50, 40),
            baseline_y=35.0
        )
        
        config = TooltipConfig(style=TooltipStyle.DETAILED, show_geometry=True)
        result = format_span_tooltip(span, config)
        
        # Detailed debería mostrar bbox
        assert "BBox" in result
    
    @pytest.mark.skipif(not TEXT_ENGINE_AVAILABLE, reason="text_engine no disponible")
    def test_color_swatch_included(self):
        """Incluir swatch de color."""
        span = create_test_span(fill_color="#ff0000")
        
        config = TooltipConfig(show_color_swatch=True)
        result = format_span_tooltip(span, config)
        
        assert "#ff0000" in result
        assert "background-color" in result
    
    @pytest.mark.skipif(not TEXT_ENGINE_AVAILABLE, reason="text_engine no disponible")
    def test_html_in_text_escaped(self):
        """Texto con HTML debe escaparse."""
        span = create_test_span(text="<script>alert('xss')</script>")
        
        result = format_span_tooltip(span)
        
        # Verificar que no hay etiquetas sin escapar
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


# ===========================================================================
# Tests para format_line_tooltip
# ===========================================================================

class TestFormatLineTooltip:
    """Tests para la función format_line_tooltip."""
    
    def test_returns_empty_for_none(self):
        """Retorna cadena vacía si line es None."""
        result = format_line_tooltip(None)
        assert result == ""
    
    @pytest.mark.skipif(not TEXT_ENGINE_AVAILABLE, reason="text_engine no disponible")
    def test_basic_line_format(self):
        """Formatear línea básica."""
        span = create_test_span(text="Línea de prueba")
        line = TextLine(spans=[span], page_num=0)
        
        result = format_line_tooltip(line)
        
        assert "Línea" in result
        assert "1" in result  # span_count


# ===========================================================================
# Tests para TextPropertiesTooltip
# ===========================================================================

class TestTextPropertiesTooltip:
    """Tests para la clase TextPropertiesTooltip."""
    
    def test_init_default_config(self, qapp):
        """Inicialización con configuración por defecto."""
        widget = QWidget()
        tooltip = TextPropertiesTooltip(widget)
        
        assert tooltip.enabled is True
        assert tooltip.config.style == TooltipStyle.STANDARD
    
    def test_init_custom_config(self, qapp):
        """Inicialización con configuración personalizada."""
        widget = QWidget()
        config = TooltipConfig(style=TooltipStyle.DETAILED)
        tooltip = TextPropertiesTooltip(widget, config)
        
        assert tooltip.config.style == TooltipStyle.DETAILED
    
    def test_enable_disable(self, qapp):
        """Habilitar/deshabilitar tooltip."""
        widget = QWidget()
        tooltip = TextPropertiesTooltip(widget)
        
        assert tooltip.enabled is True
        
        tooltip.enabled = False
        assert tooltip.enabled is False
        
        tooltip.enabled = True
        assert tooltip.enabled is True
    
    def test_set_style(self, qapp):
        """Cambiar estilo del tooltip."""
        widget = QWidget()
        tooltip = TextPropertiesTooltip(widget)
        
        tooltip.set_style(TooltipStyle.COMPACT)
        assert tooltip.config.style == TooltipStyle.COMPACT
        
        tooltip.set_style(TooltipStyle.DETAILED)
        assert tooltip.config.style == TooltipStyle.DETAILED
    
    def test_update_config(self, qapp):
        """Actualizar configuración individualmente."""
        widget = QWidget()
        tooltip = TextPropertiesTooltip(widget)
        
        tooltip.update_config(show_delay_ms=500, dark_theme=False)
        
        assert tooltip.config.show_delay_ms == 500
        assert tooltip.config.dark_theme is False
    
    def test_on_span_hovered_none(self, qapp):
        """Manejar hover con span None."""
        widget = QWidget()
        tooltip = TextPropertiesTooltip(widget)
        
        # No debería lanzar excepción
        tooltip.on_span_hovered(None)
    
    def test_on_span_hovered_disabled(self, qapp):
        """No hacer nada si tooltip está deshabilitado."""
        widget = QWidget()
        tooltip = TextPropertiesTooltip(widget)
        tooltip.enabled = False
        
        # Mock del timer
        tooltip._show_timer = Mock()
        tooltip._hide_timer = Mock()
        
        tooltip.on_span_hovered(Mock())
        
        # No debería iniciar timers
        tooltip._show_timer.start.assert_not_called()
    
    @pytest.mark.skipif(not TEXT_ENGINE_AVAILABLE, reason="text_engine no disponible")
    def test_on_span_hovered_with_span(self, qapp):
        """Manejar hover con span válido."""
        widget = QWidget()
        tooltip = TextPropertiesTooltip(widget)
        
        # Mock del timer
        tooltip._show_timer = Mock()
        tooltip._hide_timer = Mock()
        
        span = create_test_span()
        
        tooltip.on_span_hovered(span)
        
        # Debería iniciar timer de mostrar
        tooltip._show_timer.start.assert_called_with(tooltip.config.show_delay_ms)
    
    def test_hide(self, qapp):
        """Ocultar tooltip inmediatamente."""
        widget = QWidget()
        tooltip = TextPropertiesTooltip(widget)
        
        # Mock de timers
        tooltip._show_timer = Mock()
        tooltip._hide_timer = Mock()
        
        tooltip.hide()
        
        # Debería detener ambos timers
        tooltip._show_timer.stop.assert_called()
        tooltip._hide_timer.stop.assert_called()
    
    def test_timers_created(self, qapp):
        """Verificar que los timers se crean."""
        widget = QWidget()
        tooltip = TextPropertiesTooltip(widget)
        
        assert isinstance(tooltip._show_timer, QTimer)
        assert isinstance(tooltip._hide_timer, QTimer)
        assert tooltip._show_timer.isSingleShot()
        assert tooltip._hide_timer.isSingleShot()


# ===========================================================================
# Tests para create_text_properties_tooltip factory
# ===========================================================================

class TestCreateTextPropertiesTooltip:
    """Tests para la función de fábrica."""
    
    def test_creates_tooltip(self, qapp):
        """Crear tooltip con factory."""
        widget = QWidget()
        tooltip = create_text_properties_tooltip(widget)
        
        assert isinstance(tooltip, TextPropertiesTooltip)
    
    def test_respects_style_param(self, qapp):
        """Respetar parámetro de estilo."""
        widget = QWidget()
        tooltip = create_text_properties_tooltip(
            widget, 
            style=TooltipStyle.DETAILED
        )
        
        assert tooltip.config.style == TooltipStyle.DETAILED
    
    def test_respects_dark_theme_param(self, qapp):
        """Respetar parámetro de tema."""
        widget = QWidget()
        tooltip = create_text_properties_tooltip(
            widget, 
            dark_theme=False
        )
        
        assert tooltip.config.dark_theme is False


# ===========================================================================
# Tests de integración
# ===========================================================================

class TestIntegration:
    """Tests de integración."""
    
    @pytest.mark.skipif(not TEXT_ENGINE_AVAILABLE, reason="text_engine no disponible")
    def test_full_tooltip_workflow(self, qapp):
        """Flujo completo de tooltip."""
        widget = QWidget()
        tooltip = create_text_properties_tooltip(widget)
        
        # Crear span de prueba
        span = create_test_span(text="Test text")
        
        # Simular hover
        tooltip.on_span_hovered(span)
        
        # Verificar estado
        assert tooltip._current_span == span
        
        # Simular salir del span
        tooltip.on_span_hovered(None)
        
        # Verificar limpieza
        assert tooltip._current_span is None
    
    @pytest.mark.skipif(not TEXT_ENGINE_AVAILABLE, reason="text_engine no disponible")
    def test_tooltip_with_all_styles(self, qapp):
        """Verificar que todos los estilos producen output."""
        span = create_test_span(
            is_bold=True,
            is_italic=True,
            fill_color="#ff0000"
        )
        
        for style in TooltipStyle:
            config = TooltipConfig(style=style)
            result = format_span_tooltip(span, config)
            assert len(result) > 0, f"Estilo {style} no generó output"
    
    @pytest.mark.skipif(not TEXT_ENGINE_AVAILABLE, reason="text_engine no disponible")
    def test_span_with_special_characters(self, qapp):
        """Span con caracteres especiales."""
        span = create_test_span(text="Español: áéíóú ñ Ç € <>&\"")
        
        result = format_span_tooltip(span)
        
        # Verificar que caracteres especiales HTML están escapados
        assert "&lt;" in result
        assert "&gt;" in result
        assert "&amp;" in result
        # Pero los acentos deben mantenerse
        assert "Espa" in result


# ===========================================================================
# Tests de rendimiento
# ===========================================================================

class TestPerformance:
    """Tests de rendimiento."""
    
    @pytest.mark.skipif(not TEXT_ENGINE_AVAILABLE, reason="text_engine no disponible")
    def test_format_many_spans(self):
        """Formatear muchos spans rápidamente."""
        import time
        
        span = create_test_span(text="Test text content")
        
        config = TooltipConfig()
        
        start = time.time()
        for _ in range(1000):
            format_span_tooltip(span, config)
        elapsed = time.time() - start
        
        # Debe completar 1000 formatos en menos de 1 segundo
        assert elapsed < 1.0, f"Formateo tardó {elapsed:.2f}s para 1000 spans"


# ===========================================================================
# Tests de edge cases
# ===========================================================================

class TestEdgeCases:
    """Tests de casos extremos."""
    
    def test_empty_text_span(self):
        """Span con texto vacío."""
        if not TEXT_ENGINE_AVAILABLE:
            pytest.skip("text_engine no disponible")
        
        span = create_test_span(text="")
        
        result = format_span_tooltip(span)
        # Debe generar output aunque el texto esté vacío
        assert len(result) > 0
    
    def test_none_font_name(self):
        """Span con font_name None."""
        if not TEXT_ENGINE_AVAILABLE:
            pytest.skip("text_engine no disponible")
        
        span = create_test_span(font_name=None)
        
        result = format_span_tooltip(span)
        assert "Desconocida" in result
    
    def test_none_fill_color(self):
        """Span con fill_color None."""
        if not TEXT_ENGINE_AVAILABLE:
            pytest.skip("text_engine no disponible")
        
        span = create_test_span(fill_color=None)
        
        result = format_span_tooltip(span)
        # Debe usar color por defecto
        assert "#000000" in result
    
    def test_very_long_font_name(self):
        """Span con nombre de fuente muy largo."""
        if not TEXT_ENGINE_AVAILABLE:
            pytest.skip("text_engine no disponible")
        
        long_name = "A" * 200
        span = create_test_span(font_name=long_name)
        
        result = format_span_tooltip(span)
        # No debe truncar nombre de fuente (solo preview de texto)
        assert long_name in result
    
    def test_zero_font_size(self):
        """Span con tamaño de fuente cero."""
        if not TEXT_ENGINE_AVAILABLE:
            pytest.skip("text_engine no disponible")
        
        span = create_test_span(font_size=0)
        
        result = format_span_tooltip(span)
        # Debe generar output válido
        assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

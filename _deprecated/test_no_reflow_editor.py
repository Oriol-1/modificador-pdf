"""
Tests para NoReflowEditor - Editor con cajas fijas.

PHASE3-3C06: Tests para el modo "no reflow" con preservación de posición.
"""

import pytest

# Intentar importar PyQt5
pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import QApplication  # noqa: E402
from PyQt5.QtCore import QRectF  # noqa: E402

# Asegurar QApplication existe
@pytest.fixture(scope="session")
def qapp():
    """Crear QApplication para tests."""
    app = QApplication.instance() or QApplication([])
    yield app


# Importar módulo bajo test
from ui.no_reflow_editor import (  # noqa: E402
    # Enums
    OverflowStrategy,
    BboxDisplayMode,
    # Dataclasses
    BboxConstraints,
    AdjustmentResult,
    NoReflowConfig,
    # Widgets
    BboxOverlay,
    FitIndicatorWidget,
    TrackingAdjuster,
    SizeAdjuster,
    HorizontalScaleAdjuster,
    OverflowOptionsPanel,
    NoReflowEditorPanel,
    # Calculator
    TextFitCalculator,
    # Factory functions
    create_no_reflow_panel,
    calculate_best_fit,
)


# ================== Fixtures ==================


@pytest.fixture
def sample_span_data():
    """Datos de span de ejemplo."""
    return {
        'text': 'Texto de ejemplo',
        'font_name': 'Helvetica',
        'font_size': 12.0,
        'bbox': (100.0, 200.0, 250.0, 220.0),
        'char_spacing': 0.0,
    }


@pytest.fixture
def long_span_data():
    """Span con texto largo que desborda."""
    return {
        'text': 'Este es un texto muy largo que definitivamente no cabe en el bbox',
        'font_name': 'Helvetica',
        'font_size': 12.0,
        'bbox': (100.0, 200.0, 200.0, 220.0),  # Solo 100pt de ancho
        'char_spacing': 0.0,
    }


@pytest.fixture
def default_config():
    """Configuración por defecto."""
    return NoReflowConfig()


@pytest.fixture
def constraints_from_bbox():
    """Constraints desde un bbox."""
    return BboxConstraints.from_bbox((100.0, 200.0, 300.0, 220.0))


# ================== Tests: Enums ==================


class TestOverflowStrategy:
    """Tests para OverflowStrategy enum."""
    
    def test_none_strategy(self):
        """Estrategia NONE tiene valor correcto."""
        assert OverflowStrategy.NONE.value == "none"
    
    def test_truncate_strategy(self):
        """Estrategia TRUNCATE tiene valor correcto."""
        assert OverflowStrategy.TRUNCATE.value == "truncate"
    
    def test_reduce_tracking_strategy(self):
        """Estrategia REDUCE_TRACKING tiene valor correcto."""
        assert OverflowStrategy.REDUCE_TRACKING.value == "tracking"
    
    def test_reduce_size_strategy(self):
        """Estrategia REDUCE_SIZE tiene valor correcto."""
        assert OverflowStrategy.REDUCE_SIZE.value == "size"
    
    def test_scale_horizontal_strategy(self):
        """Estrategia SCALE_HORIZONTAL tiene valor correcto."""
        assert OverflowStrategy.SCALE_HORIZONTAL.value == "scale"
    
    def test_all_strategies_count(self):
        """Hay 5 estrategias disponibles."""
        assert len(list(OverflowStrategy)) == 5


class TestBboxDisplayMode:
    """Tests para BboxDisplayMode enum."""
    
    def test_hidden_mode(self):
        """Modo HIDDEN tiene valor correcto."""
        assert BboxDisplayMode.HIDDEN.value == "hidden"
    
    def test_outline_mode(self):
        """Modo OUTLINE tiene valor correcto."""
        assert BboxDisplayMode.OUTLINE.value == "outline"
    
    def test_filled_mode(self):
        """Modo FILLED tiene valor correcto."""
        assert BboxDisplayMode.FILLED.value == "filled"
    
    def test_guide_lines_mode(self):
        """Modo GUIDE_LINES tiene valor correcto."""
        assert BboxDisplayMode.GUIDE_LINES.value == "guide_lines"
    
    def test_all_modes_count(self):
        """Hay 4 modos de visualización."""
        assert len(list(BboxDisplayMode)) == 4


# ================== Tests: BboxConstraints ==================


class TestBboxConstraints:
    """Tests para BboxConstraints dataclass."""
    
    def test_default_values(self):
        """Valores por defecto correctos."""
        c = BboxConstraints()
        assert c.x == 0.0
        assert c.y == 0.0
        assert c.width == 100.0
        assert c.height == 20.0
    
    def test_inner_width_no_padding(self):
        """Ancho interno sin padding es igual al ancho."""
        c = BboxConstraints(width=150.0)
        assert c.inner_width == 150.0
    
    def test_inner_width_with_padding(self):
        """Ancho interno con padding se reduce."""
        c = BboxConstraints(width=150.0, padding_left=10.0, padding_right=10.0)
        assert c.inner_width == 130.0
    
    def test_inner_height(self):
        """Alto interno con padding se reduce."""
        c = BboxConstraints(height=30.0, padding_top=5.0, padding_bottom=5.0)
        assert c.inner_height == 20.0
    
    def test_rect_property(self):
        """Propiedad rect retorna QRectF correcto."""
        c = BboxConstraints(x=10.0, y=20.0, width=100.0, height=50.0)
        rect = c.rect
        assert isinstance(rect, QRectF)
        assert rect.x() == 10.0
        assert rect.y() == 20.0
        assert rect.width() == 100.0
        assert rect.height() == 50.0
    
    def test_inner_rect_property(self):
        """Propiedad inner_rect considera padding."""
        c = BboxConstraints(
            x=10.0, y=20.0, width=100.0, height=50.0,
            padding_left=5.0, padding_top=3.0
        )
        inner = c.inner_rect
        assert inner.x() == 15.0  # x + padding_left
        assert inner.y() == 23.0  # y + padding_top
    
    def test_from_bbox_tuple(self):
        """Crear desde tuple bbox (x0, y0, x1, y1)."""
        c = BboxConstraints.from_bbox((100.0, 200.0, 300.0, 250.0))
        assert c.x == 100.0
        assert c.y == 200.0
        assert c.width == 200.0  # x1 - x0
        assert c.height == 50.0  # y1 - y0


# ================== Tests: AdjustmentResult ==================


class TestAdjustmentResult:
    """Tests para AdjustmentResult dataclass."""
    
    def test_creation(self):
        """Crear AdjustmentResult básico."""
        result = AdjustmentResult(
            strategy=OverflowStrategy.TRUNCATE,
            original_text="Texto largo",
            adjusted_text="Texto...",
            fits=True
        )
        assert result.strategy == OverflowStrategy.TRUNCATE
        assert result.fits is True
    
    def test_overflow_amount_positive(self):
        """overflow_amount positivo indica desbordamiento."""
        result = AdjustmentResult(
            strategy=OverflowStrategy.NONE,
            original_text="Texto",
            adjusted_text="Texto",
            fits=False,
            adjusted_width=150.0,
            available_width=100.0
        )
        assert result.overflow_amount == 50.0
    
    def test_overflow_amount_negative(self):
        """overflow_amount negativo indica que cabe."""
        result = AdjustmentResult(
            strategy=OverflowStrategy.NONE,
            original_text="Texto",
            adjusted_text="Texto",
            fits=True,
            adjusted_width=80.0,
            available_width=100.0
        )
        assert result.overflow_amount == -20.0
    
    def test_fit_percentage(self):
        """Porcentaje de uso del espacio."""
        result = AdjustmentResult(
            strategy=OverflowStrategy.NONE,
            original_text="Texto",
            adjusted_text="Texto",
            fits=True,
            adjusted_width=75.0,
            available_width=100.0
        )
        assert result.fit_percentage == 75.0
    
    def test_fit_percentage_overflow(self):
        """Porcentaje mayor a 100% indica overflow."""
        result = AdjustmentResult(
            strategy=OverflowStrategy.NONE,
            original_text="Texto",
            adjusted_text="Texto",
            fits=False,
            adjusted_width=120.0,
            available_width=100.0
        )
        assert result.fit_percentage == 120.0
    
    def test_fit_percentage_zero_available(self):
        """Porcentaje es 0 si available_width es 0."""
        result = AdjustmentResult(
            strategy=OverflowStrategy.NONE,
            original_text="Texto",
            adjusted_text="Texto",
            fits=False,
            available_width=0.0
        )
        assert result.fit_percentage == 0.0


# ================== Tests: NoReflowConfig ==================


class TestNoReflowConfig:
    """Tests para NoReflowConfig dataclass."""
    
    def test_default_values(self):
        """Valores por defecto correctos."""
        config = NoReflowConfig()
        assert config.default_strategy == OverflowStrategy.NONE
        assert config.bbox_display == BboxDisplayMode.OUTLINE
        assert config.show_overflow_warning is True
        assert config.allow_overflow is False
    
    def test_tracking_limits(self):
        """Límites de tracking por defecto."""
        config = NoReflowConfig()
        assert config.min_tracking == -2.0
        assert config.max_tracking == 5.0
    
    def test_size_factor_limits(self):
        """Límites de factor de tamaño por defecto."""
        config = NoReflowConfig()
        assert config.min_size_factor == 0.7
        assert config.max_size_factor == 1.2
    
    def test_scale_limits(self):
        """Límites de escala horizontal por defecto."""
        config = NoReflowConfig()
        assert config.min_scale == 0.8
        assert config.max_scale == 1.2
    
    def test_custom_colors(self):
        """Colores personalizados."""
        config = NoReflowConfig(
            bbox_color="#ff0000",
            overflow_color="#00ff00"
        )
        assert config.bbox_color == "#ff0000"
        assert config.overflow_color == "#00ff00"


# ================== Tests: TextFitCalculator ==================


class TestTextFitCalculator:
    """Tests para TextFitCalculator."""
    
    def test_calculate_text_width_basic(self, qapp):
        """Calcular ancho básico de texto."""
        width = TextFitCalculator.calculate_text_width(
            "Test", "Helvetica", 12.0
        )
        assert width > 0
    
    def test_longer_text_wider(self, qapp):
        """Texto más largo tiene mayor ancho."""
        short = TextFitCalculator.calculate_text_width("Hi", "Helvetica", 12.0)
        long = TextFitCalculator.calculate_text_width("Hello World", "Helvetica", 12.0)
        assert long > short
    
    def test_larger_font_wider(self, qapp):
        """Fuente más grande produce mayor ancho."""
        small = TextFitCalculator.calculate_text_width("Test", "Helvetica", 10.0)
        large = TextFitCalculator.calculate_text_width("Test", "Helvetica", 20.0)
        assert large > small
    
    def test_positive_tracking_wider(self, qapp):
        """Tracking positivo aumenta el ancho."""
        normal = TextFitCalculator.calculate_text_width(
            "Test Text", "Helvetica", 12.0, char_spacing=0.0
        )
        spaced = TextFitCalculator.calculate_text_width(
            "Test Text", "Helvetica", 12.0, char_spacing=2.0
        )
        assert spaced > normal
    
    def test_negative_tracking_narrower(self, qapp):
        """Tracking negativo reduce el ancho."""
        normal = TextFitCalculator.calculate_text_width(
            "Test Text", "Helvetica", 12.0, char_spacing=0.0
        )
        tight = TextFitCalculator.calculate_text_width(
            "Test Text", "Helvetica", 12.0, char_spacing=-1.0
        )
        assert tight < normal
    
    def test_scale_affects_width(self, qapp):
        """Escala horizontal afecta el ancho."""
        normal = TextFitCalculator.calculate_text_width(
            "Test", "Helvetica", 12.0, scale_x=1.0
        )
        scaled = TextFitCalculator.calculate_text_width(
            "Test", "Helvetica", 12.0, scale_x=0.8
        )
        assert scaled < normal
    
    def test_fit_by_truncation_fits(self, qapp):
        """Truncamiento cuando ya cabe."""
        result = TextFitCalculator.fit_by_truncation(
            "Hi", "Helvetica", 12.0, 100.0
        )
        assert result.fits is True
        assert result.adjusted_text == "Hi"
        assert result.truncated_chars == 0
    
    def test_fit_by_truncation_overflow(self, qapp):
        """Truncamiento cuando no cabe."""
        result = TextFitCalculator.fit_by_truncation(
            "Este es un texto muy largo", "Helvetica", 12.0, 50.0
        )
        assert result.adjusted_text.endswith("...")
        assert result.truncated_chars > 0
    
    def test_fit_by_tracking_fits(self, qapp):
        """Ajuste de tracking cuando ya cabe."""
        result = TextFitCalculator.fit_by_tracking(
            "Hi", "Helvetica", 12.0, 100.0
        )
        assert result.fits is True
        assert result.char_spacing_delta == 0.0
    
    def test_fit_by_tracking_overflow(self, qapp):
        """Ajuste de tracking cuando no cabe."""
        result = TextFitCalculator.fit_by_tracking(
            "Este es un texto largo", "Helvetica", 12.0, 80.0,
            min_tracking=-2.0
        )
        # Debe intentar reducir tracking
        assert result.char_spacing_delta <= 0
    
    def test_fit_by_size_fits(self, qapp):
        """Ajuste de tamaño cuando ya cabe."""
        result = TextFitCalculator.fit_by_size(
            "Hi", "Helvetica", 12.0, 100.0
        )
        assert result.fits is True
        assert result.font_size_delta == 0.0
    
    def test_fit_by_size_overflow(self, qapp):
        """Ajuste de tamaño cuando no cabe."""
        result = TextFitCalculator.fit_by_size(
            "Texto largo", "Helvetica", 12.0, 30.0,
            min_factor=0.5
        )
        # Debe reducir tamaño
        assert result.font_size_delta < 0
    
    def test_fit_by_scale_fits(self, qapp):
        """Ajuste de escala cuando ya cabe."""
        result = TextFitCalculator.fit_by_scale(
            "Hi", "Helvetica", 12.0, 100.0
        )
        assert result.fits is True
        assert result.scale_factor == 1.0
    
    def test_fit_by_scale_overflow(self, qapp):
        """Ajuste de escala cuando no cabe."""
        result = TextFitCalculator.fit_by_scale(
            "Texto largo", "Helvetica", 12.0, 40.0,
            min_scale=0.5
        )
        # Debe reducir escala
        assert result.scale_factor < 1.0


# ================== Tests: BboxOverlay ==================


class TestBboxOverlay:
    """Tests para BboxOverlay widget."""
    
    def test_creation(self, qapp):
        """Crear BboxOverlay básico."""
        overlay = BboxOverlay()
        assert overlay is not None
    
    def test_creation_with_constraints(self, qapp, constraints_from_bbox):
        """Crear con constraints."""
        overlay = BboxOverlay(constraints=constraints_from_bbox)
        assert overlay._constraints == constraints_from_bbox
    
    def test_set_constraints(self, qapp):
        """Cambiar constraints."""
        overlay = BboxOverlay()
        new_constraints = BboxConstraints(x=50.0, y=50.0, width=200.0)
        overlay.set_constraints(new_constraints)
        assert overlay._constraints.x == 50.0
    
    def test_set_overflow(self, qapp):
        """Establecer estado de overflow."""
        overlay = BboxOverlay()
        overlay.set_overflow(True, 150.0)
        assert overlay._is_overflow is True
        assert overlay._current_width == 150.0
    
    def test_set_display_mode(self, qapp):
        """Cambiar modo de visualización."""
        overlay = BboxOverlay()
        overlay.set_display_mode(BboxDisplayMode.FILLED)
        assert overlay._config.bbox_display == BboxDisplayMode.FILLED


# ================== Tests: FitIndicatorWidget ==================


class TestFitIndicatorWidget:
    """Tests para FitIndicatorWidget."""
    
    def test_creation(self, qapp):
        """Crear FitIndicatorWidget."""
        widget = FitIndicatorWidget()
        assert widget is not None
        assert widget.minimumHeight() == 24
    
    def test_set_percentage_fits(self, qapp):
        """Establecer porcentaje que cabe."""
        widget = FitIndicatorWidget()
        widget.set_percentage(75.0, True)
        assert widget._percentage == 75.0
        assert widget._fits is True
    
    def test_set_percentage_tight(self, qapp):
        """Establecer porcentaje ajustado."""
        widget = FitIndicatorWidget()
        widget.set_percentage(98.0, True)
        assert widget._percentage == 98.0
    
    def test_set_percentage_overflow(self, qapp):
        """Establecer porcentaje de overflow."""
        widget = FitIndicatorWidget()
        widget.set_percentage(120.0, False)
        assert widget._percentage == 120.0
        assert widget._fits is False


# ================== Tests: TrackingAdjuster ==================


class TestTrackingAdjuster:
    """Tests para TrackingAdjuster."""
    
    def test_creation(self, qapp):
        """Crear TrackingAdjuster."""
        adjuster = TrackingAdjuster()
        assert adjuster is not None
    
    def test_default_value(self, qapp):
        """Valor por defecto es 0."""
        adjuster = TrackingAdjuster()
        assert adjuster.get_value() == 0.0
    
    def test_set_value(self, qapp):
        """Establecer valor."""
        adjuster = TrackingAdjuster()
        adjuster.set_value(1.5)
        assert adjuster.get_value() == 1.5
    
    def test_reset(self, qapp):
        """Reset vuelve a 0."""
        adjuster = TrackingAdjuster()
        adjuster.set_value(2.0)
        adjuster.reset()
        assert adjuster.get_value() == 0.0
    
    def test_signal_emitted(self, qapp):
        """Señal se emite al cambiar valor."""
        adjuster = TrackingAdjuster()
        received = []
        adjuster.trackingChanged.connect(lambda v: received.append(v))
        adjuster.set_value(1.0)
        assert len(received) >= 1


# ================== Tests: SizeAdjuster ==================


class TestSizeAdjuster:
    """Tests para SizeAdjuster."""
    
    def test_creation(self, qapp):
        """Crear SizeAdjuster."""
        adjuster = SizeAdjuster()
        assert adjuster is not None
    
    def test_default_factor(self, qapp):
        """Factor por defecto es 1.0."""
        adjuster = SizeAdjuster(base_size=12.0)
        assert adjuster.get_factor() == 1.0
    
    def test_default_size(self, qapp):
        """Tamaño resultante igual al base."""
        adjuster = SizeAdjuster(base_size=12.0)
        assert adjuster.get_size() == 12.0
    
    def test_set_base_size(self, qapp):
        """Cambiar tamaño base."""
        adjuster = SizeAdjuster(base_size=10.0)
        adjuster.set_base_size(14.0)
        assert adjuster._base_size == 14.0
    
    def test_reset(self, qapp):
        """Reset vuelve a 100%."""
        adjuster = SizeAdjuster(base_size=12.0)
        adjuster._slider.setValue(80)  # 80%
        adjuster.reset()
        assert adjuster.get_factor() == 1.0


# ================== Tests: HorizontalScaleAdjuster ==================


class TestHorizontalScaleAdjuster:
    """Tests para HorizontalScaleAdjuster."""
    
    def test_creation(self, qapp):
        """Crear HorizontalScaleAdjuster."""
        adjuster = HorizontalScaleAdjuster()
        assert adjuster is not None
    
    def test_default_scale(self, qapp):
        """Escala por defecto es 1.0."""
        adjuster = HorizontalScaleAdjuster()
        assert adjuster.get_scale() == 1.0
    
    def test_reset(self, qapp):
        """Reset vuelve a 100%."""
        adjuster = HorizontalScaleAdjuster()
        adjuster._slider.setValue(90)
        adjuster.reset()
        assert adjuster.get_scale() == 1.0


# ================== Tests: OverflowOptionsPanel ==================


class TestOverflowOptionsPanel:
    """Tests para OverflowOptionsPanel."""
    
    def test_creation(self, qapp):
        """Crear OverflowOptionsPanel."""
        panel = OverflowOptionsPanel()
        assert panel is not None
    
    def test_default_strategy(self, qapp):
        """Estrategia por defecto es NONE."""
        panel = OverflowOptionsPanel()
        assert panel.get_selected_strategy() == OverflowStrategy.NONE
    
    def test_set_strategy(self, qapp):
        """Establecer estrategia."""
        panel = OverflowOptionsPanel()
        panel.set_strategy(OverflowStrategy.TRUNCATE)
        assert panel.get_selected_strategy() == OverflowStrategy.TRUNCATE
    
    def test_all_strategies_available(self, qapp):
        """Todas las estrategias están como opciones."""
        panel = OverflowOptionsPanel()
        buttons = panel._button_group.buttons()
        strategies = [b.property("strategy") for b in buttons]
        
        assert OverflowStrategy.NONE in strategies
        assert OverflowStrategy.TRUNCATE in strategies
        assert OverflowStrategy.REDUCE_TRACKING in strategies
        assert OverflowStrategy.REDUCE_SIZE in strategies
        assert OverflowStrategy.SCALE_HORIZONTAL in strategies


# ================== Tests: NoReflowEditorPanel ==================


class TestNoReflowEditorPanel:
    """Tests para NoReflowEditorPanel."""
    
    def test_creation(self, qapp):
        """Crear NoReflowEditorPanel."""
        panel = NoReflowEditorPanel()
        assert panel is not None
    
    def test_creation_with_config(self, qapp, default_config):
        """Crear con configuración."""
        panel = NoReflowEditorPanel(config=default_config)
        assert panel._config == default_config
    
    def test_set_span_data(self, qapp, sample_span_data):
        """Establecer datos de span."""
        panel = NoReflowEditorPanel()
        panel.set_span_data(sample_span_data)
        
        assert panel._current_text == sample_span_data['text']
        assert panel._text_display.text() == sample_span_data['text']
    
    def test_set_text(self, qapp, sample_span_data):
        """Actualizar texto."""
        panel = NoReflowEditorPanel()
        panel.set_span_data(sample_span_data)
        panel.set_text("Nuevo texto")
        
        assert panel._current_text == "Nuevo texto"
    
    def test_set_constraints(self, qapp, constraints_from_bbox):
        """Establecer constraints."""
        panel = NoReflowEditorPanel()
        panel.set_constraints(constraints_from_bbox)
        
        assert panel._constraints == constraints_from_bbox
    
    def test_get_current_adjustments(self, qapp):
        """Obtener ajustes actuales."""
        panel = NoReflowEditorPanel()
        adjustments = panel.get_current_adjustments()
        
        assert 'tracking' in adjustments
        assert 'size_factor' in adjustments
        assert 'scale' in adjustments
    
    def test_adjustments_default_values(self, qapp):
        """Ajustes por defecto son neutros."""
        panel = NoReflowEditorPanel()
        adjustments = panel.get_current_adjustments()
        
        assert adjustments['tracking'] == 0.0
        assert adjustments['size_factor'] == 1.0
        assert adjustments['scale'] == 1.0


# ================== Tests: Factory Functions ==================


class TestFactoryFunctions:
    """Tests para funciones factory."""
    
    def test_create_no_reflow_panel_default(self, qapp):
        """Crear panel sin argumentos."""
        panel = create_no_reflow_panel()
        assert panel is not None
        assert isinstance(panel, NoReflowEditorPanel)
    
    def test_create_no_reflow_panel_with_span(self, qapp, sample_span_data):
        """Crear panel con datos de span."""
        panel = create_no_reflow_panel(span_data=sample_span_data)
        assert panel._current_text == sample_span_data['text']
    
    def test_create_no_reflow_panel_with_config(self, qapp, default_config):
        """Crear panel con configuración."""
        panel = create_no_reflow_panel(config=default_config)
        assert panel._config == default_config
    
    def test_calculate_best_fit_already_fits(self, qapp):
        """calculate_best_fit cuando ya cabe."""
        result = calculate_best_fit(
            "Hi", "Helvetica", 12.0, 100.0
        )
        assert result.fits is True
        assert result.strategy == OverflowStrategy.NONE
    
    def test_calculate_best_fit_needs_adjustment(self, qapp):
        """calculate_best_fit cuando necesita ajuste."""
        result = calculate_best_fit(
            "Este es un texto bastante largo para probar",
            "Helvetica", 12.0, 100.0
        )
        # Debe retornar algún ajuste que funcione (o truncate como último recurso)
        assert result.strategy != OverflowStrategy.NONE


# ================== Tests: Edge Cases ==================


class TestEdgeCases:
    """Tests para casos límite."""
    
    def test_empty_text(self, qapp):
        """Texto vacío."""
        width = TextFitCalculator.calculate_text_width("", "Helvetica", 12.0)
        assert width == 0.0
    
    def test_single_char(self, qapp):
        """Un solo carácter."""
        result = TextFitCalculator.fit_by_tracking(
            "X", "Helvetica", 12.0, 50.0
        )
        # No puede ajustar tracking con un solo char
        assert result.char_spacing_delta == 0.0
    
    def test_special_characters(self, qapp):
        """Caracteres especiales."""
        width = TextFitCalculator.calculate_text_width(
            "¡Hola! ¿Qué tal? €100", "Helvetica", 12.0
        )
        assert width > 0
    
    def test_zero_available_width(self, qapp):
        """Ancho disponible cero."""
        result = TextFitCalculator.fit_by_truncation(
            "Texto", "Helvetica", 12.0, 0.0
        )
        # Debe truncar todo
        assert result.adjusted_text == "..."
    
    def test_negative_tracking_limit(self, qapp):
        """Límite de tracking negativo."""
        result = TextFitCalculator.fit_by_tracking(
            "Texto muy largo", "Helvetica", 12.0, 10.0,
            min_tracking=-5.0
        )
        # No debe exceder el límite
        assert result.char_spacing_delta >= -5.0
    
    def test_very_small_min_factor(self, qapp):
        """Factor mínimo muy pequeño."""
        result = TextFitCalculator.fit_by_size(
            "Texto", "Helvetica", 12.0, 5.0,
            min_factor=0.1
        )
        # Debe respetar el límite
        assert result.font_size_delta is not None


# ================== Tests: Integration ==================


class TestIntegration:
    """Tests de integración."""
    
    def test_panel_with_long_text(self, qapp, long_span_data):
        """Panel con texto que desborda."""
        panel = NoReflowEditorPanel()
        panel.set_span_data(long_span_data)
        
        # Debe mostrar overflow
        assert panel._current_text == long_span_data['text']
    
    def test_adjustment_workflow(self, qapp, sample_span_data):
        """Flujo de trabajo de ajuste completo."""
        panel = NoReflowEditorPanel()
        panel.set_span_data(sample_span_data)
        
        # Cambiar tracking
        panel._tracking_adjuster.set_value(-0.5)
        adjustments = panel.get_current_adjustments()
        assert adjustments['tracking'] == -0.5
        
        # Cambiar tamaño
        panel._size_adjuster._slider.setValue(90)  # 90%
        adjustments = panel.get_current_adjustments()
        assert adjustments['size_factor'] == 0.9
    
    def test_signal_on_apply(self, qapp, sample_span_data):
        """Señal se emite al aplicar ajuste."""
        panel = NoReflowEditorPanel()
        panel.set_span_data(sample_span_data)
        
        received = []
        panel.adjustmentApplied.connect(lambda r: received.append(r))
        
        # Seleccionar estrategia y aplicar
        panel._overflow_options.set_strategy(OverflowStrategy.TRUNCATE)
        panel._on_apply_adjustment()
        
        assert len(received) == 1
        assert isinstance(received[0], AdjustmentResult)

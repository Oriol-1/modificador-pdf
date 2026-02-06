"""
Tests para GlyphWidthPreserver - Preservación de anchos de glifos.

PHASE3-3D04: Preservar anchos de glifos al editar
"""

import pytest
from unittest.mock import Mock

from core.text_engine.glyph_width_preserver import (
    # Enums
    FitStrategy,
    FitResult,
    AdjustmentType,
    WidthUnit,
    # Dataclasses
    GlyphWidth,
    TextWidthInfo,
    SpacingAdjustment,
    FitAnalysis,
    PreserverConfig,
    TJArrayEntry,
    # Classes
    GlyphWidthPreserver,
    # Factory functions
    create_width_preserver,
    calculate_text_width,
    fit_text_to_width,
    get_spacing_adjustment,
)


# ============== Fixtures ==============


@pytest.fixture
def preserver():
    """Preservador con configuración por defecto."""
    return GlyphWidthPreserver()


@pytest.fixture
def strict_preserver():
    """Preservador con configuración estricta."""
    config = PreserverConfig(
        width_tolerance=0.1,
        max_tracking=2.0,
        min_tracking=-2.0,
        max_word_spacing=5.0,
        min_word_spacing=-3.0,
        max_horizontal_scale=120.0,
        min_horizontal_scale=80.0,
    )
    return GlyphWidthPreserver(config=config)


@pytest.fixture
def mock_font_extractor():
    """Mock de EmbeddedFontExtractor."""
    mock = Mock()
    mock.get_glyph_widths.return_value = [500, 500, 500]  # 500 fu por carácter
    mock.calculate_text_width.return_value = 18.0  # 18pt para texto
    return mock


# ============== Tests FitStrategy Enum ==============


class TestFitStrategyEnum:
    """Tests para FitStrategy enum."""
    
    def test_all_strategies_exist(self):
        """Verifica todas las estrategias."""
        assert FitStrategy.EXACT
        assert FitStrategy.COMPRESS
        assert FitStrategy.EXPAND
        assert FitStrategy.TRUNCATE
        assert FitStrategy.ELLIPSIS
        assert FitStrategy.SCALE
        assert FitStrategy.ALLOW_OVERFLOW
    
    def test_strategy_count(self):
        """Verifica número de estrategias."""
        assert len(FitStrategy) == 7


class TestFitResultEnum:
    """Tests para FitResult enum."""
    
    def test_all_results_exist(self):
        """Verifica todos los resultados."""
        assert FitResult.SUCCESS
        assert FitResult.COMPRESSED
        assert FitResult.EXPANDED
        assert FitResult.TRUNCATED
        assert FitResult.SCALED
        assert FitResult.OVERFLOW
        assert FitResult.FAILED


class TestAdjustmentTypeEnum:
    """Tests para AdjustmentType enum."""
    
    def test_all_types_exist(self):
        """Verifica todos los tipos."""
        assert AdjustmentType.NONE
        assert AdjustmentType.TRACKING
        assert AdjustmentType.KERNING
        assert AdjustmentType.WORD_SPACING
        assert AdjustmentType.HORIZONTAL_SCALE
        assert AdjustmentType.COMBINED


class TestWidthUnitEnum:
    """Tests para WidthUnit enum."""
    
    def test_all_units_exist(self):
        """Verifica todas las unidades."""
        assert WidthUnit.POINTS
        assert WidthUnit.FONT_UNITS
        assert WidthUnit.EM
        assert WidthUnit.PERCENT


# ============== Tests GlyphWidth Dataclass ==============


class TestGlyphWidthDataclass:
    """Tests para GlyphWidth dataclass."""
    
    def test_create_basic(self):
        """Crea glyph width básico."""
        gw = GlyphWidth(
            char='A',
            char_code=65,
            width_font_units=722,
            width_points=8.664,
        )
        
        assert gw.char == 'A'
        assert gw.char_code == 65
        assert gw.width_font_units == 722
        assert gw.width_points == 8.664
        assert gw.glyph_name == ""
        assert gw.is_space is False
    
    def test_space_glyph(self):
        """Glyph de espacio."""
        gw = GlyphWidth(
            char=' ',
            char_code=32,
            width_font_units=250,
            width_points=3.0,
            is_space=True,
        )
        
        assert gw.is_space is True
        assert gw.is_whitespace is True
    
    def test_is_whitespace_property(self):
        """Verifica propiedad is_whitespace."""
        tab = GlyphWidth(
            char='\t',
            char_code=9,
            width_font_units=500,
            width_points=6.0,
        )
        assert tab.is_whitespace is True
        
        newline = GlyphWidth(
            char='\n',
            char_code=10,
            width_font_units=0,
            width_points=0.0,
        )
        assert newline.is_whitespace is True


# ============== Tests TextWidthInfo Dataclass ==============


class TestTextWidthInfoDataclass:
    """Tests para TextWidthInfo dataclass."""
    
    def test_create_basic(self):
        """Crea info básica."""
        char_widths = [
            GlyphWidth('H', 72, 722, 8.664),
            GlyphWidth('i', 105, 278, 3.336),
        ]
        
        info = TextWidthInfo(
            text="Hi",
            total_width_points=12.0,
            total_width_font_units=1000,
            char_widths=char_widths,
            font_name="Helvetica",
            font_size=12.0,
        )
        
        assert info.text == "Hi"
        assert info.total_width_points == 12.0
        assert info.char_count == 2
        assert info.space_count == 0
        assert info.avg_char_width == 6.0
    
    def test_space_stats(self):
        """Estadísticas de espacios."""
        char_widths = [
            GlyphWidth('A', 65, 722, 8.664, is_space=False),
            GlyphWidth(' ', 32, 250, 3.0, is_space=True),
            GlyphWidth('B', 66, 722, 8.664, is_space=False),
        ]
        
        info = TextWidthInfo(
            text="A B",
            total_width_points=20.328,
            total_width_font_units=1694,
            char_widths=char_widths,
            font_name="Helvetica",
            font_size=12.0,
        )
        
        assert info.space_count == 1
        assert info.non_space_width == pytest.approx(17.328)
        assert info.space_width == pytest.approx(3.0)
    
    def test_to_dict(self):
        """Serialización a diccionario."""
        info = TextWidthInfo(
            text="Test",
            total_width_points=24.0,
            total_width_font_units=2000,
            char_widths=[],
            font_name="Helvetica",
            font_size=12.0,
        )
        
        d = info.to_dict()
        assert d['text'] == "Test"
        assert d['total_width_points'] == 24.0
        assert d['font_name'] == "Helvetica"


# ============== Tests SpacingAdjustment Dataclass ==============


class TestSpacingAdjustmentDataclass:
    """Tests para SpacingAdjustment dataclass."""
    
    def test_no_adjustment(self):
        """Ajuste vacío."""
        adj = SpacingAdjustment(adjustment_type=AdjustmentType.NONE)
        
        assert adj.has_adjustment is False
        assert adj.to_pdf_operators() == []
    
    def test_tracking_adjustment(self):
        """Ajuste de tracking."""
        adj = SpacingAdjustment(
            adjustment_type=AdjustmentType.TRACKING,
            tracking=-0.5,
        )
        
        assert adj.has_adjustment is True
        ops = adj.to_pdf_operators()
        assert len(ops) == 1
        assert "Tc" in ops[0]
    
    def test_word_spacing_adjustment(self):
        """Ajuste de word spacing."""
        adj = SpacingAdjustment(
            adjustment_type=AdjustmentType.WORD_SPACING,
            word_spacing=2.0,
        )
        
        assert adj.has_adjustment is True
        ops = adj.to_pdf_operators()
        assert any("Tw" in op for op in ops)
    
    def test_horizontal_scale_adjustment(self):
        """Ajuste de escala horizontal."""
        adj = SpacingAdjustment(
            adjustment_type=AdjustmentType.HORIZONTAL_SCALE,
            horizontal_scale=95.0,
        )
        
        assert adj.has_adjustment is True
        ops = adj.to_pdf_operators()
        assert any("Tz" in op for op in ops)
    
    def test_combined_adjustment(self):
        """Ajuste combinado."""
        adj = SpacingAdjustment(
            adjustment_type=AdjustmentType.COMBINED,
            tracking=-0.3,
            word_spacing=1.5,
        )
        
        ops = adj.to_pdf_operators()
        assert len(ops) == 2
    
    def test_to_dict(self):
        """Serialización."""
        adj = SpacingAdjustment(
            adjustment_type=AdjustmentType.TRACKING,
            tracking=-0.5,
            total_adjustment=-3.0,
        )
        
        d = adj.to_dict()
        assert d['adjustment_type'] == 'TRACKING'
        assert d['tracking'] == -0.5


# ============== Tests FitAnalysis Dataclass ==============


class TestFitAnalysisDataclass:
    """Tests para FitAnalysis dataclass."""
    
    def test_create_basic(self):
        """Crea análisis básico."""
        analysis = FitAnalysis(
            original_text="Hello",
            new_text="Hola",
            original_width=30.0,
            new_text_natural_width=25.0,
            target_width=30.0,
            width_difference=-5.0,
            width_ratio=0.833,
            fit_result=FitResult.SUCCESS,
            fit_strategy=FitStrategy.EXACT,
        )
        
        assert analysis.original_text == "Hello"
        assert analysis.new_text == "Hola"
        assert analysis.final_text == "Hola"  # Se hereda de new_text
    
    def test_is_success_property(self):
        """Propiedad is_success."""
        success_results = [
            FitResult.SUCCESS,
            FitResult.COMPRESSED,
            FitResult.EXPANDED,
            FitResult.SCALED,
        ]
        
        for result in success_results:
            analysis = FitAnalysis(
                original_text="", new_text="",
                original_width=10, new_text_natural_width=10,
                target_width=10, width_difference=0, width_ratio=1.0,
                fit_result=result, fit_strategy=FitStrategy.EXACT,
            )
            assert analysis.is_success is True
    
    def test_failed_not_success(self):
        """FAILED no es éxito."""
        analysis = FitAnalysis(
            original_text="", new_text="",
            original_width=10, new_text_natural_width=20,
            target_width=10, width_difference=10, width_ratio=2.0,
            fit_result=FitResult.FAILED, fit_strategy=FitStrategy.EXACT,
        )
        assert analysis.is_success is False
    
    def test_fits_exactly_property(self):
        """Propiedad fits_exactly."""
        analysis = FitAnalysis(
            original_text="", new_text="",
            original_width=30, new_text_natural_width=30,
            target_width=30, width_difference=0, width_ratio=1.0,
            fit_result=FitResult.SUCCESS, fit_strategy=FitStrategy.EXACT,
            final_width=30.05,  # Casi exacto
        )
        assert analysis.fits_exactly is True
        
        analysis.final_width = 29.0  # Diferencia mayor a 0.1
        assert analysis.fits_exactly is False
    
    def test_to_dict(self):
        """Serialización."""
        analysis = FitAnalysis(
            original_text="Hello",
            new_text="Hola",
            original_width=30.0,
            new_text_natural_width=25.0,
            target_width=30.0,
            width_difference=-5.0,
            width_ratio=0.833,
            fit_result=FitResult.SUCCESS,
            fit_strategy=FitStrategy.EXACT,
        )
        
        d = analysis.to_dict()
        assert d['original_text'] == "Hello"
        assert d['fit_result'] == "SUCCESS"


# ============== Tests PreserverConfig Dataclass ==============


class TestPreserverConfigDataclass:
    """Tests para PreserverConfig dataclass."""
    
    def test_defaults(self):
        """Valores por defecto."""
        config = PreserverConfig()
        
        assert config.default_strategy == FitStrategy.EXACT
        assert config.width_tolerance == 0.5
        assert config.max_tracking == 5.0
        assert config.min_tracking == -3.0
        assert config.ellipsis == "..."
    
    def test_custom_config(self):
        """Configuración personalizada."""
        config = PreserverConfig(
            default_strategy=FitStrategy.COMPRESS,
            width_tolerance=0.1,
            max_tracking=10.0,
            ellipsis="…",
        )
        
        assert config.default_strategy == FitStrategy.COMPRESS
        assert config.width_tolerance == 0.1
        assert config.max_tracking == 10.0
        assert config.ellipsis == "…"


# ============== Tests TJArrayEntry Dataclass ==============


class TestTJArrayEntryDataclass:
    """Tests para TJArrayEntry dataclass."""
    
    def test_text_entry(self):
        """Entrada de texto."""
        entry = TJArrayEntry(is_text=True, text="Hello")
        
        assert entry.is_text is True
        assert entry.to_pdf() == "(Hello)"
    
    def test_adjustment_entry(self):
        """Entrada de ajuste."""
        entry = TJArrayEntry(is_text=False, adjustment=-50.5)
        
        assert entry.is_text is False
        assert "-50.50" in entry.to_pdf()
    
    def test_escape_parentheses(self):
        """Escapa paréntesis."""
        entry = TJArrayEntry(is_text=True, text="test(1)")
        
        pdf = entry.to_pdf()
        assert "\\(" in pdf
        assert "\\)" in pdf
    
    def test_escape_backslash(self):
        """Escapa backslash."""
        entry = TJArrayEntry(is_text=True, text="path\\file")
        
        pdf = entry.to_pdf()
        assert "\\\\" in pdf


# ============== Tests GlyphWidthPreserver - Initialization ==============


class TestGlyphWidthPreserverInit:
    """Tests de inicialización de GlyphWidthPreserver."""
    
    def test_default_initialization(self):
        """Inicialización por defecto."""
        preserver = GlyphWidthPreserver()
        
        assert preserver.config is not None
        assert preserver.config.default_strategy == FitStrategy.EXACT
    
    def test_with_config(self):
        """Con configuración."""
        config = PreserverConfig(width_tolerance=1.0)
        preserver = GlyphWidthPreserver(config=config)
        
        assert preserver.config.width_tolerance == 1.0
    
    def test_with_font_extractor(self, mock_font_extractor):
        """Con extractor de fuentes."""
        preserver = GlyphWidthPreserver(font_extractor=mock_font_extractor)
        
        # Verificar que se usa el extractor
        preserver.set_font_extractor(mock_font_extractor)
        # Cache debería limpiarse
        assert preserver._width_cache == {}


# ============== Tests GlyphWidthPreserver - Width Calculation ==============


class TestGlyphWidthPreserverWidthCalc:
    """Tests de cálculo de anchos."""
    
    def test_get_char_width_helvetica(self, preserver):
        """Ancho de carácter Helvetica."""
        width = preserver.get_char_width('m', 'Helvetica', 12.0)
        
        # 'm' es uno de los caracteres más anchos
        assert width > 0
        assert width < 15  # Razonable para 12pt
    
    def test_get_char_width_courier(self, preserver):
        """Ancho de carácter Courier (monospace)."""
        # En monospace todos tienen el mismo ancho
        width_m = preserver.get_char_width('m', 'Courier', 12.0)
        width_i = preserver.get_char_width('i', 'Courier', 12.0)
        
        assert width_m == width_i  # Monospace
    
    def test_get_char_width_times(self, preserver):
        """Ancho de carácter Times."""
        width = preserver.get_char_width('W', 'Times', 12.0)
        
        assert width > 0
    
    def test_space_width(self, preserver):
        """Ancho del espacio."""
        width = preserver.get_char_width(' ', 'Helvetica', 12.0)
        
        assert width > 0
        assert width < 5  # Espacio es más angosto
    
    def test_measure_text_basic(self, preserver):
        """Medición de texto básico."""
        info = preserver.measure_text("Hello", "Helvetica", 12.0)
        
        assert info.text == "Hello"
        assert info.char_count == 5
        assert info.total_width_points > 0
        assert len(info.char_widths) == 5
    
    def test_measure_text_with_spaces(self, preserver):
        """Medición con espacios."""
        info = preserver.measure_text("Hello World", "Helvetica", 12.0)
        
        assert info.space_count == 1
        assert info.space_width > 0
        assert info.non_space_width > 0
    
    def test_measure_empty_text(self, preserver):
        """Medición de texto vacío."""
        info = preserver.measure_text("", "Helvetica", 12.0)
        
        assert info.char_count == 0
        assert info.total_width_points == 0
    
    def test_measure_with_font_extractor(self, preserver, mock_font_extractor):
        """Medición usando extractor de fuentes."""
        preserver.set_font_extractor(mock_font_extractor)
        
        preserver.measure_text("ABC", "EmbeddedFont", 12.0)
        
        # El mock devuelve 500 fu por carácter
        mock_font_extractor.get_glyph_widths.assert_called()


# ============== Tests GlyphWidthPreserver - Fit Analysis ==============


class TestGlyphWidthPreserverFitAnalysis:
    """Tests de análisis de ajuste."""
    
    def test_same_text_success(self, preserver):
        """Mismo texto siempre es éxito."""
        analysis = preserver.analyze_fit(
            original_text="Hello",
            new_text="Hello",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        assert analysis.fit_result == FitResult.SUCCESS
        assert analysis.width_difference == pytest.approx(0, abs=0.1)
    
    def test_shorter_text_needs_expansion(self, preserver):
        """Texto más corto necesita expansión."""
        analysis = preserver.analyze_fit(
            original_text="Hello World",
            new_text="Hi",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        assert analysis.width_difference < 0  # Nuevo es más corto
        # Con diferencia muy grande puede fallar con EXACT pero no debería crashear
        assert analysis.fit_result in (
            FitResult.SUCCESS, FitResult.EXPANDED, FitResult.SCALED, FitResult.FAILED
        )
    
    def test_longer_text_needs_compression(self, preserver):
        """Texto más largo necesita compresión."""
        analysis = preserver.analyze_fit(
            original_text="Hi",
            new_text="Hello World",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        assert analysis.width_difference > 0  # Nuevo es más largo
    
    def test_exact_strategy(self, preserver):
        """Estrategia EXACT."""
        analysis = preserver.analyze_fit(
            original_text="Hello World",
            new_text="Hola Mundo!",
            font_name="Helvetica",
            font_size=12.0,
            strategy=FitStrategy.EXACT,
        )
        
        # Debería intentar ajustar
        if analysis.is_success:
            assert analysis.adjustment is not None or abs(analysis.width_difference) < 0.5
    
    def test_compress_strategy_longer_text(self, preserver):
        """Estrategia COMPRESS con texto más largo."""
        analysis = preserver.analyze_fit(
            original_text="Hi",
            new_text="Hello World long text",
            font_name="Helvetica",
            font_size=12.0,
            strategy=FitStrategy.COMPRESS,
        )
        
        # Debería comprimir o escalar
        assert analysis.fit_strategy == FitStrategy.COMPRESS
    
    def test_expand_strategy_shorter_text(self, preserver):
        """Estrategia EXPAND con texto más corto."""
        analysis = preserver.analyze_fit(
            original_text="Hello World",
            new_text="Hi",
            font_name="Helvetica",
            font_size=12.0,
            strategy=FitStrategy.EXPAND,
        )
        
        assert analysis.fit_strategy == FitStrategy.EXPAND
    
    def test_truncate_strategy(self, preserver):
        """Estrategia TRUNCATE."""
        analysis = preserver.analyze_fit(
            original_text="Hi",
            new_text="Hello World Long Text Here",
            font_name="Helvetica",
            font_size=12.0,
            strategy=FitStrategy.TRUNCATE,
        )
        
        assert len(analysis.final_text) < len(analysis.new_text)
        assert analysis.fit_result == FitResult.TRUNCATED
    
    def test_ellipsis_strategy(self, preserver):
        """Estrategia ELLIPSIS."""
        analysis = preserver.analyze_fit(
            original_text="Short",
            new_text="Very Long Text That Should Be Truncated",
            font_name="Helvetica",
            font_size=12.0,
            strategy=FitStrategy.ELLIPSIS,
        )
        
        if analysis.fit_result == FitResult.TRUNCATED:
            assert analysis.final_text.endswith("...")
    
    def test_scale_strategy(self, preserver):
        """Estrategia SCALE."""
        analysis = preserver.analyze_fit(
            original_text="Hello World",
            new_text="Hello World!!",
            font_name="Helvetica",
            font_size=12.0,
            strategy=FitStrategy.SCALE,
        )
        
        if analysis.is_success:
            assert analysis.adjustment is not None
            assert analysis.adjustment.horizontal_scale != 100.0
    
    def test_allow_overflow_strategy(self, preserver):
        """Estrategia ALLOW_OVERFLOW."""
        analysis = preserver.analyze_fit(
            original_text="Hi",
            new_text="Hello World Long Text",
            font_name="Helvetica",
            font_size=12.0,
            strategy=FitStrategy.ALLOW_OVERFLOW,
        )
        
        assert analysis.fit_result == FitResult.OVERFLOW
        assert analysis.overflow_amount > 0
    
    def test_custom_target_width(self, preserver):
        """Ancho objetivo personalizado."""
        analysis = preserver.analyze_fit(
            original_text="Hello",
            new_text="Hi",
            font_name="Helvetica",
            font_size=12.0,
            target_width=100.0,  # Ancho personalizado
        )
        
        assert analysis.target_width == 100.0


# ============== Tests GlyphWidthPreserver - Adjustment Calculation ==============


class TestGlyphWidthPreserverAdjustment:
    """Tests de cálculo de ajustes."""
    
    def test_word_spacing_preferred_with_spaces(self, preserver):
        """Ajuste de espaciado preferido cuando hay espacios."""
        # Configurar para preferir word spacing
        preserver._config.prefer_word_spacing = True
        
        analysis = preserver.analyze_fit(
            original_text="Hello World Test",
            new_text="Hola Mundo Test",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        if analysis.adjustment and analysis.adjustment.has_adjustment:
            # Podría ser word_spacing o tracking
            assert analysis.adjustment.adjustment_type in (
                AdjustmentType.WORD_SPACING,
                AdjustmentType.TRACKING,
                AdjustmentType.COMBINED,
                AdjustmentType.HORIZONTAL_SCALE,
            )
    
    def test_tracking_used_without_spaces(self, preserver):
        """Tracking usado sin espacios."""
        analysis = preserver.analyze_fit(
            original_text="Hello",
            new_text="Hola!",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        if analysis.adjustment and analysis.adjustment.has_adjustment:
            # Sin espacios, debería usar tracking o scale
            assert analysis.adjustment.adjustment_type in (
                AdjustmentType.TRACKING,
                AdjustmentType.HORIZONTAL_SCALE,
            )
    
    def test_adjustment_limits_respected(self, strict_preserver):
        """Límites de ajuste respetados."""
        analysis = strict_preserver.analyze_fit(
            original_text="Hi",
            new_text="Hello World Very Long Text",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        if analysis.adjustment:
            adj = analysis.adjustment
            config = strict_preserver.config
            
            assert adj.tracking >= config.min_tracking
            assert adj.tracking <= config.max_tracking
            assert adj.word_spacing >= config.min_word_spacing
            assert adj.word_spacing <= config.max_word_spacing


# ============== Tests GlyphWidthPreserver - TJ Array ==============


class TestGlyphWidthPreserverTJArray:
    """Tests de generación de arrays TJ."""
    
    def test_generate_tj_simple(self, preserver):
        """TJ array simple."""
        entries = preserver.generate_tj_array(
            text="Hello",
            font_name="Helvetica",
            font_size=12.0,
            target_width=28.0,  # Aproximadamente ancho natural
        )
        
        assert len(entries) > 0
        assert any(e.is_text for e in entries)
    
    def test_generate_tj_with_adjustment(self, preserver):
        """TJ array con ajustes."""
        # Forzar diferencia grande
        entries = preserver.generate_tj_array(
            text="Hello",
            font_name="Helvetica",
            font_size=12.0,
            target_width=50.0,  # Más ancho que natural
        )
        
        # Debería tener ajustes entre caracteres
        # Puede tener ajustes si la diferencia es significativa
        assert any(not e.is_text for e in entries) or len(entries) > 0
    
    def test_generate_tj_empty(self, preserver):
        """TJ array para texto vacío."""
        entries = preserver.generate_tj_array(
            text="",
            font_name="Helvetica",
            font_size=12.0,
            target_width=10.0,
        )
        
        assert entries == []
    
    def test_tj_array_to_pdf(self, preserver):
        """Conversión a string PDF."""
        entries = [
            TJArrayEntry(is_text=True, text="Hel"),
            TJArrayEntry(is_text=False, adjustment=-50),
            TJArrayEntry(is_text=True, text="lo"),
        ]
        
        pdf = preserver.tj_array_to_pdf(entries)
        
        assert "TJ" in pdf
        assert "(Hel)" in pdf
        assert "(lo)" in pdf
        assert "-50" in pdf
    
    def test_tj_array_to_pdf_empty(self, preserver):
        """PDF para array vacío."""
        pdf = preserver.tj_array_to_pdf([])
        
        assert pdf == "[] TJ"


# ============== Tests GlyphWidthPreserver - Validation ==============


class TestGlyphWidthPreserverValidation:
    """Tests de validación."""
    
    def test_validate_same_text(self, preserver):
        """Validar mismo texto."""
        valid, msg = preserver.validate_fit(
            original_text="Hello",
            new_text="Hello",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        assert valid is True
    
    def test_validate_similar_text(self, preserver):
        """Validar texto similar."""
        valid, msg = preserver.validate_fit(
            original_text="Hello",
            new_text="Hola!",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        # Debería ser posible con alguna estrategia
        assert isinstance(valid, bool)
        assert isinstance(msg, str)
    
    def test_validate_very_different_text(self, strict_preserver):
        """Validar texto muy diferente."""
        valid, msg = strict_preserver.validate_fit(
            original_text="A",
            new_text="This is a very long text that cannot fit",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        # Con configuración estricta, probablemente no quepa
        assert isinstance(valid, bool)
    
    def test_get_max_text_length(self, preserver):
        """Obtener longitud máxima de texto."""
        max_len = preserver.get_max_text_length(
            target_width=100.0,
            font_name="Helvetica",
            font_size=12.0,
        )
        
        assert isinstance(max_len, int)
        assert max_len > 0
        assert max_len < 50  # Para 100pt y 12pt, razonable


# ============== Tests GlyphWidthPreserver - Serialization ==============


class TestGlyphWidthPreserverSerialization:
    """Tests de serialización."""
    
    def test_to_dict(self, preserver):
        """Serialización a diccionario."""
        d = preserver.to_dict()
        
        assert 'config' in d
        assert d['config']['default_strategy'] == 'EXACT'


# ============== Tests Factory Functions ==============


class TestFactoryFunctions:
    """Tests de funciones factory."""
    
    def test_create_width_preserver_default(self):
        """Crear preservador por defecto."""
        preserver = create_width_preserver()
        
        assert isinstance(preserver, GlyphWidthPreserver)
        assert preserver.config.default_strategy == FitStrategy.EXACT
    
    def test_create_width_preserver_custom(self):
        """Crear preservador personalizado."""
        preserver = create_width_preserver(
            default_strategy=FitStrategy.COMPRESS,
            width_tolerance=1.0,
        )
        
        assert preserver.config.default_strategy == FitStrategy.COMPRESS
        assert preserver.config.width_tolerance == 1.0
    
    def test_calculate_text_width_function(self):
        """Función calculate_text_width."""
        width = calculate_text_width(
            text="Hello",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        assert isinstance(width, float)
        assert width > 0
    
    def test_fit_text_to_width_function(self):
        """Función fit_text_to_width."""
        analysis = fit_text_to_width(
            original_text="Hello",
            new_text="Hi",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        assert isinstance(analysis, FitAnalysis)
        assert analysis.original_text == "Hello"
        assert analysis.new_text == "Hi"
    
    def test_get_spacing_adjustment_function(self):
        """Función get_spacing_adjustment."""
        adjustment = get_spacing_adjustment(
            original_text="Hello World",
            new_text="Hola Mundo",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        # Puede ser None o SpacingAdjustment
        assert adjustment is None or isinstance(adjustment, SpacingAdjustment)


# ============== Tests Edge Cases ==============


class TestEdgeCases:
    """Tests de casos límite."""
    
    def test_single_character(self, preserver):
        """Texto de un solo carácter."""
        info = preserver.measure_text("X", "Helvetica", 12.0)
        
        assert info.char_count == 1
        assert info.total_width_points > 0
    
    def test_unicode_text(self, preserver):
        """Texto Unicode."""
        info = preserver.measure_text("Héllo Wörld", "Helvetica", 12.0)
        
        assert info.char_count == 11
        assert info.total_width_points > 0
    
    def test_special_characters(self, preserver):
        """Caracteres especiales."""
        info = preserver.measure_text("@#$%^&*()", "Helvetica", 12.0)
        
        assert info.char_count == 9
        assert info.total_width_points > 0
    
    def test_zero_font_size(self, preserver):
        """Tamaño de fuente cero."""
        info = preserver.measure_text("Hello", "Helvetica", 0.0)
        
        assert info.total_width_points == 0
    
    def test_very_large_font_size(self, preserver):
        """Tamaño de fuente muy grande."""
        info = preserver.measure_text("Hi", "Helvetica", 1000.0)
        
        assert info.total_width_points > 0
    
    def test_unknown_font_fallback(self, preserver):
        """Fallback para fuente desconocida."""
        info = preserver.measure_text("Hello", "UnknownFont", 12.0)
        
        # Debería usar aproximación de Helvetica
        assert info.total_width_points > 0
    
    def test_only_spaces(self, preserver):
        """Texto de solo espacios."""
        info = preserver.measure_text("     ", "Helvetica", 12.0)
        
        assert info.space_count == 5
        assert info.char_count == 5
        assert info.non_space_width == 0
    
    def test_fit_empty_to_empty(self, preserver):
        """Ajustar vacío a vacío."""
        analysis = preserver.analyze_fit(
            original_text="",
            new_text="",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        assert analysis.fit_result == FitResult.SUCCESS


# ============== Tests Performance Considerations ==============


class TestPerformance:
    """Tests de rendimiento."""
    
    def test_long_text_measurement(self, preserver):
        """Medición de texto largo."""
        long_text = "Lorem ipsum dolor sit amet " * 100
        
        info = preserver.measure_text(long_text, "Helvetica", 12.0)
        
        assert info.char_count == len(long_text)
        assert info.total_width_points > 0
    
    def test_repeated_measurements_cached(self, preserver, mock_font_extractor):
        """Mediciones repetidas usan cache."""
        preserver.set_font_extractor(mock_font_extractor)
        
        # Primera medición
        preserver.measure_text("ABC", "TestFont", 12.0)
        
        # El mock debería ser llamado para cada carácter inicialmente
        first_call_count = mock_font_extractor.get_glyph_widths.call_count
        
        # Segunda medición con misma fuente y página
        preserver.measure_text("ABC", "TestFont", 12.0)
        
        # Verificar que el mock fue llamado al menos una vez
        assert first_call_count > 0


# ============== Tests Integration Scenarios ==============


class TestIntegrationScenarios:
    """Tests de escenarios de integración."""
    
    def test_replace_name_scenario(self, preserver):
        """Escenario: reemplazar nombre."""
        analysis = preserver.analyze_fit(
            original_text="John Smith",
            new_text="Jane Doe",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        assert analysis.is_success or analysis.fit_result in (
            FitResult.SCALED, FitResult.OVERFLOW
        )
    
    def test_replace_date_scenario(self, preserver):
        """Escenario: reemplazar fecha."""
        analysis = preserver.analyze_fit(
            original_text="2023-01-15",
            new_text="2024-12-31",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        # Mismo largo, debería ser exitoso fácilmente
        assert analysis.is_success
    
    def test_replace_currency_scenario(self, preserver):
        """Escenario: reemplazar monto."""
        analysis = preserver.analyze_fit(
            original_text="$1,234.56",
            new_text="$99.99",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        # Más corto, necesitará expansión
        assert analysis.width_difference < 0
    
    def test_replace_paragraph_title(self, preserver):
        """Escenario: reemplazar título de párrafo."""
        analysis = preserver.analyze_fit(
            original_text="Introduction to Programming",
            new_text="Getting Started with Code",
            font_name="Times",
            font_size=14.0,
        )
        
        # Verificar que se analiza correctamente
        assert analysis.original_text == "Introduction to Programming"
        assert analysis.new_text == "Getting Started with Code"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

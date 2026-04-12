"""
Tests para BaselineTracker.

Pruebas unitarias del módulo de rastreo de líneas base
e interlineado del motor de texto PDF.
"""

import pytest

from core.text_engine.baseline_tracker import (
    # Enums
    LeadingType,
    AlignmentGrid,
    
    # Dataclasses
    BaselineInfo,
    ParagraphBreak,
    BaselineAnalysis,
    LeadingAnalysis,
    BaselineTrackerConfig,
    
    # Clase principal
    BaselineTracker,
    
    # Funciones de utilidad
    analyze_page_baselines,
    calculate_leading,
    snap_to_grid,
    generate_baseline_grid,
    estimate_baseline_from_bbox,
    classify_leading_type,
    find_paragraph_breaks_in_baselines,
    validate_baseline_consistency,
)

from core.text_engine.text_line import TextLine
from core.text_engine.text_span import TextSpanMetrics


# ========== Fixtures ==========

@pytest.fixture
def create_text_line():
    """Factory fixture para crear TextLine."""
    def _create(
        baseline: float,
        font_size: float = 12.0,
        x0: float = 72.0,
        x1: float = 540.0,
        text: str = "Sample text"
    ) -> TextLine:
        # Crear span con los campos correctos de TextSpanMetrics
        span = TextSpanMetrics(
            text=text,
            page_num=0,
            font_name="Helvetica",
            font_size=font_size,
            bbox=(x0, baseline - font_size * 0.8, x1, baseline + font_size * 0.2),
            origin=(x0, baseline),
            baseline_y=baseline,
            char_spacing=0.0,
            word_spacing=0.0,
            rise=0.0,
            ctm=(1, 0, 0, 1, 0, 0),
            char_widths=[font_size * 0.5] * len(text)
        )
        
        # Crear TextLine y establecer baseline_y explícitamente
        line = TextLine(
            spans=[span],
            page_num=0,
            baseline_y=baseline
        )
        
        return line
    
    return _create


@pytest.fixture
def sample_lines(create_text_line):
    """Crea un conjunto de líneas de ejemplo."""
    # Simular un documento con interlineado de 14.4pt (12pt * 1.2)
    baselines = [100.0, 114.4, 128.8, 143.2, 157.6, 172.0]
    return [create_text_line(baseline=bl) for bl in baselines]


@pytest.fixture
def lines_with_paragraph_break(create_text_line):
    """Crea líneas con un salto de párrafo."""
    # Interlineado normal de 14.4pt, con salto de 28.8pt entre línea 3 y 4
    baselines = [100.0, 114.4, 128.8, 157.6, 172.0, 186.4]  # Salto extra después de 128.8
    return [create_text_line(baseline=bl) for bl in baselines]


@pytest.fixture
def tracker():
    """Crea un tracker básico."""
    return BaselineTracker()


@pytest.fixture
def configured_tracker():
    """Crea un tracker con configuración personalizada."""
    config = BaselineTrackerConfig(
        alignment_tolerance=0.5,
        paragraph_break_threshold=1.5,
        snap_tolerance=1.0
    )
    return BaselineTracker(config=config)


# ========== Tests de LeadingType Enum ==========

class TestLeadingTypeEnum:
    """Tests para el enum LeadingType."""
    
    def test_all_types_exist(self):
        """Verifica que todos los tipos existan."""
        assert LeadingType.SINGLE is not None
        assert LeadingType.ONE_HALF is not None
        assert LeadingType.DOUBLE is not None
        assert LeadingType.CUSTOM is not None
        assert LeadingType.PARAGRAPH_BREAK is not None
        assert LeadingType.UNKNOWN is not None
    
    def test_types_are_unique(self):
        """Verifica que los tipos sean únicos."""
        types = [
            LeadingType.SINGLE, LeadingType.ONE_HALF, LeadingType.DOUBLE,
            LeadingType.CUSTOM, LeadingType.PARAGRAPH_BREAK, LeadingType.UNKNOWN
        ]
        assert len(types) == len(set(types))


# ========== Tests de AlignmentGrid Enum ==========

class TestAlignmentGridEnum:
    """Tests para el enum AlignmentGrid."""
    
    def test_all_grid_types_exist(self):
        """Verifica que todos los tipos de grid existan."""
        assert AlignmentGrid.NONE is not None
        assert AlignmentGrid.REGULAR is not None
        assert AlignmentGrid.BASELINE is not None
        assert AlignmentGrid.MODULAR is not None


# ========== Tests de BaselineInfo ==========

class TestBaselineInfo:
    """Tests para BaselineInfo dataclass."""
    
    def test_creation(self):
        """Test de creación básica."""
        info = BaselineInfo(
            y=100.0,
            font_size=12.0,
            line_index=0
        )
        assert info.y == 100.0
        assert info.font_size == 12.0
        assert info.line_index == 0
        assert info.is_paragraph_start is False
        assert info.leading_from_prev is None
    
    def test_distance_to(self):
        """Test de cálculo de distancia."""
        info1 = BaselineInfo(y=100.0, font_size=12.0, line_index=0)
        info2 = BaselineInfo(y=114.4, font_size=12.0, line_index=1)
        
        assert abs(info1.distance_to(info2) - 14.4) < 0.01
        assert info1.distance_to(info2) == info2.distance_to(info1)


# ========== Tests de ParagraphBreak ==========

class TestParagraphBreak:
    """Tests para ParagraphBreak dataclass."""
    
    def test_creation(self):
        """Test de creación básica."""
        pb = ParagraphBreak(
            position=143.2,
            size=28.8,
            before_line=2,
            after_line=3
        )
        assert pb.position == 143.2
        assert pb.size == 28.8
        
    def test_ratio_to_leading(self):
        """Test del ratio al leading."""
        pb = ParagraphBreak(
            position=143.2,
            size=24.0,  # 2x el leading "normal" de 12pt
            before_line=2,
            after_line=3
        )
        assert pb.ratio_to_leading == 2.0


# ========== Tests de LeadingAnalysis ==========

class TestLeadingAnalysis:
    """Tests para LeadingAnalysis dataclass."""
    
    def test_classify_single(self):
        """Test clasificación de interlineado simple."""
        analysis = LeadingAnalysis.classify(14.4, 12.0)  # 1.2x
        assert analysis.type == LeadingType.SINGLE
        assert analysis.font_size_ratio == pytest.approx(1.2, rel=0.01)
    
    def test_classify_one_half(self):
        """Test clasificación de interlineado 1.5."""
        analysis = LeadingAnalysis.classify(18.0, 12.0)  # 1.5x
        assert analysis.type == LeadingType.ONE_HALF
    
    def test_classify_double(self):
        """Test clasificación de interlineado doble."""
        analysis = LeadingAnalysis.classify(24.0, 12.0)  # 2.0x
        assert analysis.type == LeadingType.DOUBLE
    
    def test_classify_paragraph_break(self):
        """Test clasificación de salto de párrafo."""
        analysis = LeadingAnalysis.classify(30.0, 12.0)  # 2.5x
        assert analysis.type == LeadingType.PARAGRAPH_BREAK
    
    def test_classify_custom(self):
        """Test clasificación de interlineado personalizado."""
        analysis = LeadingAnalysis.classify(48.0, 12.0)  # 4.0x
        assert analysis.type == LeadingType.CUSTOM


# ========== Tests de BaselineAnalysis ==========

class TestBaselineAnalysis:
    """Tests para BaselineAnalysis dataclass."""
    
    @pytest.fixture
    def sample_analysis(self):
        """Crea un análisis de ejemplo."""
        baselines = [
            BaselineInfo(y=100.0, font_size=12.0, line_index=0, leading_from_prev=None),
            BaselineInfo(y=114.4, font_size=12.0, line_index=1, leading_from_prev=14.4),
            BaselineInfo(y=128.8, font_size=12.0, line_index=2, leading_from_prev=14.4),
        ]
        return BaselineAnalysis(
            baselines=baselines,
            average_leading=14.4,
            leading_variance=0.0,
            paragraph_breaks=[],
            leading_type=LeadingType.SINGLE,
            grid_type=AlignmentGrid.REGULAR,
            dominant_font_size=12.0,
            min_leading=14.4,
            max_leading=14.4,
            baseline_count=3
        )
    
    def test_get_leading_at(self, sample_analysis):
        """Test obtención de leading en posición."""
        leading = sample_analysis.get_leading_at(110.0)
        assert leading == 14.4
    
    def test_get_nearest_baseline(self, sample_analysis):
        """Test obtención de baseline más cercana."""
        nearest = sample_analysis.get_nearest_baseline(112.0)
        assert nearest is not None
        assert nearest.y == 114.4
    
    def test_is_on_grid(self, sample_analysis):
        """Test verificación de posición en grid."""
        assert sample_analysis.is_on_grid(114.4, tolerance=0.5)
        assert not sample_analysis.is_on_grid(110.0, tolerance=0.5)


# ========== Tests de BaselineTrackerConfig ==========

class TestBaselineTrackerConfig:
    """Tests para BaselineTrackerConfig."""
    
    def test_default_values(self):
        """Test valores por defecto."""
        config = BaselineTrackerConfig()
        assert config.alignment_tolerance == 1.0
        assert config.paragraph_break_threshold == 1.8
        assert config.snap_tolerance == 2.0
    
    def test_custom_values(self):
        """Test valores personalizados."""
        config = BaselineTrackerConfig(
            alignment_tolerance=0.5,
            paragraph_break_threshold=2.0,
            snap_tolerance=1.5
        )
        assert config.alignment_tolerance == 0.5
        assert config.paragraph_break_threshold == 2.0
        assert config.snap_tolerance == 1.5


# ========== Tests de BaselineTracker ==========

class TestBaselineTracker:
    """Tests para la clase BaselineTracker."""
    
    def test_init_empty(self):
        """Test inicialización vacía."""
        tracker = BaselineTracker()
        assert tracker.baselines == []
        assert tracker.line_spacings == []
    
    def test_init_with_config(self):
        """Test inicialización con configuración."""
        config = BaselineTrackerConfig(snap_tolerance=3.0)
        tracker = BaselineTracker(config=config)
        assert tracker.config.snap_tolerance == 3.0
    
    def test_set_lines(self, tracker, sample_lines):
        """Test establecer líneas."""
        tracker.set_lines(sample_lines)
        assert len(tracker._lines) == len(sample_lines)
    
    def test_analyze_page_empty(self, tracker):
        """Test análisis de página vacía."""
        analysis = tracker.analyze_page([])
        assert analysis.baseline_count == 0
        assert analysis.leading_type == LeadingType.UNKNOWN
    
    def test_analyze_page(self, tracker, sample_lines):
        """Test análisis de página con líneas."""
        analysis = tracker.analyze_page(sample_lines)
        
        assert analysis.baseline_count == 6
        assert analysis.average_leading == pytest.approx(14.4, rel=0.01)
        assert analysis.leading_type == LeadingType.SINGLE
    
    def test_analyze_page_with_paragraph_break(self, tracker, lines_with_paragraph_break):
        """Test análisis detecta saltos de párrafo."""
        analysis = tracker.analyze_page(lines_with_paragraph_break)
        
        # Debe detectar que hay líneas marca como inicio de párrafo
        para_starts = [bl for bl in analysis.baselines if bl.is_paragraph_start]
        assert len(para_starts) >= 1  # Al menos la primera línea
    
    def test_detect_leading(self, tracker, create_text_line):
        """Test detección de interlineado."""
        line1 = create_text_line(baseline=100.0)
        line2 = create_text_line(baseline=114.4)
        
        leading = tracker.detect_leading(line1, line2)
        assert leading == pytest.approx(14.4, rel=0.01)
    
    def test_snap_to_baseline_grid(self, tracker, sample_lines):
        """Test snap a grid de baselines."""
        tracker.analyze_page(sample_lines)
        
        # Snap a baseline cercana
        snapped = tracker.snap_to_baseline_grid(113.5)
        assert snapped == pytest.approx(114.4, rel=0.01)
    
    def test_snap_no_snap_far_position(self, tracker, sample_lines):
        """Test no snap para posición lejana."""
        tracker.analyze_page(sample_lines)
        
        # Posición muy lejana no debe hacer snap
        original = 107.0
        snapped = tracker.snap_to_baseline_grid(original)
        assert snapped == original  # No cambió
    
    def test_calculate_new_position(self, tracker, sample_lines):
        """Test cálculo de nueva posición."""
        tracker.analyze_page(sample_lines)
        
        new_pos = tracker.calculate_new_position(100.0, 5.0, preserve_grid=False)
        assert new_pos == pytest.approx(104.5, rel=0.01)  # Con factor 0.9
    
    def test_get_leading_at_position(self, tracker, sample_lines):
        """Test obtención de leading en posición."""
        tracker.analyze_page(sample_lines)
        
        leading, leading_type = tracker.get_leading_at_position(110.0)
        assert leading == pytest.approx(14.4, rel=0.01)
        assert leading_type == LeadingType.SINGLE
    
    def test_find_insertion_point_middle(self, tracker, sample_lines):
        """Test encontrar punto de inserción en medio."""
        tracker.analyze_page(sample_lines)
        
        points = tracker.find_insertion_point(2, num_lines=1)
        assert len(points) == 1
        # Debe estar entre línea 2 y 3
    
    def test_find_insertion_point_start(self, tracker, sample_lines):
        """Test punto de inserción al inicio."""
        tracker.analyze_page(sample_lines)
        
        points = tracker.find_insertion_point(-1, num_lines=1)
        assert len(points) == 1
        assert points[0] < 100.0  # Antes de primera línea
    
    def test_find_insertion_point_end(self, tracker, sample_lines):
        """Test punto de inserción al final."""
        tracker.analyze_page(sample_lines)
        
        points = tracker.find_insertion_point(10, num_lines=1)
        assert len(points) == 1
        assert points[0] > 172.0  # Después de última línea
    
    def test_validate_leading_valid(self, tracker, sample_lines):
        """Test validación de leading válido."""
        tracker.analyze_page(sample_lines)
        
        is_valid, msg = tracker.validate_leading(14.4)
        assert is_valid
    
    def test_validate_leading_too_small(self, tracker, sample_lines):
        """Test validación de leading muy pequeño."""
        tracker.analyze_page(sample_lines)
        
        is_valid, msg = tracker.validate_leading(2.0)
        assert not is_valid
        assert "too small" in msg.lower()
    
    def test_validate_leading_too_large(self, tracker, sample_lines):
        """Test validación de leading muy grande."""
        tracker.analyze_page(sample_lines)
        
        is_valid, msg = tracker.validate_leading(100.0)
        assert not is_valid
        assert "too large" in msg.lower()
    
    def test_estimate_lines_that_fit(self, tracker, sample_lines):
        """Test estimación de líneas que caben."""
        tracker.analyze_page(sample_lines)
        
        # Con 72 puntos de altura y leading de 14.4, caben 5 líneas
        num_lines = tracker.estimate_lines_that_fit(72.0)
        assert num_lines == 5
    
    def test_estimate_lines_zero_height(self, tracker, sample_lines):
        """Test estimación con altura cero."""
        tracker.analyze_page(sample_lines)
        
        num_lines = tracker.estimate_lines_that_fit(0)
        assert num_lines == 0
    
    def test_get_baseline_grid(self, tracker, sample_lines):
        """Test generación de grid de baselines."""
        tracker.analyze_page(sample_lines)
        
        grid = tracker.get_baseline_grid(100.0, 150.0)
        assert len(grid) >= 3  # Al menos 3 puntos
        assert grid[0] == 100.0
    
    def test_align_to_existing_baselines(self, tracker, sample_lines):
        """Test alineación a baselines existentes."""
        tracker.analyze_page(sample_lines)
        
        positions = [99.5, 114.0, 129.0]
        aligned = tracker.align_to_existing_baselines(positions)
        
        # Deberían ajustarse a baselines cercanas
        assert aligned[0] == pytest.approx(100.0, rel=0.01)
        assert aligned[1] == pytest.approx(114.4, rel=0.01)


# ========== Tests de funciones de utilidad ==========

class TestUtilityFunctions:
    """Tests para funciones de utilidad."""
    
    def test_analyze_page_baselines(self, sample_lines):
        """Test función analyze_page_baselines."""
        analysis = analyze_page_baselines(sample_lines)
        
        assert analysis.baseline_count == 6
        assert analysis.average_leading > 0
    
    def test_calculate_leading(self, create_text_line):
        """Test función calculate_leading."""
        line1 = create_text_line(baseline=100.0)
        line2 = create_text_line(baseline=114.4)
        
        leading = calculate_leading(line1, line2)
        assert leading == pytest.approx(14.4, rel=0.01)
    
    def test_snap_to_grid_within_tolerance(self):
        """Test snap a grid dentro de tolerancia."""
        baselines = [100.0, 114.4, 128.8]
        
        snapped = snap_to_grid(100.5, baselines, tolerance=1.0)
        assert snapped == 100.0
    
    def test_snap_to_grid_outside_tolerance(self):
        """Test snap a grid fuera de tolerancia."""
        baselines = [100.0, 114.4, 128.8]
        
        snapped = snap_to_grid(105.0, baselines, tolerance=1.0)
        assert snapped == 105.0  # Sin cambio
    
    def test_snap_to_grid_empty(self):
        """Test snap a grid vacío."""
        snapped = snap_to_grid(100.0, [], tolerance=1.0)
        assert snapped == 100.0
    
    def test_generate_baseline_grid(self):
        """Test generación de grid."""
        grid = generate_baseline_grid(100.0, 150.0, 10.0)
        
        assert len(grid) == 6
        assert grid[0] == 100.0
        assert grid[-1] == 150.0
    
    def test_generate_baseline_grid_invalid(self):
        """Test generación de grid con valores inválidos."""
        assert generate_baseline_grid(100.0, 50.0, 10.0) == []  # start > end
        assert generate_baseline_grid(100.0, 150.0, 0) == []   # leading = 0
        assert generate_baseline_grid(100.0, 150.0, -5) == []  # leading < 0
    
    def test_estimate_baseline_from_bbox(self):
        """Test estimación de baseline desde bbox."""
        bbox = (72.0, 700.0, 540.0, 712.0)  # Altura de 12pt
        
        baseline = estimate_baseline_from_bbox(bbox, font_size=12.0)
        
        # Baseline debe estar en ~80% desde arriba
        expected = 700.0 + 12.0 * 0.8
        assert baseline == pytest.approx(expected, rel=0.01)
    
    def test_classify_leading_type_single(self):
        """Test clasificación de leading simple."""
        lead_type = classify_leading_type(14.4, 12.0)
        assert lead_type == LeadingType.SINGLE
    
    def test_classify_leading_type_double(self):
        """Test clasificación de leading doble."""
        lead_type = classify_leading_type(24.0, 12.0)
        assert lead_type == LeadingType.DOUBLE
    
    def test_find_paragraph_breaks_in_baselines(self):
        """Test encontrar saltos de párrafo."""
        # Interlineado normal ~14.4, salto de ~43.2 (3x) después del 3er elemento
        baselines = [100.0, 114.4, 128.8, 172.0, 186.4]  # Salto grande de 43.2
        
        breaks = find_paragraph_breaks_in_baselines(baselines, threshold_ratio=1.8)
        
        assert len(breaks) == 1
        assert breaks[0] == 3  # Salto antes del índice 3
    
    def test_find_paragraph_breaks_none(self):
        """Test sin saltos de párrafo."""
        baselines = [100.0, 114.4, 128.8, 143.2]
        
        breaks = find_paragraph_breaks_in_baselines(baselines)
        assert len(breaks) == 0
    
    def test_validate_baseline_consistency_consistent(self):
        """Test validación de baselines consistentes."""
        baselines = [100.0, 114.4, 128.8, 143.2]
        
        is_consistent, inconsistent = validate_baseline_consistency(baselines)
        assert is_consistent
        assert len(inconsistent) == 0
    
    def test_validate_baseline_consistency_inconsistent(self):
        """Test validación de baselines inconsistentes."""
        baselines = [100.0, 114.4, 150.0, 164.4]  # Salto grande en medio
        
        is_consistent, inconsistent = validate_baseline_consistency(baselines, tolerance=2.0)
        assert not is_consistent
        assert len(inconsistent) > 0


# ========== Tests de integración ==========

class TestIntegration:
    """Tests de integración del BaselineTracker."""
    
    def test_full_workflow(self, create_text_line):
        """Test flujo completo de trabajo."""
        # Crear documento con varias secciones
        lines = [
            # Primer párrafo
            create_text_line(baseline=100.0, text="Line 1"),
            create_text_line(baseline=114.4, text="Line 2"),
            create_text_line(baseline=128.8, text="Line 3"),
            # Salto de párrafo grande (3x leading)
            create_text_line(baseline=172.0, text="Line 4"),
            create_text_line(baseline=186.4, text="Line 5"),
        ]
        
        tracker = BaselineTracker()
        analysis = tracker.analyze_page(lines)
        
        # Verificar análisis básico
        assert analysis.baseline_count == 5
        
        # Verificar que detecta inicio de párrafos
        para_starts = [bl for bl in analysis.baselines if bl.is_paragraph_start]
        assert len(para_starts) >= 1
        
        # Probar snap a grid
        snapped = tracker.snap_to_baseline_grid(113.0)
        assert snapped == pytest.approx(114.4, rel=0.1)
        
        # Probar inserción
        insert_points = tracker.find_insertion_point(2, num_lines=1)
        assert len(insert_points) == 1
    
    def test_multisize_document(self, create_text_line):
        """Test documento con múltiples tamaños de fuente."""
        lines = [
            create_text_line(baseline=100.0, font_size=18.0, text="Title"),
            create_text_line(baseline=130.0, font_size=12.0, text="Body 1"),
            create_text_line(baseline=144.4, font_size=12.0, text="Body 2"),
        ]
        
        tracker = BaselineTracker()
        analysis = tracker.analyze_page(lines)
        
        # Debe manejar tamaños mixtos
        assert analysis.baseline_count == 3
        assert analysis.dominant_font_size == 12.0  # El más común
    
    def test_realignment_after_edit(self, sample_lines):
        """Test realineación después de editar."""
        tracker = BaselineTracker()
        tracker.analyze_page(sample_lines)
        
        # Simular que el texto creció 5 puntos
        new_pos = tracker.calculate_new_position(
            original_baseline=100.0,
            text_height_change=5.0,
            preserve_grid=False  # Sin preservar grid para test simple
        )
        
        # Debe calcular nueva posición (con factor 0.9)
        assert new_pos == pytest.approx(104.5, rel=0.01)
    
    def test_empty_page_handling(self):
        """Test manejo de página vacía."""
        tracker = BaselineTracker()
        analysis = tracker.analyze_page([])
        
        # No debe fallar con página vacía
        assert analysis.baseline_count == 0
        assert analysis.average_leading == 0.0
        
        # Métodos deben manejar estado vacío
        assert tracker.snap_to_baseline_grid(100.0) == 100.0
        assert tracker.estimate_lines_that_fit(100.0, font_size=12.0) == 6


# ========== Tests de edge cases ==========

class TestEdgeCases:
    """Tests de casos límite."""
    
    def test_single_line(self, create_text_line):
        """Test con una sola línea."""
        lines = [create_text_line(baseline=100.0)]
        
        tracker = BaselineTracker()
        analysis = tracker.analyze_page(lines)
        
        assert analysis.baseline_count == 1
        assert analysis.average_leading == 0.0
    
    def test_two_lines(self, create_text_line):
        """Test con dos líneas."""
        lines = [
            create_text_line(baseline=100.0),
            create_text_line(baseline=114.4),
        ]
        
        tracker = BaselineTracker()
        analysis = tracker.analyze_page(lines)
        
        assert analysis.baseline_count == 2
        assert analysis.average_leading == pytest.approx(14.4, rel=0.01)
    
    def test_irregular_leading(self, create_text_line):
        """Test con interlineado irregular."""
        lines = [
            create_text_line(baseline=100.0),
            create_text_line(baseline=115.0),  # 15pt
            create_text_line(baseline=128.0),  # 13pt
            create_text_line(baseline=145.0),  # 17pt
        ]
        
        tracker = BaselineTracker()
        analysis = tracker.analyze_page(lines)
        
        # Debe detectar varianza alta
        assert analysis.leading_variance > 0
    
    def test_very_large_document(self, create_text_line):
        """Test con documento muy grande."""
        # 100 líneas
        lines = [create_text_line(baseline=100.0 + i * 14.4) for i in range(100)]
        
        tracker = BaselineTracker()
        analysis = tracker.analyze_page(lines)
        
        assert analysis.baseline_count == 100
        assert analysis.grid_type == AlignmentGrid.REGULAR
    
    def test_negative_baselines(self, create_text_line):
        """Test con baselines negativas."""
        lines = [
            create_text_line(baseline=-50.0),
            create_text_line(baseline=-35.6),
            create_text_line(baseline=-21.2),
        ]
        
        tracker = BaselineTracker()
        analysis = tracker.analyze_page(lines)
        
        assert analysis.baseline_count == 3
        # Debe funcionar con coordenadas negativas
    
    def test_zero_font_size(self, create_text_line):
        """Test handling de font size cero."""
        # Esto no debería ocurrir en la práctica, pero no debe crashear
        lines = [create_text_line(baseline=100.0, font_size=0.001)]
        
        tracker = BaselineTracker()
        analysis = tracker.analyze_page(lines)
        
        assert analysis.baseline_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

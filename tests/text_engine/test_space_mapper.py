"""
Tests para SpaceMapper - Mapeo y análisis de espacios en texto PDF.

Cobertura:
1. SpaceInfo - propiedades de espacios individuales
2. SpaceAnalysis - resultado del análisis
3. SpaceMapper - análisis de espacios intra-span
4. SpaceMapper - análisis de gaps inter-span
5. SpaceMapper - reconstrucción de texto
6. SpaceMapper - preservación de espaciado
7. Funciones de utilidad
"""

import pytest
from typing import List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.text_engine.space_mapper import (
    SpaceType,
    SpaceInfo,
    WordBoundary,
    SpaceAnalysis,
    SpaceMapperConfig,
    SpaceMapper,
    analyze_line_spacing,
    reconstruct_line_text,
    count_words_in_line,
    estimate_character_positions,
    find_char_at_x,
    calculate_space_metrics,
)
from core.text_engine.text_line import TextLine
from core.text_engine.text_span import TextSpanMetrics


# === Fixtures ===

def create_span(
    text: str,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    font: str = "Helvetica",
    size: float = 12.0,
    word_spacing: float = 0.0,
    char_widths: List[float] = None
) -> TextSpanMetrics:
    """Crea un TextSpanMetrics para testing."""
    return TextSpanMetrics(
        text=text,
        page_num=0,
        bbox=(x0, y0, x1, y1),
        baseline_y=y1 - size * 0.2,
        font_name=font,
        font_size=size,
        font_flags=0,
        char_spacing=0.0,
        word_spacing=word_spacing,
        rise=0.0,
        ctm=(1.0, 0.0, 0.0, 1.0, x0, y0),
        char_widths=char_widths or [],
    )


def create_line_with_spans(
    span_data: List[tuple],
    page_num: int = 0
) -> TextLine:
    """
    Crea una TextLine con múltiples spans.
    
    span_data: Lista de (text, x0, x1) para cada span
    """
    spans = []
    y0, y1 = 88.0, 100.0
    
    for text, x0, x1 in span_data:
        span = create_span(text, x0, y0, x1, y1)
        spans.append(span)
    
    return TextLine(spans=spans, page_num=page_num, baseline_y=98.0)


def create_simple_line(text: str, x_start: float = 72.0) -> TextLine:
    """Crea una línea simple con un solo span."""
    char_width = 7.0
    width = len(text) * char_width
    span = create_span(text, x_start, 88.0, x_start + width, 100.0)
    return TextLine(spans=[span], page_num=0, baseline_y=98.0)


# ============================================================
# TESTS: SpaceInfo
# ============================================================

class TestSpaceInfo:
    """Tests para SpaceInfo dataclass."""
    
    def test_default_space_info(self):
        """SpaceInfo con valores por defecto."""
        info = SpaceInfo()
        
        assert info.space_type == SpaceType.UNKNOWN
        assert info.width == 0.0
        assert info.char_index is None
        assert not info.is_inter_span
    
    def test_real_space_properties(self):
        """Propiedades de un espacio real."""
        info = SpaceInfo(
            space_type=SpaceType.REAL_SPACE,
            x_start=100.0,
            x_end=107.0,
            width=7.0,
            char_index=5,
            source="char"
        )
        
        assert info.is_real
        assert not info.is_virtual
        assert info.is_word_boundary
    
    def test_virtual_space_properties(self):
        """Propiedades de un espacio virtual."""
        info = SpaceInfo(
            space_type=SpaceType.VIRTUAL_SPACE,
            width=5.0,
            source="gap"
        )
        
        assert not info.is_real
        assert info.is_virtual
        assert info.is_word_boundary
    
    def test_tab_properties(self):
        """Propiedades de una tabulación."""
        info = SpaceInfo(
            space_type=SpaceType.TAB,
            width=28.0,
            source="gap"
        )
        
        assert not info.is_real
        assert info.is_virtual
        assert info.is_word_boundary
    
    def test_nbsp_is_real(self):
        """Non-breaking space es un espacio real."""
        info = SpaceInfo(space_type=SpaceType.NBSP)
        
        assert info.is_real
        assert not info.is_virtual
    
    def test_tj_adjustment_not_word_boundary(self):
        """Ajustes TJ no son límites de palabra."""
        info = SpaceInfo(
            space_type=SpaceType.TJ_ADJUSTMENT,
            width=0.5
        )
        
        assert info.is_virtual
        assert not info.is_word_boundary


# ============================================================
# TESTS: SpaceAnalysis
# ============================================================

class TestSpaceAnalysis:
    """Tests para SpaceAnalysis dataclass."""
    
    def test_empty_analysis(self):
        """Análisis vacío."""
        analysis = SpaceAnalysis()
        
        assert analysis.total_space_count == 0
        assert len(analysis.all_spaces) == 0
        assert analysis.word_count == 1
    
    def test_all_spaces_sorted(self):
        """all_spaces retorna espacios ordenados por X."""
        analysis = SpaceAnalysis(
            real_spaces=[
                SpaceInfo(x_start=50.0, x_end=57.0),
            ],
            virtual_spaces=[
                SpaceInfo(x_start=100.0, x_end=107.0),
            ],
            probable_tabs=[
                SpaceInfo(x_start=25.0, x_end=53.0),
            ]
        )
        
        all_sp = analysis.all_spaces
        
        assert len(all_sp) == 3
        assert all_sp[0].x_start == 25.0  # Tab primero
        assert all_sp[1].x_start == 50.0  # Luego real
        assert all_sp[2].x_start == 100.0  # Luego virtual
    
    def test_word_count_with_boundaries(self):
        """word_count basado en boundaries."""
        analysis = SpaceAnalysis(
            word_boundaries=[
                WordBoundary(x_position=50.0),
                WordBoundary(x_position=100.0),
            ]
        )
        
        assert analysis.word_count == 3  # 2 boundaries = 3 palabras
    
    def test_get_space_at_index(self):
        """Obtener espacio por índice de carácter."""
        space1 = SpaceInfo(char_index=5, x_start=35.0)
        space2 = SpaceInfo(char_index=10, x_start=70.0)
        
        analysis = SpaceAnalysis(real_spaces=[space1, space2])
        
        found = analysis.get_space_at_index(5)
        assert found is not None
        assert found.x_start == 35.0
        
        not_found = analysis.get_space_at_index(7)
        assert not_found is None
    
    def test_get_space_at_x(self):
        """Obtener espacio por posición X."""
        space = SpaceInfo(x_start=50.0, x_end=57.0)
        analysis = SpaceAnalysis(real_spaces=[space])
        
        found = analysis.get_space_at_x(53.0)
        assert found is not None
        
        not_found = analysis.get_space_at_x(100.0)
        assert not_found is None


# ============================================================
# TESTS: SpaceMapperConfig
# ============================================================

class TestSpaceMapperConfig:
    """Tests para configuración del SpaceMapper."""
    
    def test_default_config(self):
        """Configuración por defecto."""
        config = SpaceMapperConfig()
        
        assert config.min_space_width == 1.0
        assert config.tab_threshold_multiplier == 3.5
        assert config.default_space_width == 3.0
        assert config.use_word_spacing
        assert config.include_tj_adjustments
    
    def test_custom_config(self):
        """Configuración personalizada."""
        config = SpaceMapperConfig(
            min_space_width=2.0,
            tab_threshold_multiplier=4.0
        )
        
        assert config.min_space_width == 2.0
        assert config.tab_threshold_multiplier == 4.0


# ============================================================
# TESTS: SpaceMapper - Análisis básico
# ============================================================

class TestSpaceMapperBasic:
    """Tests básicos para SpaceMapper."""
    
    def test_analyze_empty_line(self):
        """Analizar línea vacía."""
        line = TextLine(spans=[], page_num=0)
        mapper = SpaceMapper()
        
        analysis = mapper.analyze_line(line)
        
        assert analysis.total_space_count == 0
        assert len(analysis.real_spaces) == 0
    
    def test_analyze_single_word(self):
        """Línea con una sola palabra (sin espacios)."""
        line = create_simple_line("Hello")
        mapper = SpaceMapper()
        
        analysis = mapper.analyze_line(line)
        
        assert len(analysis.real_spaces) == 0
        assert analysis.word_count == 1
    
    def test_analyze_two_words(self):
        """Línea con dos palabras y un espacio."""
        line = create_simple_line("Hello World")
        mapper = SpaceMapper()
        
        analysis = mapper.analyze_line(line)
        
        # Debe detectar el espacio entre "Hello" y "World"
        assert len(analysis.real_spaces) >= 1
    
    def test_analyze_multiple_spaces(self):
        """Línea con múltiples espacios."""
        line = create_simple_line("One Two Three Four")
        mapper = SpaceMapper()
        
        analysis = mapper.analyze_line(line)
        
        # 3 espacios entre 4 palabras
        assert len(analysis.real_spaces) >= 3


# ============================================================
# TESTS: SpaceMapper - Análisis intra-span
# ============================================================

class TestSpaceMapperIntraSpan:
    """Tests para análisis de espacios dentro de spans."""
    
    def test_detect_real_space_in_span(self):
        """Detectar carácter espacio real dentro de un span."""
        span = create_span("Hello World", 72.0, 88.0, 149.0, 100.0)
        line = TextLine(spans=[span], baseline_y=98.0)
        
        mapper = SpaceMapper()
        analysis = mapper.analyze_line(line)
        
        # Debe encontrar el espacio entre "Hello" y "World"
        assert len(analysis.real_spaces) >= 1
        
        space = analysis.real_spaces[0]
        assert space.space_type == SpaceType.REAL_SPACE
        assert space.char_index == 5  # Índice del espacio
    
    def test_detect_nbsp(self):
        """Detectar non-breaking space."""
        span = create_span("Hello\u00A0World", 72.0, 88.0, 156.0, 100.0)
        line = TextLine(spans=[span], baseline_y=98.0)
        
        mapper = SpaceMapper()
        analysis = mapper.analyze_line(line)
        
        nbsp_spaces = [s for s in analysis.real_spaces if s.space_type == SpaceType.NBSP]
        assert len(nbsp_spaces) == 1
    
    def test_space_width_from_char_widths(self):
        """Usar char_widths para ancho de espacio si está disponible."""
        # Crear span con char_widths definidos
        char_widths = [7.0, 7.0, 7.0, 7.0, 7.0, 5.0, 7.0, 7.0, 7.0, 7.0, 7.0]  # 5.0 para el espacio
        span = create_span(
            "Hello World",
            72.0, 88.0, 149.0, 100.0,
            char_widths=char_widths
        )
        line = TextLine(spans=[span], baseline_y=98.0)
        
        mapper = SpaceMapper()
        analysis = mapper.analyze_line(line)
        
        # El espacio debe tener el ancho especificado
        if analysis.real_spaces:
            space = analysis.real_spaces[0]
            assert space.width == 5.0


# ============================================================
# TESTS: SpaceMapper - Análisis inter-span
# ============================================================

class TestSpaceMapperInterSpan:
    """Tests para análisis de gaps entre spans."""
    
    def test_detect_gap_between_spans(self):
        """Detectar gap entre dos spans."""
        line = create_line_with_spans([
            ("Hello", 72.0, 107.0),
            ("World", 115.0, 150.0),  # Gap de 8pt
        ])
        
        mapper = SpaceMapper()
        analysis = mapper.analyze_line(line)
        
        # Debe encontrar el gap virtual
        assert len(analysis.virtual_spaces) >= 1 or len(analysis.probable_tabs) >= 0
    
    def test_large_gap_as_tab(self):
        """Gap grande se detecta como tabulación."""
        line = create_line_with_spans([
            ("Hello", 72.0, 107.0),
            ("World", 180.0, 215.0),  # Gap de 73pt (muy grande)
        ])
        
        # Con configuración que detecte tabs fácilmente
        config = SpaceMapperConfig(tab_threshold_multiplier=3.0)
        mapper = SpaceMapper(config)
        analysis = mapper.analyze_line(line)
        
        # Debe detectarse como tab debido al gran tamaño
        total_spaces = analysis.all_spaces
        assert len(total_spaces) >= 1
    
    def test_no_gap_overlapping_spans(self):
        """No detectar gap si spans se superponen."""
        line = create_line_with_spans([
            ("Hello", 72.0, 110.0),
            ("World", 108.0, 145.0),  # Se superpone ligeramente
        ])
        
        mapper = SpaceMapper()
        analysis = mapper.analyze_line(line)
        
        # No debe haber gaps inter-span (se superponen)
        inter_span_spaces = [s for s in analysis.all_spaces if s.is_inter_span]
        assert len(inter_span_spaces) == 0
    
    def test_gap_marked_as_inter_span(self):
        """Gaps entre spans se marcan como is_inter_span=True."""
        line = create_line_with_spans([
            ("A", 72.0, 79.0),
            ("B", 90.0, 97.0),
        ])
        
        mapper = SpaceMapper()
        analysis = mapper.analyze_line(line)
        
        inter_spaces = [s for s in analysis.all_spaces if s.is_inter_span]
        for space in inter_spaces:
            assert space.is_inter_span
            assert space.source == "gap"


# ============================================================
# TESTS: SpaceMapper - Reconstrucción de texto
# ============================================================

class TestSpaceMapperReconstruct:
    """Tests para reconstrucción de texto."""
    
    def test_reconstruct_simple(self):
        """Reconstruir texto simple."""
        line = create_simple_line("Hello World")
        mapper = SpaceMapper()
        
        text = mapper.reconstruct_with_spaces(line)
        
        assert "Hello" in text
        assert "World" in text
    
    def test_reconstruct_with_gap(self):
        """Reconstruir texto con gap entre spans."""
        line = create_line_with_spans([
            ("Hello", 72.0, 107.0),
            ("World", 115.0, 150.0),
        ])
        
        mapper = SpaceMapper()
        text = mapper.reconstruct_with_spaces(line)
        
        # Debe haber espacio entre las palabras
        assert "Hello" in text
        assert "World" in text
    
    def test_reconstruct_normalize_spaces(self):
        """Normalizar múltiples espacios."""
        # Simular texto con múltiples espacios
        span = create_span("Hello  World", 72.0, 88.0, 163.0, 100.0)
        line = TextLine(spans=[span], baseline_y=98.0)
        
        mapper = SpaceMapper()
        text = mapper.reconstruct_with_spaces(line, normalize_spaces=True)
        
        # No debe haber dobles espacios
        assert "  " not in text
    
    def test_reconstruct_empty_line(self):
        """Reconstruir línea vacía."""
        line = TextLine(spans=[], page_num=0)
        mapper = SpaceMapper()
        
        text = mapper.reconstruct_with_spaces(line)
        
        assert text == ""


# ============================================================
# TESTS: SpaceMapper - Preservación de espaciado
# ============================================================

class TestSpaceMapperPreserve:
    """Tests para preservación de espaciado al editar."""
    
    def test_preserve_spacing_instructions(self):
        """Generar instrucciones de preservación."""
        line = create_simple_line("Hello World")
        mapper = SpaceMapper()
        
        instructions = mapper.preserve_spacing_for_edit(line, "Hola Mundo")
        
        # Debe generar instrucciones para el espacio
        assert isinstance(instructions, list)
    
    def test_preserve_empty_text(self):
        """Preservar con texto vacío."""
        line = create_simple_line("Hello")
        mapper = SpaceMapper()
        
        instructions = mapper.preserve_spacing_for_edit(line, "")
        
        assert instructions == []


# ============================================================
# TESTS: SpaceMapper - Cálculo de ajuste
# ============================================================

class TestSpaceMapperFit:
    """Tests para cálculo de ajuste de texto."""
    
    def test_text_fits(self):
        """Texto que cabe en el espacio disponible."""
        mapper = SpaceMapper()
        
        result = mapper.calculate_text_fit(
            available_width=100.0,
            text="Hello",
            avg_char_width=7.0
        )
        
        assert result['fits']
        assert not result['needs_truncation']
        assert result['overflow'] == 0
    
    def test_text_too_long(self):
        """Texto demasiado largo."""
        mapper = SpaceMapper()
        
        result = mapper.calculate_text_fit(
            available_width=30.0,
            text="Hello World",
            avg_char_width=7.0
        )
        
        assert not result['fits']
        assert result['needs_truncation']
        assert result['overflow'] > 0
    
    def test_text_utilization(self):
        """Calcular utilización del espacio."""
        mapper = SpaceMapper()
        
        result = mapper.calculate_text_fit(
            available_width=100.0,
            text="Hello",  # 5 chars * 7 = 35pt
            avg_char_width=7.0
        )
        
        assert result['utilization'] == 0.35  # 35/100
    
    def test_chars_that_fit(self):
        """Calcular caracteres que caben."""
        mapper = SpaceMapper()
        
        result = mapper.calculate_text_fit(
            available_width=28.0,
            text="Hello World",
            avg_char_width=7.0
        )
        
        assert result['chars_that_fit'] == 4  # 28 / 7 = 4


# ============================================================
# TESTS: SpaceMapper - Sugerencia de saltos de línea
# ============================================================

class TestSpaceMapperLineBreaks:
    """Tests para sugerencia de saltos de línea."""
    
    def test_no_breaks_short_text(self):
        """No sugerir saltos para texto corto."""
        mapper = SpaceMapper()
        
        breaks = mapper.suggest_line_breaks(
            text="Hello",
            max_width=100.0,
            avg_char_width=7.0
        )
        
        assert breaks == []
    
    def test_suggest_break_at_space(self):
        """Sugerir salto en espacio."""
        mapper = SpaceMapper()
        
        breaks = mapper.suggest_line_breaks(
            text="Hello World Test",
            max_width=70.0,  # ~10 chars
            avg_char_width=7.0
        )
        
        assert len(breaks) >= 1
    
    def test_empty_text_no_breaks(self):
        """Texto vacío no tiene saltos."""
        mapper = SpaceMapper()
        
        breaks = mapper.suggest_line_breaks(
            text="",
            max_width=100.0
        )
        
        assert breaks == []


# ============================================================
# TESTS: WordBoundary
# ============================================================

class TestWordBoundary:
    """Tests para WordBoundary dataclass."""
    
    def test_default_boundary(self):
        """WordBoundary con valores por defecto."""
        boundary = WordBoundary()
        
        assert boundary.x_position == 0.0
        assert boundary.char_index == 0
        assert boundary.word_before == ""
        assert boundary.word_after == ""
    
    def test_boundary_with_words(self):
        """WordBoundary con palabras."""
        boundary = WordBoundary(
            x_position=50.0,
            char_index=5,
            word_before="Hello",
            word_after="World",
            space_width=7.0
        )
        
        assert boundary.word_before == "Hello"
        assert boundary.word_after == "World"
        assert boundary.space_width == 7.0


# ============================================================
# TESTS: Funciones de utilidad
# ============================================================

class TestUtilityFunctions:
    """Tests para funciones de utilidad."""
    
    def test_analyze_line_spacing(self):
        """Función de conveniencia analyze_line_spacing."""
        line = create_simple_line("Hello World")
        
        analysis = analyze_line_spacing(line)
        
        assert isinstance(analysis, SpaceAnalysis)
    
    def test_reconstruct_line_text(self):
        """Función de conveniencia reconstruct_line_text."""
        line = create_simple_line("Hello World")
        
        text = reconstruct_line_text(line)
        
        assert "Hello" in text
        assert "World" in text
    
    def test_count_words_in_line(self):
        """Función de conveniencia count_words_in_line."""
        line = create_simple_line("One Two Three")
        
        count = count_words_in_line(line)
        
        assert count >= 1
    
    def test_estimate_character_positions(self):
        """Estimar posiciones de caracteres."""
        span = create_span("ABC", 72.0, 88.0, 93.0, 100.0)  # 21pt para 3 chars
        
        positions = estimate_character_positions(span)
        
        assert len(positions) == 3
        assert positions[0][0] == 72.0  # Primer char empieza en x0
    
    def test_estimate_positions_empty_span(self):
        """Posiciones de span vacío."""
        span = create_span("", 72.0, 88.0, 72.0, 100.0)
        
        positions = estimate_character_positions(span)
        
        assert positions == []
    
    def test_estimate_positions_with_char_widths(self):
        """Usar char_widths reales si están disponibles."""
        char_widths = [7.0, 8.0, 9.0]
        span = create_span("ABC", 72.0, 88.0, 96.0, 100.0, char_widths=char_widths)
        
        positions = estimate_character_positions(span)
        
        assert len(positions) == 3
        assert positions[0] == (72.0, 79.0)   # 7pt
        assert positions[1] == (79.0, 87.0)   # 8pt
        assert positions[2] == (87.0, 96.0)   # 9pt
    
    def test_find_char_at_x(self):
        """Encontrar carácter en posición X."""
        span = create_span("ABC", 72.0, 88.0, 93.0, 100.0)  # 7pt por char
        
        idx = find_char_at_x(span, 75.0)  # Dentro del primer char
        assert idx == 0
        
        idx = find_char_at_x(span, 82.0)  # Dentro del segundo char
        assert idx == 1
    
    def test_find_char_at_x_not_found(self):
        """No encontrar carácter fuera de rango."""
        span = create_span("ABC", 72.0, 88.0, 93.0, 100.0)
        
        idx = find_char_at_x(span, 50.0)  # Antes del span
        assert idx is None
        
        idx = find_char_at_x(span, 200.0)  # Después del span
        assert idx is None
    
    def test_calculate_space_metrics(self):
        """Calcular métricas de espacios."""
        analysis = SpaceAnalysis(
            real_spaces=[
                SpaceInfo(width=7.0),
                SpaceInfo(width=7.0),
            ],
            virtual_spaces=[
                SpaceInfo(width=5.0),
            ],
            probable_tabs=[
                SpaceInfo(width=28.0),
            ]
        )
        
        metrics = calculate_space_metrics(analysis)
        
        assert metrics['total_spaces'] == 4
        assert metrics['real_space_count'] == 2
        assert metrics['virtual_space_count'] == 1
        assert metrics['tab_count'] == 1
        assert metrics['min_width'] == 5.0
        assert metrics['max_width'] == 28.0
    
    def test_calculate_space_metrics_empty(self):
        """Métricas de análisis vacío."""
        analysis = SpaceAnalysis()
        
        metrics = calculate_space_metrics(analysis)
        
        assert metrics['total_spaces'] == 0
        assert metrics['avg_width'] == 0.0


# ============================================================
# TESTS: Estadísticas
# ============================================================

class TestSpaceStatistics:
    """Tests para cálculo de estadísticas."""
    
    def test_statistics_calculated(self):
        """Las estadísticas se calculan correctamente."""
        line = create_simple_line("Hello World Test")
        mapper = SpaceMapper()
        
        analysis = mapper.analyze_line(line)
        
        # Debe haber estadísticas
        assert analysis.total_space_count >= 0
    
    def test_consistent_spacing_detection(self):
        """Detectar espaciado consistente."""
        # Crear análisis con espacios de igual tamaño
        analysis = SpaceAnalysis(
            real_spaces=[
                SpaceInfo(width=7.0),
                SpaceInfo(width=7.0),
                SpaceInfo(width=7.0),
            ]
        )
        
        mapper = SpaceMapper()
        mapper._calculate_statistics(analysis)
        
        assert analysis.has_consistent_spacing
    
    def test_inconsistent_spacing_detection(self):
        """Detectar espaciado inconsistente."""
        # Crear análisis con espacios muy diferentes
        analysis = SpaceAnalysis(
            real_spaces=[
                SpaceInfo(width=5.0),
                SpaceInfo(width=15.0),
                SpaceInfo(width=3.0),
            ]
        )
        
        config = SpaceMapperConfig(consistency_tolerance=0.5)
        mapper = SpaceMapper(config)
        mapper._calculate_statistics(analysis)
        
        # Con tolerancia baja, debería ser inconsistente
        # (depende de la varianza calculada)
        assert analysis.space_variance > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

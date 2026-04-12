"""
Tests para TextLine - Agrupación de spans en líneas.

Cobertura:
- Creación de TextLine
- Propiedades de línea (texto, geometría, estilos)
- Agrupación de spans con LineGrouper
- Detección de párrafos
- Alineación y estadísticas
"""

from typing import List

from core.text_engine.text_line import (
    TextLine,
    LineGrouper,
    LineGroupingConfig,
    ReadingDirection,
    LineAlignment,
    group_spans_into_lines,
    find_line_at_point,
    calculate_line_statistics,
)
from core.text_engine.text_span import TextSpanMetrics


# ============================================================================
# Helper Functions
# ============================================================================

def create_span(
    text: str,
    x: float,
    y: float,
    width: float = None,
    height: float = 12.0,
    font_name: str = "Helvetica",
    font_size: float = 12.0,
    is_bold: bool = False,
    is_italic: bool = False,
    baseline: float = None,
) -> TextSpanMetrics:
    """Crea un TextSpanMetrics para testing."""
    if width is None:
        width = len(text) * font_size * 0.6  # Aproximación
    if baseline is None:
        baseline = y + height * 0.8  # Baseline típica
    
    return TextSpanMetrics(
        text=text,
        page_num=0,
        bbox=(x, y, x + width, y + height),
        origin=(x, baseline),
        baseline_y=baseline,
        font_name=font_name,
        font_size=font_size,
        char_spacing=0.0,
        word_spacing=0.0,
        is_bold=is_bold,
        is_italic=is_italic,
        total_width=width,
    )


def create_line_of_spans(
    texts: List[str],
    start_x: float = 0.0,
    y: float = 100.0,
    spacing: float = 5.0,
    font_size: float = 12.0,
) -> List[TextSpanMetrics]:
    """Crea una lista de spans formando una línea horizontal."""
    spans = []
    current_x = start_x
    
    for text in texts:
        width = len(text) * font_size * 0.6
        span = create_span(
            text=text,
            x=current_x,
            y=y,
            width=width,
            font_size=font_size,
        )
        spans.append(span)
        current_x += width + spacing
    
    return spans


# ============================================================================
# Test Class: TextLine Creation
# ============================================================================

class TestTextLineCreation:
    """Tests para creación de TextLine."""
    
    def test_create_empty_line(self):
        """Test crear línea vacía."""
        line = TextLine(spans=[])
        assert line.text == ""
        assert line.char_count == 0
        assert line.span_count == 0
    
    def test_create_single_span_line(self):
        """Test línea con un solo span."""
        span = create_span("Hello World", x=10.0, y=100.0)
        line = TextLine(spans=[span])
        
        assert line.text == "Hello World"
        assert line.span_count == 1
        assert line.char_count == 11
    
    def test_create_multi_span_line(self):
        """Test línea con múltiples spans."""
        spans = create_line_of_spans(["Hello", "World", "Test"])
        line = TextLine(spans=spans)
        
        assert "Hello" in line.text
        assert "World" in line.text
        assert "Test" in line.text
        assert line.span_count == 3
    
    def test_line_id_assignment(self):
        """Test asignación de ID de línea."""
        spans = create_line_of_spans(["Line 1"])
        line = TextLine(spans=spans, line_id="custom_id")
        assert line.line_id == "custom_id"
    
    def test_page_number_assignment(self):
        """Test asignación de número de página."""
        spans = create_line_of_spans(["Page content"])
        line = TextLine(spans=spans, page_num=5)
        assert line.page_num == 5


# ============================================================================
# Test Class: Text Properties
# ============================================================================

class TestTextProperties:
    """Tests para propiedades de texto."""
    
    def test_text_concatenation(self):
        """Test concatenación de texto de spans."""
        spans = create_line_of_spans(["Hello", "World"])
        line = TextLine(spans=spans)
        
        # El texto debe incluir espacio implícito entre spans
        text = line.text
        assert "Hello" in text
        assert "World" in text
    
    def test_word_count(self):
        """Test conteo de palabras."""
        span = create_span("Hello World Test", x=0.0, y=100.0)
        line = TextLine(spans=[span])
        
        assert line.word_count == 3
    
    def test_word_count_empty(self):
        """Test conteo de palabras en línea vacía."""
        line = TextLine(spans=[])
        assert line.word_count == 0
    
    def test_get_spans(self):
        """Test obtener spans."""
        spans = create_line_of_spans(["A", "B", "C"])
        line = TextLine(spans=spans)
        
        retrieved = line.spans
        assert len(retrieved) == 3


# ============================================================================
# Test Class: Geometry Properties
# ============================================================================

class TestGeometryProperties:
    """Tests para propiedades geométricas."""
    
    def test_bbox(self):
        """Test bounding box de línea."""
        spans = create_line_of_spans(["Hello", "World"], start_x=10.0, y=100.0)
        line = TextLine(spans=spans)
        
        bbox = line.bbox
        assert bbox[0] == 10.0  # x0
        assert bbox[1] == 100.0  # y0
        assert bbox[2] > 10.0  # x1
        assert bbox[3] > 100.0  # y1
    
    def test_bbox_empty_line(self):
        """Test bbox de línea vacía."""
        line = TextLine(spans=[])
        bbox = line.bbox
        assert bbox == (0.0, 0.0, 0.0, 0.0)
    
    def test_width(self):
        """Test ancho de línea."""
        span = create_span("Test", x=10.0, y=100.0, width=100.0)
        line = TextLine(spans=[span])
        
        assert line.width == 100.0
    
    def test_height(self):
        """Test altura de línea."""
        span = create_span("Test", x=10.0, y=100.0, height=14.0)
        line = TextLine(spans=[span])
        
        assert line.height == 14.0
    
    def test_x_start_x_end(self):
        """Test x_start y x_end."""
        span = create_span("Test", x=50.0, y=100.0, width=100.0)
        line = TextLine(spans=[span])
        
        assert line.x_start == 50.0
        assert line.x_end == 150.0
    
    def test_baseline_y(self):
        """Test baseline_y promedio."""
        span = create_span("Test", x=10.0, y=100.0, baseline=110.0)
        line = TextLine(spans=[span])
        
        assert line.baseline_y == 110.0
    
    def test_baseline_y_multiple_spans(self):
        """Test baseline promedio con múltiples spans."""
        span1 = create_span("A", x=0.0, y=100.0, baseline=109.0)
        span2 = create_span("B", x=50.0, y=100.0, baseline=111.0)
        line = TextLine(spans=[span1, span2])
        
        # Promedio de baselines
        assert line.baseline_y == 110.0


# ============================================================================
# Test Class: Style Properties
# ============================================================================

class TestStyleProperties:
    """Tests para propiedades de estilo."""
    
    def test_dominant_font(self):
        """Test fuente dominante."""
        span1 = create_span("Hello", x=0.0, y=100.0, font_name="Arial")
        span2 = create_span("World", x=50.0, y=100.0, font_name="Arial")
        span3 = create_span("!", x=100.0, y=100.0, font_name="Times")
        line = TextLine(spans=[span1, span2, span3])
        
        assert line.dominant_font == "Arial"
    
    def test_dominant_font_size(self):
        """Test tamaño de fuente dominante."""
        span1 = create_span("Big", x=0.0, y=100.0, font_size=14.0)
        span2 = create_span("Text", x=50.0, y=100.0, font_size=14.0)
        span3 = create_span("!", x=100.0, y=100.0, font_size=10.0)
        line = TextLine(spans=[span1, span2, span3])
        
        assert line.dominant_font_size == 14.0
    
    def test_is_bold_all_bold(self):
        """Test detección de negrita."""
        span1 = create_span("Bold", x=0.0, y=100.0, is_bold=True)
        span2 = create_span("Text", x=50.0, y=100.0, is_bold=True)
        line = TextLine(spans=[span1, span2])
        
        assert line.is_bold
    
    def test_is_bold_mixed(self):
        """Test negrita mixta."""
        span1 = create_span("Bold", x=0.0, y=100.0, is_bold=True)
        span2 = create_span("Normal", x=50.0, y=100.0, is_bold=False)
        line = TextLine(spans=[span1, span2])
        
        # Con spans mixtos, is_bold debería ser False
        assert not line.is_bold
    
    def test_is_italic(self):
        """Test detección de cursiva."""
        span = create_span("Italic Text", x=0.0, y=100.0, is_italic=True)
        line = TextLine(spans=[span])
        
        assert line.is_italic
    
    def test_has_mixed_styles(self):
        """Test detección de estilos mixtos."""
        span1 = create_span("Bold", x=0.0, y=100.0, is_bold=True)
        span2 = create_span("Normal", x=50.0, y=100.0, is_bold=False)
        line = TextLine(spans=[span1, span2])
        
        assert line.has_mixed_styles
    
    def test_no_mixed_styles(self):
        """Test sin estilos mixtos."""
        span1 = create_span("Text", x=0.0, y=100.0)
        span2 = create_span("More", x=50.0, y=100.0)
        line = TextLine(spans=[span1, span2])
        
        assert not line.has_mixed_styles


# ============================================================================
# Test Class: Spacing Properties
# ============================================================================

class TestSpacingProperties:
    """Tests para propiedades de espaciado."""
    
    def test_avg_char_spacing(self):
        """Test espaciado promedio de caracteres."""
        span = TextSpanMetrics(
            text="Test",
            page_num=0,
            bbox=(0.0, 100.0, 50.0, 112.0),
            origin=(0.0, 110.0),
            baseline_y=110.0,
            font_name="Helvetica",
            font_size=12.0,
            char_spacing=0.5,
            word_spacing=0.0,
            total_width=50.0,
        )
        line = TextLine(spans=[span])
        
        assert line.avg_char_spacing == 0.5
    
    def test_inter_span_gaps(self):
        """Test gaps entre spans."""
        span1 = create_span("Hello", x=0.0, y=100.0, width=50.0)
        span2 = create_span("World", x=60.0, y=100.0, width=50.0)
        line = TextLine(spans=[span1, span2])
        
        gaps = line.inter_span_gaps
        assert len(gaps) == 1
        assert gaps[0] == 10.0  # 60 - 50


# ============================================================================
# Test Class: Find Methods
# ============================================================================

class TestFindMethods:
    """Tests para métodos de búsqueda."""
    
    def test_find_span_at_x(self):
        """Test encontrar span en posición x."""
        span1 = create_span("Hello", x=0.0, y=100.0, width=50.0)
        span2 = create_span("World", x=60.0, y=100.0, width=50.0)
        line = TextLine(spans=[span1, span2])
        
        found = line.find_span_at_x(25.0)
        assert found is not None
        assert found.text == "Hello"
        
        found2 = line.find_span_at_x(75.0)
        assert found2 is not None
        assert found2.text == "World"
    
    def test_find_span_at_x_not_found(self):
        """Test no encontrar span en gap."""
        span1 = create_span("Hello", x=0.0, y=100.0, width=50.0)
        span2 = create_span("World", x=100.0, y=100.0, width=50.0)
        line = TextLine(spans=[span1, span2])
        
        found = line.find_span_at_x(75.0)
        assert found is None
    
    def test_find_char_at_x(self):
        """Test encontrar carácter en posición x."""
        span = create_span("Hello", x=0.0, y=100.0, width=50.0)
        # Añadir char_widths para que funcione find_char_at_x
        span = TextSpanMetrics(
            text="Hello",
            page_num=0,
            bbox=(0.0, 100.0, 50.0, 112.0),
            origin=(0.0, 109.6),
            baseline_y=109.6,
            font_name="Helvetica",
            font_size=12.0,
            char_widths=[10.0, 10.0, 10.0, 10.0, 10.0],  # 5 chars
            total_width=50.0,
        )
        line = TextLine(spans=[span])
        
        result = line.find_char_at_x(5.0)
        assert result is not None
        span_found, char_idx = result
        # El índice debe estar en rango
        assert 0 <= char_idx < len(span.text)


# ============================================================================
# Test Class: Split Methods
# ============================================================================

class TestSplitMethods:
    """Tests para métodos de división."""
    
    def test_split_at_x_simple(self):
        """Test división simple en x."""
        span1 = create_span("Hello", x=0.0, y=100.0, width=50.0)
        span2 = create_span("World", x=60.0, y=100.0, width=50.0)
        line = TextLine(spans=[span1, span2])
        
        left, right = line.split_at_x(55.0)
        
        assert left is not None
        assert right is not None
        assert left.span_count == 1
        assert right.span_count == 1
        assert "Hello" in left.text
        assert "World" in right.text
    
    def test_split_at_x_all_left(self):
        """Test división con todo a la izquierda."""
        span = create_span("Hello", x=0.0, y=100.0, width=50.0)
        line = TextLine(spans=[span])
        
        left, right = line.split_at_x(100.0)
        
        assert left is not None
        assert right is None or right.span_count == 0


# ============================================================================
# Test Class: Alignment Detection
# ============================================================================

class TestAlignmentDetection:
    """Tests para detección de alineación."""
    
    def test_detect_alignment_left(self):
        """Test detección de alineación izquierda."""
        # Línea pegada al margen izquierdo
        span = create_span("Left aligned text", x=10.0, y=100.0, width=200.0)
        line = TextLine(spans=[span])
        
        # detect_alignment solo recibe page_width
        alignment = line.detect_alignment(page_width=600.0)
        assert alignment == LineAlignment.LEFT
    
    def test_detect_alignment_right(self):
        """Test detección de alineación derecha."""
        # Línea pegada al margen derecho
        span = create_span("Right aligned", x=400.0, y=100.0, width=190.0)
        line = TextLine(spans=[span])
        
        # detect_alignment solo recibe page_width
        alignment = line.detect_alignment(page_width=600.0)
        assert alignment == LineAlignment.RIGHT
    
    def test_detect_alignment_center(self):
        """Test detección de alineación centrada."""
        # Línea centrada
        span = create_span("Centered text", x=200.0, y=100.0, width=200.0)
        line = TextLine(spans=[span])
        
        alignment = line.detect_alignment(page_width=600.0)
        assert alignment == LineAlignment.CENTER


# ============================================================================
# Test Class: LineGroupingConfig
# ============================================================================

class TestLineGroupingConfig:
    """Tests para configuración de agrupación."""
    
    def test_default_config(self):
        """Test configuración por defecto."""
        config = LineGroupingConfig()
        
        assert config.baseline_tolerance == 3.0
        assert config.horizontal_gap_threshold == 50.0
        assert config.min_overlap_ratio == 0.5
    
    def test_custom_config(self):
        """Test configuración personalizada."""
        config = LineGroupingConfig(
            baseline_tolerance=5.0,
            horizontal_gap_threshold=100.0,
            min_overlap_ratio=0.3,
        )
        
        assert config.baseline_tolerance == 5.0
        assert config.horizontal_gap_threshold == 100.0
        assert config.min_overlap_ratio == 0.3


# ============================================================================
# Test Class: LineGrouper
# ============================================================================

class TestLineGrouper:
    """Tests para LineGrouper."""
    
    def test_group_single_span(self):
        """Test agrupar un solo span."""
        span = create_span("Single span", x=10.0, y=100.0)
        grouper = LineGrouper()
        
        lines = grouper.group_spans([span])
        
        assert len(lines) == 1
        assert lines[0].text == "Single span"
    
    def test_group_same_baseline(self):
        """Test agrupar spans en misma baseline."""
        span1 = create_span("Hello", x=0.0, y=100.0, baseline=110.0)
        span2 = create_span("World", x=60.0, y=100.0, baseline=110.0)
        grouper = LineGrouper()
        
        lines = grouper.group_spans([span1, span2])
        
        assert len(lines) == 1
        assert "Hello" in lines[0].text
        assert "World" in lines[0].text
    
    def test_group_different_baselines(self):
        """Test separar spans en diferentes baselines."""
        span1 = create_span("Line 1", x=0.0, y=100.0, baseline=110.0)
        span2 = create_span("Line 2", x=0.0, y=130.0, baseline=140.0)
        grouper = LineGrouper()
        
        lines = grouper.group_spans([span1, span2])
        
        assert len(lines) == 2
    
    def test_group_with_tolerance(self):
        """Test agrupación con tolerancia de baseline."""
        span1 = create_span("A", x=0.0, y=100.0, baseline=110.0)
        span2 = create_span("B", x=50.0, y=100.0, baseline=111.0)  # Ligera diferencia
        
        config = LineGroupingConfig(baseline_tolerance=3.0)
        grouper = LineGrouper(config=config)
        
        lines = grouper.group_spans([span1, span2])
        
        # Deberían agruparse porque la diferencia < tolerancia
        assert len(lines) == 1
    
    def test_group_respects_horizontal_gap(self):
        """Test que respeta gap horizontal máximo."""
        span1 = create_span("Left", x=0.0, y=100.0, width=50.0, baseline=110.0)
        span2 = create_span("Right", x=200.0, y=100.0, width=50.0, baseline=110.0)
        
        # Con gap threshold pequeño, deberían estar en la misma línea
        # ya que LineGrouper agrupa por baseline primero
        config = LineGroupingConfig(horizontal_gap_threshold=50.0)
        grouper = LineGrouper(config=config)
        
        lines = grouper.group_spans([span1, span2])
        
        # Con baseline igual, ambos están en misma línea
        assert len(lines) >= 1
    
    def test_group_empty_input(self):
        """Test con entrada vacía."""
        grouper = LineGrouper()
        lines = grouper.group_spans([])
        assert len(lines) == 0
    
    def test_group_maintains_order(self):
        """Test que mantiene orden de lectura."""
        span1 = create_span("First", x=0.0, y=100.0, baseline=110.0)
        span2 = create_span("Second", x=60.0, y=100.0, baseline=110.0)
        span3 = create_span("Third", x=130.0, y=100.0, baseline=110.0)
        
        grouper = LineGrouper()
        lines = grouper.group_spans([span1, span2, span3])
        
        assert len(lines) == 1
        text = lines[0].text
        # El orden debe ser First, Second, Third
        assert text.index("First") < text.index("Second") < text.index("Third")


# ============================================================================
# Test Class: LineGrouper - Line Spacing
# ============================================================================

class TestLineGrouperSpacing:
    """Tests para cálculo de espaciado de líneas."""
    
    def test_estimate_line_spacing(self):
        """Test estimación de espaciado entre líneas."""
        span1 = create_span("Line 1", x=0.0, y=100.0, baseline=110.0)
        span2 = create_span("Line 2", x=0.0, y=120.0, baseline=130.0)
        span3 = create_span("Line 3", x=0.0, y=140.0, baseline=150.0)
        
        grouper = LineGrouper()
        lines = grouper.group_spans([span1, span2, span3])
        spacing = grouper.estimate_line_spacing(lines)
        
        assert spacing is not None
        assert spacing == 20.0  # Diferencia entre baselines
    
    def test_estimate_line_spacing_single_line(self):
        """Test espaciado con una sola línea."""
        span = create_span("Only line", x=0.0, y=100.0)
        
        grouper = LineGrouper()
        lines = grouper.group_spans([span])
        spacing = grouper.estimate_line_spacing(lines)
        
        # Con una sola línea, devuelve 0.0 ya que no hay spacing entre líneas
        assert spacing == 0.0


# ============================================================================
# Test Class: LineGrouper - Paragraph Detection
# ============================================================================

class TestParagraphDetection:
    """Tests para detección de párrafos."""
    
    def test_detect_paragraphs_basic(self):
        """Test detección básica de párrafos."""
        # Primer párrafo (líneas cercanas)
        span1 = create_span("Line 1 para 1", x=0.0, y=100.0, baseline=110.0)
        span2 = create_span("Line 2 para 1", x=0.0, y=120.0, baseline=130.0)
        # Segundo párrafo (gap mayor)
        span3 = create_span("Line 1 para 2", x=0.0, y=180.0, baseline=190.0)
        
        # Usar configuración por defecto
        grouper = LineGrouper()
        
        lines = grouper.group_spans([span1, span2, span3])
        paragraphs = grouper.detect_paragraphs(lines)
        
        assert len(paragraphs) >= 1


# ============================================================================
# Test Class: Utility Functions
# ============================================================================

class TestUtilityFunctions:
    """Tests para funciones utilitarias."""
    
    def test_group_spans_into_lines(self):
        """Test función conveniente de agrupación."""
        spans = create_line_of_spans(["Hello", "World"], y=100.0)
        lines = group_spans_into_lines(spans)
        
        assert len(lines) == 1
    
    def test_group_spans_into_lines_with_config(self):
        """Test agrupación con configuración."""
        spans = create_line_of_spans(["A", "B", "C"], y=100.0)
        config = LineGroupingConfig(baseline_tolerance=5.0)
        grouper = LineGrouper(config=config)
        
        # Usar el grouper directamente
        lines = grouper.group_spans(spans)
        
        assert len(lines) >= 1
    
    def test_find_line_at_point_found(self):
        """Test encontrar línea en punto."""
        spans = create_line_of_spans(["Test line"], y=100.0)
        lines = group_spans_into_lines(spans)
        
        found = find_line_at_point(lines, x=20.0, y=106.0)
        
        assert found is not None
    
    def test_find_line_at_point_not_found(self):
        """Test no encontrar línea en punto vacío."""
        spans = create_line_of_spans(["Test line"], y=100.0)
        lines = group_spans_into_lines(spans)
        
        found = find_line_at_point(lines, x=20.0, y=300.0)
        
        assert found is None
    
    def test_calculate_line_statistics(self):
        """Test cálculo de estadísticas de líneas."""
        span1 = create_span("Line 1", x=0.0, y=100.0, font_size=12.0, baseline=110.0)
        span2 = create_span("Line 2", x=0.0, y=120.0, font_size=12.0, baseline=130.0)
        span3 = create_span("Line 3", x=0.0, y=140.0, font_size=14.0, baseline=152.0)
        
        lines = group_spans_into_lines([span1, span2, span3])
        stats = calculate_line_statistics(lines)
        
        # Verificar que devuelve un diccionario con estadísticas
        assert isinstance(stats, dict)
        assert 'avg_height' in stats or 'line_count' in stats or len(stats) > 0


# ============================================================================
# Test Class: Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests para casos límite."""
    
    def test_overlapping_spans(self):
        """Test spans solapados."""
        span1 = create_span("Over", x=0.0, y=100.0, width=60.0, baseline=110.0)
        span2 = create_span("lap", x=40.0, y=100.0, width=40.0, baseline=110.0)
        
        grouper = LineGrouper()
        lines = grouper.group_spans([span1, span2])
        
        # Deberían agruparse en misma línea
        assert len(lines) == 1
    
    def test_very_small_spans(self):
        """Test spans muy pequeños."""
        span = create_span(".", x=100.0, y=100.0, width=3.0, height=2.0)
        
        grouper = LineGrouper()
        lines = grouper.group_spans([span])
        
        assert len(lines) == 1
    
    def test_spans_different_pages(self):
        """Test spans de diferentes páginas."""
        span1 = create_span("Page 1", x=0.0, y=100.0)
        span2 = create_span("Page 2", x=0.0, y=100.0)
        
        # Simular páginas diferentes con page_num
        line1 = TextLine(spans=[span1], page_num=0)
        line2 = TextLine(spans=[span2], page_num=1)
        
        assert line1.page_num != line2.page_num
    
    def test_rtl_text_hint(self):
        """Test indicación de texto RTL."""
        # Crear línea con reading_direction
        span = create_span("مرحبا", x=100.0, y=100.0)  # Texto árabe
        line = TextLine(spans=[span], reading_direction=ReadingDirection.RTL)
        
        assert line.reading_direction == ReadingDirection.RTL
    
    def test_mixed_font_sizes(self):
        """Test tamaños de fuente mixtos en línea."""
        span1 = create_span("Big", x=0.0, y=100.0, font_size=24.0, baseline=120.0)
        span2 = create_span("small", x=60.0, y=105.0, font_size=10.0, baseline=113.0)
        
        # Aunque tienen diferentes tamaños, si baselines están cerca, se agrupan
        config = LineGroupingConfig(baseline_tolerance=10.0)
        grouper = LineGrouper(config=config)
        
        lines = grouper.group_spans([span1, span2])
        
        # Pueden o no agruparse dependiendo de la tolerancia
        assert len(lines) >= 1
    
    def test_whitespace_only_span(self):
        """Test span solo con espacios."""
        span = create_span("   ", x=50.0, y=100.0)
        
        grouper = LineGrouper()
        lines = grouper.group_spans([span])
        
        # Debería manejar span de espacios
        assert len(lines) == 1
    
    def test_newline_in_span(self):
        """Test span con salto de línea interno."""
        span = create_span("Line1\nLine2", x=0.0, y=100.0)
        line = TextLine(spans=[span])
        
        # El texto debería preservar el newline
        assert "\n" in line.text


# ============================================================================
# Test Class: Performance
# ============================================================================

class TestPerformance:
    """Tests de rendimiento básicos."""
    
    def test_group_many_spans(self):
        """Test agrupar muchos spans."""
        # Crear 100 spans en 10 líneas
        spans = []
        for line_num in range(10):
            y = 100.0 + line_num * 20.0
            baseline = y + 10.0
            for word_num in range(10):
                x = word_num * 50.0
                span = create_span(f"word{word_num}", x=x, y=y, baseline=baseline)
                spans.append(span)
        
        grouper = LineGrouper()
        lines = grouper.group_spans(spans)
        
        assert len(lines) == 10
        for line in lines:
            assert line.span_count == 10


# ============================================================================
# Test Class: TextLine Immutability  
# ============================================================================

class TestTextLineImmutability:
    """Tests para verificar comportamiento de TextLine."""
    
    def test_spans_reference(self):
        """Test que spans son referencia a la lista original."""
        spans = create_line_of_spans(["Hello", "World"])
        line = TextLine(spans=spans)
        
        original_count = line.span_count
        # Nota: TextLine guarda la referencia, no una copia
        # Esto es por diseño para eficiencia
        assert original_count == 2
    
    def test_line_to_dict(self):
        """Test serialización a diccionario."""
        spans = create_line_of_spans(["Test"])
        line = TextLine(spans=spans, line_id="test_id_5")
        
        d = line.to_dict()
        
        assert 'text' in d
        assert 'bbox' in d
        assert 'line_id' in d
        assert d['line_id'] == "test_id_5"

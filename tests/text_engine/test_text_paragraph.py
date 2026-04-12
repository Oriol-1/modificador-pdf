"""
Tests para TextParagraph - Agrupación de líneas en párrafos.

Cobertura:
1. TextParagraph - propiedades básicas
2. TextParagraph - propiedades geométricas
3. TextParagraph - detección de estilos
4. ParagraphDetector - agrupación de líneas
5. ParagraphDetector - detección de tipos
6. Funciones de utilidad
"""

import pytest
from typing import List

# Import del módulo a testear
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.text_engine.text_paragraph import (
    TextParagraph,
    ParagraphType,
    ParagraphAlignment,
    ListType,
    ListMarkerInfo,
    ParagraphStyle,
    ParagraphDetectionConfig,
    ParagraphDetector,
    group_lines_into_paragraphs,
    find_paragraph_at_point,
    find_paragraphs_in_region,
    calculate_paragraph_statistics,
    merge_paragraphs,
    split_paragraph_at_line,
)
from core.text_engine.text_line import TextLine, LineAlignment
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
    is_bold: bool = False,
    is_italic: bool = False
) -> TextSpanMetrics:
    """Crea un TextSpanMetrics para testing."""
    return TextSpanMetrics(
        text=text,
        page_num=0,
        bbox=(x0, y0, x1, y1),
        baseline_y=y1 - size * 0.2,
        font_name=font,
        font_size=size,
        font_flags=1 if is_bold else 0,
        char_spacing=0.0,
        word_spacing=0.0,
        rise=0.0,
        ctm=(1.0, 0.0, 0.0, 1.0, x0, y0),
        char_widths=[],
        is_bold=is_bold,
        is_italic=is_italic,
    )


def create_line(
    text: str,
    y_baseline: float,
    x_start: float = 72.0,
    font: str = "Helvetica",
    size: float = 12.0,
    is_bold: bool = False,
    page_num: int = 0
) -> TextLine:
    """Crea una TextLine para testing."""
    char_width = size * 0.6
    width = len(text) * char_width
    
    span = create_span(
        text=text,
        x0=x_start,
        y0=y_baseline - size,
        x1=x_start + width,
        y1=y_baseline,
        font=font if not is_bold else f"{font}-Bold",
        size=size,
        is_bold=is_bold
    )
    
    return TextLine(
        spans=[span],
        page_num=page_num,
        baseline_y=y_baseline
    )


def create_multiline_paragraph(
    texts: List[str],
    start_y: float = 100.0,
    line_spacing: float = 14.0,
    x_start: float = 72.0,
    font_size: float = 12.0,
    page_num: int = 0
) -> TextParagraph:
    """Crea un párrafo con múltiples líneas."""
    lines = []
    y = start_y
    
    for text in texts:
        line = create_line(
            text=text,
            y_baseline=y,
            x_start=x_start,
            size=font_size,
            page_num=page_num
        )
        lines.append(line)
        y += line_spacing
    
    return TextParagraph(lines=lines, page_num=page_num)


# ============================================================
# TESTS: TextParagraph - Propiedades Básicas
# ============================================================

class TestTextParagraphBasics:
    """Tests para propiedades básicas de TextParagraph."""
    
    def test_empty_paragraph(self):
        """Párrafo vacío tiene valores por defecto."""
        para = TextParagraph()
        
        assert para.text == ""
        assert para.line_count == 0
        assert para.char_count == 0
        assert para.word_count == 0
        assert para.bbox == (0.0, 0.0, 0.0, 0.0)
    
    def test_single_line_paragraph(self):
        """Párrafo con una sola línea."""
        line = create_line("Hello World", y_baseline=100.0)
        para = TextParagraph(lines=[line])
        
        assert para.text == "Hello World"
        assert para.line_count == 1
        assert para.word_count == 2
        assert para.char_count == 11
    
    def test_multi_line_paragraph(self):
        """Párrafo con múltiples líneas."""
        para = create_multiline_paragraph([
            "Primera línea",
            "Segunda línea",
            "Tercera línea"
        ])
        
        assert para.line_count == 3
        assert "Primera" in para.text
        assert "Segunda" in para.text
        assert "Tercera" in para.text
    
    def test_text_without_breaks(self):
        """Texto sin saltos de línea para búsqueda."""
        para = create_multiline_paragraph([
            "Hello",
            "World"
        ])
        
        assert para.text_without_breaks == "Hello World"
    
    def test_get_full_text_method(self):
        """Método get_full_text() para compatibilidad PORM."""
        para = create_multiline_paragraph(["Test", "Line"])
        
        assert para.get_full_text() == para.text
        assert para.full_text == para.text
    
    def test_paragraph_id_generation(self):
        """Se genera ID único automáticamente."""
        para = create_multiline_paragraph(["Test"])
        
        assert para.paragraph_id != ""
        assert len(para.paragraph_id) == 8  # MD5 truncado
    
    def test_span_count(self):
        """Cuenta total de spans en el párrafo."""
        line1 = create_line("Part one", y_baseline=100.0)
        line2 = create_line("Part two", y_baseline=114.0)
        
        para = TextParagraph(lines=[line1, line2])
        
        assert para.span_count == 2
    
    def test_lines_sorted_by_y(self):
        """Las líneas se ordenan por posición Y."""
        line_bottom = create_line("Bottom", y_baseline=200.0)
        line_top = create_line("Top", y_baseline=100.0)
        
        # Insertar en orden inverso
        para = TextParagraph(lines=[line_bottom, line_top])
        
        # Deben estar ordenadas de arriba a abajo
        assert para.lines[0].text == "Top"
        assert para.lines[1].text == "Bottom"


# ============================================================
# TESTS: TextParagraph - Propiedades Geométricas
# ============================================================

class TestTextParagraphGeometry:
    """Tests para propiedades geométricas."""
    
    def test_bbox_calculation(self):
        """Bounding box combinado de todas las líneas."""
        para = create_multiline_paragraph([
            "Short",
            "Much longer line here"
        ], x_start=72.0)
        
        bbox = para.bbox
        assert bbox[0] == 72.0  # x_start
        assert bbox[1] > 0      # y_start
        assert bbox[2] > 72.0   # x_end
        assert bbox[3] > bbox[1]  # y_end > y_start
    
    def test_width_and_height(self):
        """Ancho y alto del párrafo."""
        para = create_multiline_paragraph([
            "Line one",
            "Line two"
        ], line_spacing=14.0)
        
        assert para.width > 0
        assert para.height > 0
    
    def test_x_start_and_x_end(self):
        """Posiciones X inicial y final."""
        para = create_multiline_paragraph(["Test"], x_start=100.0)
        
        assert para.x_start == 100.0
        assert para.x_end > para.x_start
    
    def test_y_start_and_y_end(self):
        """Posiciones Y inicial y final."""
        para = create_multiline_paragraph(["Line1", "Line2"], start_y=100.0)
        
        assert para.y_start > 0
        assert para.y_end > para.y_start


# ============================================================
# TESTS: TextParagraph - Sangría e Interlineado
# ============================================================

class TestTextParagraphIndentation:
    """Tests para sangría e interlineado."""
    
    def test_no_indent_single_line(self):
        """Párrafo de una línea no tiene sangría."""
        para = create_multiline_paragraph(["Single line"])
        
        assert para.first_line_indent == 0.0
    
    def test_first_line_indent_positive(self):
        """Sangría positiva de primera línea."""
        line1 = create_line("Indented first line", y_baseline=100.0, x_start=90.0)
        line2 = create_line("Normal line", y_baseline=114.0, x_start=72.0)
        line3 = create_line("Another normal", y_baseline=128.0, x_start=72.0)
        
        para = TextParagraph(lines=[line1, line2, line3])
        
        # Primera línea 18pt más a la derecha
        assert para.first_line_indent > 0
        assert abs(para.first_line_indent - 18.0) < 1.0
    
    def test_first_line_indent_negative(self):
        """Sangría francesa (negativa)."""
        line1 = create_line("Hanging line", y_baseline=100.0, x_start=72.0)
        line2 = create_line("Indented continuation", y_baseline=114.0, x_start=90.0)
        line3 = create_line("More continuation", y_baseline=128.0, x_start=90.0)
        
        para = TextParagraph(lines=[line1, line2, line3])
        
        # Primera línea 18pt más a la izquierda que el resto
        assert para.first_line_indent < 0
    
    def test_line_spacing(self):
        """Cálculo de interlineado."""
        para = create_multiline_paragraph(
            ["Line 1", "Line 2", "Line 3"],
            line_spacing=16.0
        )
        
        # El interlineado debe ser cercano a 16pt
        assert abs(para.line_spacing - 16.0) < 1.0
    
    def test_line_spacing_single_line(self):
        """Interlineado de párrafo de una línea es 0."""
        para = create_multiline_paragraph(["Only one"])
        
        assert para.line_spacing == 0.0
    
    def test_line_spacing_mode_fixed(self):
        """Detección de interlineado fijo."""
        para = create_multiline_paragraph(
            ["Line 1", "Line 2", "Line 3", "Line 4"],
            line_spacing=14.0  # Constante
        )
        
        assert para.line_spacing_mode in ("fixed", "auto")
    
    def test_baseline_grid(self):
        """Cálculo de grid de baselines."""
        para = create_multiline_paragraph(
            ["L1", "L2", "L3"],
            start_y=100.0,
            line_spacing=14.0
        )
        
        grid = para.calculate_baseline_grid()
        
        assert len(grid) == 3
        assert grid[0] == 100.0
        assert abs(grid[1] - 114.0) < 1.0
        assert abs(grid[2] - 128.0) < 1.0


# ============================================================
# TESTS: TextParagraph - Estilos Dominantes
# ============================================================

class TestTextParagraphStyles:
    """Tests para detección de estilos."""
    
    def test_dominant_font(self):
        """Fuente más común en el párrafo."""
        line1 = create_line("Regular text", y_baseline=100.0, font="Helvetica")
        line2 = create_line("More regular", y_baseline=114.0, font="Helvetica")
        
        para = TextParagraph(lines=[line1, line2])
        
        assert "Helvetica" in para.dominant_font
    
    def test_dominant_font_size(self):
        """Tamaño de fuente más común."""
        para = create_multiline_paragraph(
            ["Line 1", "Line 2"],
            font_size=14.0
        )
        
        assert abs(para.dominant_font_size - 14.0) < 1.0
    
    def test_is_bold(self):
        """Detección de párrafo en negrita."""
        line1 = create_line("Bold text", y_baseline=100.0, is_bold=True)
        line2 = create_line("More bold", y_baseline=114.0, is_bold=True)
        
        para = TextParagraph(lines=[line1, line2])
        
        assert para.is_bold
    
    def test_is_not_bold(self):
        """Párrafo regular no es negrita."""
        para = create_multiline_paragraph(["Regular", "Text"])
        
        assert not para.is_bold
    
    def test_dominant_alignment(self):
        """Alineación dominante del párrafo."""
        para = create_multiline_paragraph(["Test text"])
        
        # Por defecto debería detectarse alguna alineación
        assert para.dominant_alignment in list(ParagraphAlignment)
    
    def test_get_style(self):
        """Obtención de estilo completo."""
        para = create_multiline_paragraph(["Test"], font_size=14.0)
        style = para.get_style()
        
        assert isinstance(style, ParagraphStyle)
        assert abs(style.font_size - 14.0) < 1.0


# ============================================================
# TESTS: TextParagraph - Tipos de Párrafo
# ============================================================

class TestTextParagraphTypes:
    """Tests para tipos de párrafo."""
    
    def test_default_type_is_normal(self):
        """Tipo por defecto es NORMAL."""
        para = create_multiline_paragraph(["Regular text"])
        
        assert para.paragraph_type == ParagraphType.NORMAL
    
    def test_is_heading_property(self):
        """Propiedad is_heading."""
        para = TextParagraph(
            lines=[create_line("Title", y_baseline=100.0)],
            paragraph_type=ParagraphType.HEADING
        )
        
        assert para.is_heading
    
    def test_is_not_heading(self):
        """Párrafo normal no es heading."""
        para = create_multiline_paragraph(["Normal paragraph"])
        
        assert not para.is_heading
    
    def test_is_list_item_property(self):
        """Propiedad is_list_item."""
        para = TextParagraph(
            lines=[create_line("• Item", y_baseline=100.0)],
            paragraph_type=ParagraphType.LIST_ITEM,
            list_info=ListMarkerInfo(
                list_type=ListType.BULLET,
                marker="•"
            )
        )
        
        assert para.is_list_item
        assert para.list_marker == "•"
    
    def test_heading_level(self):
        """Nivel de encabezado."""
        para = TextParagraph(
            lines=[create_line("H1", y_baseline=100.0)],
            paragraph_type=ParagraphType.HEADING,
            heading_level=1
        )
        
        assert para.heading_level == 1


# ============================================================
# TESTS: ParagraphDetector - Agrupación
# ============================================================

class TestParagraphDetectorGrouping:
    """Tests para agrupación de líneas en párrafos."""
    
    def test_single_line_single_paragraph(self):
        """Una línea = un párrafo."""
        line = create_line("Only line", y_baseline=100.0)
        
        detector = ParagraphDetector()
        paragraphs = detector.detect_paragraphs([line])
        
        assert len(paragraphs) == 1
        assert paragraphs[0].line_count == 1
    
    def test_consecutive_lines_same_paragraph(self):
        """Líneas consecutivas forman un párrafo."""
        lines = [
            create_line("Line 1", y_baseline=100.0),
            create_line("Line 2", y_baseline=114.0),
            create_line("Line 3", y_baseline=128.0),
        ]
        
        detector = ParagraphDetector()
        paragraphs = detector.detect_paragraphs(lines)
        
        assert len(paragraphs) == 1
        assert paragraphs[0].line_count == 3
    
    def test_gap_creates_new_paragraph(self):
        """Gap grande crea nuevo párrafo."""
        lines = [
            create_line("First para", y_baseline=100.0),
            create_line("Still first", y_baseline=114.0),
            # Gran gap aquí
            create_line("Second para", y_baseline=180.0),  # Gap > threshold
        ]
        
        config = ParagraphDetectionConfig(paragraph_gap_threshold=1.5)
        detector = ParagraphDetector(config)
        paragraphs = detector.detect_paragraphs(lines)
        
        assert len(paragraphs) == 2
    
    def test_empty_lines_returns_empty(self):
        """Lista vacía retorna lista vacía."""
        detector = ParagraphDetector()
        paragraphs = detector.detect_paragraphs([])
        
        assert paragraphs == []
    
    def test_preserves_page_num(self):
        """Se preserva el número de página."""
        line = create_line("Test", y_baseline=100.0, page_num=5)
        
        detector = ParagraphDetector()
        paragraphs = detector.detect_paragraphs([line], page_num=5)
        
        assert paragraphs[0].page_num == 5


# ============================================================
# TESTS: ParagraphDetector - Detección de Tipos
# ============================================================

class TestParagraphDetectorTypes:
    """Tests para detección de tipos de párrafo."""
    
    def test_detect_heading_by_size(self):
        """Detecta encabezado por tamaño de fuente."""
        lines = [
            create_line("Big Title", y_baseline=100.0, size=24.0),  # Grande
            create_line("Normal text", y_baseline=140.0, size=12.0),
            create_line("More normal", y_baseline=154.0, size=12.0),
        ]
        
        detector = ParagraphDetector()
        paragraphs = detector.detect_paragraphs(lines)
        
        # El título grande debe detectarse como heading
        assert paragraphs[0].paragraph_type == ParagraphType.HEADING
    
    def test_detect_heading_by_bold(self):
        """Detecta encabezado por negrita y brevedad."""
        lines = [
            create_line("Section", y_baseline=100.0, is_bold=True, size=12.0),
            create_line("Normal text here that is longer", y_baseline=150.0, size=12.0),
        ]
        
        config = ParagraphDetectionConfig(paragraph_gap_threshold=1.5)
        detector = ParagraphDetector(config)
        paragraphs = detector.detect_paragraphs(lines)
        
        # "Section" (bold y corto) puede detectarse como heading
        assert len(paragraphs) >= 1
    
    def test_detect_bullet_list(self):
        """Detecta lista con viñetas."""
        lines = [
            create_line("• First item", y_baseline=100.0),
            create_line("• Second item", y_baseline=114.0),
        ]
        
        detector = ParagraphDetector()
        paragraphs = detector.detect_paragraphs(lines)
        
        assert paragraphs[0].paragraph_type == ParagraphType.LIST_ITEM
        assert paragraphs[0].list_info.list_type == ListType.BULLET
    
    def test_detect_numbered_list(self):
        """Detecta lista numerada."""
        line = create_line("1. First point", y_baseline=100.0)
        
        detector = ParagraphDetector()
        paragraphs = detector.detect_paragraphs([line])
        
        assert paragraphs[0].paragraph_type == ParagraphType.LIST_ITEM
        assert paragraphs[0].list_info.list_type == ListType.NUMBERED
    
    def test_detect_lettered_list(self):
        """Detecta lista con letras."""
        line = create_line("a. Option A", y_baseline=100.0)
        
        detector = ParagraphDetector()
        paragraphs = detector.detect_paragraphs([line])
        
        assert paragraphs[0].paragraph_type == ParagraphType.LIST_ITEM
        assert paragraphs[0].list_info.list_type == ListType.LETTERED
    
    def test_detect_code_by_font(self):
        """Detecta código por fuente monoespaciada."""
        line = create_line("print('hello')", y_baseline=100.0, font="Courier")
        
        detector = ParagraphDetector()
        paragraphs = detector.detect_paragraphs([line])
        
        assert paragraphs[0].paragraph_type == ParagraphType.CODE


# ============================================================
# TESTS: ListMarkerInfo
# ============================================================

class TestListMarkerInfo:
    """Tests para ListMarkerInfo."""
    
    def test_default_not_list(self):
        """Por defecto no es lista."""
        info = ListMarkerInfo()
        
        assert not info.is_list
        assert info.list_type == ListType.NONE
        assert info.marker == ""
    
    def test_bullet_list_info(self):
        """Info de lista con viñetas."""
        info = ListMarkerInfo(
            list_type=ListType.BULLET,
            marker="•",
            level=0
        )
        
        assert info.is_list
        assert info.marker == "•"
        assert info.level == 0
    
    def test_numbered_with_sequence(self):
        """Lista numerada con número de secuencia."""
        info = ListMarkerInfo(
            list_type=ListType.NUMBERED,
            marker="3.",
            sequence_num=3
        )
        
        assert info.is_list
        assert info.sequence_num == 3


# ============================================================
# TESTS: ParagraphStyle
# ============================================================

class TestParagraphStyle:
    """Tests para ParagraphStyle."""
    
    def test_default_style(self):
        """Estilo por defecto."""
        style = ParagraphStyle()
        
        assert style.font_name == ""
        assert style.font_size == 0.0
        assert not style.is_bold
        assert not style.is_italic
        assert style.alignment == ParagraphAlignment.LEFT
    
    def test_is_similar_to_same(self):
        """Estilos idénticos son similares."""
        style1 = ParagraphStyle(font_name="Helvetica", font_size=12.0)
        style2 = ParagraphStyle(font_name="Helvetica", font_size=12.0)
        
        assert style1.is_similar_to(style2)
    
    def test_is_similar_to_different_font(self):
        """Fuentes diferentes no son similares."""
        style1 = ParagraphStyle(font_name="Helvetica", font_size=12.0)
        style2 = ParagraphStyle(font_name="Times", font_size=12.0)
        
        assert not style1.is_similar_to(style2)
    
    def test_is_similar_to_different_size(self):
        """Tamaños muy diferentes no son similares."""
        style1 = ParagraphStyle(font_name="Helvetica", font_size=12.0)
        style2 = ParagraphStyle(font_name="Helvetica", font_size=20.0)
        
        assert not style1.is_similar_to(style2)
    
    def test_is_similar_to_within_tolerance(self):
        """Tamaños dentro de tolerancia son similares."""
        style1 = ParagraphStyle(font_name="Helvetica", font_size=12.0)
        style2 = ParagraphStyle(font_name="Helvetica", font_size=13.0)
        
        assert style1.is_similar_to(style2, tolerance=2.0)


# ============================================================
# TESTS: Funciones de Utilidad
# ============================================================

class TestUtilityFunctions:
    """Tests para funciones de utilidad."""
    
    def test_group_lines_into_paragraphs(self):
        """Función de conveniencia para agrupar."""
        lines = [create_line("Test", y_baseline=100.0)]
        
        paragraphs = group_lines_into_paragraphs(lines, page_num=1)
        
        assert len(paragraphs) == 1
        assert paragraphs[0].page_num == 1
    
    def test_find_paragraph_at_point(self):
        """Encontrar párrafo en un punto."""
        para = create_multiline_paragraph(["Test content"], start_y=100.0)
        para2 = create_multiline_paragraph(["Other"], start_y=200.0)
        
        found = find_paragraph_at_point([para, para2], x=100.0, y=95.0)
        
        assert found == para
    
    def test_find_paragraph_at_point_not_found(self):
        """No encontrar párrafo fuera de bounds."""
        para = create_multiline_paragraph(["Test"], start_y=100.0)
        
        found = find_paragraph_at_point([para], x=100.0, y=500.0)
        
        assert found is None
    
    def test_find_paragraphs_in_region(self):
        """Encontrar párrafos en una región."""
        para1 = create_multiline_paragraph(["Para 1"], start_y=100.0)
        para2 = create_multiline_paragraph(["Para 2"], start_y=200.0)
        para3 = create_multiline_paragraph(["Para 3"], start_y=300.0)
        
        # Región que incluye para1 y para2
        region = (0.0, 80.0, 500.0, 250.0)
        
        found = find_paragraphs_in_region([para1, para2, para3], region)
        
        assert len(found) >= 1
    
    def test_calculate_paragraph_statistics(self):
        """Cálculo de estadísticas."""
        para1 = create_multiline_paragraph(["Line 1", "Line 2"])
        para2 = create_multiline_paragraph(["Single"])
        
        stats = calculate_paragraph_statistics([para1, para2])
        
        assert stats['count'] == 2
        assert stats['total_lines'] == 3
        assert 'type_distribution' in stats
    
    def test_calculate_statistics_empty(self):
        """Estadísticas de lista vacía."""
        stats = calculate_paragraph_statistics([])
        
        assert stats['count'] == 0
        assert stats['total_lines'] == 0
    
    def test_merge_paragraphs(self):
        """Fusionar dos párrafos."""
        para1 = create_multiline_paragraph(["First"], start_y=100.0)
        para2 = create_multiline_paragraph(["Second"], start_y=150.0)
        
        merged = merge_paragraphs(para1, para2)
        
        assert merged.line_count == 2
        assert "First" in merged.text
        assert "Second" in merged.text
    
    def test_split_paragraph_at_line(self):
        """Dividir párrafo en un índice."""
        para = create_multiline_paragraph(["L1", "L2", "L3", "L4"])
        
        p1, p2 = split_paragraph_at_line(para, line_index=2)
        
        assert p1.line_count == 2
        assert p2.line_count == 2
    
    def test_split_paragraph_invalid_index(self):
        """Error al dividir con índice inválido."""
        para = create_multiline_paragraph(["L1", "L2"])
        
        with pytest.raises(ValueError):
            split_paragraph_at_line(para, line_index=0)
        
        with pytest.raises(ValueError):
            split_paragraph_at_line(para, line_index=5)


# ============================================================
# TESTS: TextParagraph - Métodos de Navegación
# ============================================================

class TestTextParagraphNavigation:
    """Tests para métodos de navegación."""
    
    def test_get_line_at_y(self):
        """Encontrar línea por posición Y."""
        para = create_multiline_paragraph(
            ["Line 1", "Line 2", "Line 3"],
            start_y=100.0,
            line_spacing=20.0
        )
        
        line = para.get_line_at_y(105.0)
        
        assert line is not None
        assert "Line 1" in line.text
    
    def test_get_line_at_y_not_found(self):
        """No encontrar línea fuera de rango."""
        para = create_multiline_paragraph(["Test"], start_y=100.0)
        
        line = para.get_line_at_y(500.0)
        
        assert line is None
    
    def test_get_line_by_index(self):
        """Obtener línea por índice."""
        para = create_multiline_paragraph(["First", "Second", "Third"])
        
        assert para.get_line_by_index(0) is not None
        assert "First" in para.get_line_by_index(0).text
        assert "Third" in para.get_line_by_index(2).text
    
    def test_get_line_by_index_invalid(self):
        """Índice inválido retorna None."""
        para = create_multiline_paragraph(["Test"])
        
        assert para.get_line_by_index(-1) is None
        assert para.get_line_by_index(10) is None
    
    def test_iter_lines(self):
        """Iterar sobre líneas."""
        para = create_multiline_paragraph(["A", "B", "C"])
        
        lines = list(para.iter_lines())
        
        assert len(lines) == 3
    
    def test_iter_spans(self):
        """Iterar sobre spans."""
        para = create_multiline_paragraph(["First", "Second"])
        
        spans = list(para.iter_spans())
        
        assert len(spans) == 2


# ============================================================
# TESTS: TextParagraph - Serialización
# ============================================================

class TestTextParagraphSerialization:
    """Tests para serialización."""
    
    def test_to_dict(self):
        """Conversión a diccionario."""
        para = create_multiline_paragraph(["Test line"])
        
        data = para.to_dict()
        
        assert 'paragraph_id' in data
        assert 'text' in data
        assert 'bbox' in data
        assert 'lines' in data
        assert data['line_count'] == 1
    
    def test_to_dict_preserves_type(self):
        """El diccionario preserva el tipo."""
        para = TextParagraph(
            lines=[create_line("Title", y_baseline=100.0)],
            paragraph_type=ParagraphType.HEADING,
            heading_level=2
        )
        
        data = para.to_dict()
        
        assert data['paragraph_type'] == 'heading'
        assert data['heading_level'] == 2


# ============================================================
# TESTS: ParagraphDetectionConfig
# ============================================================

class TestParagraphDetectionConfig:
    """Tests para configuración de detección."""
    
    def test_default_config(self):
        """Configuración por defecto."""
        config = ParagraphDetectionConfig()
        
        assert config.paragraph_gap_threshold == 1.5
        assert config.indent_threshold == 10.0
        assert config.heading_size_ratio == 1.2
    
    def test_custom_config(self):
        """Configuración personalizada."""
        config = ParagraphDetectionConfig(
            paragraph_gap_threshold=2.0,
            indent_threshold=20.0
        )
        
        assert config.paragraph_gap_threshold == 2.0
        assert config.indent_threshold == 20.0
    
    def test_bullet_markers(self):
        """Marcadores de viñeta por defecto."""
        config = ParagraphDetectionConfig()
        
        assert "•" in config.bullet_markers
        assert "-" in config.bullet_markers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

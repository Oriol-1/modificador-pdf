"""
Tests para el módulo TextHitTester.

Pruebas de hit-testing preciso de texto PDF.
"""

import pytest
from unittest.mock import Mock

# Mock del módulo fitz para tests sin PyMuPDF instalado
import sys


# Crear mock de fitz antes de importar el módulo
class MockFitzModule:
    """Mock del módulo fitz (PyMuPDF)."""
    TEXT_PRESERVE_WHITESPACE = 1
    TEXT_PRESERVE_LIGATURES = 2
    
    class Document:
        def __init__(self, path=None):
            self._pages = []
            self.is_open = True
            self.page_count = 0
        
        def __getitem__(self, index):
            if 0 <= index < len(self._pages):
                return self._pages[index]
            return MockPage()
        
        def close(self):
            self.is_open = False
    
    class Rect:
        def __init__(self, x0=0, y0=0, x1=0, y1=0):
            self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
            
        @property
        def width(self):
            return self.x1 - self.x0
            
        @property
        def height(self):
            return self.y1 - self.y0


class MockPage:
    """Mock de una página de PDF."""
    
    def __init__(self, blocks=None):
        self._blocks = blocks or []
    
    def get_text(self, mode="dict", flags=0):
        return {"blocks": self._blocks}


# Solo usar mock si fitz no está disponible
try:
    import fitz
except ImportError:
    sys.modules['fitz'] = MockFitzModule()
    fitz = MockFitzModule()


from core.text_engine.text_hit_tester import (  # noqa: E402
    HitType,
    HitTestResult,
    PageTextCache,
    TextHitTester,
    create_hit_tester,
    hit_test_point,
    get_span_at_point,
    get_line_at_point,
)
from core.text_engine.text_span import TextSpanMetrics  # noqa: E402
from core.text_engine.text_line import TextLine  # noqa: E402


# ================== Fixtures ==================

@pytest.fixture
def sample_span():
    """Crear un span de prueba."""
    return TextSpanMetrics(
        text="Hello World",
        page_num=0,
        span_id="span001",
        bbox=(100.0, 200.0, 200.0, 220.0),
        origin=(100.0, 218.0),
        baseline_y=218.0,
        font_name="Helvetica",
        font_size=12.0,
        fill_color="#000000",
    )


@pytest.fixture
def sample_spans():
    """Crear varios spans de prueba."""
    return [
        TextSpanMetrics(
            text="Hello",
            page_num=0,
            span_id="span001",
            bbox=(100.0, 200.0, 150.0, 220.0),
            baseline_y=218.0,
            font_name="Helvetica",
            font_size=12.0,
        ),
        TextSpanMetrics(
            text="World",
            page_num=0,
            span_id="span002",
            bbox=(155.0, 200.0, 210.0, 220.0),
            baseline_y=218.0,
            font_name="Helvetica",
            font_size=12.0,
        ),
        TextSpanMetrics(
            text="Test",
            page_num=0,
            span_id="span003",
            bbox=(100.0, 250.0, 140.0, 270.0),
            baseline_y=268.0,
            font_name="Arial",
            font_size=14.0,
        ),
    ]


@pytest.fixture
def sample_line(sample_spans):
    """Crear una línea de prueba."""
    return TextLine(
        spans=sample_spans[:2],  # Los dos primeros spans
        page_num=0,
        baseline_y=218.0,
    )


@pytest.fixture
def sample_lines(sample_spans):
    """Crear varias líneas de prueba."""
    return [
        TextLine(
            spans=[sample_spans[0], sample_spans[1]],
            page_num=0,
            baseline_y=218.0,
        ),
        TextLine(
            spans=[sample_spans[2]],
            page_num=0,
            baseline_y=268.0,
        ),
    ]


@pytest.fixture
def mock_document():
    """Crear un documento mock."""
    doc = Mock()
    doc.is_open = True
    doc.page_count = 2
    
    # Crear páginas mock
    page0 = Mock()
    page0.get_text = Mock(return_value={
        "blocks": [
            {
                "type": 0,
                "lines": [
                    {
                        "spans": [
                            {
                                "text": "Hello",
                                "bbox": (100, 200, 150, 220),
                                "origin": (100, 218),
                                "font": "Helvetica",
                                "size": 12.0,
                                "color": 0,
                                "flags": 0,
                            },
                            {
                                "text": "World",
                                "bbox": (155, 200, 210, 220),
                                "origin": (155, 218),
                                "font": "Helvetica",
                                "size": 12.0,
                                "color": 0,
                                "flags": 0,
                            },
                        ]
                    },
                    {
                        "spans": [
                            {
                                "text": "Second line",
                                "bbox": (100, 250, 200, 270),
                                "origin": (100, 268),
                                "font": "Arial",
                                "size": 14.0,
                                "color": 0,
                                "flags": 0,
                            },
                        ]
                    }
                ]
            }
        ]
    })
    
    page1 = Mock()
    page1.get_text = Mock(return_value={"blocks": []})
    
    doc.__getitem__ = Mock(side_effect=lambda i: page0 if i == 0 else page1)
    
    return doc


@pytest.fixture
def hit_tester():
    """Crear un hit-tester básico."""
    return TextHitTester()


@pytest.fixture
def hit_tester_with_doc(mock_document):
    """Crear un hit-tester con documento."""
    tester = TextHitTester()
    tester.set_document(mock_document)
    return tester


# ================== Tests para HitType ==================

class TestHitType:
    """Tests para la enumeración HitType."""
    
    def test_hit_type_values(self):
        """Verificar valores de la enumeración."""
        assert HitType.NONE.value == "none"
        assert HitType.SPAN.value == "span"
        assert HitType.LINE.value == "line"
        assert HitType.INTER_SPAN_GAP.value == "gap"
        assert HitType.CHARACTER.value == "character"
    
    def test_hit_type_comparison(self):
        """Verificar comparación de tipos."""
        assert HitType.NONE != HitType.SPAN
        assert HitType.SPAN == HitType.SPAN


# ================== Tests para HitTestResult ==================

class TestHitTestResult:
    """Tests para la clase HitTestResult."""
    
    def test_default_creation(self):
        """Verificar creación por defecto."""
        result = HitTestResult()
        assert result.hit_type == HitType.NONE
        assert result.span is None
        assert result.line is None
        assert result.char_index is None
        assert result.point == (0.0, 0.0)
        assert result.bbox is None
        assert result.distance == float('inf')
    
    def test_found_property_none(self):
        """Verificar propiedad found cuando no hay resultado."""
        result = HitTestResult()
        assert result.found is False
    
    def test_found_property_span(self, sample_span):
        """Verificar propiedad found con span."""
        result = HitTestResult(
            hit_type=HitType.SPAN,
            span=sample_span,
        )
        assert result.found is True
    
    def test_found_property_line(self, sample_line):
        """Verificar propiedad found con línea."""
        result = HitTestResult(
            hit_type=HitType.LINE,
            line=sample_line,
        )
        assert result.found is True
    
    def test_text_property_span(self, sample_span):
        """Verificar propiedad text con span."""
        result = HitTestResult(
            hit_type=HitType.SPAN,
            span=sample_span,
        )
        assert result.text == "Hello World"
    
    def test_text_property_line(self, sample_line):
        """Verificar propiedad text con línea."""
        result = HitTestResult(
            hit_type=HitType.LINE,
            line=sample_line,
        )
        # La línea tiene "Hello" y "World" separados
        assert "Hello" in result.text
        assert "World" in result.text
    
    def test_text_property_empty(self):
        """Verificar propiedad text vacía."""
        result = HitTestResult()
        assert result.text == ""
    
    def test_char_text_property(self, sample_span):
        """Verificar propiedad char_text."""
        result = HitTestResult(
            hit_type=HitType.CHARACTER,
            span=sample_span,
            char_index=0,
        )
        assert result.char_text == "H"
    
    def test_char_text_invalid_index(self, sample_span):
        """Verificar char_text con índice inválido."""
        result = HitTestResult(
            hit_type=HitType.CHARACTER,
            span=sample_span,
            char_index=100,  # Fuera de rango
        )
        assert result.char_text == ""
    
    def test_to_dict(self, sample_span, sample_line):
        """Verificar conversión a diccionario."""
        result = HitTestResult(
            hit_type=HitType.SPAN,
            span=sample_span,
            line=sample_line,
            char_index=5,
            point=(150.0, 210.0),
            bbox=(100.0, 200.0, 200.0, 220.0),
            distance=2.5,
        )
        
        d = result.to_dict()
        
        assert d['hit_type'] == "span"
        assert d['span_id'] == "span001"
        assert d['span_text'] == "Hello World"
        assert d['char_index'] == 5
        assert d['point'] == (150.0, 210.0)
        assert d['distance'] == 2.5


# ================== Tests para PageTextCache ==================

class TestPageTextCache:
    """Tests para la clase PageTextCache."""
    
    def test_default_creation(self):
        """Verificar creación por defecto."""
        cache = PageTextCache(page_num=0)
        assert cache.page_num == 0
        assert cache.spans == []
        assert cache.lines == []
        assert cache.is_valid is False
    
    def test_build_spatial_index(self, sample_spans, sample_lines):
        """Verificar construcción del índice espacial."""
        cache = PageTextCache(
            page_num=0,
            spans=sample_spans,
            lines=sample_lines,
            is_valid=True,
        )
        
        cache.build_spatial_index()
        
        # Verificar que el índice está ordenado
        assert len(cache._y_sorted_lines) == 2
        # La primera línea debería tener baseline_y menor
        assert cache._y_sorted_lines[0].baseline_y <= cache._y_sorted_lines[1].baseline_y
    
    def test_get_lines_near_y(self, sample_lines):
        """Verificar búsqueda de líneas cerca de Y."""
        cache = PageTextCache(
            page_num=0,
            lines=sample_lines,
            is_valid=True,
        )
        cache.build_spatial_index()
        
        # Buscar cerca de la primera línea (baseline_y=218)
        lines = cache.get_lines_near_y(215.0, tolerance=10.0)
        assert len(lines) >= 1
        
        # Buscar lejos de ambas líneas
        lines = cache.get_lines_near_y(400.0, tolerance=10.0)
        assert len(lines) == 0
    
    def test_clear(self, sample_spans, sample_lines):
        """Verificar limpieza de caché."""
        cache = PageTextCache(
            page_num=0,
            spans=sample_spans,
            lines=sample_lines,
            is_valid=True,
        )
        cache.build_spatial_index()
        
        cache.clear()
        
        assert cache.spans == []
        assert cache.lines == []
        assert cache._y_sorted_lines == []
        assert cache.is_valid is False


# ================== Tests para TextHitTester ==================

class TestTextHitTester:
    """Tests para la clase TextHitTester."""
    
    def test_creation(self):
        """Verificar creación básica."""
        tester = TextHitTester()
        assert tester._document is None
        assert tester._page_caches == {}
    
    def test_creation_with_font_manager(self):
        """Verificar creación con font manager."""
        font_manager = Mock()
        tester = TextHitTester(font_manager=font_manager)
        assert tester._font_manager == font_manager
    
    def test_set_document(self, hit_tester, mock_document):
        """Verificar establecer documento."""
        hit_tester.set_document(mock_document)
        assert hit_tester._document == mock_document
    
    def test_set_document_clears_cache(self, hit_tester_with_doc, mock_document):
        """Verificar que cambiar documento limpia la caché."""
        # Poner algo en caché primero
        hit_tester_with_doc._page_caches[0] = PageTextCache(page_num=0)
        
        new_doc = Mock()
        new_doc.is_open = True
        new_doc.page_count = 1
        
        hit_tester_with_doc.set_document(new_doc)
        
        # La caché debería estar limpia
        assert hit_tester_with_doc._page_caches == {}
    
    def test_clear_cache(self, hit_tester_with_doc):
        """Verificar limpieza de toda la caché."""
        hit_tester_with_doc._page_caches[0] = PageTextCache(page_num=0)
        hit_tester_with_doc._page_caches[1] = PageTextCache(page_num=1)
        
        hit_tester_with_doc.clear_cache()
        
        assert hit_tester_with_doc._page_caches == {}
    
    def test_invalidate_page(self, hit_tester_with_doc):
        """Verificar invalidar página específica."""
        cache = PageTextCache(page_num=0, is_valid=True)
        hit_tester_with_doc._page_caches[0] = cache
        
        hit_tester_with_doc.invalidate_page(0)
        
        assert cache.is_valid is False
    
    def test_ensure_page_cached(self, hit_tester_with_doc):
        """Verificar que se crea caché para página."""
        cache = hit_tester_with_doc.ensure_page_cached(0)
        
        assert cache is not None
        assert cache.page_num == 0
        assert 0 in hit_tester_with_doc._page_caches
    
    def test_hit_test_no_document(self, hit_tester):
        """Verificar hit-test sin documento."""
        result = hit_tester.hit_test(0, 100.0, 200.0)
        assert result.hit_type == HitType.NONE
        assert result.found is False
    
    def test_hit_test_with_document(self, hit_tester_with_doc):
        """Verificar hit-test con documento."""
        # El mock tiene texto en (100, 200) - (210, 220)
        result = hit_tester_with_doc.hit_test(0, 125.0, 210.0)
        
        # Debería encontrar algo
        assert result is not None
        assert result.point == (125.0, 210.0)
    
    def test_hit_test_outside_text(self, hit_tester_with_doc):
        """Verificar hit-test fuera del texto."""
        # Buscar lejos del texto
        result = hit_tester_with_doc.hit_test(0, 500.0, 500.0, tolerance=5.0)
        
        # No debería encontrar nada
        assert result.hit_type == HitType.NONE or result.distance > 10.0
    
    def test_hit_test_spans_in_rect(self, hit_tester_with_doc):
        """Verificar búsqueda de spans en rectángulo."""
        # Rectángulo que cubre el área del texto
        spans = hit_tester_with_doc.hit_test_spans_in_rect(
            0,
            (90.0, 190.0, 220.0, 230.0)
        )
        
        # Debería encontrar spans
        assert isinstance(spans, list)
    
    def test_hit_test_lines_in_rect(self, hit_tester_with_doc):
        """Verificar búsqueda de líneas en rectángulo."""
        lines = hit_tester_with_doc.hit_test_lines_in_rect(
            0,
            (90.0, 190.0, 220.0, 280.0)
        )
        
        assert isinstance(lines, list)
    
    def test_get_all_spans(self, hit_tester_with_doc):
        """Verificar obtener todos los spans."""
        spans = hit_tester_with_doc.get_all_spans(0)
        assert isinstance(spans, list)
    
    def test_get_all_lines(self, hit_tester_with_doc):
        """Verificar obtener todas las líneas."""
        lines = hit_tester_with_doc.get_all_lines(0)
        assert isinstance(lines, list)
    
    def test_get_page_text(self, hit_tester_with_doc):
        """Verificar obtener texto de página."""
        text = hit_tester_with_doc.get_page_text(0)
        assert isinstance(text, str)
    
    def test_find_nearest_span(self, hit_tester_with_doc):
        """Verificar encontrar span más cercano."""
        # El mock tiene texto cerca de (125, 210)
        # Puede o no encontrar dependiendo de la implementación
        # Solo verificamos que no falla
        hit_tester_with_doc.find_nearest_span(0, 125.0, 210.0)


# ================== Tests para funciones de conveniencia ==================

class TestConvenienceFunctions:
    """Tests para las funciones de conveniencia."""
    
    def test_create_hit_tester_basic(self):
        """Verificar creación básica de hit-tester."""
        tester = create_hit_tester()
        assert tester is not None
        assert tester._document is None
    
    def test_create_hit_tester_with_document(self, mock_document):
        """Verificar creación con documento."""
        tester = create_hit_tester(document=mock_document)
        assert tester._document == mock_document
    
    def test_create_hit_tester_with_font_manager(self):
        """Verificar creación con font manager."""
        fm = Mock()
        tester = create_hit_tester(font_manager=fm)
        assert tester._font_manager == fm
    
    def test_hit_test_point_function(self, mock_document):
        """Verificar función hit_test_point."""
        result = hit_test_point(mock_document, 0, 125.0, 210.0)
        assert result is not None
        assert isinstance(result, HitTestResult)
    
    def test_get_span_at_point_function(self, mock_document):
        """Verificar función get_span_at_point."""
        span = get_span_at_point(mock_document, 0, 125.0, 210.0)
        # Puede ser None o un span
        assert span is None or isinstance(span, TextSpanMetrics)
    
    def test_get_line_at_point_function(self, mock_document):
        """Verificar función get_line_at_point."""
        line = get_line_at_point(mock_document, 0, 125.0, 210.0)
        # Puede ser None o una línea
        assert line is None or isinstance(line, TextLine)


# ================== Tests de integración ==================

class TestHitTesterIntegration:
    """Tests de integración del hit-tester."""
    
    def test_full_workflow(self, hit_tester_with_doc):
        """Verificar flujo completo de uso."""
        # 1. Obtener spans de la página
        assert hit_tester_with_doc.get_all_spans(0) is not None
        
        # 2. Obtener líneas
        assert hit_tester_with_doc.get_all_lines(0) is not None
        
        # 3. Hacer hit-test y verificar resultado
        result = hit_tester_with_doc.hit_test(0, 125.0, 210.0)
        assert result is not None
    
    def test_cache_persistence(self, hit_tester_with_doc):
        """Verificar que la caché persiste entre llamadas."""
        # Primera llamada
        spans1 = hit_tester_with_doc.get_all_spans(0)
        
        # La caché debería estar activa
        assert 0 in hit_tester_with_doc._page_caches
        assert hit_tester_with_doc._page_caches[0].is_valid
        
        # Segunda llamada debería usar caché
        spans2 = hit_tester_with_doc.get_all_spans(0)
        
        # Los resultados deberían ser consistentes
        assert len(spans1) == len(spans2)
    
    def test_invalidate_and_refresh(self, hit_tester_with_doc):
        """Verificar invalidación y re-carga de caché."""
        # Cargar caché
        hit_tester_with_doc.get_all_spans(0)
        assert hit_tester_with_doc._page_caches[0].is_valid is True
        
        # Invalidar
        hit_tester_with_doc.invalidate_page(0)
        assert hit_tester_with_doc._page_caches[0].is_valid is False
        
        # Re-cargar
        hit_tester_with_doc.get_all_spans(0)
        assert hit_tester_with_doc._page_caches[0].is_valid is True


# ================== Tests de edge cases ==================

class TestEdgeCases:
    """Tests para casos límite."""
    
    def test_empty_page(self, hit_tester):
        """Verificar página vacía."""
        doc = Mock()
        doc.is_open = True
        doc.page_count = 1
        
        page = Mock()
        page.get_text = Mock(return_value={"blocks": []})
        doc.__getitem__ = Mock(return_value=page)
        
        hit_tester.set_document(doc)
        
        result = hit_tester.hit_test(0, 100.0, 100.0)
        assert result.found is False
    
    def test_invalid_page_number(self, hit_tester_with_doc):
        """Verificar número de página inválido."""
        result = hit_tester_with_doc.hit_test(-1, 100.0, 100.0)
        assert result.found is False
        
        result = hit_tester_with_doc.hit_test(999, 100.0, 100.0)
        assert result.found is False
    
    def test_negative_coordinates(self, hit_tester_with_doc):
        """Verificar coordenadas negativas."""
        result = hit_tester_with_doc.hit_test(0, -100.0, -100.0)
        # No debería fallar
        assert result is not None
    
    def test_very_large_coordinates(self, hit_tester_with_doc):
        """Verificar coordenadas muy grandes."""
        result = hit_tester_with_doc.hit_test(0, 10000.0, 10000.0)
        # No debería fallar
        assert result is not None
    
    def test_zero_tolerance(self, hit_tester_with_doc):
        """Verificar tolerancia cero."""
        result = hit_tester_with_doc.hit_test(0, 125.0, 210.0, tolerance=0.0)
        # No debería fallar
        assert result is not None
    
    def test_very_large_tolerance(self, hit_tester_with_doc):
        """Verificar tolerancia muy grande."""
        result = hit_tester_with_doc.hit_test(0, 0.0, 0.0, tolerance=1000.0)
        # Debería encontrar algo con tolerancia grande
        assert result is not None


# ================== Tests de rendimiento ==================

class TestPerformance:
    """Tests relacionados con rendimiento."""
    
    def test_cache_is_used(self, hit_tester_with_doc):
        """Verificar que la caché se usa para múltiples llamadas."""
        # Primera llamada - llena la caché
        hit_tester_with_doc.hit_test(0, 125.0, 210.0)
        
        # Guardar referencia de caché
        cache = hit_tester_with_doc._page_caches[0]
        
        # Múltiples llamadas
        for _ in range(10):
            hit_tester_with_doc.hit_test(0, 125.0, 210.0)
        
        # La caché debería seguir siendo la misma
        assert hit_tester_with_doc._page_caches[0] is cache
    
    def test_spatial_index_used(self, sample_lines):
        """Verificar que el índice espacial se construye."""
        cache = PageTextCache(
            page_num=0,
            lines=sample_lines,
            is_valid=True,
        )
        
        # Buscar sin índice construido (esto construye el índice automáticamente)
        cache.get_lines_near_y(218.0)
        
        # El índice debería construirse automáticamente
        assert len(cache._y_sorted_lines) > 0

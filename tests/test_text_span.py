"""
Tests para TextSpanMetrics - Métricas completas de spans de texto PDF.

Cobertura:
- Creación y valores por defecto
- Propiedades calculadas
- Detección de embedding status
- Comparación de estilos
- Serialización JSON
- Función factory create_span_from_pymupdf
"""

import json
from core.text_engine.text_span import (
    TextSpanMetrics,
    RenderMode,
    FontEmbeddingStatus,
    create_span_from_pymupdf,
    create_empty_span,
)


class TestTextSpanMetricsBasics:
    """Tests básicos de creación y valores por defecto."""
    
    def test_create_minimal_span(self):
        """Crear span con parámetros mínimos."""
        span = TextSpanMetrics(text="Hello", page_num=0)
        
        assert span.text == "Hello"
        assert span.page_num == 0
        assert span.font_name == "Helvetica"
        assert span.font_size == 12.0
        assert span.fill_color == "#000000"
        assert len(span.span_id) == 8  # UUID truncado
    
    def test_create_full_span(self):
        """Crear span con todos los parámetros."""
        span = TextSpanMetrics(
            text="Test text",
            page_num=5,
            bbox=(10.0, 20.0, 100.0, 35.0),
            origin=(10.0, 35.0),
            baseline_y=32.0,
            font_name="Arial",
            font_name_pdf="ABCDEF+Arial",
            font_size=14.0,
            font_flags=64,
            fill_color="#FF0000",
            char_spacing=0.5,
            word_spacing=2.0,
            rise=3.0,
            is_bold=True,
        )
        
        assert span.text == "Test text"
        assert span.page_num == 5
        assert span.bbox == (10.0, 20.0, 100.0, 35.0)
        assert span.font_name == "Arial"
        assert span.font_name_pdf == "ABCDEF+Arial"
        assert span.font_size == 14.0
        assert span.fill_color == "#FF0000"
        assert span.char_spacing == 0.5
        assert span.word_spacing == 2.0
        assert span.rise == 3.0
        assert span.is_bold is True
    
    def test_default_values(self):
        """Verificar valores por defecto."""
        span = TextSpanMetrics(text="", page_num=0)
        
        assert span.bbox == (0.0, 0.0, 0.0, 0.0)
        assert span.origin == (0.0, 0.0)
        assert span.baseline_y == 0.0
        assert span.render_mode == RenderMode.FILL
        assert span.fill_opacity == 1.0
        assert span.horizontal_scale == 100.0
        assert span.rotation == 0.0
        assert span.char_spacing == 0.0
        assert span.word_spacing == 0.0
        assert span.rise == 0.0
        assert span.leading == 0.0
        assert span.is_bold is None
        assert span.is_italic is None
        assert span.is_superscript is False
        assert span.is_subscript is False
        assert span.was_fallback is False
        assert span.confidence == 1.0
    
    def test_ctm_default_identity(self):
        """Verificar que CTM por defecto es identidad."""
        span = TextSpanMetrics(text="", page_num=0)
        
        assert span.ctm == (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        assert span.text_matrix == (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


class TestTextSpanMetricsPostInit:
    """Tests para lógica post-inicialización."""
    
    def test_superscript_detection_from_positive_rise(self):
        """Rise positivo -> superscript."""
        span = TextSpanMetrics(text="2", page_num=0, rise=3.0)
        
        assert span.is_superscript is True
        assert span.is_subscript is False
    
    def test_subscript_detection_from_negative_rise(self):
        """Rise negativo -> subscript."""
        span = TextSpanMetrics(text="2", page_num=0, rise=-3.0)
        
        assert span.is_superscript is False
        assert span.is_subscript is True
    
    def test_no_super_subscript_with_zero_rise(self):
        """Rise cero -> ni super ni subscript."""
        span = TextSpanMetrics(text="normal", page_num=0, rise=0.0)
        
        assert span.is_superscript is False
        assert span.is_subscript is False
    
    def test_font_name_pdf_defaults_to_font_name(self):
        """Si font_name_pdf vacío, usa font_name."""
        span = TextSpanMetrics(text="", page_num=0, font_name="Arial")
        
        assert span.font_name_pdf == "Arial"
    
    def test_total_width_calculated_from_char_widths(self):
        """total_width se calcula de char_widths si no está definido."""
        span = TextSpanMetrics(
            text="abc",
            page_num=0,
            char_widths=[10.0, 8.0, 12.0]
        )
        
        assert span.total_width == 30.0


class TestEmbeddingStatusDetection:
    """Tests para detección de estado de embedding."""
    
    def test_detect_subset_from_name(self):
        """Detectar subset por patrón ABCDEF+FontName."""
        span = TextSpanMetrics(
            text="",
            page_num=0,
            font_name_pdf="ABCDEF+Arial"
        )
        
        assert span.embedding_status == FontEmbeddingStatus.SUBSET
        assert span.is_subset_font is True
        assert span.is_embedded_font is True
    
    def test_detect_subset_various_prefixes(self):
        """Detectar subset con diferentes prefijos."""
        prefixes = ["ABCDEF", "GHIJKL", "MNOPQR", "ZZZZZZ"]
        
        for prefix in prefixes:
            span = TextSpanMetrics(
                text="",
                page_num=0,
                font_name_pdf=f"{prefix}+Times"
            )
            assert span.embedding_status == FontEmbeddingStatus.SUBSET, f"Failed for {prefix}"
    
    def test_not_subset_without_plus(self):
        """Sin '+' no es subset."""
        span = TextSpanMetrics(
            text="",
            page_num=0,
            font_name_pdf="Arial"
        )
        
        assert span.embedding_status == FontEmbeddingStatus.UNKNOWN
        assert span.is_subset_font is False
    
    def test_not_subset_with_invalid_prefix(self):
        """Prefijo inválido (no 6 letras) no es subset."""
        span = TextSpanMetrics(
            text="",
            page_num=0,
            font_name_pdf="ABC+Arial"  # Solo 3 letras
        )
        
        assert span.embedding_status == FontEmbeddingStatus.UNKNOWN
    
    def test_fully_embedded_flag(self):
        """Fuente completamente embebida."""
        span = TextSpanMetrics(
            text="",
            page_num=0,
            embedding_status=FontEmbeddingStatus.FULLY_EMBEDDED
        )
        
        assert span.is_embedded_font is True
        assert span.is_subset_font is False


class TestCalculatedProperties:
    """Tests para propiedades calculadas."""
    
    def test_width_and_height(self):
        """Calcular ancho y alto desde bbox."""
        span = TextSpanMetrics(
            text="",
            page_num=0,
            bbox=(10.0, 20.0, 110.0, 35.0)
        )
        
        assert span.width == 100.0
        assert span.height == 15.0
    
    def test_center(self):
        """Calcular centro desde bbox."""
        span = TextSpanMetrics(
            text="",
            page_num=0,
            bbox=(0.0, 0.0, 100.0, 50.0)
        )
        
        assert span.center == (50.0, 25.0)
    
    def test_has_transformation_false_for_identity(self):
        """Sin transformación si CTM es identidad."""
        span = TextSpanMetrics(text="", page_num=0)
        
        assert span.has_transformation is False
    
    def test_has_transformation_true_for_non_identity_ctm(self):
        """Con transformación si CTM no es identidad."""
        span = TextSpanMetrics(
            text="",
            page_num=0,
            ctm=(2.0, 0.0, 0.0, 2.0, 0.0, 0.0)  # Escala 2x
        )
        
        assert span.has_transformation is True
    
    def test_has_transformation_true_for_non_identity_text_matrix(self):
        """Con transformación si text_matrix no es identidad."""
        span = TextSpanMetrics(
            text="",
            page_num=0,
            text_matrix=(1.0, 0.5, 0.0, 1.0, 0.0, 0.0)  # Skew
        )
        
        assert span.has_transformation is True
    
    def test_has_custom_spacing_false_for_zero(self):
        """Sin espaciado custom si Tc y Tw son 0."""
        span = TextSpanMetrics(text="", page_num=0)
        
        assert span.has_custom_spacing is False
    
    def test_has_custom_spacing_true_for_char_spacing(self):
        """Con espaciado custom si Tc != 0."""
        span = TextSpanMetrics(text="", page_num=0, char_spacing=0.5)
        
        assert span.has_custom_spacing is True
    
    def test_has_custom_spacing_true_for_word_spacing(self):
        """Con espaciado custom si Tw != 0."""
        span = TextSpanMetrics(text="", page_num=0, word_spacing=1.0)
        
        assert span.has_custom_spacing is True
    
    def test_style_summary(self):
        """Generar resumen de estilo."""
        span = TextSpanMetrics(
            text="",
            page_num=0,
            font_name="Arial",
            font_size=14.0,
            is_bold=True,
            is_italic=True,
            rise=3.0  # -> superscript
        )
        
        summary = span.style_summary
        assert "Arial" in summary
        assert "14.0pt" in summary
        assert "Bold" in summary
        assert "Italic" in summary
        assert "Superscript" in summary
    
    def test_spacing_summary_normal(self):
        """Resumen de espaciado normal."""
        span = TextSpanMetrics(text="", page_num=0)
        
        assert span.spacing_summary == "Normal"
    
    def test_spacing_summary_with_values(self):
        """Resumen de espaciado con valores."""
        span = TextSpanMetrics(
            text="",
            page_num=0,
            char_spacing=0.5,
            word_spacing=2.0,
            rise=3.0
        )
        
        summary = span.spacing_summary
        assert "Tc=0.50" in summary
        assert "Tw=2.00" in summary
        assert "Rise=3.00" in summary


class TestStyleComparison:
    """Tests para comparación de estilos."""
    
    def test_same_style_identical(self):
        """Mismo estilo con spans idénticos."""
        span1 = TextSpanMetrics(
            text="a",
            page_num=0,
            font_name="Arial",
            font_size=12.0,
            fill_color="#000000",
            is_bold=True
        )
        span2 = TextSpanMetrics(
            text="b",
            page_num=0,
            font_name="Arial",
            font_size=12.0,
            fill_color="#000000",
            is_bold=True
        )
        
        assert span1.has_same_style(span2) is True
    
    def test_different_style_font(self):
        """Diferente estilo por fuente."""
        span1 = TextSpanMetrics(text="", page_num=0, font_name="Arial")
        span2 = TextSpanMetrics(text="", page_num=0, font_name="Times")
        
        assert span1.has_same_style(span2) is False
    
    def test_different_style_size(self):
        """Diferente estilo por tamaño."""
        span1 = TextSpanMetrics(text="", page_num=0, font_size=12.0)
        span2 = TextSpanMetrics(text="", page_num=0, font_size=14.0)
        
        assert span1.has_same_style(span2) is False
    
    def test_same_style_within_tolerance(self):
        """Mismo estilo dentro de tolerancia."""
        span1 = TextSpanMetrics(text="", page_num=0, font_size=12.0)
        span2 = TextSpanMetrics(text="", page_num=0, font_size=12.4)
        
        assert span1.has_same_style(span2, tolerance=0.5) is True
    
    def test_different_style_color(self):
        """Diferente estilo por color."""
        span1 = TextSpanMetrics(text="", page_num=0, fill_color="#000000")
        span2 = TextSpanMetrics(text="", page_num=0, fill_color="#FF0000")
        
        assert span1.has_same_style(span2) is False
    
    def test_same_spacing(self):
        """Mismo espaciado."""
        span1 = TextSpanMetrics(text="", page_num=0, char_spacing=0.5, word_spacing=1.0)
        span2 = TextSpanMetrics(text="", page_num=0, char_spacing=0.5, word_spacing=1.0)
        
        assert span1.has_same_spacing(span2) is True
    
    def test_different_spacing(self):
        """Diferente espaciado."""
        span1 = TextSpanMetrics(text="", page_num=0, char_spacing=0.5)
        span2 = TextSpanMetrics(text="", page_num=0, char_spacing=1.0)
        
        assert span1.has_same_spacing(span2) is False
    
    def test_same_baseline(self):
        """Mismo baseline."""
        span1 = TextSpanMetrics(text="", page_num=0, baseline_y=100.0)
        span2 = TextSpanMetrics(text="", page_num=0, baseline_y=101.0)
        
        assert span1.is_on_same_baseline(span2, tolerance=2.0) is True
    
    def test_different_baseline(self):
        """Diferente baseline."""
        span1 = TextSpanMetrics(text="", page_num=0, baseline_y=100.0)
        span2 = TextSpanMetrics(text="", page_num=0, baseline_y=120.0)
        
        assert span1.is_on_same_baseline(span2, tolerance=2.0) is False


class TestSerialization:
    """Tests para serialización JSON."""
    
    def test_to_dict_basic(self):
        """Convertir a dict básico."""
        span = TextSpanMetrics(
            text="Hello",
            page_num=1,
            font_name="Arial",
            font_size=14.0
        )
        
        d = span.to_dict()
        
        assert d["text"] == "Hello"
        assert d["page_num"] == 1
        assert d["font_name"] == "Arial"
        assert d["font_size"] == 14.0
    
    def test_to_dict_converts_tuples_to_lists(self):
        """to_dict convierte tuplas a listas para JSON."""
        span = TextSpanMetrics(
            text="",
            page_num=0,
            bbox=(1, 2, 3, 4)
        )
        
        d = span.to_dict()
        
        assert d["bbox"] == [1, 2, 3, 4]
        assert isinstance(d["bbox"], list)
    
    def test_to_dict_enums_to_values(self):
        """to_dict convierte enums a sus valores."""
        span = TextSpanMetrics(
            text="",
            page_num=0,
            render_mode=RenderMode.STROKE,
            embedding_status=FontEmbeddingStatus.SUBSET
        )
        
        d = span.to_dict()
        
        assert d["render_mode"] == 1
        assert d["embedding_status"] == "subset"
    
    def test_from_dict(self):
        """Crear desde dict."""
        d = {
            "text": "Test",
            "page_num": 2,
            "font_name": "Times",
            "font_size": 16.0,
            "bbox": [10, 20, 100, 40],
            "render_mode": 1,
            "embedding_status": "subset"
        }
        
        span = TextSpanMetrics.from_dict(d)
        
        assert span.text == "Test"
        assert span.page_num == 2
        assert span.font_name == "Times"
        assert span.font_size == 16.0
        assert span.bbox == (10, 20, 100, 40)
        assert span.render_mode == RenderMode.STROKE
        assert span.embedding_status == FontEmbeddingStatus.SUBSET
    
    def test_roundtrip_to_dict_from_dict(self):
        """Roundtrip: to_dict -> from_dict preserva datos."""
        original = TextSpanMetrics(
            text="Test roundtrip",
            page_num=5,
            bbox=(10.0, 20.0, 200.0, 40.0),
            font_name="Arial",
            font_size=12.5,
            char_spacing=0.5,
            word_spacing=1.5,
            is_bold=True,
        )
        
        restored = TextSpanMetrics.from_dict(original.to_dict())
        
        assert restored.text == original.text
        assert restored.page_num == original.page_num
        assert restored.bbox == original.bbox
        assert restored.font_name == original.font_name
        assert restored.font_size == original.font_size
        assert restored.char_spacing == original.char_spacing
        assert restored.word_spacing == original.word_spacing
        assert restored.is_bold == original.is_bold
    
    def test_to_json(self):
        """Serializar a JSON string."""
        span = TextSpanMetrics(text="JSON test", page_num=0)
        
        json_str = span.to_json()
        
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["text"] == "JSON test"
    
    def test_from_json(self):
        """Deserializar desde JSON string."""
        json_str = '{"text": "From JSON", "page_num": 3, "font_name": "Courier", "font_size": 10.0}'
        
        span = TextSpanMetrics.from_json(json_str)
        
        assert span.text == "From JSON"
        assert span.page_num == 3
        assert span.font_name == "Courier"
    
    def test_roundtrip_json(self):
        """Roundtrip: to_json -> from_json."""
        original = TextSpanMetrics(
            text="JSON roundtrip",
            page_num=7,
            char_spacing=0.3,
        )
        
        restored = TextSpanMetrics.from_json(original.to_json())
        
        assert restored.text == original.text
        assert restored.page_num == original.page_num
        assert restored.char_spacing == original.char_spacing


class TestCreateSpanFromPyMuPDF:
    """Tests para función factory create_span_from_pymupdf."""
    
    def test_basic_span_dict(self):
        """Crear desde span dict básico de PyMuPDF."""
        span_dict = {
            "text": "Hello World",
            "bbox": (72.0, 100.0, 200.0, 115.0),
            "font": "Helvetica",
            "size": 12.0,
            "color": 0,  # Negro en formato int
            "flags": 0,
        }
        
        span = create_span_from_pymupdf(span_dict, page_num=0)
        
        assert span.text == "Hello World"
        assert span.page_num == 0
        assert span.bbox == (72.0, 100.0, 200.0, 115.0)
        assert span.font_name == "Helvetica"
        assert span.font_size == 12.0
        assert span.fill_color == "#000000"
    
    def test_color_conversion_rgb(self):
        """Convertir color int a hex correctamente."""
        # Rojo: en formato BGR de PyMuPDF
        span_dict = {
            "text": "Red",
            "bbox": (0, 0, 0, 0),
            "font": "Arial",
            "size": 12,
            "color": 0xFF,  # Rojo puro
        }
        
        span = create_span_from_pymupdf(span_dict, page_num=0)
        
        assert span.fill_color == "#ff0000"
    
    def test_color_conversion_blue(self):
        """Convertir azul."""
        span_dict = {
            "text": "Blue",
            "bbox": (0, 0, 0, 0),
            "font": "Arial",
            "size": 12,
            "color": 0xFF0000,  # Azul en BGR
        }
        
        span = create_span_from_pymupdf(span_dict, page_num=0)
        
        assert span.fill_color == "#0000ff"
    
    def test_subset_font_name_normalization(self):
        """Normalizar nombre de fuente subset."""
        span_dict = {
            "text": "Subset",
            "bbox": (0, 0, 0, 0),
            "font": "ABCDEF+Arial-Bold",
            "size": 12,
            "color": 0,
        }
        
        span = create_span_from_pymupdf(span_dict, page_num=0)
        
        assert span.font_name == "Arial-Bold"
        assert span.font_name_pdf == "ABCDEF+Arial-Bold"
        assert span.embedding_status == FontEmbeddingStatus.SUBSET
    
    def test_bold_detection_from_name(self):
        """Detectar bold por nombre de fuente."""
        span_dict = {
            "text": "Bold text",
            "bbox": (0, 0, 0, 0),
            "font": "Arial-Bold",
            "size": 12,
            "color": 0,
            "flags": 0,
        }
        
        span = create_span_from_pymupdf(span_dict, page_num=0)
        
        assert span.is_bold is True
    
    def test_italic_detection_from_name(self):
        """Detectar italic por nombre de fuente."""
        span_dict = {
            "text": "Italic text",
            "bbox": (0, 0, 0, 0),
            "font": "Times-Italic",
            "size": 12,
            "color": 0,
            "flags": 0,
        }
        
        span = create_span_from_pymupdf(span_dict, page_num=0)
        
        assert span.is_italic is True
    
    def test_char_widths_from_chars(self):
        """Extraer anchos de caracteres si hay info de chars."""
        span_dict = {
            "text": "ab",
            "bbox": (0, 0, 20, 12),
            "font": "Arial",
            "size": 12,
            "color": 0,
            "chars": [
                {"bbox": (0, 0, 8, 12)},
                {"bbox": (8, 0, 20, 12)},
            ]
        }
        
        span = create_span_from_pymupdf(span_dict, page_num=0)
        
        assert span.char_widths == [8.0, 12.0]
    
    def test_origin_from_span_dict(self):
        """Extraer origen si está disponible."""
        span_dict = {
            "text": "With origin",
            "bbox": (10, 20, 100, 35),
            "origin": (10, 32),
            "font": "Arial",
            "size": 12,
            "color": 0,
        }
        
        span = create_span_from_pymupdf(span_dict, page_num=0)
        
        assert span.origin == (10, 32)
    
    def test_handles_missing_optional_fields(self):
        """Manejar campos opcionales faltantes."""
        span_dict = {
            "text": "Minimal",
        }
        
        span = create_span_from_pymupdf(span_dict, page_num=0)
        
        assert span.text == "Minimal"
        assert span.font_name == "Helvetica"
        assert span.font_size == 12.0


class TestCreateEmptySpan:
    """Tests para función factory create_empty_span."""
    
    def test_create_empty_defaults(self):
        """Crear span vacío con defaults."""
        span = create_empty_span()
        
        assert span.text == ""
        assert span.page_num == 0
        assert span.font_name == "Helvetica"
        assert span.font_size == 12.0
    
    def test_create_empty_with_params(self):
        """Crear span vacío con parámetros custom."""
        span = create_empty_span(
            page_num=5,
            font_name="Arial",
            font_size=14.0
        )
        
        assert span.text == ""
        assert span.page_num == 5
        assert span.font_name == "Arial"
        assert span.font_size == 14.0


class TestRepresentation:
    """Tests para __repr__ y __str__."""
    
    def test_repr_short_text(self):
        """repr con texto corto."""
        span = TextSpanMetrics(
            text="Short",
            page_num=0,
            font_name="Arial",
            font_size=12.0
        )
        
        r = repr(span)
        
        assert "Short" in r
        assert "Arial" in r
        assert "12.0pt" in r
    
    def test_repr_long_text_truncated(self):
        """repr con texto largo se trunca."""
        span = TextSpanMetrics(
            text="This is a very long text that should be truncated in repr",
            page_num=0,
        )
        
        r = repr(span)
        
        assert "..." in r
        assert len(r) < 200
    
    def test_str(self):
        """__str__ muestra ID y resumen."""
        span = TextSpanMetrics(
            text="Test",
            page_num=0,
            font_name="Times",
            font_size=14.0,
        )
        
        s = str(span)
        
        assert span.span_id in s
        assert "Test" in s
        assert "Times" in s
    
    def test_detailed_info(self):
        """detailed_info genera info completa."""
        span = TextSpanMetrics(
            text="Detailed test",
            page_num=2,
            bbox=(10, 20, 100, 35),
            font_name="Arial",
            font_size=12.0,
            char_spacing=0.5,
            was_fallback=True,
            fallback_from="CustomFont",
        )
        
        info = span.detailed_info()
        
        assert "Detailed test" in info
        assert "Page: 2" in info
        assert "Arial" in info
        assert "Char Spacing" in info
        assert "Fallback" in info
        assert "CustomFont" in info


class TestRenderModeEnum:
    """Tests para enum RenderMode."""
    
    def test_render_mode_values(self):
        """Verificar valores de RenderMode."""
        assert RenderMode.FILL == 0
        assert RenderMode.STROKE == 1
        assert RenderMode.FILL_STROKE == 2
        assert RenderMode.INVISIBLE == 3
    
    def test_render_mode_names(self):
        """Verificar nombres de RenderMode."""
        assert RenderMode(0).name == "FILL"
        assert RenderMode(1).name == "STROKE"


class TestFontEmbeddingStatusEnum:
    """Tests para enum FontEmbeddingStatus."""
    
    def test_embedding_status_values(self):
        """Verificar valores de FontEmbeddingStatus."""
        assert FontEmbeddingStatus.NOT_EMBEDDED.value == "not_embedded"
        assert FontEmbeddingStatus.FULLY_EMBEDDED.value == "fully_embedded"
        assert FontEmbeddingStatus.SUBSET.value == "subset"
        assert FontEmbeddingStatus.UNKNOWN.value == "unknown"

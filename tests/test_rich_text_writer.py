"""
Tests para RichTextWriter.

Verifica:
- Generación de HTML desde spans
- Escritura al PDF via insert_htmlbox
- Fallback cuando falla
- Detección de cambios de formato
"""

import pytest
from unittest.mock import MagicMock, patch
import fitz


class TestRichTextWriterHTML:
    """Tests para la generación de HTML desde spans."""
    
    def test_simple_span_html(self):
        """Genera HTML básico para un span sin formato especial."""
        from core.text_engine.rich_text_writer import RichTextWriter
        from core.text_engine.page_document_model import EditableSpan
        
        span = EditableSpan(
            original_text="Hello World",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        page = MagicMock()
        doc = MagicMock()
        writer = RichTextWriter(page, doc)
        html = writer._spans_to_html([span])
        
        assert "Hello World" in html
        assert "font-size:12.0pt" in html
        assert "font-family:" in html
    
    def test_bold_span_html(self):
        """Genera HTML con font-weight:bold."""
        from core.text_engine.rich_text_writer import RichTextWriter
        from core.text_engine.page_document_model import EditableSpan
        
        span = EditableSpan(
            original_text="Bold text",
            font_name="Helvetica",
            font_size=12.0,
            is_bold=True,
        )
        
        page = MagicMock()
        doc = MagicMock()
        writer = RichTextWriter(page, doc)
        html = writer._spans_to_html([span])
        
        assert "font-weight:bold" in html
    
    def test_italic_span_html(self):
        """Genera HTML con font-style:italic."""
        from core.text_engine.rich_text_writer import RichTextWriter
        from core.text_engine.page_document_model import EditableSpan
        
        span = EditableSpan(
            original_text="Italic text",
            font_name="Helvetica",
            font_size=12.0,
            is_italic=True,
        )
        
        page = MagicMock()
        doc = MagicMock()
        writer = RichTextWriter(page, doc)
        html = writer._spans_to_html([span])
        
        assert "font-style:italic" in html
    
    def test_color_span_html(self):
        """Genera HTML con color."""
        from core.text_engine.rich_text_writer import RichTextWriter
        from core.text_engine.page_document_model import EditableSpan
        
        span = EditableSpan(
            original_text="Red text",
            font_name="Helvetica",
            font_size=12.0,
            fill_color="#FF0000",
        )
        
        page = MagicMock()
        doc = MagicMock()
        writer = RichTextWriter(page, doc)
        html = writer._spans_to_html([span])
        
        assert "color:#FF0000" in html
    
    def test_char_spacing_html(self):
        """Genera HTML con letter-spacing."""
        from core.text_engine.rich_text_writer import RichTextWriter
        from core.text_engine.page_document_model import EditableSpan
        
        span = EditableSpan(
            original_text="Spaced",
            font_name="Helvetica",
            font_size=12.0,
            char_spacing=1.5,
        )
        
        page = MagicMock()
        doc = MagicMock()
        writer = RichTextWriter(page, doc)
        html = writer._spans_to_html([span])
        
        assert "letter-spacing:1.50pt" in html
    
    def test_format_changed_span_html(self):
        """Genera HTML usando effective_* cuando hay cambios de formato."""
        from core.text_engine.rich_text_writer import RichTextWriter
        from core.text_engine.page_document_model import EditableSpan
        
        span = EditableSpan(
            original_text="Changed",
            font_name="Helvetica",
            font_size=12.0,
            is_bold=False,
            new_font_size=18.0,
            new_is_bold=True,
            dirty_format=True,
        )
        
        page = MagicMock()
        doc = MagicMock()
        writer = RichTextWriter(page, doc)
        html = writer._spans_to_html([span])
        
        assert "font-size:18.0pt" in html
        assert "font-weight:bold" in html
    
    def test_html_escaping(self):
        """Caracteres especiales se escapan en el HTML."""
        from core.text_engine.rich_text_writer import RichTextWriter
        from core.text_engine.page_document_model import EditableSpan
        
        span = EditableSpan(
            original_text="<script>alert('xss')</script>",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        page = MagicMock()
        doc = MagicMock()
        writer = RichTextWriter(page, doc)
        html = writer._spans_to_html([span])
        
        assert "<script>" not in html
        assert "&lt;script&gt;" in html
    
    def test_multiple_spans_html(self):
        """Genera HTML para múltiples spans."""
        from core.text_engine.rich_text_writer import RichTextWriter
        from core.text_engine.page_document_model import EditableSpan
        
        spans = [
            EditableSpan(original_text="First ", font_size=12.0),
            EditableSpan(original_text="Second", font_size=14.0, is_bold=True),
        ]
        
        page = MagicMock()
        doc = MagicMock()
        writer = RichTextWriter(page, doc)
        html = writer._spans_to_html(spans)
        
        assert "First " in html
        assert "Second" in html
        assert html.count("<span") == 2


class TestRichTextWriterWrite:
    """Tests para la escritura al PDF."""
    
    def test_write_single_span_success(self):
        """Escritura exitosa de un solo span."""
        from core.text_engine.rich_text_writer import RichTextWriter
        from core.text_engine.page_document_model import EditableSpan
        
        span = EditableSpan(
            original_text="Hello",
            font_name="Helvetica",
            font_size=12.0,
            bbox=(10, 10, 100, 25),
        )
        
        page = MagicMock()
        page.insert_htmlbox.return_value = 0  # no overflow
        doc = MagicMock()
        
        writer = RichTextWriter(page, doc)
        result = writer.write_single_span(span)
        
        assert result.success is True
        assert result.overflow is False
        page.insert_htmlbox.assert_called_once()
    
    def test_write_with_overflow(self):
        """Detecta overflow cuando insert_htmlbox retorna > 0."""
        from core.text_engine.rich_text_writer import RichTextWriter
        from core.text_engine.page_document_model import EditableSpan
        
        span = EditableSpan(
            original_text="Long text that overflows",
            font_name="Helvetica",
            font_size=12.0,
            bbox=(10, 10, 50, 25),  # very small bbox
        )
        
        page = MagicMock()
        page.insert_htmlbox.return_value = 42  # overflow
        doc = MagicMock()
        
        writer = RichTextWriter(page, doc)
        result = writer.write_spans([span])
        
        assert result.success is True
        assert result.overflow is True
    
    def test_write_empty_spans(self):
        """Lista vacía retorna éxito."""
        from core.text_engine.rich_text_writer import RichTextWriter
        
        page = MagicMock()
        doc = MagicMock()
        writer = RichTextWriter(page, doc)
        result = writer.write_spans([])
        
        assert result.success is True
    
    def test_write_failure(self):
        """Fallo de insert_htmlbox se maneja gracefully."""
        from core.text_engine.rich_text_writer import RichTextWriter
        from core.text_engine.page_document_model import EditableSpan
        
        span = EditableSpan(
            original_text="Fail",
            font_size=12.0,
            bbox=(10, 10, 100, 25),
        )
        
        page = MagicMock()
        page.insert_htmlbox.side_effect = RuntimeError("API error")
        doc = MagicMock()
        
        writer = RichTextWriter(page, doc)
        result = writer.write_spans([span])
        
        assert result.success is False
        assert result.error is not None


class TestRichTextWriterFontMapping:
    """Tests para la resolución de familias de fuentes."""
    
    def test_helvetica_mapping(self):
        from core.text_engine.rich_text_writer import RichTextWriter
        
        page = MagicMock()
        doc = MagicMock()
        writer = RichTextWriter(page, doc)
        
        family = writer._resolve_font_family("Helvetica")
        assert "Helvetica" in family
    
    def test_times_mapping(self):
        from core.text_engine.rich_text_writer import RichTextWriter
        
        page = MagicMock()
        doc = MagicMock()
        writer = RichTextWriter(page, doc)
        
        family = writer._resolve_font_family("Times")
        assert "Times" in family
    
    def test_unknown_font_fallback(self):
        from core.text_engine.rich_text_writer import RichTextWriter
        
        page = MagicMock()
        doc = MagicMock()
        writer = RichTextWriter(page, doc)
        
        family = writer._resolve_font_family("MyCustomFont")
        assert "MyCustomFont" in family
    
    def test_spans_have_format_changes(self):
        from core.text_engine.rich_text_writer import RichTextWriter
        from core.text_engine.page_document_model import EditableSpan
        
        spans = [
            EditableSpan(original_text="no change"),
            EditableSpan(original_text="changed", dirty_format=True),
        ]
        assert RichTextWriter.spans_have_format_changes(spans) is True
    
    def test_spans_no_format_changes(self):
        from core.text_engine.rich_text_writer import RichTextWriter
        from core.text_engine.page_document_model import EditableSpan
        
        spans = [
            EditableSpan(original_text="no change"),
        ]
        assert RichTextWriter.spans_have_format_changes(spans) is False


class TestComputeRect:
    """Tests para cálculo de rectángulos."""
    
    def test_single_span_rect(self):
        from core.text_engine.rich_text_writer import RichTextWriter
        from core.text_engine.page_document_model import EditableSpan
        
        span = EditableSpan(bbox=(10, 20, 100, 35))
        
        page = MagicMock()
        doc = MagicMock()
        writer = RichTextWriter(page, doc)
        rect = writer._compute_rect([span])
        
        assert rect.x0 == pytest.approx(9.5)
        assert rect.y0 == pytest.approx(19.5)
        assert rect.x1 == pytest.approx(100.5)
        assert rect.y1 == pytest.approx(35.5)
    
    def test_multiple_spans_rect(self):
        from core.text_engine.rich_text_writer import RichTextWriter
        from core.text_engine.page_document_model import EditableSpan
        
        spans = [
            EditableSpan(bbox=(10, 20, 50, 35)),
            EditableSpan(bbox=(55, 20, 120, 35)),
        ]
        
        page = MagicMock()
        doc = MagicMock()
        writer = RichTextWriter(page, doc)
        rect = writer._compute_rect(spans)
        
        assert rect.x0 == pytest.approx(9.5)
        assert rect.x1 == pytest.approx(120.5)

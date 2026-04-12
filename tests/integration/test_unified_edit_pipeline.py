"""
Tests para el pipeline unificado de edición de texto PDF.

Verifica el flujo completo:
    PageDocumentModel → (edición) → PageWriter → PDF actualizado

Cubre:
1. PageDocumentModel: parseo de página, búsqueda de spans
2. PageWriter: redacción + reescritura con TextWriter
3. Ciclo completo: parsear → editar → escribir → verificar
"""

import pytest
import fitz
from typing import List

from core.text_engine.page_document_model import (
    EditableSpan, LineModel, PageDocumentModel
)
from core.text_engine.page_writer import PageWriter


# ============================================================================
# Helpers
# ============================================================================

def _create_test_pdf(texts: List[dict] = None) -> fitz.Document:
    """Crea un PDF de prueba con textos posicionados.
    
    Args:
        texts: Lista de dicts con keys: text, point, fontsize, color, fontname
               Si None, crea un PDF con textos por defecto.
    """
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    
    if texts is None:
        texts = [
            {"text": "Título del documento", "point": (72, 72), "fontsize": 18, "fontname": "hebo"},
            {"text": "Primer párrafo de texto.", "point": (72, 120), "fontsize": 12, "fontname": "helv"},
            {"text": "Segunda línea del párrafo.", "point": (72, 136), "fontsize": 12, "fontname": "helv"},
            {"text": "Texto en negrita aquí.", "point": (72, 180), "fontsize": 12, "fontname": "hebo"},
        ]
    
    tw = fitz.TextWriter(page.rect)
    for t in texts:
        font = fitz.Font(t.get("fontname", "helv"))
        tw.append(
            fitz.Point(t["point"][0], t["point"][1]),
            t["text"],
            font=font,
            fontsize=t.get("fontsize", 12),
        )
    
    color = (0, 0, 0)
    tw.write_text(page, color=color)
    return doc


# ============================================================================
# Test PageDocumentModel
# ============================================================================

class TestPageDocumentModel:
    """Tests para el parseo de páginas PDF en modelo editable."""
    
    def test_from_page_parses_spans(self):
        """Verifica que from_page extrae spans del PDF."""
        doc = _create_test_pdf()
        page = doc[0]
        model = PageDocumentModel.from_page(page, page_num=0)
        
        assert len(model.all_spans) > 0
        assert model.page_num == 0
        assert model.page_rect is not None
        doc.close()
    
    def test_span_text_preserved(self):
        """Verifica que el texto extraído coincide con el original."""
        doc = _create_test_pdf()
        page = doc[0]
        model = PageDocumentModel.from_page(page, page_num=0)
        
        all_text = model.full_text
        assert "Título del documento" in all_text
        assert "Primer párrafo" in all_text
        assert "Segunda línea" in all_text
        doc.close()
    
    def test_spans_in_rect(self):
        """Verifica búsqueda de spans por rectángulo."""
        doc = _create_test_pdf()
        page = doc[0]
        model = PageDocumentModel.from_page(page, page_num=0)
        
        # Rect que cubre el título (alrededor de y=72)
        rect = fitz.Rect(60, 50, 400, 80)
        spans = model.spans_in_rect(rect)
        
        assert len(spans) > 0
        title_text = " ".join(s.text for s in spans)
        assert "Título" in title_text
        doc.close()
    
    def test_find_span_at(self):
        """Verifica búsqueda de span por coordenadas."""
        doc = _create_test_pdf()
        page = doc[0]
        model = PageDocumentModel.from_page(page, page_num=0)
        
        # Buscar en la zona del primer span (título)
        # Los spans tienen bbox, buscar dentro de uno
        first_span = model.all_spans[0]
        x0, y0, x1, y1 = first_span.bbox
        mid_x = (x0 + x1) / 2
        mid_y = (y0 + y1) / 2
        
        found = model.find_span_at(mid_x, mid_y)
        assert found is not None
        assert found.span_id == first_span.span_id
        doc.close()
    
    def test_empty_page(self):
        """Verifica que una página vacía produce modelo vacío."""
        doc = fitz.open()
        page = doc.new_page()
        model = PageDocumentModel.from_page(page, page_num=0)
        
        assert len(model.all_spans) == 0
        assert len(model.paragraphs) == 0
        assert model.full_text == ""
        doc.close()
    
    def test_editable_span_dirty_tracking(self):
        """Verifica que el tracking de cambios funciona."""
        span = EditableSpan(
            span_id="test1",
            original_text="Hello",
            font_size=12.0,
            font_name="Helvetica",
        )
        
        assert not span.dirty
        assert span.text == "Hello"
        
        span.text = "World"
        assert span.dirty
        assert span.text == "World"
        assert span.original_text == "Hello"
        
        # Revertir
        span.text = "Hello"
        assert not span.dirty
    
    def test_span_color_rgb(self):
        """Verifica conversión de color hex a RGB."""
        span = EditableSpan(fill_color="#ff0000")
        r, g, b = span.color_rgb
        assert abs(r - 1.0) < 0.01
        assert abs(g - 0.0) < 0.01
        assert abs(b - 0.0) < 0.01
    
    def test_dirty_spans_property(self):
        """Verifica que dirty_spans retorna solo los modificados."""
        doc = _create_test_pdf()
        page = doc[0]
        model = PageDocumentModel.from_page(page, page_num=0)
        
        assert len(model.dirty_spans) == 0
        
        # Modificar un span
        first_span = model.all_spans[0]
        first_span.text = "Texto cambiado"
        
        assert len(model.dirty_spans) == 1
        assert model.dirty_spans[0].span_id == first_span.span_id
        doc.close()


# ============================================================================
# Test PageWriter
# ============================================================================

class TestPageWriter:
    """Tests para la escritura de spans editados al PDF."""
    
    def test_apply_edits_modifies_text(self):
        """Verifica que apply_edits cambia el texto en el PDF."""
        doc = _create_test_pdf()
        page = doc[0]
        
        # Parsear y editar
        model = PageDocumentModel.from_page(page, page_num=0)
        first_span = model.all_spans[0]
        original_text = first_span.original_text
        first_span.text = "REEMPLAZADO"
        
        # Aplicar
        writer = PageWriter(doc, page_num=0)
        result = writer.apply_edits(model.dirty_spans)
        
        assert result is True
        
        # Verificar que el texto cambió en el PDF
        page = doc[0]  # Re-obtener página después de redact
        new_text = page.get_text()
        assert "REEMPLAZADO" in new_text
        assert original_text not in new_text
        doc.close()
    
    def test_apply_edits_no_changes(self):
        """Verifica que no hace nada si no hay cambios."""
        doc = _create_test_pdf()
        
        writer = PageWriter(doc, page_num=0)
        result = writer.apply_edits([])
        
        assert result is False
        doc.close()
    
    def test_preserves_unedited_text(self):
        """Verifica que el texto no editado se preserva."""
        doc = _create_test_pdf()
        page = doc[0]
        
        model = PageDocumentModel.from_page(page, page_num=0)
        # Solo editar el primer span
        model.all_spans[0].text = "CAMBIADO"
        
        writer = PageWriter(doc, page_num=0)
        writer.apply_edits(model.dirty_spans)
        
        # Verificar que los otros textos siguen
        page = doc[0]
        text = page.get_text()
        assert "CAMBIADO" in text
        assert "Primer párrafo" in text  # Texto no editado preservado
        doc.close()
    
    def test_write_single_span(self):
        """Verifica escritura de un solo span."""
        doc = fitz.open()
        _page = doc.new_page()
        
        span = EditableSpan(
            original_text="Test",
            new_text="Test",
            bbox=(72, 60, 150, 80),
            origin=(72, 72),
            font_name="Helvetica",
            font_size=12.0,
            fill_color="#000000",
        )
        
        writer = PageWriter(doc, page_num=0)
        result = writer.write_single_span(span)
        
        assert result is True
        text = doc[0].get_text()
        assert "Test" in text
        doc.close()
    
    def test_erase_rect(self):
        """Verifica borrado de un área rectangular."""
        doc = _create_test_pdf()
        page = doc[0]
        
        # Verificar que el título existe
        text_before = page.get_text()
        assert "Título del documento" in text_before
        
        # Borrar área del título
        writer = PageWriter(doc, page_num=0)
        writer.erase_rect(fitz.Rect(60, 50, 400, 80))
        
        # Verificar que desapareció
        page = doc[0]
        text_after = page.get_text()
        assert "Título del documento" not in text_after
        doc.close()
    
    def test_font_resolution_base14(self):
        """Verifica mapeo de fuentes a base14."""
        doc = _create_test_pdf()
        writer = PageWriter(doc, page_num=0)
        
        # Helvetica
        assert writer._map_to_base14("Helvetica", False) == "helv"
        assert writer._map_to_base14("Helvetica", True) == "hebo"
        
        # Arial → Helvetica
        assert writer._map_to_base14("Arial", False) == "helv"
        
        # Times
        assert writer._map_to_base14("Times New Roman", False) == "tiro"
        assert writer._map_to_base14("Times New Roman", True) == "tibo"
        
        # Courier
        assert writer._map_to_base14("Courier", False) == "cour"
        
        # Unknown → Helvetica
        assert writer._map_to_base14("MiFuenteExotica", False) == "helv"
        doc.close()


# ============================================================================
# Test ciclo completo
# ============================================================================

class TestFullEditCycle:
    """Tests del ciclo completo: parsear → editar → escribir → verificar."""
    
    def test_edit_and_verify(self):
        """Ciclo completo: editar texto y verificar resultado."""
        doc = _create_test_pdf()
        page = doc[0]
        
        # 1. Parsear
        model = PageDocumentModel.from_page(page, page_num=0)
        
        # 2. Encontrar span del título
        title_spans = [s for s in model.all_spans if "Título" in s.original_text]
        assert len(title_spans) > 0
        
        # 3. Editar
        title_spans[0].text = "Nuevo Título"
        
        # 4. Escribir
        writer = PageWriter(doc, page_num=0)
        writer.apply_edits(model.dirty_spans)
        
        # 5. Verificar re-parseando
        page = doc[0]
        model2 = PageDocumentModel.from_page(page, page_num=0)
        all_text = model2.full_text
        
        assert "Nuevo Título" in all_text
        assert "Título del documento" not in all_text
        doc.close()
    
    def test_multiple_edits(self):
        """Verifica que se pueden hacer múltiples ediciones."""
        doc = _create_test_pdf()
        page = doc[0]
        
        model = PageDocumentModel.from_page(page, page_num=0)
        
        # Editar varios spans
        for span in model.all_spans:
            span.text = span.original_text.upper()
        
        writer = PageWriter(doc, page_num=0)
        writer.apply_edits(model.dirty_spans)
        
        # Verificar
        page = doc[0]
        text = page.get_text()
        # Al menos algún texto debería estar en mayúsculas
        assert any(word.isupper() for word in text.split() if len(word) > 2)
        doc.close()
    
    def test_sequential_edits(self):
        """Verifica ediciones secuenciales (editar, re-parsear, editar de nuevo)."""
        doc = _create_test_pdf()
        
        # Primera edición
        model1 = PageDocumentModel.from_page(doc[0], page_num=0)
        first_span = model1.all_spans[0]
        first_span.text = "Paso 1"
        
        writer1 = PageWriter(doc, page_num=0)
        writer1.apply_edits(model1.dirty_spans)
        
        # Re-parsear y segunda edición
        model2 = PageDocumentModel.from_page(doc[0], page_num=0)
        paso1_spans = [s for s in model2.all_spans if "Paso 1" in s.original_text]
        assert len(paso1_spans) > 0
        
        paso1_spans[0].text = "Paso 2"
        writer2 = PageWriter(doc, page_num=0)
        writer2.apply_edits(model2.dirty_spans)
        
        # Verificar resultado final
        text = doc[0].get_text()
        assert "Paso 2" in text
        assert "Paso 1" not in text
        doc.close()
    
    def test_edit_preserves_font_info(self):
        """Verifica que la información de fuente se preserva al parsear."""
        doc = _create_test_pdf()
        page = doc[0]
        
        model = PageDocumentModel.from_page(page, page_num=0)
        
        # El título usa hebo (bold), el párrafo usa helv
        for span in model.all_spans:
            assert span.font_size > 0
            assert span.font_name != ""
            assert span.bbox != (0, 0, 0, 0)
            assert span.origin != (0, 0)
        
        doc.close()


# ============================================================================
# Test UnifiedTextEditor (sin GUI, solo lógica)
# ============================================================================

class TestEditableSpanLogic:
    """Tests de la lógica de EditableSpan sin necesitar GUI."""
    
    def test_text_setter_tracks_changes(self):
        span = EditableSpan(original_text="abc", span_id="s1")
        assert span.text == "abc"
        assert not span.dirty
        
        span.text = "xyz"
        assert span.text == "xyz"
        assert span.dirty
        assert span.new_text == "xyz"
    
    def test_text_setter_revert(self):
        span = EditableSpan(original_text="abc", span_id="s1")
        span.text = "xyz"
        assert span.dirty
        
        span.text = "abc"  # Revertir al original
        assert not span.dirty
        assert span.new_text is None
    
    def test_color_rgb_conversion(self):
        span = EditableSpan(fill_color="#00ff80")
        r, g, b = span.color_rgb
        assert abs(r - 0.0) < 0.01
        assert abs(g - 1.0) < 0.01
        assert abs(b - 128/255) < 0.01
    
    def test_from_span_metrics(self):
        """Verifica conversión desde TextSpanMetrics."""
        from core.text_engine.text_span import TextSpanMetrics
        
        sm = TextSpanMetrics(
            span_id="test_span",
            page_num=0,
            text="Hello World",
            bbox=(10, 20, 100, 35),
            origin=(10, 32),
            baseline_y=32.0,
            font_name="Arial",
            font_name_pdf="Arial-Regular",
            font_size=14.0,
            is_bold=True,
            is_italic=False,
            fill_color="#333333",
        )
        
        es = EditableSpan.from_span_metrics(sm)
        assert es.span_id == "test_span"
        assert es.original_text == "Hello World"
        assert es.font_size == 14.0
        assert es.is_bold is True
        assert es.fill_color == "#333333"
        assert not es.dirty


class TestLineModel:
    """Tests para LineModel."""
    
    def test_text_concatenation(self):
        spans = [
            EditableSpan(original_text="Hello ", span_id="s1"),
            EditableSpan(original_text="World", span_id="s2"),
        ]
        line = LineModel(spans=spans, line_id="l1")
        
        assert line.text == "Hello World"
    
    def test_dirty_detection(self):
        spans = [
            EditableSpan(original_text="Hello", span_id="s1"),
            EditableSpan(original_text="World", span_id="s2"),
        ]
        line = LineModel(spans=spans, line_id="l1")
        
        assert not line.is_dirty
        
        spans[1].text = "Changed"
        assert line.is_dirty
    
    def test_dominant_font(self):
        spans = [
            EditableSpan(original_text="Hi", font_name="Arial", span_id="s1"),
            EditableSpan(original_text="This is longer text", font_name="Times", span_id="s2"),
        ]
        line = LineModel(spans=spans, line_id="l1")
        
        assert line.dominant_font == "Times"  # Más texto


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

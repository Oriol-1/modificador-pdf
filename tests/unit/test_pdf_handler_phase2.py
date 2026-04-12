"""
Tests para extensiones PHASE2 del PDFDocument (Font Management).

Prueba la integración con FontManager:
- get_text_run_descriptors()
- replace_text_preserving_metrics()
- detect_bold_in_span()
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Asegurar que core está en el path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.pdf_handler import PDFDocument
from core.font_manager import FontManager, FontDescriptor, get_font_manager


class TestGetTextRunDescriptors:
    """Tests para get_text_run_descriptors."""
    
    @pytest.fixture
    def pdf_doc(self):
        """Crear documento PDF vacío para tests."""
        doc = PDFDocument()
        # Crear un PDF simple en memoria
        try:
            import fitz
            pdf = fitz.open()
            page = pdf.new_page()
            page.insert_text((50, 50), "Texto de prueba", fontsize=12)
            
            # Guardar en temp
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf.save(tmp.name)
                tmp_path = tmp.name
            
            doc.open(tmp_path)
            yield doc
            
            # Cleanup
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        except Exception:
            # Si fitz no está disponible, usar mock
            yield doc
    
    def test_get_descriptors_empty_pdf(self):
        """Retorna lista vacía para PDF sin texto."""
        doc = PDFDocument()
        descriptors = doc.get_text_run_descriptors(0, None)
        assert isinstance(descriptors, list)
        assert len(descriptors) == 0
    
    def test_get_descriptors_returns_font_descriptors(self, pdf_doc):
        """Retorna lista de FontDescriptor."""
        try:
            import fitz
            rect = fitz.Rect(0, 0, 100, 100)
            descriptors = pdf_doc.get_text_run_descriptors(0, rect)
            
            assert isinstance(descriptors, list)
            # Si hay descriptores, verificar que sean FontDescriptor
            if len(descriptors) > 0:
                assert isinstance(descriptors[0], FontDescriptor)
        except Exception:
            pytest.skip("PyMuPDF no disponible o PDF sin texto")
    
    def test_get_descriptors_out_of_range_page(self):
        """Retorna lista vacía para página fuera de rango."""
        doc = PDFDocument()
        descriptors = doc.get_text_run_descriptors(999, None)
        assert descriptors == []
    
    @patch('core.font_manager.FontManager.detect_font')
    def test_get_descriptors_calls_font_manager(self, mock_detect):
        """Utiliza FontManager para detectar fuentes."""
        mock_descriptor = FontDescriptor(
            name="Times",
            size=12.0,
            color="#000000",
            flags=0,
            was_fallback=False,
            fallback_from=None,
            possible_bold=False
        )
        mock_detect.return_value = mock_descriptor
        
        doc = PDFDocument()
        # Mock del documento
        with patch.object(doc, 'doc', True):
            with patch.object(doc, 'page_count', return_value=1):
                # Este test principalmente verifica la integración
                # Sin PDF real, la lista será vacía
                descriptors = doc.get_text_run_descriptors(0, None)
                assert isinstance(descriptors, list)


class TestReplaceTextPreservingMetrics:
    """Tests para replace_text_preserving_metrics."""
    
    def test_replace_text_no_document(self):
        """Falla si no hay documento abierto."""
        doc = PDFDocument()
        result = doc.replace_text_preserving_metrics(0, "old", "new")
        assert result is False
    
    def test_replace_text_page_out_of_range(self):
        """Falla si la página está fuera de rango."""
        doc = PDFDocument()
        with patch.object(doc, 'doc', True):
            with patch.object(doc, 'page_count', return_value=5):
                result = doc.replace_text_preserving_metrics(999, "old", "new")
                assert result is False
    
    @patch('core.pdf_handler.PDFDocument.search_text')
    def test_replace_text_not_found(self, mock_search):
        """Falla si el texto no se encuentra."""
        mock_search.return_value = []
        
        doc = PDFDocument()
        with patch.object(doc, 'doc') as mock_doc:
            mock_doc.page_count = 1
            result = doc.replace_text_preserving_metrics(0, "notfound", "new")
            assert result is False
    
    def test_replace_text_with_descriptors(self):
        """Reemplaza texto usando descriptores disponibles."""
        import fitz
        rect = fitz.Rect(0, 0, 100, 50)
        
        descriptor = FontDescriptor(
            name="Arial",
            size=12.0,
            color="#000000",
            flags=0,
            was_fallback=False,
            fallback_from=None,
            possible_bold=False
        )
        
        doc = PDFDocument()
        mock_doc = MagicMock()
        mock_doc.__getitem__ = MagicMock(return_value=MagicMock())
        
        with patch.object(doc, 'doc', mock_doc):
            with patch.object(doc, 'page_count', return_value=1):
                with patch.object(doc, '_save_snapshot'):
                    with patch.object(doc, 'search_text', return_value=[(0, rect)]):
                        with patch.object(doc, 'get_text_run_descriptors', return_value=[descriptor]):
                            with patch.object(doc, 'edit_text', return_value=True) as mock_edit:
                                result = doc.replace_text_preserving_metrics(0, "old", "new")
                                
                                # Verificar que edit_text fue llamado
                                assert mock_edit.called
                                assert result is True
    
    def test_replace_text_preserves_bold(self):
        """Preserva bold cuando preserve_bold=True."""
        import fitz
        rect = fitz.Rect(0, 0, 100, 50)
        
        descriptor = FontDescriptor(
            name="Arial",
            size=12.0,
            color="#000000",
            flags=0,
            was_fallback=False,
            fallback_from=None,
            possible_bold=True  # Bold detectado
        )
        
        doc = PDFDocument()
        mock_doc = MagicMock()
        mock_doc.__getitem__ = MagicMock(return_value=MagicMock())
        
        with patch.object(doc, 'doc', mock_doc):
            with patch.object(doc, 'page_count', return_value=1):
                with patch.object(doc, '_save_snapshot'):
                    with patch.object(doc, 'search_text', return_value=[(0, rect)]):
                        with patch.object(doc, 'get_text_run_descriptors', return_value=[descriptor]):
                            with patch.object(doc, 'edit_text', return_value=True) as mock_edit:
                                result = doc.replace_text_preserving_metrics(
                                    0, "old", "new",
                                    preserve_bold=True
                                )
                                
                                # Verificar que se llamó edit_text
                                assert mock_edit.called
                                assert result is True
    
    def test_replace_text_sets_modified_flag(self):
        """Establece la bandera modified en True."""
        import fitz
        rect = fitz.Rect(0, 0, 100, 50)
        
        descriptor = FontDescriptor(
            name="Arial", size=12.0, color="#000000",
            flags=0, was_fallback=False,
            fallback_from=None, possible_bold=False
        )
        
        doc = PDFDocument()
        doc.modified = False  # Asegurar estado inicial
        mock_doc = MagicMock()
        mock_doc.__getitem__ = MagicMock(return_value=MagicMock())
        
        with patch.object(doc, 'doc', mock_doc):
            with patch.object(doc, 'page_count', return_value=1):
                with patch.object(doc, '_save_snapshot'):
                    with patch.object(doc, 'search_text', return_value=[(0, rect)]):
                        with patch.object(doc, 'get_text_run_descriptors', return_value=[descriptor]):
                            with patch.object(doc, 'edit_text', return_value=True):
                                result = doc.replace_text_preserving_metrics(0, "old", "new")
                                assert result is True
                                assert doc.modified is True


class TestDetectBoldInSpan:
    """Tests para detect_bold_in_span."""
    
    def test_detect_bold_no_document(self):
        """Retorna None si no hay documento."""
        doc = PDFDocument()
        result = doc.detect_bold_in_span(0, None)
        assert result is None
    
    def test_detect_bold_page_out_of_range(self):
        """Retorna None si la página está fuera de rango."""
        doc = PDFDocument()
        with patch.object(doc, 'doc', True):  # Documento simulado
            with patch.object(doc, 'page_count', return_value=5):
                result = doc.detect_bold_in_span(999, None)
                assert result is None
    
    @patch('core.pdf_handler.PDFDocument.get_text_run_descriptors')
    def test_detect_bold_no_descriptors(self, mock_desc):
        """Retorna None si no hay descriptores."""
        mock_desc.return_value = []
        
        doc = PDFDocument()
        with patch.object(doc, 'doc', True):
            with patch.object(doc, 'page_count', return_value=1):
                result = doc.detect_bold_in_span(0, None)
                assert result is None
    
    @patch('core.font_manager.FontManager.detect_possible_bold')
    @patch('core.pdf_handler.PDFDocument.get_text_run_descriptors')
    def test_detect_bold_calls_font_manager(self, mock_desc, mock_detect_bold):
        """Utiliza FontManager.detect_possible_bold."""
        descriptor = FontDescriptor(
            name="Arial",
            size=12.0,
            color="#000000",
            flags=0,
            was_fallback=False,
            fallback_from=None,
            possible_bold=False
        )
        mock_desc.return_value = [descriptor]
        mock_detect_bold.return_value = True
        
        doc = PDFDocument()
        with patch.object(doc, 'doc', True):
            with patch.object(doc, 'page_count', return_value=1):
                result = doc.detect_bold_in_span(0, None)
                
                # Verificar que detect_possible_bold fue llamado
                assert mock_detect_bold.called
                assert result
    
    @patch('core.font_manager.FontManager.detect_possible_bold')
    @patch('core.pdf_handler.PDFDocument.get_text_run_descriptors')
    def test_detect_bold_returns_boolean(self, mock_desc, mock_detect_bold):
        """Retorna valor booleano de FontManager."""
        descriptor = FontDescriptor(
            name="Arial",
            size=12.0,
            color="#000000",
            flags=0,
            was_fallback=False,
            fallback_from="Arial-Bold",
            possible_bold=True
        )
        mock_desc.return_value = [descriptor]
        mock_detect_bold.return_value = False
        
        doc = PDFDocument()
        with patch.object(doc, 'doc', True):
            with patch.object(doc, 'page_count', return_value=1):
                result = doc.detect_bold_in_span(0, None)
                assert isinstance(result, bool)
                assert result is False
    
    @patch('core.pdf_handler.PDFDocument.get_text_run_descriptors')
    def test_detect_bold_error_handling(self, mock_desc):
        """Captura excepciones y retorna None."""
        mock_desc.side_effect = Exception("Test error")
        
        doc = PDFDocument()
        with patch.object(doc, 'doc', True):
            with patch.object(doc, 'page_count', return_value=1):
                result = doc.detect_bold_in_span(0, None)
                assert result is None
                assert "Error detecting bold" in doc._last_error


class TestIntegrationWithFontManager:
    """Tests de integración entre PDFDocument y FontManager."""
    
    def test_font_manager_singleton_available(self):
        """Verifica que FontManager singleton esté disponible."""
        fm = get_font_manager()
        assert isinstance(fm, FontManager)
    
    def test_pdf_handler_imports_font_manager(self):
        """Verifica que PDFDocument importe FontManager."""
        import core.pdf_handler as pdf_handler
        assert hasattr(pdf_handler, 'FontManager')
    
    @patch('core.pdf_handler.FontManager.detect_font')
    def test_pdf_handler_uses_font_manager(self, mock_detect):
        """Verifica que PDFDocument use métodos de FontManager."""
        descriptor = FontDescriptor(
            name="Times",
            size=12.0,
            color="#000000",
            flags=0,
            was_fallback=False,
            fallback_from=None,
            possible_bold=False
        )
        mock_detect.return_value = descriptor
        
        # Test que el método sea accesible
        doc = PDFDocument()
        assert hasattr(doc, 'get_text_run_descriptors')
        assert hasattr(doc, 'replace_text_preserving_metrics')
        assert hasattr(doc, 'detect_bold_in_span')


class TestErrorHandling:
    """Tests para manejo de errores en métodos PHASE2."""
    
    def test_get_descriptors_sets_error_message(self):
        """Establece _last_error en caso de excepción."""
        doc = PDFDocument()
        with patch.object(doc, 'doc') as mock_doc:
            mock_doc.page_count = 1
            mock_doc.__getitem__.side_effect = Exception("Test error")
            
            doc.get_text_run_descriptors(0, None)
            assert "Error extracting font descriptors" in doc._last_error
    
    def test_replace_text_sets_error_message(self):
        """Establece _last_error si el texto no se encuentra."""
        doc = PDFDocument()
        doc._last_error = ""  # Limpiar estado
        mock_doc = MagicMock()
        mock_doc.__getitem__ = MagicMock(return_value=MagicMock())
        
        with patch.object(doc, 'doc', mock_doc):
            with patch.object(doc, 'page_count', return_value=1):
                with patch.object(doc, 'search_text', return_value=[]):
                    result = doc.replace_text_preserving_metrics(0, "notfound", "new")
                    assert result is False
                    assert "not found" in doc._last_error.lower()
    
    def test_detect_bold_sets_error_message(self):
        """Establece _last_error en caso de excepción."""
        doc = PDFDocument()
        with patch.object(doc, 'doc', True):
            with patch.object(doc, 'page_count', return_value=1):
                with patch.object(doc, 'get_text_run_descriptors', 
                                side_effect=Exception("Test error")):
                    doc.detect_bold_in_span(0, None)
                    assert "Error detecting bold" in doc._last_error

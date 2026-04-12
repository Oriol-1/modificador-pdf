"""Tests para la funcionalidad de inserción de imágenes en PDF.

Verifica el método PDFDocument.insert_image() con mocks.
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import fitz


class TestInsertImage:
    """Tests para PDFDocument.insert_image()."""

    @pytest.fixture
    def pdf_doc(self):
        """Fixture: PDFDocument con documento mock."""
        from core.pdf_handler import PDFDocument
        doc = PDFDocument()
        doc.doc = MagicMock()
        doc.doc.page_count = 3
        doc.modified = False
        doc._last_error = None
        doc._snapshots = []
        doc._snapshot_index = -1
        return doc

    @pytest.fixture
    def mock_page(self):
        """Fixture: página mock."""
        page = MagicMock()
        page.rect = fitz.Rect(0, 0, 595, 842)
        page.insert_image = MagicMock()
        return page

    def test_insert_image_success(self, pdf_doc, mock_page, tmp_path):
        """Insertar imagen con parámetros válidos."""
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
        
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        pdf_doc._save_snapshot = MagicMock()
        
        rect = fitz.Rect(10, 10, 200, 200)
        result = pdf_doc.insert_image(0, rect, str(img_file))
        
        assert result is True
        assert pdf_doc.modified is True
        mock_page.insert_image.assert_called_once()

    def test_insert_image_no_document(self, pdf_doc):
        """Falla sin documento abierto."""
        pdf_doc.doc = None
        result = pdf_doc.insert_image(0, fitz.Rect(0, 0, 100, 100), "test.png")
        assert result is False

    def test_insert_image_invalid_page(self, pdf_doc):
        """Falla con página inválida."""
        pdf_doc.get_page = MagicMock(return_value=None)
        result = pdf_doc.insert_image(99, fitz.Rect(0, 0, 100, 100), "test.png")
        assert result is False

    def test_insert_image_file_not_found(self, pdf_doc, mock_page):
        """Falla si el archivo de imagen no existe."""
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        result = pdf_doc.insert_image(0, fitz.Rect(0, 0, 100, 100), "/nonexistent.png")
        assert result is False
        assert "no encontrado" in pdf_doc._last_error

    def test_insert_image_saves_snapshot(self, pdf_doc, mock_page, tmp_path):
        """Guarda snapshot antes de insertar."""
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
        
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        pdf_doc._save_snapshot = MagicMock()
        
        pdf_doc.insert_image(0, fitz.Rect(0, 0, 100, 100), str(img_file))
        pdf_doc._save_snapshot.assert_called_once()

    def test_insert_image_keep_proportion(self, pdf_doc, mock_page, tmp_path):
        """Parámetro keep_proportion se pasa correctamente."""
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
        
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        pdf_doc._save_snapshot = MagicMock()
        
        pdf_doc.insert_image(0, fitz.Rect(0, 0, 100, 100), str(img_file), keep_proportion=False)
        call_kwargs = mock_page.insert_image.call_args[1]
        assert call_kwargs['keep_proportion'] is False

    def test_insert_image_overlay_false(self, pdf_doc, mock_page, tmp_path):
        """Parámetro overlay se pasa correctamente."""
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
        
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        pdf_doc._save_snapshot = MagicMock()
        
        pdf_doc.insert_image(0, fitz.Rect(0, 0, 100, 100), str(img_file), overlay=False)
        call_kwargs = mock_page.insert_image.call_args[1]
        assert call_kwargs['overlay'] is False

    def test_insert_image_exception_handled(self, pdf_doc, mock_page, tmp_path):
        """Excepciones se capturan y retornan False."""
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
        
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        pdf_doc._save_snapshot = MagicMock()
        mock_page.insert_image.side_effect = RuntimeError("bad image")
        
        result = pdf_doc.insert_image(0, fitz.Rect(0, 0, 100, 100), str(img_file))
        assert result is False
        assert "bad image" in pdf_doc._last_error

    def test_insert_image_rect_passed(self, pdf_doc, mock_page, tmp_path):
        """El rectángulo se pasa correctamente a PyMuPDF."""
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
        
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        pdf_doc._save_snapshot = MagicMock()
        
        rect = fitz.Rect(50, 100, 250, 300)
        pdf_doc.insert_image(0, rect, str(img_file))
        call_args = mock_page.insert_image.call_args[0]
        assert call_args[0] == rect

    def test_insert_image_marks_modified(self, pdf_doc, mock_page, tmp_path):
        """Marca el documento como modificado."""
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
        
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        pdf_doc._save_snapshot = MagicMock()
        
        assert pdf_doc.modified is False
        pdf_doc.insert_image(0, fitz.Rect(0, 0, 100, 100), str(img_file))
        assert pdf_doc.modified is True

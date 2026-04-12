"""Tests para las funcionalidades de anotaciones en PDF.

Verifica los métodos de PDFDocument para subrayado, tachado,
notas adhesivas, texto libre y eliminación de anotaciones.
"""
import pytest
from unittest.mock import MagicMock, patch
import fitz


class TestAnnotations:
    """Tests para métodos de anotación en PDFDocument."""

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
        doc._save_snapshot = MagicMock()
        return doc

    @pytest.fixture
    def mock_page(self):
        """Fixture: página mock con métodos de anotación."""
        page = MagicMock()
        page.rect = fitz.Rect(0, 0, 595, 842)
        
        mock_annot = MagicMock()
        mock_annot.set_colors = MagicMock()
        mock_annot.update = MagicMock()
        
        page.add_underline_annot = MagicMock(return_value=mock_annot)
        page.add_strikeout_annot = MagicMock(return_value=mock_annot)
        page.add_text_annot = MagicMock(return_value=mock_annot)
        page.add_freetext_annot = MagicMock(return_value=mock_annot)
        page.annots = MagicMock(return_value=[])
        page.delete_annot = MagicMock()
        return page

    # --- Underline ---

    def test_underline_success(self, pdf_doc, mock_page):
        """Subrayado exitoso marca modified."""
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        rect = fitz.Rect(10, 10, 200, 30)
        assert pdf_doc.add_underline_annot(0, rect) is True
        assert pdf_doc.modified is True

    def test_underline_no_page(self, pdf_doc):
        """Subrayado falla si la página no existe."""
        pdf_doc.get_page = MagicMock(return_value=None)
        assert pdf_doc.add_underline_annot(99, fitz.Rect(0, 0, 10, 10)) is False

    def test_underline_custom_color(self, pdf_doc, mock_page):
        """Subrayado con color personalizado."""
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        pdf_doc.add_underline_annot(0, fitz.Rect(0, 0, 10, 10), color=(0, 1, 0))
        mock_annot = mock_page.add_underline_annot.return_value
        mock_annot.set_colors.assert_called_once_with(stroke=(0, 1, 0))

    # --- Strikeout ---

    def test_strikeout_success(self, pdf_doc, mock_page):
        """Tachado exitoso marca modified."""
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        assert pdf_doc.add_strikeout_annot(0, fitz.Rect(0, 0, 10, 10)) is True
        assert pdf_doc.modified is True

    def test_strikeout_no_page(self, pdf_doc):
        """Tachado falla si la página no existe."""
        pdf_doc.get_page = MagicMock(return_value=None)
        assert pdf_doc.add_strikeout_annot(99, fitz.Rect(0, 0, 10, 10)) is False

    # --- Text annotation (sticky note) ---

    def test_text_annot_success(self, pdf_doc, mock_page):
        """Nota adhesiva exitosa."""
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        assert pdf_doc.add_text_annot(0, (100, 200), "Mi nota") is True
        assert pdf_doc.modified is True

    def test_text_annot_empty_text(self, pdf_doc, mock_page):
        """Nota adhesiva falla con texto vacío."""
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        assert pdf_doc.add_text_annot(0, (100, 200), "") is False

    def test_text_annot_no_page(self, pdf_doc):
        """Nota adhesiva falla sin página."""
        pdf_doc.get_page = MagicMock(return_value=None)
        assert pdf_doc.add_text_annot(99, (0, 0), "nota") is False

    # --- Freetext annotation ---

    def test_freetext_success(self, pdf_doc, mock_page):
        """Texto libre exitoso."""
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        rect = fitz.Rect(50, 50, 200, 100)
        assert pdf_doc.add_freetext_annot(0, rect, "Anotación libre") is True
        assert pdf_doc.modified is True

    def test_freetext_empty_text(self, pdf_doc, mock_page):
        """Texto libre falla con texto vacío."""
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        assert pdf_doc.add_freetext_annot(0, fitz.Rect(0, 0, 10, 10), "") is False

    def test_freetext_no_page(self, pdf_doc):
        """Texto libre falla sin página."""
        pdf_doc.get_page = MagicMock(return_value=None)
        assert pdf_doc.add_freetext_annot(99, fitz.Rect(0, 0, 10, 10), "texto") is False

    # --- Get annotations ---

    def test_get_annotations_empty(self, pdf_doc, mock_page):
        """Lista vacía cuando no hay anotaciones."""
        mock_page.annots.return_value = []
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        result = pdf_doc.get_annotations(0)
        assert result == []

    def test_get_annotations_no_page(self, pdf_doc):
        """Lista vacía con página inválida."""
        pdf_doc.get_page = MagicMock(return_value=None)
        assert pdf_doc.get_annotations(99) == []

    def test_get_annotations_with_annots(self, pdf_doc, mock_page):
        """Retorna info de anotaciones existentes."""
        mock_annot = MagicMock()
        mock_annot.type = (8, "Highlight")
        mock_annot.rect = fitz.Rect(10, 10, 100, 30)
        mock_annot.info = {'content': 'test note'}
        mock_annot.colors = {'stroke': (1, 0, 0)}
        mock_page.annots.return_value = [mock_annot]
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        
        result = pdf_doc.get_annotations(0)
        assert len(result) == 1
        assert result[0]['type'] == 8
        assert result[0]['content'] == 'test note'

    # --- Delete annotation ---

    def test_delete_annotation_success(self, pdf_doc, mock_page):
        """Elimina anotación cercana al punto."""
        mock_annot = MagicMock()
        mock_annot.rect = fitz.Rect(95, 195, 120, 220)
        mock_page.annots.return_value = [mock_annot]
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        
        result = pdf_doc.delete_annotation_at_point(0, (100, 200))
        assert result is True
        mock_page.delete_annot.assert_called_once_with(mock_annot)

    def test_delete_annotation_none_found(self, pdf_doc, mock_page):
        """No elimina si no hay anotación cerca."""
        mock_page.annots.return_value = []
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        result = pdf_doc.delete_annotation_at_point(0, (100, 200))
        assert result is False

    def test_delete_annotation_no_page(self, pdf_doc):
        """Falla con página inválida."""
        pdf_doc.get_page = MagicMock(return_value=None)
        assert pdf_doc.delete_annotation_at_point(99, (0, 0)) is False

    # --- Snapshot/Undo support ---

    def test_underline_saves_snapshot(self, pdf_doc, mock_page):
        """Subrayado guarda snapshot."""
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        pdf_doc.add_underline_annot(0, fitz.Rect(0, 0, 10, 10))
        pdf_doc._save_snapshot.assert_called_once()

    def test_strikeout_saves_snapshot(self, pdf_doc, mock_page):
        """Tachado guarda snapshot."""
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        pdf_doc.add_strikeout_annot(0, fitz.Rect(0, 0, 10, 10))
        pdf_doc._save_snapshot.assert_called_once()

    def test_text_annot_saves_snapshot(self, pdf_doc, mock_page):
        """Nota adhesiva guarda snapshot."""
        pdf_doc.get_page = MagicMock(return_value=mock_page)
        pdf_doc.add_text_annot(0, (0, 0), "nota")
        pdf_doc._save_snapshot.assert_called_once()

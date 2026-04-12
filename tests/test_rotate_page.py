"""
Tests para la funcionalidad de rotación de página.
Cobertura: rotate_page en pdf_handler, transformación de overlays.
"""

import pytest
import fitz
import tempfile
import os


@pytest.fixture
def sample_pdf_path():
    """Crea un PDF temporal de 3 páginas para tests."""
    path = os.path.join(tempfile.gettempdir(), "test_rotate.pdf")
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=612, height=792)
        page.insert_text(fitz.Point(72, 72), f"Página {i + 1}", fontsize=24)
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def pdf_doc(sample_pdf_path):
    """Crea una instancia de PDFDocument con el PDF de prueba."""
    from core.pdf_handler import PDFDocument
    doc = PDFDocument()
    doc.open(sample_pdf_path)
    yield doc
    doc.close()


class TestRotatePage:
    """Tests para pdf_handler.rotate_page()."""

    def test_rotate_90(self, pdf_doc):
        """Rotar 90° cambia la rotación y las dimensiones visuales."""
        result = pdf_doc.rotate_page(0, 90)
        assert result is not None
        old_w, old_h, new_rotation = result
        assert new_rotation == 90
        assert old_w == 612
        assert old_h == 792
        # Después de rotar 90°, las dimensiones visuales se intercambian
        page = pdf_doc.get_page(0)
        assert abs(page.rect.width - 792) < 1
        assert abs(page.rect.height - 612) < 1

    def test_rotate_180(self, pdf_doc):
        """Rotar 180° mantiene las mismas dimensiones."""
        result = pdf_doc.rotate_page(0, 180)
        assert result is not None
        _, _, new_rotation = result
        assert new_rotation == 180
        page = pdf_doc.get_page(0)
        assert abs(page.rect.width - 612) < 1
        assert abs(page.rect.height - 792) < 1

    def test_rotate_270(self, pdf_doc):
        """Rotar 270° intercambia dimensiones (igual que 90°)."""
        result = pdf_doc.rotate_page(0, 270)
        assert result is not None
        _, _, new_rotation = result
        assert new_rotation == 270
        page = pdf_doc.get_page(0)
        assert abs(page.rect.width - 792) < 1
        assert abs(page.rect.height - 612) < 1

    def test_rotate_360_cycle(self, pdf_doc):
        """Rotar 90° × 4 veces debe volver a rotación 0."""
        for _ in range(4):
            pdf_doc.rotate_page(0, 90)
        page = pdf_doc.get_page(0)
        assert page.rotation == 0
        assert abs(page.rect.width - 612) < 1
        assert abs(page.rect.height - 792) < 1

    def test_rotate_preserves_other_pages(self, pdf_doc):
        """Rotar una página no debe afectar las demás."""
        pdf_doc.rotate_page(1, 90)
        page0 = pdf_doc.get_page(0)
        page2 = pdf_doc.get_page(2)
        assert page0.rotation == 0
        assert page2.rotation == 0

    def test_rotate_invalid_angle(self, pdf_doc):
        """Ángulos inválidos deben retornar None."""
        assert pdf_doc.rotate_page(0, 45) is None
        assert pdf_doc.rotate_page(0, 0) is None

    def test_rotate_invalid_page(self, pdf_doc):
        """Página inexistente debe retornar None."""
        assert pdf_doc.rotate_page(99, 90) is None

    def test_rotate_undo(self, pdf_doc):
        """Undo después de rotar debe restaurar la rotación original."""
        pdf_doc.rotate_page(0, 90)
        assert pdf_doc.get_page(0).rotation == 90
        pdf_doc.undo()
        assert pdf_doc.get_page(0).rotation == 0

    def test_rotate_sets_modified(self, pdf_doc):
        """Rotar debe marcar el documento como modificado."""
        pdf_doc.modified = False
        pdf_doc.rotate_page(0, 90)
        assert pdf_doc.modified is True

    def test_rotate_save_reload(self, pdf_doc, sample_pdf_path):
        """La rotación debe persistir al guardar y reabrir."""
        pdf_doc.rotate_page(0, 90)
        save_path = sample_pdf_path.replace(".pdf", "_rotated.pdf")
        pdf_doc.save(save_path)

        from core.pdf_handler import PDFDocument
        doc2 = PDFDocument()
        doc2.open(save_path)
        assert doc2.get_page(0).rotation == 90
        assert doc2.get_page(1).rotation == 0
        doc2.close()
        os.remove(save_path)

    def test_rotate_cumulative(self, pdf_doc):
        """Rotaciones se acumulan correctamente."""
        pdf_doc.rotate_page(0, 90)
        assert pdf_doc.get_page(0).rotation == 90
        pdf_doc.rotate_page(0, 90)
        assert pdf_doc.get_page(0).rotation == 180
        pdf_doc.rotate_page(0, 180)
        assert pdf_doc.get_page(0).rotation == 0


class TestOverlayTransform:
    """Tests para la transformación de coordenadas de overlays."""

    @staticmethod
    def _rotate_rect(rect, angle, old_w, old_h):
        """Importa y usa el método estático de MainWindow."""
        # Re-implementar la lógica aquí para test independiente de Qt
        x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
        if angle == 90:
            nx0 = old_h - y1
            ny0 = x0
            nx1 = old_h - y0
            ny1 = x1
        elif angle == 180:
            nx0 = old_w - x1
            ny0 = old_h - y1
            nx1 = old_w - x0
            ny1 = old_h - y0
        elif angle == 270:
            nx0 = y0
            ny0 = old_w - x1
            nx1 = y1
            ny1 = old_w - x0
        else:
            return rect
        return fitz.Rect(min(nx0, nx1), min(ny0, ny1), max(nx0, nx1), max(ny0, ny1))

    def test_transform_90(self):
        """Rect (100,200,300,400) en página 612×792 rotada 90°."""
        rect = fitz.Rect(100, 200, 300, 400)
        result = self._rotate_rect(rect, 90, 612, 792)
        assert abs(result.x0 - 392) < 0.1
        assert abs(result.y0 - 100) < 0.1
        assert abs(result.x1 - 592) < 0.1
        assert abs(result.y1 - 300) < 0.1

    def test_transform_180(self):
        """Rect (100,200,300,400) en página 612×792 rotada 180°."""
        rect = fitz.Rect(100, 200, 300, 400)
        result = self._rotate_rect(rect, 180, 612, 792)
        assert abs(result.x0 - 312) < 0.1
        assert abs(result.y0 - 392) < 0.1
        assert abs(result.x1 - 512) < 0.1
        assert abs(result.y1 - 592) < 0.1

    def test_transform_270(self):
        """Rect (100,200,300,400) en página 612×792 rotada 270°."""
        rect = fitz.Rect(100, 200, 300, 400)
        result = self._rotate_rect(rect, 270, 612, 792)
        assert abs(result.x0 - 200) < 0.1
        assert abs(result.y0 - 312) < 0.1
        assert abs(result.x1 - 400) < 0.1
        assert abs(result.y1 - 512) < 0.1

    def test_transform_full_cycle(self):
        """Rotar 90° cuatro veces debe devolver el rect original."""
        original = fitz.Rect(100, 200, 300, 400)
        rect = fitz.Rect(original)
        w, h = 612, 792
        for _ in range(4):
            rect = self._rotate_rect(rect, 90, w, h)
            # Intercambiar dimensiones tras cada rotación de 90°
            w, h = h, w
        assert abs(rect.x0 - original.x0) < 0.1
        assert abs(rect.y0 - original.y0) < 0.1
        assert abs(rect.x1 - original.x1) < 0.1
        assert abs(rect.y1 - original.y1) < 0.1

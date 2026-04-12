"""Tests para core.ocr.pdf_ocr_layer — Capa de texto invisible OCR.

Usa documentos PDF sintéticos generados con PyMuPDF.
"""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock

import fitz

from core.ocr.pdf_ocr_layer import (
    is_scanned_page,
    detect_scanned_pages,
    page_image_to_numpy,
    insert_invisible_text,
    OCRPageResult,
    OCRDocumentResult,
)
from core.ocr.ocr_engine import OCRResult, OCRWord


# ═══════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def text_pdf():
    """PDF con texto normal (no escaneado)."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text(fitz.Point(72, 72), "Este es un documento de texto normal.", fontsize=12)
    page.insert_text(fitz.Point(72, 100), "Segunda línea de texto.", fontsize=12)
    return doc


@pytest.fixture
def scanned_pdf():
    """PDF que simula un documento escaneado (solo imagen, sin texto)."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    # Insertar una imagen sintética (bloque blanco)
    img_data = np.ones((100, 200, 3), dtype=np.uint8) * 200
    import cv2
    success, buf = cv2.imencode('.png', img_data)
    if success:
        page.insert_image(fitz.Rect(50, 50, 250, 150), stream=buf.tobytes())
    return doc


@pytest.fixture
def mixed_pdf(text_pdf, scanned_pdf):
    """PDF con páginas de texto y escaneadas."""
    doc = fitz.open()
    # Página con texto
    page1 = doc.new_page(width=595, height=842)
    page1.insert_text(fitz.Point(72, 72), "Página con texto real.", fontsize=12)
    # Página escaneada (solo imagen)
    page2 = doc.new_page(width=595, height=842)
    img_data = np.ones((100, 200, 3), dtype=np.uint8) * 200
    import cv2
    success, buf = cv2.imencode('.png', img_data)
    if success:
        page2.insert_image(fitz.Rect(50, 50, 250, 150), stream=buf.tobytes())
    return doc


@pytest.fixture
def sample_ocr_result():
    """Resultado OCR de ejemplo."""
    words = [
        OCRWord(text="Hola", x=100, y=200, width=80, height=25, confidence=95.0,
                block_num=1, par_num=1, line_num=1, word_num=1),
        OCRWord(text="Mundo", x=200, y=200, width=100, height=25, confidence=90.0,
                block_num=1, par_num=1, line_num=1, word_num=2),
        OCRWord(text="PDF", x=100, y=250, width=60, height=25, confidence=88.0,
                block_num=1, par_num=1, line_num=2, word_num=1),
    ]
    return OCRResult(
        text="Hola Mundo\nPDF",
        words=words,
        language="spa",
        avg_confidence=91.0,
        image_size=(600, 400),
    )


# ═══════════════════════════════════════════════════════════
# Tests: is_scanned_page
# ═══════════════════════════════════════════════════════════

class TestIsScannedPage:
    """Tests para detección de páginas escaneadas."""

    def test_text_page_not_scanned(self, text_pdf):
        page = text_pdf[0]
        assert is_scanned_page(page) is False

    @pytest.mark.skipif(
        not hasattr(fitz, 'open'), reason="PyMuPDF no disponible"
    )
    def test_scanned_page_detected(self, scanned_pdf):
        page = scanned_pdf[0]
        assert is_scanned_page(page) is True

    def test_empty_page_not_scanned(self):
        doc = fitz.open()
        page = doc.new_page()
        # Sin texto ni imagen → no es escaneada
        assert is_scanned_page(page) is False

    def test_custom_threshold(self, text_pdf):
        page = text_pdf[0]
        # Con threshold muy alto, debería considerar como escaneada
        assert is_scanned_page(page, text_threshold=1000) is False  # Pero no tiene imágenes


# ═══════════════════════════════════════════════════════════
# Tests: detect_scanned_pages
# ═══════════════════════════════════════════════════════════

class TestDetectScannedPages:
    """Tests para detección de páginas escaneadas en todo el documento."""

    def test_text_only_pdf(self, text_pdf):
        scanned = detect_scanned_pages(text_pdf)
        assert scanned == []

    def test_scanned_pdf(self, scanned_pdf):
        scanned = detect_scanned_pages(scanned_pdf)
        assert len(scanned) == 1
        assert 0 in scanned

    def test_mixed_pdf(self, mixed_pdf):
        scanned = detect_scanned_pages(mixed_pdf)
        assert 0 not in scanned  # Texto
        assert 1 in scanned     # Imagen


# ═══════════════════════════════════════════════════════════
# Tests: page_image_to_numpy
# ═══════════════════════════════════════════════════════════

cv2 = pytest.importorskip("cv2", reason="OpenCV no disponible")


class TestPageImageToNumpy:
    """Tests para conversión de página a numpy array."""

    def test_returns_numpy_array(self, text_pdf):
        img = page_image_to_numpy(text_pdf[0], dpi=150)
        assert isinstance(img, np.ndarray)
        assert img.ndim == 3  # BGR

    def test_dpi_affects_size(self, text_pdf):
        img_low = page_image_to_numpy(text_pdf[0], dpi=72)
        img_high = page_image_to_numpy(text_pdf[0], dpi=300)
        assert img_high.shape[0] > img_low.shape[0]
        assert img_high.shape[1] > img_low.shape[1]


# ═══════════════════════════════════════════════════════════
# Tests: insert_invisible_text
# ═══════════════════════════════════════════════════════════

class TestInsertInvisibleText:
    """Tests para inserción de texto invisible."""

    def test_inserts_words(self, scanned_pdf, sample_ocr_result):
        page = scanned_pdf[0]
        count = insert_invisible_text(page, sample_ocr_result, image_dpi=300)
        assert count == 3

    def test_empty_result_inserts_nothing(self, scanned_pdf):
        empty_result = OCRResult()
        page = scanned_pdf[0]
        count = insert_invisible_text(page, empty_result)
        assert count == 0

    def test_low_confidence_skipped(self, scanned_pdf):
        words = [
            OCRWord(text="Bueno", x=10, y=10, width=50, height=20, confidence=50.0),
            OCRWord(text="Malo", x=10, y=40, width=50, height=20, confidence=5.0),
        ]
        result = OCRResult(text="Bueno Malo", words=words)
        page = scanned_pdf[0]
        count = insert_invisible_text(page, result)
        assert count == 1  # Solo "Bueno" (confidence > 10)

    def test_text_becomes_selectable(self, scanned_pdf, sample_ocr_result):
        page = scanned_pdf[0]
        text_before = page.get_text("text").strip()
        insert_invisible_text(page, sample_ocr_result, image_dpi=300)
        text_after = page.get_text("text").strip()
        assert len(text_after) > len(text_before)
        assert "Hola" in text_after

    def test_blank_words_skipped(self, scanned_pdf):
        words = [
            OCRWord(text="  ", x=10, y=10, width=50, height=20, confidence=90.0),
            OCRWord(text="Real", x=70, y=10, width=50, height=20, confidence=90.0),
        ]
        result = OCRResult(text="Real", words=words)
        page = scanned_pdf[0]
        count = insert_invisible_text(page, result)
        assert count == 1


# ═══════════════════════════════════════════════════════════
# Tests: Dataclasses OCRPageResult / OCRDocumentResult
# ═══════════════════════════════════════════════════════════

class TestOCRPageResult:
    """Tests para la dataclass de resultado por página."""

    def test_defaults(self):
        pr = OCRPageResult(page_num=0)
        assert pr.page_num == 0
        assert pr.ocr_result is None
        assert pr.was_scanned is False
        assert pr.text_inserted is False


class TestOCRDocumentResult:
    """Tests para la dataclass de resultado del documento."""

    def test_defaults(self):
        dr = OCRDocumentResult()
        assert dr.total_pages == 0
        assert dr.scanned_pages == 0
        assert dr.total_words == 0
        assert dr.avg_confidence == 0.0

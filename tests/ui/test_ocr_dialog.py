"""Tests para ui.ocr_dialog — Diálogo OCR.

Tests de widgets sin dependencias de Tesseract.
"""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock

import fitz

pytest.importorskip("PyQt5", reason="PyQt5 no disponible")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from ui.ocr_dialog import OCRDialog, OCRWorker


# ═══════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def qapp():
    """QApplication compartida para la sesión de tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def scanned_pdf():
    """PDF simulando documento escaneado."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    return doc


@pytest.fixture
def dialog(qapp, scanned_pdf):
    """Instancia del diálogo OCR."""
    dlg = OCRDialog(doc=scanned_pdf, scanned_pages=[0])
    yield dlg
    dlg.close()


# ═══════════════════════════════════════════════════════════
# Tests: Creación del diálogo
# ═══════════════════════════════════════════════════════════

class TestOCRDialogCreation:
    """Tests de inicialización del diálogo."""

    def test_creates_dialog(self, dialog):
        assert dialog is not None
        assert dialog.windowTitle() == "OCR — Reconocimiento de Texto"

    def test_has_language_combo(self, dialog):
        assert dialog._combo_language is not None
        assert dialog._combo_language.count() >= 7

    def test_default_language_spanish(self, dialog):
        assert dialog._combo_language.currentData() == "spa"

    def test_has_preprocess_checkboxes(self, dialog):
        assert dialog._chk_deskew.isChecked()
        assert dialog._chk_denoise.isChecked()
        assert dialog._chk_binarize.isChecked()
        assert not dialog._chk_contrast.isChecked()
        assert dialog._chk_rescale.isChecked()

    def test_has_dpi_spinner(self, dialog):
        assert dialog._spin_dpi.value() == 300
        assert dialog._spin_dpi.minimum() == 150
        assert dialog._spin_dpi.maximum() == 600

    def test_has_progress_bar(self, dialog):
        assert dialog._progress.value() == 0

    def test_has_buttons(self, dialog):
        assert dialog._btn_start is not None
        assert dialog._btn_cancel is not None
        assert dialog._btn_save is not None
        assert not dialog._btn_save.isEnabled()

    def test_has_results_area(self, dialog):
        assert dialog._txt_results is not None
        assert dialog._txt_results.isReadOnly()


# ═══════════════════════════════════════════════════════════
# Tests: Configuración de preprocesado
# ═══════════════════════════════════════════════════════════

class TestPreprocessConfig:
    """Tests para la generación de configuración de preprocesado."""

    def test_build_fn_returns_callable(self, dialog):
        fn = dialog._build_preprocess_fn()
        assert callable(fn)

    def test_build_fn_none_when_all_disabled(self, dialog):
        dialog._chk_deskew.setChecked(False)
        dialog._chk_denoise.setChecked(False)
        dialog._chk_binarize.setChecked(False)
        dialog._chk_contrast.setChecked(False)
        dialog._chk_rescale.setChecked(False)
        fn = dialog._build_preprocess_fn()
        assert fn is None

    def test_dpi_value_used(self, dialog):
        dialog._spin_dpi.setValue(200)
        assert dialog._spin_dpi.value() == 200


# ═══════════════════════════════════════════════════════════
# Tests: Control habilitación
# ═══════════════════════════════════════════════════════════

class TestControlsEnabled:
    """Tests para habilitar/deshabilitar controles."""

    def test_disable_controls(self, dialog):
        dialog._set_controls_enabled(False)
        assert not dialog._combo_language.isEnabled()
        assert not dialog._chk_deskew.isEnabled()
        assert not dialog._spin_dpi.isEnabled()

    def test_enable_controls(self, dialog):
        dialog._set_controls_enabled(False)
        dialog._set_controls_enabled(True)
        assert dialog._combo_language.isEnabled()
        assert dialog._chk_deskew.isEnabled()


# ═══════════════════════════════════════════════════════════
# Tests: Progress callback
# ═══════════════════════════════════════════════════════════

class TestProgressCallback:
    """Tests para actualización de progreso."""

    def test_on_progress_updates_bar(self, dialog):
        dialog._on_progress(5, 10, "Procesando...")
        assert dialog._progress.value() == 50

    def test_on_progress_zero_total(self, dialog):
        dialog._on_progress(0, 0, "Esperando...")
        assert dialog._lbl_status.text() == "Esperando..."


# ═══════════════════════════════════════════════════════════
# Tests: Error handling
# ═══════════════════════════════════════════════════════════

class TestErrorHandling:
    """Tests para manejo de errores."""

    def test_on_error_shows_message(self, dialog):
        dialog._on_ocr_error("Tesseract no encontrado")
        assert "Error" in dialog._lbl_status.text()
        assert "Tesseract" in dialog._txt_results.toPlainText()

    def test_on_error_re_enables_controls(self, dialog):
        dialog._set_controls_enabled(False)
        dialog._btn_start.setEnabled(False)
        dialog._on_ocr_error("Error test")
        assert dialog._btn_start.isEnabled()
        assert dialog._combo_language.isEnabled()


# ═══════════════════════════════════════════════════════════
# Tests: OCR finished
# ═══════════════════════════════════════════════════════════

class TestOCRFinished:
    """Tests para cuando OCR finaliza."""

    def test_on_finished_enables_save(self, dialog):
        from core.ocr.pdf_ocr_layer import OCRDocumentResult, OCRPageResult
        from core.ocr.ocr_engine import OCRResult

        page_result = OCRPageResult(page_num=0)
        page_result.ocr_result = OCRResult(text="Texto de prueba", avg_confidence=92.0)
        
        doc_result = OCRDocumentResult(
            pages=[page_result],
            total_pages=1,
            scanned_pages=1,
            processed_pages=1,
            total_words=3,
            avg_confidence=92.0,
        )
        
        dialog._on_ocr_finished(doc_result)
        assert dialog._btn_save.isEnabled()
        assert dialog._progress.value() == 100
        assert "completado" in dialog._lbl_status.text().lower()
        assert "Texto de prueba" in dialog._txt_results.toPlainText()

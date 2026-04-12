"""Tests para ui.signature_dialog — Diálogo de firma digital."""

import os
import pytest
import fitz

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from ui.signature_dialog import SignatureDialog, SignWorker


@pytest.fixture(scope="module")
def app():
    """Crea la app Qt para tests."""
    _app = QApplication.instance() or QApplication([])
    yield _app


@pytest.fixture
def sample_pdf(tmp_path):
    """Crea un PDF de prueba."""
    path = str(tmp_path / "test.pdf")
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"Página {i + 1}")
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def dialog(app, sample_pdf):
    """Crea el diálogo de prueba."""
    dlg = SignatureDialog(sample_pdf, 3)
    yield dlg
    dlg.close()


# ━━━ Inicialización ━━━


class TestDialogInit:
    """Tests de inicialización del diálogo."""

    def test_creates(self, dialog):
        assert dialog is not None

    def test_title(self, dialog):
        assert dialog.windowTitle() == "Firma digital"

    def test_min_size(self, dialog):
        assert dialog.minimumWidth() >= 520
        assert dialog.minimumHeight() >= 440

    def test_file_stored(self, dialog):
        assert dialog._file_path.endswith("test.pdf")

    def test_page_count(self, dialog):
        assert dialog._page_count == 3


# ━━━ Sign Tab ━━━


class TestSignTab:
    """Tests de la pestaña de firma."""

    def test_pfx_input(self, dialog):
        assert dialog._txt_pfx_path is not None
        assert dialog._txt_pfx_path.text() == ""

    def test_password_masked(self, dialog):
        from PyQt5.QtWidgets import QLineEdit
        assert dialog._txt_password.echoMode() == QLineEdit.Password

    def test_reason_input(self, dialog):
        assert dialog._txt_reason is not None

    def test_location_input(self, dialog):
        assert dialog._txt_location is not None

    def test_visible_checkbox(self, dialog):
        assert not dialog._chk_visible.isChecked()

    def test_page_spinner(self, dialog):
        assert dialog._spn_page.minimum() == 1
        assert dialog._spn_page.maximum() == 3
        assert dialog._spn_page.value() == 1

    def test_sign_no_cert(self, dialog):
        dialog._on_sign()
        assert "certificado" in dialog._lbl_status.text().lower()

    def test_cert_info_no_cert(self, dialog):
        dialog._show_cert_info()
        assert "seleccione" in dialog._lbl_status.text().lower()


# ━━━ Verify Tab ━━━


class TestVerifyTab:
    """Tests de la pestaña de verificación."""

    def test_table_exists(self, dialog):
        assert dialog._sig_table is not None
        assert dialog._sig_table.columnCount() == 4

    def test_verify_unsigned(self, dialog):
        dialog._on_verify()
        assert "no tiene firmas" in dialog._lbl_verify_status.text().lower()

    def test_table_empty_after_verify_unsigned(self, dialog):
        dialog._on_verify()
        assert dialog._sig_table.rowCount() == 0


# ━━━ Worker ━━━


class TestSignWorker:
    """Tests para SignWorker."""

    def test_worker_success(self, app):
        from core.digital_signature import SignResult

        def dummy(**kwargs):
            return SignResult(success=True, message="OK")

        worker = SignWorker(dummy, {})
        results = []
        worker.finished.connect(results.append)
        worker.start()
        worker.wait(3000)
        app.processEvents()
        assert len(results) == 1
        assert results[0].success is True

    def test_worker_error(self, app):
        def failing(**kwargs):
            raise RuntimeError("fallo")

        worker = SignWorker(failing, {})
        errors = []
        worker.error.connect(errors.append)
        worker.start()
        worker.wait(3000)
        app.processEvents()
        assert len(errors) == 1
        assert "fallo" in errors[0]


# ━━━ Callbacks ━━━


class TestCallbacks:
    """Tests para callbacks."""

    def test_sign_done_success(self, dialog):
        from core.digital_signature import SignResult

        result = SignResult(
            success=True,
            output_path="/tmp/signed.pdf",
            message="Firma aplicada",
            signer_name="Test User",
        )
        emitted = []
        dialog.signature_applied.connect(emitted.append)
        dialog._on_sign_done(result)
        assert "✅" in dialog._lbl_status.text()
        assert len(emitted) == 1

    def test_sign_done_failure(self, dialog):
        from core.digital_signature import SignResult

        result = SignResult(success=False, message="Error de firma")
        dialog._on_sign_done(result)
        assert "❌" in dialog._lbl_status.text()

    def test_sign_error(self, dialog):
        dialog._on_sign_error("Error crítico")
        assert "Error crítico" in dialog._lbl_status.text()

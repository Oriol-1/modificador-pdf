"""Tests para ui.compression_dialog — Diálogo de compresión."""
import pytest
import os
import tempfile

import fitz

pytest.importorskip("PyQt5", reason="PyQt5 no disponible")

from PyQt5.QtWidgets import QApplication

from ui.compression_dialog import CompressionDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def pdf_file(tmp_path):
    path = str(tmp_path / "test.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(fitz.Point(72, 72), "Texto de prueba.", fontsize=12)
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def dialog(qapp, pdf_file):
    dlg = CompressionDialog(file_path=pdf_file)
    yield dlg
    dlg.close()


class TestCompressionDialogCreation:
    def test_creates_dialog(self, dialog):
        assert dialog.windowTitle() == "Comprimir PDF"

    def test_has_preset_buttons(self, dialog):
        assert dialog._radio_buttons["email"].isChecked()
        assert not dialog._radio_buttons["custom"].isChecked()

    def test_has_progress_bar(self, dialog):
        assert dialog._progress.value() == 0

    def test_has_compress_button(self, dialog):
        assert dialog._btn_compress.isEnabled()

    def test_save_disabled_initially(self, dialog):
        assert not dialog._btn_save_as.isEnabled()

    def test_custom_controls_disabled(self, dialog):
        assert not dialog._spin_target.isEnabled()
        assert not dialog._combo_quality.isEnabled()


class TestPresetSelection:
    def test_custom_enables_controls(self, dialog):
        dialog._radio_buttons["custom"].setChecked(True)
        dialog._on_preset_changed()
        assert dialog._spin_target.isEnabled()
        assert dialog._combo_quality.isEnabled()

    def test_email_disables_custom(self, dialog):
        dialog._radio_buttons["custom"].setChecked(True)
        dialog._on_preset_changed()
        dialog._radio_buttons["email"].setChecked(True)
        dialog._on_preset_changed()
        assert not dialog._spin_target.isEnabled()


class TestBuildConfig:
    def test_email_config(self, dialog):
        dialog._radio_buttons["email"].setChecked(True)
        config = dialog._build_config()
        assert config.target_size_kb == 5120

    def test_web_config(self, dialog):
        dialog._radio_buttons["web"].setChecked(True)
        config = dialog._build_config()
        assert config.target_size_kb == 1024

    def test_minimum_config(self, dialog):
        dialog._radio_buttons["minimum"].setChecked(True)
        config = dialog._build_config()
        assert config.target_size_kb == 400

    def test_custom_config(self, dialog):
        dialog._radio_buttons["custom"].setChecked(True)
        dialog._spin_target.setValue(2000)
        dialog._combo_quality.setCurrentIndex(0)
        config = dialog._build_config()
        assert config.target_size_kb == 2000
        assert config.image_quality == 85


class TestProgress:
    def test_on_progress(self, dialog):
        dialog._on_progress(3, 5, "Comprimiendo...")
        assert dialog._progress.value() == 60

    def test_on_error(self, dialog):
        dialog._on_error("Fallo")
        assert "Fallo" in dialog._lbl_status.text()
        assert dialog._btn_compress.isEnabled()

    def test_on_finished_success(self, dialog):
        from core.compression_engine import CompressionResult, CompressionTechnique
        result = CompressionResult(
            original_size=10000, compressed_size=5000,
            techniques_applied=[CompressionTechnique.GARBAGE_CLEANUP],
            success=True,
        )
        dialog._on_finished(result)
        assert dialog._btn_save_as.isEnabled()
        assert dialog._progress.value() == 100
        assert not dialog._lbl_result.isHidden()

"""Tests para ui.page_manager_dialog — Diálogo de gestión de páginas."""

import os
import pytest
import fitz

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from ui.page_manager_dialog import PageManagerDialog, PageOperationWorker


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
    for i in range(5):
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 72), f"Página {i + 1}")
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def dialog(app, sample_pdf):
    """Crea el diálogo de prueba."""
    dlg = PageManagerDialog(sample_pdf, 5)
    yield dlg
    dlg.close()


# ━━━ Inicialización ━━━


class TestDialogInit:
    """Tests de inicialización del diálogo."""

    def test_creates(self, dialog):
        assert dialog is not None

    def test_title(self, dialog):
        assert dialog.windowTitle() == "Gestión de páginas"

    def test_min_size(self, dialog):
        assert dialog.minimumWidth() >= 550
        assert dialog.minimumHeight() >= 450

    def test_file_info_shown(self, dialog):
        assert dialog._file_path.endswith("test.pdf")

    def test_page_count_stored(self, dialog):
        assert dialog._page_count == 5


# ━━━ Tab Merge ━━━


class TestMergeTab:
    """Tests de la pestaña de unión."""

    def test_merge_list_exists(self, dialog):
        assert dialog._merge_list is not None

    def test_current_file_preloaded(self, dialog):
        assert dialog._merge_list.count() == 1
        assert dialog._merge_list.item(0).text().endswith("test.pdf")

    def test_remove_item(self, dialog):
        dialog._merge_list.addItem("/tmp/extra.pdf")
        assert dialog._merge_list.count() == 2
        dialog._merge_list.setCurrentRow(1)
        dialog._on_merge_remove()
        assert dialog._merge_list.count() == 1

    def test_move_item_down(self, dialog):
        dialog._merge_list.addItem("/tmp/extra.pdf")
        dialog._merge_list.setCurrentRow(0)
        dialog._move_merge_item(1)
        assert dialog._merge_list.item(0).text() == "/tmp/extra.pdf"

    def test_move_item_up(self, dialog):
        dialog._merge_list.addItem("/tmp/extra.pdf")
        dialog._merge_list.setCurrentRow(1)
        dialog._move_merge_item(-1)
        assert dialog._merge_list.item(0).text() == "/tmp/extra.pdf"

    def test_merge_needs_two(self, dialog):
        # Only one file in list
        dialog._on_merge()
        assert "2" in dialog._lbl_status.text()


# ━━━ Tab Reorder ━━━


class TestReorderTab:
    """Tests de la pestaña de reordenamiento."""

    def test_reorder_list_populated(self, dialog):
        assert dialog._reorder_list.count() == 5

    def test_reorder_list_labels(self, dialog):
        for i in range(5):
            assert dialog._reorder_list.item(i).text() == f"Página {i + 1}"

    def test_reorder_no_change_detected(self, dialog):
        dialog._on_reorder()
        assert "no ha cambiado" in dialog._lbl_status.text().lower()


# ━━━ Parse page list ━━━


class TestParsePageList:
    """Tests para _parse_page_list."""

    def test_single(self, dialog):
        result = dialog._parse_page_list("3")
        assert result == [2]

    def test_range(self, dialog):
        result = dialog._parse_page_list("1-3")
        assert result == [0, 1, 2]

    def test_mixed(self, dialog):
        result = dialog._parse_page_list("1, 3, 5")
        assert result == [0, 2, 4]

    def test_range_and_single(self, dialog):
        result = dialog._parse_page_list("1-2, 5")
        assert result == [0, 1, 4]

    def test_empty(self, dialog):
        result = dialog._parse_page_list("")
        assert result is None

    def test_out_of_range(self, dialog):
        result = dialog._parse_page_list("99")
        assert result is None

    def test_zero(self, dialog):
        result = dialog._parse_page_list("0")
        assert result is None

    def test_deduplicate(self, dialog):
        result = dialog._parse_page_list("1, 1, 1")
        assert result == [0]

    def test_sorted(self, dialog):
        result = dialog._parse_page_list("5, 1, 3")
        assert result == [0, 2, 4]


# ━━━ Worker ━━━


class TestWorker:
    """Tests para PageOperationWorker."""

    def test_worker_success(self, app):
        def dummy(**kwargs):
            from core.page_manager import OperationResult
            return OperationResult(success=True, message="OK")

        worker = PageOperationWorker(dummy, {})
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

        worker = PageOperationWorker(failing, {})
        errors = []
        worker.error.connect(errors.append)
        worker.start()
        worker.wait(3000)
        app.processEvents()
        assert len(errors) == 1
        assert "fallo" in errors[0]


# ━━━ Operation callbacks ━━━


class TestCallbacks:
    """Tests para callbacks de operación."""

    def test_on_operation_done_success(self, dialog):
        from core.page_manager import OperationResult

        result = OperationResult(
            success=True,
            output_path="/tmp/out.pdf",
            message="Listo",
        )
        emitted = []
        dialog.operation_completed.connect(emitted.append)
        dialog._on_operation_done(result)

        assert "✅" in dialog._lbl_status.text()
        assert len(emitted) == 1

    def test_on_operation_done_failure(self, dialog):
        from core.page_manager import OperationResult

        result = OperationResult(success=False, message="Fallo")
        dialog._on_operation_done(result)

        assert "❌" in dialog._lbl_status.text()

    def test_on_operation_error(self, dialog):
        dialog._on_operation_error("Error crítico")
        assert "Error crítico" in dialog._lbl_status.text()

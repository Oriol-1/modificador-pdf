"""Tests para ui.translation_dialog."""

import pytest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QApplication

from ui.translation_dialog import TranslationDialog, TranslationWorker
from core.ai.ai_config import AIConfig, LLMProvider
from core.ai.translator import TranslationLanguage, TranslationResult


@pytest.fixture(scope="module")
def app():
    """Fixture de QApplication."""
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


class TestTranslationDialog:
    """Tests para TranslationDialog."""

    def _make_dialog(self, pages=None, provider=LLMProvider.NONE):
        """Helper para crear diálogo."""
        if pages is None:
            pages = ["Página uno", "Página dos", "Página tres"]
        config = AIConfig(llm_provider=provider)
        return TranslationDialog(pages, config)

    def test_creation(self, app):
        dialog = self._make_dialog()
        assert dialog.windowTitle() == "Traducir documento"

    def test_language_combos(self, app):
        dialog = self._make_dialog()
        assert dialog._cmb_source.count() == len(TranslationLanguage)
        assert dialog._cmb_target.count() == len(TranslationLanguage)

    def test_default_languages(self, app):
        dialog = self._make_dialog()
        assert dialog._cmb_source.currentIndex() == 0  # Spanish
        assert dialog._cmb_target.currentIndex() == 1  # English

    def test_all_pages_default(self, app):
        dialog = self._make_dialog()
        assert dialog._radio_all.isChecked()

    def test_get_selected_pages_all(self, app):
        pages = ["A", "B", "C"]
        dialog = self._make_dialog(pages)
        selected = dialog._get_selected_pages()
        assert selected == ["A", "B", "C"]

    def test_get_selected_pages_range(self, app):
        pages = ["A", "B", "C", "D"]
        dialog = self._make_dialog(pages)
        dialog._radio_range.setChecked(True)
        dialog._spn_from.setValue(2)
        dialog._spn_to.setValue(3)
        selected = dialog._get_selected_pages()
        assert selected == ["B", "C"]

    def test_range_spinbox_disabled_by_default(self, app):
        dialog = self._make_dialog()
        assert not dialog._spn_from.isEnabled()
        assert not dialog._spn_to.isEnabled()

    def test_range_spinbox_enabled_on_range(self, app):
        dialog = self._make_dialog()
        dialog._radio_range.setChecked(True)
        assert dialog._spn_from.isEnabled()
        assert dialog._spn_to.isEnabled()

    def test_translate_no_provider(self, app):
        dialog = self._make_dialog(provider=LLMProvider.NONE)
        dialog._on_translate()
        assert not dialog._lbl_status.isHidden()

    def test_translate_same_language(self, app):
        dialog = self._make_dialog(provider=LLMProvider.OPENAI)
        dialog._cmb_source.setCurrentIndex(0)
        dialog._cmb_target.setCurrentIndex(0)
        dialog._on_translate()
        assert "diferentes" in dialog._lbl_status.text().lower()

    def test_on_finished(self, app):
        dialog = self._make_dialog()
        results = [
            TranslationResult(
                original="Hola",
                translated="Hello",
                source_lang=TranslationLanguage.SPANISH,
                target_lang=TranslationLanguage.ENGLISH,
                page_num=0,
            ),
        ]
        dialog._on_finished(results)
        assert dialog._progress.value() == 100
        assert "completada" in dialog._lbl_status.text().lower()
        assert len(dialog.get_results()) == 1

    def test_on_error(self, app):
        dialog = self._make_dialog()
        dialog._on_error("Test error")
        assert "Error" in dialog._lbl_status.text()
        assert dialog._btn_translate.isEnabled()

    def test_on_progress(self, app):
        dialog = self._make_dialog()
        dialog._on_progress(1, 3)
        assert dialog._progress.value() == 33

    def test_get_results_empty(self, app):
        dialog = self._make_dialog()
        assert dialog.get_results() == []


class TestTranslationWorker:
    """Tests para TranslationWorker."""

    def test_creation(self, app):
        worker = TranslationWorker(
            ["Text"],
            TranslationLanguage.SPANISH,
            TranslationLanguage.ENGLISH,
            AIConfig(),
        )
        assert worker._source_lang == TranslationLanguage.SPANISH

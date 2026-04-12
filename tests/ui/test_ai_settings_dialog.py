"""Tests para ui.ai_settings_dialog."""

import pytest
from unittest.mock import patch
from PyQt5.QtWidgets import QApplication

from ui.ai_settings_dialog import AISettingsDialog
from core.ai.ai_config import AIConfig, LLMProvider, EmbeddingProvider


@pytest.fixture(scope="module")
def app():
    """Fixture de QApplication."""
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


class TestAISettingsDialog:
    """Tests para AISettingsDialog."""

    def test_creation(self, app):
        config = AIConfig()
        dialog = AISettingsDialog(config)
        assert dialog.windowTitle() == "Ajustes de IA"

    def test_loads_defaults(self, app):
        config = AIConfig()
        dialog = AISettingsDialog(config)
        assert dialog._cmb_provider.currentIndex() == 0  # None

    def test_loads_openai_config(self, app):
        config = AIConfig(
            llm_provider=LLMProvider.OPENAI,
            openai_api_key="sk-test",
            openai_model="gpt-4o",
        )
        dialog = AISettingsDialog(config)
        assert dialog._cmb_provider.currentIndex() == 1
        assert dialog._txt_api_key.text() == "sk-test"

    def test_loads_ollama_config(self, app):
        config = AIConfig(
            llm_provider=LLMProvider.OLLAMA,
            ollama_model="mistral",
        )
        dialog = AISettingsDialog(config)
        assert dialog._cmb_provider.currentIndex() == 2

    def test_build_config_none(self, app):
        config = AIConfig()
        dialog = AISettingsDialog(config)
        dialog._cmb_provider.setCurrentIndex(0)
        result = dialog._build_config()
        assert result.llm_provider == LLMProvider.NONE

    def test_build_config_openai(self, app):
        config = AIConfig()
        dialog = AISettingsDialog(config)
        dialog._cmb_provider.setCurrentIndex(1)
        dialog._txt_api_key.setText("sk-new-key")
        dialog._cmb_openai_model.setCurrentText("gpt-4o")
        result = dialog._build_config()
        assert result.llm_provider == LLMProvider.OPENAI
        assert result.openai_api_key == "sk-new-key"
        assert result.openai_model == "gpt-4o"

    def test_build_config_ollama(self, app):
        config = AIConfig()
        dialog = AISettingsDialog(config)
        dialog._cmb_provider.setCurrentIndex(2)
        dialog._txt_ollama_url.setText("http://myserver:11434")
        dialog._cmb_ollama_model.setCurrentText("codellama")
        result = dialog._build_config()
        assert result.llm_provider == LLMProvider.OLLAMA
        assert result.ollama_url == "http://myserver:11434"
        assert result.ollama_model == "codellama"

    def test_build_config_search_params(self, app):
        config = AIConfig()
        dialog = AISettingsDialog(config)
        dialog._spn_chunk_size.setValue(300)
        dialog._spn_overlap.setValue(30)
        dialog._spn_top_k.setValue(8)
        result = dialog._build_config()
        assert result.chunk_size == 300
        assert result.chunk_overlap == 30
        assert result.top_k == 8

    def test_provider_changed_enables_fields(self, app):
        config = AIConfig()
        dialog = AISettingsDialog(config)
        dialog._cmb_provider.setCurrentIndex(1)  # OpenAI
        assert dialog._txt_api_key.isEnabled()
        assert not dialog._txt_ollama_url.isEnabled()

        dialog._cmb_provider.setCurrentIndex(2)  # Ollama
        assert not dialog._txt_api_key.isEnabled()
        assert dialog._txt_ollama_url.isEnabled()

    def test_get_config_after_save(self, app):
        config = AIConfig()
        dialog = AISettingsDialog(config)
        dialog._cmb_provider.setCurrentIndex(1)
        dialog._txt_api_key.setText("my-key")
        dialog._on_save()
        result = dialog.get_config()
        assert result.llm_provider == LLMProvider.OPENAI
        assert result.openai_api_key == "my-key"

    def test_temperature_range(self, app):
        config = AIConfig()
        dialog = AISettingsDialog(config)
        dialog._spn_temperature.setValue(1.5)
        result = dialog._build_config()
        assert result.temperature == 1.5

    def test_embedding_provider_selection(self, app):
        config = AIConfig()
        dialog = AISettingsDialog(config)
        dialog._cmb_embedding.setCurrentIndex(0)
        result = dialog._build_config()
        assert result.embedding_provider == EmbeddingProvider.TFIDF

        dialog._cmb_embedding.setCurrentIndex(1)
        result = dialog._build_config()
        assert result.embedding_provider == EmbeddingProvider.OPENAI

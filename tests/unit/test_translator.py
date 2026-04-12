"""Tests para core.ai.translator."""

import pytest
from unittest.mock import patch, MagicMock

from core.ai.ai_config import AIConfig, LLMProvider
from core.ai.translator import (
    TranslationLanguage, TranslationRequest, TranslationResult,
    translate_text, translate_pages,
)


class TestTranslationLanguage:
    """Tests para TranslationLanguage."""

    def test_spanish(self):
        assert TranslationLanguage.SPANISH.value == "Español"

    def test_english(self):
        assert TranslationLanguage.ENGLISH.value == "English"

    def test_all_languages(self):
        assert len(TranslationLanguage) == 15


class TestTranslationRequest:
    """Tests para TranslationRequest."""

    def test_creation(self):
        req = TranslationRequest(
            text="Hola mundo",
            source_lang=TranslationLanguage.SPANISH,
            target_lang=TranslationLanguage.ENGLISH,
        )
        assert req.text == "Hola mundo"
        assert req.source_lang == TranslationLanguage.SPANISH
        assert req.page_num == 0


class TestTranslationResult:
    """Tests para TranslationResult."""

    def test_success(self):
        result = TranslationResult(
            original="Hola",
            translated="Hello",
            source_lang=TranslationLanguage.SPANISH,
            target_lang=TranslationLanguage.ENGLISH,
        )
        assert result.success
        assert result.error == ""

    def test_failure(self):
        result = TranslationResult(
            original="Hola",
            translated="",
            source_lang=TranslationLanguage.SPANISH,
            target_lang=TranslationLanguage.ENGLISH,
            success=False,
            error="API error",
        )
        assert not result.success
        assert result.error == "API error"


class TestTranslateText:
    """Tests para translate_text."""

    def test_no_provider(self):
        config = AIConfig(llm_provider=LLMProvider.NONE)
        req = TranslationRequest(
            text="Hola",
            source_lang=TranslationLanguage.SPANISH,
            target_lang=TranslationLanguage.ENGLISH,
        )
        result = translate_text(req, config)
        assert not result.success
        assert "proveedor" in result.error.lower()

    @patch('core.ai.translator.call_openai')
    def test_openai_success(self, mock_call):
        mock_call.return_value = "Hello"
        config = AIConfig(
            llm_provider=LLMProvider.OPENAI,
            openai_api_key="test-key",
        )
        req = TranslationRequest(
            text="Hola",
            source_lang=TranslationLanguage.SPANISH,
            target_lang=TranslationLanguage.ENGLISH,
        )
        result = translate_text(req, config)
        assert result.success
        assert result.translated == "Hello"
        mock_call.assert_called_once()

    @patch('core.ai.translator.call_ollama')
    def test_ollama_success(self, mock_call):
        mock_call.return_value = "Hello"
        config = AIConfig(llm_provider=LLMProvider.OLLAMA)
        req = TranslationRequest(
            text="Hola",
            source_lang=TranslationLanguage.SPANISH,
            target_lang=TranslationLanguage.ENGLISH,
        )
        result = translate_text(req, config)
        assert result.success
        assert result.translated == "Hello"

    @patch('core.ai.translator.call_openai')
    def test_api_error(self, mock_call):
        mock_call.side_effect = RuntimeError("API failed")
        config = AIConfig(
            llm_provider=LLMProvider.OPENAI,
            openai_api_key="test-key",
        )
        req = TranslationRequest(
            text="Hola",
            source_lang=TranslationLanguage.SPANISH,
            target_lang=TranslationLanguage.ENGLISH,
        )
        result = translate_text(req, config)
        assert not result.success
        assert "API failed" in result.error

    @patch('core.ai.translator.call_openai')
    def test_preserves_page_num(self, mock_call):
        mock_call.return_value = "Translated"
        config = AIConfig(
            llm_provider=LLMProvider.OPENAI,
            openai_api_key="k",
        )
        req = TranslationRequest(
            text="Text",
            source_lang=TranslationLanguage.SPANISH,
            target_lang=TranslationLanguage.ENGLISH,
            page_num=5,
        )
        result = translate_text(req, config)
        assert result.page_num == 5


class TestTranslatePages:
    """Tests para translate_pages."""

    @patch('core.ai.translator.call_openai')
    def test_translate_multiple_pages(self, mock_call):
        mock_call.return_value = "Translated"
        config = AIConfig(
            llm_provider=LLMProvider.OPENAI,
            openai_api_key="k",
        )
        pages = ["Página uno.", "Página dos.", "Página tres."]
        results = translate_pages(
            pages,
            TranslationLanguage.SPANISH,
            TranslationLanguage.ENGLISH,
            config,
        )
        assert len(results) == 3
        assert all(r.success for r in results)

    @patch('core.ai.translator.call_openai')
    def test_empty_pages_skipped(self, mock_call):
        mock_call.return_value = "Translated"
        config = AIConfig(
            llm_provider=LLMProvider.OPENAI,
            openai_api_key="k",
        )
        pages = ["Content", "", "More content"]
        results = translate_pages(
            pages,
            TranslationLanguage.SPANISH,
            TranslationLanguage.ENGLISH,
            config,
        )
        assert len(results) == 3
        # Empty page should still be success but empty
        assert results[1].translated == ""
        assert results[1].success
        # Only 2 calls (empty page skipped)
        assert mock_call.call_count == 2

    def test_progress_callback(self):
        config = AIConfig(llm_provider=LLMProvider.NONE)
        progress_calls = []
        translate_pages(
            ["Text"],
            TranslationLanguage.SPANISH,
            TranslationLanguage.ENGLISH,
            config,
            progress_callback=lambda cur, total: progress_calls.append((cur, total)),
        )
        assert len(progress_calls) >= 1

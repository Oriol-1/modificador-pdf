"""Tests para core.ai.ai_config."""

import json
import os
import tempfile
import pytest

from core.ai.ai_config import AIConfig, LLMProvider, EmbeddingProvider


class TestLLMProvider:
    """Tests para el enum LLMProvider."""

    def test_values(self):
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.OLLAMA.value == "ollama"
        assert LLMProvider.NONE.value == "none"

    def test_from_string(self):
        assert LLMProvider("openai") == LLMProvider.OPENAI
        assert LLMProvider("ollama") == LLMProvider.OLLAMA


class TestEmbeddingProvider:
    """Tests para el enum EmbeddingProvider."""

    def test_values(self):
        assert EmbeddingProvider.TFIDF.value == "tfidf"
        assert EmbeddingProvider.OPENAI.value == "openai"
        assert EmbeddingProvider.SENTENCE_TRANSFORMERS.value == "sentence_transformers"


class TestAIConfig:
    """Tests para AIConfig."""

    def test_defaults(self):
        config = AIConfig()
        assert config.llm_provider == LLMProvider.NONE
        assert config.embedding_provider == EmbeddingProvider.TFIDF
        assert config.openai_api_key == ""
        assert config.openai_model == "gpt-4o-mini"
        assert config.ollama_url == "http://localhost:11434"
        assert config.ollama_model == "llama3.2"
        assert config.chunk_size == 500
        assert config.chunk_overlap == 50
        assert config.top_k == 5
        assert config.temperature == 0.3

    def test_to_dict(self):
        config = AIConfig(llm_provider=LLMProvider.OPENAI, openai_api_key="test-key")
        d = config.to_dict()
        assert d["llm_provider"] == "openai"
        assert d["openai_api_key"] == "test-key"
        assert d["chunk_size"] == 500

    def test_from_dict(self):
        data = {
            "llm_provider": "ollama",
            "embedding_provider": "tfidf",
            "ollama_model": "mistral",
            "top_k": 10,
        }
        config = AIConfig.from_dict(data)
        assert config.llm_provider == LLMProvider.OLLAMA
        assert config.ollama_model == "mistral"
        assert config.top_k == 10

    def test_from_dict_defaults(self):
        config = AIConfig.from_dict({})
        assert config.llm_provider == LLMProvider.NONE
        assert config.chunk_size == 500

    def test_roundtrip(self):
        original = AIConfig(
            llm_provider=LLMProvider.OPENAI,
            openai_api_key="sk-test",
            openai_model="gpt-4o",
            temperature=0.7,
            top_k=8,
        )
        restored = AIConfig.from_dict(original.to_dict())
        assert restored.llm_provider == original.llm_provider
        assert restored.openai_api_key == original.openai_api_key
        assert restored.openai_model == original.openai_model
        assert restored.temperature == original.temperature
        assert restored.top_k == original.top_k

    def test_save_and_load(self, tmp_path):
        config = AIConfig(
            llm_provider=LLMProvider.OLLAMA,
            ollama_model="codellama",
            chunk_size=300,
        )
        path = str(tmp_path / "ai_config.json")
        config.save(path)

        loaded = AIConfig.load(path)
        assert loaded.llm_provider == LLMProvider.OLLAMA
        assert loaded.ollama_model == "codellama"
        assert loaded.chunk_size == 300

    def test_load_missing_file(self, tmp_path):
        path = str(tmp_path / "nonexistent.json")
        config = AIConfig.load(path)
        assert config.llm_provider == LLMProvider.NONE

    def test_load_invalid_json(self, tmp_path):
        path = str(tmp_path / "bad.json")
        with open(path, 'w') as f:
            f.write("not json")
        config = AIConfig.load(path)
        assert config.llm_provider == LLMProvider.NONE

    def test_has_llm_none(self):
        config = AIConfig(llm_provider=LLMProvider.NONE)
        assert not config.has_llm

    def test_has_llm_openai_no_key(self):
        config = AIConfig(llm_provider=LLMProvider.OPENAI, openai_api_key="")
        assert not config.has_llm

    def test_has_llm_openai_with_key(self):
        config = AIConfig(llm_provider=LLMProvider.OPENAI, openai_api_key="sk-test")
        assert config.has_llm

    def test_has_llm_ollama(self):
        config = AIConfig(llm_provider=LLMProvider.OLLAMA)
        assert config.has_llm

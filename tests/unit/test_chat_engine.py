"""Tests para core.ai.chat_engine."""

import pytest
from unittest.mock import MagicMock, patch

from core.ai.ai_config import AIConfig, LLMProvider
from core.ai.document_indexer import TextChunk, DocumentIndex
from core.ai.embedding_store import SearchResult
from core.ai.chat_engine import (
    MessageRole, Citation, ChatMessage,
    build_rag_prompt, extract_citations, ChatEngine,
)


class TestMessageRole:
    """Tests para MessageRole."""

    def test_values(self):
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"


class TestCitation:
    """Tests para Citation."""

    def test_creation(self):
        c = Citation(page_num=2, text="Some text", chunk_id=5)
        assert c.page_num == 2
        assert c.text == "Some text"
        assert c.chunk_id == 5


class TestChatMessage:
    """Tests para ChatMessage."""

    def test_creation(self):
        msg = ChatMessage(role=MessageRole.USER, content="Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.citations == []

    def test_to_dict(self):
        msg = ChatMessage(role=MessageRole.ASSISTANT, content="Response")
        d = msg.to_dict()
        assert d["role"] == "assistant"
        assert d["content"] == "Response"

    def test_with_citations(self):
        citations = [Citation(page_num=0, text="Cited")]
        msg = ChatMessage(
            role=MessageRole.ASSISTANT,
            content="Check [Página 1]",
            citations=citations,
        )
        assert len(msg.citations) == 1


class TestBuildRagPrompt:
    """Tests para build_rag_prompt."""

    def test_empty_context(self):
        messages = build_rag_prompt("What is this?", [])
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "Sin contexto" in messages[1]["content"]

    def test_with_context(self):
        chunk = TextChunk(chunk_id=0, text="Important info", page_num=0)
        results = [SearchResult(chunk=chunk, score=0.9)]
        messages = build_rag_prompt("Tell me about it", results)
        assert "Important info" in messages[1]["content"]
        assert "[Página 1]" in messages[1]["content"]

    def test_custom_system_prompt(self):
        messages = build_rag_prompt(
            "Question", [], system_prompt="Custom system"
        )
        assert messages[0]["content"] == "Custom system"

    def test_multiple_contexts(self):
        chunks = [
            SearchResult(
                chunk=TextChunk(chunk_id=i, text=f"Text {i}", page_num=i),
                score=0.8 - i * 0.1,
            )
            for i in range(3)
        ]
        messages = build_rag_prompt("Query", chunks)
        content = messages[1]["content"]
        assert "[Página 1]" in content
        assert "[Página 2]" in content
        assert "[Página 3]" in content


class TestExtractCitations:
    """Tests para extract_citations."""

    def test_no_citations(self):
        result = extract_citations("No citations here", [])
        assert result == []

    def test_single_citation(self):
        chunk = TextChunk(chunk_id=0, text="Source text", page_num=2)
        context = [SearchResult(chunk=chunk, score=0.9)]
        result = extract_citations(
            "According to [Página 3], the answer is...", context
        )
        assert len(result) == 1
        assert result[0].page_num == 2

    def test_multiple_citations(self):
        chunks = [
            SearchResult(
                chunk=TextChunk(chunk_id=i, text=f"Text {i}", page_num=i),
                score=0.9,
            )
            for i in range(3)
        ]
        text = "[Página 1] says... and [Página 2] confirms..."
        result = extract_citations(text, chunks)
        assert len(result) == 2

    def test_duplicate_citations_collapsed(self):
        chunk = TextChunk(chunk_id=0, text="Text", page_num=0)
        context = [SearchResult(chunk=chunk, score=0.9)]
        text = "[Página 1] first mention. [Página 1] second mention."
        result = extract_citations(text, context)
        assert len(result) == 1

    def test_citation_not_in_context(self):
        chunk = TextChunk(chunk_id=0, text="Text", page_num=0)
        context = [SearchResult(chunk=chunk, score=0.9)]
        result = extract_citations("[Página 5]", context)
        # Page 5 (index 4) not in context chunks (only page 0)
        assert len(result) == 0


class TestChatEngine:
    """Tests para ChatEngine."""

    def _make_engine(self, provider=LLMProvider.NONE):
        """Helper para crear motor de chat."""
        config = AIConfig(llm_provider=provider)
        return ChatEngine(config)

    def _make_doc_index(self, texts=None):
        """Helper para crear índice de documento."""
        if texts is None:
            texts = ["First page content.", "Second page content."]
        chunks = []
        for i, text in enumerate(texts):
            chunks.append(TextChunk(chunk_id=i, text=text, page_num=i))
        return DocumentIndex(
            file_path="test.pdf",
            total_pages=len(texts),
            chunks=chunks,
            page_texts=texts,
        )

    def test_initial_state(self):
        engine = self._make_engine()
        assert not engine.has_document
        assert engine.history == []

    def test_index_document(self):
        engine = self._make_engine()
        doc_idx = self._make_doc_index()
        engine.index_document(doc_idx)
        assert engine.has_document
        assert engine.history == []

    def test_ask_no_document(self):
        engine = self._make_engine()
        with pytest.raises(RuntimeError, match="No hay documento"):
            engine.ask("Question")

    def test_ask_no_llm(self):
        engine = self._make_engine(LLMProvider.NONE)
        doc_idx = self._make_doc_index(["Python programming info."])
        engine.index_document(doc_idx)
        response = engine.ask("Python")
        assert response.role == MessageRole.ASSISTANT
        assert "Fragmentos relevantes" in response.content
        assert len(engine.history) == 2  # user + assistant

    def test_ask_adds_to_history(self):
        engine = self._make_engine()
        engine.index_document(self._make_doc_index())
        engine.ask("Test question")
        assert len(engine.history) == 2
        assert engine.history[0].role == MessageRole.USER
        assert engine.history[1].role == MessageRole.ASSISTANT

    def test_clear_history(self):
        engine = self._make_engine()
        engine.index_document(self._make_doc_index())
        engine.ask("Test")
        engine.clear_history()
        assert engine.history == []

    def test_index_document_clears_history(self):
        engine = self._make_engine()
        engine.index_document(self._make_doc_index())
        engine.ask("First question")
        engine.index_document(self._make_doc_index())
        assert engine.history == []

    def test_format_context_only_empty(self):
        engine = self._make_engine()
        result = engine._format_context_only([])
        assert "No se encontraron" in result

    def test_format_context_only_with_results(self):
        engine = self._make_engine()
        chunk = TextChunk(chunk_id=0, text="Found text", page_num=2)
        context = [SearchResult(chunk=chunk, score=0.85)]
        result = engine._format_context_only(context)
        assert "[Página 3]" in result
        assert "85%" in result

    @patch('core.ai.chat_engine.call_openai')
    def test_ask_with_openai(self, mock_call):
        mock_call.return_value = "The answer from [Página 1]."
        engine = self._make_engine(LLMProvider.OPENAI)
        engine.config.openai_api_key = "test-key"
        engine.index_document(self._make_doc_index(["Relevant content."]))
        response = engine.ask("What is the content?")
        assert response.content == "The answer from [Página 1]."
        mock_call.assert_called_once()

    @patch('core.ai.chat_engine.call_ollama')
    def test_ask_with_ollama(self, mock_call):
        mock_call.return_value = "Ollama response."
        engine = self._make_engine(LLMProvider.OLLAMA)
        engine.index_document(self._make_doc_index(["Test content."]))
        response = engine.ask("Question")
        assert response.content == "Ollama response."
        mock_call.assert_called_once()

    @patch('core.ai.chat_engine.call_openai')
    def test_ask_llm_error(self, mock_call):
        mock_call.side_effect = RuntimeError("API error")
        engine = self._make_engine(LLMProvider.OPENAI)
        engine.config.openai_api_key = "test-key"
        engine.index_document(self._make_doc_index(["Content."]))
        response = engine.ask("Question")
        assert "Error" in response.content

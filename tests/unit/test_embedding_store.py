"""Tests para core.ai.embedding_store."""

import pytest

from core.ai.document_indexer import TextChunk
from core.ai.embedding_store import (
    SearchResult, TFIDFEmbedder, EmbeddingStore,
)


class TestSearchResult:
    """Tests para SearchResult."""

    def test_creation(self):
        chunk = TextChunk(chunk_id=0, text="Test", page_num=0)
        result = SearchResult(chunk=chunk, score=0.95)
        assert result.chunk.text == "Test"
        assert result.score == 0.95
        assert result.rank == 0


class TestTFIDFEmbedder:
    """Tests para TFIDFEmbedder."""

    def test_fit_empty(self):
        embedder = TFIDFEmbedder()
        embedder.fit([])
        assert embedder._fitted

    def test_fit_single_doc(self):
        embedder = TFIDFEmbedder()
        embedder.fit(["Hello world"])
        assert embedder._fitted
        assert len(embedder._vocabulary) > 0

    def test_fit_multiple_docs(self):
        embedder = TFIDFEmbedder()
        embedder.fit(["The cat sat", "The dog ran", "A bird flew"])
        assert embedder._fitted
        assert "cat" in embedder._vocabulary
        assert "dog" in embedder._vocabulary

    def test_tokenize(self):
        embedder = TFIDFEmbedder()
        tokens = embedder._tokenize("Hello World! This is a TEST.")
        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens
        # Single-char tokens filtered
        assert "a" not in tokens

    def test_search_not_fitted(self):
        embedder = TFIDFEmbedder()
        assert embedder.search("query") == []

    def test_search_basic(self):
        embedder = TFIDFEmbedder()
        texts = [
            "Python programming language",
            "Java programming language",
            "French cooking recipes",
            "Italian cuisine pasta",
        ]
        embedder.fit(texts)
        results = embedder.search("Python programming", top_k=2)
        assert len(results) > 0
        # First result should be the Python doc (index 0)
        assert results[0][0] == 0

    def test_search_top_k(self):
        embedder = TFIDFEmbedder()
        texts = [f"Document number {i}" for i in range(10)]
        embedder.fit(texts)
        results = embedder.search("document", top_k=3)
        assert len(results) <= 3

    def test_search_no_match(self):
        embedder = TFIDFEmbedder()
        embedder.fit(["Hello world"])
        results = embedder.search("zzzzzzz")
        assert results == []

    def test_embed_query_not_fitted(self):
        embedder = TFIDFEmbedder()
        vec = embedder.embed_query("test")
        assert len(vec) == 1

    def test_embed_query(self):
        embedder = TFIDFEmbedder()
        embedder.fit(["Hello world", "Foo bar"])
        vec = embedder.embed_query("Hello")
        assert len(vec) == len(embedder._vocabulary)


class TestEmbeddingStore:
    """Tests para EmbeddingStore."""

    def _make_chunks(self, texts, page_num=0):
        """Helper para crear chunks."""
        return [
            TextChunk(chunk_id=i, text=t, page_num=page_num)
            for i, t in enumerate(texts)
        ]

    def test_initial_state(self):
        store = EmbeddingStore()
        assert not store.is_indexed
        assert store.chunk_count == 0

    def test_index_chunks(self):
        store = EmbeddingStore()
        chunks = self._make_chunks(["Hello", "World"])
        store.index_chunks(chunks)
        assert store.is_indexed
        assert store.chunk_count == 2

    def test_search_not_indexed(self):
        store = EmbeddingStore()
        assert store.search("query") == []

    def test_search_basic(self):
        store = EmbeddingStore()
        chunks = self._make_chunks([
            "Python es un lenguaje de programación",
            "Java es otro lenguaje de programación",
            "La cocina francesa es exquisita",
            "La pasta italiana es deliciosa",
        ])
        store.index_chunks(chunks)
        results = store.search("programación Python")
        assert len(results) > 0
        assert isinstance(results[0], SearchResult)
        assert results[0].chunk.chunk_id == 0

    def test_search_returns_ranked(self):
        store = EmbeddingStore()
        chunks = self._make_chunks([
            "Machine learning algorithms",
            "Deep learning neural networks",
            "Cooking delicious food",
        ])
        store.index_chunks(chunks)
        results = store.search("learning algorithms", top_k=3)
        for i, result in enumerate(results):
            assert result.rank == i

    def test_search_respects_top_k(self):
        store = EmbeddingStore()
        chunks = self._make_chunks([f"Document {i}" for i in range(10)])
        store.index_chunks(chunks)
        results = store.search("document", top_k=3)
        assert len(results) <= 3

    def test_search_empty_chunks(self):
        store = EmbeddingStore()
        store.index_chunks([])
        assert store.search("query") == []

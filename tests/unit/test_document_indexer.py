"""Tests para core.ai.document_indexer."""

import pytest
from unittest.mock import MagicMock

from core.ai.document_indexer import (
    TextChunk, DocumentIndex,
    extract_page_texts, split_into_chunks, create_document_index,
)


class TestTextChunk:
    """Tests para TextChunk."""

    def test_creation(self):
        chunk = TextChunk(chunk_id=0, text="Hello", page_num=1)
        assert chunk.chunk_id == 0
        assert chunk.text == "Hello"
        assert chunk.page_num == 1
        assert chunk.start_char == 0
        assert chunk.end_char == 0

    def test_to_dict(self):
        chunk = TextChunk(chunk_id=5, text="Test", page_num=2, start_char=10, end_char=14)
        d = chunk.to_dict()
        assert d["chunk_id"] == 5
        assert d["text"] == "Test"
        assert d["page_num"] == 2

    def test_from_dict(self):
        data = {"chunk_id": 3, "text": "Data", "page_num": 0, "start_char": 0, "end_char": 4}
        chunk = TextChunk.from_dict(data)
        assert chunk.chunk_id == 3
        assert chunk.text == "Data"

    def test_roundtrip(self):
        original = TextChunk(chunk_id=7, text="Round trip", page_num=5, start_char=100, end_char=110)
        restored = TextChunk.from_dict(original.to_dict())
        assert restored.chunk_id == original.chunk_id
        assert restored.text == original.text
        assert restored.page_num == original.page_num


class TestDocumentIndex:
    """Tests para DocumentIndex."""

    def test_creation(self):
        idx = DocumentIndex(file_path="test.pdf", total_pages=3)
        assert idx.file_path == "test.pdf"
        assert idx.total_pages == 3
        assert idx.chunks == []
        assert idx.page_texts == []

    def test_with_chunks(self):
        chunks = [TextChunk(chunk_id=i, text=f"Chunk {i}", page_num=0) for i in range(3)]
        idx = DocumentIndex(file_path="doc.pdf", total_pages=1, chunks=chunks)
        assert len(idx.chunks) == 3


class TestExtractPageTexts:
    """Tests para extract_page_texts."""

    def test_empty_document(self):
        doc = []
        assert extract_page_texts(doc) == []

    def test_single_page(self):
        page = MagicMock()
        page.get_text.return_value = "Hello World\n"
        texts = extract_page_texts([page])
        assert texts == ["Hello World"]

    def test_multiple_pages(self):
        pages = []
        for i in range(3):
            page = MagicMock()
            page.get_text.return_value = f"Page {i}\n"
            pages.append(page)
        texts = extract_page_texts(pages)
        assert len(texts) == 3
        assert texts[1] == "Page 1"


class TestSplitIntoChunks:
    """Tests para split_into_chunks."""

    def test_empty_text(self):
        assert split_into_chunks("", 0) == []

    def test_whitespace_text(self):
        assert split_into_chunks("   \n  ", 0) == []

    def test_single_short_paragraph(self):
        chunks = split_into_chunks("Hello world", 0)
        assert len(chunks) == 1
        assert chunks[0].text == "Hello world"
        assert chunks[0].page_num == 0

    def test_chunk_ids_start_from(self):
        chunks = split_into_chunks("Test text", 0, start_id=10)
        assert chunks[0].chunk_id == 10

    def test_multiple_paragraphs_fit_in_one_chunk(self):
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = split_into_chunks(text, 0, chunk_size=200)
        assert len(chunks) == 1

    def test_split_large_text(self):
        paragraphs = [f"Paragraph {i} with some text content." for i in range(20)]
        text = "\n\n".join(paragraphs)
        chunks = split_into_chunks(text, 0, chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.page_num == 0

    def test_chunk_ids_sequential(self):
        paragraphs = [f"Long paragraph number {i} with enough text." for i in range(10)]
        text = "\n\n".join(paragraphs)
        chunks = split_into_chunks(text, 0, chunk_size=80, chunk_overlap=10)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_id == i

    def test_page_num_preserved(self):
        chunks = split_into_chunks("Some text", page_num=5)
        assert chunks[0].page_num == 5


class TestCreateDocumentIndex:
    """Tests para create_document_index."""

    def test_empty_document(self):
        doc = []
        idx = create_document_index(doc)
        assert idx.total_pages == 0
        assert idx.chunks == []

    def test_single_page(self):
        page = MagicMock()
        page.get_text.return_value = "Some content here."
        idx = create_document_index([page], file_path="test.pdf")
        assert idx.total_pages == 1
        assert idx.file_path == "test.pdf"
        assert len(idx.chunks) >= 1
        assert idx.page_texts[0] == "Some content here."

    def test_multi_page(self):
        pages = []
        for i in range(3):
            page = MagicMock()
            page.get_text.return_value = f"Content of page {i}."
            pages.append(page)
        idx = create_document_index(pages)
        assert idx.total_pages == 3
        assert len(idx.page_texts) == 3

    def test_chunk_ids_unique(self):
        pages = []
        for i in range(3):
            page = MagicMock()
            page.get_text.return_value = f"Content of page {i} with text."
            pages.append(page)
        idx = create_document_index(pages)
        ids = [c.chunk_id for c in idx.chunks]
        assert len(ids) == len(set(ids))

    def test_custom_chunk_size(self):
        page = MagicMock()
        paragraphs = ["Paragraph number %d with text. " % i for i in range(20)]
        page.get_text.return_value = "\n\n".join(paragraphs)
        idx = create_document_index([page], chunk_size=100, chunk_overlap=10)
        assert len(idx.chunks) > 1

    def test_empty_pages_skipped(self):
        pages = []
        empty = MagicMock()
        empty.get_text.return_value = "   "
        content = MagicMock()
        content.get_text.return_value = "Real content."
        pages = [empty, content, empty]
        idx = create_document_index(pages)
        assert idx.total_pages == 3
        assert len(idx.page_texts) == 3
        # Only the non-empty page produces chunks
        assert all(c.page_num == 1 for c in idx.chunks)

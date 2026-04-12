"""Tests para core.compression_engine — Motor de compresión de PDF."""
import pytest
import os
import tempfile

import fitz

from core.compression_engine import (
    CompressionLevel,
    CompressionTechnique,
    CompressionConfig,
    CompressionResult,
    _format_size,
    apply_garbage_cleanup,
    apply_metadata_removal,
    apply_font_subsetting,
    compress_pdf,
    compress_document,
)


# ═══════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def simple_pdf(tmp_path):
    """PDF simple con texto."""
    path = str(tmp_path / "test.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(fitz.Point(72, 72), "Texto de prueba para compresión.", fontsize=14)
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def pdf_with_metadata(tmp_path):
    """PDF con metadatos."""
    path = str(tmp_path / "meta.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(fitz.Point(72, 72), "Documento con metadatos.", fontsize=12)
    doc.set_metadata({
        "title": "Test Title",
        "author": "Test Author",
        "subject": "Test Subject",
        "keywords": "test, compression, pdf",
        "creator": "Test Creator",
    })
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def pdf_doc():
    """Documento PyMuPDF abierto."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(fitz.Point(72, 72), "Documento para comprimir.", fontsize=12)
    return doc


# ═══════════════════════════════════════════════════════════
# Tests: Enums
# ═══════════════════════════════════════════════════════════

class TestCompressionLevel:
    def test_values(self):
        assert CompressionLevel.LOSSLESS == 0
        assert CompressionLevel.LOW == 1
        assert CompressionLevel.MAXIMUM == 4

    def test_ordering(self):
        assert CompressionLevel.LOSSLESS < CompressionLevel.MAXIMUM


class TestCompressionTechnique:
    def test_values(self):
        assert CompressionTechnique.GARBAGE_CLEANUP == 0
        assert CompressionTechnique.IMAGE_JPEG_CONVERSION == 5

    def test_all_techniques(self):
        assert len(CompressionTechnique) == 6


# ═══════════════════════════════════════════════════════════
# Tests: CompressionConfig
# ═══════════════════════════════════════════════════════════

class TestCompressionConfig:
    def test_default(self):
        config = CompressionConfig()
        assert config.level == CompressionLevel.MEDIUM
        assert config.garbage_level == 4
        assert config.image_quality == 75

    def test_from_level_lossless(self):
        config = CompressionConfig.from_level(CompressionLevel.LOSSLESS)
        assert config.image_max_dpi == 0
        assert config.image_quality == 100
        assert config.convert_png_to_jpeg is False

    def test_from_level_maximum(self):
        config = CompressionConfig.from_level(CompressionLevel.MAXIMUM)
        assert config.image_max_dpi == 72
        assert config.image_quality == 40
        assert config.convert_png_to_jpeg is True

    def test_for_email(self):
        config = CompressionConfig.for_email()
        assert config.target_size_kb == 5120

    def test_for_web(self):
        config = CompressionConfig.for_web()
        assert config.target_size_kb == 1024

    def test_for_minimum(self):
        config = CompressionConfig.for_minimum()
        assert config.target_size_kb == 400


# ═══════════════════════════════════════════════════════════
# Tests: CompressionResult
# ═══════════════════════════════════════════════════════════

class TestCompressionResult:
    def test_defaults(self):
        r = CompressionResult()
        assert r.original_size == 0
        assert r.compressed_size == 0
        assert r.success is True

    def test_reduction_percent(self):
        r = CompressionResult(original_size=1000, compressed_size=600)
        assert r.reduction_percent == pytest.approx(40.0)

    def test_reduction_percent_zero(self):
        r = CompressionResult(original_size=0)
        assert r.reduction_percent == 0.0

    def test_size_strings(self):
        r = CompressionResult(original_size=5242880, compressed_size=1048576)
        assert "5.0 MB" == r.original_size_str
        assert "1.0 MB" == r.compressed_size_str


# ═══════════════════════════════════════════════════════════
# Tests: _format_size
# ═══════════════════════════════════════════════════════════

class TestFormatSize:
    def test_bytes(self):
        assert _format_size(500) == "500 B"

    def test_kilobytes(self):
        assert _format_size(1536) == "1.5 KB"

    def test_megabytes(self):
        assert _format_size(2097152) == "2.0 MB"


# ═══════════════════════════════════════════════════════════
# Tests: Técnicas individuales
# ═══════════════════════════════════════════════════════════

class TestGarbageCleanup:
    def test_succeeds(self, pdf_doc):
        assert apply_garbage_cleanup(pdf_doc) is True


class TestMetadataRemoval:
    def test_removes_metadata(self, pdf_with_metadata):
        doc = fitz.open(pdf_with_metadata)
        meta_before = doc.metadata
        assert meta_before.get("title") == "Test Title"
        
        apply_metadata_removal(doc)
        meta_after = doc.metadata
        assert meta_after.get("title", "") == ""
        doc.close()


class TestFontSubsetting:
    def test_succeeds(self, pdf_doc):
        assert apply_font_subsetting(pdf_doc) is True


# ═══════════════════════════════════════════════════════════
# Tests: compress_pdf
# ═══════════════════════════════════════════════════════════

class TestCompressPdf:
    def test_basic_compression(self, simple_pdf, tmp_path):
        output = str(tmp_path / "output.pdf")
        result = compress_pdf(simple_pdf, output)
        
        assert result.success is True
        assert result.original_size > 0
        assert result.compressed_size > 0
        assert os.path.isfile(output)
        assert len(result.techniques_applied) > 0

    def test_lossless_compression(self, simple_pdf, tmp_path):
        output = str(tmp_path / "lossless.pdf")
        config = CompressionConfig.from_level(CompressionLevel.LOSSLESS)
        result = compress_pdf(simple_pdf, output, config)
        
        assert result.success is True
        assert os.path.isfile(output)

    def test_invalid_input(self, tmp_path):
        output = str(tmp_path / "out.pdf")
        result = compress_pdf("nonexistent.pdf", output)
        
        assert result.success is False

    def test_progress_callback(self, simple_pdf, tmp_path):
        output = str(tmp_path / "progress.pdf")
        steps = []
        
        def cb(step, total, desc):
            steps.append((step, total, desc))
        
        result = compress_pdf(simple_pdf, output, progress_callback=cb)
        assert result.success is True
        assert len(steps) > 0


# ═══════════════════════════════════════════════════════════
# Tests: compress_document
# ═══════════════════════════════════════════════════════════

class TestCompressDocument:
    def test_basic(self, pdf_doc):
        data, result = compress_document(pdf_doc)
        assert result.success is True
        assert len(data) > 0
        assert result.original_size > 0
        assert result.compressed_size > 0

    def test_lossless(self, pdf_doc):
        config = CompressionConfig.from_level(CompressionLevel.LOSSLESS)
        data, result = compress_document(pdf_doc, config)
        assert result.success is True

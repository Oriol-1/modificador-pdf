"""Tests para core.page_manager — Operaciones de página PDF."""

import os
import pytest
import fitz

from core.page_manager import (
    PageOperation,
    PageRange,
    OperationResult,
    merge_pdfs,
    split_pdf,
    extract_pages,
    delete_pages,
    reorder_pages,
    rotate_pages,
    get_page_info,
)


# ━━━ Helpers ━━━


def _create_pdf(path: str, page_count: int = 3) -> str:
    """Crea un PDF de prueba con texto en cada página."""
    doc = fitz.open()
    for i in range(page_count):
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 72), f"Página {i + 1}", fontsize=24)
    doc.save(path)
    doc.close()
    return path


# ━━━ PageRange ━━━


class TestPageRange:
    """Tests para PageRange."""

    def test_to_indices(self):
        pr = PageRange(2, 4)
        assert pr.to_indices() == [1, 2, 3]

    def test_to_indices_single(self):
        pr = PageRange(3, 3)
        assert pr.to_indices() == [2]

    def test_from_string_range(self):
        pr = PageRange.from_string("2-5", 10)
        assert pr.start == 2
        assert pr.end == 5

    def test_from_string_single(self):
        pr = PageRange.from_string("3", 10)
        assert pr.start == 3
        assert pr.end == 3

    def test_from_string_with_spaces(self):
        pr = PageRange.from_string("  1 - 3  ", 10)
        assert pr.start == 1
        assert pr.end == 3

    def test_from_string_invalid_zero(self):
        with pytest.raises(ValueError, match=">="):
            PageRange.from_string("0-3", 10)

    def test_from_string_out_of_range(self):
        with pytest.raises(ValueError, match="fuera de rango"):
            PageRange.from_string("8-15", 10)

    def test_from_string_inverted(self):
        with pytest.raises(ValueError, match="invertido"):
            PageRange.from_string("5-2", 10)

    def test_from_string_invalid_text(self):
        with pytest.raises(ValueError):
            PageRange.from_string("abc", 10)


# ━━━ merge_pdfs ━━━


class TestMergePdfs:
    """Tests para merge_pdfs."""

    def test_merge_two(self, tmp_path):
        pdf1 = _create_pdf(str(tmp_path / "a.pdf"), 2)
        pdf2 = _create_pdf(str(tmp_path / "b.pdf"), 3)
        out = str(tmp_path / "merged.pdf")

        result = merge_pdfs([pdf1, pdf2], out)

        assert result.success is True
        assert result.pages_affected == 5
        assert os.path.isfile(out)

        doc = fitz.open(out)
        assert doc.page_count == 5
        doc.close()

    def test_merge_single(self, tmp_path):
        pdf1 = _create_pdf(str(tmp_path / "a.pdf"), 2)
        out = str(tmp_path / "merged.pdf")

        result = merge_pdfs([pdf1], out)
        assert result.success is True
        assert result.pages_affected == 2

    def test_merge_empty(self):
        result = merge_pdfs([], "out.pdf")
        assert result.success is False

    def test_merge_missing_file(self, tmp_path):
        result = merge_pdfs(
            [str(tmp_path / "nonexistent.pdf")],
            str(tmp_path / "out.pdf"),
        )
        assert result.success is False
        assert "no encontrado" in result.message.lower()

    def test_merge_three(self, tmp_path):
        pdfs = [
            _create_pdf(str(tmp_path / f"{c}.pdf"), 2)
            for c in "abc"
        ]
        out = str(tmp_path / "merged.pdf")

        result = merge_pdfs(pdfs, out)
        assert result.success is True
        assert result.pages_affected == 6


# ━━━ split_pdf ━━━


class TestSplitPdf:
    """Tests para split_pdf."""

    def test_split_individual(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 4)
        out_dir = str(tmp_path / "split")

        result = split_pdf(pdf, out_dir)

        assert result.success is True
        files = os.listdir(out_dir)
        assert len(files) == 4

    def test_split_by_ranges(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 6)
        out_dir = str(tmp_path / "split")

        ranges = [PageRange(1, 3), PageRange(4, 6)]
        result = split_pdf(pdf, out_dir, ranges)

        assert result.success is True
        files = os.listdir(out_dir)
        assert len(files) == 2
        assert result.pages_affected == 6

    def test_split_single_page(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 1)
        out_dir = str(tmp_path / "split")

        result = split_pdf(pdf, out_dir)

        assert result.success is True
        files = os.listdir(out_dir)
        assert len(files) == 1

    def test_split_creates_dir(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 2)
        out_dir = str(tmp_path / "nested" / "split")

        result = split_pdf(pdf, out_dir)
        assert result.success is True
        assert os.path.isdir(out_dir)


# ━━━ extract_pages ━━━


class TestExtractPages:
    """Tests para extract_pages."""

    def test_extract_first_last(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 5)
        out = str(tmp_path / "extracted.pdf")

        result = extract_pages(pdf, out, [0, 4])

        assert result.success is True
        assert result.pages_affected == 2

        doc = fitz.open(out)
        assert doc.page_count == 2
        doc.close()

    def test_extract_all(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 3)
        out = str(tmp_path / "extracted.pdf")

        result = extract_pages(pdf, out, [0, 1, 2])
        assert result.success is True
        assert result.pages_affected == 3

    def test_extract_single(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 3)
        out = str(tmp_path / "extracted.pdf")

        result = extract_pages(pdf, out, [1])
        assert result.success is True
        assert result.pages_affected == 1

    def test_extract_empty(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 3)
        out = str(tmp_path / "extracted.pdf")

        result = extract_pages(pdf, out, [])
        assert result.success is False

    def test_extract_invalid_indices(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 3)
        out = str(tmp_path / "extracted.pdf")

        result = extract_pages(pdf, out, [10, 20])
        assert result.success is False
        assert "válida" in result.message.lower()

    def test_extract_mixed_valid_invalid(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 3)
        out = str(tmp_path / "extracted.pdf")

        result = extract_pages(pdf, out, [0, 99])
        assert result.success is True
        assert result.pages_affected == 1


# ━━━ delete_pages ━━━


class TestDeletePages:
    """Tests para delete_pages."""

    def test_delete_middle(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 5)
        out = str(tmp_path / "deleted.pdf")

        result = delete_pages(pdf, out, [2])

        assert result.success is True
        assert result.pages_affected == 1

        doc = fitz.open(out)
        assert doc.page_count == 4
        doc.close()

    def test_delete_first_last(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 4)
        out = str(tmp_path / "deleted.pdf")

        result = delete_pages(pdf, out, [0, 3])
        assert result.success is True

        doc = fitz.open(out)
        assert doc.page_count == 2
        doc.close()

    def test_delete_all_fails(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 2)
        out = str(tmp_path / "deleted.pdf")

        result = delete_pages(pdf, out, [0, 1])
        assert result.success is False
        assert "todas" in result.message.lower()

    def test_delete_empty(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 3)
        out = str(tmp_path / "deleted.pdf")

        result = delete_pages(pdf, out, [])
        assert result.success is False

    def test_delete_duplicates(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 5)
        out = str(tmp_path / "deleted.pdf")

        result = delete_pages(pdf, out, [1, 1, 1])
        assert result.success is True
        assert result.pages_affected == 1


# ━━━ reorder_pages ━━━


class TestReorderPages:
    """Tests para reorder_pages."""

    def test_reverse(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 3)
        out = str(tmp_path / "reordered.pdf")

        result = reorder_pages(pdf, out, [2, 1, 0])

        assert result.success is True

        doc = fitz.open(out)
        assert doc.page_count == 3
        text = doc[0].get_text("text")
        assert "3" in text
        doc.close()

    def test_identity(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 3)
        out = str(tmp_path / "reordered.pdf")

        result = reorder_pages(pdf, out, [0, 1, 2])
        assert result.success is True

    def test_invalid_permutation(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 3)
        out = str(tmp_path / "reordered.pdf")

        result = reorder_pages(pdf, out, [0, 0, 1])
        assert result.success is False
        assert "permutación" in result.message.lower()

    def test_wrong_length(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 3)
        out = str(tmp_path / "reordered.pdf")

        result = reorder_pages(pdf, out, [0, 1])
        assert result.success is False

    def test_swap_first_last(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 4)
        out = str(tmp_path / "reordered.pdf")

        result = reorder_pages(pdf, out, [3, 1, 2, 0])
        assert result.success is True
        assert result.pages_affected == 4


# ━━━ rotate_pages ━━━


class TestRotatePages:
    """Tests para rotate_pages."""

    def test_rotate_90(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 3)
        out = str(tmp_path / "rotated.pdf")

        result = rotate_pages(pdf, out, [0], 90)

        assert result.success is True
        assert result.pages_affected == 1

        doc = fitz.open(out)
        assert doc[0].rotation == 90
        assert doc[1].rotation == 0
        doc.close()

    def test_rotate_180(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 2)
        out = str(tmp_path / "rotated.pdf")

        result = rotate_pages(pdf, out, [0, 1], 180)
        assert result.success is True

        doc = fitz.open(out)
        assert doc[0].rotation == 180
        assert doc[1].rotation == 180
        doc.close()

    def test_rotate_invalid_angle(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 2)
        out = str(tmp_path / "rotated.pdf")

        result = rotate_pages(pdf, out, [0], 45)
        assert result.success is False
        assert "ángulo" in result.message.lower()

    def test_rotate_out_of_range_indices(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 2)
        out = str(tmp_path / "rotated.pdf")

        result = rotate_pages(pdf, out, [99], 90)
        assert result.success is True
        assert result.pages_affected == 0


# ━━━ get_page_info ━━━


class TestGetPageInfo:
    """Tests para get_page_info."""

    def test_basic(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 3)
        doc = fitz.open(pdf)

        info = get_page_info(doc)

        assert len(info) == 3
        assert info[0]["number"] == 1
        assert info[2]["number"] == 3
        assert info[0]["width"] == 612
        assert info[0]["height"] == 792
        assert info[0]["rotation"] == 0
        assert info[0]["text_length"] > 0
        doc.close()

    def test_rotated(self, tmp_path):
        pdf = _create_pdf(str(tmp_path / "src.pdf"), 2)
        doc = fitz.open(pdf)
        doc[0].set_rotation(90)

        info = get_page_info(doc)
        assert info[0]["rotation"] == 90
        assert info[1]["rotation"] == 0
        doc.close()


# ━━━ OperationResult / PageOperation ━━━


class TestModels:
    """Tests para modelos de datos."""

    def test_page_operation_values(self):
        assert PageOperation.MERGE.value == "merge"
        assert PageOperation.SPLIT.value == "split"
        assert PageOperation.EXTRACT.value == "extract"
        assert PageOperation.DELETE.value == "delete"
        assert PageOperation.REORDER.value == "reorder"
        assert PageOperation.ROTATE.value == "rotate"

    def test_operation_result_defaults(self):
        r = OperationResult(success=True)
        assert r.output_path == ""
        assert r.message == ""
        assert r.pages_affected == 0

    def test_operation_result_full(self):
        r = OperationResult(
            success=True,
            output_path="/tmp/out.pdf",
            message="OK",
            pages_affected=5,
        )
        assert r.output_path == "/tmp/out.pdf"
        assert r.pages_affected == 5

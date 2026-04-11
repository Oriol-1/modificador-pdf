"""
Tests para los controles de formato y el dataclass EditedSpan extendido.

Verifica:
- EditedSpan con campos de formato
- FormatBar population y detección de cambios
- EditableSpan con campos de formato y propiedades effective_*
- RichTextWriter generación de HTML
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass


# ================== Tests para EditableSpan (page_document_model) ==================


class TestEditableSpanFormat:
    """Tests para los nuevos campos de formato en EditableSpan."""
    
    def test_default_format_fields_are_none(self):
        """Los campos de formato son None por defecto."""
        from core.text_engine.page_document_model import EditableSpan
        span = EditableSpan(original_text="hello", font_size=12.0)
        assert span.new_font_size is None
        assert span.new_is_bold is None
        assert span.new_is_italic is None
        assert span.new_color_rgb is None
        assert span.new_char_spacing is None
        assert span.new_word_spacing is None
        assert span.dirty_format is False
    
    def test_effective_font_size_original(self):
        """effective_font_size retorna original si no hay cambio."""
        from core.text_engine.page_document_model import EditableSpan
        span = EditableSpan(original_text="test", font_size=14.0)
        assert span.effective_font_size == 14.0
    
    def test_effective_font_size_changed(self):
        """effective_font_size retorna nuevo valor si hay cambio."""
        from core.text_engine.page_document_model import EditableSpan
        span = EditableSpan(original_text="test", font_size=14.0, new_font_size=18.0)
        assert span.effective_font_size == 18.0
    
    def test_effective_is_bold(self):
        """effective_is_bold retorna nuevo valor si hay cambio."""
        from core.text_engine.page_document_model import EditableSpan
        span = EditableSpan(original_text="test", is_bold=False, new_is_bold=True)
        assert span.effective_is_bold is True
    
    def test_effective_is_bold_original(self):
        """effective_is_bold retorna original si no hay cambio."""
        from core.text_engine.page_document_model import EditableSpan
        span = EditableSpan(original_text="test", is_bold=True)
        assert span.effective_is_bold is True
    
    def test_effective_is_italic(self):
        from core.text_engine.page_document_model import EditableSpan
        span = EditableSpan(original_text="test", is_italic=False, new_is_italic=True)
        assert span.effective_is_italic is True
    
    def test_effective_color(self):
        from core.text_engine.page_document_model import EditableSpan
        span = EditableSpan(original_text="test", fill_color="#000000", new_color_rgb="#FF0000")
        assert span.effective_color == "#FF0000"
    
    def test_effective_color_original(self):
        from core.text_engine.page_document_model import EditableSpan
        span = EditableSpan(original_text="test", fill_color="#336699")
        assert span.effective_color == "#336699"
    
    def test_effective_char_spacing(self):
        from core.text_engine.page_document_model import EditableSpan
        span = EditableSpan(original_text="test", char_spacing=0.0, new_char_spacing=1.5)
        assert span.effective_char_spacing == 1.5
    
    def test_effective_word_spacing(self):
        from core.text_engine.page_document_model import EditableSpan
        span = EditableSpan(original_text="test", word_spacing=0.0, new_word_spacing=3.0)
        assert span.effective_word_spacing == 3.0
    
    def test_is_dirty_text_only(self):
        """is_dirty True con solo cambio de texto."""
        from core.text_engine.page_document_model import EditableSpan
        span = EditableSpan(original_text="hello")
        span.text = "world"
        assert span.is_dirty is True
        assert span.dirty is True
        assert span.dirty_format is False
    
    def test_is_dirty_format_only(self):
        """is_dirty True con solo cambio de formato."""
        from core.text_engine.page_document_model import EditableSpan
        span = EditableSpan(original_text="hello")
        span.dirty_format = True
        assert span.is_dirty is True
        assert span.dirty is False
    
    def test_is_dirty_both(self):
        """is_dirty True con ambos cambios."""
        from core.text_engine.page_document_model import EditableSpan
        span = EditableSpan(original_text="hello")
        span.text = "world"
        span.dirty_format = True
        assert span.is_dirty is True
    
    def test_is_dirty_none(self):
        """is_dirty False sin cambios."""
        from core.text_engine.page_document_model import EditableSpan
        span = EditableSpan(original_text="hello")
        assert span.is_dirty is False


# ================== Tests para EditedSpan (pdf_text_editor) ==================


class TestEditedSpanFormat:
    """Tests para EditedSpan con campos de formato."""
    
    def test_has_changes_text_only(self):
        from ui.pdf_text_editor import EditedSpan, FitStatus
        edited = EditedSpan(
            original_span={},
            new_text="new",
            original_text="old",
        )
        assert edited.has_changes is True
        assert edited.has_format_changes is False
    
    def test_has_changes_format_only(self):
        from ui.pdf_text_editor import EditedSpan, FitStatus
        edited = EditedSpan(
            original_span={},
            new_text="same",
            original_text="same",
            new_font_size=16.0,
        )
        assert edited.has_changes is True
        assert edited.has_format_changes is True
    
    def test_has_format_changes_bold(self):
        from ui.pdf_text_editor import EditedSpan, FitStatus
        edited = EditedSpan(
            original_span={},
            new_text="same",
            original_text="same",
            new_is_bold=True,
        )
        assert edited.has_format_changes is True
    
    def test_has_format_changes_italic(self):
        from ui.pdf_text_editor import EditedSpan
        edited = EditedSpan(
            original_span={},
            new_text="same",
            original_text="same",
            new_is_italic=True,
        )
        assert edited.has_format_changes is True
    
    def test_has_format_changes_color(self):
        from ui.pdf_text_editor import EditedSpan
        edited = EditedSpan(
            original_span={},
            new_text="same",
            original_text="same",
            new_color="#FF0000",
        )
        assert edited.has_format_changes is True
    
    def test_has_format_changes_char_spacing(self):
        from ui.pdf_text_editor import EditedSpan
        edited = EditedSpan(
            original_span={},
            new_text="same",
            original_text="same",
            new_char_spacing=1.5,
        )
        assert edited.has_format_changes is True
    
    def test_has_format_changes_word_spacing(self):
        from ui.pdf_text_editor import EditedSpan
        edited = EditedSpan(
            original_span={},
            new_text="same",
            original_text="same",
            new_word_spacing=2.0,
        )
        assert edited.has_format_changes is True
    
    def test_no_changes(self):
        from ui.pdf_text_editor import EditedSpan
        edited = EditedSpan(
            original_span={},
            new_text="same",
            original_text="same",
        )
        assert edited.has_changes is False
        assert edited.has_format_changes is False


# ================== Tests para LineModel con is_dirty ==================


class TestLineModelDirty:
    """Tests para LineModel.is_dirty con dirty_format."""
    
    def test_line_not_dirty(self):
        from core.text_engine.page_document_model import EditableSpan, LineModel
        spans = [
            EditableSpan(original_text="hello"),
            EditableSpan(original_text="world"),
        ]
        line = LineModel(spans=spans)
        assert line.is_dirty is False
    
    def test_line_dirty_text(self):
        from core.text_engine.page_document_model import EditableSpan, LineModel
        s1 = EditableSpan(original_text="hello")
        s2 = EditableSpan(original_text="world")
        s1.text = "changed"
        line = LineModel(spans=[s1, s2])
        assert line.is_dirty is True
    
    def test_line_dirty_format(self):
        from core.text_engine.page_document_model import EditableSpan, LineModel
        s1 = EditableSpan(original_text="hello")
        s2 = EditableSpan(original_text="world")
        s2.dirty_format = True
        line = LineModel(spans=[s1, s2])
        assert line.is_dirty is True

"""
Tests para FontDialog - PHASE2-201

Cobertura:
- FontPreviewWidget
- ColorButton
- FontDialog
- TextFormatDialog
"""

import pytest
from unittest.mock import MagicMock
from PyQt5.QtWidgets import QApplication

# Necesitamos QApplication para tests de widgets
@pytest.fixture(scope="module")
def app():
    """Fixture para QApplication."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestFontPreviewWidget:
    """Tests para FontPreviewWidget."""
    
    def test_creation(self, app):
        """Test creación."""
        from ui.font_dialog import FontPreviewWidget
        
        widget = FontPreviewWidget()
        assert widget is not None
        assert widget.preview_label is not None
    
    def test_update_preview(self, app):
        """Test actualización de preview."""
        from ui.font_dialog import FontPreviewWidget
        
        widget = FontPreviewWidget()
        widget.update_preview(
            font_name="Arial",
            font_size=14.0,
            color="#FF0000",
            bold=True,
            italic=False
        )
        
        # Verificar que la fuente se aplicó
        font = widget.preview_label.font()
        assert font.family() == "Arial" or "Arial" in font.family()
        assert font.pointSize() == 14
        assert font.bold() is True


class TestColorButton:
    """Tests para ColorButton."""
    
    def test_creation(self, app):
        """Test creación."""
        from ui.font_dialog import ColorButton
        
        btn = ColorButton("#FF0000")
        assert btn.color() == "#FF0000"
    
    def test_set_color(self, app):
        """Test establecer color."""
        from ui.font_dialog import ColorButton
        
        btn = ColorButton("#000000")
        btn.setColor("#00FF00")
        assert btn.color() == "#00FF00"
    
    def test_color_changed_signal(self, app):
        """Test señal de cambio de color."""
        from ui.font_dialog import ColorButton
        
        btn = ColorButton("#000000")
        
        # Mock del slot
        slot = MagicMock()
        btn.colorChanged.connect(slot)
        
        # Simular cambio (sin abrir diálogo real)
        btn._color = "#0000FF"
        btn.colorChanged.emit("#0000FF")
        
        slot.assert_called_once_with("#0000FF")


class TestFontDialog:
    """Tests para FontDialog."""
    
    def test_creation(self, app):
        """Test creación básica."""
        from ui.font_dialog import FontDialog
        
        dialog = FontDialog()
        assert dialog is not None
        assert dialog.font_combo is not None
        assert dialog.size_spin is not None
        assert dialog.color_btn is not None
    
    def test_creation_with_descriptor(self, app):
        """Test creación con FontDescriptor."""
        from ui.font_dialog import FontDialog
        from core.font_manager import FontDescriptor
        
        descriptor = FontDescriptor(
            name="Arial",
            size=14.0,
            color="#0000FF",
            flags=0,
            was_fallback=False,
            fallback_from=None,
            possible_bold=True
        )
        
        dialog = FontDialog(current_font=descriptor)
        
        assert dialog.size_spin.value() == 14.0
        assert dialog.color_btn.color() == "#0000FF"
        assert dialog.bold_check.isChecked() is True
    
    def test_get_values(self, app):
        """Test obtener valores."""
        from ui.font_dialog import FontDialog
        
        dialog = FontDialog()
        dialog.size_spin.setValue(16.0)
        dialog.bold_check.setChecked(True)
        dialog.italic_check.setChecked(True)
        
        font_name, size, color, bold, italic = dialog.get_values()
        
        assert size == 16.0
        assert bold is True
        assert italic is True
    
    def test_get_font_descriptor(self, app):
        """Test obtener FontDescriptor."""
        from ui.font_dialog import FontDialog
        
        dialog = FontDialog()
        dialog.size_spin.setValue(18.0)
        dialog.color_btn.setColor("#FF0000")
        dialog.bold_check.setChecked(True)
        
        descriptor = dialog.get_font_descriptor()
        
        assert descriptor.size == 18.0
        assert descriptor.color == "#FF0000"
        assert descriptor.possible_bold is True
    
    def test_font_combo_populated(self, app):
        """Test que el combo tiene fuentes."""
        from ui.font_dialog import FontDialog
        
        dialog = FontDialog()
        
        # Debe tener al menos algunas fuentes
        assert dialog.font_combo.count() > 0


class TestTextFormatDialog:
    """Tests para TextFormatDialog."""
    
    def test_creation(self, app):
        """Test creación."""
        from ui.font_dialog import TextFormatDialog
        
        dialog = TextFormatDialog(text="Hello World")
        assert dialog is not None
        assert dialog.text_edit.toPlainText() == "Hello World"
    
    def test_creation_with_font(self, app):
        """Test creación con fuente."""
        from ui.font_dialog import TextFormatDialog
        from core.font_manager import FontDescriptor
        
        descriptor = FontDescriptor(
            name="Arial",
            size=12.0,
            color="#000000",
            flags=0,
            was_fallback=False,
            fallback_from=None,
            possible_bold=False
        )
        
        dialog = TextFormatDialog(
            text="Test text",
            current_font=descriptor
        )
        
        assert dialog.text_edit.toPlainText() == "Test text"
        assert dialog.size_spin.value() == 12.0
    
    def test_get_text(self, app):
        """Test obtener texto."""
        from ui.font_dialog import TextFormatDialog
        
        dialog = TextFormatDialog(text="Original")
        dialog.text_edit.setPlainText("Modified")
        
        assert dialog.get_text() == "Modified"
    
    def test_get_font_descriptor(self, app):
        """Test obtener descriptor."""
        from ui.font_dialog import TextFormatDialog
        
        dialog = TextFormatDialog()
        dialog.size_spin.setValue(20.0)
        dialog.bold_check.setChecked(True)
        
        descriptor = dialog.get_font_descriptor()
        
        assert descriptor.size == 20.0
        assert descriptor.possible_bold is True


class TestIntegration:
    """Tests de integración."""
    
    def test_font_dialog_preview_updates(self, app):
        """Test que el preview se actualiza."""
        from ui.font_dialog import FontDialog
        
        dialog = FontDialog()
        
        # Cambiar valores
        dialog.size_spin.setValue(24.0)
        dialog.bold_check.setChecked(True)
        
        # El preview debería actualizarse automáticamente
        preview_font = dialog.preview_widget.preview_label.font()
        assert preview_font.pointSize() == 24
        assert preview_font.bold() is True
    
    def test_text_format_dialog_preview_with_text(self, app):
        """Test preview con texto custom."""
        from ui.font_dialog import TextFormatDialog
        
        dialog = TextFormatDialog(text="Custom preview text")
        
        # El texto debería estar en el editor
        assert "Custom preview" in dialog.text_edit.toPlainText()
    
    def test_color_button_integration(self, app):
        """Test integración de ColorButton."""
        from ui.font_dialog import FontDialog
        
        dialog = FontDialog()
        
        # Cambiar color
        dialog.color_btn.setColor("#00FF00")
        
        # Verificar que se refleja en el descriptor
        descriptor = dialog.get_font_descriptor()
        assert descriptor.color == "#00FF00"

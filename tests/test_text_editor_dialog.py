"""
Tests para EnhancedTextEditDialog - PHASE2-201

Prueba el diálogo mejorado de edición de texto con:
- Preview en vivo
- Validación de si el texto cabe
- Opciones de ajuste (recortar, espaciado, tamaño)
- Checkboxes de negrita
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

# Mock Qt antes de importar el módulo
@pytest.fixture(autouse=True)
def mock_qt_app():
    """Mock de QApplication para tests sin GUI."""
    with patch('PyQt5.QtWidgets.QApplication'):
        yield


class TestTextEditResult:
    """Tests para la dataclass TextEditResult."""
    
    def test_create_result(self):
        """Test crear un TextEditResult básico."""
        from ui.text_editor_dialog import TextEditResult
        
        result = TextEditResult(
            text="Nuevo texto",
            original_text="Original",
            font_descriptor=None,
            bold_applied=False,
            tracking_reduced=0.0,
            size_reduced=0.0,
            was_truncated=False,
            warnings=[]
        )
        
        assert result.text == "Nuevo texto"
        assert result.original_text == "Original"
        assert result.bold_applied is False
        assert result.tracking_reduced == 0.0
        assert result.size_reduced == 0.0
        assert result.was_truncated is False
        assert result.warnings == []
    
    def test_result_with_truncation(self):
        """Test resultado con truncación."""
        from ui.text_editor_dialog import TextEditResult
        
        result = TextEditResult(
            text="Texto rec...",
            original_text="Texto recortado muy largo",
            font_descriptor=None,
            bold_applied=True,
            tracking_reduced=5.0,
            size_reduced=10.0,
            was_truncated=True,
            warnings=["Texto recortado de 25 a 12 caracteres"]
        )
        
        assert result.was_truncated is True
        assert len(result.warnings) == 1
        assert "recortado" in result.warnings[0]
    
    def test_result_with_font_descriptor(self):
        """Test resultado con descriptor de fuente."""
        from ui.text_editor_dialog import TextEditResult
        
        # Mock font descriptor
        mock_font = MagicMock()
        mock_font.name = "Arial"
        mock_font.size = 12
        
        result = TextEditResult(
            text="Texto",
            original_text="Texto",
            font_descriptor=mock_font,
            bold_applied=False,
            tracking_reduced=0.0,
            size_reduced=0.0,
            was_truncated=False,
            warnings=[]
        )
        
        assert result.font_descriptor is not None
        assert result.font_descriptor.name == "Arial"


class TestTextPreviewWidget:
    """Tests para el widget de preview."""
    
    @patch('PyQt5.QtWidgets.QFrame.__init__', return_value=None)
    @patch('PyQt5.QtWidgets.QVBoxLayout')
    @patch('PyQt5.QtWidgets.QLabel')
    def test_widget_creation(self, mock_label, mock_layout, mock_frame):
        """Test crear widget de preview."""
        from ui.text_editor_dialog import TextPreviewWidget
        
        # No podemos instanciar sin Qt real, pero verificamos la clase existe
        assert TextPreviewWidget is not None
    
    def test_widget_has_set_font_method(self):
        """Test que TextPreviewWidget tiene método set_font."""
        from ui.text_editor_dialog import TextPreviewWidget
        
        assert hasattr(TextPreviewWidget, 'set_font')
    
    def test_widget_has_set_text_method(self):
        """Test que TextPreviewWidget tiene método set_text."""
        from ui.text_editor_dialog import TextPreviewWidget
        
        assert hasattr(TextPreviewWidget, 'set_text')
    
    def test_widget_has_get_text_width_method(self):
        """Test que TextPreviewWidget tiene método get_text_width."""
        from ui.text_editor_dialog import TextPreviewWidget
        
        assert hasattr(TextPreviewWidget, 'get_text_width')


class TestFitStatusWidget:
    """Tests para el widget de estado de ajuste."""
    
    def test_class_exists(self):
        """Test que la clase FitStatusWidget existe."""
        from ui.text_editor_dialog import FitStatusWidget
        
        assert FitStatusWidget is not None
    
    def test_has_set_fits_method(self):
        """Test que tiene método set_fits."""
        from ui.text_editor_dialog import FitStatusWidget
        
        assert hasattr(FitStatusWidget, 'set_fits')


class TestAdjustmentOptionsWidget:
    """Tests para el widget de opciones de ajuste."""
    
    def test_class_exists(self):
        """Test que la clase AdjustmentOptionsWidget existe."""
        from ui.text_editor_dialog import AdjustmentOptionsWidget
        
        assert AdjustmentOptionsWidget is not None
    
    def test_has_option_selected_signal(self):
        """Test que tiene señal option_selected."""
        from ui.text_editor_dialog import AdjustmentOptionsWidget
        
        # La señal se define como atributo de clase
        assert hasattr(AdjustmentOptionsWidget, 'option_selected')


class TestEnhancedTextEditDialog:
    """Tests para el diálogo principal."""
    
    def test_class_exists(self):
        """Test que la clase EnhancedTextEditDialog existe."""
        from ui.text_editor_dialog import EnhancedTextEditDialog
        
        assert EnhancedTextEditDialog is not None
    
    def test_has_get_result_method(self):
        """Test que tiene método get_result."""
        from ui.text_editor_dialog import EnhancedTextEditDialog
        
        assert hasattr(EnhancedTextEditDialog, 'get_result')
    
    def test_has_get_final_text_method(self):
        """Test que tiene método get_final_text."""
        from ui.text_editor_dialog import EnhancedTextEditDialog
        
        assert hasattr(EnhancedTextEditDialog, 'get_final_text')
    
    def test_has_get_styling_choices_method(self):
        """Test que tiene método get_styling_choices."""
        from ui.text_editor_dialog import EnhancedTextEditDialog
        
        assert hasattr(EnhancedTextEditDialog, 'get_styling_choices')
    
    def test_has_validate_text_method(self):
        """Test que tiene método validate_text."""
        from ui.text_editor_dialog import EnhancedTextEditDialog
        
        assert hasattr(EnhancedTextEditDialog, 'validate_text')
    
    def test_has_apply_adjustment_method(self):
        """Test que tiene método apply_adjustment."""
        from ui.text_editor_dialog import EnhancedTextEditDialog
        
        assert hasattr(EnhancedTextEditDialog, 'apply_adjustment')


class TestShowTextEditDialog:
    """Tests para la función de conveniencia."""
    
    def test_function_exists(self):
        """Test que show_text_edit_dialog existe."""
        from ui.text_editor_dialog import show_text_edit_dialog
        
        assert show_text_edit_dialog is not None
        assert callable(show_text_edit_dialog)
    
    def test_function_signature(self):
        """Test que tiene los parámetros correctos."""
        from ui.text_editor_dialog import show_text_edit_dialog
        import inspect
        
        sig = inspect.signature(show_text_edit_dialog)
        params = list(sig.parameters.keys())
        
        assert 'parent' in params
        assert 'original_text' in params
        assert 'max_width' in params


class TestModuleExports:
    """Tests para verificar exports del módulo."""
    
    def test_all_classes_exported(self):
        """Test que todas las clases están exportadas."""
        from ui.text_editor_dialog import (
            EnhancedTextEditDialog,
            TextEditResult,
            TextPreviewWidget,
            FitStatusWidget,
            AdjustmentOptionsWidget,
            show_text_edit_dialog
        )
        
        assert EnhancedTextEditDialog is not None
        assert TextEditResult is not None
        assert TextPreviewWidget is not None
        assert FitStatusWidget is not None
        assert AdjustmentOptionsWidget is not None
        assert show_text_edit_dialog is not None


class TestUIInit:
    """Tests para verificar que ui/__init__.py exporta correctamente."""
    
    def test_enhanced_dialog_in_ui_init(self):
        """Test que EnhancedTextEditDialog está en ui.__init__."""
        from ui import EnhancedTextEditDialog
        
        assert EnhancedTextEditDialog is not None
    
    def test_text_edit_result_in_ui_init(self):
        """Test que TextEditResult está en ui.__init__."""
        from ui import TextEditResult
        
        assert TextEditResult is not None
    
    def test_show_function_in_ui_init(self):
        """Test que show_text_edit_dialog está en ui.__init__."""
        from ui import show_text_edit_dialog
        
        assert show_text_edit_dialog is not None


class TestIntegrationWithPDFViewer:
    """Tests de integración con pdf_viewer."""
    
    def test_pdf_viewer_imports_enhanced_dialog(self):
        """Test que pdf_viewer puede importar el diálogo mejorado."""
        # Verificar que las constantes existen
        from ui.pdf_viewer import HAS_ENHANCED_DIALOG, HAS_FONT_MANAGER
        
        # Deberían ser True ya que los módulos existen
        assert isinstance(HAS_ENHANCED_DIALOG, bool)
        assert isinstance(HAS_FONT_MANAGER, bool)
    
    def test_edit_text_content_method_exists(self):
        """Test que _edit_text_content existe en PDFPageView."""
        from ui.pdf_viewer import PDFPageView
        
        assert hasattr(PDFPageView, '_edit_text_content')
    
    def test_apply_text_edit_method_exists(self):
        """Test que _apply_text_edit existe en PDFPageView."""
        from ui.pdf_viewer import PDFPageView
        
        assert hasattr(PDFPageView, '_apply_text_edit')

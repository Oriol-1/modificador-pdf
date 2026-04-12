"""
Tests para PDFTextEditor - Editor de texto PDF integrado.

PHASE3-3C05: Tests para el editor principal que integra todos los componentes.
"""

import pytest
from unittest.mock import patch

# Intentar importar PyQt5
pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import QApplication  # noqa: E402

# Asegurar QApplication existe
@pytest.fixture(scope="session")
def qapp():
    """Crear QApplication para tests."""
    app = QApplication.instance() or QApplication([])
    yield app


# Importar módulo bajo test
from ui.pdf_text_editor import (  # noqa: E402
    # Enums
    EditMode,
    FitStatus,
    # Dataclasses
    EditedSpan,
    EditorConfig,
    # Widgets
    MetricsStatusBar,
    SpanComparisonWidget,
    EditorToolBar,
    TextEditArea,
    PDFTextEditorDialog,
    PDFTextEditor,
    # Factory functions
    create_pdf_text_editor,
    show_pdf_text_editor,
    # Flags
    HAS_TEXT_ENGINE,
    HAS_FONT_MANAGER,
    HAS_PROPERTY_INSPECTOR,
    HAS_SELECTION_OVERLAY,
)


# ================== Fixtures ==================


@pytest.fixture
def sample_span_data():
    """Datos de span de ejemplo para tests."""
    return {
        'text': 'Texto de ejemplo para editar',
        'font_name': 'Helvetica',
        'font_size': 12.0,
        'is_bold': False,
        'is_italic': False,
        'fill_color': '#000000',
        'bbox': (100.0, 200.0, 300.0, 220.0),  # x0, y0, x1, y1
        'origin': (100.0, 215.0),
        'char_spacing': 0.0,
        'word_spacing': 0.0,
    }


@pytest.fixture
def sample_span_bold():
    """Datos de span en negrita."""
    return {
        'text': 'Texto en negrita',
        'font_name': 'Helvetica-Bold',
        'font_size': 14.0,
        'is_bold': True,
        'is_italic': False,
        'fill_color': '#333333',
        'bbox': (50.0, 100.0, 200.0, 120.0),
    }


@pytest.fixture
def config_preserve():
    """Configuración en modo preserve."""
    return EditorConfig(mode=EditMode.PRESERVE)


@pytest.fixture
def config_flexible():
    """Configuración en modo flexible."""
    return EditorConfig(mode=EditMode.FLEXIBLE)


@pytest.fixture
def config_no_reflow():
    """Configuración en modo no_reflow."""
    return EditorConfig(mode=EditMode.NO_REFLOW)


# ================== Tests: Enums ==================


class TestEditMode:
    """Tests para el enum EditMode."""
    
    def test_preserve_mode(self):
        """Modo preserve tiene valor correcto."""
        assert EditMode.PRESERVE.value == "preserve"
    
    def test_flexible_mode(self):
        """Modo flexible tiene valor correcto."""
        assert EditMode.FLEXIBLE.value == "flexible"
    
    def test_no_reflow_mode(self):
        """Modo no_reflow tiene valor correcto."""
        assert EditMode.NO_REFLOW.value == "no_reflow"
    
    def test_all_modes_available(self):
        """Todos los modos esperados están disponibles."""
        modes = list(EditMode)
        assert len(modes) == 3
        assert EditMode.PRESERVE in modes
        assert EditMode.FLEXIBLE in modes
        assert EditMode.NO_REFLOW in modes


class TestFitStatus:
    """Tests para el enum FitStatus."""
    
    def test_fits_status(self):
        """Estado fits tiene valor correcto."""
        assert FitStatus.FITS.value == "fits"
    
    def test_tight_status(self):
        """Estado tight tiene valor correcto."""
        assert FitStatus.TIGHT.value == "tight"
    
    def test_overflow_status(self):
        """Estado overflow tiene valor correcto."""
        assert FitStatus.OVERFLOW.value == "overflow"
    
    def test_unknown_status(self):
        """Estado unknown tiene valor correcto."""
        assert FitStatus.UNKNOWN.value == "unknown"
    
    def test_all_statuses_available(self):
        """Todos los estados esperados están disponibles."""
        statuses = list(FitStatus)
        assert len(statuses) == 4


# ================== Tests: Dataclasses ==================


class TestEditedSpan:
    """Tests para EditedSpan dataclass."""
    
    def test_creation(self, sample_span_data):
        """Crear EditedSpan básico."""
        edited = EditedSpan(
            original_span=sample_span_data,
            new_text="Nuevo texto",
            original_text=sample_span_data['text']
        )
        assert edited.new_text == "Nuevo texto"
        assert edited.original_text == sample_span_data['text']
        assert edited.fit_status == FitStatus.UNKNOWN
    
    def test_has_changes_true(self, sample_span_data):
        """has_changes es True cuando el texto cambió."""
        edited = EditedSpan(
            original_span=sample_span_data,
            new_text="Nuevo texto diferente",
            original_text=sample_span_data['text']
        )
        assert edited.has_changes is True
    
    def test_has_changes_false(self, sample_span_data):
        """has_changes es False cuando el texto es igual."""
        edited = EditedSpan(
            original_span=sample_span_data,
            new_text=sample_span_data['text'],
            original_text=sample_span_data['text']
        )
        assert edited.has_changes is False
    
    def test_has_changes_with_modifications(self, sample_span_data):
        """has_changes es True con modificaciones en propiedades."""
        edited = EditedSpan(
            original_span=sample_span_data,
            new_text=sample_span_data['text'],
            original_text=sample_span_data['text'],
            modifications={'font_size': 14.0}
        )
        assert edited.has_changes is True
    
    def test_fit_status_custom(self, sample_span_data):
        """Fit status personalizado."""
        edited = EditedSpan(
            original_span=sample_span_data,
            new_text="Texto muy largo que no cabe",
            original_text=sample_span_data['text'],
            fit_status=FitStatus.OVERFLOW
        )
        assert edited.fit_status == FitStatus.OVERFLOW


class TestEditorConfig:
    """Tests para EditorConfig dataclass."""
    
    def test_default_values(self):
        """Valores por defecto correctos."""
        config = EditorConfig()
        assert config.mode == EditMode.PRESERVE
        assert config.show_metrics is True
        assert config.show_guidelines is True
        assert config.auto_validate is True
        assert config.validate_delay_ms == 300
        assert config.max_undo_steps == 50
        assert config.show_property_panel is True
        assert config.preserve_whitespace is True
    
    def test_custom_values(self):
        """Valores personalizados."""
        config = EditorConfig(
            mode=EditMode.FLEXIBLE,
            show_metrics=False,
            validate_delay_ms=500
        )
        assert config.mode == EditMode.FLEXIBLE
        assert config.show_metrics is False
        assert config.validate_delay_ms == 500


# ================== Tests: MetricsStatusBar ==================


class TestMetricsStatusBar:
    """Tests para MetricsStatusBar widget."""
    
    def test_creation(self, qapp):
        """Crear MetricsStatusBar."""
        bar = MetricsStatusBar()
        assert bar is not None
        assert bar.minimumHeight() == 28
    
    def test_update_metrics_fits(self, qapp):
        """Actualizar métricas cuando cabe."""
        bar = MetricsStatusBar()
        bar.update_metrics(100.0, 95.0, FitStatus.FITS, "Helvetica 12pt")
        # Widget no debe lanzar excepción
        assert True
    
    def test_update_metrics_overflow(self, qapp):
        """Actualizar métricas cuando desborda."""
        bar = MetricsStatusBar()
        bar.update_metrics(100.0, 150.0, FitStatus.OVERFLOW, "Arial 14pt")
        assert True
    
    def test_update_metrics_unknown(self, qapp):
        """Actualizar métricas estado desconocido."""
        bar = MetricsStatusBar()
        bar.update_metrics(None, None, FitStatus.UNKNOWN)
        assert True
    
    def test_update_metrics_tight(self, qapp):
        """Actualizar métricas estado ajustado."""
        bar = MetricsStatusBar()
        bar.update_metrics(100.0, 102.0, FitStatus.TIGHT, "Times 10pt")
        assert True


# ================== Tests: SpanComparisonWidget ==================


class TestSpanComparisonWidget:
    """Tests para SpanComparisonWidget."""
    
    def test_creation(self, qapp):
        """Crear SpanComparisonWidget."""
        widget = SpanComparisonWidget()
        assert widget is not None
    
    def test_set_comparison(self, qapp):
        """Establecer comparación de textos."""
        widget = SpanComparisonWidget()
        widget.set_comparison("Texto original", "Texto editado")
        assert True
    
    def test_set_comparison_empty(self, qapp):
        """Comparación con texto vacío."""
        widget = SpanComparisonWidget()
        widget.set_comparison("", "Nuevo texto")
        assert True
    
    def test_set_comparison_both_empty(self, qapp):
        """Comparación con ambos vacíos."""
        widget = SpanComparisonWidget()
        widget.set_comparison("", "")
        assert True


# ================== Tests: EditorToolBar ==================


class TestEditorToolBar:
    """Tests para EditorToolBar."""
    
    def test_creation(self, qapp):
        """Crear EditorToolBar."""
        toolbar = EditorToolBar()
        assert toolbar is not None
        assert toolbar.isMovable() is False
    
    def test_mode_changed_signal(self, qapp):
        """Señal modeChanged se emite."""
        toolbar = EditorToolBar()
        signal_received = []
        
        toolbar.modeChanged.connect(lambda m: signal_received.append(m))
        toolbar._on_mode_selected(EditMode.FLEXIBLE)
        
        assert len(signal_received) == 1
        assert signal_received[0] == EditMode.FLEXIBLE
    
    def test_metrics_toggled_signal(self, qapp):
        """Señal metricsToggled se emite."""
        toolbar = EditorToolBar()
        signal_received = []
        
        toolbar.metricsToggled.connect(lambda v: signal_received.append(v))
        toolbar._metrics_action.trigger()
        
        assert len(signal_received) == 1


# ================== Tests: TextEditArea ==================


class TestTextEditArea:
    """Tests para TextEditArea."""
    
    def test_creation(self, qapp):
        """Crear TextEditArea."""
        area = TextEditArea()
        assert area is not None
        assert area.acceptRichText() is False
    
    def test_set_span_data(self, qapp, sample_span_data):
        """Establecer datos de span."""
        area = TextEditArea()
        area.set_span_data(sample_span_data)
        
        assert area.get_current_text() == sample_span_data['text']
        assert area.get_original_text() == sample_span_data['text']
    
    def test_has_changes_initially_false(self, qapp, sample_span_data):
        """has_changes es False inicialmente."""
        area = TextEditArea()
        area.set_span_data(sample_span_data)
        
        assert area.has_changes() is False
    
    def test_has_changes_after_edit(self, qapp, sample_span_data):
        """has_changes es True después de editar."""
        area = TextEditArea()
        area.set_span_data(sample_span_data)
        area.setPlainText("Nuevo texto diferente")
        
        assert area.has_changes() is True
    
    def test_text_modified_signal(self, qapp, sample_span_data):
        """Señal textModified se emite al editar."""
        area = TextEditArea()
        area.set_span_data(sample_span_data)
        
        signal_received = []
        area.textModified.connect(lambda t: signal_received.append(t))
        
        area.setPlainText("Texto nuevo")
        
        assert len(signal_received) >= 1
        assert "Texto nuevo" in signal_received
    
    def test_cursor_moved_signal(self, qapp, sample_span_data):
        """Señal cursorMoved se emite."""
        area = TextEditArea()
        area.set_span_data(sample_span_data)
        
        signal_received = []
        area.cursorMoved.connect(lambda p: signal_received.append(p))
        
        # Mover cursor
        cursor = area.textCursor()
        cursor.setPosition(5)
        area.setTextCursor(cursor)
        
        assert len(signal_received) >= 1
    
    def test_font_applied_bold(self, qapp, sample_span_bold):
        """Fuente bold se aplica correctamente."""
        area = TextEditArea()
        area.set_span_data(sample_span_bold)
        
        font = area.font()
        assert font.bold() is True


# ================== Tests: PDFTextEditorDialog ==================


class TestPDFTextEditorDialog:
    """Tests para PDFTextEditorDialog."""
    
    def test_creation(self, qapp, sample_span_data):
        """Crear PDFTextEditorDialog."""
        dialog = PDFTextEditorDialog(span_data=sample_span_data)
        assert dialog is not None
        assert dialog.windowTitle() == "Editor de Texto PDF"
    
    def test_minimum_size(self, qapp, sample_span_data):
        """Tamaño mínimo correcto."""
        dialog = PDFTextEditorDialog(span_data=sample_span_data)
        assert dialog.minimumWidth() == 800
        assert dialog.minimumHeight() == 600
    
    def test_with_custom_config(self, qapp, sample_span_data, config_flexible):
        """Crear con configuración personalizada."""
        dialog = PDFTextEditorDialog(
            span_data=sample_span_data,
            config=config_flexible
        )
        assert dialog._config.mode == EditMode.FLEXIBLE
    
    def test_get_edited_span_no_changes(self, qapp, sample_span_data):
        """get_edited_span retorna None sin cambios."""
        dialog = PDFTextEditorDialog(span_data=sample_span_data)
        assert dialog.get_edited_span() is None
    
    def test_get_edited_span_with_changes(self, qapp, sample_span_data):
        """get_edited_span retorna EditedSpan con cambios."""
        dialog = PDFTextEditorDialog(span_data=sample_span_data)
        dialog._edit_area.setPlainText("Texto modificado")
        
        edited = dialog.get_edited_span()
        assert edited is not None
        assert edited.new_text == "Texto modificado"
        assert edited.original_text == sample_span_data['text']
    
    def test_mode_changed_updates_config(self, qapp, sample_span_data):
        """Cambio de modo actualiza configuración."""
        dialog = PDFTextEditorDialog(span_data=sample_span_data)
        dialog._on_mode_changed(EditMode.NO_REFLOW)
        
        assert dialog._config.mode == EditMode.NO_REFLOW
    
    def test_metrics_toggled_hides_bar(self, qapp, sample_span_data):
        """Toggle métricas oculta/muestra barra."""
        dialog = PDFTextEditorDialog(span_data=sample_span_data)
        
        # Usar show() para que los widgets sean visibles
        dialog.show()
        qapp.processEvents()
        
        dialog._on_metrics_toggled(False)
        assert dialog._metrics_bar.isHidden() is True
        
        dialog._on_metrics_toggled(True)
        assert dialog._metrics_bar.isHidden() is False
        
        dialog.close()
    
    def test_validate_fit_overflow(self, qapp, sample_span_data):
        """Validación detecta overflow."""
        dialog = PDFTextEditorDialog(span_data=sample_span_data)
        
        # Poner texto muy largo
        dialog._edit_area.setPlainText(
            "Este es un texto extremadamente largo que definitivamente "
            "no va a caber en el espacio original asignado al span "
            "porque es muchísimo más largo que el texto original"
        )
        
        dialog._validate_fit()
        assert dialog._fit_status == FitStatus.OVERFLOW
    
    def test_validate_fit_unknown_no_bbox(self, qapp):
        """Validación retorna unknown sin bbox."""
        span_data = {
            'text': 'Texto sin bbox',
            'font_name': 'Helvetica',
            'font_size': 12.0,
        }
        dialog = PDFTextEditorDialog(span_data=span_data)
        
        dialog._validate_fit()
        assert dialog._fit_status == FitStatus.UNKNOWN


# ================== Tests: PDFTextEditor Widget ==================


class TestPDFTextEditor:
    """Tests para PDFTextEditor widget principal."""
    
    def test_creation(self, qapp):
        """Crear PDFTextEditor."""
        editor = PDFTextEditor()
        assert editor is not None
    
    def test_creation_with_config(self, qapp, config_no_reflow):
        """Crear con configuración personalizada."""
        editor = PDFTextEditor(config=config_no_reflow)
        assert editor._config.mode == EditMode.NO_REFLOW
    
    def test_set_selected_spans_empty(self, qapp):
        """Establecer selección vacía."""
        editor = PDFTextEditor()
        editor.set_selected_spans([])
        
        assert editor._selected_spans == []
        assert editor._edit_btn.isEnabled() is False
    
    def test_set_selected_spans_one(self, qapp, sample_span_data):
        """Establecer un span seleccionado."""
        editor = PDFTextEditor()
        editor.set_selected_spans([sample_span_data])
        
        assert len(editor._selected_spans) == 1
        assert editor._edit_btn.isEnabled() is True
    
    def test_set_selected_spans_multiple(self, qapp, sample_span_data, sample_span_bold):
        """Establecer múltiples spans seleccionados."""
        editor = PDFTextEditor()
        editor.set_selected_spans([sample_span_data, sample_span_bold])
        
        assert len(editor._selected_spans) == 2
        assert editor._edit_btn.isEnabled() is True
    
    def test_selection_changed_signal(self, qapp, sample_span_data):
        """Señal selectionChanged se emite."""
        editor = PDFTextEditor()
        signal_received = []
        
        editor.selectionChanged.connect(lambda s: signal_received.append(s))
        editor.set_selected_spans([sample_span_data])
        
        assert len(signal_received) == 1
        assert len(signal_received[0]) == 1
    
    def test_clear_selection(self, qapp, sample_span_data):
        """Limpiar selección."""
        editor = PDFTextEditor()
        editor.set_selected_spans([sample_span_data])
        
        editor.clear_selection()
        
        assert editor._selected_spans == []
        assert editor._edit_btn.isEnabled() is False
    
    def test_span_edit_requested_signal(self, qapp, sample_span_data):
        """Señal spanEditRequested se emite al solicitar edición."""
        editor = PDFTextEditor()
        editor.set_selected_spans([sample_span_data])
        
        signal_received = []
        editor.spanEditRequested.connect(lambda s: signal_received.append(s))
        
        # Mock del diálogo para no abrir
        with patch.object(editor, 'edit_span', return_value=None):
            editor._on_edit_clicked()
        
        assert len(signal_received) == 1
        assert signal_received[0] == sample_span_data


# ================== Tests: Factory Functions ==================


class TestFactoryFunctions:
    """Tests para funciones factory."""
    
    def test_create_pdf_text_editor_default(self, qapp):
        """Crear editor con defaults."""
        editor = create_pdf_text_editor()
        
        assert editor is not None
        assert editor._config.mode == EditMode.PRESERVE
        assert editor._config.show_property_panel is True
    
    def test_create_pdf_text_editor_no_property_panel(self, qapp):
        """Crear editor sin panel de propiedades."""
        editor = create_pdf_text_editor(with_property_panel=False)
        
        assert editor._config.show_property_panel is False
    
    def test_create_pdf_text_editor_flexible_mode(self, qapp):
        """Crear editor en modo flexible."""
        editor = create_pdf_text_editor(mode=EditMode.FLEXIBLE)
        
        assert editor._config.mode == EditMode.FLEXIBLE
    
    def test_show_pdf_text_editor_cancel(self, qapp, sample_span_data):
        """show_pdf_text_editor retorna None al cancelar."""
        # Mock del diálogo para simular cancelación
        with patch('ui.pdf_text_editor.PDFTextEditorDialog') as MockDialog:
            mock_instance = MockDialog.return_value
            mock_instance.exec_.return_value = 0  # QDialog.Rejected
            
            result = show_pdf_text_editor(sample_span_data)
            
            assert result is None


# ================== Tests: Integration ==================


class TestIntegration:
    """Tests de integración."""
    
    def test_full_edit_workflow(self, qapp, sample_span_data):
        """Workflow completo de edición."""
        # Crear editor
        editor = PDFTextEditor()
        
        # Seleccionar span
        editor.set_selected_spans([sample_span_data])
        assert editor._edit_btn.isEnabled() is True
        
        # Verificar que info se muestra
        assert "Texto de ejemplo" in editor._info_label.text()
    
    def test_dialog_creates_edited_span(self, qapp, sample_span_data):
        """Diálogo crea EditedSpan correctamente."""
        dialog = PDFTextEditorDialog(span_data=sample_span_data)
        
        # Simular edición
        dialog._edit_area.setPlainText("Texto completamente nuevo")
        
        # Obtener resultado
        edited = dialog.get_edited_span()
        
        assert edited is not None
        assert edited.new_text == "Texto completamente nuevo"
        assert edited.original_text == sample_span_data['text']
        assert edited.has_changes is True
    
    def test_property_inspector_integration(self, qapp, sample_span_data):
        """Integración con PropertyInspector."""
        if not HAS_PROPERTY_INSPECTOR:
            pytest.skip("PropertyInspector no disponible")
        
        dialog = PDFTextEditorDialog(span_data=sample_span_data)
        
        # Verificar que property inspector se creó
        assert dialog._property_inspector is not None


# ================== Tests: Edge Cases ==================


class TestEdgeCases:
    """Tests para casos límite."""
    
    def test_empty_text_span(self, qapp):
        """Span con texto vacío."""
        span_data = {
            'text': '',
            'font_name': 'Helvetica',
            'font_size': 12.0,
        }
        dialog = PDFTextEditorDialog(span_data=span_data)
        
        assert dialog._edit_area.get_original_text() == ''
    
    def test_very_long_text(self, qapp):
        """Span con texto muy largo."""
        span_data = {
            'text': 'A' * 10000,
            'font_name': 'Helvetica',
            'font_size': 12.0,
        }
        dialog = PDFTextEditorDialog(span_data=span_data)
        
        assert len(dialog._edit_area.get_original_text()) == 10000
    
    def test_special_characters(self, qapp):
        """Span con caracteres especiales."""
        span_data = {
            'text': '¡Hola! ¿Cómo estás? €100 ñ Ü',
            'font_name': 'Helvetica',
            'font_size': 12.0,
        }
        dialog = PDFTextEditorDialog(span_data=span_data)
        
        assert dialog._edit_area.get_original_text() == span_data['text']
    
    def test_multiline_text(self, qapp):
        """Span con texto multilínea."""
        span_data = {
            'text': 'Línea 1\nLínea 2\nLínea 3',
            'font_name': 'Helvetica',
            'font_size': 12.0,
        }
        dialog = PDFTextEditorDialog(span_data=span_data)
        
        assert '\n' in dialog._edit_area.get_original_text()
    
    def test_missing_font_properties(self, qapp):
        """Span sin propiedades de fuente."""
        span_data = {
            'text': 'Texto básico',
        }
        dialog = PDFTextEditorDialog(span_data=span_data)
        
        # No debe fallar
        assert dialog._edit_area.get_current_text() == 'Texto básico'
    
    def test_invalid_color_format(self, qapp):
        """Span con formato de color inválido."""
        span_data = {
            'text': 'Texto',
            'fill_color': 'not-a-color',
            'font_name': 'Helvetica',
            'font_size': 12.0,
        }
        # No debe fallar
        dialog = PDFTextEditorDialog(span_data=span_data)
        assert dialog is not None


# ================== Tests: Concurrent Operations ==================


class TestConcurrentOperations:
    """Tests para operaciones concurrentes."""
    
    def test_rapid_text_changes(self, qapp, sample_span_data):
        """Cambios rápidos de texto."""
        dialog = PDFTextEditorDialog(span_data=sample_span_data)
        
        # Simular cambios rápidos
        for i in range(10):
            dialog._edit_area.setPlainText(f"Texto versión {i}")
        
        # El último valor debe estar
        assert "versión 9" in dialog._edit_area.get_current_text()
    
    def test_multiple_dialogs(self, qapp, sample_span_data, sample_span_bold):
        """Múltiples diálogos simultáneos."""
        dialog1 = PDFTextEditorDialog(span_data=sample_span_data)
        dialog2 = PDFTextEditorDialog(span_data=sample_span_bold)
        
        # Ambos deben ser independientes
        dialog1._edit_area.setPlainText("Cambio 1")
        dialog2._edit_area.setPlainText("Cambio 2")
        
        assert dialog1._edit_area.get_current_text() == "Cambio 1"
        assert dialog2._edit_area.get_current_text() == "Cambio 2"


# ================== Tests: Validation Timer ==================


class TestValidationTimer:
    """Tests para el timer de validación."""
    
    def test_auto_validate_enabled(self, qapp, sample_span_data):
        """Timer de validación existe cuando auto_validate=True."""
        config = EditorConfig(auto_validate=True)
        dialog = PDFTextEditorDialog(span_data=sample_span_data, config=config)
        
        assert dialog._validation_timer is not None
    
    def test_auto_validate_disabled(self, qapp, sample_span_data):
        """Timer de validación no existe cuando auto_validate=False."""
        config = EditorConfig(auto_validate=False)
        dialog = PDFTextEditorDialog(span_data=sample_span_data, config=config)
        
        assert dialog._validation_timer is None


# ================== Tests: Module Level ==================


class TestModuleFlags:
    """Tests para flags del módulo."""
    
    def test_has_text_engine_flag_exists(self):
        """Flag HAS_TEXT_ENGINE existe."""
        assert isinstance(HAS_TEXT_ENGINE, bool)
    
    def test_has_font_manager_flag_exists(self):
        """Flag HAS_FONT_MANAGER existe."""
        assert isinstance(HAS_FONT_MANAGER, bool)
    
    def test_has_property_inspector_flag_exists(self):
        """Flag HAS_PROPERTY_INSPECTOR existe."""
        assert isinstance(HAS_PROPERTY_INSPECTOR, bool)
    
    def test_has_selection_overlay_flag_exists(self):
        """Flag HAS_SELECTION_OVERLAY existe."""
        assert isinstance(HAS_SELECTION_OVERLAY, bool)

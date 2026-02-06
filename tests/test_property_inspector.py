"""
Tests para PropertyInspector - Panel de propiedades tipográficas

PHASE3-3C01: Tests del widget PropertyInspector

Cubre:
1. Creación y configuración inicial
2. Actualización desde diferentes fuentes de datos
3. Secciones colapsables
4. Formateo de propiedades
5. Limpieza y estados
"""

import pytest

from PyQt5.QtWidgets import QApplication

from ui.property_inspector import (
    PropertyInspector,
    CollapsibleSection,
    ColorSwatch,
    Property,
    PropertyType,
    create_property_inspector_dock,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def app():
    """Crea QApplication para tests."""
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    yield application


@pytest.fixture
def inspector(app):
    """Crea instancia fresca de PropertyInspector."""
    widget = PropertyInspector()
    yield widget
    widget.close()
    widget.deleteLater()


@pytest.fixture
def sample_span_data():
    """Datos de prueba simulando un TextSpanMetrics."""
    return {
        'text': "Hello, World!",
        'page_num': 0,
        'span_id': "span_001",
        'font_name': "Arial",
        'font_name_pdf': "ABCDEF+Arial-BoldMT",
        'font_size': 12.0,
        'is_bold': True,
        'is_italic': False,
        'is_embedded': True,
        'is_subset': True,
        'fill_color': "#0066cc",
        'stroke_color': None,
        'render_mode': 0,
        'char_spacing': 0.5,
        'word_spacing': 2.0,
        'leading': 14.4,
        'bbox': (72.0, 720.0, 200.0, 732.0),
        'origin': (72.0, 720.0),
        'baseline_y': 720.0,
        'ctm': (1.0, 0.0, 0.0, 1.0, 0.0, 0.0),
        'text_matrix': (1.0, 0.0, 0.0, 1.0, 72.0, 720.0),
        'horizontal_scale': 100.0,
        'rotation': 0.0,
        'rise': 0.0,
        'was_fallback': False,
        'confidence': 0.95,
        'font_flags': 0x20,
    }


@pytest.fixture
def sample_line_data():
    """Datos de prueba simulando propiedades de línea."""
    return {
        'text': "This is a full line of text",
        'bbox': (72.0, 700.0, 500.0, 720.0),
        'baseline_y': 710.0,
        'line_height': 20.0,
        'font_name': "Helvetica",
        'font_size': 11.0,
        'alignment': "left",
        'num_spans': 3,
    }


# =============================================================================
# Tests: Property Dataclass
# =============================================================================

class TestProperty:
    """Tests para la clase Property."""
    
    def test_property_creation(self):
        """Crear Property con valores básicos."""
        prop = Property("Test", "Value")
        assert prop.name == "Test"
        assert prop.value == "Value"
        assert prop.unit == ""
        assert prop.category == PropertyType.METADATA
    
    def test_property_with_unit(self):
        """Property con unidad."""
        prop = Property("Size", 12.0, "pt")
        assert prop.unit == "pt"
    
    def test_property_formatted_value_none(self):
        """Formateo de valor None."""
        prop = Property("Empty", None)
        assert prop.formatted_value() == "—"
    
    def test_property_formatted_value_bool_true(self):
        """Formateo de valor booleano True."""
        prop = Property("Bold", True)
        assert prop.formatted_value() == "Sí"
    
    def test_property_formatted_value_bool_false(self):
        """Formateo de valor booleano False."""
        prop = Property("Italic", False)
        assert prop.formatted_value() == "No"
    
    def test_property_formatted_value_small_float(self):
        """Formateo de float pequeño."""
        prop = Property("Value", 0.0005)
        formatted = prop.formatted_value()
        assert "0.000500" in formatted
    
    def test_property_formatted_value_medium_float(self):
        """Formateo de float medio."""
        prop = Property("Value", 12.345)
        formatted = prop.formatted_value()
        assert "12.35" in formatted or "12.34" in formatted
    
    def test_property_formatted_value_large_float(self):
        """Formateo de float grande."""
        prop = Property("Value", 1234.5)
        formatted = prop.formatted_value()
        assert "1234.5" in formatted
    
    def test_property_formatted_value_bbox(self):
        """Formateo de bbox (4 valores)."""
        prop = Property("BBox", (72.0, 720.0, 200.0, 732.0))
        formatted = prop.formatted_value()
        assert "72.0" in formatted
        assert "720.0" in formatted
    
    def test_property_formatted_value_point(self):
        """Formateo de punto (2 valores)."""
        prop = Property("Origin", (100.5, 200.5))
        formatted = prop.formatted_value()
        assert "100.5" in formatted
        assert "200.5" in formatted
    
    def test_property_formatted_value_matrix(self):
        """Formateo de matriz (6 valores)."""
        prop = Property("Matrix", (1.0, 0.0, 0.0, 1.0, 72.0, 720.0))
        formatted = prop.formatted_value()
        assert "1.000" in formatted
        assert "72.000" in formatted


# =============================================================================
# Tests: CollapsibleSection
# =============================================================================

class TestCollapsibleSection:
    """Tests para CollapsibleSection."""
    
    def test_section_creation(self, app):
        """Crear sección colapsable."""
        section = CollapsibleSection("Test Section")
        assert section._title == "Test Section"
        assert not section._collapsed
    
    def test_section_collapsed_initial(self, app):
        """Crear sección colapsada inicialmente."""
        section = CollapsibleSection("Test", collapsed=True)
        assert section._collapsed
    
    def test_section_toggle(self, app):
        """Toggle de sección."""
        section = CollapsibleSection("Test")
        initial_state = section._collapsed
        section._toggle()
        assert section._collapsed != initial_state
    
    def test_section_add_property(self, app):
        """Añadir propiedad a sección."""
        section = CollapsibleSection("Test")
        prop = Property("Name", "Value")
        label = section.add_property(prop, 0)
        
        assert label is not None
        assert "Value" in label.text()
    
    def test_section_add_property_with_unit(self, app):
        """Añadir propiedad con unidad."""
        section = CollapsibleSection("Test")
        prop = Property("Size", 12.0, "pt")
        label = section.add_property(prop, 0)
        
        assert "pt" in label.text()
    
    def test_section_clear_properties(self, app):
        """Limpiar propiedades de sección."""
        section = CollapsibleSection("Test")
        prop = Property("Name", "Value")
        section.add_property(prop, 0)
        
        section.clear_properties()
        
        assert section._content_layout.count() == 0
    
    def test_section_set_collapsed(self, app):
        """Establecer estado de colapso."""
        section = CollapsibleSection("Test", collapsed=False)
        section.set_collapsed(True)
        assert section._collapsed


# =============================================================================
# Tests: ColorSwatch
# =============================================================================

class TestColorSwatch:
    """Tests para ColorSwatch."""
    
    def test_color_swatch_creation(self, app):
        """Crear swatch de color."""
        swatch = ColorSwatch("#ff0000")
        assert swatch._color == "#ff0000"
    
    def test_color_swatch_default_color(self, app):
        """Swatch con color por defecto."""
        swatch = ColorSwatch()
        assert swatch._color == "#000000"
    
    def test_color_swatch_set_color(self, app):
        """Cambiar color del swatch."""
        swatch = ColorSwatch("#000000")
        swatch.set_color("#00ff00")
        assert swatch._color == "#00ff00"


# =============================================================================
# Tests: PropertyInspector Creation
# =============================================================================

class TestPropertyInspectorCreation:
    """Tests de creación del PropertyInspector."""
    
    def test_inspector_creation(self, inspector):
        """Crear PropertyInspector."""
        assert inspector is not None
    
    def test_inspector_initial_state(self, inspector):
        """Estado inicial sin selección."""
        assert inspector._current_data is None
        # El label no está oculto (hidden=False significa que se mostraría si el padre es visible)
        assert not inspector._no_selection_label.isHidden()
    
    def test_inspector_has_sections(self, inspector):
        """Inspector tiene todas las secciones."""
        expected_sections = ["text", "font", "color", "spacing", 
                           "geometry", "transform", "metadata"]
        for section_name in expected_sections:
            assert section_name in inspector._sections
    
    def test_inspector_minimum_width(self, inspector):
        """Inspector tiene ancho mínimo."""
        assert inspector.minimumWidth() >= 250
    
    def test_inspector_size_hint(self, inspector):
        """Size hint del inspector."""
        size = inspector.sizeHint()
        assert size.width() > 0
        assert size.height() > 0


# =============================================================================
# Tests: PropertyInspector Update from Span
# =============================================================================

class TestPropertyInspectorUpdateFromSpan:
    """Tests de actualización desde span."""
    
    def test_update_from_span_dict(self, inspector, sample_span_data):
        """Actualizar desde diccionario."""
        inspector.update_from_span(sample_span_data)
        
        assert inspector._current_data is not None
        assert inspector._current_data['text'] == "Hello, World!"
    
    def test_update_from_span_hides_no_selection(self, inspector, sample_span_data):
        """Actualizar oculta mensaje de sin selección."""
        inspector.update_from_span(sample_span_data)
        
        assert inspector._no_selection_label.isHidden()
    
    def test_update_from_span_shows_sections(self, inspector, sample_span_data):
        """Actualizar muestra las secciones."""
        inspector.update_from_span(sample_span_data)
        
        for section in inspector._sections.values():
            assert not section.isHidden()
    
    def test_update_from_span_none_clears(self, inspector, sample_span_data):
        """Actualizar con None limpia."""
        inspector.update_from_span(sample_span_data)
        inspector.update_from_span(None)
        
        assert inspector._current_data is None
        assert not inspector._no_selection_label.isHidden()
    
    def test_update_from_span_creates_value_labels(self, inspector, sample_span_data):
        """Actualizar crea labels de valores."""
        inspector.update_from_span(sample_span_data)
        
        assert len(inspector._value_labels) > 0
        assert 'font_name' in inspector._value_labels
        assert 'font_size' in inspector._value_labels
    
    def test_update_from_span_text_truncation(self, inspector):
        """Texto largo se trunca."""
        data = {'text': "A" * 100}
        inspector.update_from_span(data)
        
        # El label debe tener texto truncado
        if 'text' in inspector._value_labels:
            label_text = inspector._value_labels['text'].text()
            assert "..." in label_text or len(label_text) <= 55


# =============================================================================
# Tests: PropertyInspector Update from Line
# =============================================================================

class TestPropertyInspectorUpdateFromLine:
    """Tests de actualización desde línea."""
    
    def test_update_from_line_dict(self, inspector, sample_line_data):
        """Actualizar desde diccionario de línea."""
        # Simular objeto línea con atributos
        class MockLine:
            def __init__(self, d):
                for k, v in d.items():
                    setattr(self, k, v)
            def get_full_text(self):
                return self.text
            def get_dominant_font(self):
                return (self.font_name, self.font_size)
        
        line = MockLine(sample_line_data)
        line.spans = [1, 2, 3]  # Mock spans
        
        inspector.update_from_line(line)
        
        assert inspector._current_data is not None
    
    def test_update_from_line_none_clears(self, inspector):
        """Actualizar línea con None limpia."""
        inspector.update_from_line(None)
        
        assert inspector._current_data is None


# =============================================================================
# Tests: PropertyInspector Update from FontDescriptor
# =============================================================================

class TestPropertyInspectorUpdateFromFontDescriptor:
    """Tests de actualización desde FontDescriptor."""
    
    def test_update_from_font_descriptor(self, inspector):
        """Actualizar desde FontDescriptor mock."""
        class MockDescriptor:
            name = "Arial"
            size = 12.0
            color = "#000000"
            flags = 0x20
            possible_bold = True
            was_fallback = False
            fallback_from = None
        
        descriptor = MockDescriptor()
        inspector.update_from_font_descriptor(descriptor)
        
        assert inspector._current_data is not None
        assert inspector._current_data['font_name'] == "Arial"
        assert inspector._current_data['font_size'] == 12.0
    
    def test_update_from_font_descriptor_with_phase3b_fields(self, inspector):
        """Actualizar con campos de Fase 3B."""
        class MockEmbeddingStatus:
            value = "subset"
        
        class MockPreciseMetrics:
            ascender = 800
            descender = -200
            stem_v = 120
            italic_angle = 0
        
        class MockDescriptor:
            name = "Arial"
            size = 12.0
            color = "#000000"
            flags = 0x20
            possible_bold = True
            was_fallback = False
            fallback_from = None
            embedding_status = MockEmbeddingStatus()
            precise_metrics = MockPreciseMetrics()
            char_spacing = 0.5
            word_spacing = 2.0
            is_subset = True
        
        descriptor = MockDescriptor()
        inspector.update_from_font_descriptor(descriptor)
        
        assert inspector._current_data['embedding_status'] == "subset"
        assert inspector._current_data['ascender'] == 800
        assert inspector._current_data['stem_v'] == 120
    
    def test_update_from_font_descriptor_none_clears(self, inspector):
        """Actualizar descriptor con None limpia."""
        inspector.update_from_font_descriptor(None)
        
        assert inspector._current_data is None


# =============================================================================
# Tests: PropertyInspector Clear
# =============================================================================

class TestPropertyInspectorClear:
    """Tests de limpieza del inspector."""
    
    def test_clear_resets_data(self, inspector, sample_span_data):
        """Clear resetea datos."""
        inspector.update_from_span(sample_span_data)
        inspector.clear()
        
        assert inspector._current_data is None
    
    def test_clear_shows_no_selection_message(self, inspector, sample_span_data):
        """Clear muestra mensaje de sin selección."""
        inspector.update_from_span(sample_span_data)
        inspector.clear()
        
        # Verificar que el label no está oculto (se mostraría si el padre es visible)
        assert not inspector._no_selection_label.isHidden()
    
    def test_clear_hides_sections(self, inspector, sample_span_data):
        """Clear oculta secciones."""
        inspector.update_from_span(sample_span_data)
        inspector.clear()
        
        for section in inspector._sections.values():
            assert not section.isVisible()
    
    def test_clear_emits_signal(self, inspector, sample_span_data):
        """Clear emite señal selection_cleared."""
        signal_received = []
        inspector.selection_cleared.connect(lambda: signal_received.append(True))
        
        inspector.update_from_span(sample_span_data)
        inspector.clear()
        
        assert len(signal_received) == 1


# =============================================================================
# Tests: PropertyInspector Update Property
# =============================================================================

class TestPropertyInspectorUpdateProperty:
    """Tests de actualización de propiedades individuales."""
    
    def test_update_property_value(self, inspector, sample_span_data):
        """Actualizar valor de propiedad."""
        inspector.update_from_span(sample_span_data)
        inspector.update_property('font_size', 14.0)
        
        assert inspector._current_data['font_size'] == 14.0
    
    def test_update_property_updates_label(self, inspector, sample_span_data):
        """Actualizar propiedad actualiza label."""
        inspector.update_from_span(sample_span_data)
        inspector.update_property('font_size', 14.0)
        
        if 'font_size' in inspector._value_labels:
            label_text = inspector._value_labels['font_size'].text()
            assert "14" in label_text
    
    def test_update_property_bool(self, inspector, sample_span_data):
        """Actualizar propiedad booleana."""
        inspector.update_from_span(sample_span_data)
        inspector.update_property('is_bold', False)
        
        if 'is_bold' in inspector._value_labels:
            label_text = inspector._value_labels['is_bold'].text()
            assert "No" in label_text


# =============================================================================
# Tests: PropertyInspector Get Current Data
# =============================================================================

class TestPropertyInspectorGetCurrentData:
    """Tests de obtención de datos actuales."""
    
    def test_get_current_data_none_when_empty(self, inspector):
        """get_current_data retorna None si vacío."""
        assert inspector.get_current_data() is None
    
    def test_get_current_data_returns_data(self, inspector, sample_span_data):
        """get_current_data retorna los datos."""
        inspector.update_from_span(sample_span_data)
        data = inspector.get_current_data()
        
        assert data is not None
        assert data['text'] == "Hello, World!"


# =============================================================================
# Tests: Factory Function
# =============================================================================

class TestCreatePropertyInspectorDock:
    """Tests de función factory."""
    
    def test_create_property_inspector_dock(self, app):
        """Crear inspector con factory."""
        inspector = create_property_inspector_dock()
        
        assert isinstance(inspector, PropertyInspector)
        
        inspector.close()
        inspector.deleteLater()


# =============================================================================
# Tests: PropertyType Enum
# =============================================================================

class TestPropertyType:
    """Tests para PropertyType enum."""
    
    def test_property_type_values(self):
        """Verificar valores del enum."""
        assert PropertyType.FONT.value == "font"
        assert PropertyType.COLOR.value == "color"
        assert PropertyType.SPACING.value == "spacing"
        assert PropertyType.GEOMETRY.value == "geometry"
        assert PropertyType.TRANSFORM.value == "transform"
        assert PropertyType.METADATA.value == "metadata"


# =============================================================================
# Tests: Edge Cases
# =============================================================================

class TestPropertyInspectorEdgeCases:
    """Tests de casos edge."""
    
    def test_update_from_span_empty_dict(self, inspector):
        """Actualizar con diccionario vacío."""
        inspector.update_from_span({})
        
        assert inspector._current_data is not None
        # No debe fallar, solo mostrar secciones vacías
    
    def test_update_from_span_partial_data(self, inspector):
        """Actualizar con datos parciales."""
        partial_data = {
            'text': "Partial",
            'font_name': "Arial",
        }
        inspector.update_from_span(partial_data)
        
        assert inspector._current_data['text'] == "Partial"
    
    def test_update_from_span_invalid_type(self, inspector):
        """Actualizar con tipo inválido no falla."""
        inspector.update_from_span(12345)  # Tipo inválido
        
        # Debe limpiar o manejar gracefully
        assert inspector._current_data is None or inspector._current_data == {}
    
    def test_consecutive_updates(self, inspector, sample_span_data, sample_line_data):
        """Actualizaciones consecutivas funcionan."""
        inspector.update_from_span(sample_span_data)
        assert inspector._current_data['text'] == "Hello, World!"
        
        inspector.update_from_span(sample_line_data)
        assert inspector._current_data['text'] == "This is a full line of text"
    
    def test_update_preserves_section_collapse_state(self, inspector, sample_span_data):
        """Actualizar preserva estado de colapso."""
        inspector.update_from_span(sample_span_data)
        
        # Colapsar una sección
        inspector._sections["spacing"].set_collapsed(True)
        
        # Actualizar de nuevo
        inspector.update_from_span(sample_span_data)
        
        # La sección debe seguir colapsada (no se resetea)
        # Nota: Con la implementación actual, las secciones se muestran pero 
        # el estado de colapso se preserva
        assert inspector._sections["spacing"]._collapsed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

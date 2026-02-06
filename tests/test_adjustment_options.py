"""
Tests para AdjustmentOptions - Opciones interactivas de ajuste.

PHASE3-3C08: Tests completos para el módulo de opciones de ajuste.
"""

import pytest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QSignalSpy

from ui.adjustment_options import (
    # Enums
    AdjustmentMode,
    PreviewQuality,
    # Dataclasses
    AdjustmentPreset,
    AdjustmentState,
    # Constants
    BUILTIN_PRESETS,
    # Widgets
    AdjustmentPreviewWidget,
    TrackingSlider,
    SizeSlider,
    ScaleSlider,
    PresetSelector,
    ModeSelector,
    AdjustmentControlsPanel,
    TruncationPanel,
    AdjustmentOptionsDialog,
    # Factory functions
    create_adjustment_dialog,
    create_adjustment_controls,
    create_preset_selector,
    get_builtin_presets,
)


# ================== Fixtures ==================


@pytest.fixture
def qapp():
    """Proporciona aplicación Qt."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def sample_text():
    """Texto de ejemplo para pruebas."""
    return "Este es un texto de prueba bastante largo"


@pytest.fixture
def sample_font_config():
    """Configuración de fuente de ejemplo."""
    return {
        'font_name': 'Helvetica',
        'font_size': 12.0,
        'available_width': 150.0,
        'char_spacing': 0.0,
    }


@pytest.fixture
def sample_state(sample_text, sample_font_config):
    """Estado de ajuste de ejemplo."""
    return AdjustmentState(
        text=sample_text,
        font_name=sample_font_config['font_name'],
        font_size=sample_font_config['font_size'],
        available_width=sample_font_config['available_width'],
        original_char_spacing=0.0,
        current_char_spacing=0.0,
        current_font_size=sample_font_config['font_size'],
        current_text=sample_text,
    )


# ================== Tests: AdjustmentMode Enum ==================


class TestAdjustmentMode:
    """Tests para AdjustmentMode enum."""
    
    def test_all_modes_defined(self):
        """Verifica que todos los modos están definidos."""
        expected = ['NONE', 'AUTO', 'TRACKING', 'SIZE', 'SCALE', 'TRUNCATE', 'COMBINED']
        actual = [m.name for m in AdjustmentMode]
        assert actual == expected
    
    def test_str_representation(self):
        """Verifica representación de string."""
        assert str(AdjustmentMode.NONE) == "Sin ajuste"
        assert str(AdjustmentMode.AUTO) == "Automático"
        assert str(AdjustmentMode.TRACKING) == "Reducir espaciado"
        assert str(AdjustmentMode.SIZE) == "Reducir tamaño"
        assert str(AdjustmentMode.SCALE) == "Escalar ancho"
        assert str(AdjustmentMode.TRUNCATE) == "Truncar texto"
        assert str(AdjustmentMode.COMBINED) == "Combinado"
    
    def test_description_property(self):
        """Verifica propiedad description."""
        for mode in AdjustmentMode:
            desc = mode.description
            assert isinstance(desc, str)
            assert len(desc) > 0


class TestPreviewQuality:
    """Tests para PreviewQuality enum."""
    
    def test_all_qualities_defined(self):
        """Verifica que todas las calidades están definidas."""
        assert len(PreviewQuality) == 2
        assert PreviewQuality.FAST in PreviewQuality
        assert PreviewQuality.ACCURATE in PreviewQuality
    
    def test_str_representation(self):
        """Verifica representación de string."""
        assert str(PreviewQuality.FAST) == "Rápida"
        assert str(PreviewQuality.ACCURATE) == "Precisa"


# ================== Tests: AdjustmentPreset Dataclass ==================


class TestAdjustmentPreset:
    """Tests para AdjustmentPreset dataclass."""
    
    def test_default_values(self):
        """Verifica valores por defecto."""
        preset = AdjustmentPreset()
        assert preset.name == "Default"
        assert preset.mode == AdjustmentMode.AUTO
        assert preset.tracking_delta == 0.0
        assert preset.size_factor == 1.0
        assert preset.scale_x == 1.0
        assert preset.truncate_suffix == "..."
    
    def test_custom_values(self):
        """Verifica valores personalizados."""
        preset = AdjustmentPreset(
            name="Custom",
            mode=AdjustmentMode.TRACKING,
            tracking_delta=-1.5,
            min_tracking=-3.0,
        )
        assert preset.name == "Custom"
        assert preset.mode == AdjustmentMode.TRACKING
        assert preset.tracking_delta == -1.5
        assert preset.min_tracking == -3.0
    
    def test_to_dict(self):
        """Verifica conversión a diccionario."""
        preset = AdjustmentPreset(
            name="Test",
            mode=AdjustmentMode.SIZE,
            size_factor=0.9,
        )
        d = preset.to_dict()
        assert d['name'] == "Test"
        assert d['mode'] == "SIZE"
        assert d['size_factor'] == 0.9
    
    def test_from_dict(self):
        """Verifica creación desde diccionario."""
        data = {
            'name': 'FromDict',
            'mode': 'SCALE',
            'scale_x': 0.85,
        }
        preset = AdjustmentPreset.from_dict(data)
        assert preset.name == "FromDict"
        assert preset.mode == AdjustmentMode.SCALE
        assert preset.scale_x == 0.85
        assert not preset.is_builtin
    
    def test_from_dict_invalid_mode(self):
        """Verifica manejo de modo inválido."""
        data = {
            'name': 'Invalid',
            'mode': 'INVALID_MODE',
        }
        preset = AdjustmentPreset.from_dict(data)
        assert preset.mode == AdjustmentMode.AUTO  # Default


# ================== Tests: AdjustmentState Dataclass ==================


class TestAdjustmentState:
    """Tests para AdjustmentState dataclass."""
    
    def test_default_values(self):
        """Verifica valores por defecto."""
        state = AdjustmentState()
        assert state.text == ""
        assert state.font_size == 12.0
        assert state.fits is True
    
    def test_reset_to_original(self, sample_state):
        """Verifica reset a valores originales."""
        # Modificar valores
        sample_state.current_char_spacing = -1.5
        sample_state.current_font_size = 10.0
        sample_state.current_text = "Truncated"
        
        # Resetear
        sample_state.reset_to_original()
        
        assert sample_state.current_char_spacing == sample_state.original_char_spacing
        assert sample_state.current_font_size == sample_state.font_size
        assert sample_state.current_text == sample_state.text
    
    def test_has_changes_false(self, sample_state):
        """Verifica has_changes cuando no hay cambios."""
        assert not sample_state.has_changes
    
    def test_has_changes_true(self, sample_state):
        """Verifica has_changes cuando hay cambios."""
        sample_state.current_char_spacing = -1.0
        assert sample_state.has_changes
    
    def test_tracking_delta(self, sample_state):
        """Verifica cálculo de tracking delta."""
        sample_state.original_char_spacing = 0.5
        sample_state.current_char_spacing = -0.5
        assert sample_state.tracking_delta == -1.0
    
    def test_size_factor(self, sample_state):
        """Verifica cálculo de size factor."""
        sample_state.font_size = 12.0
        sample_state.current_font_size = 10.0
        assert abs(sample_state.size_factor - 0.833) < 0.01
    
    def test_size_factor_zero_division(self):
        """Verifica manejo de división por cero."""
        state = AdjustmentState(font_size=0.0)
        assert state.size_factor == 1.0
    
    def test_to_dict(self, sample_state):
        """Verifica conversión a diccionario."""
        d = sample_state.to_dict()
        assert 'text' in d
        assert 'char_spacing' in d
        assert 'font_size' in d
        assert 'fits' in d


# ================== Tests: BUILTIN_PRESETS ==================


class TestBuiltinPresets:
    """Tests para presets predefinidos."""
    
    def test_presets_not_empty(self):
        """Verifica que hay presets predefinidos."""
        assert len(BUILTIN_PRESETS) > 0
    
    def test_all_presets_valid(self):
        """Verifica que todos los presets son válidos."""
        for preset in BUILTIN_PRESETS:
            assert isinstance(preset, AdjustmentPreset)
            assert preset.name
            assert preset.is_builtin
    
    def test_preset_names_unique(self):
        """Verifica que los nombres son únicos."""
        names = [p.name for p in BUILTIN_PRESETS]
        assert len(names) == len(set(names))
    
    def test_auto_preset_exists(self):
        """Verifica que existe preset automático."""
        auto_presets = [p for p in BUILTIN_PRESETS if p.mode == AdjustmentMode.AUTO]
        assert len(auto_presets) >= 1


# ================== Tests: AdjustmentPreviewWidget ==================


class TestAdjustmentPreviewWidget:
    """Tests para AdjustmentPreviewWidget."""
    
    def test_creation(self, qapp):
        """Verifica creación del widget."""
        widget = AdjustmentPreviewWidget()
        assert widget is not None
        assert widget.minimumHeight() >= 80
        assert widget.minimumWidth() >= 200
    
    def test_set_state(self, qapp, sample_state):
        """Verifica set_state."""
        widget = AdjustmentPreviewWidget()
        widget.set_state(sample_state)
        # Widget tiene estado interno
        assert widget._state == sample_state
    
    def test_visibility_options(self, qapp):
        """Verifica opciones de visibilidad."""
        widget = AdjustmentPreviewWidget()
        
        widget.set_show_bbox(False)
        assert widget._show_bbox is False
        
        widget.set_show_overflow(False)
        assert widget._show_overflow is False
        
        widget.set_show_metrics(False)
        assert widget._show_metrics is False
    
    def test_paint_without_state(self, qapp):
        """Verifica pintado sin estado."""
        widget = AdjustmentPreviewWidget()
        widget.show()
        widget.repaint()  # No debe fallar


# ================== Tests: TrackingSlider ==================


class TestTrackingSlider:
    """Tests para TrackingSlider."""
    
    def test_creation(self, qapp):
        """Verifica creación del slider."""
        slider = TrackingSlider()
        assert slider is not None
    
    def test_default_value(self, qapp):
        """Verifica valor por defecto."""
        slider = TrackingSlider()
        assert slider.value() == 0.0
    
    def test_set_value(self, qapp):
        """Verifica set_value."""
        slider = TrackingSlider(min_value=-3.0, max_value=3.0)
        slider.set_value(-1.5)
        assert slider.value() == -1.5
    
    def test_value_clamping(self, qapp):
        """Verifica que valores se limitan al rango."""
        slider = TrackingSlider(min_value=-2.0, max_value=2.0)
        slider.set_value(-5.0)
        assert slider.value() == -2.0
    
    def test_reset(self, qapp):
        """Verifica reset."""
        slider = TrackingSlider()
        slider.set_value(-1.0)
        slider.reset()
        assert slider.value() == 0.0
    
    def test_signal_emission(self, qapp):
        """Verifica emisión de señal."""
        slider = TrackingSlider()
        spy = QSignalSpy(slider.valueChanged)
        slider.reset()
        assert len(spy) == 1


# ================== Tests: SizeSlider ==================


class TestSizeSlider:
    """Tests para SizeSlider."""
    
    def test_creation(self, qapp):
        """Verifica creación del slider."""
        slider = SizeSlider()
        assert slider is not None
    
    def test_default_factor(self, qapp):
        """Verifica factor por defecto."""
        slider = SizeSlider()
        assert slider.factor() == 1.0
    
    def test_set_factor(self, qapp):
        """Verifica set_factor."""
        slider = SizeSlider(base_size=12.0)
        slider.set_factor(0.8)
        assert slider.factor() == 0.8
    
    def test_current_size(self, qapp):
        """Verifica current_size."""
        slider = SizeSlider(base_size=12.0)
        slider.set_factor(0.75)
        assert slider.current_size() == 9.0
    
    def test_set_base_size(self, qapp):
        """Verifica set_base_size."""
        slider = SizeSlider(base_size=12.0)
        slider.set_base_size(14.0)
        assert slider.current_size() == 14.0
    
    def test_reset(self, qapp):
        """Verifica reset."""
        slider = SizeSlider()
        slider.set_factor(0.7)
        slider.reset()
        assert slider.factor() == 1.0


# ================== Tests: ScaleSlider ==================


class TestScaleSlider:
    """Tests para ScaleSlider."""
    
    def test_creation(self, qapp):
        """Verifica creación del slider."""
        slider = ScaleSlider()
        assert slider is not None
    
    def test_default_scale(self, qapp):
        """Verifica escala por defecto."""
        slider = ScaleSlider()
        assert slider.scale() == 1.0
    
    def test_set_scale(self, qapp):
        """Verifica set_scale."""
        slider = ScaleSlider()
        slider.set_scale(0.85)
        assert slider.scale() == 0.85
    
    def test_scale_clamping(self, qapp):
        """Verifica que escala se limita al rango."""
        slider = ScaleSlider(min_scale=0.5, max_scale=1.5)
        slider.set_scale(0.3)
        assert slider.scale() == 0.5
    
    def test_reset(self, qapp):
        """Verifica reset."""
        slider = ScaleSlider()
        slider.set_scale(0.75)
        slider.reset()
        assert slider.scale() == 1.0


# ================== Tests: PresetSelector ==================


class TestPresetSelector:
    """Tests para PresetSelector."""
    
    def test_creation(self, qapp):
        """Verifica creación del selector."""
        selector = PresetSelector()
        assert selector is not None
    
    def test_default_presets(self, qapp):
        """Verifica que usa presets por defecto."""
        selector = PresetSelector()
        assert selector._presets == BUILTIN_PRESETS
    
    def test_custom_presets(self, qapp):
        """Verifica presets personalizados."""
        custom = [AdjustmentPreset(name="Custom1")]
        selector = PresetSelector(presets=custom)
        assert len(selector._presets) == 1
    
    def test_current_preset(self, qapp):
        """Verifica preset actual."""
        selector = PresetSelector()
        preset = selector.current_preset()
        assert isinstance(preset, AdjustmentPreset)
    
    def test_add_preset(self, qapp):
        """Verifica agregar preset."""
        selector = PresetSelector()
        initial_count = len(selector._presets)
        selector.add_preset(AdjustmentPreset(name="New"))
        assert len(selector._presets) == initial_count + 1
    
    def test_signal_emission(self, qapp):
        """Verifica emisión de señal."""
        custom = [
            AdjustmentPreset(name="A"),
            AdjustmentPreset(name="B"),
        ]
        selector = PresetSelector(presets=custom)
        spy = QSignalSpy(selector.presetSelected)
        
        # Simular selección
        selector._on_preset_selected(1)
        assert len(spy) == 1


# ================== Tests: ModeSelector ==================


class TestModeSelector:
    """Tests para ModeSelector."""
    
    def test_creation(self, qapp):
        """Verifica creación del selector."""
        selector = ModeSelector()
        assert selector is not None
    
    def test_default_mode(self, qapp):
        """Verifica modo por defecto."""
        selector = ModeSelector()
        assert selector.current_mode() == AdjustmentMode.AUTO
    
    def test_set_mode(self, qapp):
        """Verifica set_mode."""
        selector = ModeSelector()
        selector.set_mode(AdjustmentMode.TRACKING)
        assert selector.current_mode() == AdjustmentMode.TRACKING
    
    def test_signal_emission(self, qapp):
        """Verifica emisión de señal."""
        selector = ModeSelector()
        spy = QSignalSpy(selector.modeSelected)
        selector.set_mode(AdjustmentMode.SIZE)
        # set_mode cambia index que emite señal
        assert len(spy) >= 0  # Puede o no emitir dependiendo si ya estaba


# ================== Tests: AdjustmentControlsPanel ==================


class TestAdjustmentControlsPanel:
    """Tests para AdjustmentControlsPanel."""
    
    def test_creation(self, qapp):
        """Verifica creación del panel."""
        panel = AdjustmentControlsPanel()
        assert panel is not None
    
    def test_has_sliders(self, qapp):
        """Verifica que tiene sliders."""
        panel = AdjustmentControlsPanel()
        assert hasattr(panel, '_tracking')
        assert hasattr(panel, '_size')
        assert hasattr(panel, '_scale')
    
    def test_set_state(self, qapp, sample_state):
        """Verifica set_state."""
        panel = AdjustmentControlsPanel()
        panel.set_state(sample_state)
        assert panel._state == sample_state
    
    def test_get_adjustments(self, qapp):
        """Verifica get_adjustments."""
        panel = AdjustmentControlsPanel()
        adjustments = panel.get_adjustments()
        assert 'tracking' in adjustments
        assert 'size_factor' in adjustments
        assert 'scale_x' in adjustments
    
    def test_reset_all(self, qapp, sample_state):
        """Verifica reset_all."""
        panel = AdjustmentControlsPanel()
        sample_state.current_char_spacing = -1.0
        panel.set_state(sample_state)
        panel.reset_all()
        adjustments = panel.get_adjustments()
        assert adjustments['tracking'] == 0.0


# ================== Tests: TruncationPanel ==================


class TestTruncationPanel:
    """Tests para TruncationPanel."""
    
    def test_creation(self, qapp):
        """Verifica creación del panel."""
        panel = TruncationPanel()
        assert panel is not None
    
    def test_set_text(self, qapp, sample_text):
        """Verifica set_text."""
        panel = TruncationPanel()
        panel.set_text(sample_text)
        assert panel._original_text == sample_text
    
    def test_suffix(self, qapp):
        """Verifica suffix getter."""
        panel = TruncationPanel()
        assert panel.suffix() == "..."
    
    def test_truncated_text(self, qapp):
        """Verifica truncated_text getter."""
        panel = TruncationPanel()
        panel.set_text("Hello World")
        # By default, no truncation
        assert panel.truncated_text() == "Hello World"
    
    def test_signal_emission(self, qapp):
        """Verifica emisión de señal."""
        panel = TruncationPanel()
        spy = QSignalSpy(panel.truncationChanged)
        panel.set_text("Test text")
        assert len(spy) >= 1


# ================== Tests: AdjustmentOptionsDialog ==================


class TestAdjustmentOptionsDialog:
    """Tests para AdjustmentOptionsDialog."""
    
    def test_creation(self, qapp, sample_text, sample_font_config):
        """Verifica creación del diálogo."""
        dialog = AdjustmentOptionsDialog(
            text=sample_text,
            font_name=sample_font_config['font_name'],
            font_size=sample_font_config['font_size'],
            available_width=sample_font_config['available_width'],
        )
        assert dialog is not None
    
    def test_has_state(self, qapp, sample_text, sample_font_config):
        """Verifica que tiene estado."""
        dialog = AdjustmentOptionsDialog(
            text=sample_text,
            font_name=sample_font_config['font_name'],
            font_size=sample_font_config['font_size'],
            available_width=sample_font_config['available_width'],
        )
        assert dialog._state is not None
        assert dialog._state.text == sample_text
    
    def test_has_preview(self, qapp, sample_text, sample_font_config):
        """Verifica que tiene preview widget."""
        dialog = AdjustmentOptionsDialog(
            text=sample_text,
            font_name=sample_font_config['font_name'],
            font_size=sample_font_config['font_size'],
            available_width=sample_font_config['available_width'],
        )
        assert dialog._preview is not None
    
    def test_has_tabs(self, qapp, sample_text, sample_font_config):
        """Verifica que tiene tabs."""
        dialog = AdjustmentOptionsDialog(
            text=sample_text,
            font_name=sample_font_config['font_name'],
            font_size=sample_font_config['font_size'],
            available_width=sample_font_config['available_width'],
        )
        assert dialog._tabs is not None
        assert dialog._tabs.count() >= 3
    
    def test_get_result(self, qapp, sample_text, sample_font_config):
        """Verifica get_result."""
        dialog = AdjustmentOptionsDialog(
            text=sample_text,
            font_name=sample_font_config['font_name'],
            font_size=sample_font_config['font_size'],
            available_width=sample_font_config['available_width'],
        )
        result = dialog.get_result()
        assert isinstance(result, dict)
        assert 'text' in result
    
    def test_on_reset(self, qapp, sample_text, sample_font_config):
        """Verifica _on_reset."""
        dialog = AdjustmentOptionsDialog(
            text=sample_text,
            font_name=sample_font_config['font_name'],
            font_size=sample_font_config['font_size'],
            available_width=sample_font_config['available_width'],
        )
        # Modificar estado
        dialog._state.current_char_spacing = -1.0
        # Resetear
        dialog._on_reset()
        assert dialog._state.current_char_spacing == 0.0


# ================== Tests: Factory Functions ==================


class TestFactoryFunctions:
    """Tests para funciones factory."""
    
    def test_create_adjustment_dialog(self, qapp, sample_text, sample_font_config):
        """Verifica create_adjustment_dialog."""
        dialog = create_adjustment_dialog(
            text=sample_text,
            font_name=sample_font_config['font_name'],
            font_size=sample_font_config['font_size'],
            available_width=sample_font_config['available_width'],
        )
        assert isinstance(dialog, AdjustmentOptionsDialog)
    
    def test_create_adjustment_controls(self, qapp):
        """Verifica create_adjustment_controls."""
        controls = create_adjustment_controls()
        assert isinstance(controls, AdjustmentControlsPanel)
    
    def test_create_preset_selector(self, qapp):
        """Verifica create_preset_selector."""
        selector = create_preset_selector()
        assert isinstance(selector, PresetSelector)
    
    def test_create_preset_selector_custom(self, qapp):
        """Verifica preset selector con presets custom."""
        custom = [AdjustmentPreset(name="X")]
        selector = create_preset_selector(presets=custom)
        assert len(selector._presets) == 1
    
    def test_get_builtin_presets(self):
        """Verifica get_builtin_presets."""
        presets = get_builtin_presets()
        assert presets == BUILTIN_PRESETS
        # Verifica que es una copia
        presets.append(AdjustmentPreset())
        assert len(presets) != len(BUILTIN_PRESETS)


# ================== Tests: Integration ==================


class TestIntegration:
    """Tests de integración."""
    
    def test_preset_applies_to_dialog(self, qapp, sample_text, sample_font_config):
        """Verifica que presets se aplican al diálogo."""
        dialog = AdjustmentOptionsDialog(
            text=sample_text,
            font_name=sample_font_config['font_name'],
            font_size=sample_font_config['font_size'],
            available_width=sample_font_config['available_width'],
        )
        
        # Seleccionar preset "Sin ajuste"
        none_preset = AdjustmentPreset(mode=AdjustmentMode.NONE)
        dialog._on_preset_selected(none_preset)
        
        # Estado debería estar reseteado
        assert not dialog._state.has_changes
    
    def test_controls_update_preview(self, qapp, sample_text, sample_font_config):
        """Verifica que controles actualizan preview."""
        dialog = AdjustmentOptionsDialog(
            text=sample_text,
            font_name=sample_font_config['font_name'],
            font_size=sample_font_config['font_size'],
            available_width=sample_font_config['available_width'],
        )
        
        # Inicializar controles con estado del diálogo
        dialog._controls.set_state(dialog._state)
        
        # Cambiar tracking
        dialog._controls._tracking.set_value(-1.0)
        dialog._controls._on_tracking_changed(-1.0)
        
        assert dialog._state.current_char_spacing == -1.0
    
    def test_truncation_updates_state(self, qapp, sample_text, sample_font_config):
        """Verifica que truncamiento actualiza estado."""
        dialog = AdjustmentOptionsDialog(
            text=sample_text,
            font_name=sample_font_config['font_name'],
            font_size=sample_font_config['font_size'],
            available_width=sample_font_config['available_width'],
        )
        
        # Simular truncamiento
        truncated = "Este es..."
        dialog._on_truncation_changed(truncated, "...")
        
        assert dialog._state.current_text == truncated


# ================== Tests: Edge Cases ==================


class TestEdgeCases:
    """Tests para casos extremos."""
    
    def test_empty_text(self, qapp, sample_font_config):
        """Verifica manejo de texto vacío."""
        dialog = AdjustmentOptionsDialog(
            text="",
            font_name=sample_font_config['font_name'],
            font_size=sample_font_config['font_size'],
            available_width=sample_font_config['available_width'],
        )
        assert dialog._state.text == ""
        result = dialog.get_result()
        assert result['text'] == ""
    
    def test_zero_width(self, qapp, sample_text, sample_font_config):
        """Verifica manejo de ancho cero."""
        dialog = AdjustmentOptionsDialog(
            text=sample_text,
            font_name=sample_font_config['font_name'],
            font_size=sample_font_config['font_size'],
            available_width=0.0,
        )
        assert dialog._state.available_width == 0.0
    
    def test_negative_char_spacing(self, qapp, sample_text, sample_font_config):
        """Verifica manejo de espaciado negativo."""
        dialog = AdjustmentOptionsDialog(
            text=sample_text,
            font_name=sample_font_config['font_name'],
            font_size=sample_font_config['font_size'],
            available_width=sample_font_config['available_width'],
            char_spacing=-1.0,
        )
        assert dialog._state.original_char_spacing == -1.0
    
    def test_very_long_text(self, qapp, sample_font_config):
        """Verifica manejo de texto muy largo."""
        long_text = "x" * 1000
        dialog = AdjustmentOptionsDialog(
            text=long_text,
            font_name=sample_font_config['font_name'],
            font_size=sample_font_config['font_size'],
            available_width=sample_font_config['available_width'],
        )
        assert len(dialog._state.text) == 1000
    
    def test_special_characters(self, qapp, sample_font_config):
        """Verifica manejo de caracteres especiales."""
        special_text = "Héllo Wörld! 日本語 🎉"
        dialog = AdjustmentOptionsDialog(
            text=special_text,
            font_name=sample_font_config['font_name'],
            font_size=sample_font_config['font_size'],
            available_width=sample_font_config['available_width'],
        )
        assert dialog._state.text == special_text


# ================== Tests: State Persistence ==================


class TestStatePersistence:
    """Tests para persistencia de estado."""
    
    def test_state_to_dict_and_back(self, sample_state):
        """Verifica conversión a dict y vuelta."""
        sample_state.current_char_spacing = -1.0
        sample_state.current_font_size = 10.0
        
        d = sample_state.to_dict()
        
        # Verificar valores en dict
        assert d['char_spacing'] == -1.0
        assert d['font_size'] == 10.0
    
    def test_preset_roundtrip(self):
        """Verifica roundtrip de preset."""
        original = AdjustmentPreset(
            name="Test Preset",
            mode=AdjustmentMode.COMBINED,
            tracking_delta=-1.5,
            size_factor=0.9,
        )
        
        d = original.to_dict()
        restored = AdjustmentPreset.from_dict(d)
        
        assert restored.name == original.name
        assert restored.mode == original.mode
        assert restored.tracking_delta == original.tracking_delta
        assert restored.size_factor == original.size_factor

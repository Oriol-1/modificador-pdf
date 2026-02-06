"""
Tests para SafeTextRewriter - Reescritura segura de texto PDF.

PHASE3-3D01: Tests completos para el módulo de overlay mejorado.
"""

import pytest
from unittest.mock import MagicMock, patch
import json

from core.text_engine.safe_text_rewriter import (
    # Enums
    OverlayStrategy,
    RewriteMode,
    OverlayType,
    RewriteStatus,
    # Dataclasses
    OverlayLayer,
    TextOverlayInfo,
    RewriteResult,
    RewriterConfig,
    # Classes
    ZOrderManager,
    SafeTextRewriter,
    # Factory functions
    create_safe_rewriter,
    get_recommended_strategy,
)


# ================== Fixtures ==================


@pytest.fixture
def sample_bbox():
    """Bounding box de ejemplo."""
    return (100.0, 200.0, 250.0, 220.0)


@pytest.fixture
def sample_text():
    """Texto de ejemplo."""
    return "Hello World"


@pytest.fixture
def sample_layer():
    """Capa de ejemplo."""
    return OverlayLayer(
        layer_type=OverlayType.TEXT,
        z_order=300,
        bbox=(100, 200, 250, 220),
        origin=(100, 220),
        content="Hello World",
        font_name="Helvetica",
        font_size=12.0,
        color=(0, 0, 0),
    )


@pytest.fixture
def sample_overlay_info(sample_bbox):
    """TextOverlayInfo de ejemplo."""
    return TextOverlayInfo(
        page_num=0,
        strategy=OverlayStrategy.REDACT_THEN_INSERT,
        original_text="Hello",
        original_bbox=sample_bbox,
        original_font="Helvetica",
        original_size=12.0,
        new_text="World",
        new_font="Helvetica",
        new_size=12.0,
        new_color=(0, 0, 0),
    )


@pytest.fixture
def rewriter():
    """SafeTextRewriter configurado."""
    return SafeTextRewriter()


@pytest.fixture
def z_manager():
    """ZOrderManager limpio."""
    return ZOrderManager()


# ================== Tests: OverlayStrategy Enum ==================


class TestOverlayStrategy:
    """Tests para OverlayStrategy enum."""
    
    def test_all_strategies_defined(self):
        """Verifica que todas las estrategias están definidas."""
        expected = [
            'REDACT_THEN_INSERT',
            'WHITE_BACKGROUND', 
            'TRANSPARENT_ERASE',
            'DIRECT_OVERLAY',
            'CONTENT_STREAM_EDIT',
        ]
        actual = [s.name for s in OverlayStrategy]
        assert actual == expected
    
    def test_str_representation(self):
        """Verifica representación de string."""
        assert str(OverlayStrategy.REDACT_THEN_INSERT) == "Eliminar y reemplazar"
        assert str(OverlayStrategy.WHITE_BACKGROUND) == "Fondo blanco"
        assert str(OverlayStrategy.TRANSPARENT_ERASE) == "Borrado transparente"
        assert str(OverlayStrategy.DIRECT_OVERLAY) == "Overlay directo"
    
    def test_is_safe_property(self):
        """Verifica propiedad is_safe."""
        assert OverlayStrategy.REDACT_THEN_INSERT.is_safe is True
        assert OverlayStrategy.WHITE_BACKGROUND.is_safe is True
        assert OverlayStrategy.DIRECT_OVERLAY.is_safe is True
        assert OverlayStrategy.CONTENT_STREAM_EDIT.is_safe is False
    
    def test_preserves_original_property(self):
        """Verifica propiedad preserves_original."""
        assert OverlayStrategy.DIRECT_OVERLAY.preserves_original is True
        assert OverlayStrategy.REDACT_THEN_INSERT.preserves_original is False
    
    def test_description_property(self):
        """Verifica propiedad description."""
        for strategy in OverlayStrategy:
            desc = strategy.description
            assert isinstance(desc, str)
            assert len(desc) > 0


class TestRewriteMode:
    """Tests para RewriteMode enum."""
    
    def test_all_modes_defined(self):
        """Verifica que todos los modos están definidos."""
        expected = ['PRESERVE_POSITION', 'PRESERVE_BASELINE', 'ADJUST_TO_FIT', 'CENTER_IN_BBOX']
        actual = [m.name for m in RewriteMode]
        assert actual == expected
    
    def test_str_representation(self):
        """Verifica representación de string."""
        assert str(RewriteMode.PRESERVE_POSITION) == "Preservar posición"
        assert str(RewriteMode.CENTER_IN_BBOX) == "Centrar en área"


class TestOverlayType:
    """Tests para OverlayType enum."""
    
    def test_all_types_defined(self):
        """Verifica que todos los tipos están definidos."""
        assert len(OverlayType) == 5
        assert OverlayType.TEXT in OverlayType
        assert OverlayType.BACKGROUND in OverlayType
        assert OverlayType.REDACTION in OverlayType
    
    def test_str_representation(self):
        """Verifica representación de string."""
        assert str(OverlayType.TEXT) == "text"
        assert str(OverlayType.BACKGROUND) == "background"


class TestRewriteStatus:
    """Tests para RewriteStatus enum."""
    
    def test_is_success_property(self):
        """Verifica propiedad is_success."""
        assert RewriteStatus.SUCCESS.is_success is True
        assert RewriteStatus.PARTIAL_SUCCESS.is_success is True
        assert RewriteStatus.FONT_SUBSTITUTED.is_success is True
        assert RewriteStatus.FAILED.is_success is False


# ================== Tests: OverlayLayer Dataclass ==================


class TestOverlayLayer:
    """Tests para OverlayLayer dataclass."""
    
    def test_default_values(self):
        """Verifica valores por defecto."""
        layer = OverlayLayer()
        assert layer.layer_type == OverlayType.TEXT
        assert layer.z_order == 0
        assert layer.font_name == "Helvetica"
        assert layer.layer_id != ""  # Auto-generado
    
    def test_custom_values(self, sample_layer):
        """Verifica valores personalizados."""
        assert sample_layer.layer_type == OverlayType.TEXT
        assert sample_layer.z_order == 300
        assert sample_layer.content == "Hello World"
    
    def test_width_property(self, sample_layer):
        """Verifica cálculo de ancho."""
        assert sample_layer.width == 150.0
    
    def test_height_property(self, sample_layer):
        """Verifica cálculo de alto."""
        assert sample_layer.height == 20.0
    
    def test_auto_generated_id(self):
        """Verifica que se genera ID automáticamente."""
        layer1 = OverlayLayer()
        layer2 = OverlayLayer()
        assert layer1.layer_id != layer2.layer_id
    
    def test_to_dict(self, sample_layer):
        """Verifica conversión a diccionario."""
        d = sample_layer.to_dict()
        assert d['layer_type'] == 'TEXT'
        assert d['z_order'] == 300
        assert d['content'] == "Hello World"
        assert d['font_name'] == "Helvetica"
    
    def test_from_dict(self, sample_layer):
        """Verifica creación desde diccionario."""
        d = sample_layer.to_dict()
        restored = OverlayLayer.from_dict(d)
        assert restored.layer_type == sample_layer.layer_type
        assert restored.z_order == sample_layer.z_order
        assert restored.content == sample_layer.content
    
    def test_roundtrip_serialization(self, sample_layer):
        """Verifica serialización completa."""
        d = sample_layer.to_dict()
        json_str = json.dumps(d)
        restored_dict = json.loads(json_str)
        restored = OverlayLayer.from_dict(restored_dict)
        assert restored.content == sample_layer.content


# ================== Tests: TextOverlayInfo Dataclass ==================


class TestTextOverlayInfo:
    """Tests para TextOverlayInfo dataclass."""
    
    def test_default_values(self):
        """Verifica valores por defecto."""
        info = TextOverlayInfo()
        assert info.strategy == OverlayStrategy.REDACT_THEN_INSERT
        assert info.mode == RewriteMode.PRESERVE_POSITION
        assert info.overlay_id != ""
    
    def test_custom_values(self, sample_overlay_info):
        """Verifica valores personalizados."""
        assert sample_overlay_info.page_num == 0
        assert sample_overlay_info.original_text == "Hello"
        assert sample_overlay_info.new_text == "World"
    
    def test_has_font_change(self):
        """Verifica detección de cambio de fuente."""
        info = TextOverlayInfo(
            original_font="Helvetica",
            new_font="Arial",
        )
        assert info.has_font_change is True
        
        info2 = TextOverlayInfo(
            original_font="Helvetica",
            new_font="Helvetica",
        )
        assert info2.has_font_change is False
    
    def test_has_size_change(self):
        """Verifica detección de cambio de tamaño."""
        info = TextOverlayInfo(
            original_size=12.0,
            new_size=14.0,
        )
        assert info.has_size_change is True
        
        info2 = TextOverlayInfo(
            original_size=12.0,
            new_size=12.0,
        )
        assert info2.has_size_change is False
    
    def test_has_text_change(self, sample_overlay_info):
        """Verifica detección de cambio de texto."""
        assert sample_overlay_info.has_text_change is True
    
    def test_to_dict(self, sample_overlay_info):
        """Verifica conversión a diccionario."""
        d = sample_overlay_info.to_dict()
        assert d['strategy'] == 'REDACT_THEN_INSERT'
        assert d['original_text'] == "Hello"
        assert d['new_text'] == "World"
    
    def test_from_dict(self, sample_overlay_info):
        """Verifica creación desde diccionario."""
        d = sample_overlay_info.to_dict()
        restored = TextOverlayInfo.from_dict(d)
        assert restored.strategy == sample_overlay_info.strategy
        assert restored.original_text == sample_overlay_info.original_text
        assert restored.new_text == sample_overlay_info.new_text


# ================== Tests: RewriteResult Dataclass ==================


class TestRewriteResult:
    """Tests para RewriteResult dataclass."""
    
    def test_default_success(self):
        """Verifica que por defecto es éxito."""
        result = RewriteResult()
        assert result.success is True
        assert result.status == RewriteStatus.SUCCESS
    
    def test_add_warning(self):
        """Verifica añadir warning."""
        result = RewriteResult()
        result.add_warning("Font not found")
        
        assert result.has_warnings is True
        assert len(result.warnings) == 1
        assert result.status == RewriteStatus.PARTIAL_SUCCESS
    
    def test_add_error(self):
        """Verifica añadir error."""
        result = RewriteResult()
        result.add_error("Failed to apply")
        
        assert result.success is False
        assert result.status == RewriteStatus.FAILED
        assert len(result.errors) == 1
    
    def test_to_dict(self):
        """Verifica conversión a diccionario."""
        result = RewriteResult(
            status=RewriteStatus.SUCCESS,
            message="OK",
            original_width=100.0,
            new_width=95.0,
        )
        
        d = result.to_dict()
        assert d['status'] == 'SUCCESS'
        assert d['success'] is True
        assert d['message'] == "OK"


# ================== Tests: RewriterConfig Dataclass ==================


class TestRewriterConfig:
    """Tests para RewriterConfig dataclass."""
    
    def test_default_values(self):
        """Verifica valores por defecto."""
        config = RewriterConfig()
        assert config.default_strategy == OverlayStrategy.REDACT_THEN_INSERT
        assert config.default_mode == RewriteMode.PRESERVE_POSITION
        assert config.auto_adjust_tracking is True
        assert config.min_tracking_delta == -2.0
        assert config.redact_margin == 1.0
    
    def test_custom_values(self):
        """Verifica valores personalizados."""
        config = RewriterConfig(
            default_strategy=OverlayStrategy.WHITE_BACKGROUND,
            auto_adjust_size=False,
            redact_margin=2.0,
        )
        
        assert config.default_strategy == OverlayStrategy.WHITE_BACKGROUND
        assert config.auto_adjust_size is False
        assert config.redact_margin == 2.0


# ================== Tests: ZOrderManager ==================


class TestZOrderManager:
    """Tests para ZOrderManager."""
    
    def test_creation(self, z_manager):
        """Verifica creación del gestor."""
        assert z_manager is not None
        assert len(z_manager._layers) == 0
    
    def test_add_layer(self, z_manager, sample_layer):
        """Verifica añadir capa."""
        z_manager.add_layer(sample_layer, page_num=0)
        
        assert sample_layer.layer_id in z_manager._layers
        assert 0 in z_manager._page_layers
    
    def test_remove_layer(self, z_manager, sample_layer):
        """Verifica eliminar capa."""
        z_manager.add_layer(sample_layer, page_num=0)
        result = z_manager.remove_layer(sample_layer.layer_id)
        
        assert result is True
        assert sample_layer.layer_id not in z_manager._layers
    
    def test_remove_nonexistent_layer(self, z_manager):
        """Verifica eliminar capa inexistente."""
        result = z_manager.remove_layer("nonexistent")
        assert result is False
    
    def test_get_layer(self, z_manager, sample_layer):
        """Verifica obtener capa."""
        z_manager.add_layer(sample_layer, page_num=0)
        
        layer = z_manager.get_layer(sample_layer.layer_id)
        assert layer == sample_layer
    
    def test_get_page_layers(self, z_manager):
        """Verifica obtener capas de página ordenadas."""
        layer1 = OverlayLayer(z_order=100)
        layer2 = OverlayLayer(z_order=300)
        layer3 = OverlayLayer(z_order=200)
        
        z_manager.add_layer(layer1, page_num=0)
        z_manager.add_layer(layer2, page_num=0)
        z_manager.add_layer(layer3, page_num=0)
        
        layers = z_manager.get_page_layers(page_num=0)
        
        assert len(layers) == 3
        assert layers[0].z_order == 100
        assert layers[1].z_order == 200
        assert layers[2].z_order == 300
    
    def test_get_next_z_order(self, z_manager):
        """Verifica obtener siguiente z-order."""
        z1 = z_manager.get_next_z_order(OverlayType.TEXT)
        z2 = z_manager.get_next_z_order(OverlayType.TEXT)
        
        assert z2 > z1
        assert z1 >= ZOrderManager.LEVEL_TEXT
    
    def test_move_to_front(self, z_manager):
        """Verifica mover capa al frente."""
        layer1 = OverlayLayer(z_order=100)
        layer2 = OverlayLayer(z_order=200)
        
        z_manager.add_layer(layer1, page_num=0)
        z_manager.add_layer(layer2, page_num=0)
        
        result = z_manager.move_to_front(layer1.layer_id)
        
        assert result is True
        assert layer1.z_order > layer2.z_order
    
    def test_move_to_back(self, z_manager):
        """Verifica mover capa al fondo."""
        layer1 = OverlayLayer(z_order=100)
        layer2 = OverlayLayer(z_order=200)
        
        z_manager.add_layer(layer1, page_num=0)
        z_manager.add_layer(layer2, page_num=0)
        
        result = z_manager.move_to_back(layer2.layer_id)
        
        assert result is True
        assert layer2.z_order < layer1.z_order
    
    def test_clear_page(self, z_manager):
        """Verifica limpiar página."""
        layer1 = OverlayLayer()
        layer2 = OverlayLayer()
        
        z_manager.add_layer(layer1, page_num=0)
        z_manager.add_layer(layer2, page_num=0)
        
        count = z_manager.clear_page(0)
        
        assert count == 2
        assert len(z_manager._layers) == 0
    
    def test_to_dict(self, z_manager, sample_layer):
        """Verifica serialización."""
        z_manager.add_layer(sample_layer, page_num=0)
        
        d = z_manager.to_dict()
        
        assert 'layers' in d
        assert 'page_layers' in d
        assert sample_layer.layer_id in d['layers']
    
    def test_from_dict(self, z_manager, sample_layer):
        """Verifica deserialización."""
        z_manager.add_layer(sample_layer, page_num=0)
        d = z_manager.to_dict()
        
        restored = ZOrderManager.from_dict(d)
        
        assert sample_layer.layer_id in restored._layers


# ================== Tests: SafeTextRewriter ==================


class TestSafeTextRewriter:
    """Tests para SafeTextRewriter."""
    
    def test_creation(self, rewriter):
        """Verifica creación del rewriter."""
        assert rewriter is not None
        assert rewriter._config is not None
        assert rewriter._z_manager is not None
    
    def test_creation_with_config(self):
        """Verifica creación con configuración."""
        config = RewriterConfig(
            default_strategy=OverlayStrategy.WHITE_BACKGROUND,
        )
        rewriter = SafeTextRewriter(config=config)
        
        assert rewriter.config.default_strategy == OverlayStrategy.WHITE_BACKGROUND
    
    def test_prepare_rewrite(self, rewriter, sample_bbox):
        """Verifica preparar reescritura."""
        overlay = rewriter.prepare_rewrite(
            page_num=0,
            original_text="Hello",
            original_bbox=sample_bbox,
            new_text="World",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        assert overlay is not None
        assert overlay.original_text == "Hello"
        assert overlay.new_text == "World"
        assert len(overlay.layers) >= 1
    
    def test_prepare_rewrite_redact_strategy(self, rewriter, sample_bbox):
        """Verifica capas para estrategia REDACT."""
        overlay = rewriter.prepare_rewrite(
            page_num=0,
            original_text="Hello",
            original_bbox=sample_bbox,
            new_text="World",
            strategy=OverlayStrategy.REDACT_THEN_INSERT,
        )
        
        # Debe tener capa de redacción + capa de texto
        assert len(overlay.layers) == 2
        layer_types = [layer.layer_type for layer in overlay.layers]
        assert OverlayType.REDACTION in layer_types
        assert OverlayType.TEXT in layer_types
    
    def test_prepare_rewrite_white_bg_strategy(self, rewriter, sample_bbox):
        """Verifica capas para estrategia WHITE_BACKGROUND."""
        overlay = rewriter.prepare_rewrite(
            page_num=0,
            original_text="Hello",
            original_bbox=sample_bbox,
            new_text="World",
            strategy=OverlayStrategy.WHITE_BACKGROUND,
        )
        
        # Debe tener capa de fondo + capa de texto
        assert len(overlay.layers) == 2
        layer_types = [layer.layer_type for layer in overlay.layers]
        assert OverlayType.BACKGROUND in layer_types
        assert OverlayType.TEXT in layer_types
    
    def test_prepare_rewrite_direct_overlay_strategy(self, rewriter, sample_bbox):
        """Verifica capas para estrategia DIRECT_OVERLAY."""
        overlay = rewriter.prepare_rewrite(
            page_num=0,
            original_text="Hello",
            original_bbox=sample_bbox,
            new_text="World",
            strategy=OverlayStrategy.DIRECT_OVERLAY,
        )
        
        # Solo debe tener capa de texto
        assert len(overlay.layers) == 1
        assert overlay.layers[0].layer_type == OverlayType.TEXT
    
    def test_get_overlay(self, rewriter, sample_bbox):
        """Verifica obtener overlay."""
        overlay = rewriter.prepare_rewrite(
            page_num=0,
            original_text="Hello",
            original_bbox=sample_bbox,
            new_text="World",
        )
        
        retrieved = rewriter.get_overlay(overlay.overlay_id)
        assert retrieved == overlay
    
    def test_get_page_overlays(self, rewriter, sample_bbox):
        """Verifica obtener overlays de página."""
        rewriter.prepare_rewrite(
            page_num=0,
            original_text="Hello",
            original_bbox=sample_bbox,
            new_text="World",
        )
        rewriter.prepare_rewrite(
            page_num=0,
            original_text="Foo",
            original_bbox=(50, 100, 100, 120),
            new_text="Bar",
        )
        
        overlays = rewriter.get_page_overlays(0)
        assert len(overlays) == 2
    
    def test_remove_overlay(self, rewriter, sample_bbox):
        """Verifica eliminar overlay."""
        overlay = rewriter.prepare_rewrite(
            page_num=0,
            original_text="Hello",
            original_bbox=sample_bbox,
            new_text="World",
        )
        
        result = rewriter.remove_overlay(overlay.overlay_id)
        
        assert result is True
        assert rewriter.get_overlay(overlay.overlay_id) is None
    
    def test_statistics(self, rewriter, sample_bbox):
        """Verifica estadísticas."""
        rewriter.prepare_rewrite(
            page_num=0,
            original_text="Hello",
            original_bbox=sample_bbox,
            new_text="World",
            strategy=OverlayStrategy.REDACT_THEN_INSERT,
        )
        rewriter.prepare_rewrite(
            page_num=1,
            original_text="Foo",
            original_bbox=sample_bbox,
            new_text="Bar",
            strategy=OverlayStrategy.WHITE_BACKGROUND,
        )
        
        stats = rewriter.get_statistics()
        
        assert stats['total_overlays'] == 2
        assert stats['pages_affected'] == 2
        assert 'REDACT_THEN_INSERT' in stats['by_strategy']
        assert 'WHITE_BACKGROUND' in stats['by_strategy']
    
    def test_to_dict(self, rewriter, sample_bbox):
        """Verifica serialización."""
        rewriter.prepare_rewrite(
            page_num=0,
            original_text="Hello",
            original_bbox=sample_bbox,
            new_text="World",
        )
        
        d = rewriter.to_dict()
        
        assert 'config' in d
        assert 'overlays' in d
        assert 'z_manager' in d
    
    def test_from_dict(self, rewriter, sample_bbox):
        """Verifica deserialización."""
        rewriter.prepare_rewrite(
            page_num=0,
            original_text="Hello",
            original_bbox=sample_bbox,
            new_text="World",
        )
        
        d = rewriter.to_dict()
        restored = SafeTextRewriter.from_dict(d)
        
        assert len(restored._overlays) == 1
        assert restored.config.default_strategy == rewriter.config.default_strategy


class TestSafeTextRewriterModes:
    """Tests para modos de reescritura."""
    
    def test_preserve_position_mode(self, rewriter, sample_bbox):
        """Verifica modo PRESERVE_POSITION."""
        overlay = rewriter.prepare_rewrite(
            page_num=0,
            original_text="Hello",
            original_bbox=sample_bbox,
            new_text="World",
            mode=RewriteMode.PRESERVE_POSITION,
        )
        
        text_layer = next(lyr for lyr in overlay.layers if lyr.layer_type == OverlayType.TEXT)
        # El origen debe estar en x0 del bbox
        assert text_layer.origin[0] == sample_bbox[0]
    
    def test_center_in_bbox_mode(self, rewriter, sample_bbox):
        """Verifica modo CENTER_IN_BBOX."""
        overlay = rewriter.prepare_rewrite(
            page_num=0,
            original_text="Hello",
            original_bbox=sample_bbox,
            new_text="World",
            mode=RewriteMode.CENTER_IN_BBOX,
        )
        
        text_layer = next(lyr for lyr in overlay.layers if lyr.layer_type == OverlayType.TEXT)
        # El origen debe estar centrado
        expected_x = (sample_bbox[0] + sample_bbox[2]) / 2
        assert text_layer.origin[0] == expected_x


# ================== Tests: Factory Functions ==================


class TestFactoryFunctions:
    """Tests para funciones factory."""
    
    def test_create_safe_rewriter(self):
        """Verifica create_safe_rewriter."""
        rewriter = create_safe_rewriter(
            strategy=OverlayStrategy.WHITE_BACKGROUND,
            mode=RewriteMode.CENTER_IN_BBOX,
        )
        
        assert rewriter.config.default_strategy == OverlayStrategy.WHITE_BACKGROUND
        assert rewriter.config.default_mode == RewriteMode.CENTER_IN_BBOX
    
    def test_create_safe_rewriter_with_kwargs(self):
        """Verifica create_safe_rewriter con kwargs."""
        rewriter = create_safe_rewriter(
            auto_adjust_size=False,
            redact_margin=2.5,
        )
        
        assert rewriter.config.auto_adjust_size is False
        assert rewriter.config.redact_margin == 2.5
    
    def test_get_recommended_strategy_small_change(self):
        """Verifica recomendación para cambio pequeño."""
        strategy = get_recommended_strategy(
            text_length_change=2,
            has_font_change=False,
        )
        
        assert strategy == OverlayStrategy.TRANSPARENT_ERASE
    
    def test_get_recommended_strategy_large_change(self):
        """Verifica recomendación para texto más largo."""
        strategy = get_recommended_strategy(
            text_length_change=15,
            has_font_change=False,
        )
        
        assert strategy == OverlayStrategy.WHITE_BACKGROUND
    
    def test_get_recommended_strategy_with_signatures(self):
        """Verifica recomendación con firmas digitales."""
        strategy = get_recommended_strategy(
            text_length_change=0,
            has_font_change=False,
            pdf_has_signatures=True,
        )
        
        assert strategy == OverlayStrategy.DIRECT_OVERLAY
    
    def test_get_recommended_strategy_font_change(self):
        """Verifica recomendación con cambio de fuente."""
        strategy = get_recommended_strategy(
            text_length_change=0,
            has_font_change=True,
        )
        
        # Con cambio de fuente, default es REDACT
        assert strategy == OverlayStrategy.REDACT_THEN_INSERT


# ================== Tests: Integration with Mock Page ==================


class TestIntegrationWithMockPage:
    """Tests de integración con página mock."""
    
    @pytest.fixture
    def mock_page(self):
        """Crea una página mock."""
        page = MagicMock()
        page.add_redact_annot = MagicMock(return_value=MagicMock())
        page.apply_redactions = MagicMock()
        page.new_shape = MagicMock(return_value=MagicMock())
        page.insert_text = MagicMock(return_value=1)  # rc > 0 = éxito
        return page
    
    def test_apply_overlay_success(self, rewriter, sample_bbox, mock_page):
        """Verifica aplicar overlay exitoso."""
        overlay = rewriter.prepare_rewrite(
            page_num=0,
            original_text="Hello",
            original_bbox=sample_bbox,
            new_text="World",
            strategy=OverlayStrategy.DIRECT_OVERLAY,  # Solo texto
        )
        
        with patch('core.text_engine.safe_text_rewriter.HAS_FITZ', True):
            with patch('core.text_engine.safe_text_rewriter.fitz') as mock_fitz:
                mock_fitz.Rect = MagicMock(return_value=MagicMock())
                mock_fitz.Point = MagicMock(return_value=MagicMock())
                
                result = rewriter.apply_overlay(overlay, mock_page)
        
        assert result.success is True
        assert overlay.applied is True
    
    def test_rewrite_text_convenience(self, rewriter, sample_bbox, mock_page):
        """Verifica función de conveniencia rewrite_text."""
        with patch('core.text_engine.safe_text_rewriter.HAS_FITZ', True):
            with patch('core.text_engine.safe_text_rewriter.fitz') as mock_fitz:
                mock_fitz.Rect = MagicMock(return_value=MagicMock())
                mock_fitz.Point = MagicMock(return_value=MagicMock())
                
                result = rewriter.rewrite_text(
                    page=mock_page,
                    page_num=0,
                    original_text="Hello",
                    original_bbox=sample_bbox,
                    new_text="World",
                )
        
        assert result.success is True


# ================== Tests: Edge Cases ==================


class TestEdgeCases:
    """Tests para casos extremos."""
    
    def test_empty_text(self, rewriter, sample_bbox):
        """Verifica manejo de texto vacío."""
        overlay = rewriter.prepare_rewrite(
            page_num=0,
            original_text="",
            original_bbox=sample_bbox,
            new_text="",
        )
        
        assert overlay is not None
        assert overlay.new_text == ""
    
    def test_very_long_text(self, rewriter, sample_bbox):
        """Verifica manejo de texto muy largo."""
        long_text = "x" * 1000
        overlay = rewriter.prepare_rewrite(
            page_num=0,
            original_text="Hello",
            original_bbox=sample_bbox,
            new_text=long_text,
        )
        
        assert len(overlay.new_text) == 1000
    
    def test_special_characters(self, rewriter, sample_bbox):
        """Verifica manejo de caracteres especiales."""
        special_text = "Héllo Wörld! 日本語 🎉"
        overlay = rewriter.prepare_rewrite(
            page_num=0,
            original_text="Hello",
            original_bbox=sample_bbox,
            new_text=special_text,
        )
        
        assert overlay.new_text == special_text
    
    def test_zero_size_bbox(self, rewriter):
        """Verifica manejo de bbox con tamaño cero."""
        zero_bbox = (100, 100, 100, 100)
        overlay = rewriter.prepare_rewrite(
            page_num=0,
            original_text="Hello",
            original_bbox=zero_bbox,
            new_text="World",
        )
        
        assert overlay is not None
    
    def test_negative_coordinates(self, rewriter):
        """Verifica manejo de coordenadas negativas."""
        neg_bbox = (-100, -200, 50, 20)
        overlay = rewriter.prepare_rewrite(
            page_num=0,
            original_text="Hello",
            original_bbox=neg_bbox,
            new_text="World",
        )
        
        assert overlay is not None
        assert overlay.original_bbox == neg_bbox


# ================== Tests: Z-Order Levels ==================


class TestZOrderLevels:
    """Tests para niveles de z-order."""
    
    def test_level_constants(self):
        """Verifica constantes de nivel."""
        assert ZOrderManager.LEVEL_BACKGROUND < ZOrderManager.LEVEL_REDACTION
        assert ZOrderManager.LEVEL_REDACTION < ZOrderManager.LEVEL_FILL
        assert ZOrderManager.LEVEL_FILL < ZOrderManager.LEVEL_TEXT
        assert ZOrderManager.LEVEL_TEXT < ZOrderManager.LEVEL_ANNOTATION
    
    def test_layers_ordered_correctly(self, rewriter, sample_bbox):
        """Verifica que las capas se ordenan correctamente."""
        overlay = rewriter.prepare_rewrite(
            page_num=0,
            original_text="Hello",
            original_bbox=sample_bbox,
            new_text="World",
            strategy=OverlayStrategy.REDACT_THEN_INSERT,
        )
        
        # La capa de redacción debe estar debajo del texto
        redact_layer = next(lyr for lyr in overlay.layers if lyr.layer_type == OverlayType.REDACTION)
        text_layer = next(lyr for lyr in overlay.layers if lyr.layer_type == OverlayType.TEXT)
        
        assert redact_layer.z_order < text_layer.z_order


# ================== Tests: Serialization Robustness ==================


class TestSerializationRobustness:
    """Tests de robustez de serialización."""
    
    def test_json_roundtrip_full(self, rewriter, sample_bbox):
        """Verifica roundtrip JSON completo."""
        # Crear varios overlays
        for i in range(3):
            rewriter.prepare_rewrite(
                page_num=i % 2,
                original_text=f"Text{i}",
                original_bbox=sample_bbox,
                new_text=f"New{i}",
            )
        
        # Serializar
        d = rewriter.to_dict()
        json_str = json.dumps(d)
        
        # Deserializar
        restored_dict = json.loads(json_str)
        restored = SafeTextRewriter.from_dict(restored_dict)
        
        # Verificar
        assert len(restored._overlays) == 3
        assert restored.get_statistics()['total_overlays'] == 3
    
    def test_handles_missing_fields(self):
        """Verifica manejo de campos faltantes."""
        minimal_data = {
            'config': {},
            'overlays': {},
            'page_overlays': {},
        }
        
        restored = SafeTextRewriter.from_dict(minimal_data)
        assert restored is not None
        assert restored.config.default_strategy == OverlayStrategy.REDACT_THEN_INSERT

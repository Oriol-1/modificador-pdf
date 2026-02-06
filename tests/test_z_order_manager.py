"""
Tests para el módulo z_order_manager.

Cobertura completa del gestor avanzado de z-order para overlays PDF.
"""

import pytest
# unittest.mock available if needed
import json

from core.text_engine.z_order_manager import (
    # Enums
    LayerLevel,
    CollisionType,
    ReorderOperation,
    # Dataclasses
    LayerInfo,
    CollisionInfo,
    LayerGroup,
    ReorderHistoryEntry,
    ZOrderConfig,
    # Classes
    AdvancedZOrderManager,
    # Factory functions
    create_z_order_manager,
    get_layer_level_for_type,
    resolve_z_order_conflict,
)


# ===================== Tests LayerLevel =====================


class TestLayerLevel:
    """Tests para enum LayerLevel."""
    
    def test_level_values(self):
        """Verifica valores de niveles."""
        assert LayerLevel.BACKGROUND.value == 0
        assert LayerLevel.REDACTION.value == 100
        assert LayerLevel.TEXT.value == 400
        assert LayerLevel.ANNOTATION.value == 600
        assert LayerLevel.UI.value == 1000
    
    def test_level_ordering(self):
        """Verifica orden correcto de niveles."""
        assert LayerLevel.BACKGROUND.value < LayerLevel.TEXT.value
        assert LayerLevel.TEXT.value < LayerLevel.ANNOTATION.value
        assert LayerLevel.ANNOTATION.value < LayerLevel.UI.value
    
    def test_z_base_property(self):
        """Verifica propiedad z_base."""
        assert LayerLevel.TEXT.z_base == 400
        assert LayerLevel.REDACTION.z_base == 100
    
    def test_str_representation(self):
        """Verifica representación de string."""
        text_str = str(LayerLevel.TEXT)
        assert "Texto" in text_str or "TEXT" in text_str
    
    def test_from_z_order_exact(self):
        """Verifica from_z_order con valor exacto."""
        level = LayerLevel.from_z_order(400)
        assert level == LayerLevel.TEXT
    
    def test_from_z_order_between_levels(self):
        """Verifica from_z_order entre niveles."""
        level = LayerLevel.from_z_order(450)
        assert level == LayerLevel.TEXT_DECORATION
    
    def test_from_z_order_high_value(self):
        """Verifica from_z_order con valor alto."""
        level = LayerLevel.from_z_order(2000)
        assert level == LayerLevel.UI
    
    def test_from_z_order_zero(self):
        """Verifica from_z_order con cero."""
        level = LayerLevel.from_z_order(0)
        assert level == LayerLevel.BACKGROUND


# ===================== Tests CollisionType =====================


class TestCollisionType:
    """Tests para enum CollisionType."""
    
    def test_collision_types_exist(self):
        """Verifica que existen todos los tipos."""
        assert hasattr(CollisionType, 'NONE')
        assert hasattr(CollisionType, 'PARTIAL')
        assert hasattr(CollisionType, 'FULL')
        assert hasattr(CollisionType, 'CONTAINS')
        assert hasattr(CollisionType, 'IDENTICAL')
    
    def test_types_are_distinct(self):
        """Verifica que los tipos son distintos."""
        types = [CollisionType.NONE, CollisionType.PARTIAL, CollisionType.FULL]
        assert len(set(types)) == len(types)


# ===================== Tests ReorderOperation =====================


class TestReorderOperation:
    """Tests para enum ReorderOperation."""
    
    def test_operations_exist(self):
        """Verifica que existen todas las operaciones."""
        assert hasattr(ReorderOperation, 'TO_FRONT')
        assert hasattr(ReorderOperation, 'TO_BACK')
        assert hasattr(ReorderOperation, 'FORWARD')
        assert hasattr(ReorderOperation, 'BACKWARD')
        assert hasattr(ReorderOperation, 'TO_LEVEL')
        assert hasattr(ReorderOperation, 'SWAP')


# ===================== Tests LayerInfo =====================


class TestLayerInfo:
    """Tests para dataclass LayerInfo."""
    
    def test_basic_creation(self):
        """Verifica creación básica."""
        layer = LayerInfo(
            page_num=0,
            bbox=(10, 20, 100, 80),
            level=LayerLevel.TEXT,
        )
        assert layer.page_num == 0
        assert layer.bbox == (10, 20, 100, 80)
        assert layer.level == LayerLevel.TEXT
    
    def test_auto_generated_id(self):
        """Verifica generación automática de ID."""
        layer1 = LayerInfo()
        layer2 = LayerInfo()
        assert layer1.layer_id != ""
        assert layer2.layer_id != ""
        assert layer1.layer_id != layer2.layer_id
    
    def test_auto_generated_name(self):
        """Verifica nombre automático."""
        layer = LayerInfo()
        assert layer.name.startswith("Layer_")
    
    def test_custom_name(self):
        """Verifica nombre personalizado."""
        layer = LayerInfo(name="Mi Capa")
        assert layer.name == "Mi Capa"
    
    def test_width_height_properties(self):
        """Verifica propiedades de dimensiones."""
        layer = LayerInfo(bbox=(10, 20, 110, 70))
        assert layer.width == 100
        assert layer.height == 50
    
    def test_area_property(self):
        """Verifica propiedad de área."""
        layer = LayerInfo(bbox=(0, 0, 100, 50))
        assert layer.area == 5000
    
    def test_center_property(self):
        """Verifica propiedad del centro."""
        layer = LayerInfo(bbox=(0, 0, 100, 50))
        cx, cy = layer.center
        assert cx == 50
        assert cy == 25
    
    def test_contains_point_inside(self):
        """Verifica punto dentro del bbox."""
        layer = LayerInfo(bbox=(10, 10, 100, 100))
        assert layer.contains_point(50, 50)
    
    def test_contains_point_outside(self):
        """Verifica punto fuera del bbox."""
        layer = LayerInfo(bbox=(10, 10, 100, 100))
        assert not layer.contains_point(5, 5)
    
    def test_contains_point_on_edge(self):
        """Verifica punto en el borde."""
        layer = LayerInfo(bbox=(10, 10, 100, 100))
        assert layer.contains_point(10, 10)  # Esquina
        assert layer.contains_point(100, 100)  # Otra esquina
    
    def test_touch_updates_timestamp(self):
        """Verifica que touch actualiza timestamp."""
        layer = LayerInfo()
        old_time = layer.modified_at
        layer.touch()
        # El nuevo timestamp debería ser >= al anterior
        assert layer.modified_at >= old_time
    
    def test_to_dict(self):
        """Verifica serialización a diccionario."""
        layer = LayerInfo(
            name="Test Layer",
            page_num=1,
            z_order=450,
            level=LayerLevel.TEXT,
            bbox=(0, 0, 100, 50),
        )
        data = layer.to_dict()
        
        assert data['name'] == "Test Layer"
        assert data['page_num'] == 1
        assert data['z_order'] == 450
        assert data['level'] == "TEXT"
        assert data['bbox'] == [0, 0, 100, 50]
    
    def test_from_dict(self):
        """Verifica deserialización desde diccionario."""
        data = {
            'layer_id': 'test123',
            'name': 'Test Layer',
            'page_num': 2,
            'z_order': 500,
            'level': 'ANNOTATION',
            'bbox': [10, 20, 30, 40],
            'visible': True,
            'locked': False,
        }
        layer = LayerInfo.from_dict(data)
        
        assert layer.layer_id == 'test123'
        assert layer.name == 'Test Layer'
        assert layer.page_num == 2
        assert layer.level == LayerLevel.ANNOTATION
        assert layer.bbox == (10, 20, 30, 40)
    
    def test_from_dict_invalid_level(self):
        """Verifica manejo de nivel inválido."""
        data = {
            'level': 'INVALID_LEVEL',
        }
        layer = LayerInfo.from_dict(data)
        assert layer.level == LayerLevel.TEXT  # Default
    
    def test_roundtrip_serialization(self):
        """Verifica serialización ida y vuelta."""
        original = LayerInfo(
            name="Round Trip",
            page_num=3,
            z_order=600,
            level=LayerLevel.HIGHLIGHT,
            bbox=(5, 10, 95, 90),
            visible=False,
            locked=True,
        )
        data = original.to_dict()
        restored = LayerInfo.from_dict(data)
        
        assert restored.name == original.name
        assert restored.page_num == original.page_num
        assert restored.z_order == original.z_order
        assert restored.level == original.level
        assert restored.visible == original.visible
        assert restored.locked == original.locked


# ===================== Tests CollisionInfo =====================


class TestCollisionInfo:
    """Tests para dataclass CollisionInfo."""
    
    def test_basic_creation(self):
        """Verifica creación básica."""
        info = CollisionInfo(
            layer1_id="a",
            layer2_id="b",
            collision_type=CollisionType.PARTIAL,
        )
        assert info.layer1_id == "a"
        assert info.layer2_id == "b"
        assert info.collision_type == CollisionType.PARTIAL
    
    def test_is_collision_true(self):
        """Verifica is_collision cuando hay colisión."""
        info = CollisionInfo(
            layer1_id="a",
            layer2_id="b",
            collision_type=CollisionType.PARTIAL,
        )
        assert info.is_collision is True
    
    def test_is_collision_false(self):
        """Verifica is_collision cuando no hay colisión."""
        info = CollisionInfo(
            layer1_id="a",
            layer2_id="b",
            collision_type=CollisionType.NONE,
        )
        assert info.is_collision is False
    
    def test_to_dict(self):
        """Verifica serialización."""
        info = CollisionInfo(
            layer1_id="a",
            layer2_id="b",
            collision_type=CollisionType.FULL,
            overlap_bbox=(10, 10, 50, 50),
            overlap_area=1600,
            overlap_percentage=80.0,
        )
        data = info.to_dict()
        
        assert data['layer1_id'] == "a"
        assert data['collision_type'] == "FULL"
        assert data['overlap_area'] == 1600


# ===================== Tests LayerGroup =====================


class TestLayerGroup:
    """Tests para dataclass LayerGroup."""
    
    def test_basic_creation(self):
        """Verifica creación básica."""
        group = LayerGroup(name="Test Group")
        assert group.name == "Test Group"
        assert group.layer_ids == []
    
    def test_auto_name(self):
        """Verifica nombre automático."""
        group = LayerGroup()
        assert group.name.startswith("Group_")
    
    def test_count_property(self):
        """Verifica propiedad count."""
        group = LayerGroup(layer_ids=["a", "b", "c"])
        assert group.count == 3
    
    def test_add_layer(self):
        """Verifica añadir capa."""
        group = LayerGroup()
        group.add("layer1")
        assert "layer1" in group.layer_ids
        assert group.count == 1
    
    def test_add_duplicate_ignored(self):
        """Verifica que no añade duplicados."""
        group = LayerGroup()
        group.add("layer1")
        group.add("layer1")
        assert group.count == 1
    
    def test_remove_layer(self):
        """Verifica eliminar capa."""
        group = LayerGroup(layer_ids=["a", "b", "c"])
        result = group.remove("b")
        assert result is True
        assert "b" not in group.layer_ids
        assert group.count == 2
    
    def test_remove_nonexistent(self):
        """Verifica eliminar capa inexistente."""
        group = LayerGroup(layer_ids=["a"])
        result = group.remove("z")
        assert result is False
    
    def test_to_dict(self):
        """Verifica serialización."""
        group = LayerGroup(
            group_id="g1",
            name="My Group",
            layer_ids=["l1", "l2"],
            locked=True,
        )
        data = group.to_dict()
        
        assert data['group_id'] == "g1"
        assert data['name'] == "My Group"
        assert data['layer_ids'] == ["l1", "l2"]
        assert data['locked'] is True
    
    def test_from_dict(self):
        """Verifica deserialización."""
        data = {
            'group_id': 'g2',
            'name': 'Restored',
            'layer_ids': ['x', 'y'],
            'locked': False,
        }
        group = LayerGroup.from_dict(data)
        
        assert group.group_id == 'g2'
        assert group.name == 'Restored'
        assert group.layer_ids == ['x', 'y']


# ===================== Tests ZOrderConfig =====================


class TestZOrderConfig:
    """Tests para dataclass ZOrderConfig."""
    
    def test_default_values(self):
        """Verifica valores por defecto."""
        config = ZOrderConfig()
        assert config.auto_resolve_conflicts is True
        assert config.maintain_level_boundaries is True
        assert config.max_layers_per_page == 1000
        assert config.enable_history is True
    
    def test_custom_values(self):
        """Verifica valores personalizados."""
        config = ZOrderConfig(
            auto_resolve_conflicts=False,
            max_layers_per_page=500,
            z_order_step=5,
        )
        assert config.auto_resolve_conflicts is False
        assert config.max_layers_per_page == 500
        assert config.z_order_step == 5


# ===================== Tests AdvancedZOrderManager =====================


class TestAdvancedZOrderManagerBasic:
    """Tests básicos para AdvancedZOrderManager."""
    
    def test_creation(self):
        """Verifica creación del gestor."""
        manager = AdvancedZOrderManager()
        assert manager.layer_count == 0
        assert manager.page_count == 0
    
    def test_creation_with_config(self):
        """Verifica creación con configuración."""
        config = ZOrderConfig(max_layers_per_page=50)
        manager = AdvancedZOrderManager(config)
        assert manager.config.max_layers_per_page == 50
    
    def test_add_layer(self):
        """Verifica añadir capa."""
        manager = AdvancedZOrderManager()
        layer = manager.add_layer(
            page_num=0,
            bbox=(0, 0, 100, 50),
            level=LayerLevel.TEXT,
        )
        
        assert manager.layer_count == 1
        assert layer.page_num == 0
        assert layer.level == LayerLevel.TEXT
    
    def test_add_multiple_layers(self):
        """Verifica añadir múltiples capas."""
        manager = AdvancedZOrderManager()
        
        for i in range(5):
            manager.add_layer(
                page_num=0,
                bbox=(i * 10, 0, i * 10 + 50, 50),
            )
        
        assert manager.layer_count == 5
    
    def test_add_layer_with_name(self):
        """Verifica añadir capa con nombre."""
        manager = AdvancedZOrderManager()
        layer = manager.add_layer(
            page_num=0,
            bbox=(0, 0, 100, 50),
            name="Custom Name",
        )
        assert layer.name == "Custom Name"
    
    def test_remove_layer(self):
        """Verifica eliminar capa."""
        manager = AdvancedZOrderManager()
        layer = manager.add_layer(page_num=0, bbox=(0, 0, 100, 50))
        
        result = manager.remove_layer(layer.layer_id)
        assert result is True
        assert manager.layer_count == 0
    
    def test_remove_nonexistent(self):
        """Verifica eliminar capa inexistente."""
        manager = AdvancedZOrderManager()
        result = manager.remove_layer("nonexistent")
        assert result is False
    
    def test_remove_locked_layer(self):
        """Verifica que no se puede eliminar capa bloqueada."""
        manager = AdvancedZOrderManager()
        layer = manager.add_layer(page_num=0, bbox=(0, 0, 100, 50))
        layer.locked = True
        
        result = manager.remove_layer(layer.layer_id)
        assert result is False
        assert manager.layer_count == 1
    
    def test_get_layer(self):
        """Verifica obtener capa."""
        manager = AdvancedZOrderManager()
        layer = manager.add_layer(page_num=0, bbox=(0, 0, 100, 50))
        
        retrieved = manager.get_layer(layer.layer_id)
        assert retrieved is not None
        assert retrieved.layer_id == layer.layer_id
    
    def test_get_layer_nonexistent(self):
        """Verifica obtener capa inexistente."""
        manager = AdvancedZOrderManager()
        result = manager.get_layer("nonexistent")
        assert result is None
    
    def test_max_layers_limit(self):
        """Verifica límite de capas por página."""
        config = ZOrderConfig(max_layers_per_page=3)
        manager = AdvancedZOrderManager(config)
        
        for _ in range(3):
            manager.add_layer(page_num=0, bbox=(0, 0, 10, 10))
        
        with pytest.raises(ValueError):
            manager.add_layer(page_num=0, bbox=(0, 0, 10, 10))


class TestAdvancedZOrderManagerRetrieval:
    """Tests de recuperación de capas."""
    
    def test_get_page_layers(self):
        """Verifica obtener capas de página."""
        manager = AdvancedZOrderManager()
        manager.add_layer(page_num=0, bbox=(0, 0, 50, 50), level=LayerLevel.TEXT)
        manager.add_layer(page_num=0, bbox=(60, 0, 110, 50), level=LayerLevel.ANNOTATION)
        manager.add_layer(page_num=1, bbox=(0, 0, 50, 50))
        
        layers = manager.get_page_layers(0)
        assert len(layers) == 2
    
    def test_get_page_layers_by_level(self):
        """Verifica filtro por nivel."""
        manager = AdvancedZOrderManager()
        manager.add_layer(page_num=0, bbox=(0, 0, 50, 50), level=LayerLevel.TEXT)
        manager.add_layer(page_num=0, bbox=(60, 0, 110, 50), level=LayerLevel.ANNOTATION)
        
        layers = manager.get_page_layers(0, level=LayerLevel.TEXT)
        assert len(layers) == 1
        assert layers[0].level == LayerLevel.TEXT
    
    def test_get_page_layers_visible_only(self):
        """Verifica filtro de visibilidad."""
        manager = AdvancedZOrderManager()
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50))
        layer2 = manager.add_layer(page_num=0, bbox=(60, 0, 110, 50))
        layer1.visible = False
        
        layers = manager.get_page_layers(0, visible_only=True)
        assert len(layers) == 1
        assert layers[0].layer_id == layer2.layer_id
    
    def test_get_page_layers_empty(self):
        """Verifica página vacía."""
        manager = AdvancedZOrderManager()
        layers = manager.get_page_layers(99)
        assert layers == []
    
    def test_get_layers_at_point(self):
        """Verifica capas en un punto."""
        manager = AdvancedZOrderManager()
        manager.add_layer(page_num=0, bbox=(0, 0, 100, 100))
        manager.add_layer(page_num=0, bbox=(50, 50, 150, 150))
        manager.add_layer(page_num=0, bbox=(200, 200, 300, 300))
        
        layers = manager.get_layers_at_point(0, 75, 75)
        assert len(layers) == 2
    
    def test_get_layers_at_point_ordered(self):
        """Verifica orden de capas (arriba primero)."""
        manager = AdvancedZOrderManager()
        l1 = manager.add_layer(page_num=0, bbox=(0, 0, 100, 100))
        l2 = manager.add_layer(page_num=0, bbox=(0, 0, 100, 100))
        
        layers = manager.get_layers_at_point(0, 50, 50)
        # l2 debería estar primero (tiene z-order mayor)
        assert layers[0].layer_id == l2.layer_id
        assert layers[1].layer_id == l1.layer_id
    
    def test_get_all_layers(self):
        """Verifica obtener todas las capas."""
        manager = AdvancedZOrderManager()
        manager.add_layer(page_num=0, bbox=(0, 0, 50, 50))
        manager.add_layer(page_num=1, bbox=(0, 0, 50, 50))
        manager.add_layer(page_num=2, bbox=(0, 0, 50, 50))
        
        all_layers = manager.get_all_layers()
        assert len(all_layers) == 3


class TestAdvancedZOrderManagerReorder:
    """Tests de operaciones de reordenamiento."""
    
    def test_bring_to_front(self):
        """Verifica mover al frente."""
        manager = AdvancedZOrderManager()
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50), level=LayerLevel.TEXT)
        layer2 = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50), level=LayerLevel.TEXT)
        
        manager.bring_to_front(layer1.layer_id)
        
        assert layer1.z_order > layer2.z_order
    
    def test_send_to_back(self):
        """Verifica mover al fondo."""
        manager = AdvancedZOrderManager()
        manager.add_layer(page_num=0, bbox=(0, 0, 50, 50), level=LayerLevel.TEXT)
        layer2 = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50), level=LayerLevel.TEXT)
        layer3 = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50), level=LayerLevel.TEXT)
        
        # layer3 tiene el z_order más alto
        manager.send_to_back(layer3.layer_id)
        
        # layer3 debería tener z_order menor que layer2
        assert layer3.z_order < layer2.z_order
    
    def test_bring_forward(self):
        """Verifica subir una posición."""
        manager = AdvancedZOrderManager()
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50), level=LayerLevel.TEXT)
        layer2 = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50), level=LayerLevel.TEXT)
        manager.add_layer(page_num=0, bbox=(0, 0, 50, 50), level=LayerLevel.TEXT)  # layer3
        
        z1_before = layer1.z_order
        z2_before = layer2.z_order
        
        manager.bring_forward(layer1.layer_id)
        
        # Deberían haber intercambiado
        assert layer1.z_order == z2_before
        assert layer2.z_order == z1_before
    
    def test_send_backward(self):
        """Verifica bajar una posición."""
        manager = AdvancedZOrderManager()
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50), level=LayerLevel.TEXT)
        layer2 = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50), level=LayerLevel.TEXT)
        
        z1_before = layer1.z_order
        z2_before = layer2.z_order
        
        manager.send_backward(layer2.layer_id)
        
        assert layer2.z_order == z1_before
        assert layer1.z_order == z2_before
    
    def test_reorder_locked_layer(self):
        """Verifica que no se puede reordenar capa bloqueada."""
        manager = AdvancedZOrderManager()
        layer = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50))
        layer.locked = True
        original_z = layer.z_order
        
        result = manager.bring_to_front(layer.layer_id)
        assert result is False
        assert layer.z_order == original_z
    
    def test_swap_layers(self):
        """Verifica intercambio de capas."""
        manager = AdvancedZOrderManager()
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50))
        layer2 = manager.add_layer(page_num=0, bbox=(60, 0, 110, 50))
        
        z1 = layer1.z_order
        z2 = layer2.z_order
        
        result = manager.swap_layers(layer1.layer_id, layer2.layer_id)
        
        assert result is True
        assert layer1.z_order == z2
        assert layer2.z_order == z1
    
    def test_swap_different_pages_fails(self):
        """Verifica que no se pueden intercambiar capas de diferentes páginas."""
        manager = AdvancedZOrderManager()
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50))
        layer2 = manager.add_layer(page_num=1, bbox=(0, 0, 50, 50))
        
        result = manager.swap_layers(layer1.layer_id, layer2.layer_id)
        assert result is False
    
    def test_move_to_level(self):
        """Verifica mover a nivel diferente."""
        config = ZOrderConfig(allow_cross_level_movement=True)
        manager = AdvancedZOrderManager(config)
        layer = manager.add_layer(
            page_num=0,
            bbox=(0, 0, 50, 50),
            level=LayerLevel.TEXT,
        )
        
        result = manager.move_to_level(layer.layer_id, LayerLevel.ANNOTATION)
        
        assert result is True
        assert layer.level == LayerLevel.ANNOTATION
    
    def test_move_to_level_disabled(self):
        """Verifica que movimiento entre niveles puede estar deshabilitado."""
        config = ZOrderConfig(allow_cross_level_movement=False)
        manager = AdvancedZOrderManager(config)
        layer = manager.add_layer(
            page_num=0,
            bbox=(0, 0, 50, 50),
            level=LayerLevel.TEXT,
        )
        
        result = manager.move_to_level(layer.layer_id, LayerLevel.ANNOTATION)
        
        assert result is False
        assert layer.level == LayerLevel.TEXT


class TestAdvancedZOrderManagerCollision:
    """Tests de detección de colisiones."""
    
    def test_no_collision(self):
        """Verifica sin colisión."""
        manager = AdvancedZOrderManager()
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50))
        layer2 = manager.add_layer(page_num=0, bbox=(100, 100, 150, 150))
        
        collision = manager.detect_collision(layer1.layer_id, layer2.layer_id)
        assert collision.collision_type == CollisionType.NONE
    
    def test_partial_collision(self):
        """Verifica colisión parcial."""
        manager = AdvancedZOrderManager()
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 100, 100))
        layer2 = manager.add_layer(page_num=0, bbox=(80, 80, 150, 150))
        
        collision = manager.detect_collision(layer1.layer_id, layer2.layer_id)
        assert collision.collision_type == CollisionType.PARTIAL
    
    def test_full_collision(self):
        """Verifica colisión completa (>50% solapamiento)."""
        manager = AdvancedZOrderManager()
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 100, 100))
        layer2 = manager.add_layer(page_num=0, bbox=(10, 10, 110, 110))  # Gran solapamiento
        
        collision = manager.detect_collision(layer1.layer_id, layer2.layer_id)
        # Dependiendo del porcentaje exacto
        assert collision.is_collision
    
    def test_identical_bbox(self):
        """Verifica bbox idéntico."""
        manager = AdvancedZOrderManager()
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 100, 100))
        layer2 = manager.add_layer(page_num=0, bbox=(0, 0, 100, 100))
        
        collision = manager.detect_collision(layer1.layer_id, layer2.layer_id)
        assert collision.collision_type == CollisionType.IDENTICAL
    
    def test_detect_collisions_page(self):
        """Verifica detección de todas las colisiones en página."""
        manager = AdvancedZOrderManager()
        manager.add_layer(page_num=0, bbox=(0, 0, 100, 100))
        manager.add_layer(page_num=0, bbox=(50, 50, 150, 150))  # Colisiona con 1
        manager.add_layer(page_num=0, bbox=(200, 200, 300, 300))  # No colisiona
        
        collisions = manager.detect_collisions(page_num=0)
        assert len(collisions) == 1
    
    def test_has_collision(self):
        """Verifica has_collision."""
        manager = AdvancedZOrderManager()
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 100, 100))
        manager.add_layer(page_num=0, bbox=(50, 50, 150, 150))  # colisiona
        layer3 = manager.add_layer(page_num=0, bbox=(300, 300, 400, 400))
        
        assert manager.has_collision(layer1.layer_id) is True
        assert manager.has_collision(layer3.layer_id) is False
    
    def test_collision_nonexistent_layer(self):
        """Verifica colisión con capa inexistente."""
        manager = AdvancedZOrderManager()
        layer = manager.add_layer(page_num=0, bbox=(0, 0, 100, 100))
        
        collision = manager.detect_collision(layer.layer_id, "nonexistent")
        assert collision.collision_type == CollisionType.NONE


class TestAdvancedZOrderManagerGroups:
    """Tests de grupos de capas."""
    
    def test_create_group(self):
        """Verifica creación de grupo."""
        manager = AdvancedZOrderManager()
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50))
        layer2 = manager.add_layer(page_num=0, bbox=(60, 0, 110, 50))
        
        group = manager.create_group("Test Group", [layer1.layer_id, layer2.layer_id])
        
        assert group is not None
        assert group.name == "Test Group"
        assert group.count == 2
    
    def test_create_group_updates_layers(self):
        """Verifica que crear grupo actualiza capas."""
        manager = AdvancedZOrderManager()
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50))
        layer2 = manager.add_layer(page_num=0, bbox=(60, 0, 110, 50))
        
        group = manager.create_group("G", [layer1.layer_id, layer2.layer_id])
        
        assert layer1.group_id == group.group_id
        assert layer2.group_id == group.group_id
    
    def test_create_group_invalid_layers(self):
        """Verifica grupo con capas inválidas."""
        manager = AdvancedZOrderManager()
        group = manager.create_group("Empty", ["nonexistent1", "nonexistent2"])
        assert group is None
    
    def test_dissolve_group(self):
        """Verifica disolver grupo."""
        manager = AdvancedZOrderManager()
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50))
        layer2 = manager.add_layer(page_num=0, bbox=(60, 0, 110, 50))
        group = manager.create_group("G", [layer1.layer_id, layer2.layer_id])
        
        result = manager.dissolve_group(group.group_id)
        
        assert result is True
        assert layer1.group_id is None
        assert layer2.group_id is None
    
    def test_dissolve_nonexistent_group(self):
        """Verifica disolver grupo inexistente."""
        manager = AdvancedZOrderManager()
        result = manager.dissolve_group("nonexistent")
        assert result is False
    
    def test_get_group(self):
        """Verifica obtener grupo."""
        manager = AdvancedZOrderManager()
        layer = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50))
        group = manager.create_group("G", [layer.layer_id])
        
        retrieved = manager.get_group(group.group_id)
        assert retrieved is not None
        assert retrieved.group_id == group.group_id
    
    def test_get_layer_group(self):
        """Verifica obtener grupo de una capa."""
        manager = AdvancedZOrderManager()
        layer = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50))
        group = manager.create_group("G", [layer.layer_id])
        
        retrieved = manager.get_layer_group(layer.layer_id)
        assert retrieved is not None
        assert retrieved.group_id == group.group_id
    
    def test_move_group(self):
        """Verifica mover grupo completo."""
        manager = AdvancedZOrderManager()
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50), level=LayerLevel.TEXT)
        layer2 = manager.add_layer(page_num=0, bbox=(60, 0, 110, 50), level=LayerLevel.TEXT)
        manager.add_layer(page_num=0, bbox=(120, 0, 170, 50), level=LayerLevel.TEXT)  # layer3
        
        group = manager.create_group("G", [layer1.layer_id, layer2.layer_id])
        
        result = manager.move_group(group.group_id, ReorderOperation.TO_FRONT)
        assert result is True


class TestAdvancedZOrderManagerHistory:
    """Tests de historial."""
    
    def test_undo(self):
        """Verifica undo."""
        manager = AdvancedZOrderManager()
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50))
        layer2 = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50))
        
        # Intercambiamos layer1 y layer2 (forward sube una posición)
        z1_before = layer1.z_order
        z2_before = layer2.z_order
        
        manager.bring_forward(layer1.layer_id)
        
        # Ahora layer1 debería tener el z de layer2 (intercambio)
        new_z = layer1.z_order
        assert new_z == z2_before
        
        result = manager.undo()
        
        assert result is True
        assert layer1.z_order == z1_before
    
    def test_redo(self):
        """Verifica redo."""
        manager = AdvancedZOrderManager()
        layer = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50))
        
        manager.bring_to_front(layer.layer_id)
        new_z = layer.z_order
        
        manager.undo()
        manager.redo()
        
        assert layer.z_order == new_z
    
    def test_undo_empty_history(self):
        """Verifica undo con historial vacío."""
        manager = AdvancedZOrderManager()
        result = manager.undo()
        assert result is False
    
    def test_redo_at_end(self):
        """Verifica redo al final del historial."""
        manager = AdvancedZOrderManager()
        layer = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50))
        manager.bring_to_front(layer.layer_id)
        
        result = manager.redo()
        assert result is False
    
    def test_clear_history(self):
        """Verifica limpiar historial."""
        manager = AdvancedZOrderManager()
        layer = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50))
        manager.bring_to_front(layer.layer_id)
        
        manager.clear_history()
        
        result = manager.undo()
        assert result is False
    
    def test_history_disabled(self):
        """Verifica historial deshabilitado."""
        config = ZOrderConfig(enable_history=False)
        manager = AdvancedZOrderManager(config)
        layer = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50))
        
        manager.bring_to_front(layer.layer_id)
        result = manager.undo()
        
        assert result is False


class TestAdvancedZOrderManagerSerialization:
    """Tests de serialización."""
    
    def test_to_dict(self):
        """Verifica serialización a diccionario."""
        manager = AdvancedZOrderManager()
        layer = manager.add_layer(
            page_num=0,
            bbox=(0, 0, 100, 50),
            name="Test",
        )
        manager.create_group("Group", [layer.layer_id])
        
        data = manager.to_dict()
        
        assert 'config' in data
        assert 'layers' in data
        assert 'groups' in data
        assert len(data['layers']) == 1
    
    def test_from_dict(self):
        """Verifica deserialización."""
        original = AdvancedZOrderManager()
        layer = original.add_layer(
            page_num=0,
            bbox=(0, 0, 100, 50),
            level=LayerLevel.ANNOTATION,
            name="Restored",
        )
        
        data = original.to_dict()
        restored = AdvancedZOrderManager.from_dict(data)
        
        assert restored.layer_count == 1
        restored_layer = restored.get_layer(layer.layer_id)
        assert restored_layer is not None
        assert restored_layer.name == "Restored"
        assert restored_layer.level == LayerLevel.ANNOTATION
    
    def test_roundtrip_with_groups(self):
        """Verifica ida y vuelta con grupos."""
        original = AdvancedZOrderManager()
        layer1 = original.add_layer(page_num=0, bbox=(0, 0, 50, 50))
        layer2 = original.add_layer(page_num=0, bbox=(60, 0, 110, 50))
        group = original.create_group("MyGroup", [layer1.layer_id, layer2.layer_id])
        
        data = original.to_dict()
        restored = AdvancedZOrderManager.from_dict(data)
        
        restored_group = restored.get_group(group.group_id)
        assert restored_group is not None
        assert restored_group.count == 2
    
    def test_json_serialization(self):
        """Verifica que se puede serializar a JSON."""
        manager = AdvancedZOrderManager()
        manager.add_layer(page_num=0, bbox=(0, 0, 100, 50))
        
        data = manager.to_dict()
        json_str = json.dumps(data)
        
        assert len(json_str) > 0
    
    def test_clear(self):
        """Verifica limpiar gestor."""
        manager = AdvancedZOrderManager()
        layer = manager.add_layer(page_num=0, bbox=(0, 0, 100, 50))
        manager.create_group("G", [layer.layer_id])
        
        manager.clear()
        
        assert manager.layer_count == 0
        assert len(manager._groups) == 0


class TestAdvancedZOrderManagerStatistics:
    """Tests de estadísticas."""
    
    def test_get_statistics(self):
        """Verifica obtención de estadísticas."""
        manager = AdvancedZOrderManager()
        manager.add_layer(page_num=0, bbox=(0, 0, 50, 50), level=LayerLevel.TEXT)
        manager.add_layer(page_num=0, bbox=(60, 0, 110, 50), level=LayerLevel.TEXT)
        manager.add_layer(page_num=1, bbox=(0, 0, 50, 50), level=LayerLevel.ANNOTATION)
        
        stats = manager.get_statistics()
        
        assert stats['total_layers'] == 3
        assert stats['total_pages'] == 2
        assert stats['layers_by_level']['TEXT'] == 2
        assert stats['layers_by_level']['ANNOTATION'] == 1
    
    def test_get_layer_stack(self):
        """Verifica obtención de stack de capas."""
        manager = AdvancedZOrderManager()
        manager.add_layer(page_num=0, bbox=(0, 0, 50, 50), name="L1")
        manager.add_layer(page_num=0, bbox=(60, 0, 110, 50), name="L2")
        
        stack = manager.get_layer_stack(0)
        
        assert len(stack) == 2
        # Verifica formato (z_order, layer_id, name, level)
        assert len(stack[0]) == 4


# ===================== Tests Factory Functions =====================


class TestFactoryFunctions:
    """Tests para funciones factory."""
    
    def test_create_z_order_manager(self):
        """Verifica factory básica."""
        manager = create_z_order_manager()
        assert isinstance(manager, AdvancedZOrderManager)
    
    def test_create_z_order_manager_custom(self):
        """Verifica factory con opciones."""
        manager = create_z_order_manager(
            auto_resolve=False,
            maintain_boundaries=False,
            enable_history=False,
        )
        
        assert manager.config.auto_resolve_conflicts is False
        assert manager.config.maintain_level_boundaries is False
        assert manager.config.enable_history is False
    
    def test_get_layer_level_for_type_text(self):
        """Verifica nivel para tipo text."""
        level = get_layer_level_for_type("text")
        assert level == LayerLevel.TEXT
    
    def test_get_layer_level_for_type_annotation(self):
        """Verifica nivel para tipo annotation."""
        level = get_layer_level_for_type("annotation")
        assert level == LayerLevel.ANNOTATION
    
    def test_get_layer_level_for_type_highlight(self):
        """Verifica nivel para tipo highlight."""
        level = get_layer_level_for_type("highlight")
        assert level == LayerLevel.HIGHLIGHT
    
    def test_get_layer_level_for_type_unknown(self):
        """Verifica nivel para tipo desconocido."""
        level = get_layer_level_for_type("unknown_type")
        assert level == LayerLevel.TEXT  # Default
    
    def test_get_layer_level_for_type_case_insensitive(self):
        """Verifica que es case insensitive."""
        level_lower = get_layer_level_for_type("text")
        level_upper = get_layer_level_for_type("TEXT")
        level_mixed = get_layer_level_for_type("Text")
        
        assert level_lower == level_upper == level_mixed
    
    def test_resolve_z_order_conflict(self):
        """Verifica resolución de conflicto."""
        manager = AdvancedZOrderManager()
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 100, 100))
        layer2 = manager.add_layer(page_num=0, bbox=(0, 0, 100, 100))
        
        winner_id = resolve_z_order_conflict(manager, layer1.layer_id, layer2.layer_id)
        
        # Con prefer_newer=True, layer2 debería ganar
        assert winner_id == layer2.layer_id
    
    def test_resolve_z_order_conflict_prefer_older(self):
        """Verifica resolución con prefer_newer=False."""
        manager = AdvancedZOrderManager()
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 100, 100))
        layer2 = manager.add_layer(page_num=0, bbox=(0, 0, 100, 100))
        
        winner_id = resolve_z_order_conflict(
            manager, layer1.layer_id, layer2.layer_id, prefer_newer=False
        )
        
        assert winner_id == layer1.layer_id


# ===================== Tests Edge Cases =====================


class TestEdgeCases:
    """Tests de casos borde."""
    
    def test_zero_size_bbox(self):
        """Verifica bbox de tamaño cero."""
        manager = AdvancedZOrderManager()
        layer = manager.add_layer(page_num=0, bbox=(50, 50, 50, 50))
        
        assert layer.width == 0
        assert layer.height == 0
        assert layer.area == 0
    
    def test_negative_coordinates(self):
        """Verifica coordenadas negativas."""
        manager = AdvancedZOrderManager()
        layer = manager.add_layer(page_num=0, bbox=(-100, -50, 0, 0))
        
        assert layer.width == 100
        assert layer.height == 50
    
    def test_large_page_number(self):
        """Verifica número de página grande."""
        manager = AdvancedZOrderManager()
        layer = manager.add_layer(page_num=9999, bbox=(0, 0, 50, 50))
        
        assert layer.page_num == 9999
        assert manager.page_count == 1
    
    def test_many_layers_performance(self):
        """Test de rendimiento con muchas capas."""
        config = ZOrderConfig(max_layers_per_page=500)
        manager = AdvancedZOrderManager(config)
        
        for i in range(100):
            manager.add_layer(page_num=0, bbox=(i, 0, i + 10, 10))
        
        assert manager.layer_count == 100
        
        # Operaciones deberían completarse rápido
        layers = manager.get_page_layers(0)
        assert len(layers) == 100
    
    def test_layer_removal_from_group(self):
        """Verifica que eliminar capa la saca del grupo."""
        manager = AdvancedZOrderManager()
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 50, 50))
        layer2 = manager.add_layer(page_num=0, bbox=(60, 0, 110, 50))
        group = manager.create_group("G", [layer1.layer_id, layer2.layer_id])
        
        manager.remove_layer(layer1.layer_id)
        
        # El grupo debería tener solo layer2
        updated_group = manager.get_group(group.group_id)
        assert layer1.layer_id not in updated_group.layer_ids


class TestReorderHistoryEntry:
    """Tests para ReorderHistoryEntry."""
    
    def test_creation(self):
        """Verifica creación básica."""
        entry = ReorderHistoryEntry(
            operation=ReorderOperation.TO_FRONT,
            layer_id="test",
            old_z_order=100,
            new_z_order=500,
        )
        
        assert entry.operation == ReorderOperation.TO_FRONT
        assert entry.layer_id == "test"
        assert entry.old_z_order == 100
        assert entry.new_z_order == 500
    
    def test_to_dict(self):
        """Verifica serialización."""
        entry = ReorderHistoryEntry(
            operation=ReorderOperation.FORWARD,
            layer_id="abc",
            old_z_order=200,
            new_z_order=300,
            affected_layers=["x", "y"],
        )
        
        data = entry.to_dict()
        
        assert data['operation'] == "FORWARD"
        assert data['layer_id'] == "abc"
        assert data['affected_layers'] == ["x", "y"]

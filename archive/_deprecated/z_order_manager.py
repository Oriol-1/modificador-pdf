"""
ZOrderManager - Gestión avanzada de z-order para overlays PDF.

Este módulo proporciona gestión completa del orden de apilamiento
de overlays en documentos PDF, incluyendo:

- Niveles semánticos de capas (fondo, redacción, texto, etc.)
- Detección de colisiones y solapamientos
- Resolución automática de conflictos
- Operaciones de reordenamiento (front, back, up, down)
- Agrupación de capas relacionadas
- Historial de cambios para undo/redo
- Serialización y persistencia

PHASE3-3D03: Gestión de z-order para overlays (3h estimado)
Dependencia: 3D-01 (SafeTextRewriter)
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


# ================== Enums ==================


class LayerLevel(Enum):
    """
    Niveles semánticos de capas.
    
    Define la jerarquía natural de elementos en un PDF.
    Los valores más bajos están al fondo.
    """
    BACKGROUND = 0          # Fondo de página (color, imagen)
    REDACTION = 100         # Áreas redactadas/borradas
    CONTENT_BASE = 200      # Contenido base del PDF
    FILL = 300              # Rellenos de forma
    STROKE = 350            # Bordes de forma
    TEXT_BACKGROUND = 380   # Fondo detrás de texto editado
    TEXT = 400              # Texto principal
    TEXT_DECORATION = 450   # Subrayado, tachado
    HIGHLIGHT = 500         # Resaltados
    ANNOTATION = 600        # Anotaciones (notas, etc.)
    MARKUP = 700            # Marcas de revisión
    FOREGROUND = 800        # Elementos de primer plano
    OVERLAY = 900           # Overlays temporales
    UI = 1000               # Elementos de UI (selección, etc.)
    
    def __str__(self) -> str:
        descriptions = {
            LayerLevel.BACKGROUND: "Fondo",
            LayerLevel.REDACTION: "Redacción",
            LayerLevel.CONTENT_BASE: "Contenido base",
            LayerLevel.FILL: "Relleno",
            LayerLevel.STROKE: "Borde",
            LayerLevel.TEXT_BACKGROUND: "Fondo de texto",
            LayerLevel.TEXT: "Texto",
            LayerLevel.TEXT_DECORATION: "Decoración de texto",
            LayerLevel.HIGHLIGHT: "Resaltado",
            LayerLevel.ANNOTATION: "Anotación",
            LayerLevel.MARKUP: "Marcado",
            LayerLevel.FOREGROUND: "Primer plano",
            LayerLevel.OVERLAY: "Overlay",
            LayerLevel.UI: "UI",
        }
        return descriptions.get(self, self.name)
    
    @property
    def z_base(self) -> int:
        """Obtiene el valor base de z-order para este nivel."""
        return self.value
    
    @classmethod
    def from_z_order(cls, z_order: int) -> 'LayerLevel':
        """
        Determina el nivel semántico de un z-order.
        
        Args:
            z_order: Valor de z-order
            
        Returns:
            Nivel semántico correspondiente
        """
        levels = sorted(cls, key=lambda x: x.value, reverse=True)
        for level in levels:
            if z_order >= level.value:
                return level
        return cls.BACKGROUND


class CollisionType(Enum):
    """Tipos de colisión entre capas."""
    NONE = auto()           # Sin colisión
    PARTIAL = auto()        # Solapamiento parcial
    FULL = auto()           # Solapamiento completo
    CONTAINS = auto()       # Una contiene a la otra
    IDENTICAL = auto()      # Mismo bbox exacto


class ReorderOperation(Enum):
    """Operaciones de reordenamiento."""
    TO_FRONT = auto()       # Mover al frente absoluto
    TO_BACK = auto()        # Mover al fondo absoluto
    FORWARD = auto()        # Subir una posición
    BACKWARD = auto()       # Bajar una posición
    TO_LEVEL = auto()       # Mover a nivel específico
    SWAP = auto()           # Intercambiar con otra capa


# ================== Dataclasses ==================


@dataclass
class LayerInfo:
    """
    Información de una capa en el sistema de z-order.
    
    Almacena metadatos y posición de una capa.
    """
    # Identificación
    layer_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    
    # Posición
    page_num: int = 0
    z_order: int = 0
    level: LayerLevel = LayerLevel.TEXT
    
    # Bounding box (x0, y0, x1, y1)
    bbox: Tuple[float, float, float, float] = (0, 0, 0, 0)
    
    # Relaciones
    group_id: Optional[str] = None  # Grupo al que pertenece
    parent_id: Optional[str] = None  # Capa padre (para anidación)
    
    # Estado
    visible: bool = True
    locked: bool = False
    
    # Metadatos
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Datos de origen
    source_type: str = ""  # "overlay", "annotation", "edit", etc.
    source_id: str = ""    # ID del objeto fuente
    
    def __post_init__(self):
        """Inicialización post-creación."""
        if not self.name:
            self.name = f"Layer_{self.layer_id}"
    
    @property
    def width(self) -> float:
        """Ancho del bounding box."""
        return self.bbox[2] - self.bbox[0]
    
    @property
    def height(self) -> float:
        """Alto del bounding box."""
        return self.bbox[3] - self.bbox[1]
    
    @property
    def area(self) -> float:
        """Área del bounding box."""
        return self.width * self.height
    
    @property
    def center(self) -> Tuple[float, float]:
        """Centro del bounding box."""
        return (
            (self.bbox[0] + self.bbox[2]) / 2,
            (self.bbox[1] + self.bbox[3]) / 2,
        )
    
    def contains_point(self, x: float, y: float) -> bool:
        """Verifica si el punto está dentro del bbox."""
        return (
            self.bbox[0] <= x <= self.bbox[2] and
            self.bbox[1] <= y <= self.bbox[3]
        )
    
    def touch(self) -> None:
        """Actualiza timestamp de modificación."""
        self.modified_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario."""
        return {
            'layer_id': self.layer_id,
            'name': self.name,
            'page_num': self.page_num,
            'z_order': self.z_order,
            'level': self.level.name,
            'bbox': list(self.bbox),
            'group_id': self.group_id,
            'parent_id': self.parent_id,
            'visible': self.visible,
            'locked': self.locked,
            'created_at': self.created_at,
            'modified_at': self.modified_at,
            'source_type': self.source_type,
            'source_id': self.source_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayerInfo':
        """Crea desde diccionario."""
        level_name = data.get('level', 'TEXT')
        level = LayerLevel[level_name] if level_name in LayerLevel.__members__ else LayerLevel.TEXT
        
        return cls(
            layer_id=data.get('layer_id', ''),
            name=data.get('name', ''),
            page_num=data.get('page_num', 0),
            z_order=data.get('z_order', 0),
            level=level,
            bbox=tuple(data.get('bbox', [0, 0, 0, 0])),
            group_id=data.get('group_id'),
            parent_id=data.get('parent_id'),
            visible=data.get('visible', True),
            locked=data.get('locked', False),
            created_at=data.get('created_at', ''),
            modified_at=data.get('modified_at', ''),
            source_type=data.get('source_type', ''),
            source_id=data.get('source_id', ''),
        )


@dataclass
class CollisionInfo:
    """
    Información sobre colisión entre dos capas.
    """
    layer1_id: str
    layer2_id: str
    collision_type: CollisionType
    overlap_bbox: Optional[Tuple[float, float, float, float]] = None
    overlap_area: float = 0.0
    overlap_percentage: float = 0.0  # Porcentaje del área menor
    
    @property
    def is_collision(self) -> bool:
        """Verifica si hay colisión."""
        return self.collision_type != CollisionType.NONE
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario."""
        return {
            'layer1_id': self.layer1_id,
            'layer2_id': self.layer2_id,
            'collision_type': self.collision_type.name,
            'overlap_bbox': list(self.overlap_bbox) if self.overlap_bbox else None,
            'overlap_area': self.overlap_area,
            'overlap_percentage': self.overlap_percentage,
        }


@dataclass
class LayerGroup:
    """
    Grupo de capas relacionadas.
    
    Permite agrupar capas para operaciones conjuntas.
    """
    group_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    layer_ids: List[str] = field(default_factory=list)
    locked: bool = False
    
    def __post_init__(self):
        if not self.name:
            self.name = f"Group_{self.group_id}"
    
    @property
    def count(self) -> int:
        """Número de capas en el grupo."""
        return len(self.layer_ids)
    
    def add(self, layer_id: str) -> None:
        """Añade una capa al grupo."""
        if layer_id not in self.layer_ids:
            self.layer_ids.append(layer_id)
    
    def remove(self, layer_id: str) -> bool:
        """Elimina una capa del grupo."""
        if layer_id in self.layer_ids:
            self.layer_ids.remove(layer_id)
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario."""
        return {
            'group_id': self.group_id,
            'name': self.name,
            'layer_ids': self.layer_ids.copy(),
            'locked': self.locked,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayerGroup':
        """Crea desde diccionario."""
        return cls(
            group_id=data.get('group_id', ''),
            name=data.get('name', ''),
            layer_ids=data.get('layer_ids', []).copy(),
            locked=data.get('locked', False),
        )


@dataclass
class ReorderHistoryEntry:
    """Entrada en el historial de reordenamiento."""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    operation: ReorderOperation = ReorderOperation.FORWARD
    layer_id: str = ""
    old_z_order: int = 0
    new_z_order: int = 0
    affected_layers: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario."""
        return {
            'entry_id': self.entry_id,
            'timestamp': self.timestamp,
            'operation': self.operation.name,
            'layer_id': self.layer_id,
            'old_z_order': self.old_z_order,
            'new_z_order': self.new_z_order,
            'affected_layers': self.affected_layers.copy(),
        }


@dataclass
class ZOrderConfig:
    """Configuración del gestor de z-order."""
    # Comportamiento
    auto_resolve_conflicts: bool = True
    maintain_level_boundaries: bool = True
    allow_cross_level_movement: bool = False
    
    # Límites
    max_layers_per_page: int = 1000
    z_order_step: int = 10  # Espacio entre z-orders para inserción
    
    # Historial
    enable_history: bool = True
    max_history_entries: int = 100
    
    # Colisiones
    collision_tolerance: float = 0.5  # Tolerancia para detección de colisión
    warn_on_collision: bool = True


# ================== Main Class ==================


class AdvancedZOrderManager:
    """
    Gestor avanzado de z-order para overlays PDF.
    
    Proporciona gestión completa del orden de apilamiento con:
    - Niveles semánticos
    - Detección de colisiones
    - Operaciones de reordenamiento
    - Agrupación de capas
    - Historial para undo/redo
    
    Usage:
        manager = AdvancedZOrderManager()
        
        # Añadir capas
        layer1 = manager.add_layer(page_num=0, bbox=(0, 0, 100, 50), level=LayerLevel.TEXT)
        layer2 = manager.add_layer(page_num=0, bbox=(50, 0, 150, 50), level=LayerLevel.TEXT)
        
        # Detectar colisiones
        collisions = manager.detect_collisions(page_num=0)
        
        # Reordenar
        manager.bring_to_front(layer1.layer_id)
        
        # Agrupar
        group = manager.create_group("My Group", [layer1.layer_id, layer2.layer_id])
    """
    
    def __init__(self, config: Optional[ZOrderConfig] = None):
        """
        Inicializa el gestor.
        
        Args:
            config: Configuración opcional
        """
        self._config = config or ZOrderConfig()
        
        # Almacenamiento de capas
        self._layers: Dict[str, LayerInfo] = {}
        self._page_layers: Dict[int, List[str]] = {}  # page_num -> [layer_ids ordenados]
        
        # Grupos
        self._groups: Dict[str, LayerGroup] = {}
        
        # Historial
        self._history: List[ReorderHistoryEntry] = []
        self._history_position: int = -1  # Para undo/redo
        
        # Contadores de z-order por nivel y página
        self._z_counters: Dict[Tuple[int, LayerLevel], int] = {}
    
    @property
    def config(self) -> ZOrderConfig:
        """Obtiene configuración."""
        return self._config
    
    @property
    def layer_count(self) -> int:
        """Número total de capas."""
        return len(self._layers)
    
    @property
    def page_count(self) -> int:
        """Número de páginas con capas."""
        return len(self._page_layers)
    
    # ================== Layer Operations ==================
    
    def add_layer(
        self,
        page_num: int,
        bbox: Tuple[float, float, float, float],
        level: LayerLevel = LayerLevel.TEXT,
        name: str = "",
        **kwargs
    ) -> LayerInfo:
        """
        Añade una nueva capa.
        
        Args:
            page_num: Número de página
            bbox: Bounding box (x0, y0, x1, y1)
            level: Nivel semántico
            name: Nombre opcional
            **kwargs: Argumentos adicionales para LayerInfo
            
        Returns:
            LayerInfo creada
        """
        # Verificar límite de capas
        current_count = len(self._page_layers.get(page_num, []))
        if current_count >= self._config.max_layers_per_page:
            raise ValueError(
                f"Límite de capas alcanzado en página {page_num} "
                f"({self._config.max_layers_per_page})"
            )
        
        # Calcular z-order
        z_order = self._get_next_z_order(page_num, level)
        
        # Crear capa
        layer = LayerInfo(
            name=name,
            page_num=page_num,
            z_order=z_order,
            level=level,
            bbox=bbox,
            **kwargs
        )
        
        # Registrar
        self._layers[layer.layer_id] = layer
        
        if page_num not in self._page_layers:
            self._page_layers[page_num] = []
        
        # Insertar en orden
        self._insert_layer_sorted(page_num, layer.layer_id)
        
        return layer
    
    def remove_layer(self, layer_id: str) -> bool:
        """
        Elimina una capa.
        
        Args:
            layer_id: ID de la capa
            
        Returns:
            True si se eliminó
        """
        layer = self._layers.get(layer_id)
        if not layer:
            return False
        
        if layer.locked:
            logger.warning(f"No se puede eliminar capa bloqueada: {layer_id}")
            return False
        
        # Eliminar de grupos
        if layer.group_id and layer.group_id in self._groups:
            self._groups[layer.group_id].remove(layer_id)
        
        # Eliminar de página
        page_num = layer.page_num
        if page_num in self._page_layers:
            if layer_id in self._page_layers[page_num]:
                self._page_layers[page_num].remove(layer_id)
        
        # Eliminar del registro
        del self._layers[layer_id]
        
        return True
    
    def get_layer(self, layer_id: str) -> Optional[LayerInfo]:
        """Obtiene una capa por ID."""
        return self._layers.get(layer_id)
    
    def get_layers_at_point(
        self,
        page_num: int,
        x: float,
        y: float,
        visible_only: bool = True,
    ) -> List[LayerInfo]:
        """
        Obtiene capas en un punto, ordenadas de arriba a abajo.
        
        Args:
            page_num: Número de página
            x, y: Coordenadas del punto
            visible_only: Si solo incluir visibles
            
        Returns:
            Lista de capas (primero = más arriba)
        """
        if page_num not in self._page_layers:
            return []
        
        result = []
        for layer_id in reversed(self._page_layers[page_num]):
            layer = self._layers.get(layer_id)
            if layer:
                if visible_only and not layer.visible:
                    continue
                if layer.contains_point(x, y):
                    result.append(layer)
        
        return result
    
    def get_page_layers(
        self,
        page_num: int,
        level: Optional[LayerLevel] = None,
        visible_only: bool = False,
    ) -> List[LayerInfo]:
        """
        Obtiene capas de una página ordenadas por z-order.
        
        Args:
            page_num: Número de página
            level: Filtrar por nivel (opcional)
            visible_only: Solo capas visibles
            
        Returns:
            Lista de capas (menor z primero)
        """
        if page_num not in self._page_layers:
            return []
        
        result = []
        for layer_id in self._page_layers[page_num]:
            layer = self._layers.get(layer_id)
            if layer:
                if visible_only and not layer.visible:
                    continue
                if level and layer.level != level:
                    continue
                result.append(layer)
        
        return result
    
    def get_all_layers(self) -> List[LayerInfo]:
        """Obtiene todas las capas."""
        return list(self._layers.values())
    
    # ================== Reorder Operations ==================
    
    def bring_to_front(self, layer_id: str) -> bool:
        """
        Mueve capa al frente (máximo z-order en su nivel).
        
        Args:
            layer_id: ID de la capa
            
        Returns:
            True si se movió
        """
        return self._reorder(layer_id, ReorderOperation.TO_FRONT)
    
    def send_to_back(self, layer_id: str) -> bool:
        """
        Mueve capa al fondo (mínimo z-order en su nivel).
        
        Args:
            layer_id: ID de la capa
            
        Returns:
            True si se movió
        """
        return self._reorder(layer_id, ReorderOperation.TO_BACK)
    
    def bring_forward(self, layer_id: str) -> bool:
        """
        Mueve capa una posición hacia arriba.
        
        Args:
            layer_id: ID de la capa
            
        Returns:
            True si se movió
        """
        return self._reorder(layer_id, ReorderOperation.FORWARD)
    
    def send_backward(self, layer_id: str) -> bool:
        """
        Mueve capa una posición hacia abajo.
        
        Args:
            layer_id: ID de la capa
            
        Returns:
            True si se movió
        """
        return self._reorder(layer_id, ReorderOperation.BACKWARD)
    
    def move_to_level(
        self,
        layer_id: str,
        new_level: LayerLevel,
    ) -> bool:
        """
        Mueve capa a un nivel diferente.
        
        Args:
            layer_id: ID de la capa
            new_level: Nuevo nivel
            
        Returns:
            True si se movió
        """
        layer = self._layers.get(layer_id)
        if not layer or layer.locked:
            return False
        
        if not self._config.allow_cross_level_movement:
            logger.warning("Movimiento entre niveles no permitido")
            return False
        
        old_z = layer.z_order
        new_z = self._get_next_z_order(layer.page_num, new_level)
        
        layer.level = new_level
        layer.z_order = new_z
        layer.touch()
        
        # Reordenar lista de página
        self._sort_page_layers(layer.page_num)
        
        # Historial
        if self._config.enable_history:
            self._add_history_entry(
                ReorderOperation.TO_LEVEL,
                layer_id,
                old_z,
                new_z,
            )
        
        return True
    
    def swap_layers(self, layer1_id: str, layer2_id: str) -> bool:
        """
        Intercambia posición de dos capas.
        
        Args:
            layer1_id: ID primera capa
            layer2_id: ID segunda capa
            
        Returns:
            True si se intercambiaron
        """
        layer1 = self._layers.get(layer1_id)
        layer2 = self._layers.get(layer2_id)
        
        if not layer1 or not layer2:
            return False
        
        if layer1.locked or layer2.locked:
            return False
        
        if layer1.page_num != layer2.page_num:
            logger.warning("No se pueden intercambiar capas de diferentes páginas")
            return False
        
        # Intercambiar z-orders
        layer1.z_order, layer2.z_order = layer2.z_order, layer1.z_order
        layer1.touch()
        layer2.touch()
        
        # Reordenar
        self._sort_page_layers(layer1.page_num)
        
        return True
    
    def _reorder(
        self,
        layer_id: str,
        operation: ReorderOperation,
    ) -> bool:
        """Ejecuta operación de reordenamiento."""
        layer = self._layers.get(layer_id)
        if not layer or layer.locked:
            return False
        
        page_num = layer.page_num
        layer_ids = self._page_layers.get(page_num, [])
        
        if layer_id not in layer_ids:
            return False
        
        current_idx = layer_ids.index(layer_id)
        old_z = layer.z_order
        new_z = old_z
        
        # Filtrar capas del mismo nivel si hay restricción
        if self._config.maintain_level_boundaries:
            same_level_ids = [
                lid for lid in layer_ids
                if self._layers[lid].level == layer.level
            ]
            level_idx = same_level_ids.index(layer_id) if layer_id in same_level_ids else -1
        else:
            same_level_ids = layer_ids
            level_idx = current_idx
        
        if operation == ReorderOperation.TO_FRONT:
            if level_idx < len(same_level_ids) - 1:
                top_layer = self._layers[same_level_ids[-1]]
                new_z = top_layer.z_order + self._config.z_order_step
        
        elif operation == ReorderOperation.TO_BACK:
            if level_idx > 0:
                bottom_layer = self._layers[same_level_ids[0]]
                new_z = max(layer.level.z_base, bottom_layer.z_order - self._config.z_order_step)
        
        elif operation == ReorderOperation.FORWARD:
            if level_idx < len(same_level_ids) - 1:
                next_layer = self._layers[same_level_ids[level_idx + 1]]
                # Intercambiar
                new_z = next_layer.z_order
                next_layer.z_order, layer.z_order = layer.z_order, next_layer.z_order
                next_layer.touch()
        
        elif operation == ReorderOperation.BACKWARD:
            if level_idx > 0:
                prev_layer = self._layers[same_level_ids[level_idx - 1]]
                # Intercambiar
                new_z = prev_layer.z_order
                prev_layer.z_order, layer.z_order = layer.z_order, prev_layer.z_order
                prev_layer.touch()
        
        if operation in (ReorderOperation.TO_FRONT, ReorderOperation.TO_BACK):
            layer.z_order = new_z
        
        layer.touch()
        self._sort_page_layers(page_num)
        
        # Historial - registrar si hubo cambio
        actual_z = layer.z_order
        if self._config.enable_history and actual_z != old_z:
            self._add_history_entry(operation, layer_id, old_z, actual_z)
        
        return True
    
    # ================== Collision Detection ==================
    
    def detect_collision(
        self,
        layer1_id: str,
        layer2_id: str,
    ) -> CollisionInfo:
        """
        Detecta colisión entre dos capas.
        
        Args:
            layer1_id: ID primera capa
            layer2_id: ID segunda capa
            
        Returns:
            Información de colisión
        """
        layer1 = self._layers.get(layer1_id)
        layer2 = self._layers.get(layer2_id)
        
        if not layer1 or not layer2:
            return CollisionInfo(
                layer1_id=layer1_id,
                layer2_id=layer2_id,
                collision_type=CollisionType.NONE,
            )
        
        # Calcular intersección de bboxes
        x0 = max(layer1.bbox[0], layer2.bbox[0])
        y0 = max(layer1.bbox[1], layer2.bbox[1])
        x1 = min(layer1.bbox[2], layer2.bbox[2])
        y1 = min(layer1.bbox[3], layer2.bbox[3])
        
        # Sin intersección
        tolerance = self._config.collision_tolerance
        if x0 - tolerance >= x1 or y0 - tolerance >= y1:
            return CollisionInfo(
                layer1_id=layer1_id,
                layer2_id=layer2_id,
                collision_type=CollisionType.NONE,
            )
        
        overlap_bbox = (x0, y0, x1, y1)
        overlap_area = (x1 - x0) * (y1 - y0)
        
        # Determinar tipo de colisión
        area1 = layer1.area
        area2 = layer2.area
        min_area = min(area1, area2) if min(area1, area2) > 0 else 1
        overlap_percentage = (overlap_area / min_area) * 100
        
        # Mismo bbox
        bbox_matches = (
            abs(layer1.bbox[0] - layer2.bbox[0]) < tolerance and
            abs(layer1.bbox[1] - layer2.bbox[1]) < tolerance and
            abs(layer1.bbox[2] - layer2.bbox[2]) < tolerance and
            abs(layer1.bbox[3] - layer2.bbox[3]) < tolerance
        )
        
        if bbox_matches:
            collision_type = CollisionType.IDENTICAL
        elif overlap_percentage >= 95:
            collision_type = CollisionType.CONTAINS
        elif overlap_percentage >= 50:
            collision_type = CollisionType.FULL
        else:
            collision_type = CollisionType.PARTIAL
        
        return CollisionInfo(
            layer1_id=layer1_id,
            layer2_id=layer2_id,
            collision_type=collision_type,
            overlap_bbox=overlap_bbox,
            overlap_area=overlap_area,
            overlap_percentage=overlap_percentage,
        )
    
    def detect_collisions(
        self,
        page_num: int,
        level: Optional[LayerLevel] = None,
    ) -> List[CollisionInfo]:
        """
        Detecta todas las colisiones en una página.
        
        Args:
            page_num: Número de página
            level: Filtrar por nivel (opcional)
            
        Returns:
            Lista de colisiones encontradas
        """
        layers = self.get_page_layers(page_num, level)
        collisions = []
        
        for i, layer1 in enumerate(layers):
            for layer2 in layers[i + 1:]:
                collision = self.detect_collision(layer1.layer_id, layer2.layer_id)
                if collision.is_collision:
                    collisions.append(collision)
        
        return collisions
    
    def has_collision(self, layer_id: str) -> bool:
        """
        Verifica si una capa tiene colisiones.
        
        Args:
            layer_id: ID de la capa
            
        Returns:
            True si tiene al menos una colisión
        """
        layer = self._layers.get(layer_id)
        if not layer:
            return False
        
        for other_id in self._page_layers.get(layer.page_num, []):
            if other_id != layer_id:
                collision = self.detect_collision(layer_id, other_id)
                if collision.is_collision:
                    return True
        
        return False
    
    # ================== Group Operations ==================
    
    def create_group(
        self,
        name: str,
        layer_ids: List[str],
    ) -> Optional[LayerGroup]:
        """
        Crea un grupo de capas.
        
        Args:
            name: Nombre del grupo
            layer_ids: IDs de las capas a agrupar
            
        Returns:
            LayerGroup creado o None si falla
        """
        # Validar que todas las capas existen
        valid_ids = [lid for lid in layer_ids if lid in self._layers]
        if not valid_ids:
            return None
        
        # Verificar que no estén ya agrupadas
        for lid in valid_ids:
            if self._layers[lid].group_id:
                logger.warning(f"Capa {lid} ya pertenece a un grupo")
        
        group = LayerGroup(name=name, layer_ids=valid_ids)
        self._groups[group.group_id] = group
        
        # Actualizar capas
        for lid in valid_ids:
            self._layers[lid].group_id = group.group_id
        
        return group
    
    def dissolve_group(self, group_id: str) -> bool:
        """
        Disuelve un grupo.
        
        Args:
            group_id: ID del grupo
            
        Returns:
            True si se disolvió
        """
        group = self._groups.get(group_id)
        if not group:
            return False
        
        # Actualizar capas
        for lid in group.layer_ids:
            if lid in self._layers:
                self._layers[lid].group_id = None
        
        del self._groups[group_id]
        return True
    
    def get_group(self, group_id: str) -> Optional[LayerGroup]:
        """Obtiene un grupo por ID."""
        return self._groups.get(group_id)
    
    def get_layer_group(self, layer_id: str) -> Optional[LayerGroup]:
        """Obtiene el grupo de una capa."""
        layer = self._layers.get(layer_id)
        if layer and layer.group_id:
            return self._groups.get(layer.group_id)
        return None
    
    def move_group(
        self,
        group_id: str,
        operation: ReorderOperation,
    ) -> bool:
        """
        Aplica operación de reordenamiento a todo un grupo.
        
        Args:
            group_id: ID del grupo
            operation: Operación a aplicar
            
        Returns:
            True si se aplicó
        """
        group = self._groups.get(group_id)
        if not group or group.locked:
            return False
        
        success = True
        for lid in group.layer_ids:
            if not self._reorder(lid, operation):
                success = False
        
        return success
    
    # ================== History Operations ==================
    
    def undo(self) -> bool:
        """
        Deshace el último reordenamiento.
        
        Returns:
            True si se deshizo
        """
        if not self._config.enable_history:
            return False
        
        if self._history_position < 0:
            return False
        
        entry = self._history[self._history_position]
        layer = self._layers.get(entry.layer_id)
        
        if layer:
            layer.z_order = entry.old_z_order
            self._sort_page_layers(layer.page_num)
        
        self._history_position -= 1
        return True
    
    def redo(self) -> bool:
        """
        Rehace el último reordenamiento deshecho.
        
        Returns:
            True si se rehizo
        """
        if not self._config.enable_history:
            return False
        
        if self._history_position >= len(self._history) - 1:
            return False
        
        self._history_position += 1
        entry = self._history[self._history_position]
        layer = self._layers.get(entry.layer_id)
        
        if layer:
            layer.z_order = entry.new_z_order
            self._sort_page_layers(layer.page_num)
        
        return True
    
    def clear_history(self) -> None:
        """Limpia el historial."""
        self._history.clear()
        self._history_position = -1
    
    def _add_history_entry(
        self,
        operation: ReorderOperation,
        layer_id: str,
        old_z: int,
        new_z: int,
    ) -> None:
        """Añade entrada al historial."""
        # Truncar historial si estamos en medio
        if self._history_position < len(self._history) - 1:
            self._history = self._history[:self._history_position + 1]
        
        entry = ReorderHistoryEntry(
            operation=operation,
            layer_id=layer_id,
            old_z_order=old_z,
            new_z_order=new_z,
        )
        
        self._history.append(entry)
        self._history_position = len(self._history) - 1
        
        # Limitar tamaño
        while len(self._history) > self._config.max_history_entries:
            self._history.pop(0)
            self._history_position -= 1
    
    # ================== Helper Methods ==================
    
    def _get_next_z_order(
        self,
        page_num: int,
        level: LayerLevel,
    ) -> int:
        """Obtiene siguiente z-order disponible para nivel y página."""
        key = (page_num, level)
        
        if key not in self._z_counters:
            self._z_counters[key] = 0
        
        z = level.z_base + self._z_counters[key] * self._config.z_order_step
        self._z_counters[key] += 1
        
        return z
    
    def _insert_layer_sorted(self, page_num: int, layer_id: str) -> None:
        """Inserta capa manteniendo orden."""
        layer = self._layers[layer_id]
        layer_list = self._page_layers[page_num]
        
        # Insertar en posición correcta
        for i, lid in enumerate(layer_list):
            if self._layers[lid].z_order > layer.z_order:
                layer_list.insert(i, layer_id)
                return
        
        layer_list.append(layer_id)
    
    def _sort_page_layers(self, page_num: int) -> None:
        """Reordena lista de capas de una página."""
        if page_num in self._page_layers:
            self._page_layers[page_num].sort(
                key=lambda lid: self._layers[lid].z_order if lid in self._layers else 0
            )
    
    # ================== Statistics ==================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del gestor."""
        by_level: Dict[str, int] = {}
        by_page: Dict[int, int] = {}
        
        for layer in self._layers.values():
            level_name = layer.level.name
            by_level[level_name] = by_level.get(level_name, 0) + 1
            by_page[layer.page_num] = by_page.get(layer.page_num, 0) + 1
        
        return {
            'total_layers': len(self._layers),
            'total_pages': len(self._page_layers),
            'total_groups': len(self._groups),
            'layers_by_level': by_level,
            'layers_by_page': by_page,
            'history_entries': len(self._history),
            'history_position': self._history_position,
        }
    
    def get_layer_stack(
        self,
        page_num: int,
    ) -> List[Tuple[int, str, str, LayerLevel]]:
        """
        Obtiene representación del stack de capas.
        
        Returns:
            Lista de (z_order, layer_id, name, level)
        """
        layers = self.get_page_layers(page_num)
        return [
            (layer.z_order, layer.layer_id, layer.name, layer.level)
            for layer in layers
        ]
    
    # ================== Serialization ==================
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa el gestor completo."""
        return {
            'config': {
                'auto_resolve_conflicts': self._config.auto_resolve_conflicts,
                'maintain_level_boundaries': self._config.maintain_level_boundaries,
                'allow_cross_level_movement': self._config.allow_cross_level_movement,
                'max_layers_per_page': self._config.max_layers_per_page,
                'z_order_step': self._config.z_order_step,
                'enable_history': self._config.enable_history,
                'max_history_entries': self._config.max_history_entries,
            },
            'layers': {
                lid: layer.to_dict()
                for lid, layer in self._layers.items()
            },
            'page_layers': {
                str(page): ids
                for page, ids in self._page_layers.items()
            },
            'groups': {
                gid: group.to_dict()
                for gid, group in self._groups.items()
            },
            'z_counters': {
                f"{page}_{level.name}": count
                for (page, level), count in self._z_counters.items()
            },
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AdvancedZOrderManager':
        """Crea desde diccionario."""
        config_data = data.get('config', {})
        config = ZOrderConfig(
            auto_resolve_conflicts=config_data.get('auto_resolve_conflicts', True),
            maintain_level_boundaries=config_data.get('maintain_level_boundaries', True),
            allow_cross_level_movement=config_data.get('allow_cross_level_movement', False),
            max_layers_per_page=config_data.get('max_layers_per_page', 1000),
            z_order_step=config_data.get('z_order_step', 10),
            enable_history=config_data.get('enable_history', True),
            max_history_entries=config_data.get('max_history_entries', 100),
        )
        
        manager = cls(config)
        
        # Restaurar capas
        for lid, layer_data in data.get('layers', {}).items():
            manager._layers[lid] = LayerInfo.from_dict(layer_data)
        
        # Restaurar page_layers
        for page_str, ids in data.get('page_layers', {}).items():
            manager._page_layers[int(page_str)] = ids
        
        # Restaurar grupos
        for gid, group_data in data.get('groups', {}).items():
            manager._groups[gid] = LayerGroup.from_dict(group_data)
        
        # Restaurar contadores
        for key_str, count in data.get('z_counters', {}).items():
            parts = key_str.split('_', 1)
            if len(parts) == 2:
                page = int(parts[0])
                level_name = parts[1]
                if level_name in LayerLevel.__members__:
                    level = LayerLevel[level_name]
                    manager._z_counters[(page, level)] = count
        
        return manager
    
    def clear(self) -> None:
        """Limpia todo el gestor."""
        self._layers.clear()
        self._page_layers.clear()
        self._groups.clear()
        self._history.clear()
        self._history_position = -1
        self._z_counters.clear()


# ================== Factory Functions ==================


def create_z_order_manager(
    auto_resolve: bool = True,
    maintain_boundaries: bool = True,
    enable_history: bool = True,
    **kwargs
) -> AdvancedZOrderManager:
    """
    Crea un gestor de z-order configurado.
    
    Args:
        auto_resolve: Si resolver conflictos automáticamente
        maintain_boundaries: Si mantener límites de nivel
        enable_history: Si habilitar historial
        **kwargs: Argumentos adicionales para config
        
    Returns:
        AdvancedZOrderManager configurado
    """
    config = ZOrderConfig(
        auto_resolve_conflicts=auto_resolve,
        maintain_level_boundaries=maintain_boundaries,
        enable_history=enable_history,
        **kwargs
    )
    return AdvancedZOrderManager(config)


def get_layer_level_for_type(source_type: str) -> LayerLevel:
    """
    Obtiene el nivel semántico recomendado para un tipo de fuente.
    
    Args:
        source_type: Tipo de fuente ("overlay", "annotation", etc.)
        
    Returns:
        LayerLevel recomendado
    """
    mapping = {
        'background': LayerLevel.BACKGROUND,
        'redaction': LayerLevel.REDACTION,
        'erase': LayerLevel.REDACTION,
        'fill': LayerLevel.FILL,
        'text_background': LayerLevel.TEXT_BACKGROUND,
        'text': LayerLevel.TEXT,
        'overlay': LayerLevel.TEXT,
        'underline': LayerLevel.TEXT_DECORATION,
        'strikethrough': LayerLevel.TEXT_DECORATION,
        'highlight': LayerLevel.HIGHLIGHT,
        'annotation': LayerLevel.ANNOTATION,
        'note': LayerLevel.ANNOTATION,
        'comment': LayerLevel.ANNOTATION,
        'markup': LayerLevel.MARKUP,
        'selection': LayerLevel.UI,
        'cursor': LayerLevel.UI,
    }
    return mapping.get(source_type.lower(), LayerLevel.TEXT)


def resolve_z_order_conflict(
    manager: AdvancedZOrderManager,
    layer1_id: str,
    layer2_id: str,
    prefer_newer: bool = True,
) -> str:
    """
    Resuelve conflicto de z-order entre dos capas.
    
    Args:
        manager: Gestor de z-order
        layer1_id: ID primera capa
        layer2_id: ID segunda capa
        prefer_newer: Si preferir la capa más nueva
        
    Returns:
        ID de la capa que quedó arriba
    """
    layer1 = manager.get_layer(layer1_id)
    layer2 = manager.get_layer(layer2_id)
    
    if not layer1 or not layer2:
        return layer1_id if layer1 else layer2_id
    
    # Determinar cuál poner arriba
    if prefer_newer:
        newer = layer1 if layer1.created_at > layer2.created_at else layer2
        older = layer2 if newer == layer1 else layer1
    else:
        newer = layer1
        older = layer2
    
    # Asegurar que newer esté arriba
    if newer.z_order <= older.z_order:
        manager.bring_forward(newer.layer_id)
    
    return newer.layer_id


__all__ = [
    # Enums
    'LayerLevel',
    'CollisionType',
    'ReorderOperation',
    # Dataclasses
    'LayerInfo',
    'CollisionInfo',
    'LayerGroup',
    'ReorderHistoryEntry',
    'ZOrderConfig',
    # Classes
    'AdvancedZOrderManager',
    # Factory functions
    'create_z_order_manager',
    'get_layer_level_for_type',
    'resolve_z_order_conflict',
]

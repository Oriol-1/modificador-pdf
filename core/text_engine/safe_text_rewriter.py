"""
SafeTextRewriter - Reescritura segura de texto PDF mediante overlay.

PHASE3-3D01: Estrategia de overlay mejorada para edición de texto PDF.

Este módulo proporciona:
- OverlayStrategy: Estrategias de overlay disponibles
- RewriteMode: Modos de reescritura (posición, ajuste)
- OverlayLayer: Capa individual de overlay
- TextOverlayInfo: Información completa del overlay
- RewriteResult: Resultado de operación de reescritura
- SafeTextRewriter: Reescritor seguro con overlay
- ZOrderManager: Gestión de orden de capas
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, Any, List, Tuple, Callable
from datetime import datetime
import uuid

try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


# ================== Enums ==================


class OverlayStrategy(Enum):
    """
    Estrategia de overlay para reescritura de texto.
    
    Define cómo se maneja el texto original al sobrescribir.
    """
    
    REDACT_THEN_INSERT = auto()     # Eliminar texto con redact, luego insertar nuevo
    WHITE_BACKGROUND = auto()        # Cubrir con fondo blanco, insertar encima
    TRANSPARENT_ERASE = auto()       # Borrar transparente, insertar encima
    DIRECT_OVERLAY = auto()          # Solo insertar encima (puede verse original)
    CONTENT_STREAM_EDIT = auto()     # Editar directamente el content stream (avanzado)
    
    def __str__(self) -> str:
        labels = {
            OverlayStrategy.REDACT_THEN_INSERT: "Eliminar y reemplazar",
            OverlayStrategy.WHITE_BACKGROUND: "Fondo blanco",
            OverlayStrategy.TRANSPARENT_ERASE: "Borrado transparente",
            OverlayStrategy.DIRECT_OVERLAY: "Overlay directo",
            OverlayStrategy.CONTENT_STREAM_EDIT: "Edición de content stream",
        }
        return labels.get(self, self.name)
    
    @property
    def is_safe(self) -> bool:
        """True si la estrategia es segura (no modifica content stream)."""
        return self != OverlayStrategy.CONTENT_STREAM_EDIT
    
    @property
    def preserves_original(self) -> bool:
        """True si preserva el contenido original (puede verse debajo)."""
        return self == OverlayStrategy.DIRECT_OVERLAY
    
    @property
    def description(self) -> str:
        """Descripción detallada de la estrategia."""
        descriptions = {
            OverlayStrategy.REDACT_THEN_INSERT: 
                "Elimina completamente el texto original usando redacción PDF, "
                "luego inserta el nuevo texto. Seguro y limpio.",
            OverlayStrategy.WHITE_BACKGROUND:
                "Dibuja un rectángulo blanco sobre el texto original, "
                "luego inserta el nuevo texto encima. Visible en PDFs transparentes.",
            OverlayStrategy.TRANSPARENT_ERASE:
                "Borra el texto original con redacción transparente, "
                "luego inserta el nuevo texto. Mantiene fondo original.",
            OverlayStrategy.DIRECT_OVERLAY:
                "Inserta el nuevo texto directamente sobre el original. "
                "El texto original puede verse debajo si hay diferencia de tamaño.",
            OverlayStrategy.CONTENT_STREAM_EDIT:
                "Modifica directamente el content stream del PDF. "
                "Más limpio pero con mayor riesgo de corrupción.",
        }
        return descriptions.get(self, "")


class RewriteMode(Enum):
    """
    Modo de reescritura para posicionamiento del texto.
    """
    
    PRESERVE_POSITION = auto()      # Mantener posición exacta del original
    PRESERVE_BASELINE = auto()      # Mantener baseline, ajustar inicio
    ADJUST_TO_FIT = auto()          # Ajustar posición para que quepa
    CENTER_IN_BBOX = auto()         # Centrar en el bbox original
    
    def __str__(self) -> str:
        labels = {
            RewriteMode.PRESERVE_POSITION: "Preservar posición",
            RewriteMode.PRESERVE_BASELINE: "Preservar baseline",
            RewriteMode.ADJUST_TO_FIT: "Ajustar para caber",
            RewriteMode.CENTER_IN_BBOX: "Centrar en área",
        }
        return labels.get(self, self.name)


class OverlayType(Enum):
    """
    Tipo de overlay en la página.
    """
    
    TEXT = auto()           # Texto insertado
    BACKGROUND = auto()     # Fondo (rectángulo)
    REDACTION = auto()      # Redacción
    SHAPE = auto()          # Forma geométrica
    IMAGE = auto()          # Imagen
    
    def __str__(self) -> str:
        return self.name.lower()


class RewriteStatus(Enum):
    """
    Estado del resultado de reescritura.
    """
    
    SUCCESS = auto()                # Éxito completo
    PARTIAL_SUCCESS = auto()        # Éxito parcial (algunos warnings)
    FAILED = auto()                 # Falló completamente
    FONT_SUBSTITUTED = auto()       # Éxito pero con fuente sustituida
    TEXT_TRUNCATED = auto()         # Éxito pero texto truncado
    POSITION_ADJUSTED = auto()      # Éxito pero posición ajustada
    
    @property
    def is_success(self) -> bool:
        """True si la operación tuvo algún nivel de éxito."""
        return self in [
            RewriteStatus.SUCCESS,
            RewriteStatus.PARTIAL_SUCCESS,
            RewriteStatus.FONT_SUBSTITUTED,
            RewriteStatus.TEXT_TRUNCATED,
            RewriteStatus.POSITION_ADJUSTED,
        ]


# ================== Dataclasses ==================


@dataclass
class OverlayLayer:
    """
    Capa individual de overlay.
    
    Representa una única operación de overlay en la página.
    """
    
    layer_id: str = ""
    layer_type: OverlayType = OverlayType.TEXT
    z_order: int = 0                    # Orden de apilamiento (mayor = encima)
    
    # Geometría
    bbox: Tuple[float, float, float, float] = (0, 0, 0, 0)  # x0, y0, x1, y1
    origin: Tuple[float, float] = (0, 0)    # Punto de origen
    
    # Contenido
    content: str = ""                   # Texto o referencia
    
    # Estilo (para texto)
    font_name: str = "Helvetica"
    font_size: float = 12.0
    color: Tuple[float, float, float] = (0, 0, 0)  # RGB 0-1
    
    # Para fondos
    fill_color: Optional[Tuple[float, float, float]] = None
    fill_opacity: float = 1.0
    stroke_color: Optional[Tuple[float, float, float]] = None
    stroke_width: float = 0.0
    
    # Metadatos
    created_at: str = ""
    source_span_id: Optional[str] = None  # ID del span original si aplica
    
    def __post_init__(self):
        if not self.layer_id:
            self.layer_id = str(uuid.uuid4())[:8]
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    @property
    def width(self) -> float:
        """Ancho del layer."""
        return self.bbox[2] - self.bbox[0]
    
    @property
    def height(self) -> float:
        """Alto del layer."""
        return self.bbox[3] - self.bbox[1]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'layer_id': self.layer_id,
            'layer_type': self.layer_type.name,
            'z_order': self.z_order,
            'bbox': self.bbox,
            'origin': self.origin,
            'content': self.content,
            'font_name': self.font_name,
            'font_size': self.font_size,
            'color': self.color,
            'fill_color': self.fill_color,
            'fill_opacity': self.fill_opacity,
            'stroke_color': self.stroke_color,
            'stroke_width': self.stroke_width,
            'created_at': self.created_at,
            'source_span_id': self.source_span_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OverlayLayer":
        """Crea desde diccionario."""
        layer_type_name = data.get('layer_type', 'TEXT')
        layer_type = OverlayType[layer_type_name] if layer_type_name in OverlayType.__members__ else OverlayType.TEXT
        
        return cls(
            layer_id=data.get('layer_id', ''),
            layer_type=layer_type,
            z_order=data.get('z_order', 0),
            bbox=tuple(data.get('bbox', (0, 0, 0, 0))),
            origin=tuple(data.get('origin', (0, 0))),
            content=data.get('content', ''),
            font_name=data.get('font_name', 'Helvetica'),
            font_size=data.get('font_size', 12.0),
            color=tuple(data.get('color', (0, 0, 0))),
            fill_color=tuple(data['fill_color']) if data.get('fill_color') else None,
            fill_opacity=data.get('fill_opacity', 1.0),
            stroke_color=tuple(data['stroke_color']) if data.get('stroke_color') else None,
            stroke_width=data.get('stroke_width', 0.0),
            created_at=data.get('created_at', ''),
            source_span_id=data.get('source_span_id'),
        )


@dataclass
class TextOverlayInfo:
    """
    Información completa de un overlay de texto.
    
    Agrupa la información del texto original y el nuevo.
    """
    
    overlay_id: str = ""
    page_num: int = 0
    strategy: OverlayStrategy = OverlayStrategy.REDACT_THEN_INSERT
    mode: RewriteMode = RewriteMode.PRESERVE_POSITION
    
    # Texto original
    original_text: str = ""
    original_bbox: Tuple[float, float, float, float] = (0, 0, 0, 0)
    original_font: str = ""
    original_size: float = 0.0
    original_span_id: Optional[str] = None
    
    # Texto nuevo
    new_text: str = ""
    new_font: str = ""
    new_size: float = 0.0
    new_color: Tuple[float, float, float] = (0, 0, 0)
    
    # Ajustes aplicados
    char_spacing_delta: float = 0.0
    scale_factor: float = 1.0
    position_offset: Tuple[float, float] = (0, 0)
    
    # Capas creadas
    layers: List[OverlayLayer] = field(default_factory=list)
    
    # Metadatos
    created_at: str = ""
    applied: bool = False
    
    def __post_init__(self):
        if not self.overlay_id:
            self.overlay_id = str(uuid.uuid4())[:12]
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    @property
    def has_font_change(self) -> bool:
        """True si cambió la fuente."""
        return self.new_font != self.original_font
    
    @property
    def has_size_change(self) -> bool:
        """True si cambió el tamaño."""
        return abs(self.new_size - self.original_size) > 0.01
    
    @property
    def has_text_change(self) -> bool:
        """True si cambió el texto."""
        return self.new_text != self.original_text
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'overlay_id': self.overlay_id,
            'page_num': self.page_num,
            'strategy': self.strategy.name,
            'mode': self.mode.name,
            'original_text': self.original_text,
            'original_bbox': self.original_bbox,
            'original_font': self.original_font,
            'original_size': self.original_size,
            'original_span_id': self.original_span_id,
            'new_text': self.new_text,
            'new_font': self.new_font,
            'new_size': self.new_size,
            'new_color': self.new_color,
            'char_spacing_delta': self.char_spacing_delta,
            'scale_factor': self.scale_factor,
            'position_offset': self.position_offset,
            'layers': [layer.to_dict() for layer in self.layers],
            'created_at': self.created_at,
            'applied': self.applied,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TextOverlayInfo":
        """Crea desde diccionario."""
        strategy_name = data.get('strategy', 'REDACT_THEN_INSERT')
        strategy = OverlayStrategy[strategy_name] if strategy_name in OverlayStrategy.__members__ else OverlayStrategy.REDACT_THEN_INSERT
        
        mode_name = data.get('mode', 'PRESERVE_POSITION')
        mode = RewriteMode[mode_name] if mode_name in RewriteMode.__members__ else RewriteMode.PRESERVE_POSITION
        
        layers = [OverlayLayer.from_dict(layer_data) for layer_data in data.get('layers', [])]
        
        return cls(
            overlay_id=data.get('overlay_id', ''),
            page_num=data.get('page_num', 0),
            strategy=strategy,
            mode=mode,
            original_text=data.get('original_text', ''),
            original_bbox=tuple(data.get('original_bbox', (0, 0, 0, 0))),
            original_font=data.get('original_font', ''),
            original_size=data.get('original_size', 0.0),
            original_span_id=data.get('original_span_id'),
            new_text=data.get('new_text', ''),
            new_font=data.get('new_font', ''),
            new_size=data.get('new_size', 0.0),
            new_color=tuple(data.get('new_color', (0, 0, 0))),
            char_spacing_delta=data.get('char_spacing_delta', 0.0),
            scale_factor=data.get('scale_factor', 1.0),
            position_offset=tuple(data.get('position_offset', (0, 0))),
            layers=layers,
            created_at=data.get('created_at', ''),
            applied=data.get('applied', False),
        )


@dataclass
class RewriteResult:
    """
    Resultado de una operación de reescritura.
    """
    
    status: RewriteStatus = RewriteStatus.SUCCESS
    overlay_info: Optional[TextOverlayInfo] = None
    
    # Detalles del resultado
    message: str = ""
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # Métricas
    original_width: float = 0.0
    new_width: float = 0.0
    width_difference: float = 0.0
    
    # Sustituciones
    font_substituted: bool = False
    original_font_requested: str = ""
    font_used: str = ""
    
    @property
    def success(self) -> bool:
        """True si la operación fue exitosa."""
        return self.status.is_success
    
    @property
    def has_warnings(self) -> bool:
        """True si hay warnings."""
        return len(self.warnings) > 0
    
    def add_warning(self, warning: str) -> None:
        """Añade un warning."""
        self.warnings.append(warning)
        if self.status == RewriteStatus.SUCCESS:
            self.status = RewriteStatus.PARTIAL_SUCCESS
    
    def add_error(self, error: str) -> None:
        """Añade un error."""
        self.errors.append(error)
        self.status = RewriteStatus.FAILED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'status': self.status.name,
            'success': self.success,
            'message': self.message,
            'warnings': self.warnings,
            'errors': self.errors,
            'original_width': self.original_width,
            'new_width': self.new_width,
            'width_difference': self.width_difference,
            'font_substituted': self.font_substituted,
            'original_font_requested': self.original_font_requested,
            'font_used': self.font_used,
            'overlay_info': self.overlay_info.to_dict() if self.overlay_info else None,
        }


@dataclass 
class RewriterConfig:
    """
    Configuración del SafeTextRewriter.
    """
    
    # Estrategia por defecto
    default_strategy: OverlayStrategy = OverlayStrategy.REDACT_THEN_INSERT
    default_mode: RewriteMode = RewriteMode.PRESERVE_POSITION
    
    # Opciones de ajuste automático
    auto_adjust_tracking: bool = True
    auto_adjust_size: bool = True
    auto_scale_horizontal: bool = False
    
    # Límites de ajuste
    min_tracking_delta: float = -2.0
    max_tracking_delta: float = 2.0
    min_size_factor: float = 0.7
    max_size_factor: float = 1.3
    min_scale_x: float = 0.75
    max_scale_x: float = 1.25
    
    # Opciones de fuente
    allow_font_substitution: bool = True
    prefer_embedded_fonts: bool = True
    
    # Margen adicional para redacción
    redact_margin: float = 1.0  # puntos adicionales alrededor del texto
    
    # Debug
    verbose: bool = False


# ================== ZOrderManager ==================


class ZOrderManager:
    """
    Gestor de orden de capas (z-order).
    
    Controla el orden de apilamiento de los overlays.
    """
    
    # Niveles base predefinidos
    LEVEL_BACKGROUND = 0
    LEVEL_REDACTION = 100
    LEVEL_FILL = 200
    LEVEL_TEXT = 300
    LEVEL_ANNOTATION = 400
    LEVEL_FOREGROUND = 500
    
    def __init__(self):
        """Inicializa el gestor."""
        self._layers: Dict[str, OverlayLayer] = {}
        self._page_layers: Dict[int, List[str]] = {}  # page_num -> [layer_ids]
        self._next_z: Dict[int, int] = {}  # Siguiente z-order por nivel
    
    def add_layer(self, layer: OverlayLayer, page_num: int) -> None:
        """
        Añade una capa.
        
        Args:
            layer: Capa a añadir
            page_num: Número de página
        """
        self._layers[layer.layer_id] = layer
        
        if page_num not in self._page_layers:
            self._page_layers[page_num] = []
        
        self._page_layers[page_num].append(layer.layer_id)
    
    def remove_layer(self, layer_id: str) -> bool:
        """
        Elimina una capa.
        
        Args:
            layer_id: ID de la capa
            
        Returns:
            True si se eliminó
        """
        if layer_id not in self._layers:
            return False
        
        del self._layers[layer_id]
        
        for page_layers in self._page_layers.values():
            if layer_id in page_layers:
                page_layers.remove(layer_id)
        
        return True
    
    def get_layer(self, layer_id: str) -> Optional[OverlayLayer]:
        """Obtiene una capa por ID."""
        return self._layers.get(layer_id)
    
    def get_page_layers(self, page_num: int) -> List[OverlayLayer]:
        """
        Obtiene las capas de una página ordenadas por z-order.
        
        Args:
            page_num: Número de página
            
        Returns:
            Lista de capas ordenadas (menor z primero = debajo)
        """
        if page_num not in self._page_layers:
            return []
        
        layers = [self._layers[lid] for lid in self._page_layers[page_num] if lid in self._layers]
        return sorted(layers, key=lambda layer: layer.z_order)
    
    def get_next_z_order(self, layer_type: OverlayType) -> int:
        """
        Obtiene el siguiente z-order para un tipo de capa.
        
        Args:
            layer_type: Tipo de capa
            
        Returns:
            Siguiente z-order disponible
        """
        base_level = {
            OverlayType.BACKGROUND: self.LEVEL_BACKGROUND,
            OverlayType.REDACTION: self.LEVEL_REDACTION,
            OverlayType.SHAPE: self.LEVEL_FILL,
            OverlayType.TEXT: self.LEVEL_TEXT,
            OverlayType.IMAGE: self.LEVEL_ANNOTATION,
        }.get(layer_type, self.LEVEL_TEXT)
        
        if base_level not in self._next_z:
            self._next_z[base_level] = 0
        
        z = base_level + self._next_z[base_level]
        self._next_z[base_level] += 1
        
        return z
    
    def move_to_front(self, layer_id: str) -> bool:
        """
        Mueve una capa al frente.
        
        Args:
            layer_id: ID de la capa
            
        Returns:
            True si se movió
        """
        layer = self._layers.get(layer_id)
        if not layer:
            return False
        
        # Encontrar el máximo z-order en la misma página
        for page_num, layer_ids in self._page_layers.items():
            if layer_id in layer_ids:
                max_z = max(
                    (self._layers[lid].z_order for lid in layer_ids if lid in self._layers),
                    default=0
                )
                layer.z_order = max_z + 1
                return True
        
        return False
    
    def move_to_back(self, layer_id: str) -> bool:
        """
        Mueve una capa al fondo.
        
        Args:
            layer_id: ID de la capa
            
        Returns:
            True si se movió
        """
        layer = self._layers.get(layer_id)
        if not layer:
            return False
        
        for page_num, layer_ids in self._page_layers.items():
            if layer_id in layer_ids:
                min_z = min(
                    (self._layers[lid].z_order for lid in layer_ids if lid in self._layers),
                    default=0
                )
                layer.z_order = min_z - 1
                return True
        
        return False
    
    def clear_page(self, page_num: int) -> int:
        """
        Elimina todas las capas de una página.
        
        Args:
            page_num: Número de página
            
        Returns:
            Número de capas eliminadas
        """
        if page_num not in self._page_layers:
            return 0
        
        count = 0
        for layer_id in self._page_layers[page_num]:
            if layer_id in self._layers:
                del self._layers[layer_id]
                count += 1
        
        del self._page_layers[page_num]
        return count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            'layers': {lid: layer.to_dict() for lid, layer in self._layers.items()},
            'page_layers': self._page_layers,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ZOrderManager":
        """Crea desde diccionario."""
        manager = cls()
        
        for lid, layer_data in data.get('layers', {}).items():
            manager._layers[lid] = OverlayLayer.from_dict(layer_data)
        
        manager._page_layers = data.get('page_layers', {})
        # Convertir claves a int si vienen como string
        manager._page_layers = {
            int(k): v for k, v in manager._page_layers.items()
        }
        
        return manager


# ================== SafeTextRewriter ==================


class SafeTextRewriter:
    """
    Reescritor seguro de texto PDF mediante overlay.
    
    Proporciona múltiples estrategias para reescribir texto de forma
    segura, preservando la estructura del documento.
    """
    
    def __init__(
        self,
        config: Optional[RewriterConfig] = None
    ):
        """
        Inicializa el reescritor.
        
        Args:
            config: Configuración opcional
        """
        self._config = config or RewriterConfig()
        self._z_manager = ZOrderManager()
        self._overlays: Dict[str, TextOverlayInfo] = {}
        self._page_overlays: Dict[int, List[str]] = {}
    
    @property
    def config(self) -> RewriterConfig:
        """Obtiene la configuración."""
        return self._config
    
    @property
    def z_manager(self) -> ZOrderManager:
        """Obtiene el gestor de z-order."""
        return self._z_manager
    
    def prepare_rewrite(
        self,
        page_num: int,
        original_text: str,
        original_bbox: Tuple[float, float, float, float],
        new_text: str,
        font_name: str = "Helvetica",
        font_size: float = 12.0,
        color: Tuple[float, float, float] = (0, 0, 0),
        strategy: Optional[OverlayStrategy] = None,
        mode: Optional[RewriteMode] = None,
        original_font: str = "",
        original_size: float = 0.0,
        original_span_id: Optional[str] = None,
    ) -> TextOverlayInfo:
        """
        Prepara una reescritura de texto.
        
        Crea la información del overlay sin aplicarlo aún.
        
        Args:
            page_num: Número de página
            original_text: Texto original
            original_bbox: Bounding box original (x0, y0, x1, y1)
            new_text: Nuevo texto
            font_name: Nombre de fuente para el nuevo texto
            font_size: Tamaño de fuente
            color: Color RGB (0-1)
            strategy: Estrategia de overlay
            mode: Modo de reescritura
            original_font: Fuente original
            original_size: Tamaño original
            original_span_id: ID del span original
            
        Returns:
            TextOverlayInfo preparado
        """
        strategy = strategy or self._config.default_strategy
        mode = mode or self._config.default_mode
        
        overlay_info = TextOverlayInfo(
            page_num=page_num,
            strategy=strategy,
            mode=mode,
            original_text=original_text,
            original_bbox=original_bbox,
            original_font=original_font or font_name,
            original_size=original_size or font_size,
            original_span_id=original_span_id,
            new_text=new_text,
            new_font=font_name,
            new_size=font_size,
            new_color=color,
        )
        
        # Crear capas según estrategia
        self._create_layers_for_strategy(overlay_info)
        
        # Registrar overlay
        self._overlays[overlay_info.overlay_id] = overlay_info
        if page_num not in self._page_overlays:
            self._page_overlays[page_num] = []
        self._page_overlays[page_num].append(overlay_info.overlay_id)
        
        return overlay_info
    
    def _create_layers_for_strategy(self, overlay_info: TextOverlayInfo) -> None:
        """
        Crea las capas necesarias según la estrategia.
        
        Args:
            overlay_info: Información del overlay
        """
        bbox = overlay_info.original_bbox
        margin = self._config.redact_margin
        
        # Expandir bbox con margen para redacción
        expanded_bbox = (
            bbox[0] - margin,
            bbox[1] - margin,
            bbox[2] + margin,
            bbox[3] + margin,
        )
        
        if overlay_info.strategy == OverlayStrategy.REDACT_THEN_INSERT:
            # Capa 1: Redacción (elimina texto original)
            redact_layer = OverlayLayer(
                layer_type=OverlayType.REDACTION,
                z_order=self._z_manager.get_next_z_order(OverlayType.REDACTION),
                bbox=expanded_bbox,
                content="",
                source_span_id=overlay_info.original_span_id,
            )
            overlay_info.layers.append(redact_layer)
            self._z_manager.add_layer(redact_layer, overlay_info.page_num)
            
            # Capa 2: Texto nuevo
            text_layer = self._create_text_layer(overlay_info)
            overlay_info.layers.append(text_layer)
            self._z_manager.add_layer(text_layer, overlay_info.page_num)
            
        elif overlay_info.strategy == OverlayStrategy.WHITE_BACKGROUND:
            # Capa 1: Fondo blanco
            bg_layer = OverlayLayer(
                layer_type=OverlayType.BACKGROUND,
                z_order=self._z_manager.get_next_z_order(OverlayType.BACKGROUND),
                bbox=expanded_bbox,
                fill_color=(1, 1, 1),
                fill_opacity=1.0,
                source_span_id=overlay_info.original_span_id,
            )
            overlay_info.layers.append(bg_layer)
            self._z_manager.add_layer(bg_layer, overlay_info.page_num)
            
            # Capa 2: Texto nuevo
            text_layer = self._create_text_layer(overlay_info)
            overlay_info.layers.append(text_layer)
            self._z_manager.add_layer(text_layer, overlay_info.page_num)
            
        elif overlay_info.strategy == OverlayStrategy.TRANSPARENT_ERASE:
            # Capa 1: Redacción transparente
            erase_layer = OverlayLayer(
                layer_type=OverlayType.REDACTION,
                z_order=self._z_manager.get_next_z_order(OverlayType.REDACTION),
                bbox=expanded_bbox,
                fill_color=None,  # Transparente
                fill_opacity=0.0,
                source_span_id=overlay_info.original_span_id,
            )
            overlay_info.layers.append(erase_layer)
            self._z_manager.add_layer(erase_layer, overlay_info.page_num)
            
            # Capa 2: Texto nuevo
            text_layer = self._create_text_layer(overlay_info)
            overlay_info.layers.append(text_layer)
            self._z_manager.add_layer(text_layer, overlay_info.page_num)
            
        elif overlay_info.strategy == OverlayStrategy.DIRECT_OVERLAY:
            # Solo capa de texto (sin eliminar original)
            text_layer = self._create_text_layer(overlay_info)
            overlay_info.layers.append(text_layer)
            self._z_manager.add_layer(text_layer, overlay_info.page_num)
    
    def _create_text_layer(self, overlay_info: TextOverlayInfo) -> OverlayLayer:
        """
        Crea la capa de texto.
        
        Args:
            overlay_info: Información del overlay
            
        Returns:
            Capa de texto configurada
        """
        # Calcular posición según modo
        origin = self._calculate_text_origin(overlay_info)
        
        return OverlayLayer(
            layer_type=OverlayType.TEXT,
            z_order=self._z_manager.get_next_z_order(OverlayType.TEXT),
            bbox=overlay_info.original_bbox,
            origin=origin,
            content=overlay_info.new_text,
            font_name=overlay_info.new_font,
            font_size=overlay_info.new_size,
            color=overlay_info.new_color,
            source_span_id=overlay_info.original_span_id,
        )
    
    def _calculate_text_origin(self, overlay_info: TextOverlayInfo) -> Tuple[float, float]:
        """
        Calcula el punto de origen del texto según el modo.
        
        Args:
            overlay_info: Información del overlay
            
        Returns:
            Punto de origen (x, y)
        """
        bbox = overlay_info.original_bbox
        offset = overlay_info.position_offset
        
        if overlay_info.mode == RewriteMode.PRESERVE_POSITION:
            # Misma posición que el original
            return (bbox[0] + offset[0], bbox[3] + offset[1])  # x0, y1 (baseline)
            
        elif overlay_info.mode == RewriteMode.PRESERVE_BASELINE:
            # Mantener baseline, ajustar inicio
            return (bbox[0] + offset[0], bbox[3] + offset[1])
            
        elif overlay_info.mode == RewriteMode.CENTER_IN_BBOX:
            # Centrar en el bbox
            center_x = (bbox[0] + bbox[2]) / 2
            center_y = (bbox[1] + bbox[3]) / 2
            return (center_x + offset[0], center_y + offset[1])
            
        elif overlay_info.mode == RewriteMode.ADJUST_TO_FIT:
            # Similar a preserve pero permite ajustes
            return (bbox[0] + offset[0], bbox[3] + offset[1])
        
        return (bbox[0], bbox[3])
    
    def apply_overlay(
        self,
        overlay_info: TextOverlayInfo,
        page: Any,  # fitz.Page
        transform_rect_func: Optional[Callable] = None,
    ) -> RewriteResult:
        """
        Aplica un overlay a una página PDF.
        
        Args:
            overlay_info: Información del overlay
            page: Página PyMuPDF
            transform_rect_func: Función para transformar coordenadas
            
        Returns:
            Resultado de la operación
        """
        if not HAS_FITZ:
            result = RewriteResult(status=RewriteStatus.FAILED)
            result.add_error("PyMuPDF (fitz) no disponible")
            return result
        
        result = RewriteResult()
        result.overlay_info = overlay_info
        
        try:
            for layer in sorted(overlay_info.layers, key=lambda lyr: lyr.z_order):
                self._apply_layer(layer, page, result, transform_rect_func)
            
            overlay_info.applied = True
            result.status = RewriteStatus.SUCCESS
            result.message = f"Overlay aplicado exitosamente ({len(overlay_info.layers)} capas)"
            
        except Exception as e:
            result.add_error(f"Error aplicando overlay: {str(e)}")
        
        return result
    
    def _apply_layer(
        self,
        layer: OverlayLayer,
        page: Any,
        result: RewriteResult,
        transform_rect_func: Optional[Callable] = None,
    ) -> None:
        """
        Aplica una capa individual.
        
        Args:
            layer: Capa a aplicar
            page: Página PyMuPDF
            result: Resultado para actualizar
            transform_rect_func: Función de transformación
        """
        bbox = layer.bbox
        if transform_rect_func:
            bbox = transform_rect_func(bbox)
        
        rect = fitz.Rect(bbox)
        
        if layer.layer_type == OverlayType.REDACTION:
            # Aplicar redacción
            fill = layer.fill_color if layer.fill_color else False
            page.add_redact_annot(rect, fill=fill)
            page.apply_redactions()
            
        elif layer.layer_type == OverlayType.BACKGROUND:
            # Dibujar fondo
            shape = page.new_shape()
            shape.draw_rect(rect)
            shape.finish(
                color=layer.stroke_color,
                fill=layer.fill_color,
                fill_opacity=layer.fill_opacity,
                width=layer.stroke_width,
            )
            shape.commit(overlay=True)
            
        elif layer.layer_type == OverlayType.TEXT:
            # Insertar texto
            origin = layer.origin
            if transform_rect_func:
                # Transformar también el origen
                temp_rect = fitz.Rect(origin[0], origin[1], origin[0], origin[1])
                transformed = transform_rect_func((temp_rect.x0, temp_rect.y0, temp_rect.x1, temp_rect.y1))
                origin = (transformed[0], transformed[1])
            
            rc = page.insert_text(
                fitz.Point(origin),
                layer.content,
                fontname=layer.font_name,
                fontsize=layer.font_size,
                color=layer.color,
            )
            
            if rc < 0:
                result.add_warning(f"insert_text retornó {rc} para '{layer.content[:20]}...'")
    
    def rewrite_text(
        self,
        page: Any,  # fitz.Page
        page_num: int,
        original_text: str,
        original_bbox: Tuple[float, float, float, float],
        new_text: str,
        font_name: str = "Helvetica",
        font_size: float = 12.0,
        color: Tuple[float, float, float] = (0, 0, 0),
        strategy: Optional[OverlayStrategy] = None,
        mode: Optional[RewriteMode] = None,
        transform_rect_func: Optional[Callable] = None,
    ) -> RewriteResult:
        """
        Reescribe texto en una sola llamada.
        
        Combina prepare_rewrite y apply_overlay.
        
        Args:
            page: Página PyMuPDF
            page_num: Número de página
            original_text: Texto original
            original_bbox: Bounding box original
            new_text: Nuevo texto
            font_name: Nombre de fuente
            font_size: Tamaño de fuente
            color: Color RGB
            strategy: Estrategia de overlay
            mode: Modo de reescritura
            transform_rect_func: Función de transformación
            
        Returns:
            Resultado de la operación
        """
        overlay_info = self.prepare_rewrite(
            page_num=page_num,
            original_text=original_text,
            original_bbox=original_bbox,
            new_text=new_text,
            font_name=font_name,
            font_size=font_size,
            color=color,
            strategy=strategy,
            mode=mode,
        )
        
        return self.apply_overlay(overlay_info, page, transform_rect_func)
    
    def get_overlay(self, overlay_id: str) -> Optional[TextOverlayInfo]:
        """Obtiene un overlay por ID."""
        return self._overlays.get(overlay_id)
    
    def get_page_overlays(self, page_num: int) -> List[TextOverlayInfo]:
        """Obtiene los overlays de una página."""
        if page_num not in self._page_overlays:
            return []
        return [
            self._overlays[oid] 
            for oid in self._page_overlays[page_num] 
            if oid in self._overlays
        ]
    
    def remove_overlay(self, overlay_id: str) -> bool:
        """
        Elimina un overlay (no deshace cambios en PDF).
        
        Args:
            overlay_id: ID del overlay
            
        Returns:
            True si se eliminó
        """
        if overlay_id not in self._overlays:
            return False
        
        overlay = self._overlays[overlay_id]
        
        # Eliminar capas del z-manager
        for layer in overlay.layers:
            self._z_manager.remove_layer(layer.layer_id)
        
        # Eliminar de registros
        del self._overlays[overlay_id]
        
        for page_overlays in self._page_overlays.values():
            if overlay_id in page_overlays:
                page_overlays.remove(overlay_id)
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de uso."""
        total_overlays = len(self._overlays)
        applied = sum(1 for o in self._overlays.values() if o.applied)
        
        by_strategy = {}
        for overlay in self._overlays.values():
            strategy_name = overlay.strategy.name
            by_strategy[strategy_name] = by_strategy.get(strategy_name, 0) + 1
        
        return {
            'total_overlays': total_overlays,
            'applied': applied,
            'pending': total_overlays - applied,
            'by_strategy': by_strategy,
            'total_layers': len(self._z_manager._layers),
            'pages_affected': len(self._page_overlays),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            'config': {
                'default_strategy': self._config.default_strategy.name,
                'default_mode': self._config.default_mode.name,
                'auto_adjust_tracking': self._config.auto_adjust_tracking,
                'auto_adjust_size': self._config.auto_adjust_size,
                'allow_font_substitution': self._config.allow_font_substitution,
            },
            'overlays': {oid: o.to_dict() for oid, o in self._overlays.items()},
            'page_overlays': self._page_overlays,
            'z_manager': self._z_manager.to_dict(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SafeTextRewriter":
        """Crea desde diccionario."""
        config_data = data.get('config', {})
        
        strategy_name = config_data.get('default_strategy', 'REDACT_THEN_INSERT')
        mode_name = config_data.get('default_mode', 'PRESERVE_POSITION')
        
        config = RewriterConfig(
            default_strategy=OverlayStrategy[strategy_name] if strategy_name in OverlayStrategy.__members__ else OverlayStrategy.REDACT_THEN_INSERT,
            default_mode=RewriteMode[mode_name] if mode_name in RewriteMode.__members__ else RewriteMode.PRESERVE_POSITION,
            auto_adjust_tracking=config_data.get('auto_adjust_tracking', True),
            auto_adjust_size=config_data.get('auto_adjust_size', True),
            allow_font_substitution=config_data.get('allow_font_substitution', True),
        )
        
        rewriter = cls(config=config)
        
        # Restaurar overlays
        for oid, overlay_data in data.get('overlays', {}).items():
            rewriter._overlays[oid] = TextOverlayInfo.from_dict(overlay_data)
        
        rewriter._page_overlays = {
            int(k): v for k, v in data.get('page_overlays', {}).items()
        }
        
        # Restaurar z-manager
        if 'z_manager' in data:
            rewriter._z_manager = ZOrderManager.from_dict(data['z_manager'])
        
        return rewriter


# ================== Factory Functions ==================


def create_safe_rewriter(
    strategy: OverlayStrategy = OverlayStrategy.REDACT_THEN_INSERT,
    mode: RewriteMode = RewriteMode.PRESERVE_POSITION,
    **config_kwargs
) -> SafeTextRewriter:
    """
    Crea un SafeTextRewriter configurado.
    
    Args:
        strategy: Estrategia por defecto
        mode: Modo por defecto
        **config_kwargs: Opciones adicionales de configuración
        
    Returns:
        SafeTextRewriter configurado
    """
    config = RewriterConfig(
        default_strategy=strategy,
        default_mode=mode,
        **config_kwargs
    )
    return SafeTextRewriter(config=config)


def rewrite_text_safe(
    page: Any,
    page_num: int,
    original_text: str,
    original_bbox: Tuple[float, float, float, float],
    new_text: str,
    font_name: str = "Helvetica",
    font_size: float = 12.0,
    color: Tuple[float, float, float] = (0, 0, 0),
    strategy: OverlayStrategy = OverlayStrategy.REDACT_THEN_INSERT,
) -> RewriteResult:
    """
    Función conveniente para reescribir texto de forma segura.
    
    Crea un rewriter temporal y aplica el cambio.
    
    Args:
        page: Página PyMuPDF
        page_num: Número de página
        original_text: Texto original
        original_bbox: Bounding box original
        new_text: Nuevo texto
        font_name: Nombre de fuente
        font_size: Tamaño de fuente
        color: Color RGB
        strategy: Estrategia de overlay
        
    Returns:
        Resultado de la operación
    """
    rewriter = create_safe_rewriter(strategy=strategy)
    return rewriter.rewrite_text(
        page=page,
        page_num=page_num,
        original_text=original_text,
        original_bbox=original_bbox,
        new_text=new_text,
        font_name=font_name,
        font_size=font_size,
        color=color,
    )


def get_recommended_strategy(
    text_length_change: int,
    has_font_change: bool,
    pdf_has_signatures: bool = False,
) -> OverlayStrategy:
    """
    Recomienda una estrategia según las características del cambio.
    
    Args:
        text_length_change: Diferencia de longitud (nuevo - original)
        has_font_change: True si cambia la fuente
        pdf_has_signatures: True si el PDF tiene firmas digitales
        
    Returns:
        Estrategia recomendada
    """
    if pdf_has_signatures:
        # Con firmas, usar overlay directo para no invalidarlas
        return OverlayStrategy.DIRECT_OVERLAY
    
    if abs(text_length_change) <= 3 and not has_font_change:
        # Cambio pequeño: transparent erase es suficiente
        return OverlayStrategy.TRANSPARENT_ERASE
    
    if text_length_change > 10:
        # Texto más largo: fondo blanco más seguro
        return OverlayStrategy.WHITE_BACKGROUND
    
    # Por defecto: redact then insert
    return OverlayStrategy.REDACT_THEN_INSERT

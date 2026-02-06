"""
TextSelectionOverlay - Overlay de selección con visualización de métricas.

Este módulo proporciona un overlay visual para:
- Mostrar bounding boxes de spans/líneas seleccionados
- Visualizar baselines y métricas tipográficas
- Indicadores de espaciado (char_spacing, word_spacing)
- Soporte para multi-selección

Tarea 3C-04 del Phase 3 PDF Text Engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional, List, Dict, Any, Set

from PyQt5.QtWidgets import QGraphicsItem, QGraphicsRectItem, QGraphicsLineItem
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QObject
from PyQt5.QtGui import QPen, QBrush, QColor, QPainter

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QGraphicsScene


# ================== Enums y Configuración ==================


class SelectionMode(Enum):
    """Modo de selección de texto."""
    SPAN = "span"           # Selección de spans individuales
    LINE = "line"           # Selección de líneas completas
    PARAGRAPH = "paragraph" # Selección de párrafos
    CHARACTER = "character" # Selección a nivel de carácter


class MetricIndicator(Enum):
    """Tipos de indicadores de métricas."""
    BBOX = "bbox"               # Bounding box
    BASELINE = "baseline"       # Línea de base
    ASCENDER = "ascender"       # Línea de ascendentes
    DESCENDER = "descender"     # Línea de descendentes
    CHAR_SPACING = "char_spacing"   # Espaciado entre caracteres
    WORD_SPACING = "word_spacing"   # Espaciado entre palabras
    ORIGIN = "origin"           # Punto de origen


@dataclass
class SelectionStyle:
    """Estilo visual para la selección."""
    # Colores principales
    fill_color: QColor = field(default_factory=lambda: QColor(0, 120, 215, 60))
    stroke_color: QColor = field(default_factory=lambda: QColor(0, 120, 215, 200))
    stroke_width: float = 1.5
    
    # Colores para hover
    hover_fill_color: QColor = field(default_factory=lambda: QColor(0, 150, 255, 40))
    hover_stroke_color: QColor = field(default_factory=lambda: QColor(0, 150, 255, 180))
    
    # Colores para indicadores de métricas
    baseline_color: QColor = field(default_factory=lambda: QColor(255, 100, 100, 180))
    ascender_color: QColor = field(default_factory=lambda: QColor(100, 255, 100, 150))
    descender_color: QColor = field(default_factory=lambda: QColor(100, 100, 255, 150))
    spacing_color: QColor = field(default_factory=lambda: QColor(255, 200, 0, 150))
    origin_color: QColor = field(default_factory=lambda: QColor(255, 0, 255, 200))
    
    # Grosor de líneas de métricas
    metric_line_width: float = 1.0
    
    # Mostrar indicadores
    show_bbox: bool = True
    show_baseline: bool = True
    show_ascender: bool = False
    show_descender: bool = False
    show_char_spacing: bool = False
    show_word_spacing: bool = False
    show_origin: bool = False


@dataclass
class SelectionConfig:
    """Configuración del overlay de selección."""
    # Modo de selección
    mode: SelectionMode = SelectionMode.SPAN
    
    # Permitir multi-selección
    multi_select: bool = True
    
    # Estilo visual
    style: SelectionStyle = field(default_factory=SelectionStyle)
    
    # Escalado para zoom
    base_stroke_width: float = 1.5
    min_stroke_width: float = 0.5
    max_stroke_width: float = 4.0
    
    # Z-order
    z_value: float = 100.0


# ================== Clases de Items Gráficos ==================


class SpanSelectionItem(QGraphicsRectItem):
    """
    Item gráfico para visualizar un span seleccionado.
    
    Muestra el bounding box del span y opcionalmente métricas adicionales.
    """
    
    def __init__(
        self,
        span_data: Dict[str, Any],
        style: SelectionStyle,
        zoom: float = 1.0,
        parent: Optional[QGraphicsItem] = None
    ):
        """
        Inicializar item de selección de span.
        
        Args:
            span_data: Diccionario con datos del span (bbox, baseline_y, etc.)
            style: Estilo visual a aplicar
            zoom: Nivel de zoom actual
            parent: Item padre opcional
        """
        # Extraer bbox
        bbox = span_data.get('bbox', (0, 0, 0, 0))
        rect = QRectF(bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1])
        
        super().__init__(rect, parent)
        
        self._span_data = span_data
        self._style = style
        self._zoom = zoom
        self._is_hovered = False
        self._metric_items: List[QGraphicsItem] = []
        
        self._apply_style()
        self.setAcceptHoverEvents(True)
    
    def _apply_style(self) -> None:
        """Aplicar estilo visual."""
        if self._is_hovered:
            pen = QPen(self._style.hover_stroke_color, self._style.stroke_width)
            brush = QBrush(self._style.hover_fill_color)
        else:
            pen = QPen(self._style.stroke_color, self._style.stroke_width)
            brush = QBrush(self._style.fill_color)
        
        self.setPen(pen)
        self.setBrush(brush)
    
    @property
    def span_data(self) -> Dict[str, Any]:
        """Datos del span asociado."""
        return self._span_data
    
    @property
    def span_id(self) -> Optional[str]:
        """ID del span si está disponible."""
        return self._span_data.get('span_id')
    
    def set_hovered(self, hovered: bool) -> None:
        """Cambiar estado de hover."""
        if self._is_hovered != hovered:
            self._is_hovered = hovered
            self._apply_style()
            self.update()
    
    def hoverEnterEvent(self, event) -> None:
        """Manejar entrada de hover."""
        self.set_hovered(True)
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event) -> None:
        """Manejar salida de hover."""
        self.set_hovered(False)
        super().hoverLeaveEvent(event)
    
    def add_metric_items(self, scene: 'QGraphicsScene') -> None:
        """
        Añadir items de métricas a la escena.
        
        Args:
            scene: Escena donde añadir los items
        """
        self._clear_metric_items(scene)
        
        bbox = self._span_data.get('bbox', (0, 0, 0, 0))
        x0, y0, x1, y1 = bbox
        
        # Baseline
        if self._style.show_baseline:
            baseline_y = self._span_data.get('baseline_y')
            if baseline_y is not None:
                line = QGraphicsLineItem(x0, baseline_y, x1, baseline_y)
                pen = QPen(self._style.baseline_color, self._style.metric_line_width)
                pen.setStyle(Qt.DashLine)
                line.setPen(pen)
                line.setZValue(self.zValue() + 1)
                scene.addItem(line)
                self._metric_items.append(line)
        
        # Ascender line
        if self._style.show_ascender:
            ascender = self._span_data.get('ascender')
            baseline_y = self._span_data.get('baseline_y')
            if ascender is not None and baseline_y is not None:
                asc_y = baseline_y - ascender
                line = QGraphicsLineItem(x0, asc_y, x1, asc_y)
                pen = QPen(self._style.ascender_color, self._style.metric_line_width)
                pen.setStyle(Qt.DotLine)
                line.setPen(pen)
                line.setZValue(self.zValue() + 1)
                scene.addItem(line)
                self._metric_items.append(line)
        
        # Descender line
        if self._style.show_descender:
            descender = self._span_data.get('descender')
            baseline_y = self._span_data.get('baseline_y')
            if descender is not None and baseline_y is not None:
                desc_y = baseline_y + abs(descender)
                line = QGraphicsLineItem(x0, desc_y, x1, desc_y)
                pen = QPen(self._style.descender_color, self._style.metric_line_width)
                pen.setStyle(Qt.DotLine)
                line.setPen(pen)
                line.setZValue(self.zValue() + 1)
                scene.addItem(line)
                self._metric_items.append(line)
        
        # Origin point
        if self._style.show_origin:
            origin = self._span_data.get('origin')
            if origin:
                ox, oy = origin
                # Dibujar una pequeña cruz en el origen
                size = 4
                line_h = QGraphicsLineItem(ox - size, oy, ox + size, oy)
                line_v = QGraphicsLineItem(ox, oy - size, ox, oy + size)
                pen = QPen(self._style.origin_color, 2)
                line_h.setPen(pen)
                line_v.setPen(pen)
                line_h.setZValue(self.zValue() + 2)
                line_v.setZValue(self.zValue() + 2)
                scene.addItem(line_h)
                scene.addItem(line_v)
                self._metric_items.extend([line_h, line_v])
    
    def _clear_metric_items(self, scene: 'QGraphicsScene') -> None:
        """Eliminar items de métricas de la escena."""
        for item in self._metric_items:
            if scene:
                scene.removeItem(item)
        self._metric_items.clear()
    
    def cleanup(self, scene: 'QGraphicsScene') -> None:
        """Limpiar item y sus métricas de la escena."""
        self._clear_metric_items(scene)
        if scene:
            scene.removeItem(self)


class LineSelectionItem(QGraphicsRectItem):
    """
    Item gráfico para visualizar una línea seleccionada.
    
    Muestra el bounding box de la línea completa y opcionalmente
    los spans individuales y métricas de línea.
    """
    
    def __init__(
        self,
        line_data: Dict[str, Any],
        style: SelectionStyle,
        zoom: float = 1.0,
        parent: Optional[QGraphicsItem] = None
    ):
        """
        Inicializar item de selección de línea.
        
        Args:
            line_data: Diccionario con datos de la línea
            style: Estilo visual a aplicar
            zoom: Nivel de zoom actual
            parent: Item padre opcional
        """
        bbox = line_data.get('bbox', (0, 0, 0, 0))
        rect = QRectF(bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1])
        
        super().__init__(rect, parent)
        
        self._line_data = line_data
        self._style = style
        self._zoom = zoom
        self._is_hovered = False
        self._metric_items: List[QGraphicsItem] = []
        self._span_items: List[SpanSelectionItem] = []
        
        # Estilo de línea más sutil
        pen = QPen(self._style.stroke_color, self._style.stroke_width)
        pen.setStyle(Qt.DashDotLine)
        self.setPen(pen)
        self.setBrush(QBrush(Qt.NoBrush))  # Sin relleno para líneas
        
        self.setAcceptHoverEvents(True)
    
    @property
    def line_data(self) -> Dict[str, Any]:
        """Datos de la línea asociada."""
        return self._line_data
    
    @property
    def line_id(self) -> Optional[str]:
        """ID de la línea si está disponible."""
        return self._line_data.get('line_id')
    
    def set_hovered(self, hovered: bool) -> None:
        """Cambiar estado de hover."""
        if self._is_hovered != hovered:
            self._is_hovered = hovered
            self.update()
    
    def add_metric_items(self, scene: 'QGraphicsScene') -> None:
        """Añadir items de métricas a la escena."""
        self._clear_metric_items(scene)
        
        bbox = self._line_data.get('bbox', (0, 0, 0, 0))
        x0, y0, x1, y1 = bbox
        
        # Baseline de línea
        if self._style.show_baseline:
            baseline_y = self._line_data.get('baseline_y')
            if baseline_y is not None:
                line = QGraphicsLineItem(x0, baseline_y, x1, baseline_y)
                pen = QPen(self._style.baseline_color, self._style.metric_line_width + 0.5)
                pen.setStyle(Qt.SolidLine)
                line.setPen(pen)
                line.setZValue(self.zValue() + 1)
                scene.addItem(line)
                self._metric_items.append(line)
    
    def _clear_metric_items(self, scene: 'QGraphicsScene') -> None:
        """Eliminar items de métricas."""
        for item in self._metric_items:
            if scene:
                scene.removeItem(item)
        self._metric_items.clear()
    
    def cleanup(self, scene: 'QGraphicsScene') -> None:
        """Limpiar item y sus métricas."""
        self._clear_metric_items(scene)
        for span_item in self._span_items:
            span_item.cleanup(scene)
        self._span_items.clear()
        if scene:
            scene.removeItem(self)


class CharSpacingIndicator(QGraphicsItem):
    """
    Indicador visual de espaciado entre caracteres.
    
    Muestra pequeñas marcas entre caracteres para visualizar
    el char_spacing del span.
    """
    
    def __init__(
        self,
        positions: List[float],
        y: float,
        height: float,
        color: QColor,
        parent: Optional[QGraphicsItem] = None
    ):
        """
        Args:
            positions: Lista de posiciones X donde dibujar indicadores
            y: Posición Y base
            height: Altura de los indicadores
            color: Color de los indicadores
        """
        super().__init__(parent)
        self._positions = positions
        self._y = y
        self._height = height
        self._color = color
    
    def boundingRect(self) -> QRectF:
        """Calcular bounding rect."""
        if not self._positions:
            return QRectF()
        min_x = min(self._positions)
        max_x = max(self._positions)
        return QRectF(min_x - 2, self._y, max_x - min_x + 4, self._height)
    
    def paint(self, painter: QPainter, option, widget=None) -> None:
        """Dibujar indicadores."""
        painter.setPen(QPen(self._color, 1))
        for x in self._positions:
            painter.drawLine(
                QPointF(x, self._y),
                QPointF(x, self._y + self._height)
            )


# ================== Clase Principal de Overlay ==================


class TextSelectionOverlay(QObject):
    """
    Overlay de selección con visualización de métricas.
    
    Gestiona la selección visual de spans y líneas de texto,
    mostrando bounding boxes, baselines y otros indicadores.
    
    Signals:
        selectionChanged: Emitido cuando cambia la selección
        spanSelected: Emitido cuando se selecciona un span (dict)
        lineSelected: Emitido cuando se selecciona una línea (dict)
        metricsUpdated: Emitido cuando se actualizan las métricas mostradas
    """
    
    # Señales
    selectionChanged = pyqtSignal()
    spanSelected = pyqtSignal(object)  # Dict con datos del span
    lineSelected = pyqtSignal(object)  # Dict con datos de la línea
    metricsUpdated = pyqtSignal(list)  # Lista de métricas activas
    
    def __init__(
        self,
        scene: Optional['QGraphicsScene'] = None,
        config: Optional[SelectionConfig] = None,
        parent: Optional[QObject] = None
    ):
        """
        Inicializar overlay de selección.
        
        Args:
            scene: Escena donde dibujar (puede asignarse después)
            config: Configuración del overlay
            parent: Objeto padre
        """
        super().__init__(parent)
        
        self._scene = scene
        self._config = config or SelectionConfig()
        
        # Estado de selección
        self._selected_spans: Dict[str, SpanSelectionItem] = {}
        self._selected_lines: Dict[str, LineSelectionItem] = {}
        self._hover_item: Optional[QGraphicsItem] = None
        
        # Zoom actual
        self._zoom = 1.0
        
        # Habilitado
        self._enabled = True
    
    @property
    def scene(self) -> Optional['QGraphicsScene']:
        """Escena actual."""
        return self._scene
    
    @scene.setter
    def scene(self, value: 'QGraphicsScene') -> None:
        """Asignar escena."""
        if self._scene != value:
            self.clear_all()
            self._scene = value
    
    @property
    def config(self) -> SelectionConfig:
        """Configuración actual."""
        return self._config
    
    @property
    def enabled(self) -> bool:
        """Si el overlay está habilitado."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Habilitar/deshabilitar overlay."""
        if not value and self._enabled:
            self.clear_all()
        self._enabled = value
    
    @property
    def selection_mode(self) -> SelectionMode:
        """Modo de selección actual."""
        return self._config.mode
    
    @selection_mode.setter
    def selection_mode(self, mode: SelectionMode) -> None:
        """Cambiar modo de selección."""
        if self._config.mode != mode:
            self._config.mode = mode
            self.clear_all()
    
    @property
    def style(self) -> SelectionStyle:
        """Estilo visual actual."""
        return self._config.style
    
    @property
    def selected_span_ids(self) -> Set[str]:
        """IDs de spans seleccionados."""
        return set(self._selected_spans.keys())
    
    @property
    def selected_line_ids(self) -> Set[str]:
        """IDs de líneas seleccionadas."""
        return set(self._selected_lines.keys())
    
    @property
    def has_selection(self) -> bool:
        """True si hay algo seleccionado."""
        return bool(self._selected_spans or self._selected_lines)
    
    @property
    def selection_count(self) -> int:
        """Número de elementos seleccionados."""
        return len(self._selected_spans) + len(self._selected_lines)
    
    def set_zoom(self, zoom: float) -> None:
        """
        Actualizar nivel de zoom.
        
        Args:
            zoom: Nuevo nivel de zoom
        """
        self._zoom = max(0.1, zoom)
        # Actualizar grosor de líneas según zoom
        self._update_stroke_widths()
    
    def _update_stroke_widths(self) -> None:
        """Actualizar grosor de líneas según zoom."""
        # Calcular grosor ajustado
        base = self._config.base_stroke_width
        adjusted = base / self._zoom
        adjusted = max(self._config.min_stroke_width, 
                       min(adjusted, self._config.max_stroke_width))
        self._config.style.stroke_width = adjusted
    
    # ========== Métodos de Selección de Span ==========
    
    def select_span(
        self,
        span_data: Dict[str, Any],
        add_to_selection: bool = False
    ) -> bool:
        """
        Seleccionar un span.
        
        Args:
            span_data: Diccionario con datos del span (debe incluir bbox)
            add_to_selection: Si True, añade a la selección existente
            
        Returns:
            True si se seleccionó correctamente
        """
        if not self._enabled or not self._scene:
            return False
        
        span_id = span_data.get('span_id', f"span_{id(span_data)}")
        
        # Verificar si ya está seleccionado
        if span_id in self._selected_spans:
            return True
        
        # Limpiar selección previa si no es multi-select
        if not add_to_selection or not self._config.multi_select:
            self.clear_all()
        
        # Crear item de selección
        item = SpanSelectionItem(
            span_data=span_data,
            style=self._config.style,
            zoom=self._zoom
        )
        item.setZValue(self._config.z_value)
        
        # Añadir a la escena
        self._scene.addItem(item)
        self._selected_spans[span_id] = item
        
        # Añadir métricas si están habilitadas
        item.add_metric_items(self._scene)
        
        # Emitir señales
        self.spanSelected.emit(span_data)
        self.selectionChanged.emit()
        
        return True
    
    def deselect_span(self, span_id: str) -> bool:
        """
        Deseleccionar un span.
        
        Args:
            span_id: ID del span a deseleccionar
            
        Returns:
            True si se deseleccionó
        """
        if span_id not in self._selected_spans:
            return False
        
        item = self._selected_spans.pop(span_id)
        item.cleanup(self._scene)
        
        self.selectionChanged.emit()
        return True
    
    def toggle_span_selection(self, span_data: Dict[str, Any]) -> bool:
        """
        Alternar selección de un span.
        
        Args:
            span_data: Datos del span
            
        Returns:
            True si quedó seleccionado, False si se deseleccionó
        """
        span_id = span_data.get('span_id', f"span_{id(span_data)}")
        
        if span_id in self._selected_spans:
            self.deselect_span(span_id)
            return False
        else:
            self.select_span(span_data, add_to_selection=True)
            return True
    
    def select_spans(self, spans_data: List[Dict[str, Any]]) -> int:
        """
        Seleccionar múltiples spans.
        
        Args:
            spans_data: Lista de diccionarios con datos de spans
            
        Returns:
            Número de spans seleccionados
        """
        self.clear_all()
        count = 0
        for span_data in spans_data:
            if self.select_span(span_data, add_to_selection=True):
                count += 1
        return count
    
    # ========== Métodos de Selección de Línea ==========
    
    def select_line(
        self,
        line_data: Dict[str, Any],
        add_to_selection: bool = False
    ) -> bool:
        """
        Seleccionar una línea.
        
        Args:
            line_data: Diccionario con datos de la línea
            add_to_selection: Si True, añade a la selección existente
            
        Returns:
            True si se seleccionó correctamente
        """
        if not self._enabled or not self._scene:
            return False
        
        line_id = line_data.get('line_id', f"line_{id(line_data)}")
        
        if line_id in self._selected_lines:
            return True
        
        if not add_to_selection or not self._config.multi_select:
            self.clear_all()
        
        item = LineSelectionItem(
            line_data=line_data,
            style=self._config.style,
            zoom=self._zoom
        )
        item.setZValue(self._config.z_value - 1)  # Debajo de spans
        
        self._scene.addItem(item)
        self._selected_lines[line_id] = item
        
        item.add_metric_items(self._scene)
        
        self.lineSelected.emit(line_data)
        self.selectionChanged.emit()
        
        return True
    
    def deselect_line(self, line_id: str) -> bool:
        """Deseleccionar una línea."""
        if line_id not in self._selected_lines:
            return False
        
        item = self._selected_lines.pop(line_id)
        item.cleanup(self._scene)
        
        self.selectionChanged.emit()
        return True
    
    # ========== Métodos de Hover ==========
    
    def set_hover_span(self, span_data: Optional[Dict[str, Any]]) -> None:
        """
        Establecer span bajo hover.
        
        Args:
            span_data: Datos del span o None para limpiar
        """
        if not self._enabled:
            return
        
        # Limpiar hover anterior
        if self._hover_item and self._scene:
            if isinstance(self._hover_item, (SpanSelectionItem, LineSelectionItem)):
                self._hover_item.cleanup(self._scene)
            self._hover_item = None
        
        if not span_data or not self._scene:
            return
        
        # No mostrar hover si ya está seleccionado
        span_id = span_data.get('span_id', '')
        if span_id in self._selected_spans:
            return
        
        # Crear item de hover
        item = SpanSelectionItem(
            span_data=span_data,
            style=self._config.style,
            zoom=self._zoom
        )
        item.set_hovered(True)
        item.setZValue(self._config.z_value - 0.5)
        
        self._scene.addItem(item)
        self._hover_item = item
    
    def clear_hover(self) -> None:
        """Limpiar hover actual."""
        if self._hover_item and self._scene:
            if isinstance(self._hover_item, (SpanSelectionItem, LineSelectionItem)):
                self._hover_item.cleanup(self._scene)
            self._hover_item = None
    
    # ========== Métodos de Limpieza ==========
    
    def clear_spans(self) -> None:
        """Limpiar todos los spans seleccionados."""
        for span_id in list(self._selected_spans.keys()):
            self.deselect_span(span_id)
    
    def clear_lines(self) -> None:
        """Limpiar todas las líneas seleccionadas."""
        for line_id in list(self._selected_lines.keys()):
            self.deselect_line(line_id)
    
    def clear_all(self) -> None:
        """Limpiar toda la selección y hover."""
        self.clear_hover()
        self.clear_spans()
        self.clear_lines()
    
    # ========== Métodos de Configuración de Métricas ==========
    
    def set_metric_visibility(
        self,
        metric: MetricIndicator,
        visible: bool
    ) -> None:
        """
        Establecer visibilidad de un indicador de métrica.
        
        Args:
            metric: Tipo de métrica
            visible: Si debe ser visible
        """
        style = self._config.style
        
        if metric == MetricIndicator.BBOX:
            style.show_bbox = visible
        elif metric == MetricIndicator.BASELINE:
            style.show_baseline = visible
        elif metric == MetricIndicator.ASCENDER:
            style.show_ascender = visible
        elif metric == MetricIndicator.DESCENDER:
            style.show_descender = visible
        elif metric == MetricIndicator.CHAR_SPACING:
            style.show_char_spacing = visible
        elif metric == MetricIndicator.WORD_SPACING:
            style.show_word_spacing = visible
        elif metric == MetricIndicator.ORIGIN:
            style.show_origin = visible
        
        # Actualizar items existentes
        self._refresh_metric_items()
    
    def set_metrics_preset(self, preset: str) -> None:
        """
        Aplicar un preset de métricas.
        
        Args:
            preset: Nombre del preset ('minimal', 'standard', 'detailed', 'all')
        """
        style = self._config.style
        
        if preset == 'minimal':
            style.show_bbox = True
            style.show_baseline = False
            style.show_ascender = False
            style.show_descender = False
            style.show_char_spacing = False
            style.show_word_spacing = False
            style.show_origin = False
        elif preset == 'standard':
            style.show_bbox = True
            style.show_baseline = True
            style.show_ascender = False
            style.show_descender = False
            style.show_char_spacing = False
            style.show_word_spacing = False
            style.show_origin = False
        elif preset == 'detailed':
            style.show_bbox = True
            style.show_baseline = True
            style.show_ascender = True
            style.show_descender = True
            style.show_char_spacing = False
            style.show_word_spacing = False
            style.show_origin = True
        elif preset == 'all':
            style.show_bbox = True
            style.show_baseline = True
            style.show_ascender = True
            style.show_descender = True
            style.show_char_spacing = True
            style.show_word_spacing = True
            style.show_origin = True
        
        self._refresh_metric_items()
        self.metricsUpdated.emit(self.get_active_metrics())
    
    def get_active_metrics(self) -> List[MetricIndicator]:
        """Obtener lista de métricas activas."""
        style = self._config.style
        active = []
        
        if style.show_bbox:
            active.append(MetricIndicator.BBOX)
        if style.show_baseline:
            active.append(MetricIndicator.BASELINE)
        if style.show_ascender:
            active.append(MetricIndicator.ASCENDER)
        if style.show_descender:
            active.append(MetricIndicator.DESCENDER)
        if style.show_char_spacing:
            active.append(MetricIndicator.CHAR_SPACING)
        if style.show_word_spacing:
            active.append(MetricIndicator.WORD_SPACING)
        if style.show_origin:
            active.append(MetricIndicator.ORIGIN)
        
        return active
    
    def _refresh_metric_items(self) -> None:
        """Refrescar items de métricas."""
        if not self._scene:
            return
        
        for item in self._selected_spans.values():
            item.add_metric_items(self._scene)
        
        for item in self._selected_lines.values():
            item.add_metric_items(self._scene)
    
    # ========== Métodos de Consulta ==========
    
    def get_selected_spans_data(self) -> List[Dict[str, Any]]:
        """Obtener datos de todos los spans seleccionados."""
        return [item.span_data for item in self._selected_spans.values()]
    
    def get_selected_lines_data(self) -> List[Dict[str, Any]]:
        """Obtener datos de todas las líneas seleccionadas."""
        return [item.line_data for item in self._selected_lines.values()]
    
    def get_selection_bounds(self) -> Optional[QRectF]:
        """
        Obtener bounding box de toda la selección.
        
        Returns:
            QRectF combinando todos los elementos o None si no hay selección
        """
        rects = []
        
        for item in self._selected_spans.values():
            rects.append(item.rect())
        
        for item in self._selected_lines.values():
            rects.append(item.rect())
        
        if not rects:
            return None
        
        result = rects[0]
        for rect in rects[1:]:
            result = result.united(rect)
        
        return result
    
    def is_span_selected(self, span_id: str) -> bool:
        """Verificar si un span está seleccionado."""
        return span_id in self._selected_spans
    
    def is_line_selected(self, line_id: str) -> bool:
        """Verificar si una línea está seleccionada."""
        return line_id in self._selected_lines


# ================== Factory Functions ==================


def create_selection_overlay(
    scene: Optional['QGraphicsScene'] = None,
    mode: SelectionMode = SelectionMode.SPAN,
    multi_select: bool = True,
    preset: str = 'standard'
) -> TextSelectionOverlay:
    """
    Crear un overlay de selección con configuración predefinida.
    
    Args:
        scene: Escena donde dibujar
        mode: Modo de selección inicial
        multi_select: Permitir multi-selección
        preset: Preset de métricas ('minimal', 'standard', 'detailed', 'all')
        
    Returns:
        TextSelectionOverlay configurado
    """
    config = SelectionConfig(
        mode=mode,
        multi_select=multi_select
    )
    
    overlay = TextSelectionOverlay(scene=scene, config=config)
    overlay.set_metrics_preset(preset)
    
    return overlay


def create_dark_theme_style() -> SelectionStyle:
    """Crear estilo para tema oscuro."""
    return SelectionStyle(
        fill_color=QColor(0, 150, 255, 50),
        stroke_color=QColor(0, 180, 255, 200),
        hover_fill_color=QColor(0, 180, 255, 30),
        hover_stroke_color=QColor(0, 200, 255, 160),
        baseline_color=QColor(255, 120, 120, 200),
        ascender_color=QColor(120, 255, 120, 180),
        descender_color=QColor(120, 120, 255, 180),
        spacing_color=QColor(255, 220, 0, 180),
        origin_color=QColor(255, 0, 255, 220),
    )


def create_light_theme_style() -> SelectionStyle:
    """Crear estilo para tema claro."""
    return SelectionStyle(
        fill_color=QColor(0, 100, 200, 40),
        stroke_color=QColor(0, 80, 180, 180),
        hover_fill_color=QColor(0, 120, 220, 25),
        hover_stroke_color=QColor(0, 100, 200, 150),
        baseline_color=QColor(220, 80, 80, 180),
        ascender_color=QColor(80, 180, 80, 150),
        descender_color=QColor(80, 80, 200, 150),
        spacing_color=QColor(220, 180, 0, 150),
        origin_color=QColor(200, 0, 200, 200),
    )

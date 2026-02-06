"""
TextPropertiesTooltip - Tooltip de propiedades tipográficas de texto PDF.

PHASE3-3C03: Tooltip de propiedades al hover

Muestra un tooltip con información tipográfica cuando el cursor
está sobre texto en el visor de PDF.

Funcionalidades:
- Formateo de propiedades de span para mostrar en tooltip
- Estilos configurables (compacto, detallado)
- Integración con PDFPageView vía señales
- Soporte para temas claro/oscuro

Propiedades mostradas:
- Fuente: nombre, tamaño, estilos
- Color: fill color
- Espaciado: Tc (char spacing), Tw (word spacing)
- Estado: embedding, fallback
- Texto: preview del contenido
"""

from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

from PyQt5.QtWidgets import QWidget, QToolTip
from PyQt5.QtCore import QPoint, QTimer

import logging

logger = logging.getLogger(__name__)

# Type checking imports
if TYPE_CHECKING:
    from core.text_engine import TextSpanMetrics, TextLine

# Runtime imports
try:
    from core.text_engine import (
        TextSpanMetrics as _TextSpanMetrics,
        TextLine as _TextLine,
        FontEmbeddingStatus,
    )
    TEXT_ENGINE_AVAILABLE = True
except ImportError:
    TEXT_ENGINE_AVAILABLE = False
    _TextSpanMetrics = None
    _TextLine = None
    FontEmbeddingStatus = None  # type: ignore


class TooltipStyle(Enum):
    """Estilos de tooltip disponibles."""
    COMPACT = "compact"      # Solo información esencial
    STANDARD = "standard"    # Información básica
    DETAILED = "detailed"    # Toda la información disponible


@dataclass
class TooltipConfig:
    """Configuración del tooltip de propiedades."""
    style: TooltipStyle = TooltipStyle.STANDARD
    show_delay_ms: int = 300  # Retraso antes de mostrar
    hide_delay_ms: int = 100  # Retraso antes de ocultar
    max_text_preview: int = 30  # Máximo de caracteres de preview
    show_color_swatch: bool = True  # Mostrar cuadro de color
    show_spacing: bool = True  # Mostrar espaciado Tc/Tw
    show_embedding: bool = True  # Mostrar estado de embedding
    show_geometry: bool = False  # Mostrar bbox y baseline
    dark_theme: bool = True  # Usar tema oscuro


def format_span_tooltip(
    span: 'TextSpanMetrics',
    config: Optional[TooltipConfig] = None
) -> str:
    """
    Formatea la información de un span para mostrar en tooltip.
    
    Args:
        span: TextSpanMetrics con la información del texto
        config: Configuración del tooltip
        
    Returns:
        HTML formateado para el tooltip
    """
    if not span or not TEXT_ENGINE_AVAILABLE:
        return ""
    
    if config is None:
        config = TooltipConfig()
    
    lines: List[str] = []
    
    # Estilo base según tema
    bg_color = "#2d2d2d" if config.dark_theme else "#ffffff"
    text_color = "#e0e0e0" if config.dark_theme else "#333333"
    label_color = "#a0a0a0" if config.dark_theme else "#666666"
    accent_color = "#4a9eff" if config.dark_theme else "#0066cc"
    
    # Inicio del HTML
    lines.append(f'<div style="background-color:{bg_color}; padding:6px 8px; '
                 f'border-radius:4px; font-size:11px; color:{text_color};">')
    
    # Preview del texto
    text_preview = span.text
    if len(text_preview) > config.max_text_preview:
        text_preview = text_preview[:config.max_text_preview] + "…"
    
    lines.append(f'<div style="font-weight:bold; margin-bottom:4px; '
                 f'color:{accent_color};">"{_escape_html(text_preview)}"</div>')
    
    # Tabla de propiedades
    lines.append('<table style="border-collapse:collapse;">')
    
    # --- Fuente ---
    font_name = span.font_name or "Desconocida"
    font_size = span.font_size or 12.0
    
    # Estilos inferidos
    styles = []
    if span.is_bold:
        styles.append("Bold")
    if span.is_italic:
        styles.append("Italic")
    style_str = ", ".join(styles) if styles else "Regular"
    
    lines.append(_tooltip_row("Fuente", f"{font_name}", label_color))
    lines.append(_tooltip_row("Tamaño", f"{font_size:.1f} pt", label_color))
    lines.append(_tooltip_row("Estilo", style_str, label_color))
    
    # --- Color ---
    if config.show_color_swatch:
        fill_color = span.fill_color or "#000000"
        color_swatch = (f'<span style="background-color:{fill_color}; '
                       f'width:12px; height:12px; display:inline-block; '
                       f'border:1px solid #666; vertical-align:middle;"></span>')
        lines.append(_tooltip_row("Color", f"{color_swatch} {fill_color}", label_color))
    
    # --- Espaciado (Standard y Detailed) ---
    if config.show_spacing and config.style != TooltipStyle.COMPACT:
        tc = span.char_spacing if hasattr(span, 'char_spacing') else 0.0
        tw = span.word_spacing if hasattr(span, 'word_spacing') else 0.0
        
        if tc != 0 or tw != 0 or config.style == TooltipStyle.DETAILED:
            if tc != 0:
                lines.append(_tooltip_row("Tc (char)", f"{tc:.2f} pt", label_color))
            if tw != 0:
                lines.append(_tooltip_row("Tw (word)", f"{tw:.2f} pt", label_color))
    
    # --- Embedding (Standard y Detailed) ---
    if config.show_embedding and config.style != TooltipStyle.COMPACT:
        embedding = span.embedding_status if hasattr(span, 'embedding_status') else None
        if embedding and TEXT_ENGINE_AVAILABLE:
            embedding_text = _format_embedding_status(embedding)
            lines.append(_tooltip_row("Embedding", embedding_text, label_color))
    
    # --- Geometría (Solo Detailed) ---
    if config.show_geometry and config.style == TooltipStyle.DETAILED:
        if hasattr(span, 'bbox') and span.bbox:
            bbox = span.bbox
            bbox_str = f"({bbox[0]:.1f}, {bbox[1]:.1f}, {bbox[2]:.1f}, {bbox[3]:.1f})"
            lines.append(_tooltip_row("BBox", bbox_str, label_color))
        
        if hasattr(span, 'baseline_y') and span.baseline_y:
            lines.append(_tooltip_row("Baseline", f"{span.baseline_y:.1f}", label_color))
    
    # --- Fallback (si aplica) ---
    if hasattr(span, 'was_fallback') and span.was_fallback:
        fallback_from = span.fallback_from or "original"
        lines.append(_tooltip_row("Fallback", f"de {fallback_from}", label_color))
    
    lines.append('</table>')
    lines.append('</div>')
    
    return "\n".join(lines)


def format_line_tooltip(
    line: 'TextLine',
    config: Optional[TooltipConfig] = None
) -> str:
    """
    Formatea la información de una línea para mostrar en tooltip.
    
    Args:
        line: TextLine con la información de la línea
        config: Configuración del tooltip
        
    Returns:
        HTML formateado para el tooltip
    """
    if not line or not TEXT_ENGINE_AVAILABLE:
        return ""
    
    if config is None:
        config = TooltipConfig()
    
    lines: List[str] = []
    
    # Estilo base según tema
    bg_color = "#2d2d2d" if config.dark_theme else "#ffffff"
    text_color = "#e0e0e0" if config.dark_theme else "#333333"
    label_color = "#a0a0a0" if config.dark_theme else "#666666"
    accent_color = "#4a9eff" if config.dark_theme else "#0066cc"
    
    lines.append(f'<div style="background-color:{bg_color}; padding:6px 8px; '
                 f'border-radius:4px; font-size:11px; color:{text_color};">')
    
    # Preview del texto
    text_preview = line.text
    if len(text_preview) > config.max_text_preview:
        text_preview = text_preview[:config.max_text_preview] + "…"
    
    lines.append(f'<div style="font-weight:bold; margin-bottom:4px; '
                 f'color:{accent_color};">"{_escape_html(text_preview)}"</div>')
    
    lines.append('<table style="border-collapse:collapse;">')
    
    # Información de la línea
    lines.append(_tooltip_row("Tipo", "Línea", label_color))
    lines.append(_tooltip_row("Spans", str(line.span_count), label_color))
    lines.append(_tooltip_row("Caracteres", str(line.char_count), label_color))
    
    # Fuente dominante
    if hasattr(line, 'dominant_font'):
        lines.append(_tooltip_row("Fuente", line.dominant_font, label_color))
    if hasattr(line, 'dominant_font_size'):
        lines.append(_tooltip_row("Tamaño", f"{line.dominant_font_size:.1f} pt", label_color))
    
    lines.append('</table>')
    lines.append('</div>')
    
    return "\n".join(lines)


def _tooltip_row(label: str, value: str, label_color: str) -> str:
    """Genera una fila de la tabla del tooltip."""
    return (f'<tr>'
            f'<td style="color:{label_color}; padding-right:8px; '
            f'white-space:nowrap;">{label}:</td>'
            f'<td style="font-family:monospace;">{value}</td>'
            f'</tr>')


def _escape_html(text: str) -> str:
    """Escapa caracteres HTML especiales."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _format_embedding_status(status) -> str:
    """Formatea el estado de embedding."""
    if not TEXT_ENGINE_AVAILABLE or status is None:
        return "Desconocido"
    
    try:
        if status == FontEmbeddingStatus.FULLY_EMBEDDED:
            return "✓ Embebida"
        elif status == FontEmbeddingStatus.SUBSET:
            return "⊂ Subset"
        elif status == FontEmbeddingStatus.NOT_EMBEDDED:
            return "✗ No embebida"
        else:
            return "? Desconocido"
    except Exception:
        return str(status)


class TextPropertiesTooltip:
    """
    Manejador de tooltip de propiedades de texto para PDFPageView.
    
    Uso:
        tooltip = TextPropertiesTooltip(viewer)
        viewer.spanHovered.connect(tooltip.on_span_hovered)
    """
    
    def __init__(
        self,
        parent: QWidget,
        config: Optional[TooltipConfig] = None
    ):
        """
        Inicializa el manejador de tooltip.
        
        Args:
            parent: Widget padre (generalmente PDFPageView)
            config: Configuración del tooltip
        """
        self._parent = parent
        self._config = config or TooltipConfig()
        
        # Estado
        self._current_span: Optional['TextSpanMetrics'] = None
        self._tooltip_visible = False
        self._enabled = True
        
        # Timer para delay de mostrar
        self._show_timer = QTimer()
        self._show_timer.setSingleShot(True)
        self._show_timer.timeout.connect(self._show_tooltip)
        
        # Timer para ocultar
        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide_tooltip)
        
        # Posición del cursor
        self._cursor_pos: Optional[QPoint] = None
    
    @property
    def enabled(self) -> bool:
        """Si el tooltip está habilitado."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        """Habilita/deshabilita el tooltip."""
        self._enabled = value
        if not value:
            self._hide_tooltip()
    
    @property
    def config(self) -> TooltipConfig:
        """Obtiene la configuración actual."""
        return self._config
    
    @config.setter
    def config(self, value: TooltipConfig):
        """Establece nueva configuración."""
        self._config = value
    
    def set_style(self, style: TooltipStyle) -> None:
        """Cambia el estilo del tooltip."""
        self._config.style = style
    
    def on_span_hovered(self, span: Optional['TextSpanMetrics']) -> None:
        """
        Callback cuando el cursor está sobre un span.
        
        Args:
            span: TextSpanMetrics o None si no hay span bajo el cursor
        """
        if not self._enabled:
            return
        
        # Cancelar timers pendientes
        self._show_timer.stop()
        self._hide_timer.stop()
        
        if span is None:
            # Ocultar tooltip con delay
            if self._tooltip_visible:
                self._hide_timer.start(self._config.hide_delay_ms)
            self._current_span = None
            return
        
        # Nuevo span
        self._current_span = span
        
        # Actualizar posición del cursor
        if self._parent:
            self._cursor_pos = self._parent.mapFromGlobal(
                self._parent.cursor().pos()
            )
        
        # Mostrar tooltip con delay
        self._show_timer.start(self._config.show_delay_ms)
    
    def on_line_hovered(self, line: Optional['TextLine']) -> None:
        """
        Callback cuando el cursor está sobre una línea.
        
        Args:
            line: TextLine o None
        """
        if not self._enabled or line is None:
            return
        
        # Similar a span pero con formato de línea
        # Generalmente no mostramos tooltip solo para líneas
        # a menos que sea modo detallado
        if self._config.style == TooltipStyle.DETAILED:
            # Solo mostrar si no hay span específico
            if self._current_span is None:
                self._show_line_tooltip(line)
    
    def _show_tooltip(self) -> None:
        """Muestra el tooltip con la información del span actual."""
        if self._current_span is None or not self._parent:
            return
        
        # Generar HTML del tooltip
        html = format_span_tooltip(self._current_span, self._config)
        
        if not html:
            return
        
        # Calcular posición (un poco debajo y a la derecha del cursor)
        if self._cursor_pos:
            pos = self._parent.mapToGlobal(
                self._cursor_pos + QPoint(15, 15)
            )
        else:
            pos = self._parent.mapToGlobal(
                self._parent.cursor().pos() + QPoint(15, 15)
            )
        
        # Mostrar tooltip
        QToolTip.showText(pos, html, self._parent)
        self._tooltip_visible = True
    
    def _show_line_tooltip(self, line: 'TextLine') -> None:
        """Muestra el tooltip con información de línea."""
        if line is None or not self._parent:
            return
        
        html = format_line_tooltip(line, self._config)
        
        if not html:
            return
        
        pos = self._parent.mapToGlobal(
            self._parent.cursor().pos() + QPoint(15, 15)
        )
        
        QToolTip.showText(pos, html, self._parent)
        self._tooltip_visible = True
    
    def _hide_tooltip(self) -> None:
        """Oculta el tooltip."""
        QToolTip.hideText()
        self._tooltip_visible = False
    
    def show_immediately(self, span: 'TextSpanMetrics', pos: QPoint) -> None:
        """
        Muestra el tooltip inmediatamente sin delay.
        
        Args:
            span: Span a mostrar
            pos: Posición global donde mostrar
        """
        if not self._enabled:
            return
        
        html = format_span_tooltip(span, self._config)
        if html:
            QToolTip.showText(pos, html, self._parent)
            self._tooltip_visible = True
    
    def hide(self) -> None:
        """Oculta el tooltip inmediatamente."""
        self._show_timer.stop()
        self._hide_timer.stop()
        self._hide_tooltip()
        self._current_span = None
    
    def update_config(self, **kwargs) -> None:
        """
        Actualiza configuración individualmente.
        
        Args:
            **kwargs: Atributos de TooltipConfig a actualizar
        """
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)


def create_text_properties_tooltip(
    parent: QWidget,
    style: TooltipStyle = TooltipStyle.STANDARD,
    dark_theme: bool = True
) -> TextPropertiesTooltip:
    """
    Función de fábrica para crear un TextPropertiesTooltip.
    
    Args:
        parent: Widget padre
        style: Estilo del tooltip
        dark_theme: Si usar tema oscuro
        
    Returns:
        TextPropertiesTooltip configurado
    """
    config = TooltipConfig(
        style=style,
        dark_theme=dark_theme,
    )
    return TextPropertiesTooltip(parent, config)

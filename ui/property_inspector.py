"""
PropertyInspector - Panel de propiedades tipográficas del texto PDF

PHASE3-3C01: Property Inspector Widget

Muestra todas las propiedades extraídas de un span/línea/párrafo de texto:
- Fuente: nombre, tamaño, estilos, embedding status
- Color: fill, stroke
- Espaciado: char spacing (Tc), word spacing (Tw), leading
- Geometría: bbox, baseline, origin
- Transformación: matriz, rotación, escala horizontal
- Metadatos: confianza, fallback info

Diseño: Panel colapsable con secciones organizadas

Integración:
- Se actualiza cuando el usuario selecciona texto en PDFPageView
- Emite señales cuando se modifican propiedades (para edición futura)
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QScrollArea, QToolButton,
    QApplication,
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize

import logging

logger = logging.getLogger(__name__)

# Try to import text_engine components
try:
    from core.text_engine import (
        TextSpanMetrics,
        TextLine,
        TextParagraph,
    )
    TEXT_ENGINE_AVAILABLE = True
except ImportError:
    TEXT_ENGINE_AVAILABLE = False
    TextSpanMetrics = None
    TextLine = None
    TextParagraph = None

# Import font_manager components
FONT_MANAGER_AVAILABLE = True  # Simplified check


class PropertyType(Enum):
    """Tipos de propiedades para categorización."""
    FONT = "font"
    COLOR = "color"
    SPACING = "spacing"
    GEOMETRY = "geometry"
    TRANSFORM = "transform"
    METADATA = "metadata"


@dataclass
class Property:
    """Representa una propiedad individual a mostrar."""
    name: str
    value: Any
    unit: str = ""
    category: PropertyType = PropertyType.METADATA
    editable: bool = False
    tooltip: str = ""
    
    def formatted_value(self) -> str:
        """Retorna el valor formateado para mostrar."""
        if self.value is None:
            return "—"
        if isinstance(self.value, bool):
            return "Sí" if self.value else "No"
        if isinstance(self.value, float):
            # Formatear con precisión adecuada
            if abs(self.value) < 0.001:
                return f"{self.value:.6f}"
            elif abs(self.value) < 1:
                return f"{self.value:.4f}"
            elif abs(self.value) < 100:
                return f"{self.value:.2f}"
            else:
                return f"{self.value:.1f}"
        if isinstance(self.value, (list, tuple)):
            if len(self.value) == 4:  # bbox
                return f"({self.value[0]:.1f}, {self.value[1]:.1f}, {self.value[2]:.1f}, {self.value[3]:.1f})"
            elif len(self.value) == 2:  # point
                return f"({self.value[0]:.1f}, {self.value[1]:.1f})"
            elif len(self.value) == 6:  # matrix
                return f"[{', '.join(f'{v:.3f}' for v in self.value)}]"
            return str(self.value)
        return str(self.value)


class CollapsibleSection(QWidget):
    """Sección colapsable para agrupar propiedades."""
    
    toggled = pyqtSignal(bool)
    
    def __init__(
        self,
        title: str,
        parent: Optional[QWidget] = None,
        collapsed: bool = False
    ):
        super().__init__(parent)
        self._collapsed = collapsed
        self._title = title
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura la UI de la sección."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header con botón de colapso
        self._header = QFrame()
        self._header.setStyleSheet("""
            QFrame {
                background-color: #3c3c3c;
                border: none;
                border-radius: 4px;
            }
        """)
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        
        # Botón de toggle
        self._toggle_btn = QToolButton()
        self._toggle_btn.setArrowType(
            Qt.RightArrow if self._collapsed else Qt.DownArrow
        )
        self._toggle_btn.setStyleSheet("""
            QToolButton {
                border: none;
                background: transparent;
                color: #cccccc;
            }
        """)
        self._toggle_btn.setFixedSize(16, 16)
        self._toggle_btn.clicked.connect(self._toggle)
        header_layout.addWidget(self._toggle_btn)
        
        # Título
        self._title_label = QLabel(self._title)
        self._title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()
        
        self._header.setCursor(Qt.PointingHandCursor)
        self._header.mousePressEvent = lambda e: self._toggle()
        
        layout.addWidget(self._header)
        
        # Container para contenido
        self._content = QFrame()
        self._content.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: none;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
            }
        """)
        self._content_layout = QGridLayout(self._content)
        self._content_layout.setContentsMargins(12, 8, 12, 8)
        self._content_layout.setSpacing(6)
        self._content_layout.setColumnStretch(1, 1)
        
        layout.addWidget(self._content)
        
        # Estado inicial
        self._content.setVisible(not self._collapsed)
    
    def _toggle(self):
        """Toggle estado colapsado."""
        self._collapsed = not self._collapsed
        self._content.setVisible(not self._collapsed)
        self._toggle_btn.setArrowType(
            Qt.RightArrow if self._collapsed else Qt.DownArrow
        )
        self.toggled.emit(self._collapsed)
    
    def add_property(self, prop: Property, row: int) -> QLabel:
        """
        Añade una propiedad a la sección.
        
        Args:
            prop: Property a mostrar
            row: Fila en el grid
            
        Returns:
            QLabel del valor (para actualización posterior)
        """
        # Label del nombre
        name_label = QLabel(prop.name + ":")
        name_label.setStyleSheet("""
            QLabel {
                color: #a0a0a0;
                font-size: 10px;
            }
        """)
        if prop.tooltip:
            name_label.setToolTip(prop.tooltip)
        
        # Label del valor
        value_text = prop.formatted_value()
        if prop.unit:
            value_text += f" {prop.unit}"
        
        value_label = QLabel(value_text)
        value_label.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 10px;
                font-family: monospace;
            }
        """)
        value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        if prop.tooltip:
            value_label.setToolTip(prop.tooltip)
        
        self._content_layout.addWidget(name_label, row, 0, Qt.AlignLeft | Qt.AlignTop)
        self._content_layout.addWidget(value_label, row, 1, Qt.AlignLeft | Qt.AlignTop)
        
        return value_label
    
    def clear_properties(self):
        """Limpia todas las propiedades."""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def set_collapsed(self, collapsed: bool):
        """Establece estado de colapso."""
        if collapsed != self._collapsed:
            self._toggle()
    
    @property
    def content_layout(self) -> QGridLayout:
        """Acceso al layout de contenido."""
        return self._content_layout


class ColorSwatch(QLabel):
    """Widget que muestra un color como un pequeño cuadrado."""
    
    def __init__(self, color: str = "#000000", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self._color = color
        self._update_style()
    
    def _update_style(self):
        """Actualiza el estilo visual."""
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {self._color};
                border: 1px solid #666;
                border-radius: 2px;
            }}
        """)
    
    def set_color(self, color: str):
        """Establece el color."""
        self._color = color
        self._update_style()


class PropertyInspector(QWidget):
    """
    Panel de inspección de propiedades tipográficas.
    
    Muestra propiedades del texto seleccionado en secciones colapsables:
    - Fuente
    - Color
    - Espaciado
    - Geometría
    - Transformación
    - Metadatos
    
    Signals:
        property_changed: Emitido cuando se modifica una propiedad
        selection_cleared: Emitido cuando se limpia la selección
    """
    
    # Señales
    property_changed = pyqtSignal(str, object)  # (property_name, new_value)
    selection_cleared = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._current_data: Optional[Dict[str, Any]] = None
        self._sections: Dict[str, CollapsibleSection] = {}
        self._value_labels: Dict[str, QLabel] = {}
        
        self._setup_ui()
        self._create_sections()
        
        # Estado inicial: sin selección
        self.clear()
    
    def _setup_ui(self):
        """Configura la UI principal."""
        self.setMinimumWidth(250)
        self.setMaximumWidth(350)
        
        # Estilo general
        self.setStyleSheet("""
            PropertyInspector {
                background-color: #252525;
            }
        """)
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # Título del panel
        title_label = QLabel("📋 Propiedades del Texto")
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 12px;
                font-weight: bold;
                padding: 4px 0;
            }
        """)
        main_layout.addWidget(title_label)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #3c3c3c;")
        separator.setFixedHeight(1)
        main_layout.addWidget(separator)
        
        # Área scrollable para las secciones
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background-color: #555;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #666;
            }
        """)
        
        # Container para secciones
        self._sections_container = QWidget()
        self._sections_layout = QVBoxLayout(self._sections_container)
        self._sections_layout.setContentsMargins(0, 0, 0, 0)
        self._sections_layout.setSpacing(6)
        
        scroll.setWidget(self._sections_container)
        main_layout.addWidget(scroll)
        
        # Label para cuando no hay selección
        self._no_selection_label = QLabel("Selecciona texto para\nver sus propiedades")
        self._no_selection_label.setAlignment(Qt.AlignCenter)
        self._no_selection_label.setStyleSheet("""
            QLabel {
                color: #808080;
                font-size: 11px;
                padding: 20px;
            }
        """)
        main_layout.addWidget(self._no_selection_label)
        
        main_layout.addStretch()
    
    def _create_sections(self):
        """Crea las secciones de propiedades."""
        # Sección: Texto
        self._sections["text"] = CollapsibleSection("Texto", collapsed=False)
        self._sections_layout.addWidget(self._sections["text"])
        
        # Sección: Fuente
        self._sections["font"] = CollapsibleSection("Fuente", collapsed=False)
        self._sections_layout.addWidget(self._sections["font"])
        
        # Sección: Color
        self._sections["color"] = CollapsibleSection("Color", collapsed=False)
        self._sections_layout.addWidget(self._sections["color"])
        
        # Sección: Espaciado
        self._sections["spacing"] = CollapsibleSection("Espaciado", collapsed=True)
        self._sections_layout.addWidget(self._sections["spacing"])
        
        # Sección: Geometría
        self._sections["geometry"] = CollapsibleSection("Geometría", collapsed=True)
        self._sections_layout.addWidget(self._sections["geometry"])
        
        # Sección: Transformación
        self._sections["transform"] = CollapsibleSection("Transformación", collapsed=True)
        self._sections_layout.addWidget(self._sections["transform"])
        
        # Sección: Metadatos
        self._sections["metadata"] = CollapsibleSection("Metadatos", collapsed=True)
        self._sections_layout.addWidget(self._sections["metadata"])
    
    def update_from_span(self, span: Any) -> None:
        """
        Actualiza las propiedades desde un TextSpanMetrics.
        
        Args:
            span: TextSpanMetrics o dict con propiedades del span
        """
        if span is None:
            self.clear()
            return
        
        # Convertir a dict si es necesario
        if hasattr(span, '__dict__'):
            data = vars(span) if not hasattr(span, 'to_dict') else span.to_dict()
        elif isinstance(span, dict):
            data = span
        else:
            logger.warning(f"Tipo de span no soportado: {type(span)}")
            self.clear()
            return
        
        self._current_data = data
        self._populate_sections(data)
        
        # Mostrar secciones, ocultar mensaje
        self._no_selection_label.hide()
        for section in self._sections.values():
            section.show()
    
    def update_from_line(self, line: Any) -> None:
        """
        Actualiza las propiedades desde un TextLine.
        Muestra propiedades agregadas de la línea.
        """
        if line is None:
            self.clear()
            return
        
        # Construir datos de línea
        data = {}
        
        if hasattr(line, 'get_full_text'):
            data['text'] = line.get_full_text()
        elif hasattr(line, 'text'):
            data['text'] = line.text
        
        if hasattr(line, 'bbox'):
            data['bbox'] = line.bbox
        
        if hasattr(line, 'baseline_y'):
            data['baseline_y'] = line.baseline_y
        
        if hasattr(line, 'line_height'):
            data['line_height'] = line.line_height
        
        if hasattr(line, 'get_dominant_font'):
            font_name, font_size = line.get_dominant_font()
            data['font_name'] = font_name
            data['font_size'] = font_size
        
        if hasattr(line, 'alignment'):
            data['alignment'] = line.alignment
        
        if hasattr(line, 'spans'):
            data['num_spans'] = len(line.spans)
        
        self._current_data = data
        self._populate_sections(data)
        
        self._no_selection_label.hide()
        for section in self._sections.values():
            section.show()
    
    def update_from_font_descriptor(self, descriptor: Any) -> None:
        """
        Actualiza las propiedades desde un FontDescriptor.
        """
        if descriptor is None:
            self.clear()
            return
        
        data = {
            'font_name': descriptor.name,
            'font_size': descriptor.size,
            'fill_color': descriptor.color,
            'font_flags': descriptor.flags,
            'is_bold': descriptor.possible_bold,
            'was_fallback': descriptor.was_fallback,
            'fallback_from': descriptor.fallback_from,
        }
        
        # Fase 3B campos
        if hasattr(descriptor, 'embedding_status'):
            data['embedding_status'] = descriptor.embedding_status.value if hasattr(descriptor.embedding_status, 'value') else str(descriptor.embedding_status)
        
        if hasattr(descriptor, 'precise_metrics') and descriptor.precise_metrics:
            pm = descriptor.precise_metrics
            data['ascender'] = pm.ascender
            data['descender'] = pm.descender
            data['stem_v'] = pm.stem_v
            data['italic_angle'] = pm.italic_angle
        
        if hasattr(descriptor, 'char_spacing'):
            data['char_spacing'] = descriptor.char_spacing
        
        if hasattr(descriptor, 'word_spacing'):
            data['word_spacing'] = descriptor.word_spacing
        
        if hasattr(descriptor, 'is_subset'):
            data['is_subset'] = descriptor.is_subset
        
        self._current_data = data
        self._populate_sections(data)
        
        self._no_selection_label.hide()
        for section in self._sections.values():
            section.show()
    
    def _populate_sections(self, data: Dict[str, Any]):
        """
        Puebla las secciones con los datos proporcionados.
        """
        self._value_labels.clear()
        
        # === Sección: Texto ===
        section = self._sections["text"]
        section.clear_properties()
        row = 0
        
        if 'text' in data:
            text = data['text']
            # Truncar si es muy largo
            display_text = text[:50] + "..." if len(text) > 50 else text
            prop = Property("Contenido", display_text, category=PropertyType.FONT,
                          tooltip=text if len(text) > 50 else "")
            self._value_labels['text'] = section.add_property(prop, row)
            row += 1
        
        if 'num_spans' in data:
            prop = Property("Spans", data['num_spans'], category=PropertyType.METADATA)
            self._value_labels['num_spans'] = section.add_property(prop, row)
            row += 1
        
        # === Sección: Fuente ===
        section = self._sections["font"]
        section.clear_properties()
        row = 0
        
        if 'font_name' in data:
            prop = Property("Nombre", data['font_name'], category=PropertyType.FONT,
                          tooltip="Nombre de la fuente")
            self._value_labels['font_name'] = section.add_property(prop, row)
            row += 1
        
        if 'font_name_pdf' in data and data['font_name_pdf'] != data.get('font_name'):
            prop = Property("Nombre PDF", data['font_name_pdf'], category=PropertyType.FONT,
                          tooltip="Nombre original en el PDF")
            self._value_labels['font_name_pdf'] = section.add_property(prop, row)
            row += 1
        
        if 'font_size' in data:
            prop = Property("Tamaño", data['font_size'], "pt", PropertyType.FONT,
                          tooltip="Tamaño en puntos")
            self._value_labels['font_size'] = section.add_property(prop, row)
            row += 1
        
        if 'is_bold' in data:
            prop = Property("Negrita", data['is_bold'], category=PropertyType.FONT,
                          tooltip="Detección heurística de negrita")
            self._value_labels['is_bold'] = section.add_property(prop, row)
            row += 1
        
        if 'is_italic' in data:
            prop = Property("Cursiva", data['is_italic'], category=PropertyType.FONT,
                          tooltip="Detección de cursiva")
            self._value_labels['is_italic'] = section.add_property(prop, row)
            row += 1
        
        if 'is_embedded' in data:
            prop = Property("Embebida", data['is_embedded'], category=PropertyType.FONT,
                          tooltip="¿La fuente está embebida en el PDF?")
            self._value_labels['is_embedded'] = section.add_property(prop, row)
            row += 1
        
        if 'is_subset' in data:
            prop = Property("Subset", data['is_subset'], category=PropertyType.FONT,
                          tooltip="¿Es un subset de la fuente?")
            self._value_labels['is_subset'] = section.add_property(prop, row)
            row += 1
        
        if 'embedding_status' in data:
            prop = Property("Estado", data['embedding_status'], category=PropertyType.FONT,
                          tooltip="Estado de embedding")
            self._value_labels['embedding_status'] = section.add_property(prop, row)
            row += 1
        
        # === Sección: Color ===
        section = self._sections["color"]
        section.clear_properties()
        row = 0
        
        if 'fill_color' in data:
            color = data['fill_color']
            prop = Property("Relleno", color, category=PropertyType.COLOR,
                          tooltip="Color de relleno del texto")
            self._value_labels['fill_color'] = section.add_property(prop, row)
            # Añadir swatch de color
            swatch = ColorSwatch(color)
            section.content_layout.addWidget(swatch, row, 2)
            row += 1
        
        if 'stroke_color' in data and data['stroke_color']:
            color = data['stroke_color']
            prop = Property("Trazo", color, category=PropertyType.COLOR,
                          tooltip="Color de trazo")
            self._value_labels['stroke_color'] = section.add_property(prop, row)
            swatch = ColorSwatch(color)
            section.content_layout.addWidget(swatch, row, 2)
            row += 1
        
        if 'render_mode' in data:
            modes = {0: "Relleno", 1: "Trazo", 2: "Relleno+Trazo", 3: "Invisible",
                    4: "Relleno (clip)", 5: "Trazo (clip)", 6: "R+T (clip)", 7: "Clip"}
            mode_str = modes.get(data['render_mode'], str(data['render_mode']))
            prop = Property("Modo render", mode_str, category=PropertyType.COLOR,
                          tooltip="Modo de renderizado PDF")
            self._value_labels['render_mode'] = section.add_property(prop, row)
            row += 1
        
        # === Sección: Espaciado ===
        section = self._sections["spacing"]
        section.clear_properties()
        row = 0
        
        if 'char_spacing' in data:
            prop = Property("Char spacing (Tc)", data['char_spacing'], "pt", PropertyType.SPACING,
                          tooltip="Espaciado adicional entre caracteres")
            self._value_labels['char_spacing'] = section.add_property(prop, row)
            row += 1
        
        if 'word_spacing' in data:
            prop = Property("Word spacing (Tw)", data['word_spacing'], "pt", PropertyType.SPACING,
                          tooltip="Espaciado adicional entre palabras")
            self._value_labels['word_spacing'] = section.add_property(prop, row)
            row += 1
        
        if 'leading' in data:
            prop = Property("Leading (TL)", data['leading'], "pt", PropertyType.SPACING,
                          tooltip="Interlineado")
            self._value_labels['leading'] = section.add_property(prop, row)
            row += 1
        
        if 'line_height' in data:
            prop = Property("Altura de línea", data['line_height'], "pt", PropertyType.SPACING,
                          tooltip="Altura total de la línea")
            self._value_labels['line_height'] = section.add_property(prop, row)
            row += 1
        
        if 'ascender' in data:
            prop = Property("Ascender", data['ascender'], "", PropertyType.SPACING,
                          tooltip="Altura sobre baseline (unidades de fuente)")
            self._value_labels['ascender'] = section.add_property(prop, row)
            row += 1
        
        if 'descender' in data:
            prop = Property("Descender", data['descender'], "", PropertyType.SPACING,
                          tooltip="Profundidad bajo baseline (unidades de fuente)")
            self._value_labels['descender'] = section.add_property(prop, row)
            row += 1
        
        # === Sección: Geometría ===
        section = self._sections["geometry"]
        section.clear_properties()
        row = 0
        
        if 'bbox' in data:
            prop = Property("BBox", data['bbox'], category=PropertyType.GEOMETRY,
                          tooltip="Bounding box: (x0, y0, x1, y1)")
            self._value_labels['bbox'] = section.add_property(prop, row)
            row += 1
        
        if 'origin' in data:
            prop = Property("Origen", data['origin'], category=PropertyType.GEOMETRY,
                          tooltip="Punto de origen del texto")
            self._value_labels['origin'] = section.add_property(prop, row)
            row += 1
        
        if 'baseline_y' in data:
            prop = Property("Baseline Y", data['baseline_y'], "pt", PropertyType.GEOMETRY,
                          tooltip="Coordenada Y del baseline")
            self._value_labels['baseline_y'] = section.add_property(prop, row)
            row += 1
        
        if 'alignment' in data:
            prop = Property("Alineación", data['alignment'], category=PropertyType.GEOMETRY,
                          tooltip="Alineación del texto")
            self._value_labels['alignment'] = section.add_property(prop, row)
            row += 1
        
        # === Sección: Transformación ===
        section = self._sections["transform"]
        section.clear_properties()
        row = 0
        
        if 'ctm' in data:
            prop = Property("CTM", data['ctm'], category=PropertyType.TRANSFORM,
                          tooltip="Current Transformation Matrix")
            self._value_labels['ctm'] = section.add_property(prop, row)
            row += 1
        
        if 'text_matrix' in data:
            prop = Property("Text Matrix", data['text_matrix'], category=PropertyType.TRANSFORM,
                          tooltip="Matriz de texto (Tm)")
            self._value_labels['text_matrix'] = section.add_property(prop, row)
            row += 1
        
        if 'horizontal_scale' in data:
            prop = Property("Escala H", data['horizontal_scale'], "%", PropertyType.TRANSFORM,
                          tooltip="Escalado horizontal (Tz)")
            self._value_labels['horizontal_scale'] = section.add_property(prop, row)
            row += 1
        
        if 'rotation' in data:
            prop = Property("Rotación", data['rotation'], "°", PropertyType.TRANSFORM,
                          tooltip="Ángulo de rotación")
            self._value_labels['rotation'] = section.add_property(prop, row)
            row += 1
        
        if 'rise' in data:
            prop = Property("Rise (Ts)", data['rise'], "pt", PropertyType.TRANSFORM,
                          tooltip="Desplazamiento vertical (super/subíndice)")
            self._value_labels['rise'] = section.add_property(prop, row)
            row += 1
        
        if 'stem_v' in data:
            prop = Property("Stem V", data['stem_v'], "", PropertyType.TRANSFORM,
                          tooltip="Grosor de stems verticales")
            self._value_labels['stem_v'] = section.add_property(prop, row)
            row += 1
        
        if 'italic_angle' in data:
            prop = Property("Ángulo itálica", data['italic_angle'], "°", PropertyType.TRANSFORM,
                          tooltip="Ángulo de inclinación para itálicas")
            self._value_labels['italic_angle'] = section.add_property(prop, row)
            row += 1
        
        # === Sección: Metadatos ===
        section = self._sections["metadata"]
        section.clear_properties()
        row = 0
        
        if 'page_num' in data:
            prop = Property("Página", data['page_num'] + 1, category=PropertyType.METADATA,
                          tooltip="Número de página (1-based)")
            self._value_labels['page_num'] = section.add_property(prop, row)
            row += 1
        
        if 'span_id' in data:
            prop = Property("Span ID", data['span_id'], category=PropertyType.METADATA,
                          tooltip="Identificador único del span")
            self._value_labels['span_id'] = section.add_property(prop, row)
            row += 1
        
        if 'was_fallback' in data:
            prop = Property("Usó fallback", data['was_fallback'], category=PropertyType.METADATA,
                          tooltip="¿Se usó fuente de fallback?")
            self._value_labels['was_fallback'] = section.add_property(prop, row)
            row += 1
        
        if 'fallback_from' in data and data['fallback_from']:
            prop = Property("Fuente original", data['fallback_from'], category=PropertyType.METADATA,
                          tooltip="Fuente original antes del fallback")
            self._value_labels['fallback_from'] = section.add_property(prop, row)
            row += 1
        
        if 'confidence' in data:
            conf_pct = data['confidence'] * 100 if data['confidence'] <= 1 else data['confidence']
            prop = Property("Confianza", f"{conf_pct:.0f}%", category=PropertyType.METADATA,
                          tooltip="Confianza en la detección de propiedades")
            self._value_labels['confidence'] = section.add_property(prop, row)
            row += 1
        
        if 'font_flags' in data:
            prop = Property("Flags PDF", f"0x{data['font_flags']:04X}", category=PropertyType.METADATA,
                          tooltip="Flags de fuente del PDF")
            self._value_labels['font_flags'] = section.add_property(prop, row)
            row += 1
    
    def clear(self):
        """Limpia el inspector y muestra mensaje de sin selección."""
        self._current_data = None
        self._value_labels.clear()
        
        for section in self._sections.values():
            section.clear_properties()
            section.hide()
        
        self._no_selection_label.show()
        self.selection_cleared.emit()
    
    def get_current_data(self) -> Optional[Dict[str, Any]]:
        """Retorna los datos actuales o None si no hay selección."""
        return self._current_data
    
    def update_property(self, name: str, value: Any):
        """
        Actualiza una propiedad específica.
        
        Args:
            name: Nombre de la propiedad
            value: Nuevo valor
        """
        if self._current_data is not None:
            self._current_data[name] = value
        
        if name in self._value_labels:
            # Formatear el valor
            if isinstance(value, bool):
                display = "Sí" if value else "No"
            elif isinstance(value, float):
                display = f"{value:.2f}"
            else:
                display = str(value)
            
            self._value_labels[name].setText(display)
    
    def sizeHint(self) -> QSize:
        """Tamaño sugerido del widget."""
        return QSize(280, 600)


# =============================================================================
# Funciones de utilidad
# =============================================================================

def create_property_inspector_dock(parent: Optional[QWidget] = None) -> PropertyInspector:
    """
    Crea un PropertyInspector listo para usar como dock widget.
    
    Args:
        parent: Widget padre opcional
        
    Returns:
        PropertyInspector configurado
    """
    inspector = PropertyInspector(parent)
    return inspector


# =============================================================================
# Tests básicos (ejecutar como módulo)
# =============================================================================

if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    
    # Crear inspector
    inspector = PropertyInspector()
    inspector.setWindowTitle("Property Inspector - Test")
    inspector.resize(300, 700)
    
    # Datos de prueba (simula un TextSpanMetrics)
    test_data = {
        'text': "Hello, World! This is a test text span.",
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
    
    # Actualizar con datos de prueba
    inspector.update_from_span(test_data)
    
    inspector.show()
    
    sys.exit(app.exec_())

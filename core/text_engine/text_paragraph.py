"""
TextParagraph - Agrupación de líneas en párrafos.

Este módulo implementa la detección y agrupación de TextLine en párrafos,
identificando estructura como encabezados, listas y párrafos normales.

La detección de párrafos en PDF es heurística porque:
1. Los PDFs no tienen marcado semántico de párrafos
2. Debe inferirse del espaciado, sangría y estilos
3. Diferentes documentos usan diferentes convenciones

El módulo proporciona:
- TextParagraph: Contenedor de líneas con análisis de estructura
- ParagraphDetector: Algoritmo de detección de párrafos
- ParagraphStyle: Configuración de estilos de párrafo
- Utilidades para detección de encabezados y listas
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, Iterator
from enum import Enum
import statistics
import re

# Import sibling modules
try:
    from .text_line import TextLine, LineAlignment
    from .text_span import TextSpanMetrics
except ImportError:
    from text_line import TextLine, LineAlignment
    from text_span import TextSpanMetrics


class ParagraphType(Enum):
    """Tipo de párrafo detectado."""
    NORMAL = "normal"           # Párrafo de texto normal
    HEADING = "heading"         # Encabezado/título
    SUBHEADING = "subheading"   # Subtítulo
    LIST_ITEM = "list_item"     # Ítem de lista
    QUOTE = "quote"             # Cita (texto sangrado)
    CODE = "code"               # Código (fuente monoespaciada)
    CAPTION = "caption"         # Pie de figura/tabla
    FOOTNOTE = "footnote"       # Nota al pie
    HEADER = "header"           # Encabezado de página
    FOOTER = "footer"           # Pie de página
    PAGE_NUMBER = "page_number" # Número de página


class ListType(Enum):
    """Tipo de lista detectado."""
    NONE = "none"              # No es lista
    BULLET = "bullet"          # Lista con viñetas (•, -, *, etc.)
    NUMBERED = "numbered"      # Lista numerada (1., 2., etc.)
    LETTERED = "lettered"      # Lista con letras (a., b., A., etc.)
    ROMAN = "roman"            # Lista con números romanos (i., ii., etc.)
    CHECKBOX = "checkbox"      # Lista de checkbox (☐, ☑, etc.)


class ParagraphAlignment(Enum):
    """Alineación del párrafo."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFIED = "justified"
    UNKNOWN = "unknown"


@dataclass
class ListMarkerInfo:
    """Información sobre el marcador de lista detectado."""
    list_type: ListType = ListType.NONE
    marker: str = ""           # El marcador real ("•", "1.", "a)", etc.)
    level: int = 0             # Nivel de anidación (0 = primer nivel)
    sequence_num: Optional[int] = None  # Número en la secuencia (para numeradas)
    
    @property
    def is_list(self) -> bool:
        """Indica si es un ítem de lista."""
        return self.list_type != ListType.NONE


@dataclass
class ParagraphStyle:
    """Estilo de párrafo para detección y formato."""
    
    # Fuente y tamaño
    font_name: str = ""
    font_size: float = 0.0
    is_bold: bool = False
    is_italic: bool = False
    
    # Espaciado
    line_spacing: float = 1.0      # Multiplicador (1.0 = simple, 1.5 = 1.5 líneas)
    space_before: float = 0.0      # Espacio antes del párrafo (puntos)
    space_after: float = 0.0       # Espacio después del párrafo (puntos)
    
    # Márgenes e indentación
    left_margin: float = 0.0
    right_margin: float = 0.0
    first_line_indent: float = 0.0  # Positivo = sangría, negativo = francesa
    
    # Alineación
    alignment: ParagraphAlignment = ParagraphAlignment.LEFT
    
    def is_similar_to(self, other: 'ParagraphStyle', tolerance: float = 2.0) -> bool:
        """Compara si dos estilos son similares (mismo párrafo visual)."""
        if self.font_name != other.font_name:
            return False
        if abs(self.font_size - other.font_size) > tolerance:
            return False
        if self.is_bold != other.is_bold:
            return False
        if self.is_italic != other.is_italic:
            return False
        return True


@dataclass
class ParagraphDetectionConfig:
    """Configuración para la detección de párrafos."""
    
    # Umbral de espacio vertical para separar párrafos
    # (como múltiplo del interlineado normal)
    paragraph_gap_threshold: float = 1.5
    
    # Umbral de sangría para detectar primera línea
    indent_threshold: float = 10.0  # puntos
    
    # Umbral de tamaño para detectar encabezados
    heading_size_ratio: float = 1.2  # 20% más grande que texto normal
    
    # Márgenes de página (para detectar headers/footers)
    page_top_margin: float = 72.0     # 1 pulgada = 72 puntos
    page_bottom_margin: float = 72.0
    page_left_margin: float = 72.0
    page_right_margin: float = 72.0
    
    # Ancho de página (para calcular márgenes)
    page_width: float = 612.0   # Carta US
    page_height: float = 792.0
    
    # Patrones de marcadores de lista
    bullet_markers: Tuple[str, ...] = ("•", "●", "○", "◦", "▪", "▫", "-", "*", "–", "—")
    numbered_pattern: str = r"^\d+[\.\)]\s*$"
    lettered_pattern: str = r"^[a-zA-Z][\.\)]\s*$"
    roman_pattern: str = r"^[ivxIVX]+[\.\)]\s*$"
    checkbox_markers: Tuple[str, ...] = ("☐", "☑", "☒", "□", "■", "✓", "✗")


@dataclass
class TextParagraph:
    """
    Un párrafo compuesto por una o más líneas de texto.
    
    Representa una unidad semántica de texto que incluye análisis
    de estructura (encabezados, listas, etc.) y estilo.
    
    Attributes:
        lines: Lista de TextLine ordenadas verticalmente
        page_num: Número de página
        paragraph_id: Identificador único del párrafo
        paragraph_type: Tipo detectado (normal, heading, list_item, etc.)
    """
    lines: List[TextLine] = field(default_factory=list)
    page_num: int = 0
    paragraph_id: str = ""
    paragraph_type: ParagraphType = ParagraphType.NORMAL
    
    # Información de lista (si aplica)
    list_info: ListMarkerInfo = field(default_factory=ListMarkerInfo)
    
    # Nivel de encabezado (1-6, 0 si no es encabezado)
    heading_level: int = 0
    
    def __post_init__(self):
        """Inicialización y cálculos automáticos."""
        if self.lines:
            self._sort_lines()
        
        if not self.paragraph_id:
            self._generate_paragraph_id()
    
    def _sort_lines(self) -> None:
        """Ordenar líneas por posición Y (de arriba a abajo)."""
        self.lines.sort(key=lambda line: line.bbox[1])
    
    def _generate_paragraph_id(self) -> None:
        """Generar ID único basado en contenido y posición."""
        import hashlib
        content = f"{self.page_num}:{self.bbox[1]:.2f}:{self.text[:30] if self.text else ''}"
        self.paragraph_id = hashlib.md5(content.encode()).hexdigest()[:8]
    
    # === Propiedades de texto ===
    
    @property
    def text(self) -> str:
        """Texto completo del párrafo concatenando todas las líneas."""
        if not self.lines:
            return ""
        return "\n".join(line.text for line in self.lines)
    
    @property
    def full_text(self) -> str:
        """Alias de text para compatibilidad con PORM."""
        return self.text
    
    def get_full_text(self) -> str:
        """Método para compatibilidad con especificación PORM."""
        return self.text
    
    @property
    def text_without_breaks(self) -> str:
        """Texto con líneas unidas por espacios (para búsqueda)."""
        if not self.lines:
            return ""
        return " ".join(line.text.strip() for line in self.lines)
    
    @property
    def line_count(self) -> int:
        """Número de líneas en el párrafo."""
        return len(self.lines)
    
    @property
    def char_count(self) -> int:
        """Número total de caracteres."""
        return sum(line.char_count for line in self.lines)
    
    @property
    def word_count(self) -> int:
        """Número aproximado de palabras."""
        return len(self.text_without_breaks.split())
    
    @property
    def span_count(self) -> int:
        """Número total de spans en todas las líneas."""
        return sum(line.span_count for line in self.lines)
    
    # === Propiedades geométricas ===
    
    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        """Bounding box combinado de todas las líneas."""
        if not self.lines:
            return (0.0, 0.0, 0.0, 0.0)
        
        x0 = min(line.bbox[0] for line in self.lines)
        y0 = min(line.bbox[1] for line in self.lines)
        x1 = max(line.bbox[2] for line in self.lines)
        y1 = max(line.bbox[3] for line in self.lines)
        
        return (x0, y0, x1, y1)
    
    @property
    def width(self) -> float:
        """Ancho del párrafo."""
        bbox = self.bbox
        return bbox[2] - bbox[0]
    
    @property
    def height(self) -> float:
        """Altura del párrafo."""
        bbox = self.bbox
        return bbox[3] - bbox[1]
    
    @property
    def x_start(self) -> float:
        """Posición X inicial."""
        return self.bbox[0] if self.lines else 0.0
    
    @property
    def x_end(self) -> float:
        """Posición X final."""
        return self.bbox[2] if self.lines else 0.0
    
    @property
    def y_start(self) -> float:
        """Posición Y inicial (parte superior)."""
        return self.bbox[1] if self.lines else 0.0
    
    @property
    def y_end(self) -> float:
        """Posición Y final (parte inferior)."""
        return self.bbox[3] if self.lines else 0.0
    
    # === Sangría y márgenes ===
    
    @property
    def first_line_indent(self) -> float:
        """
        Sangría de la primera línea respecto al resto.
        
        Positivo = sangría normal (primera línea más a la derecha)
        Negativo = sangría francesa (primera línea más a la izquierda)
        """
        if len(self.lines) < 2:
            return 0.0
        
        first_line_x = self.lines[0].x_start
        
        # Calcular el margen izquierdo promedio de las líneas restantes
        other_xs = [line.x_start for line in self.lines[1:]]
        avg_other_x = statistics.mean(other_xs) if other_xs else first_line_x
        
        return first_line_x - avg_other_x
    
    @property
    def left_margin(self) -> float:
        """Margen izquierdo del párrafo."""
        return self.bbox[0] if self.lines else 0.0
    
    @property
    def right_margin(self) -> float:
        """Margen derecho (requiere ancho de página para calcular)."""
        return self.bbox[2] if self.lines else 0.0
    
    # === Interlineado ===
    
    @property
    def line_spacing(self) -> float:
        """
        Espacio entre líneas (interlineado) en puntos.
        
        Calculado como la distancia promedio entre baselines consecutivas.
        """
        if len(self.lines) < 2:
            return 0.0
        
        spacings = []
        for i in range(len(self.lines) - 1):
            # Distancia entre baselines (Y aumenta hacia abajo en PDF coords)
            spacing = self.lines[i + 1].baseline_y - self.lines[i].baseline_y
            if spacing > 0:
                spacings.append(spacing)
        
        return statistics.mean(spacings) if spacings else 0.0
    
    @property
    def line_spacing_mode(self) -> str:
        """
        Modo de interlineado detectado.
        
        Returns:
            "fixed": Interlineado fijo
            "auto": Interlineado automático (basado en tamaño de fuente)
            "variable": Interlineado variable
        """
        if len(self.lines) < 2:
            return "auto"
        
        spacings = []
        for i in range(len(self.lines) - 1):
            spacing = self.lines[i + 1].baseline_y - self.lines[i].baseline_y
            if spacing > 0:
                spacings.append(spacing)
        
        if not spacings:
            return "auto"
        
        # Si hay poca variación, es fijo
        if len(spacings) > 1:
            variance = statistics.variance(spacings)
            if variance < 1.0:
                return "fixed"
        
        return "auto"
    
    def calculate_baseline_grid(self) -> List[float]:
        """
        Retorna las posiciones Y de todos los baselines.
        
        Útil para alinear texto editado con la cuadrícula de baselines.
        """
        return [line.baseline_y for line in self.lines]
    
    # === Estilos dominantes ===
    
    @property
    def dominant_font(self) -> str:
        """Fuente más común en el párrafo."""
        if not self.lines:
            return ""
        
        fonts: Dict[str, int] = {}
        for line in self.lines:
            font = line.dominant_font
            if font:
                fonts[font] = fonts.get(font, 0) + line.char_count
        
        if not fonts:
            return ""
        
        return max(fonts, key=fonts.get)
    
    @property
    def dominant_font_size(self) -> float:
        """Tamaño de fuente más común en el párrafo."""
        if not self.lines:
            return 0.0
        
        sizes: Dict[float, int] = {}
        for line in self.lines:
            size = round(line.dominant_font_size, 1)
            if size > 0:
                sizes[size] = sizes.get(size, 0) + line.char_count
        
        if not sizes:
            return 0.0
        
        return max(sizes, key=sizes.get)
    
    @property
    def dominant_alignment(self) -> ParagraphAlignment:
        """Alineación detectada del párrafo."""
        if not self.lines:
            return ParagraphAlignment.UNKNOWN
        
        alignments: Dict[LineAlignment, int] = {}
        for line in self.lines:
            align = line.detect_alignment()
            alignments[align] = alignments.get(align, 0) + 1
        
        if not alignments:
            return ParagraphAlignment.UNKNOWN
        
        dominant = max(alignments, key=alignments.get)
        
        # Mapear LineAlignment a ParagraphAlignment
        mapping = {
            LineAlignment.LEFT: ParagraphAlignment.LEFT,
            LineAlignment.CENTER: ParagraphAlignment.CENTER,
            LineAlignment.RIGHT: ParagraphAlignment.RIGHT,
            LineAlignment.JUSTIFIED: ParagraphAlignment.JUSTIFIED,
            LineAlignment.UNKNOWN: ParagraphAlignment.UNKNOWN,
        }
        
        return mapping.get(dominant, ParagraphAlignment.UNKNOWN)
    
    @property
    def is_bold(self) -> bool:
        """Indica si el párrafo es predominantemente negrita."""
        if not self.lines:
            return False
        
        bold_chars = sum(line.char_count for line in self.lines if line.is_bold)
        total_chars = sum(line.char_count for line in self.lines)
        
        return bold_chars > total_chars / 2 if total_chars > 0 else False
    
    @property
    def is_italic(self) -> bool:
        """Indica si el párrafo es predominantemente cursiva."""
        if not self.lines:
            return False
        
        italic_chars = sum(line.char_count for line in self.lines if line.is_italic)
        total_chars = sum(line.char_count for line in self.lines)
        
        return italic_chars > total_chars / 2 if total_chars > 0 else False
    
    @property
    def has_mixed_styles(self) -> bool:
        """Indica si el párrafo tiene múltiples estilos."""
        return any(line.has_mixed_styles for line in self.lines)
    
    # === Detección de tipo ===
    
    @property
    def is_heading(self) -> bool:
        """Indica si el párrafo es un encabezado."""
        return self.paragraph_type in (ParagraphType.HEADING, ParagraphType.SUBHEADING)
    
    @property
    def is_list_item(self) -> bool:
        """Indica si el párrafo es un ítem de lista."""
        return self.paragraph_type == ParagraphType.LIST_ITEM
    
    @property
    def list_marker(self) -> Optional[str]:
        """Marcador de lista si es un ítem."""
        return self.list_info.marker if self.list_info.is_list else None
    
    # === Métodos de análisis ===
    
    def get_style(self) -> ParagraphStyle:
        """Obtiene el estilo del párrafo."""
        return ParagraphStyle(
            font_name=self.dominant_font,
            font_size=self.dominant_font_size,
            is_bold=self.is_bold,
            is_italic=self.is_italic,
            line_spacing=self.line_spacing / self.dominant_font_size if self.dominant_font_size > 0 else 1.0,
            first_line_indent=self.first_line_indent,
            left_margin=self.left_margin,
            right_margin=self.right_margin,
            alignment=self.dominant_alignment,
        )
    
    def get_line_at_y(self, y: float, tolerance: float = 5.0) -> Optional[TextLine]:
        """
        Encuentra la línea en una posición Y.
        
        Args:
            y: Coordenada Y a buscar
            tolerance: Tolerancia para matching
            
        Returns:
            TextLine si se encuentra, None si no
        """
        for line in self.lines:
            if line.bbox[1] - tolerance <= y <= line.bbox[3] + tolerance:
                return line
        return None
    
    def get_line_by_index(self, index: int) -> Optional[TextLine]:
        """Obtiene una línea por su índice."""
        if 0 <= index < len(self.lines):
            return self.lines[index]
        return None
    
    def iter_lines(self) -> Iterator[TextLine]:
        """Itera sobre las líneas del párrafo."""
        return iter(self.lines)
    
    def iter_spans(self) -> Iterator[TextSpanMetrics]:
        """Itera sobre todos los spans del párrafo."""
        for line in self.lines:
            yield from line.spans
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el párrafo a diccionario para serialización."""
        return {
            'paragraph_id': self.paragraph_id,
            'page_num': self.page_num,
            'paragraph_type': self.paragraph_type.value,
            'heading_level': self.heading_level,
            'text': self.text,
            'bbox': self.bbox,
            'line_count': self.line_count,
            'char_count': self.char_count,
            'word_count': self.word_count,
            'first_line_indent': self.first_line_indent,
            'line_spacing': self.line_spacing,
            'dominant_font': self.dominant_font,
            'dominant_font_size': self.dominant_font_size,
            'dominant_alignment': self.dominant_alignment.value,
            'is_bold': self.is_bold,
            'is_italic': self.is_italic,
            'is_heading': self.is_heading,
            'is_list_item': self.is_list_item,
            'list_marker': self.list_marker,
            'lines': [
                {
                    'line_id': line.line_id,
                    'text': line.text,
                    'bbox': line.bbox,
                }
                for line in self.lines
            ],
        }


class ParagraphDetector:
    """
    Detector de párrafos que agrupa líneas y clasifica su tipo.
    
    Usa heurísticas para:
    - Agrupar líneas en párrafos por espaciado vertical
    - Detectar encabezados por tamaño de fuente
    - Identificar listas por marcadores
    - Clasificar elementos especiales (citas, código, etc.)
    """
    
    def __init__(self, config: Optional[ParagraphDetectionConfig] = None):
        """
        Inicializa el detector.
        
        Args:
            config: Configuración de detección (usa valores por defecto si None)
        """
        self.config = config or ParagraphDetectionConfig()
        
        # Compilar patrones regex
        self._numbered_re = re.compile(self.config.numbered_pattern)
        self._lettered_re = re.compile(self.config.lettered_pattern)
        self._roman_re = re.compile(self.config.roman_pattern)
    
    def detect_paragraphs(
        self,
        lines: List[TextLine],
        page_num: int = 0
    ) -> List[TextParagraph]:
        """
        Agrupa líneas en párrafos y detecta su tipo.
        
        Args:
            lines: Lista de líneas a agrupar
            page_num: Número de página
            
        Returns:
            Lista de TextParagraph detectados
        """
        if not lines:
            return []
        
        # Ordenar líneas por Y
        sorted_lines = sorted(lines, key=lambda line: line.bbox[1])
        
        # Calcular tamaño de fuente "normal" (más frecuente)
        normal_font_size = self._calculate_normal_font_size(sorted_lines)
        
        # Calcular interlineado típico
        typical_spacing = self._calculate_typical_line_spacing(sorted_lines)
        
        # Agrupar líneas en párrafos
        paragraph_groups = self._group_lines_into_paragraphs(
            sorted_lines,
            typical_spacing
        )
        
        # Crear párrafos y detectar tipos
        paragraphs = []
        for group in paragraph_groups:
            paragraph = TextParagraph(
                lines=group,
                page_num=page_num
            )
            
            # Detectar y asignar tipo
            self._detect_paragraph_type(
                paragraph,
                normal_font_size
            )
            
            paragraphs.append(paragraph)
        
        return paragraphs
    
    def _calculate_normal_font_size(self, lines: List[TextLine]) -> float:
        """Calcula el tamaño de fuente más común (considerado "normal")."""
        if not lines:
            return 12.0
        
        sizes: Dict[float, int] = {}
        for line in lines:
            size = round(line.dominant_font_size, 1)
            if size > 0:
                chars = line.char_count
                sizes[size] = sizes.get(size, 0) + chars
        
        if not sizes:
            return 12.0
        
        return max(sizes, key=sizes.get)
    
    def _calculate_typical_line_spacing(self, lines: List[TextLine]) -> float:
        """Calcula el interlineado típico entre líneas consecutivas."""
        if len(lines) < 2:
            return 14.0  # Default aproximado
        
        spacings = []
        for i in range(len(lines) - 1):
            spacing = lines[i + 1].bbox[1] - lines[i].bbox[3]
            if 0 < spacing < 50:  # Filtrar valores raros
                spacings.append(spacing)
        
        if not spacings:
            return 14.0
        
        # Usar mediana para evitar outliers
        return statistics.median(spacings)
    
    def _group_lines_into_paragraphs(
        self,
        lines: List[TextLine],
        typical_spacing: float
    ) -> List[List[TextLine]]:
        """Agrupa líneas en párrafos basándose en espaciado vertical."""
        if not lines:
            return []
        
        groups: List[List[TextLine]] = []
        current_group: List[TextLine] = [lines[0]]
        
        gap_threshold = typical_spacing * self.config.paragraph_gap_threshold
        
        for i in range(1, len(lines)):
            prev_line = lines[i - 1]
            curr_line = lines[i]
            
            # Calcular gap vertical
            gap = curr_line.bbox[1] - prev_line.bbox[3]
            
            # Verificar si es un nuevo párrafo
            is_new_paragraph = False
            
            # 1. Gap grande indica nuevo párrafo
            if gap > gap_threshold:
                is_new_paragraph = True
            
            # 2. Cambio significativo de fuente puede indicar nuevo párrafo
            elif self._has_significant_style_change(prev_line, curr_line):
                is_new_paragraph = True
            
            # 3. Sangría de primera línea puede indicar nuevo párrafo
            elif self._has_first_line_indent(prev_line, curr_line):
                is_new_paragraph = True
            
            if is_new_paragraph:
                groups.append(current_group)
                current_group = [curr_line]
            else:
                current_group.append(curr_line)
        
        # Añadir el último grupo
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _has_significant_style_change(
        self,
        prev_line: TextLine,
        curr_line: TextLine
    ) -> bool:
        """Detecta si hay un cambio de estilo significativo."""
        prev_size = prev_line.dominant_font_size
        curr_size = curr_line.dominant_font_size
        
        if prev_size > 0 and curr_size > 0:
            # Cambio de tamaño > 20%
            ratio = curr_size / prev_size
            if ratio > 1.2 or ratio < 0.8:
                return True
        
        # Cambio de bold puede indicar nuevo párrafo (ej: título)
        if prev_line.is_bold != curr_line.is_bold and curr_line.is_bold:
            return True
        
        return False
    
    def _has_first_line_indent(
        self,
        prev_line: TextLine,
        curr_line: TextLine
    ) -> bool:
        """Detecta si hay una sangría de primera línea."""
        indent_diff = curr_line.x_start - prev_line.x_start
        
        # Sangría positiva significativa
        if indent_diff > self.config.indent_threshold:
            return True
        
        return False
    
    def _detect_paragraph_type(
        self,
        paragraph: TextParagraph,
        normal_font_size: float
    ) -> None:
        """Detecta y asigna el tipo de párrafo."""
        if not paragraph.lines:
            return
        
        first_line = paragraph.lines[0]
        
        # 1. Detectar lista primero
        list_info = self._detect_list_marker(first_line)
        if list_info.is_list:
            paragraph.paragraph_type = ParagraphType.LIST_ITEM
            paragraph.list_info = list_info
            return
        
        # 2. Detectar encabezado
        if self._is_heading(paragraph, normal_font_size):
            paragraph.paragraph_type = ParagraphType.HEADING
            paragraph.heading_level = self._estimate_heading_level(
                paragraph,
                normal_font_size
            )
            return
        
        # 3. Detectar número de página
        if self._is_page_number(paragraph):
            paragraph.paragraph_type = ParagraphType.PAGE_NUMBER
            return
        
        # 4. Detectar header/footer de página
        if self._is_header_or_footer(paragraph):
            if paragraph.y_start < self.config.page_top_margin:
                paragraph.paragraph_type = ParagraphType.HEADER
            else:
                paragraph.paragraph_type = ParagraphType.FOOTER
            return
        
        # 5. Detectar código (fuente monoespaciada)
        if self._is_code(paragraph):
            paragraph.paragraph_type = ParagraphType.CODE
            return
        
        # 6. Detectar cita (texto muy sangrado)
        if self._is_quote(paragraph):
            paragraph.paragraph_type = ParagraphType.QUOTE
            return
        
        # Por defecto es párrafo normal
        paragraph.paragraph_type = ParagraphType.NORMAL
    
    def _detect_list_marker(self, line: TextLine) -> ListMarkerInfo:
        """Detecta si la línea comienza con un marcador de lista."""
        text = line.text.strip()
        if not text:
            return ListMarkerInfo()
        
        # Calcular nivel de anidación basado en sangría
        indent = line.x_start
        level = int(indent / 36)  # ~0.5 pulgada por nivel
        
        # 1. Buscar viñetas
        first_char = text[0]
        if first_char in self.config.bullet_markers:
            return ListMarkerInfo(
                list_type=ListType.BULLET,
                marker=first_char,
                level=level
            )
        
        # 2. Buscar checkbox
        if first_char in self.config.checkbox_markers:
            return ListMarkerInfo(
                list_type=ListType.CHECKBOX,
                marker=first_char,
                level=level
            )
        
        # Extraer posible marcador (primeros caracteres hasta espacio)
        words = text.split(maxsplit=1)
        if not words:
            return ListMarkerInfo()
        
        potential_marker = words[0]
        
        # 3. Buscar números (1., 2., 1), etc.)
        if self._numbered_re.match(potential_marker):
            num_match = re.match(r"(\d+)", potential_marker)
            seq_num = int(num_match.group(1)) if num_match else None
            return ListMarkerInfo(
                list_type=ListType.NUMBERED,
                marker=potential_marker,
                level=level,
                sequence_num=seq_num
            )
        
        # 4. Buscar letras (a., b., A), etc.)
        if self._lettered_re.match(potential_marker):
            letter = potential_marker[0].lower()
            seq_num = ord(letter) - ord('a') + 1
            return ListMarkerInfo(
                list_type=ListType.LETTERED,
                marker=potential_marker,
                level=level,
                sequence_num=seq_num
            )
        
        # 5. Buscar números romanos (i., ii., I), etc.)
        if self._roman_re.match(potential_marker):
            return ListMarkerInfo(
                list_type=ListType.ROMAN,
                marker=potential_marker,
                level=level
            )
        
        return ListMarkerInfo()
    
    def _is_heading(self, paragraph: TextParagraph, normal_font_size: float) -> bool:
        """Detecta si el párrafo es un encabezado."""
        if not paragraph.lines:
            return False
        
        # Encabezados típicamente tienen pocas líneas
        if paragraph.line_count > 3:
            return False
        
        # Tamaño de fuente mayor que lo normal
        size_ratio = paragraph.dominant_font_size / normal_font_size if normal_font_size > 0 else 1.0
        if size_ratio >= self.config.heading_size_ratio:
            return True
        
        # Bold y corto puede ser encabezado
        if paragraph.is_bold and paragraph.word_count <= 10:
            return True
        
        # Todo mayúsculas puede ser encabezado
        text = paragraph.text_without_breaks
        if text.isupper() and len(text) > 2 and paragraph.word_count <= 10:
            return True
        
        return False
    
    def _estimate_heading_level(
        self,
        paragraph: TextParagraph,
        normal_font_size: float
    ) -> int:
        """Estima el nivel de encabezado (1-6)."""
        size = paragraph.dominant_font_size
        
        if normal_font_size <= 0:
            return 1
        
        ratio = size / normal_font_size
        
        # Mapear ratio a nivel
        if ratio >= 2.0:
            return 1
        elif ratio >= 1.7:
            return 2
        elif ratio >= 1.5:
            return 3
        elif ratio >= 1.3:
            return 4
        elif ratio >= 1.2:
            return 5
        else:
            return 6
    
    def _is_page_number(self, paragraph: TextParagraph) -> bool:
        """Detecta si el párrafo es un número de página."""
        text = paragraph.text_without_breaks.strip()
        
        # Solo números
        if text.isdigit():
            # En posición típica de número de página
            y = paragraph.y_start
            if y < self.config.page_top_margin or y > self.config.page_height - self.config.page_bottom_margin:
                return True
        
        # Patrones como "Page 1" o "- 1 -"
        page_patterns = [
            r"^page\s+\d+$",
            r"^-\s*\d+\s*-$",
            r"^\d+\s*/\s*\d+$",  # 1/10
        ]
        
        for pattern in page_patterns:
            if re.match(pattern, text.lower()):
                return True
        
        return False
    
    def _is_header_or_footer(self, paragraph: TextParagraph) -> bool:
        """Detecta si el párrafo está en zona de header/footer."""
        if paragraph.line_count > 2:
            return False
        
        y = paragraph.y_start
        
        # En la parte superior
        if y < self.config.page_top_margin:
            return True
        
        # En la parte inferior
        if y > self.config.page_height - self.config.page_bottom_margin:
            return True
        
        return False
    
    def _is_code(self, paragraph: TextParagraph) -> bool:
        """Detecta si el párrafo es código (fuente monoespaciada)."""
        font = paragraph.dominant_font.lower()
        
        mono_fonts = ['courier', 'consolas', 'menlo', 'monaco', 'mono', 'source code']
        
        return any(m in font for m in mono_fonts)
    
    def _is_quote(self, paragraph: TextParagraph) -> bool:
        """Detecta si el párrafo es una cita (muy sangrado)."""
        if not paragraph.lines:
            return False
        
        # Citas típicamente están sangradas a ambos lados
        left_indent = paragraph.left_margin
        
        # Sangría significativa a la izquierda
        return left_indent > self.config.page_left_margin + 36  # 0.5 pulgada extra


# === Funciones de utilidad ===

def group_lines_into_paragraphs(
    lines: List[TextLine],
    page_num: int = 0,
    config: Optional[ParagraphDetectionConfig] = None
) -> List[TextParagraph]:
    """
    Función de conveniencia para agrupar líneas en párrafos.
    
    Args:
        lines: Lista de líneas a agrupar
        page_num: Número de página
        config: Configuración opcional
        
    Returns:
        Lista de párrafos detectados
    """
    detector = ParagraphDetector(config)
    return detector.detect_paragraphs(lines, page_num)


def find_paragraph_at_point(
    paragraphs: List[TextParagraph],
    x: float,
    y: float
) -> Optional[TextParagraph]:
    """
    Encuentra el párrafo que contiene un punto dado.
    
    Args:
        paragraphs: Lista de párrafos
        x, y: Coordenadas del punto
        
    Returns:
        Párrafo que contiene el punto, o None
    """
    for paragraph in paragraphs:
        bbox = paragraph.bbox
        if bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]:
            return paragraph
    return None


def find_paragraphs_in_region(
    paragraphs: List[TextParagraph],
    region: Tuple[float, float, float, float],
    min_overlap: float = 0.5
) -> List[TextParagraph]:
    """
    Encuentra párrafos que intersectan una región.
    
    Args:
        paragraphs: Lista de párrafos
        region: Región (x0, y0, x1, y1)
        min_overlap: Overlap mínimo requerido (0.0 a 1.0)
        
    Returns:
        Lista de párrafos que intersectan la región
    """
    result = []
    rx0, ry0, rx1, ry1 = region
    _region_area = (rx1 - rx0) * (ry1 - ry0)  # noqa: F841 - Reserved for future use
    
    for paragraph in paragraphs:
        px0, py0, px1, py1 = paragraph.bbox
        
        # Calcular intersección
        ix0 = max(rx0, px0)
        iy0 = max(ry0, py0)
        ix1 = min(rx1, px1)
        iy1 = min(ry1, py1)
        
        if ix0 < ix1 and iy0 < iy1:
            intersection_area = (ix1 - ix0) * (iy1 - iy0)
            paragraph_area = (px1 - px0) * (py1 - py0)
            
            if paragraph_area > 0:
                overlap = intersection_area / paragraph_area
                if overlap >= min_overlap:
                    result.append(paragraph)
    
    return result


def calculate_paragraph_statistics(
    paragraphs: List[TextParagraph]
) -> Dict[str, Any]:
    """
    Calcula estadísticas sobre una lista de párrafos.
    
    Args:
        paragraphs: Lista de párrafos
        
    Returns:
        Diccionario con estadísticas
    """
    if not paragraphs:
        return {
            'count': 0,
            'total_lines': 0,
            'total_words': 0,
            'total_chars': 0,
            'type_distribution': {},
            'avg_lines_per_paragraph': 0.0,
            'avg_words_per_paragraph': 0.0,
        }
    
    total_lines = sum(p.line_count for p in paragraphs)
    total_words = sum(p.word_count for p in paragraphs)
    total_chars = sum(p.char_count for p in paragraphs)
    
    type_counts: Dict[str, int] = {}
    for p in paragraphs:
        type_name = p.paragraph_type.value
        type_counts[type_name] = type_counts.get(type_name, 0) + 1
    
    return {
        'count': len(paragraphs),
        'total_lines': total_lines,
        'total_words': total_words,
        'total_chars': total_chars,
        'type_distribution': type_counts,
        'avg_lines_per_paragraph': total_lines / len(paragraphs),
        'avg_words_per_paragraph': total_words / len(paragraphs),
    }


def merge_paragraphs(
    paragraph1: TextParagraph,
    paragraph2: TextParagraph
) -> TextParagraph:
    """
    Fusiona dos párrafos en uno.
    
    Args:
        paragraph1: Primer párrafo (va arriba)
        paragraph2: Segundo párrafo (va abajo)
        
    Returns:
        Nuevo párrafo fusionado
    """
    merged_lines = paragraph1.lines + paragraph2.lines
    
    return TextParagraph(
        lines=merged_lines,
        page_num=paragraph1.page_num,
        paragraph_type=paragraph1.paragraph_type,
        list_info=paragraph1.list_info,
        heading_level=paragraph1.heading_level,
    )


def split_paragraph_at_line(
    paragraph: TextParagraph,
    line_index: int
) -> Tuple[TextParagraph, TextParagraph]:
    """
    Divide un párrafo en dos en un índice de línea.
    
    Args:
        paragraph: Párrafo a dividir
        line_index: Índice donde dividir (esta línea va al segundo párrafo)
        
    Returns:
        Tupla con (párrafo_antes, párrafo_después)
    """
    if line_index <= 0 or line_index >= paragraph.line_count:
        raise ValueError(f"line_index {line_index} fuera de rango")
    
    lines_before = paragraph.lines[:line_index]
    lines_after = paragraph.lines[line_index:]
    
    para1 = TextParagraph(
        lines=lines_before,
        page_num=paragraph.page_num,
        paragraph_type=paragraph.paragraph_type,
    )
    
    para2 = TextParagraph(
        lines=lines_after,
        page_num=paragraph.page_num,
        paragraph_type=ParagraphType.NORMAL,  # El segundo pierde tipo especial
    )
    
    return para1, para2

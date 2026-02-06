"""
TextLine - Agrupación de spans de texto en líneas.

Este módulo implementa la agrupación de TextSpanMetrics en líneas
basándose en el baseline y la proximidad horizontal.

Una "línea" de texto en PDF no es explícita - debe inferirse de:
1. Spans con el mismo baseline (o muy cercano)
2. Spans contiguos horizontalmente
3. Orden de lectura coherente (izquierda a derecha para idiomas LTR)

El módulo proporciona:
- TextLine: Contenedor de spans con métodos de análisis
- LineGrouper: Algoritmo de agrupación de spans en líneas
- Utilidades para detección de interlineado y estructura
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, Iterable, Iterator
from enum import Enum
import statistics

# Import sibling module - use try/except for flexibility
try:
    from .text_span import TextSpanMetrics
except ImportError:
    from text_span import TextSpanMetrics


class ReadingDirection(Enum):
    """Dirección de lectura del texto."""
    LTR = "ltr"   # Left to right (español, inglés, etc.)
    RTL = "rtl"   # Right to left (árabe, hebreo, etc.)
    TTB = "ttb"   # Top to bottom (japonés vertical, etc.)
    MIXED = "mixed"  # Dirección mixta


class LineAlignment(Enum):
    """Alineación detectada de una línea."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFIED = "justified"
    UNKNOWN = "unknown"


@dataclass
class TextLine:
    """
    Una línea de texto compuesta por uno o más spans.
    
    Representa una secuencia horizontal de texto que comparte
    aproximadamente el mismo baseline.
    
    Attributes:
        spans: Lista de TextSpanMetrics ordenados por posición X
        page_num: Número de página
        line_id: Identificador único de la línea
        baseline_y: Baseline promedio de la línea
        reading_direction: Dirección de lectura detectada
    """
    spans: List[TextSpanMetrics] = field(default_factory=list)
    page_num: int = 0
    line_id: str = ""
    baseline_y: float = 0.0
    reading_direction: ReadingDirection = ReadingDirection.LTR
    
    def __post_init__(self):
        """Ordenar spans y calcular baseline si es necesario."""
        if self.spans and self.baseline_y == 0.0:
            self._calculate_baseline()
        
        if self.spans:
            self._sort_spans()
        
        if not self.line_id:
            self._generate_line_id()
    
    def _calculate_baseline(self) -> None:
        """Calcular el baseline promedio de los spans."""
        if not self.spans:
            return
        
        baselines = [s.baseline_y for s in self.spans]
        self.baseline_y = statistics.mean(baselines)
    
    def _sort_spans(self) -> None:
        """Ordenar spans por posición X."""
        self.spans.sort(key=lambda s: s.bbox[0])
    
    def _generate_line_id(self) -> None:
        """Generar ID único basado en contenido y posición."""
        import hashlib
        content = f"{self.page_num}:{self.baseline_y:.2f}:{self.text[:20] if self.text else ''}"
        self.line_id = hashlib.md5(content.encode()).hexdigest()[:8]
    
    # === Propiedades de texto ===
    
    @property
    def text(self) -> str:
        """Texto completo de la línea concatenando todos los spans."""
        if not self.spans:
            return ""
        
        result = []
        prev_span = None
        
        for span in self.spans:
            if prev_span is not None:
                # Detectar si hay espacio entre spans
                gap = span.bbox[0] - prev_span.bbox[2]
                if gap > 0:
                    # Estimar si el gap representa un espacio
                    avg_char_width = prev_span.width / max(len(prev_span.text), 1)
                    if gap > avg_char_width * 0.3:
                        result.append(" ")
            
            result.append(span.text)
            prev_span = span
        
        return "".join(result)
    
    @property
    def char_count(self) -> int:
        """Número total de caracteres en la línea."""
        return sum(len(s.text) for s in self.spans)
    
    @property
    def word_count(self) -> int:
        """Número aproximado de palabras en la línea."""
        return len(self.text.split())
    
    @property
    def span_count(self) -> int:
        """Número de spans en la línea."""
        return len(self.spans)
    
    # === Propiedades geométricas ===
    
    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        """Bounding box combinado de todos los spans."""
        if not self.spans:
            return (0.0, 0.0, 0.0, 0.0)
        
        x0 = min(s.bbox[0] for s in self.spans)
        y0 = min(s.bbox[1] for s in self.spans)
        x1 = max(s.bbox[2] for s in self.spans)
        y1 = max(s.bbox[3] for s in self.spans)
        
        return (x0, y0, x1, y1)
    
    @property
    def width(self) -> float:
        """Ancho total de la línea."""
        bbox = self.bbox
        return bbox[2] - bbox[0]
    
    @property
    def height(self) -> float:
        """Altura de la línea (máximo de spans)."""
        bbox = self.bbox
        return bbox[3] - bbox[1]
    
    @property
    def x_start(self) -> float:
        """Coordenada X del inicio de la línea."""
        return self.bbox[0] if self.spans else 0.0
    
    @property
    def x_end(self) -> float:
        """Coordenada X del final de la línea."""
        return self.bbox[2] if self.spans else 0.0
    
    @property
    def center_x(self) -> float:
        """Centro horizontal de la línea."""
        bbox = self.bbox
        return (bbox[0] + bbox[2]) / 2
    
    @property
    def center_y(self) -> float:
        """Centro vertical de la línea."""
        bbox = self.bbox
        return (bbox[1] + bbox[3]) / 2
    
    # === Propiedades de estilo ===
    
    @property
    def dominant_font(self) -> str:
        """Fuente más común en la línea."""
        if not self.spans:
            return "Helvetica"
        
        # Contar caracteres por fuente
        font_chars: Dict[str, int] = {}
        for span in self.spans:
            font = span.font_name
            font_chars[font] = font_chars.get(font, 0) + len(span.text)
        
        return max(font_chars.keys(), key=lambda k: font_chars[k])
    
    @property
    def dominant_font_size(self) -> float:
        """Tamaño de fuente más común en la línea."""
        if not self.spans:
            return 12.0
        
        # Contar caracteres por tamaño
        size_chars: Dict[float, int] = {}
        for span in self.spans:
            size = round(span.font_size, 1)
            size_chars[size] = size_chars.get(size, 0) + len(span.text)
        
        return max(size_chars.keys(), key=lambda k: size_chars[k])
    
    @property
    def dominant_color(self) -> str:
        """Color más común en la línea."""
        if not self.spans:
            return "#000000"
        
        color_chars: Dict[str, int] = {}
        for span in self.spans:
            color = span.fill_color
            color_chars[color] = color_chars.get(color, 0) + len(span.text)
        
        return max(color_chars.keys(), key=lambda k: color_chars[k])
    
    @property
    def is_bold(self) -> bool:
        """True si la mayoría de la línea es bold."""
        if not self.spans:
            return False
        
        bold_chars = sum(len(s.text) for s in self.spans if s.is_bold)
        return bold_chars > self.char_count / 2
    
    @property
    def is_italic(self) -> bool:
        """True si la mayoría de la línea es italic."""
        if not self.spans:
            return False
        
        italic_chars = sum(len(s.text) for s in self.spans if s.is_italic)
        return italic_chars > self.char_count / 2
    
    @property
    def has_mixed_styles(self) -> bool:
        """True si la línea tiene múltiples estilos."""
        if len(self.spans) <= 1:
            return False
        
        first = self.spans[0]
        for span in self.spans[1:]:
            if not span.has_same_style(first):
                return True
        return False
    
    @property
    def has_superscript(self) -> bool:
        """True si algún span es superíndice."""
        return any(s.is_superscript for s in self.spans)
    
    @property
    def has_subscript(self) -> bool:
        """True si algún span es subíndice."""
        return any(s.is_subscript for s in self.spans)
    
    # === Propiedades de espaciado ===
    
    @property
    def avg_char_spacing(self) -> float:
        """Espaciado de caracteres promedio (Tc)."""
        if not self.spans:
            return 0.0
        
        total = sum(s.char_spacing * len(s.text) for s in self.spans)
        return total / self.char_count if self.char_count > 0 else 0.0
    
    @property
    def avg_word_spacing(self) -> float:
        """Espaciado de palabras promedio (Tw)."""
        if not self.spans:
            return 0.0
        
        # Ponderar por número de espacios en cada span
        total_spacing = 0.0
        total_spaces = 0
        
        for span in self.spans:
            spaces = span.text.count(' ')
            total_spacing += span.word_spacing * spaces
            total_spaces += spaces
        
        return total_spacing / total_spaces if total_spaces > 0 else 0.0
    
    @property
    def inter_span_gaps(self) -> List[float]:
        """Lista de espacios entre spans consecutivos."""
        gaps = []
        for i in range(len(self.spans) - 1):
            gap = self.spans[i + 1].bbox[0] - self.spans[i].bbox[2]
            gaps.append(gap)
        return gaps
    
    @property
    def avg_inter_span_gap(self) -> float:
        """Espacio promedio entre spans."""
        gaps = self.inter_span_gaps
        return statistics.mean(gaps) if gaps else 0.0
    
    # === Métodos de análisis ===
    
    def detect_alignment(self, page_width: Optional[float] = None) -> LineAlignment:
        """
        Detectar la alineación de la línea.
        
        Args:
            page_width: Ancho de página para calcular alineación
            
        Returns:
            LineAlignment detectada
        """
        if not page_width or not self.spans:
            return LineAlignment.UNKNOWN
        
        left_margin = self.x_start
        right_margin = page_width - self.x_end
        
        margin_diff = abs(left_margin - right_margin)
        threshold = page_width * 0.05  # 5% de tolerancia
        
        if margin_diff < threshold:
            # Márgenes iguales - posiblemente centrado o justificado
            if len(self.spans) > 1 and self._has_even_spacing():
                return LineAlignment.JUSTIFIED
            return LineAlignment.CENTER
        
        if left_margin < right_margin:
            return LineAlignment.LEFT
        return LineAlignment.RIGHT
    
    def _has_even_spacing(self) -> bool:
        """Detectar si hay espaciado uniforme (texto justificado)."""
        gaps = self.inter_span_gaps
        if len(gaps) < 2:
            return False
        
        # Calcular varianza del espaciado
        try:
            variance = statistics.variance(gaps)
            mean_gap = statistics.mean(gaps)
            # Si la varianza es baja relativa a la media, es uniforme
            return variance < (mean_gap * 0.2) if mean_gap > 0 else False
        except statistics.StatisticsError:
            return False
    
    def find_span_at_x(self, x: float) -> Optional[TextSpanMetrics]:
        """
        Encontrar el span que contiene la coordenada X.
        
        Args:
            x: Coordenada X a buscar
            
        Returns:
            TextSpanMetrics si se encuentra, None si no
        """
        for span in self.spans:
            if span.bbox[0] <= x <= span.bbox[2]:
                return span
        return None
    
    def find_char_at_x(self, x: float) -> Optional[Tuple[TextSpanMetrics, int]]:
        """
        Encontrar el carácter en la coordenada X.
        
        Returns:
            Tupla (span, índice_carácter) o None
        """
        span = self.find_span_at_x(x)
        if span is None or not span.char_widths:
            return None
        
        # Buscar carácter por posición
        current_x = span.bbox[0]
        for i, width in enumerate(span.char_widths):
            if current_x <= x <= current_x + width:
                return (span, i)
            current_x += width
        
        return (span, len(span.text) - 1)
    
    def get_spans_in_range(self, x_start: float, x_end: float) -> List[TextSpanMetrics]:
        """Obtener spans que intersectan con un rango X."""
        result = []
        for span in self.spans:
            # Verificar intersección
            if span.bbox[2] >= x_start and span.bbox[0] <= x_end:
                result.append(span)
        return result
    
    def split_at_x(self, x: float) -> Tuple['TextLine', 'TextLine']:
        """
        Dividir la línea en una coordenada X.
        
        Returns:
            Tupla (línea_izquierda, línea_derecha)
        """
        left_spans = []
        right_spans = []
        
        for span in self.spans:
            if span.bbox[2] <= x:
                left_spans.append(span)
            elif span.bbox[0] >= x:
                right_spans.append(span)
            else:
                # Span cruza el punto de corte - va a ambos lados
                # (simplificación: asignar al lado donde está la mayoría)
                center = (span.bbox[0] + span.bbox[2]) / 2
                if center < x:
                    left_spans.append(span)
                else:
                    right_spans.append(span)
        
        return (
            TextLine(spans=left_spans, page_num=self.page_num),
            TextLine(spans=right_spans, page_num=self.page_num)
        )
    
    # === Métodos de manipulación ===
    
    def add_span(self, span: TextSpanMetrics) -> None:
        """Añadir un span y reordenar."""
        self.spans.append(span)
        self._sort_spans()
        self._calculate_baseline()
    
    def remove_span(self, span: TextSpanMetrics) -> bool:
        """Eliminar un span de la línea."""
        try:
            self.spans.remove(span)
            if self.spans:
                self._calculate_baseline()
            return True
        except ValueError:
            return False
    
    def merge_with(self, other: 'TextLine') -> 'TextLine':
        """
        Fusionar con otra línea.
        
        Returns:
            Nueva TextLine con spans combinados
        """
        combined_spans = self.spans + other.spans
        return TextLine(spans=combined_spans, page_num=self.page_num)
    
    # === Iteración ===
    
    def __iter__(self) -> Iterator[TextSpanMetrics]:
        """Iterar sobre los spans de la línea."""
        return iter(self.spans)
    
    def __len__(self) -> int:
        """Número de spans."""
        return len(self.spans)
    
    def __getitem__(self, index: int) -> TextSpanMetrics:
        """Acceso por índice a spans."""
        return self.spans[index]
    
    def __bool__(self) -> bool:
        """True si la línea tiene spans."""
        return len(self.spans) > 0
    
    # === Serialización ===
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializar a diccionario."""
        return {
            'line_id': self.line_id,
            'page_num': self.page_num,
            'baseline_y': self.baseline_y,
            'reading_direction': self.reading_direction.value,
            'text': self.text,
            'bbox': list(self.bbox),
            'span_count': self.span_count,
            'dominant_font': self.dominant_font,
            'dominant_font_size': self.dominant_font_size,
            'dominant_color': self.dominant_color,
            'is_bold': self.is_bold,
            'is_italic': self.is_italic,
            'has_mixed_styles': self.has_mixed_styles,
            'avg_char_spacing': self.avg_char_spacing,
            'avg_word_spacing': self.avg_word_spacing,
            'spans': [s.to_dict() for s in self.spans]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextLine':
        """Crear desde diccionario."""
        spans = [TextSpanMetrics.from_dict(s) for s in data.get('spans', [])]
        return cls(
            spans=spans,
            page_num=data.get('page_num', 0),
            line_id=data.get('line_id', ''),
            baseline_y=data.get('baseline_y', 0.0),
            reading_direction=ReadingDirection(data.get('reading_direction', 'ltr'))
        )
    
    def __repr__(self) -> str:
        """Representación para debugging."""
        text_preview = self.text[:30] + "..." if len(self.text) > 30 else self.text
        return f"TextLine('{text_preview}', spans={self.span_count}, baseline={self.baseline_y:.1f})"


@dataclass
class LineGroupingConfig:
    """
    Configuración para el algoritmo de agrupación de líneas.
    
    Attributes:
        baseline_tolerance: Tolerancia para considerar spans en la misma línea (puntos)
        horizontal_gap_threshold: Máximo gap horizontal para considerare mismo grupo (puntos)
        min_overlap_ratio: Mínimo solapamiento vertical para agrupar (0-1)
        reading_direction: Dirección de lectura por defecto
    """
    baseline_tolerance: float = 3.0
    horizontal_gap_threshold: float = 50.0
    min_overlap_ratio: float = 0.5
    reading_direction: ReadingDirection = ReadingDirection.LTR


class LineGrouper:
    """
    Agrupa TextSpanMetrics en TextLines basándose en baseline y proximidad.
    
    El algoritmo:
    1. Ordena spans por baseline_y
    2. Agrupa spans con baselines cercanos
    3. Dentro de cada grupo, ordena por posición X
    4. Opcionalmente divide grupos muy separados horizontalmente
    
    Usage:
        >>> grouper = LineGrouper()
        >>> lines = grouper.group_spans(spans)
    """
    
    def __init__(self, config: Optional[LineGroupingConfig] = None):
        """
        Inicializar el agrupador.
        
        Args:
            config: Configuración de agrupación (usa defaults si None)
        """
        self.config = config or LineGroupingConfig()
    
    def group_spans(self, spans: Iterable[TextSpanMetrics]) -> List[TextLine]:
        """
        Agrupar spans en líneas.
        
        Args:
            spans: Colección de TextSpanMetrics a agrupar
            
        Returns:
            Lista de TextLine ordenadas por posición vertical (arriba a abajo)
        """
        span_list = list(spans)
        
        if not span_list:
            return []
        
        # Paso 1: Ordenar por baseline
        span_list.sort(key=lambda s: (s.baseline_y, s.bbox[0]))
        
        # Paso 2: Agrupar por baseline similar
        lines: List[TextLine] = []
        current_group: List[TextSpanMetrics] = [span_list[0]]
        current_baseline = span_list[0].baseline_y
        
        for span in span_list[1:]:
            # ¿Está en la misma línea (baseline similar)?
            if abs(span.baseline_y - current_baseline) <= self.config.baseline_tolerance:
                current_group.append(span)
            else:
                # Nueva línea
                lines.append(self._create_line(current_group))
                current_group = [span]
                current_baseline = span.baseline_y
        
        # No olvidar el último grupo
        if current_group:
            lines.append(self._create_line(current_group))
        
        # Paso 3: Ordenar líneas de arriba a abajo
        lines.sort(key=lambda line: line.baseline_y)
        
        return lines
    
    def _create_line(self, spans: List[TextSpanMetrics]) -> TextLine:
        """Crear TextLine a partir de un grupo de spans."""
        page_num = spans[0].page_num if spans else 0
        return TextLine(
            spans=spans,
            page_num=page_num,
            reading_direction=self.config.reading_direction
        )
    
    def group_by_vertical_position(
        self,
        spans: Iterable[TextSpanMetrics],
        tolerance: Optional[float] = None
    ) -> List[List[TextSpanMetrics]]:
        """
        Agrupar spans solo por posición vertical (baseline).
        
        Útil para análisis preliminar sin crear objetos TextLine.
        
        Returns:
            Lista de grupos (cada grupo es una lista de spans)
        """
        tol = tolerance or self.config.baseline_tolerance
        span_list = sorted(spans, key=lambda s: s.baseline_y)
        
        if not span_list:
            return []
        
        groups: List[List[TextSpanMetrics]] = []
        current_group: List[TextSpanMetrics] = [span_list[0]]
        current_baseline = span_list[0].baseline_y
        
        for span in span_list[1:]:
            if abs(span.baseline_y - current_baseline) <= tol:
                current_group.append(span)
            else:
                groups.append(current_group)
                current_group = [span]
                current_baseline = span.baseline_y
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def split_by_horizontal_gap(
        self,
        line: TextLine,
        gap_threshold: Optional[float] = None
    ) -> List[TextLine]:
        """
        Dividir una línea si hay gaps horizontales grandes.
        
        Útil para detectar columnas o texto tabulado.
        
        Args:
            line: TextLine a analizar
            gap_threshold: Umbral de gap (usa config si None)
            
        Returns:
            Lista de TextLines (puede ser una sola si no hay división)
        """
        threshold = gap_threshold or self.config.horizontal_gap_threshold
        
        if len(line.spans) <= 1:
            return [line]
        
        # Ordenar spans por X
        sorted_spans = sorted(line.spans, key=lambda s: s.bbox[0])
        
        # Detectar gaps grandes
        result_lines: List[TextLine] = []
        current_group: List[TextSpanMetrics] = [sorted_spans[0]]
        
        for i in range(1, len(sorted_spans)):
            prev_span = sorted_spans[i - 1]
            curr_span = sorted_spans[i]
            gap = curr_span.bbox[0] - prev_span.bbox[2]
            
            if gap > threshold:
                # Gap grande - crear nueva línea
                result_lines.append(TextLine(spans=current_group, page_num=line.page_num))
                current_group = [curr_span]
            else:
                current_group.append(curr_span)
        
        if current_group:
            result_lines.append(TextLine(spans=current_group, page_num=line.page_num))
        
        return result_lines
    
    def estimate_line_spacing(self, lines: List[TextLine]) -> float:
        """
        Estimar el interlineado (leading) de una lista de líneas.
        
        Returns:
            Interlineado estimado en puntos, o 0 si no se puede calcular
        """
        if len(lines) < 2:
            return 0.0
        
        # Calcular distancias entre baselines consecutivos
        spacings = []
        for i in range(len(lines) - 1):
            # En PDF, Y aumenta hacia arriba, así que lines[i+1] está "arriba"
            # Pero nuestras líneas están ordenadas de arriba a abajo
            spacing = lines[i + 1].baseline_y - lines[i].baseline_y
            if spacing > 0:
                spacings.append(spacing)
        
        if not spacings:
            return 0.0
        
        return statistics.median(spacings)
    
    def detect_paragraphs(
        self,
        lines: List[TextLine],
        paragraph_gap_factor: float = 1.5
    ) -> List[List[TextLine]]:
        """
        Agrupar líneas en párrafos basándose en interlineado.
        
        Líneas con un gap mayor que el interlineado normal * factor
        se consideran de diferentes párrafos.
        
        Args:
            lines: Lista de TextLine ordenadas verticalmente
            paragraph_gap_factor: Multiplicador del interlineado normal
            
        Returns:
            Lista de párrafos (cada párrafo es una lista de TextLine)
        """
        if not lines:
            return []
        
        if len(lines) == 1:
            return [[lines[0]]]
        
        # Estimar interlineado normal
        normal_spacing = self.estimate_line_spacing(lines)
        if normal_spacing == 0:
            return [[line] for line in lines]
        
        threshold = normal_spacing * paragraph_gap_factor
        
        # Agrupar líneas
        paragraphs: List[List[TextLine]] = []
        current_para: List[TextLine] = [lines[0]]
        
        for i in range(1, len(lines)):
            spacing = lines[i].baseline_y - lines[i - 1].baseline_y
            
            if spacing > threshold:
                paragraphs.append(current_para)
                current_para = [lines[i]]
            else:
                current_para.append(lines[i])
        
        if current_para:
            paragraphs.append(current_para)
        
        return paragraphs


# === Funciones de conveniencia ===

def group_spans_into_lines(
    spans: Iterable[TextSpanMetrics],
    baseline_tolerance: float = 3.0
) -> List[TextLine]:
    """
    Función de conveniencia para agrupar spans en líneas.
    
    Args:
        spans: Colección de TextSpanMetrics
        baseline_tolerance: Tolerancia de baseline en puntos
        
    Returns:
        Lista de TextLine ordenadas verticalmente
    """
    config = LineGroupingConfig(baseline_tolerance=baseline_tolerance)
    grouper = LineGrouper(config)
    return grouper.group_spans(spans)


def find_line_at_point(
    lines: List[TextLine],
    x: float,
    y: float,
    tolerance: float = 5.0
) -> Optional[TextLine]:
    """
    Encontrar la línea en una coordenada específica.
    
    Args:
        lines: Lista de TextLine
        x: Coordenada X
        y: Coordenada Y
        tolerance: Tolerancia de búsqueda en puntos
        
    Returns:
        TextLine si se encuentra, None si no
    """
    for line in lines:
        bbox = line.bbox
        # Verificar si el punto está dentro del bbox expandido por tolerancia
        if (bbox[0] - tolerance <= x <= bbox[2] + tolerance and
            bbox[1] - tolerance <= y <= bbox[3] + tolerance):
            return line
    return None


def calculate_line_statistics(lines: List[TextLine]) -> Dict[str, Any]:
    """
    Calcular estadísticas sobre una lista de líneas.
    
    Returns:
        Diccionario con estadísticas: avg_height, avg_width, line_count, etc.
    """
    if not lines:
        return {
            'line_count': 0,
            'total_chars': 0,
            'total_words': 0,
            'avg_height': 0.0,
            'avg_width': 0.0,
            'avg_spans_per_line': 0.0,
            'line_spacing': 0.0
        }
    
    heights = [line.height for line in lines]
    widths = [line.width for line in lines]
    
    grouper = LineGrouper()
    
    return {
        'line_count': len(lines),
        'total_chars': sum(line.char_count for line in lines),
        'total_words': sum(line.word_count for line in lines),
        'avg_height': statistics.mean(heights),
        'avg_width': statistics.mean(widths),
        'avg_spans_per_line': statistics.mean([line.span_count for line in lines]),
        'line_spacing': grouper.estimate_line_spacing(lines),
        'min_x': min(line.x_start for line in lines),
        'max_x': max(line.x_end for line in lines),
        'dominant_font': _get_most_common_font(lines),
        'dominant_font_size': _get_most_common_font_size(lines)
    }


def _get_most_common_font(lines: List[TextLine]) -> str:
    """Obtener la fuente más común en todas las líneas."""
    font_counts: Dict[str, int] = {}
    for line in lines:
        for span in line.spans:
            font = span.font_name
            font_counts[font] = font_counts.get(font, 0) + len(span.text)
    
    if not font_counts:
        return "Unknown"
    
    return max(font_counts.keys(), key=lambda k: font_counts[k])


def _get_most_common_font_size(lines: List[TextLine]) -> float:
    """Obtener el tamaño de fuente más común."""
    size_counts: Dict[float, int] = {}
    for line in lines:
        for span in line.spans:
            size = round(span.font_size, 1)
            size_counts[size] = size_counts.get(size, 0) + len(span.text)
    
    if not size_counts:
        return 12.0
    
    return max(size_counts.keys(), key=lambda k: size_counts[k])

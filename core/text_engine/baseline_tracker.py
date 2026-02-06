"""
BaselineTracker - Rastreo de líneas base e interlineado.

Módulo para análisis y seguimiento de la estructura vertical del texto
en documentos PDF. Permite mantener la alineación y el interlineado
durante las operaciones de edición.

Parte de la Fase 3A del motor de texto PDF.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple, Sequence, TYPE_CHECKING
import statistics

# Importaciones del módulo
if TYPE_CHECKING:
    import fitz

from .text_line import TextLine


class LeadingType(Enum):
    """Tipos de interlineado detectados."""
    SINGLE = auto()       # Interlineado simple (1.0-1.2x)
    ONE_HALF = auto()     # Interlineado 1.5x
    DOUBLE = auto()       # Interlineado doble
    CUSTOM = auto()       # Interlineado personalizado
    PARAGRAPH_BREAK = auto()  # Salto de párrafo (mayor que doble)
    UNKNOWN = auto()      # No se puede determinar


class AlignmentGrid(Enum):
    """Tipos de grid de alineación."""
    NONE = auto()         # Sin grid detectado
    REGULAR = auto()      # Grid regular uniforme
    BASELINE = auto()     # Grid de líneas base
    MODULAR = auto()      # Grid modular (bloques)


@dataclass
class BaselineInfo:
    """Información de una línea base individual."""
    y: float                      # Coordenada Y de la baseline
    font_size: float              # Tamaño de fuente en esta línea
    line_index: int               # Índice de la línea
    is_paragraph_start: bool = False  # Si es inicio de párrafo
    leading_from_prev: Optional[float] = None  # Interlineado desde anterior
    
    def distance_to(self, other: 'BaselineInfo') -> float:
        """Calcula la distancia a otra baseline."""
        return abs(self.y - other.y)


@dataclass
class ParagraphBreak:
    """Información de un salto de párrafo."""
    position: float         # Posición Y del salto
    size: float             # Tamaño del salto
    before_line: int        # Índice de línea antes del salto
    after_line: int         # Índice de línea después del salto
    
    @property
    def ratio_to_leading(self) -> float:
        """Ratio del salto respecto al interlineado normal."""
        # Asumimos leading normal de ~12pt si no hay referencia
        return self.size / 12.0


@dataclass
class BaselineAnalysis:
    """Resultado del análisis de baselines de una página."""
    baselines: List[BaselineInfo]           # Lista de baselines
    average_leading: float                  # Interlineado promedio
    leading_variance: float                 # Varianza del interlineado
    paragraph_breaks: List[ParagraphBreak]  # Posiciones de saltos
    leading_type: LeadingType               # Tipo de interlineado detectado
    grid_type: AlignmentGrid                # Tipo de grid detectado
    dominant_font_size: float               # Tamaño de fuente dominante
    
    # Estadísticas adicionales
    min_leading: float = 0.0
    max_leading: float = 0.0
    baseline_count: int = 0
    page_height: float = 0.0
    
    def get_leading_at(self, y: float) -> Optional[float]:
        """Obtiene el interlineado en una posición Y específica."""
        for i, bl in enumerate(self.baselines[:-1]):
            if bl.y <= y <= self.baselines[i + 1].y:
                return bl.leading_from_prev or self.average_leading
        return self.average_leading
    
    def get_nearest_baseline(self, y: float) -> Optional[BaselineInfo]:
        """Obtiene la baseline más cercana a una posición Y."""
        if not self.baselines:
            return None
        return min(self.baselines, key=lambda bl: abs(bl.y - y))
    
    def is_on_grid(self, y: float, tolerance: float = 1.0) -> bool:
        """Verifica si una posición está en el grid de baselines."""
        nearest = self.get_nearest_baseline(y)
        if nearest:
            return abs(nearest.y - y) <= tolerance
        return False


@dataclass
class LeadingAnalysis:
    """Análisis detallado del interlineado."""
    leading: float                  # Valor del interlineado
    type: LeadingType               # Tipo clasificado
    font_size_ratio: float          # Ratio respecto al tamaño de fuente
    is_consistent: bool             # Si es consistente con otras líneas
    
    @classmethod
    def classify(cls, leading: float, font_size: float) -> 'LeadingAnalysis':
        """Clasifica un interlineado según su valor y tamaño de fuente."""
        ratio = leading / font_size if font_size > 0 else 1.0
        
        # Determinar tipo según ratio
        if ratio < 0.5:
            lead_type = LeadingType.UNKNOWN
        elif ratio < 1.3:
            lead_type = LeadingType.SINGLE
        elif ratio < 1.7:
            lead_type = LeadingType.ONE_HALF
        elif ratio < 2.3:
            lead_type = LeadingType.DOUBLE
        elif ratio < 3.0:
            lead_type = LeadingType.PARAGRAPH_BREAK
        else:
            lead_type = LeadingType.CUSTOM
        
        return cls(
            leading=leading,
            type=lead_type,
            font_size_ratio=ratio,
            is_consistent=True  # Se determina después
        )


@dataclass
class BaselineTrackerConfig:
    """Configuración para el rastreador de baselines."""
    # Tolerancia para considerar dos baselines como alineadas
    alignment_tolerance: float = 1.0
    
    # Umbral para detectar salto de párrafo (ratio vs leading normal)
    paragraph_break_threshold: float = 1.8
    
    # Umbral mínimo de varianza para grid regular
    regular_grid_variance_threshold: float = 2.0
    
    # Número mínimo de líneas para análisis estadístico
    min_lines_for_stats: int = 3
    
    # Tolerancia para snap a baseline (puntos)
    snap_tolerance: float = 2.0
    
    # Factor de seguridad para cambios de altura
    height_change_safety_factor: float = 0.9


class BaselineTracker:
    """
    Rastrea baselines e interlineado para mantener la estructura vertical.
    
    Esta clase analiza la estructura de baselines de una página PDF y proporciona
    métodos para mantener la alineación durante la edición de texto.
    
    Attributes:
        page: Página PDF (fitz.Page)
        baselines: Lista de coordenadas Y de baselines
        line_spacings: Lista de interlineados detectados
        config: Configuración del tracker
    """
    
    def __init__(
        self, 
        page: Optional['fitz.Page'] = None,
        config: Optional[BaselineTrackerConfig] = None
    ):
        """
        Inicializa el tracker de baselines.
        
        Args:
            page: Página PDF a analizar (opcional)
            config: Configuración del tracker
        """
        self.page = page
        self.config = config or BaselineTrackerConfig()
        self.baselines: List[float] = []
        self.line_spacings: List[float] = []
        self._analysis: Optional[BaselineAnalysis] = None
        self._lines: List[TextLine] = []
    
    def set_lines(self, lines: Sequence[TextLine]) -> None:
        """
        Establece las líneas de texto para analizar.
        
        Args:
            lines: Secuencia de TextLine a analizar
        """
        self._lines = list(lines)
        self._analysis = None  # Invalidar análisis previo
    
    def analyze_page(
        self, 
        lines: Optional[Sequence[TextLine]] = None
    ) -> BaselineAnalysis:
        """
        Analiza la estructura de baselines de toda la página.
        
        Args:
            lines: Líneas de texto a analizar (opcional si ya se establecieron)
        
        Returns:
            BaselineAnalysis con información completa de baselines
        """
        if lines is not None:
            self._lines = list(lines)
        
        if not self._lines:
            # Retornar análisis vacío
            return BaselineAnalysis(
                baselines=[],
                average_leading=0.0,
                leading_variance=0.0,
                paragraph_breaks=[],
                leading_type=LeadingType.UNKNOWN,
                grid_type=AlignmentGrid.NONE,
                dominant_font_size=12.0,
                baseline_count=0
            )
        
        # Extraer baselines y font sizes de las líneas
        baseline_infos: List[BaselineInfo] = []
        leadings: List[float] = []
        font_sizes: List[float] = []
        
        sorted_lines = sorted(self._lines, key=lambda line: line.baseline_y)
        
        for i, line in enumerate(sorted_lines):
            avg_font_size = line.average_font_size if hasattr(line, 'average_font_size') else 12.0
            font_sizes.append(avg_font_size)
            
            # Calcular leading desde la línea anterior
            leading_from_prev = None
            if i > 0:
                prev_line = sorted_lines[i - 1]
                leading_from_prev = abs(line.baseline_y - prev_line.baseline_y)
                leadings.append(leading_from_prev)
            
            is_para_start = self._detect_paragraph_start(
                line, 
                sorted_lines[i - 1] if i > 0 else None,
                leading_from_prev
            )
            
            baseline_infos.append(BaselineInfo(
                y=line.baseline_y,
                font_size=avg_font_size,
                line_index=i,
                is_paragraph_start=is_para_start,
                leading_from_prev=leading_from_prev
            ))
        
        self.baselines = [bl.y for bl in baseline_infos]
        self.line_spacings = leadings
        
        # Calcular estadísticas
        avg_leading = statistics.mean(leadings) if leadings else 0.0
        lead_variance = statistics.variance(leadings) if len(leadings) > 1 else 0.0
        dominant_font_size = statistics.mode(font_sizes) if font_sizes else 12.0
        
        # Detectar saltos de párrafo
        paragraph_breaks = self._detect_paragraph_breaks(
            baseline_infos, avg_leading
        )
        
        # Clasificar tipo de interlineado
        leading_type = self._classify_leading(avg_leading, dominant_font_size)
        
        # Detectar tipo de grid
        grid_type = self._detect_grid_type(baseline_infos, lead_variance)
        
        # Construir análisis
        self._analysis = BaselineAnalysis(
            baselines=baseline_infos,
            average_leading=avg_leading,
            leading_variance=lead_variance,
            paragraph_breaks=paragraph_breaks,
            leading_type=leading_type,
            grid_type=grid_type,
            dominant_font_size=dominant_font_size,
            min_leading=min(leadings) if leadings else 0.0,
            max_leading=max(leadings) if leadings else 0.0,
            baseline_count=len(baseline_infos),
            page_height=self.page.rect.height if self.page else 842.0  # A4 default
        )
        
        return self._analysis
    
    def detect_leading(
        self, 
        line1: TextLine, 
        line2: TextLine
    ) -> float:
        """
        Detecta el interlineado entre dos líneas consecutivas.
        
        Método:
        1. Distancia entre baselines
        2. Si no disponible: inferir de font_size + espacio
        
        Args:
            line1: Primera línea (superior en página)
            line2: Segunda línea (inferior)
        
        Returns:
            Valor del interlineado en puntos
        """
        # Método primario: distancia entre baselines
        if line1.baseline_y is not None and line2.baseline_y is not None:
            return abs(line2.baseline_y - line1.baseline_y)
        
        # Método alternativo: inferir de bounding box
        bbox1 = line1.bounds
        bbox2 = line2.bounds
        
        if bbox1 and bbox2:
            # Distancia desde bottom de línea1 a top de línea2
            # más altura estimada del ascender
            return bbox2[3] - bbox1[1]  # y_max2 - y_min1
        
        # Fallback: usar tamaño de fuente * 1.2
        avg_size = (line1.average_font_size + line2.average_font_size) / 2
        return avg_size * 1.2
    
    def snap_to_baseline_grid(self, y: float) -> float:
        """
        Ajusta una coordenada Y al baseline más cercano.
        Útil para mantener alineación al editar.
        
        Args:
            y: Coordenada Y a ajustar
        
        Returns:
            Coordenada Y ajustada al baseline más cercano
        """
        if not self.baselines:
            return y
        
        # Encontrar baseline más cercano
        closest = min(self.baselines, key=lambda bl: abs(bl - y))
        
        # Solo hacer snap si está dentro de la tolerancia
        if abs(closest - y) <= self.config.snap_tolerance:
            return closest
        
        return y
    
    def calculate_new_position(
        self, 
        original_baseline: float, 
        text_height_change: float,
        preserve_grid: bool = True
    ) -> float:
        """
        Calcula nueva posición si el texto cambia de altura.
        
        Args:
            original_baseline: Baseline original
            text_height_change: Cambio de altura del texto (positivo = más alto)
            preserve_grid: Si debe preservar alineación con grid
        
        Returns:
            Nueva coordenada de baseline
        """
        # Aplicar factor de seguridad
        effective_change = text_height_change * self.config.height_change_safety_factor
        
        # Calcular nueva posición básica
        new_y = original_baseline + effective_change
        
        # Ajustar a grid si se solicita
        if preserve_grid:
            new_y = self.snap_to_baseline_grid(new_y)
        
        return new_y
    
    def get_leading_at_position(
        self, 
        y: float
    ) -> Tuple[float, LeadingType]:
        """
        Obtiene el interlineado en una posición específica.
        
        Args:
            y: Posición Y
        
        Returns:
            Tupla de (interlineado, tipo de interlineado)
        """
        if self._analysis:
            leading = self._analysis.get_leading_at(y) or self._analysis.average_leading
            return leading, self._analysis.leading_type
        
        # Valor por defecto si no hay análisis
        return 14.4, LeadingType.SINGLE  # 12pt * 1.2
    
    def find_insertion_point(
        self, 
        after_line_index: int,
        num_lines: int = 1
    ) -> List[float]:
        """
        Encuentra puntos de inserción para nuevas líneas.
        
        Args:
            after_line_index: Índice de línea después de la cual insertar
            num_lines: Número de líneas a insertar
        
        Returns:
            Lista de coordenadas Y para las nuevas baselines
        """
        if not self._analysis or not self._analysis.baselines:
            return [0.0] * num_lines
        
        baselines = self._analysis.baselines
        leading = self._analysis.average_leading
        
        if after_line_index < 0:
            # Insertar al principio
            start_y = baselines[0].y if baselines else 0.0
            return [start_y - leading * (i + 1) for i in range(num_lines)]
        
        if after_line_index >= len(baselines):
            # Insertar al final
            start_y = baselines[-1].y if baselines else 0.0
            return [start_y + leading * (i + 1) for i in range(num_lines)]
        
        # Insertar en medio
        current_bl = baselines[after_line_index]
        next_bl = baselines[after_line_index + 1] if after_line_index + 1 < len(baselines) else None
        
        if next_bl:
            # Calcular espaciado uniforme
            total_space = next_bl.y - current_bl.y
            step = total_space / (num_lines + 1)
            return [current_bl.y + step * (i + 1) for i in range(num_lines)]
        else:
            # Sin siguiente línea, usar leading promedio
            return [current_bl.y + leading * (i + 1) for i in range(num_lines)]
    
    def validate_leading(
        self, 
        proposed_leading: float
    ) -> Tuple[bool, str]:
        """
        Valida si un interlineado propuesto es razonable.
        
        Args:
            proposed_leading: Interlineado propuesto
        
        Returns:
            Tupla de (es_válido, mensaje)
        """
        if proposed_leading <= 0:
            return False, "Leading must be positive"
        
        if not self._analysis:
            return True, "No analysis available for comparison"
        
        avg = self._analysis.average_leading
        
        # Verificar que esté en rango razonable (50% - 300% del promedio)
        if proposed_leading < avg * 0.5:
            return False, f"Leading too small (< 50% of average {avg:.1f})"
        
        if proposed_leading > avg * 3.0:
            return False, f"Leading too large (> 300% of average {avg:.1f})"
        
        return True, "Leading is within acceptable range"
    
    def estimate_lines_that_fit(
        self, 
        available_height: float,
        font_size: Optional[float] = None
    ) -> int:
        """
        Estima cuántas líneas caben en una altura disponible.
        
        Args:
            available_height: Altura disponible en puntos
            font_size: Tamaño de fuente (usa dominante si no se especifica)
        
        Returns:
            Número estimado de líneas
        """
        if available_height <= 0:
            return 0
        
        # Determinar interlineado a usar
        if self._analysis:
            leading = self._analysis.average_leading
        else:
            font_size = font_size or 12.0
            leading = font_size * 1.2
        
        if leading <= 0:
            return 0
        
        return int(available_height / leading)
    
    def get_baseline_grid(
        self, 
        start_y: float,
        end_y: float,
        leading: Optional[float] = None
    ) -> List[float]:
        """
        Genera un grid de baselines entre dos posiciones.
        
        Args:
            start_y: Posición inicial
            end_y: Posición final
            leading: Interlineado (usa promedio si no se especifica)
        
        Returns:
            Lista de coordenadas Y del grid
        """
        if self._analysis:
            leading = leading or self._analysis.average_leading
        else:
            leading = leading or 14.4  # Default 12pt * 1.2
        
        if leading <= 0:
            return []
        
        grid = []
        current_y = start_y
        
        while current_y <= end_y:
            grid.append(current_y)
            current_y += leading
        
        return grid
    
    def align_to_existing_baselines(
        self, 
        y_positions: List[float]
    ) -> List[float]:
        """
        Alinea una lista de posiciones Y a baselines existentes.
        
        Args:
            y_positions: Lista de posiciones a alinear
        
        Returns:
            Lista de posiciones alineadas
        """
        return [self.snap_to_baseline_grid(y) for y in y_positions]
    
    # ========== Métodos privados ==========
    
    def _detect_paragraph_start(
        self,
        line: TextLine,
        prev_line: Optional[TextLine],
        leading: Optional[float]
    ) -> bool:
        """Detecta si una línea es inicio de párrafo."""
        if prev_line is None:
            return True  # Primera línea siempre es inicio
        
        if leading is None:
            return False
        
        # Comparar con leading promedio
        avg_leading = self._analysis.average_leading if self._analysis else 14.4
        
        # Si el leading es significativamente mayor, es salto de párrafo
        if leading > avg_leading * self.config.paragraph_break_threshold:
            return True
        
        # Verificar indentación
        if hasattr(line, 'bounds') and hasattr(prev_line, 'bounds'):
            if line.bounds and prev_line.bounds:
                indent_diff = line.bounds[0] - prev_line.bounds[0]
                if indent_diff > 20:  # Indentación significativa
                    return True
        
        return False
    
    def _detect_paragraph_breaks(
        self,
        baselines: List[BaselineInfo],
        avg_leading: float
    ) -> List[ParagraphBreak]:
        """Detecta saltos de párrafo en las baselines."""
        breaks = []
        threshold = avg_leading * self.config.paragraph_break_threshold
        
        for i, bl in enumerate(baselines[1:], 1):
            if bl.leading_from_prev and bl.leading_from_prev > threshold:
                breaks.append(ParagraphBreak(
                    position=(baselines[i - 1].y + bl.y) / 2,
                    size=bl.leading_from_prev,
                    before_line=i - 1,
                    after_line=i
                ))
        
        return breaks
    
    def _classify_leading(
        self, 
        avg_leading: float, 
        font_size: float
    ) -> LeadingType:
        """Clasifica el tipo de interlineado."""
        analysis = LeadingAnalysis.classify(avg_leading, font_size)
        return analysis.type
    
    def _detect_grid_type(
        self,
        baselines: List[BaselineInfo],
        variance: float
    ) -> AlignmentGrid:
        """Detecta el tipo de grid de alineación."""
        if len(baselines) < self.config.min_lines_for_stats:
            return AlignmentGrid.NONE
        
        # Si la varianza es baja, es grid regular
        if variance < self.config.regular_grid_variance_threshold:
            return AlignmentGrid.REGULAR
        
        # Verificar si hay pattern de grid modular
        leadings = [bl.leading_from_prev for bl in baselines[1:] if bl.leading_from_prev]
        if leadings:
            unique_leadings = set(round(lead, 1) for lead in leadings)
            if len(unique_leadings) <= 2:
                return AlignmentGrid.MODULAR
        
        return AlignmentGrid.BASELINE


# ========== Funciones de utilidad ==========

def analyze_page_baselines(
    lines: Sequence[TextLine],
    config: Optional[BaselineTrackerConfig] = None
) -> BaselineAnalysis:
    """
    Analiza las baselines de una página.
    
    Args:
        lines: Líneas de texto de la página
        config: Configuración del tracker
    
    Returns:
        BaselineAnalysis con información de baselines
    """
    tracker = BaselineTracker(config=config)
    return tracker.analyze_page(lines)


def calculate_leading(
    line1: TextLine, 
    line2: TextLine
) -> float:
    """
    Calcula el interlineado entre dos líneas.
    
    Args:
        line1: Primera línea
        line2: Segunda línea
    
    Returns:
        Interlineado en puntos
    """
    tracker = BaselineTracker()
    return tracker.detect_leading(line1, line2)


def snap_to_grid(
    y: float, 
    baselines: List[float], 
    tolerance: float = 2.0
) -> float:
    """
    Ajusta una coordenada Y al baseline más cercano.
    
    Args:
        y: Coordenada Y
        baselines: Lista de baselines
        tolerance: Tolerancia de snap
    
    Returns:
        Coordenada ajustada
    """
    if not baselines:
        return y
    
    closest = min(baselines, key=lambda bl: abs(bl - y))
    if abs(closest - y) <= tolerance:
        return closest
    return y


def generate_baseline_grid(
    start_y: float,
    end_y: float,
    leading: float
) -> List[float]:
    """
    Genera un grid de baselines.
    
    Args:
        start_y: Posición inicial
        end_y: Posición final
        leading: Interlineado
    
    Returns:
        Lista de coordenadas Y
    """
    if leading <= 0 or start_y >= end_y:
        return []
    
    grid_points = []
    current_y = start_y
    while current_y <= end_y:
        grid_points.append(current_y)
        current_y += leading
    return grid_points


def estimate_baseline_from_bbox(
    bbox: Tuple[float, float, float, float],
    font_size: float,
    ascender_ratio: float = 0.8
) -> float:
    """
    Estima la baseline desde un bounding box.
    
    Args:
        bbox: Bounding box (x0, y0, x1, y1)
        font_size: Tamaño de fuente
        ascender_ratio: Ratio del ascender (típicamente ~0.8)
    
    Returns:
        Coordenada Y estimada de la baseline
    """
    y0, y1 = bbox[1], bbox[3]
    height = y1 - y0
    
    # La baseline está aproximadamente a ascender_ratio desde arriba
    return y0 + height * ascender_ratio


def classify_leading_type(leading: float, font_size: float) -> LeadingType:
    """
    Clasifica un interlineado según su tipo.
    
    Args:
        leading: Valor del interlineado
        font_size: Tamaño de fuente
    
    Returns:
        LeadingType clasificado
    """
    return LeadingAnalysis.classify(leading, font_size).type


def find_paragraph_breaks_in_baselines(
    baselines: List[float],
    threshold_ratio: float = 1.8
) -> List[int]:
    """
    Encuentra índices donde hay saltos de párrafo.
    
    Args:
        baselines: Lista de coordenadas Y de baselines
        threshold_ratio: Ratio umbral vs leading normal
    
    Returns:
        Lista de índices donde hay saltos de párrafo
    """
    if len(baselines) < 2:
        return []
    
    # Calcular leadings
    leadings = [baselines[i + 1] - baselines[i] for i in range(len(baselines) - 1)]
    avg_leading = statistics.mean(leadings) if leadings else 0.0
    
    if avg_leading <= 0:
        return []
    
    # Encontrar saltos
    threshold = avg_leading * threshold_ratio
    breaks = [i + 1 for i, lead in enumerate(leadings) if lead > threshold]
    
    return breaks


def validate_baseline_consistency(
    baselines: List[float],
    tolerance: float = 2.0
) -> Tuple[bool, List[int]]:
    """
    Valida la consistencia de un conjunto de baselines.
    
    Args:
        baselines: Lista de coordenadas Y
        tolerance: Tolerancia de variación
    
    Returns:
        Tupla de (es_consistente, índices_inconsistentes)
    """
    if len(baselines) < 2:
        return True, []
    
    # Calcular leadings
    leadings = [baselines[i + 1] - baselines[i] for i in range(len(baselines) - 1)]
    
    if not leadings:
        return True, []
    
    avg_leading = statistics.mean(leadings)
    
    # Encontrar inconsistencias
    inconsistent = []
    for i, lead in enumerate(leadings):
        deviation = abs(lead - avg_leading)
        if deviation > tolerance:
            inconsistent.append(i)
    
    return len(inconsistent) == 0, inconsistent


__all__ = [
    # Enums
    'LeadingType',
    'AlignmentGrid',
    
    # Dataclasses
    'BaselineInfo',
    'ParagraphBreak',
    'BaselineAnalysis',
    'LeadingAnalysis',
    'BaselineTrackerConfig',
    
    # Clase principal
    'BaselineTracker',
    
    # Funciones de utilidad
    'analyze_page_baselines',
    'calculate_leading',
    'snap_to_grid',
    'generate_baseline_grid',
    'estimate_baseline_from_bbox',
    'classify_leading_type',
    'find_paragraph_breaks_in_baselines',
    'validate_baseline_consistency',
]

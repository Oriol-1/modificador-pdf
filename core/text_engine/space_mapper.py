"""
SpaceMapper - Mapeo y análisis de espacios en texto PDF.

Este módulo maneja la complejidad de los espacios en PDFs:
- En PDF, los espacios pueden ser caracteres reales o gaps implícitos
- Los operadores TJ pueden incluir ajustes de posición negativos
- Word spacing (Tw) afecta solo a caracteres espacio reales
- Tabulaciones no existen como tal, son gaps grandes

El módulo proporciona:
- SpaceMapper: Analizador principal de espacios
- SpaceAnalysis: Resultado del análisis de una línea
- SpaceInfo: Información sobre un espacio individual
- Utilidades para reconstruir y preservar espaciado
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
import statistics

# Import sibling modules
try:
    from .text_line import TextLine
    from .text_span import TextSpanMetrics
except ImportError:
    from text_line import TextLine
    from text_span import TextSpanMetrics


class SpaceType(Enum):
    """Tipo de espacio detectado."""
    REAL_SPACE = "real_space"       # Carácter U+0020 real
    VIRTUAL_SPACE = "virtual_space"  # Gap sin carácter
    TAB = "tab"                      # Espacio grande (~4+ espacios)
    WORD_SPACING = "word_spacing"    # Ajuste Tw aplicado
    TJ_ADJUSTMENT = "tj_adjustment"  # Ajuste negativo en TJ
    NBSP = "nbsp"                    # Non-breaking space U+00A0
    UNKNOWN = "unknown"              # Tipo indeterminado


@dataclass
class SpaceInfo:
    """
    Información detallada sobre un espacio individual.
    
    Attributes:
        space_type: Tipo de espacio detectado
        x_start: Posición X inicial del espacio
        x_end: Posición X final del espacio
        width: Ancho del espacio en puntos
        char_index: Índice del carácter en el texto (si aplica)
        span_index: Índice del span donde está el espacio
        is_inter_span: True si el espacio está entre spans
        source: Fuente del espacio ("char", "gap", "tw", "tj")
    """
    space_type: SpaceType = SpaceType.UNKNOWN
    x_start: float = 0.0
    x_end: float = 0.0
    width: float = 0.0
    char_index: Optional[int] = None
    span_index: int = 0
    is_inter_span: bool = False
    source: str = "unknown"
    
    @property
    def is_real(self) -> bool:
        """True si es un carácter espacio real."""
        return self.space_type in (SpaceType.REAL_SPACE, SpaceType.NBSP)
    
    @property
    def is_virtual(self) -> bool:
        """True si es un gap sin carácter."""
        return self.space_type in (
            SpaceType.VIRTUAL_SPACE,
            SpaceType.TAB,
            SpaceType.TJ_ADJUSTMENT
        )
    
    @property
    def is_word_boundary(self) -> bool:
        """True si este espacio marca un límite de palabra."""
        return self.width > 0 and self.space_type != SpaceType.TJ_ADJUSTMENT


@dataclass
class WordBoundary:
    """Información sobre un límite de palabra."""
    x_position: float = 0.0
    char_index: int = 0
    word_before: str = ""
    word_after: str = ""
    space_width: float = 0.0


@dataclass
class SpaceAnalysis:
    """
    Resultado del análisis de espacios en una línea.
    
    Attributes:
        line_id: ID de la línea analizada
        real_spaces: Lista de espacios como caracteres reales
        virtual_spaces: Lista de gaps sin carácter
        probable_tabs: Lista de espacios grandes (tabulaciones)
        word_boundaries: Posiciones de separación de palabras
        total_space_count: Número total de espacios detectados
        average_space_width: Ancho promedio de espacios
        space_variance: Variación en anchos de espacio
        has_consistent_spacing: True si todos los espacios son similares
    """
    line_id: str = ""
    real_spaces: List[SpaceInfo] = field(default_factory=list)
    virtual_spaces: List[SpaceInfo] = field(default_factory=list)
    probable_tabs: List[SpaceInfo] = field(default_factory=list)
    word_boundaries: List[WordBoundary] = field(default_factory=list)
    
    # Estadísticas
    total_space_count: int = 0
    average_space_width: float = 0.0
    space_variance: float = 0.0
    has_consistent_spacing: bool = True
    
    @property
    def all_spaces(self) -> List[SpaceInfo]:
        """Todos los espacios ordenados por posición X."""
        all_sp = self.real_spaces + self.virtual_spaces + self.probable_tabs
        return sorted(all_sp, key=lambda s: s.x_start)
    
    @property
    def word_count(self) -> int:
        """Número de palabras (boundaries + 1)."""
        return len(self.word_boundaries) + 1 if self.word_boundaries else 1
    
    def get_space_at_index(self, char_index: int) -> Optional[SpaceInfo]:
        """Obtiene el espacio en un índice de carácter."""
        for space in self.all_spaces:
            if space.char_index == char_index:
                return space
        return None
    
    def get_space_at_x(self, x: float, tolerance: float = 1.0) -> Optional[SpaceInfo]:
        """Obtiene el espacio en una posición X."""
        for space in self.all_spaces:
            if space.x_start - tolerance <= x <= space.x_end + tolerance:
                return space
        return None


@dataclass
class SpaceMapperConfig:
    """Configuración para el mapeo de espacios."""
    
    # Umbral mínimo para considerar un gap como espacio
    min_space_width: float = 1.0
    
    # Umbral para considerar un espacio como tabulación
    # (múltiplo del ancho promedio de espacio)
    tab_threshold_multiplier: float = 3.5
    
    # Ancho de espacio por defecto (si no se puede calcular)
    default_space_width: float = 3.0
    
    # Tolerancia para considerar espacios "consistentes"
    consistency_tolerance: float = 1.5
    
    # Usar word_spacing (Tw) del span si está disponible
    use_word_spacing: bool = True
    
    # Considerar ajustes TJ como espacios virtuales
    include_tj_adjustments: bool = True


class SpaceMapper:
    """
    Mapea espacios y tabulaciones en texto PDF.
    
    En PDF, los espacios pueden manifestarse de varias formas:
    1. Caracteres reales (U+0020, U+00A0)
    2. Gaps de posición X (entre spans o por posicionamiento)
    3. Ajustes negativos en operador TJ
    4. Word spacing (Tw) que solo afecta a caracteres espacio
    
    Esta clase analiza todas estas fuentes para proporcionar
    una vista unificada del espaciado en una línea de texto.
    """
    
    def __init__(self, config: Optional[SpaceMapperConfig] = None):
        """
        Inicializa el SpaceMapper.
        
        Args:
            config: Configuración opcional (usa valores por defecto si None)
        """
        self.config = config or SpaceMapperConfig()
    
    def analyze_line(self, line: TextLine) -> SpaceAnalysis:
        """
        Analiza los espacios en una línea de texto.
        
        Args:
            line: Línea a analizar
            
        Returns:
            SpaceAnalysis con información detallada de espacios
        """
        analysis = SpaceAnalysis(line_id=line.line_id)
        
        if not line.spans:
            return analysis
        
        # 1. Analizar espacios dentro de cada span
        char_offset = 0
        for span_idx, span in enumerate(line.spans):
            intra_spaces = self._analyze_intra_span_spaces(
                span, span_idx, char_offset
            )
            for space in intra_spaces:
                self._categorize_space(space, analysis)
            char_offset += len(span.text)
        
        # 2. Analizar gaps entre spans
        inter_spaces = self._analyze_inter_span_gaps(line)
        for space in inter_spaces:
            self._categorize_space(space, analysis)
        
        # 3. Detectar límites de palabras
        analysis.word_boundaries = self._detect_word_boundaries(line, analysis)
        
        # 4. Calcular estadísticas
        self._calculate_statistics(analysis)
        
        return analysis
    
    def _analyze_intra_span_spaces(
        self,
        span: TextSpanMetrics,
        span_index: int,
        char_offset: int
    ) -> List[SpaceInfo]:
        """Analiza espacios dentro de un span."""
        spaces: List[SpaceInfo] = []
        text = span.text
        
        if not text:
            return spaces
        
        # Calcular ancho promedio de carácter para estimaciones
        avg_char_width = span.width / len(text) if len(text) > 0 else self.config.default_space_width
        
        # Buscar caracteres espacio en el texto
        for i, char in enumerate(text):
            if char == ' ':
                # Espacio real
                space_width = avg_char_width
                
                # Si tenemos char_widths, usar el ancho real
                if span.char_widths and i < len(span.char_widths):
                    space_width = span.char_widths[i]
                
                # Añadir word_spacing si aplica
                if self.config.use_word_spacing and span.word_spacing > 0:
                    space_width += span.word_spacing
                
                # Estimar posición X
                x_start = span.bbox[0] + (i * avg_char_width)
                
                spaces.append(SpaceInfo(
                    space_type=SpaceType.REAL_SPACE,
                    x_start=x_start,
                    x_end=x_start + space_width,
                    width=space_width,
                    char_index=char_offset + i,
                    span_index=span_index,
                    is_inter_span=False,
                    source="char"
                ))
            
            elif char == '\u00A0':
                # Non-breaking space
                space_width = avg_char_width
                if span.char_widths and i < len(span.char_widths):
                    space_width = span.char_widths[i]
                
                x_start = span.bbox[0] + (i * avg_char_width)
                
                spaces.append(SpaceInfo(
                    space_type=SpaceType.NBSP,
                    x_start=x_start,
                    x_end=x_start + space_width,
                    width=space_width,
                    char_index=char_offset + i,
                    span_index=span_index,
                    is_inter_span=False,
                    source="char"
                ))
            
            elif char == '\t':
                # Tabulación (rara en PDFs pero posible)
                tab_width = avg_char_width * 4  # Aproximación
                x_start = span.bbox[0] + (i * avg_char_width)
                
                spaces.append(SpaceInfo(
                    space_type=SpaceType.TAB,
                    x_start=x_start,
                    x_end=x_start + tab_width,
                    width=tab_width,
                    char_index=char_offset + i,
                    span_index=span_index,
                    is_inter_span=False,
                    source="char"
                ))
        
        return spaces
    
    def _analyze_inter_span_gaps(self, line: TextLine) -> List[SpaceInfo]:
        """Analiza gaps entre spans consecutivos."""
        gaps: List[SpaceInfo] = []
        
        if len(line.spans) < 2:
            return gaps
        
        char_offset = 0
        for i in range(len(line.spans) - 1):
            current_span = line.spans[i]
            next_span = line.spans[i + 1]
            
            # Calcular gap
            gap_start = current_span.bbox[2]  # x_end del span actual
            gap_end = next_span.bbox[0]       # x_start del siguiente
            gap_width = gap_end - gap_start
            
            char_offset += len(current_span.text)
            
            # Ignorar gaps negativos (spans superpuestos)
            if gap_width < self.config.min_space_width:
                continue
            
            # Determinar tipo de espacio
            space_type = self._classify_gap(gap_width, line)
            
            gaps.append(SpaceInfo(
                space_type=space_type,
                x_start=gap_start,
                x_end=gap_end,
                width=gap_width,
                char_index=char_offset,  # Posición entre los dos spans
                span_index=i,
                is_inter_span=True,
                source="gap"
            ))
        
        return gaps
    
    def _classify_gap(self, gap_width: float, line: TextLine) -> SpaceType:
        """Clasifica un gap según su tamaño."""
        # Estimar ancho de espacio normal
        normal_space_width = self._estimate_space_width(line)
        
        # Umbral para tabulación
        tab_threshold = normal_space_width * self.config.tab_threshold_multiplier
        
        if gap_width >= tab_threshold:
            return SpaceType.TAB
        elif gap_width >= self.config.min_space_width:
            return SpaceType.VIRTUAL_SPACE
        else:
            return SpaceType.TJ_ADJUSTMENT
    
    def _estimate_space_width(self, line: TextLine) -> float:
        """Estima el ancho de un espacio normal para la línea."""
        if not line.spans:
            return self.config.default_space_width
        
        # Promedio de anchos de carácter de los spans
        total_width = 0.0
        total_chars = 0
        
        for span in line.spans:
            if span.text:
                total_width += span.width
                total_chars += len(span.text)
        
        if total_chars == 0:
            return self.config.default_space_width
        
        avg_char_width = total_width / total_chars
        
        # Espacio típicamente es ~25-35% del ancho de fuente
        return avg_char_width * 0.3
    
    def _categorize_space(self, space: SpaceInfo, analysis: SpaceAnalysis) -> None:
        """Categoriza un espacio en la lista apropiada del análisis."""
        if space.space_type == SpaceType.TAB:
            analysis.probable_tabs.append(space)
        elif space.space_type in (SpaceType.REAL_SPACE, SpaceType.NBSP):
            analysis.real_spaces.append(space)
        else:
            analysis.virtual_spaces.append(space)
    
    def _detect_word_boundaries(
        self,
        line: TextLine,
        analysis: SpaceAnalysis
    ) -> List[WordBoundary]:
        """Detecta los límites de palabras basándose en espacios."""
        boundaries: List[WordBoundary] = []
        full_text = line.text
        
        if not full_text:
            return boundaries
        
        # Usar todos los espacios como posibles límites
        for space in analysis.all_spaces:
            if not space.is_word_boundary:
                continue
            
            char_idx = space.char_index
            if char_idx is None or char_idx <= 0 or char_idx >= len(full_text):
                continue
            
            # Extraer palabras antes y después
            text_before = full_text[:char_idx].split()
            text_after = full_text[char_idx:].split()
            
            word_before = text_before[-1] if text_before else ""
            word_after = text_after[0] if text_after else ""
            
            boundaries.append(WordBoundary(
                x_position=space.x_start,
                char_index=char_idx,
                word_before=word_before,
                word_after=word_after,
                space_width=space.width
            ))
        
        return boundaries
    
    def _calculate_statistics(self, analysis: SpaceAnalysis) -> None:
        """Calcula estadísticas sobre los espacios."""
        all_spaces = analysis.all_spaces
        
        analysis.total_space_count = len(all_spaces)
        
        if not all_spaces:
            return
        
        widths = [s.width for s in all_spaces if s.width > 0]
        
        if widths:
            analysis.average_space_width = statistics.mean(widths)
            
            if len(widths) > 1:
                analysis.space_variance = statistics.variance(widths)
                # Consistente si la varianza es pequeña relativa al promedio
                analysis.has_consistent_spacing = (
                    analysis.space_variance < 
                    (analysis.average_space_width * self.config.consistency_tolerance) ** 2
                )
            else:
                analysis.space_variance = 0.0
                analysis.has_consistent_spacing = True
    
    def reconstruct_with_spaces(
        self,
        line: TextLine,
        normalize_spaces: bool = True
    ) -> str:
        """
        Reconstruye el texto de una línea con espacios apropiados.
        
        Convierte gaps virtuales en espacios según los umbrales configurados.
        
        Args:
            line: Línea a reconstruir
            normalize_spaces: Si True, normaliza múltiples espacios a uno
            
        Returns:
            Texto reconstruido con espacios
        """
        if not line.spans:
            return ""
        
        analysis = self.analyze_line(line)
        result_parts: List[str] = []
        
        for i, span in enumerate(line.spans):
            result_parts.append(span.text)
            
            # Buscar gap después de este span
            for space in analysis.all_spaces:
                if space.is_inter_span and space.span_index == i:
                    # Añadir espacio(s) apropiado(s)
                    if space.space_type == SpaceType.TAB:
                        if normalize_spaces:
                            result_parts.append("    ")  # 4 espacios para tab
                        else:
                            result_parts.append("\t")
                    else:
                        result_parts.append(" ")
        
        text = "".join(result_parts)
        
        if normalize_spaces:
            # Normalizar múltiples espacios consecutivos
            while "  " in text:
                text = text.replace("  ", " ")
        
        return text
    
    def preserve_spacing_for_edit(
        self,
        original_line: TextLine,
        new_text: str
    ) -> List[Dict[str, Any]]:
        """
        Genera instrucciones para mantener el espaciado al editar.
        
        Útil cuando se reemplaza texto pero se quiere preservar
        la estructura de espaciado original.
        
        Args:
            original_line: Línea original
            new_text: Nuevo texto a insertar
            
        Returns:
            Lista de instrucciones de espaciado
        """
        instructions: List[Dict[str, Any]] = []
        
        original_analysis = self.analyze_line(original_line)
        original_text = original_line.text
        
        if not original_text or not new_text:
            return instructions
        
        # Calcular ratio de cambio de longitud
        length_ratio = len(new_text) / len(original_text) if original_text else 1.0
        
        # Generar instrucciones para preservar espacios
        for space in original_analysis.all_spaces:
            if space.char_index is None:
                continue
            
            # Escalar posición al nuevo texto
            new_char_index = int(space.char_index * length_ratio)
            new_char_index = min(new_char_index, len(new_text) - 1)
            new_char_index = max(new_char_index, 0)
            
            instructions.append({
                'action': 'preserve_space',
                'original_index': space.char_index,
                'new_index': new_char_index,
                'space_type': space.space_type.value,
                'original_width': space.width,
                'preserve_width': space.space_type == SpaceType.TAB,
            })
        
        return instructions
    
    def calculate_text_fit(
        self,
        available_width: float,
        text: str,
        avg_char_width: float = 7.0
    ) -> Dict[str, Any]:
        """
        Calcula si un texto cabe en un ancho dado.
        
        Args:
            available_width: Ancho disponible en puntos
            text: Texto a evaluar
            avg_char_width: Ancho promedio de carácter (estimación)
            
        Returns:
            Dict con información de ajuste
        """
        estimated_width = len(text) * avg_char_width
        
        fits = estimated_width <= available_width
        overflow = max(0, estimated_width - available_width)
        utilization = estimated_width / available_width if available_width > 0 else 0
        
        # Calcular cuántos caracteres caben
        chars_that_fit = int(available_width / avg_char_width) if avg_char_width > 0 else 0
        
        return {
            'fits': fits,
            'estimated_width': estimated_width,
            'available_width': available_width,
            'overflow': overflow,
            'utilization': utilization,
            'chars_that_fit': chars_that_fit,
            'original_length': len(text),
            'needs_truncation': not fits,
        }
    
    def suggest_line_breaks(
        self,
        text: str,
        max_width: float,
        avg_char_width: float = 7.0
    ) -> List[int]:
        """
        Sugiere posiciones para romper una línea larga.
        
        Args:
            text: Texto a dividir
            max_width: Ancho máximo por línea
            avg_char_width: Ancho promedio de carácter
            
        Returns:
            Lista de índices donde romper
        """
        if not text:
            return []
        
        chars_per_line = int(max_width / avg_char_width) if avg_char_width > 0 else 80
        
        if len(text) <= chars_per_line:
            return []
        
        breaks: List[int] = []
        current_pos = 0
        
        while current_pos < len(text):
            # Buscar el último espacio antes del límite
            end_pos = min(current_pos + chars_per_line, len(text))
            
            if end_pos >= len(text):
                break
            
            # Buscar espacio para romper
            break_pos = text.rfind(' ', current_pos, end_pos)
            
            if break_pos <= current_pos:
                # No hay espacio, forzar el corte
                break_pos = end_pos
            
            breaks.append(break_pos)
            current_pos = break_pos + 1
        
        return breaks


# === Funciones de utilidad ===

def analyze_line_spacing(line: TextLine, config: Optional[SpaceMapperConfig] = None) -> SpaceAnalysis:
    """
    Función de conveniencia para analizar espaciado de una línea.
    
    Args:
        line: Línea a analizar
        config: Configuración opcional
        
    Returns:
        SpaceAnalysis con información de espacios
    """
    mapper = SpaceMapper(config)
    return mapper.analyze_line(line)


def reconstruct_line_text(
    line: TextLine,
    normalize: bool = True,
    config: Optional[SpaceMapperConfig] = None
) -> str:
    """
    Reconstruye el texto de una línea con espacios apropiados.
    
    Args:
        line: Línea a reconstruir
        normalize: Si normalizar espacios múltiples
        config: Configuración opcional
        
    Returns:
        Texto reconstruido
    """
    mapper = SpaceMapper(config)
    return mapper.reconstruct_with_spaces(line, normalize)


def count_words_in_line(line: TextLine, config: Optional[SpaceMapperConfig] = None) -> int:
    """
    Cuenta las palabras en una línea basándose en análisis de espacios.
    
    Args:
        line: Línea a analizar
        config: Configuración opcional
        
    Returns:
        Número de palabras
    """
    mapper = SpaceMapper(config)
    analysis = mapper.analyze_line(line)
    return analysis.word_count


def estimate_character_positions(
    span: TextSpanMetrics
) -> List[Tuple[float, float]]:
    """
    Estima las posiciones X de cada carácter en un span.
    
    Args:
        span: Span a analizar
        
    Returns:
        Lista de tuplas (x_start, x_end) para cada carácter
    """
    if not span.text:
        return []
    
    positions: List[Tuple[float, float]] = []
    char_count = len(span.text)
    
    if span.char_widths and len(span.char_widths) == char_count:
        # Usar anchos reales
        x = span.bbox[0]
        for width in span.char_widths:
            positions.append((x, x + width))
            x += width
    else:
        # Estimar anchos uniformes
        avg_width = span.width / char_count if char_count > 0 else 0
        x = span.bbox[0]
        for _ in range(char_count):
            positions.append((x, x + avg_width))
            x += avg_width
    
    return positions


def find_char_at_x(
    span: TextSpanMetrics,
    x: float,
    tolerance: float = 1.0
) -> Optional[int]:
    """
    Encuentra el índice del carácter en una posición X.
    
    Args:
        span: Span a buscar
        x: Coordenada X
        tolerance: Tolerancia de matching
        
    Returns:
        Índice del carácter o None si no se encuentra
    """
    positions = estimate_character_positions(span)
    
    for i, (x_start, x_end) in enumerate(positions):
        if x_start - tolerance <= x <= x_end + tolerance:
            return i
    
    return None


def calculate_space_metrics(analysis: SpaceAnalysis) -> Dict[str, Any]:
    """
    Calcula métricas detalladas sobre el espaciado.
    
    Args:
        analysis: Análisis de espacios
        
    Returns:
        Diccionario con métricas
    """
    all_spaces = analysis.all_spaces
    
    if not all_spaces:
        return {
            'total_spaces': 0,
            'real_space_count': 0,
            'virtual_space_count': 0,
            'tab_count': 0,
            'avg_width': 0.0,
            'min_width': 0.0,
            'max_width': 0.0,
            'total_space_width': 0.0,
        }
    
    widths = [s.width for s in all_spaces]
    
    return {
        'total_spaces': len(all_spaces),
        'real_space_count': len(analysis.real_spaces),
        'virtual_space_count': len(analysis.virtual_spaces),
        'tab_count': len(analysis.probable_tabs),
        'avg_width': statistics.mean(widths) if widths else 0.0,
        'min_width': min(widths) if widths else 0.0,
        'max_width': max(widths) if widths else 0.0,
        'total_space_width': sum(widths),
        'word_count': analysis.word_count,
        'has_consistent_spacing': analysis.has_consistent_spacing,
    }

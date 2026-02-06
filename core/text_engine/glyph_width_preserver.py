"""
GlyphWidthPreserver - Preservación de anchos de glifos al editar texto.

Este módulo asegura que las ediciones de texto mantengan la maquetación
original del documento, preservando los anchos exactos de los glifos.

Funcionalidades:
- Cálculo preciso de anchos de texto original y editado
- Estrategias de ajuste para mantener misma anchura
- Compensación mediante espaciado (tracking, kerning)
- Validación de espacio disponible
- Generación de operadores de posicionamiento (Tj, TJ arrays)

PHASE3-3D04: Preservar anchos de glifos al editar (4h estimado)
Dependencia: 3A-10 (EmbeddedFontExtractor)
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)


# ================== Enums ==================


class FitStrategy(Enum):
    """
    Estrategias para ajustar texto al espacio disponible.
    """
    EXACT = auto()          # Ajustar exactamente (modificar espaciado)
    COMPRESS = auto()       # Comprimir si es más largo
    EXPAND = auto()         # Expandir si es más corto
    TRUNCATE = auto()       # Truncar si no cabe
    ELLIPSIS = auto()       # Truncar con elipsis (...)
    SCALE = auto()          # Escalar horizontalmente
    ALLOW_OVERFLOW = auto() # Permitir desbordamiento
    

class FitResult(Enum):
    """Resultado del ajuste de texto."""
    SUCCESS = auto()        # Ajuste exitoso, texto cabe perfectamente
    COMPRESSED = auto()     # Texto comprimido para caber
    EXPANDED = auto()       # Texto expandido para llenar espacio
    TRUNCATED = auto()      # Texto truncado
    SCALED = auto()         # Texto escalado horizontalmente
    OVERFLOW = auto()       # Texto desborda (con ALLOW_OVERFLOW)
    FAILED = auto()         # No se pudo ajustar


class AdjustmentType(Enum):
    """Tipo de ajuste aplicado."""
    NONE = auto()           # Sin ajuste
    TRACKING = auto()       # Espaciado uniforme entre caracteres
    KERNING = auto()        # Ajuste de pares específicos
    WORD_SPACING = auto()   # Espaciado entre palabras
    HORIZONTAL_SCALE = auto()  # Escalado horizontal
    COMBINED = auto()       # Combinación de ajustes


class WidthUnit(Enum):
    """Unidades de medida para anchos."""
    POINTS = auto()         # Puntos (1/72 pulgada)
    FONT_UNITS = auto()     # Unidades de fuente (típicamente 1/1000 em)
    EM = auto()             # Unidades em
    PERCENT = auto()        # Porcentaje del ancho original


# ================== Dataclasses ==================


@dataclass
class GlyphWidth:
    """
    Ancho de un glifo individual.
    """
    char: str                   # Carácter
    char_code: int              # Código del carácter
    width_font_units: float     # Ancho en unidades de fuente
    width_points: float         # Ancho en puntos (calculado)
    glyph_name: str = ""        # Nombre del glifo (si se conoce)
    is_space: bool = False      # Si es un espacio
    
    @property
    def is_whitespace(self) -> bool:
        """Verifica si es espacio en blanco."""
        return self.char.isspace()


@dataclass
class TextWidthInfo:
    """
    Información de ancho de un segmento de texto.
    """
    text: str                       # Texto medido
    total_width_points: float       # Ancho total en puntos
    total_width_font_units: float   # Ancho total en unidades de fuente
    char_widths: List[GlyphWidth]   # Anchos individuales
    
    # Métricas de fuente
    font_name: str = ""
    font_size: float = 12.0
    units_per_em: int = 1000
    
    # Estadísticas
    char_count: int = 0
    space_count: int = 0
    avg_char_width: float = 0.0
    
    def __post_init__(self):
        """Calcula estadísticas."""
        self.char_count = len(self.text)
        self.space_count = sum(1 for cw in self.char_widths if cw.is_whitespace)
        if self.char_count > 0:
            self.avg_char_width = self.total_width_points / self.char_count
    
    @property
    def non_space_width(self) -> float:
        """Ancho excluyendo espacios."""
        return sum(cw.width_points for cw in self.char_widths if not cw.is_whitespace)
    
    @property
    def space_width(self) -> float:
        """Ancho total de espacios."""
        return sum(cw.width_points for cw in self.char_widths if cw.is_whitespace)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario."""
        return {
            'text': self.text,
            'total_width_points': self.total_width_points,
            'total_width_font_units': self.total_width_font_units,
            'font_name': self.font_name,
            'font_size': self.font_size,
            'char_count': self.char_count,
            'space_count': self.space_count,
            'avg_char_width': self.avg_char_width,
        }


@dataclass
class SpacingAdjustment:
    """
    Ajuste de espaciado calculado.
    """
    adjustment_type: AdjustmentType
    
    # Valores de ajuste
    tracking: float = 0.0           # Espaciado uniforme (puntos)
    word_spacing: float = 0.0       # Espaciado de palabras adicional
    horizontal_scale: float = 100.0  # Escala horizontal (%)
    
    # Para TJ arrays
    kerning_pairs: List[Tuple[int, float]] = field(default_factory=list)
    
    # Métricas
    total_adjustment: float = 0.0   # Ajuste total aplicado
    adjustment_per_char: float = 0.0
    adjustment_per_space: float = 0.0
    
    @property
    def has_adjustment(self) -> bool:
        """Verifica si hay algún ajuste."""
        return (
            self.tracking != 0 or
            self.word_spacing != 0 or
            self.horizontal_scale != 100.0 or
            len(self.kerning_pairs) > 0
        )
    
    def to_pdf_operators(self) -> List[str]:
        """
        Genera operadores PDF para aplicar el ajuste.
        
        Returns:
            Lista de operadores PDF
        """
        operators = []
        
        if self.tracking != 0:
            # Tc - Character spacing
            operators.append(f"{self.tracking:.4f} Tc")
        
        if self.word_spacing != 0:
            # Tw - Word spacing
            operators.append(f"{self.word_spacing:.4f} Tw")
        
        if self.horizontal_scale != 100.0:
            # Tz - Horizontal scaling
            operators.append(f"{self.horizontal_scale:.4f} Tz")
        
        return operators
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario."""
        return {
            'adjustment_type': self.adjustment_type.name,
            'tracking': self.tracking,
            'word_spacing': self.word_spacing,
            'horizontal_scale': self.horizontal_scale,
            'kerning_pairs': self.kerning_pairs,
            'total_adjustment': self.total_adjustment,
        }


@dataclass
class FitAnalysis:
    """
    Análisis de ajuste de texto.
    """
    # Textos
    original_text: str
    new_text: str
    
    # Anchos
    original_width: float           # Ancho original en puntos
    new_text_natural_width: float   # Ancho natural del nuevo texto
    target_width: float             # Ancho objetivo
    
    # Diferencia
    width_difference: float         # Diferencia de anchos
    width_ratio: float              # Ratio nuevo/original
    
    # Resultado
    fit_result: FitResult
    fit_strategy: FitStrategy
    
    # Ajuste aplicado
    adjustment: Optional[SpacingAdjustment] = None
    
    # Texto resultante (puede ser truncado)
    final_text: str = ""
    final_width: float = 0.0
    
    # Métricas adicionales
    overflow_amount: float = 0.0    # Cantidad de desbordamiento
    compression_percent: float = 0.0  # Porcentaje de compresión
    
    def __post_init__(self):
        if not self.final_text:
            self.final_text = self.new_text
    
    @property
    def fits_exactly(self) -> bool:
        """Verifica si el texto ajusta exactamente."""
        return abs(self.final_width - self.target_width) < 0.1
    
    @property
    def is_success(self) -> bool:
        """Verifica si el ajuste fue exitoso."""
        return self.fit_result in (
            FitResult.SUCCESS,
            FitResult.COMPRESSED,
            FitResult.EXPANDED,
            FitResult.SCALED,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario."""
        return {
            'original_text': self.original_text,
            'new_text': self.new_text,
            'final_text': self.final_text,
            'original_width': self.original_width,
            'new_text_natural_width': self.new_text_natural_width,
            'target_width': self.target_width,
            'final_width': self.final_width,
            'width_difference': self.width_difference,
            'width_ratio': self.width_ratio,
            'fit_result': self.fit_result.name,
            'fit_strategy': self.fit_strategy.name,
            'adjustment': self.adjustment.to_dict() if self.adjustment else None,
        }


@dataclass
class PreserverConfig:
    """Configuración del preservador de anchos."""
    # Estrategia por defecto
    default_strategy: FitStrategy = FitStrategy.EXACT
    
    # Tolerancias
    width_tolerance: float = 0.5        # Tolerancia en puntos
    ratio_tolerance: float = 0.01       # Tolerancia de ratio (1%)
    
    # Límites de ajuste
    max_tracking: float = 5.0           # Máximo tracking (puntos)
    min_tracking: float = -3.0          # Mínimo tracking (puntos)
    max_word_spacing: float = 10.0      # Máximo word spacing
    min_word_spacing: float = -5.0      # Mínimo word spacing
    max_horizontal_scale: float = 150.0  # Máxima escala horizontal (%)
    min_horizontal_scale: float = 50.0   # Mínima escala horizontal (%)
    
    # Preferencias
    prefer_word_spacing: bool = True     # Preferir ajustar espacios entre palabras
    use_kerning: bool = True             # Usar kerning
    
    # Truncamiento
    ellipsis: str = "..."               # Texto de elipsis
    truncate_at_word: bool = True       # Truncar en límite de palabra


@dataclass
class TJArrayEntry:
    """
    Entrada en un array TJ de PDF.
    
    PDF TJ arrays alternan texto y ajustes de posición:
    [(texto1) -50 (texto2) -100 (texto3)] TJ
    """
    is_text: bool               # True si es texto, False si es ajuste
    text: str = ""              # Texto (si is_text)
    adjustment: float = 0.0     # Ajuste en unidades de texto (si not is_text)
    
    def to_pdf(self) -> str:
        """Genera representación PDF."""
        if self.is_text:
            # Escapar paréntesis y backslashes
            escaped = self.text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            return f"({escaped})"
        else:
            # Ajuste numérico (negativo = mover a la derecha)
            return f"{self.adjustment:.2f}"


# ================== Main Class ==================


class GlyphWidthPreserver:
    """
    Preserva los anchos de glifos durante la edición de texto.
    
    Esta clase asegura que cuando se edita texto en un PDF, el nuevo
    texto ocupe exactamente el mismo espacio que el original,
    preservando la maquetación del documento.
    
    Funciona con:
    - Fuentes embebidas (usando sus métricas reales)
    - Fuentes del sistema (usando aproximaciones)
    
    Usage:
        preserver = GlyphWidthPreserver()
        
        # Analizar ajuste necesario
        analysis = preserver.analyze_fit(
            original_text="Hello World",
            new_text="Hola Mundo",
            font_name="Helvetica",
            font_size=12.0,
        )
        
        # Obtener ajuste de espaciado
        if analysis.is_success:
            operators = analysis.adjustment.to_pdf_operators()
    """
    
    # Anchos aproximados para fuentes comunes (en 1/1000 em)
    DEFAULT_WIDTHS = {
        # Helvetica-like
        'helvetica': {
            'default': 556,
            'space': 278,
            ' ': 278, 'i': 278, 'l': 222, 'I': 278, '!': 278,
            'm': 889, 'w': 778, 'M': 833, 'W': 1000,
        },
        # Times-like
        'times': {
            'default': 500,
            'space': 250,
            ' ': 250, 'i': 278, 'l': 278, 'I': 333,
            'm': 778, 'w': 722, 'M': 889, 'W': 1000,
        },
        # Courier (monospace)
        'courier': {
            'default': 600,
            'space': 600,
        },
    }
    
    def __init__(
        self,
        config: Optional[PreserverConfig] = None,
        font_extractor: Optional[Any] = None,  # EmbeddedFontExtractor
    ):
        """
        Inicializa el preservador.
        
        Args:
            config: Configuración opcional
            font_extractor: Extractor de fuentes embebidas (opcional)
        """
        self._config = config or PreserverConfig()
        self._font_extractor = font_extractor
        
        # Cache de anchos
        self._width_cache: Dict[str, Dict[int, float]] = {}
    
    @property
    def config(self) -> PreserverConfig:
        """Obtiene configuración."""
        return self._config
    
    def set_font_extractor(self, extractor: Any) -> None:
        """Establece el extractor de fuentes."""
        self._font_extractor = extractor
        self._width_cache.clear()
    
    # ================== Width Calculation ==================
    
    def get_char_width(
        self,
        char: str,
        font_name: str,
        font_size: float,
        page_num: int = 0,
    ) -> float:
        """
        Obtiene el ancho de un carácter en puntos.
        
        Args:
            char: Carácter a medir
            font_name: Nombre de la fuente
            font_size: Tamaño en puntos
            page_num: Número de página (para fuentes embebidas)
            
        Returns:
            Ancho en puntos
        """
        width_fu = self._get_char_width_font_units(char, font_name, page_num)
        return (width_fu / 1000.0) * font_size
    
    def _get_char_width_font_units(
        self,
        char: str,
        font_name: str,
        page_num: int = 0,
    ) -> float:
        """Obtiene ancho en unidades de fuente."""
        # Intentar cache
        cache_key = f"{font_name}:{page_num}"
        if cache_key in self._width_cache:
            char_code = ord(char)
            if char_code in self._width_cache[cache_key]:
                return self._width_cache[cache_key][char_code]
        
        # Intentar usar extractor de fuentes embebidas
        if self._font_extractor:
            try:
                widths = self._font_extractor.get_glyph_widths(
                    font_name, char, page_num
                )
                if widths:
                    return widths[0]
            except Exception:
                pass
        
        # Usar anchos aproximados
        return self._get_approximate_width(char, font_name)
    
    def _get_approximate_width(self, char: str, font_name: str) -> float:
        """Obtiene ancho aproximado para fuentes no embebidas."""
        # Determinar familia de fuente
        font_lower = font_name.lower()
        
        if 'courier' in font_lower or 'mono' in font_lower:
            widths = self.DEFAULT_WIDTHS['courier']
        elif 'times' in font_lower or 'serif' in font_lower:
            widths = self.DEFAULT_WIDTHS['times']
        else:
            widths = self.DEFAULT_WIDTHS['helvetica']
        
        # Buscar carácter específico
        if char in widths:
            return widths[char]
        
        # Usar ancho por defecto
        return widths['default']
    
    def measure_text(
        self,
        text: str,
        font_name: str,
        font_size: float,
        page_num: int = 0,
    ) -> TextWidthInfo:
        """
        Mide el ancho de un texto.
        
        Args:
            text: Texto a medir
            font_name: Nombre de la fuente
            font_size: Tamaño en puntos
            page_num: Número de página
            
        Returns:
            TextWidthInfo con información detallada
        """
        char_widths = []
        total_fu = 0.0
        
        for char in text:
            width_fu = self._get_char_width_font_units(char, font_name, page_num)
            width_pts = (width_fu / 1000.0) * font_size
            
            glyph = GlyphWidth(
                char=char,
                char_code=ord(char),
                width_font_units=width_fu,
                width_points=width_pts,
                is_space=char == ' ',
            )
            char_widths.append(glyph)
            total_fu += width_fu
        
        total_pts = (total_fu / 1000.0) * font_size
        
        return TextWidthInfo(
            text=text,
            total_width_points=total_pts,
            total_width_font_units=total_fu,
            char_widths=char_widths,
            font_name=font_name,
            font_size=font_size,
        )
    
    # ================== Fit Analysis ==================
    
    def analyze_fit(
        self,
        original_text: str,
        new_text: str,
        font_name: str,
        font_size: float,
        page_num: int = 0,
        strategy: Optional[FitStrategy] = None,
        target_width: Optional[float] = None,
    ) -> FitAnalysis:
        """
        Analiza cómo ajustar el nuevo texto al espacio del original.
        
        Args:
            original_text: Texto original
            new_text: Nuevo texto
            font_name: Nombre de la fuente
            font_size: Tamaño en puntos
            page_num: Número de página
            strategy: Estrategia de ajuste (usa default si None)
            target_width: Ancho objetivo (usa ancho original si None)
            
        Returns:
            FitAnalysis con el análisis completo
        """
        strategy = strategy or self._config.default_strategy
        
        # Medir textos
        original_info = self.measure_text(original_text, font_name, font_size, page_num)
        new_info = self.measure_text(new_text, font_name, font_size, page_num)
        
        # Ancho objetivo
        target = target_width if target_width is not None else original_info.total_width_points
        
        # Calcular diferencia
        width_diff = new_info.total_width_points - target
        width_ratio = new_info.total_width_points / target if target > 0 else 1.0
        
        # Crear análisis base
        analysis = FitAnalysis(
            original_text=original_text,
            new_text=new_text,
            original_width=original_info.total_width_points,
            new_text_natural_width=new_info.total_width_points,
            target_width=target,
            width_difference=width_diff,
            width_ratio=width_ratio,
            fit_result=FitResult.FAILED,
            fit_strategy=strategy,
        )
        
        # Si está dentro de tolerancia, no necesita ajuste
        if abs(width_diff) <= self._config.width_tolerance:
            analysis.fit_result = FitResult.SUCCESS
            analysis.final_width = new_info.total_width_points
            return analysis
        
        # Aplicar estrategia
        if strategy == FitStrategy.EXACT:
            self._apply_exact_fit(analysis, new_info)
        elif strategy == FitStrategy.COMPRESS:
            self._apply_compress_fit(analysis, new_info)
        elif strategy == FitStrategy.EXPAND:
            self._apply_expand_fit(analysis, new_info)
        elif strategy == FitStrategy.TRUNCATE:
            self._apply_truncate_fit(analysis, new_info, font_name, font_size, page_num)
        elif strategy == FitStrategy.ELLIPSIS:
            self._apply_ellipsis_fit(analysis, new_info, font_name, font_size, page_num)
        elif strategy == FitStrategy.SCALE:
            self._apply_scale_fit(analysis, new_info)
        elif strategy == FitStrategy.ALLOW_OVERFLOW:
            analysis.fit_result = FitResult.OVERFLOW
            analysis.final_width = new_info.total_width_points
            analysis.overflow_amount = max(0, width_diff)
        
        return analysis
    
    def _apply_exact_fit(
        self,
        analysis: FitAnalysis,
        new_info: TextWidthInfo,
    ) -> None:
        """Aplica ajuste exacto mediante espaciado."""
        width_diff = analysis.width_difference
        char_count = len(analysis.new_text)
        space_count = new_info.space_count
        non_space_count = char_count - space_count
        
        adjustment = SpacingAdjustment(adjustment_type=AdjustmentType.NONE)
        
        # Preferir ajuste de espaciado entre palabras si hay espacios
        if self._config.prefer_word_spacing and space_count > 0:
            word_spacing_needed = -width_diff / space_count
            
            if self._config.min_word_spacing <= word_spacing_needed <= self._config.max_word_spacing:
                adjustment.adjustment_type = AdjustmentType.WORD_SPACING
                adjustment.word_spacing = word_spacing_needed
                adjustment.total_adjustment = -width_diff
                adjustment.adjustment_per_space = word_spacing_needed
                
                analysis.adjustment = adjustment
                analysis.fit_result = FitResult.COMPRESSED if width_diff > 0 else FitResult.EXPANDED
                analysis.final_width = analysis.target_width
                return
        
        # Usar tracking (espaciado entre todos los caracteres)
        if non_space_count > 1:
            tracking_needed = -width_diff / (char_count - 1)
            
            if self._config.min_tracking <= tracking_needed <= self._config.max_tracking:
                adjustment.adjustment_type = AdjustmentType.TRACKING
                adjustment.tracking = tracking_needed
                adjustment.total_adjustment = -width_diff
                adjustment.adjustment_per_char = tracking_needed
                
                analysis.adjustment = adjustment
                analysis.fit_result = FitResult.COMPRESSED if width_diff > 0 else FitResult.EXPANDED
                analysis.final_width = analysis.target_width
                return
        
        # Combinar tracking y word spacing si es necesario
        if space_count > 0 and non_space_count > 1:
            # Distribuir: 60% word spacing, 40% tracking
            ws_portion = -width_diff * 0.6 / space_count if space_count > 0 else 0
            tr_portion = -width_diff * 0.4 / (char_count - 1) if char_count > 1 else 0
            
            ws_valid = self._config.min_word_spacing <= ws_portion <= self._config.max_word_spacing
            tr_valid = self._config.min_tracking <= tr_portion <= self._config.max_tracking
            
            if ws_valid and tr_valid:
                adjustment.adjustment_type = AdjustmentType.COMBINED
                adjustment.word_spacing = ws_portion
                adjustment.tracking = tr_portion
                adjustment.total_adjustment = -width_diff
                
                analysis.adjustment = adjustment
                analysis.fit_result = FitResult.COMPRESSED if width_diff > 0 else FitResult.EXPANDED
                analysis.final_width = analysis.target_width
                return
        
        # No se puede ajustar solo con espaciado, usar escala
        self._apply_scale_fit(analysis, new_info)
    
    def _apply_compress_fit(
        self,
        analysis: FitAnalysis,
        new_info: TextWidthInfo,
    ) -> None:
        """Aplica compresión si el texto es más largo."""
        if analysis.width_difference <= self._config.width_tolerance:
            analysis.fit_result = FitResult.SUCCESS
            analysis.final_width = new_info.total_width_points
            return
        
        # Solo comprimir si es más largo
        if analysis.width_difference > 0:
            self._apply_exact_fit(analysis, new_info)
        else:
            analysis.fit_result = FitResult.SUCCESS
            analysis.final_width = new_info.total_width_points
    
    def _apply_expand_fit(
        self,
        analysis: FitAnalysis,
        new_info: TextWidthInfo,
    ) -> None:
        """Aplica expansión si el texto es más corto."""
        if abs(analysis.width_difference) <= self._config.width_tolerance:
            analysis.fit_result = FitResult.SUCCESS
            analysis.final_width = new_info.total_width_points
            return
        
        # Solo expandir si es más corto
        if analysis.width_difference < 0:
            self._apply_exact_fit(analysis, new_info)
        else:
            analysis.fit_result = FitResult.SUCCESS
            analysis.final_width = new_info.total_width_points
    
    def _apply_truncate_fit(
        self,
        analysis: FitAnalysis,
        new_info: TextWidthInfo,
        font_name: str,
        font_size: float,
        page_num: int,
    ) -> None:
        """Trunca el texto si no cabe."""
        if analysis.width_difference <= self._config.width_tolerance:
            analysis.fit_result = FitResult.SUCCESS
            analysis.final_width = new_info.total_width_points
            return
        
        # Truncar carácter por carácter
        text = analysis.new_text
        target = analysis.target_width
        
        while text and self.measure_text(text, font_name, font_size, page_num).total_width_points > target:
            if self._config.truncate_at_word:
                # Intentar truncar en límite de palabra
                last_space = text.rfind(' ')
                if last_space > 0:
                    text = text[:last_space]
                else:
                    text = text[:-1]
            else:
                text = text[:-1]
        
        truncated_info = self.measure_text(text, font_name, font_size, page_num)
        
        analysis.final_text = text
        analysis.final_width = truncated_info.total_width_points
        analysis.fit_result = FitResult.TRUNCATED
    
    def _apply_ellipsis_fit(
        self,
        analysis: FitAnalysis,
        new_info: TextWidthInfo,
        font_name: str,
        font_size: float,
        page_num: int,
    ) -> None:
        """Trunca el texto con elipsis si no cabe."""
        if analysis.width_difference <= self._config.width_tolerance:
            analysis.fit_result = FitResult.SUCCESS
            analysis.final_width = new_info.total_width_points
            return
        
        ellipsis = self._config.ellipsis
        ellipsis_width = self.measure_text(
            ellipsis, font_name, font_size, page_num
        ).total_width_points
        
        # Ancho disponible para texto (sin elipsis)
        available = analysis.target_width - ellipsis_width
        
        if available <= 0:
            # No hay espacio ni para elipsis
            analysis.final_text = ellipsis[:1] if ellipsis else ""
            analysis.final_width = self.measure_text(
                analysis.final_text, font_name, font_size, page_num
            ).total_width_points
            analysis.fit_result = FitResult.TRUNCATED
            return
        
        # Truncar texto para dejar espacio para elipsis
        text = analysis.new_text
        
        while text and self.measure_text(text, font_name, font_size, page_num).total_width_points > available:
            if self._config.truncate_at_word:
                last_space = text.rfind(' ')
                if last_space > 0:
                    text = text[:last_space]
                else:
                    text = text[:-1]
            else:
                text = text[:-1]
        
        final_text = text.rstrip() + ellipsis
        final_info = self.measure_text(final_text, font_name, font_size, page_num)
        
        analysis.final_text = final_text
        analysis.final_width = final_info.total_width_points
        analysis.fit_result = FitResult.TRUNCATED
    
    def _apply_scale_fit(
        self,
        analysis: FitAnalysis,
        new_info: TextWidthInfo,
    ) -> None:
        """Aplica escalado horizontal."""
        if analysis.new_text_natural_width <= 0:
            analysis.fit_result = FitResult.FAILED
            return
        
        # Calcular escala necesaria
        scale = (analysis.target_width / analysis.new_text_natural_width) * 100
        
        # Verificar límites
        if scale < self._config.min_horizontal_scale or scale > self._config.max_horizontal_scale:
            analysis.fit_result = FitResult.FAILED
            analysis.overflow_amount = max(0, analysis.width_difference)
            return
        
        adjustment = SpacingAdjustment(
            adjustment_type=AdjustmentType.HORIZONTAL_SCALE,
            horizontal_scale=scale,
            total_adjustment=analysis.target_width - analysis.new_text_natural_width,
        )
        
        analysis.adjustment = adjustment
        analysis.fit_result = FitResult.SCALED
        analysis.final_width = analysis.target_width
        analysis.compression_percent = 100 - scale if scale < 100 else scale - 100
    
    # ================== TJ Array Generation ==================
    
    def generate_tj_array(
        self,
        text: str,
        font_name: str,
        font_size: float,
        target_width: float,
        page_num: int = 0,
    ) -> List[TJArrayEntry]:
        """
        Genera un array TJ con ajustes de posición para lograr el ancho objetivo.
        
        El array TJ de PDF permite intercalar texto con ajustes de posición,
        lo que permite kerning preciso y ajuste de ancho.
        
        Args:
            text: Texto a renderizar
            font_name: Nombre de la fuente
            font_size: Tamaño en puntos
            target_width: Ancho objetivo en puntos
            page_num: Número de página
            
        Returns:
            Lista de TJArrayEntry para construir el operador TJ
        """
        if not text:
            return []
        
        # Medir texto natural
        text_info = self.measure_text(text, font_name, font_size, page_num)
        width_diff = text_info.total_width_points - target_width
        
        # Si está dentro de tolerancia, devolver texto simple
        if abs(width_diff) <= self._config.width_tolerance:
            return [TJArrayEntry(is_text=True, text=text)]
        
        # Calcular ajuste por carácter
        char_count = len(text)
        if char_count <= 1:
            return [TJArrayEntry(is_text=True, text=text)]
        
        # Ajuste en unidades de texto (1/1000 em * font_size)
        # Negativo = mover a la derecha
        adjustment_per_gap = (width_diff / (char_count - 1)) * (1000 / font_size)
        
        # Limitar ajuste
        max_adj = 200  # Máximo ajuste por gap
        adjustment_per_gap = max(-max_adj, min(max_adj, adjustment_per_gap))
        
        entries = []
        for i, char in enumerate(text):
            entries.append(TJArrayEntry(is_text=True, text=char))
            
            # Agregar ajuste entre caracteres (excepto después del último)
            if i < len(text) - 1 and abs(adjustment_per_gap) > 0.1:
                entries.append(TJArrayEntry(is_text=False, adjustment=adjustment_per_gap))
        
        return entries
    
    def tj_array_to_pdf(self, entries: List[TJArrayEntry]) -> str:
        """
        Convierte lista de TJArrayEntry a string PDF.
        
        Args:
            entries: Lista de entradas TJ
            
        Returns:
            String del operador TJ completo
        """
        if not entries:
            return "[] TJ"
        
        parts = [entry.to_pdf() for entry in entries]
        return f"[{' '.join(parts)}] TJ"
    
    # ================== Validation ==================
    
    def validate_fit(
        self,
        original_text: str,
        new_text: str,
        font_name: str,
        font_size: float,
        page_num: int = 0,
    ) -> Tuple[bool, str]:
        """
        Valida si un texto nuevo puede ajustarse al espacio del original.
        
        Args:
            original_text: Texto original
            new_text: Nuevo texto
            font_name: Nombre de la fuente
            font_size: Tamaño en puntos
            page_num: Número de página
            
        Returns:
            Tupla (puede_ajustarse, mensaje)
        """
        analysis = self.analyze_fit(
            original_text=original_text,
            new_text=new_text,
            font_name=font_name,
            font_size=font_size,
            page_num=page_num,
            strategy=FitStrategy.EXACT,
        )
        
        if analysis.is_success:
            if analysis.adjustment and analysis.adjustment.has_adjustment:
                return True, f"Ajuste requerido: {analysis.adjustment.adjustment_type.name}"
            return True, "Texto ajusta sin modificaciones"
        
        # Verificar con otras estrategias
        for strategy in [FitStrategy.SCALE, FitStrategy.COMPRESS]:
            alt_analysis = self.analyze_fit(
                original_text=original_text,
                new_text=new_text,
                font_name=font_name,
                font_size=font_size,
                page_num=page_num,
                strategy=strategy,
            )
            if alt_analysis.is_success:
                return True, f"Posible con estrategia {strategy.name}"
        
        overflow = analysis.width_difference if analysis.width_difference > 0 else 0
        return False, f"Texto demasiado largo (desborda {overflow:.2f}pt)"
    
    def get_max_text_length(
        self,
        target_width: float,
        font_name: str,
        font_size: float,
        page_num: int = 0,
    ) -> int:
        """
        Estima el número máximo de caracteres que caben en un ancho.
        
        Args:
            target_width: Ancho objetivo en puntos
            font_name: Nombre de la fuente
            font_size: Tamaño en puntos
            page_num: Número de página
            
        Returns:
            Número estimado de caracteres
        """
        # Usar ancho promedio del carácter 'x'
        avg_width = self.get_char_width('x', font_name, font_size, page_num)
        
        if avg_width <= 0:
            return 0
        
        return int(target_width / avg_width)
    
    # ================== Serialization ==================
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa configuración."""
        return {
            'config': {
                'default_strategy': self._config.default_strategy.name,
                'width_tolerance': self._config.width_tolerance,
                'max_tracking': self._config.max_tracking,
                'min_tracking': self._config.min_tracking,
                'max_word_spacing': self._config.max_word_spacing,
                'min_word_spacing': self._config.min_word_spacing,
                'max_horizontal_scale': self._config.max_horizontal_scale,
                'min_horizontal_scale': self._config.min_horizontal_scale,
            }
        }


# ================== Factory Functions ==================


def create_width_preserver(
    font_extractor: Optional[Any] = None,
    default_strategy: FitStrategy = FitStrategy.EXACT,
    **kwargs
) -> GlyphWidthPreserver:
    """
    Crea un preservador de anchos configurado.
    
    Args:
        font_extractor: Extractor de fuentes embebidas (opcional)
        default_strategy: Estrategia por defecto
        **kwargs: Argumentos adicionales para config
        
    Returns:
        GlyphWidthPreserver configurado
    """
    config = PreserverConfig(
        default_strategy=default_strategy,
        **kwargs
    )
    return GlyphWidthPreserver(config=config, font_extractor=font_extractor)


def calculate_text_width(
    text: str,
    font_name: str,
    font_size: float,
    font_extractor: Optional[Any] = None,
    page_num: int = 0,
) -> float:
    """
    Calcula el ancho de un texto en puntos.
    
    Función de conveniencia para cálculo rápido de anchura.
    
    Args:
        text: Texto a medir
        font_name: Nombre de la fuente
        font_size: Tamaño en puntos
        font_extractor: Extractor de fuentes (opcional)
        page_num: Número de página
        
    Returns:
        Ancho en puntos
    """
    preserver = GlyphWidthPreserver(font_extractor=font_extractor)
    info = preserver.measure_text(text, font_name, font_size, page_num)
    return info.total_width_points


def fit_text_to_width(
    original_text: str,
    new_text: str,
    font_name: str,
    font_size: float,
    strategy: FitStrategy = FitStrategy.EXACT,
    font_extractor: Optional[Any] = None,
    page_num: int = 0,
) -> FitAnalysis:
    """
    Ajusta un texto nuevo al ancho de un texto original.
    
    Función de conveniencia para ajuste rápido.
    
    Args:
        original_text: Texto original
        new_text: Nuevo texto
        font_name: Nombre de la fuente
        font_size: Tamaño en puntos
        strategy: Estrategia de ajuste
        font_extractor: Extractor de fuentes (opcional)
        page_num: Número de página
        
    Returns:
        FitAnalysis con el análisis
    """
    preserver = GlyphWidthPreserver(font_extractor=font_extractor)
    return preserver.analyze_fit(
        original_text=original_text,
        new_text=new_text,
        font_name=font_name,
        font_size=font_size,
        page_num=page_num,
        strategy=strategy,
    )


def get_spacing_adjustment(
    original_text: str,
    new_text: str,
    font_name: str,
    font_size: float,
    font_extractor: Optional[Any] = None,
    page_num: int = 0,
) -> Optional[SpacingAdjustment]:
    """
    Obtiene el ajuste de espaciado necesario para reemplazar texto.
    
    Args:
        original_text: Texto original
        new_text: Nuevo texto
        font_name: Nombre de la fuente
        font_size: Tamaño en puntos
        font_extractor: Extractor de fuentes (opcional)
        page_num: Número de página
        
    Returns:
        SpacingAdjustment o None si no es posible
    """
    analysis = fit_text_to_width(
        original_text=original_text,
        new_text=new_text,
        font_name=font_name,
        font_size=font_size,
        strategy=FitStrategy.EXACT,
        font_extractor=font_extractor,
        page_num=page_num,
    )
    
    if analysis.is_success:
        return analysis.adjustment
    return None


__all__ = [
    # Enums
    'FitStrategy',
    'FitResult',
    'AdjustmentType',
    'WidthUnit',
    # Dataclasses
    'GlyphWidth',
    'TextWidthInfo',
    'SpacingAdjustment',
    'FitAnalysis',
    'PreserverConfig',
    'TJArrayEntry',
    # Classes
    'GlyphWidthPreserver',
    # Factory functions
    'create_width_preserver',
    'calculate_text_width',
    'fit_text_to_width',
    'get_spacing_adjustment',
]

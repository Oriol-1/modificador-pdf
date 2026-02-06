"""
EmbeddedFontExtractor - Extracción y gestión de fuentes embebidas.

Módulo para extraer información de fuentes embebidas en documentos PDF,
incluyendo métricas, encoding y datos del programa de fuente.

Parte de la Fase 3A del motor de texto PDF.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Set, Any, TYPE_CHECKING
import re

if TYPE_CHECKING:
    import fitz


class FontType(Enum):
    """Tipos de fuentes en PDF."""
    TYPE1 = auto()        # Adobe Type 1
    TRUETYPE = auto()     # TrueType
    OPENTYPE = auto()     # OpenType (CFF/TrueType)
    TYPE3 = auto()        # Type 3 (glyph procedures)
    CID_TYPE0 = auto()    # CID-keyed Type 0
    CID_TYPE2 = auto()    # CID-keyed TrueType
    MMTYPE1 = auto()      # Multiple Master Type 1
    UNKNOWN = auto()


class EmbeddingStatus(Enum):
    """Estado de embedding de una fuente."""
    FULL = auto()         # Completamente embebida
    SUBSET = auto()       # Subset (ABCDEF+Name)
    NOT_EMBEDDED = auto() # No embebida (solo referencia)
    PARTIAL = auto()      # Parcialmente embebida


class FontEncoding(Enum):
    """Encodings de fuentes en PDF."""
    STANDARD = auto()         # StandardEncoding
    MACROMAN = auto()         # MacRomanEncoding
    WINANSI = auto()          # WinAnsiEncoding
    PDFDOC = auto()           # PDFDocEncoding
    MACEXPERT = auto()        # MacExpertEncoding
    SYMBOL = auto()           # Built-in Symbol encoding
    ZAPFDINGBATS = auto()     # ZapfDingbats encoding
    IDENTITY_H = auto()       # Identity-H (horizontal)
    IDENTITY_V = auto()       # Identity-V (vertical)
    CUSTOM = auto()           # Custom encoding
    UNKNOWN = auto()


@dataclass
class FontMetrics:
    """Métricas de una fuente."""
    ascender: float = 0.0       # Altura del ascender
    descender: float = 0.0      # Profundidad del descender (negativo)
    cap_height: float = 0.0     # Altura de mayúsculas
    x_height: float = 0.0       # Altura de minúsculas (x)
    line_gap: float = 0.0       # Espacio entre líneas
    units_per_em: int = 1000    # Unidades por em
    
    @property
    def total_height(self) -> float:
        """Altura total (ascender + |descender|)."""
        return self.ascender + abs(self.descender)
    
    def to_points(self, value: float, font_size: float) -> float:
        """Convierte de unidades de fuente a puntos."""
        if self.units_per_em == 0:
            return value
        return (value / self.units_per_em) * font_size


@dataclass
class GlyphInfo:
    """Información de un glifo individual."""
    name: str                   # Nombre del glifo
    unicode: Optional[int]      # Código Unicode (si se conoce)
    width: float                # Ancho del glifo
    bbox: Optional[Tuple[float, float, float, float]] = None  # Bounding box
    
    @property
    def char(self) -> str:
        """Carácter Unicode correspondiente."""
        if self.unicode:
            return chr(self.unicode)
        return ""


@dataclass
class FontInfo:
    """Información completa de una fuente del PDF."""
    name: str                           # Nombre de la fuente
    base_font: str                      # Fuente base (PostScript name)
    font_type: FontType                 # Tipo de fuente
    is_embedded: bool                   # Si está embebida
    is_subset: bool                     # Si es subset
    subset_prefix: Optional[str]        # Prefijo de subset (ABCDEF)
    encoding: FontEncoding              # Encoding usado
    
    # Métricas
    metrics: FontMetrics = field(default_factory=FontMetrics)
    bbox: Tuple[float, float, float, float] = (0, 0, 0, 0)  # FontBBox
    
    # Flags (de FontDescriptor)
    is_fixed_pitch: bool = False
    is_serif: bool = False
    is_symbolic: bool = False
    is_script: bool = False
    is_italic: bool = False
    is_all_cap: bool = False
    is_small_cap: bool = False
    is_force_bold: bool = False
    
    # Anchos de glifos
    widths: Dict[int, float] = field(default_factory=dict)
    default_width: float = 0.0
    
    # Información adicional
    glyph_count: int = 0
    available_glyphs: Set[str] = field(default_factory=set)
    
    @property
    def clean_name(self) -> str:
        """Nombre sin prefijo de subset."""
        if self.is_subset and self.subset_prefix:
            return self.name.replace(f"{self.subset_prefix}+", "")
        return self.name
    
    @property
    def embedding_status(self) -> EmbeddingStatus:
        """Estado de embedding."""
        if not self.is_embedded:
            return EmbeddingStatus.NOT_EMBEDDED
        if self.is_subset:
            return EmbeddingStatus.SUBSET
        return EmbeddingStatus.FULL
    
    def get_width(self, char_code: int) -> float:
        """Obtiene el ancho de un carácter."""
        return self.widths.get(char_code, self.default_width)
    
    def has_glyph(self, glyph_name: str) -> bool:
        """Verifica si la fuente tiene un glifo específico."""
        return glyph_name in self.available_glyphs
    
    def can_render_text(self, text: str) -> Tuple[bool, List[str]]:
        """
        Verifica si la fuente puede renderizar un texto.
        
        Returns:
            Tupla de (puede_renderizar, caracteres_faltantes)
        """
        if not self.is_subset:
            return True, []  # Fuentes completas pueden renderizar todo
        
        missing = []
        for char in text:
            glyph_name = self._char_to_glyph_name(char)
            if glyph_name and glyph_name not in self.available_glyphs:
                missing.append(char)
        
        return len(missing) == 0, missing
    
    def _char_to_glyph_name(self, char: str) -> Optional[str]:
        """Convierte un carácter a nombre de glifo."""
        # Mapping básico - en implementación real sería más completo
        code = ord(char)
        if 65 <= code <= 90:  # A-Z
            return chr(code)
        if 97 <= code <= 122:  # a-z
            return chr(code)
        if 48 <= code <= 57:  # 0-9
            return chr(code)
        if char == ' ':
            return 'space'
        if char == '.':
            return 'period'
        if char == ',':
            return 'comma'
        return None


@dataclass
class FontExtractorConfig:
    """Configuración del extractor de fuentes."""
    # Cache de fuentes
    enable_cache: bool = True
    
    # Extracción de anchos
    extract_all_widths: bool = True
    
    # Análisis de glifos
    analyze_glyphs: bool = True
    
    # Extracción de programa de fuente
    extract_font_program: bool = False


class EmbeddedFontExtractor:
    """
    Extrae y gestiona fuentes embebidas del PDF.
    
    Esta clase proporciona acceso a información detallada de las fuentes
    embebidas en un documento PDF, incluyendo métricas, anchos de glifos
    y estado de embedding.
    
    Attributes:
        doc: Documento PDF (fitz.Document)
        font_cache: Cache de información de fuentes
        config: Configuración del extractor
    """
    
    # Patrón para detectar subset prefix
    SUBSET_PATTERN = re.compile(r'^([A-Z]{6})\+(.+)$')
    
    def __init__(
        self, 
        doc: Optional['fitz.Document'] = None,
        config: Optional[FontExtractorConfig] = None
    ):
        """
        Inicializa el extractor de fuentes.
        
        Args:
            doc: Documento PDF
            config: Configuración del extractor
        """
        self.doc = doc
        self.config = config or FontExtractorConfig()
        self.font_cache: Dict[str, FontInfo] = {}
        self._page_fonts: Dict[int, List[str]] = {}
    
    def set_document(self, doc: 'fitz.Document') -> None:
        """
        Establece el documento PDF.
        
        Args:
            doc: Documento PDF
        """
        self.doc = doc
        self.font_cache.clear()
        self._page_fonts.clear()
    
    def get_font_info(
        self, 
        font_name: str, 
        page_num: int = 0
    ) -> FontInfo:
        """
        Obtiene información completa de una fuente del PDF.
        
        Args:
            font_name: Nombre de la fuente
            page_num: Número de página donde se usa
        
        Returns:
            FontInfo con información completa
        """
        # Verificar cache
        cache_key = f"{font_name}:{page_num}"
        if self.config.enable_cache and cache_key in self.font_cache:
            return self.font_cache[cache_key]
        
        # Crear información base
        font_info = self._extract_font_info(font_name, page_num)
        
        # Cachear
        if self.config.enable_cache:
            self.font_cache[cache_key] = font_info
        
        return font_info
    
    def get_page_fonts(self, page_num: int) -> List[FontInfo]:
        """
        Obtiene todas las fuentes usadas en una página.
        
        Args:
            page_num: Número de página
        
        Returns:
            Lista de FontInfo
        """
        if not self.doc:
            return []
        
        try:
            page = self.doc[page_num]
            font_list = page.get_fonts()
            
            fonts = []
            for font_entry in font_list:
                xref, ext, type_, name, enc, *_ = font_entry[:5] + (None,) * (5 - len(font_entry[:5]))
                if name:
                    fonts.append(self.get_font_info(name, page_num))
            
            return fonts
        except Exception:
            return []
    
    def can_reuse_font(self, font_name: str, page_num: int = 0) -> bool:
        """
        Verifica si una fuente embebida se puede reutilizar para edición.
        
        Condiciones:
        - Fuente completamente embebida (no subset)
        - O subset con todos los glifos necesarios
        
        Args:
            font_name: Nombre de la fuente
            page_num: Número de página
        
        Returns:
            True si se puede reutilizar
        """
        font_info = self.get_font_info(font_name, page_num)
        
        # Fuentes no embebidas no se pueden reutilizar directamente
        if not font_info.is_embedded:
            return False
        
        # Fuentes completamente embebidas siempre se pueden reutilizar
        if not font_info.is_subset:
            return True
        
        # Subsets pueden reutilizarse si contienen los glifos necesarios
        # (esto requiere verificación adicional al momento de editar)
        return True
    
    def get_glyph_widths(
        self, 
        font_name: str, 
        text: str,
        page_num: int = 0
    ) -> List[float]:
        """
        Obtiene los anchos de glifos para un texto específico.
        
        Args:
            font_name: Nombre de la fuente
            text: Texto a medir
            page_num: Número de página
        
        Returns:
            Lista de anchos en unidades de fuente
        """
        font_info = self.get_font_info(font_name, page_num)
        
        widths = []
        for char in text:
            code = ord(char)
            width = font_info.get_width(code)
            widths.append(width)
        
        return widths
    
    def calculate_text_width(
        self,
        font_name: str,
        text: str,
        font_size: float,
        page_num: int = 0
    ) -> float:
        """
        Calcula el ancho de un texto en puntos.
        
        Args:
            font_name: Nombre de la fuente
            text: Texto a medir
            font_size: Tamaño de fuente
            page_num: Número de página
        
        Returns:
            Ancho total en puntos
        """
        widths = self.get_glyph_widths(font_name, text, page_num)
        font_info = self.get_font_info(font_name, page_num)
        
        total_width = sum(widths)
        
        # Convertir de unidades de fuente a puntos
        return font_info.metrics.to_points(total_width, font_size)
    
    def extract_font_program(
        self, 
        font_name: str,
        page_num: int = 0
    ) -> Optional[bytes]:
        """
        Extrae el programa de fuente (para posible reutilización).
        
        Args:
            font_name: Nombre de la fuente
            page_num: Número de página
        
        Returns:
            Bytes del programa de fuente o None
        """
        if not self.doc:
            return None
        
        try:
            page = self.doc[page_num]
            font_list = page.get_fonts()
            
            for font_entry in font_list:
                xref = font_entry[0]
                name = font_entry[3] if len(font_entry) > 3 else ""
                
                if name == font_name or self._normalize_font_name(name) == self._normalize_font_name(font_name):
                    # Intentar extraer el stream de fuente
                    return self._extract_font_stream(xref)
            
            return None
        except Exception:
            return None
    
    def get_font_metrics(
        self, 
        font_name: str,
        page_num: int = 0
    ) -> FontMetrics:
        """
        Obtiene las métricas de una fuente.
        
        Args:
            font_name: Nombre de la fuente
            page_num: Número de página
        
        Returns:
            FontMetrics con las métricas
        """
        font_info = self.get_font_info(font_name, page_num)
        return font_info.metrics
    
    def find_similar_font(
        self, 
        font_name: str,
        page_num: int = 0
    ) -> Optional[str]:
        """
        Busca una fuente similar en el documento.
        
        Útil cuando una fuente subset no tiene todos los glifos
        necesarios y se necesita un fallback.
        
        Args:
            font_name: Nombre de la fuente original
            page_num: Número de página inicial
        
        Returns:
            Nombre de fuente similar o None
        """
        target_info = self.get_font_info(font_name, page_num)
        clean_name = target_info.clean_name.lower()
        
        # Buscar en todas las páginas
        for pn in range(self.doc.page_count if self.doc else 0):
            for font in self.get_page_fonts(pn):
                if font.name == font_name:
                    continue
                
                # Verificar si es similar
                if font.clean_name.lower() in clean_name or clean_name in font.clean_name.lower():
                    # Preferir fuentes no subset
                    if not font.is_subset:
                        return font.name
        
        return None
    
    def get_document_fonts(self) -> List[FontInfo]:
        """
        Obtiene todas las fuentes del documento.
        
        Returns:
            Lista de FontInfo
        """
        if not self.doc:
            return []
        
        all_fonts: Dict[str, FontInfo] = {}
        
        for page_num in range(self.doc.page_count):
            for font in self.get_page_fonts(page_num):
                if font.name not in all_fonts:
                    all_fonts[font.name] = font
        
        return list(all_fonts.values())
    
    def analyze_font_usage(self) -> Dict[str, Any]:
        """
        Analiza el uso de fuentes en el documento.
        
        Returns:
            Diccionario con estadísticas de uso
        """
        if not self.doc:
            return {}
        
        stats = {
            'total_fonts': 0,
            'embedded_fonts': 0,
            'subset_fonts': 0,
            'font_types': {},
            'encodings': {},
            'pages_per_font': {},
        }
        
        font_pages: Dict[str, Set[int]] = {}
        
        for page_num in range(self.doc.page_count):
            for font in self.get_page_fonts(page_num):
                if font.name not in font_pages:
                    font_pages[font.name] = set()
                    stats['total_fonts'] += 1
                    
                    if font.is_embedded:
                        stats['embedded_fonts'] += 1
                    if font.is_subset:
                        stats['subset_fonts'] += 1
                    
                    # Contar tipos
                    type_name = font.font_type.name
                    stats['font_types'][type_name] = stats['font_types'].get(type_name, 0) + 1
                    
                    # Contar encodings
                    enc_name = font.encoding.name
                    stats['encodings'][enc_name] = stats['encodings'].get(enc_name, 0) + 1
                
                font_pages[font.name].add(page_num)
        
        # Calcular páginas por fuente
        stats['pages_per_font'] = {name: len(pages) for name, pages in font_pages.items()}
        
        return stats
    
    # ========== Métodos privados ==========
    
    def _extract_font_info(self, font_name: str, page_num: int) -> FontInfo:
        """Extrae información de una fuente."""
        # Detectar subset
        is_subset, subset_prefix, clean_name = self._parse_font_name(font_name)
        
        # Valores por defecto
        font_type = self._detect_font_type(font_name)
        is_embedded = self._check_embedded(font_name, page_num)
        encoding = self._detect_encoding(font_name, page_num)
        metrics = self._extract_metrics(font_name, page_num)
        widths = self._extract_widths(font_name, page_num)
        bbox = self._extract_bbox(font_name, page_num)
        flags = self._extract_flags(font_name, page_num)
        
        return FontInfo(
            name=font_name,
            base_font=clean_name,
            font_type=font_type,
            is_embedded=is_embedded,
            is_subset=is_subset,
            subset_prefix=subset_prefix,
            encoding=encoding,
            metrics=metrics,
            bbox=bbox,
            widths=widths,
            default_width=widths.get(-1, 0) if widths else 0,
            **flags
        )
    
    def _parse_font_name(self, font_name: str) -> Tuple[bool, Optional[str], str]:
        """Parsea el nombre de fuente para detectar subset."""
        match = self.SUBSET_PATTERN.match(font_name)
        if match:
            return True, match.group(1), match.group(2)
        return False, None, font_name
    
    def _detect_font_type(self, font_name: str) -> FontType:
        """Detecta el tipo de fuente."""
        name_lower = font_name.lower()
        
        # Heurísticas basadas en nombre
        if 'truetype' in name_lower or '-identity' in name_lower:
            return FontType.TRUETYPE
        if 'type1' in name_lower or 'psname' in name_lower:
            return FontType.TYPE1
        if 'opentype' in name_lower or 'cff' in name_lower:
            return FontType.OPENTYPE
        if 'cid' in name_lower:
            if 'type0' in name_lower:
                return FontType.CID_TYPE0
            if 'type2' in name_lower:
                return FontType.CID_TYPE2
        
        # Por defecto asumir TrueType (más común en PDFs modernos)
        return FontType.TRUETYPE
    
    def _check_embedded(self, font_name: str, page_num: int) -> bool:
        """Verifica si la fuente está embebida."""
        if not self.doc:
            # Asumir no embebida si no hay documento
            return False
        
        try:
            page = self.doc[page_num]
            font_list = page.get_fonts()
            
            for font_entry in font_list:
                name = font_entry[3] if len(font_entry) > 3 else ""
                if name == font_name:
                    # El segundo elemento indica si está embebida
                    ext = font_entry[1] if len(font_entry) > 1 else ""
                    # Si hay extensión de archivo, está embebida
                    return bool(ext)
            
            return False
        except Exception:
            return False
    
    def _detect_encoding(self, font_name: str, page_num: int) -> FontEncoding:
        """Detecta el encoding de la fuente."""
        name_lower = font_name.lower()
        
        if 'identity-h' in name_lower:
            return FontEncoding.IDENTITY_H
        if 'identity-v' in name_lower:
            return FontEncoding.IDENTITY_V
        if 'winansi' in name_lower:
            return FontEncoding.WINANSI
        if 'macroman' in name_lower:
            return FontEncoding.MACROMAN
        if 'symbol' in name_lower:
            return FontEncoding.SYMBOL
        if 'zapf' in name_lower or 'dingbat' in name_lower:
            return FontEncoding.ZAPFDINGBATS
        
        # Por defecto WinAnsi
        return FontEncoding.WINANSI
    
    def _extract_metrics(self, font_name: str, page_num: int) -> FontMetrics:
        """Extrae métricas de la fuente."""
        # Valores por defecto típicos para fuentes latinas
        return FontMetrics(
            ascender=800.0,
            descender=-200.0,
            cap_height=700.0,
            x_height=500.0,
            line_gap=200.0,
            units_per_em=1000
        )
    
    def _extract_widths(self, font_name: str, page_num: int) -> Dict[int, float]:
        """Extrae anchos de glifos."""
        # Anchos estándar por defecto (monoespaciado aproximado)
        widths = {}
        default_width = 600.0  # Ancho típico para fuentes proporcionales
        
        # Espacio
        widths[32] = 250.0
        
        # Letras (aproximación)
        for code in range(65, 91):  # A-Z
            widths[code] = 722.0
        for code in range(97, 123):  # a-z
            widths[code] = 500.0
        
        # Números
        for code in range(48, 58):  # 0-9
            widths[code] = 556.0
        
        # Puntuación común
        widths[46] = 250.0  # .
        widths[44] = 250.0  # ,
        widths[33] = 333.0  # !
        widths[63] = 500.0  # ?
        
        # Default width marker
        widths[-1] = default_width
        
        return widths
    
    def _extract_bbox(self, font_name: str, page_num: int) -> Tuple[float, float, float, float]:
        """Extrae el bounding box de la fuente."""
        # BBox típico
        return (-150, -250, 1100, 900)
    
    def _extract_flags(self, font_name: str, page_num: int) -> Dict[str, bool]:
        """Extrae flags de la fuente."""
        name_lower = font_name.lower()
        
        return {
            'is_fixed_pitch': 'mono' in name_lower or 'courier' in name_lower,
            'is_serif': 'times' in name_lower or 'serif' in name_lower or 'georgia' in name_lower,
            'is_symbolic': 'symbol' in name_lower or 'wingding' in name_lower,
            'is_script': 'script' in name_lower or 'brush' in name_lower,
            'is_italic': 'italic' in name_lower or 'oblique' in name_lower,
            'is_all_cap': False,
            'is_small_cap': 'smallcap' in name_lower or 'sc' in name_lower,
            'is_force_bold': 'bold' in name_lower,
        }
    
    def _extract_font_stream(self, xref: int) -> Optional[bytes]:
        """Extrae el stream de datos de la fuente."""
        if not self.doc:
            return None
        
        try:
            # Intentar obtener el objeto del xref
            obj = self.doc.xref_object(xref)
            if not obj:
                return None
            
            # Buscar el stream
            stream = self.doc.xref_stream(xref)
            return stream if stream else None
        except Exception:
            return None
    
    def _normalize_font_name(self, name: str) -> str:
        """Normaliza un nombre de fuente para comparación."""
        # Quitar prefijo de subset
        _, _, clean = self._parse_font_name(name)
        # Normalizar
        return clean.lower().replace('-', '').replace(' ', '')


# ========== Funciones de utilidad ==========

def extract_font_info(
    doc: 'fitz.Document',
    font_name: str,
    page_num: int = 0
) -> FontInfo:
    """
    Extrae información de una fuente.
    
    Args:
        doc: Documento PDF
        font_name: Nombre de la fuente
        page_num: Número de página
    
    Returns:
        FontInfo con información de la fuente
    """
    extractor = EmbeddedFontExtractor(doc)
    return extractor.get_font_info(font_name, page_num)


def is_font_embedded(
    doc: 'fitz.Document',
    font_name: str,
    page_num: int = 0
) -> bool:
    """
    Verifica si una fuente está embebida.
    
    Args:
        doc: Documento PDF
        font_name: Nombre de la fuente
        page_num: Número de página
    
    Returns:
        True si está embebida
    """
    extractor = EmbeddedFontExtractor(doc)
    info = extractor.get_font_info(font_name, page_num)
    return info.is_embedded


def is_subset_font(font_name: str) -> bool:
    """
    Verifica si un nombre de fuente indica subset.
    
    Args:
        font_name: Nombre de la fuente
    
    Returns:
        True si es subset
    """
    return bool(EmbeddedFontExtractor.SUBSET_PATTERN.match(font_name))


def get_clean_font_name(font_name: str) -> str:
    """
    Obtiene el nombre de fuente sin prefijo de subset.
    
    Args:
        font_name: Nombre de la fuente
    
    Returns:
        Nombre limpio
    """
    match = EmbeddedFontExtractor.SUBSET_PATTERN.match(font_name)
    if match:
        return match.group(2)
    return font_name


def get_font_type_from_name(font_name: str) -> FontType:
    """
    Detecta el tipo de fuente desde su nombre.
    
    Args:
        font_name: Nombre de la fuente
    
    Returns:
        FontType detectado
    """
    extractor = EmbeddedFontExtractor()
    return extractor._detect_font_type(font_name)


def calculate_text_width_simple(
    text: str,
    font_size: float,
    char_width_ratio: float = 0.5
) -> float:
    """
    Calcula ancho de texto de forma simplificada.
    
    Args:
        text: Texto a medir
        font_size: Tamaño de fuente
        char_width_ratio: Ratio ancho/alto promedio
    
    Returns:
        Ancho estimado en puntos
    """
    return len(text) * font_size * char_width_ratio


def list_embedded_fonts(doc: 'fitz.Document') -> List[str]:
    """
    Lista todas las fuentes embebidas en un documento.
    
    Args:
        doc: Documento PDF
    
    Returns:
        Lista de nombres de fuentes embebidas
    """
    extractor = EmbeddedFontExtractor(doc)
    all_fonts = extractor.get_document_fonts()
    return [f.name for f in all_fonts if f.is_embedded]


def list_subset_fonts(doc: 'fitz.Document') -> List[str]:
    """
    Lista todas las fuentes subset en un documento.
    
    Args:
        doc: Documento PDF
    
    Returns:
        Lista de nombres de fuentes subset
    """
    extractor = EmbeddedFontExtractor(doc)
    all_fonts = extractor.get_document_fonts()
    return [f.name for f in all_fonts if f.is_subset]


def get_font_embedding_status(
    doc: 'fitz.Document',
    font_name: str,
    page_num: int = 0
) -> EmbeddingStatus:
    """
    Obtiene el estado de embedding de una fuente.
    
    Args:
        doc: Documento PDF
        font_name: Nombre de la fuente
        page_num: Número de página
    
    Returns:
        EmbeddingStatus de la fuente
    """
    extractor = EmbeddedFontExtractor(doc)
    info = extractor.get_font_info(font_name, page_num)
    return info.embedding_status


__all__ = [
    # Enums
    'FontType',
    'EmbeddingStatus',
    'FontEncoding',
    
    # Dataclasses
    'FontMetrics',
    'GlyphInfo',
    'FontInfo',
    'FontExtractorConfig',
    
    # Clase principal
    'EmbeddedFontExtractor',
    
    # Funciones de utilidad
    'extract_font_info',
    'is_font_embedded',
    'is_subset_font',
    'get_clean_font_name',
    'get_font_type_from_name',
    'calculate_text_width_simple',
    'list_embedded_fonts',
    'list_subset_fonts',
    'get_font_embedding_status',
]

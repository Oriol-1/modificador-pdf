"""
TextSpanMetrics - Métricas completas de un span de texto PDF.

Este módulo define la estructura de datos fundamental para almacenar
TODAS las propiedades tipográficas extraídas de un span de texto en PDF.

Un "span" en PDF es un fragmento de texto con estilo uniforme.
Un mismo párrafo visual puede contener múltiples spans con diferentes estilos.

Propiedades extraídas:
- Identificación: texto, página, ID único
- Geometría: bbox, origen, baseline
- Fuente: nombre, tamaño, flags, embedding status
- Color y render: fill, stroke, render mode
- Transformación: CTM, text matrix, scale, rotación
- Espaciado: Tc (char), Tw (word), anchos de glifos
- Posición vertical: rise (super/sub), leading
- Estilos inferidos: bold, italic, superscript, subscript
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum, IntEnum
import uuid
import json


class RenderMode(IntEnum):
    """
    Modos de renderizado de texto en PDF.
    
    Según la especificación PDF 1.7, sección 9.3.6.
    """
    FILL = 0                    # Rellenar texto
    STROKE = 1                  # Trazar contorno
    FILL_STROKE = 2             # Rellenar y trazar
    INVISIBLE = 3               # Invisible (para selección)
    FILL_CLIP = 4               # Rellenar y añadir a path de clip
    STROKE_CLIP = 5             # Trazar y añadir a path de clip
    FILL_STROKE_CLIP = 6        # Rellenar, trazar y clip
    CLIP = 7                    # Solo añadir a path de clip


class FontEmbeddingStatus(Enum):
    """Estado de embedding de una fuente en el PDF."""
    NOT_EMBEDDED = "not_embedded"       # Fuente no embebida (referencia externa)
    FULLY_EMBEDDED = "fully_embedded"   # Fuente completamente embebida
    SUBSET = "subset"                   # Solo subset embebido (ABCDEF+FontName)
    UNKNOWN = "unknown"                 # No se pudo determinar


@dataclass
class TextSpanMetrics:
    """
    Métricas completas extraídas del PDF para un span de texto.
    
    Esta clase es el fundamento del motor de texto. Contiene TODAS las
    propiedades necesarias para:
    1. Mostrar información al usuario (tooltip, inspector)
    2. Preservar formato al editar
    3. Reconstruir el texto en el PDF
    
    Attributes:
        === Identificación básica ===
        text: Contenido de texto del span
        page_num: Número de página (0-indexed)
        span_id: ID único para tracking y referencia
        
        === Geometría ===
        bbox: Bounding box (x0, y0, x1, y1) en coordenadas PDF
        origin: Punto de origen del texto (x, y)
        baseline_y: Coordenada Y del baseline
        
        === Fuente ===
        font_name: Nombre de fuente normalizado (para uso)
        font_name_pdf: Nombre original en el PDF (puede incluir subset prefix)
        font_size: Tamaño en puntos
        font_flags: Flags PDF originales (bits para bold, italic, etc.)
        embedding_status: Estado de embedding de la fuente
        font_bbox: BBox de la fuente si está disponible
        
        === Color y render ===
        fill_color: Color de relleno como hex (#RRGGBB)
        stroke_color: Color de trazo si aplica
        render_mode: Modo de renderizado (fill, stroke, etc.)
        fill_opacity: Opacidad del relleno (0-1)
        stroke_opacity: Opacidad del trazo (0-1)
        
        === Transformación ===
        ctm: Current Transformation Matrix (a, b, c, d, e, f)
        text_matrix: Text matrix del operador Tm
        horizontal_scale: Escalado horizontal Tz (100 = normal)
        rotation: Rotación en grados
        skew_x: Inclinación horizontal
        skew_y: Inclinación vertical
        
        === Espaciado ===
        char_spacing: Tc - espaciado adicional entre caracteres (puntos)
        word_spacing: Tw - espaciado adicional entre palabras (puntos)
        char_widths: Lista de anchos de cada carácter
        total_width: Ancho total del span
        
        === Posición vertical ===
        rise: Ts - desplazamiento vertical para super/subíndices
        leading: TL - interlineado si está definido
        
        === Estilos inferidos ===
        is_bold: True/False/None (None = incierto)
        is_italic: True/False/None
        is_superscript: Inferido de rise > 0
        is_subscript: Inferido de rise < 0
        
        === Metadatos de tracking ===
        was_fallback: Si se aplicó fallback de fuente
        fallback_from: Fuente original si hubo fallback
        confidence: Confianza en la detección (0-1)
        raw_span_data: Datos originales del span de PyMuPDF
    """
    
    # === Identificación básica ===
    text: str
    page_num: int
    span_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # === Geometría ===
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    origin: Tuple[float, float] = (0.0, 0.0)
    baseline_y: float = 0.0
    
    # === Fuente ===
    font_name: str = "Helvetica"
    font_name_pdf: str = ""
    font_size: float = 12.0
    font_flags: int = 0
    embedding_status: FontEmbeddingStatus = FontEmbeddingStatus.UNKNOWN
    font_bbox: Optional[Tuple[float, float, float, float]] = None
    
    # === Color y render ===
    fill_color: str = "#000000"
    stroke_color: Optional[str] = None
    render_mode: RenderMode = RenderMode.FILL
    fill_opacity: float = 1.0
    stroke_opacity: float = 1.0
    
    # === Transformación ===
    ctm: Tuple[float, float, float, float, float, float] = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    text_matrix: Tuple[float, float, float, float, float, float] = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    horizontal_scale: float = 100.0  # Porcentaje (100 = normal)
    rotation: float = 0.0
    skew_x: float = 0.0
    skew_y: float = 0.0
    
    # === Espaciado ===
    char_spacing: float = 0.0  # Tc en puntos
    word_spacing: float = 0.0  # Tw en puntos
    char_widths: List[float] = field(default_factory=list)
    total_width: float = 0.0
    
    # === Posición vertical ===
    rise: float = 0.0  # Ts en puntos
    leading: float = 0.0  # TL en puntos
    
    # === Estilos inferidos ===
    is_bold: Optional[bool] = None
    is_italic: Optional[bool] = None
    is_superscript: bool = False
    is_subscript: bool = False
    
    # === Metadatos de tracking ===
    was_fallback: bool = False
    fallback_from: Optional[str] = None
    confidence: float = 1.0
    raw_span_data: Optional[Dict[str, Any]] = field(default=None, repr=False)
    
    def __post_init__(self):
        """Validación y normalización post-inicialización."""
        # Normalizar font_name_pdf si está vacío
        if not self.font_name_pdf:
            self.font_name_pdf = self.font_name
        
        # Detectar super/subíndice basado en rise
        if self.rise > 0:
            self.is_superscript = True
        elif self.rise < 0:
            self.is_subscript = True
        
        # Calcular total_width si no está definido pero tenemos char_widths
        if self.total_width == 0 and self.char_widths:
            self.total_width = sum(self.char_widths)
        
        # Detectar embedding status por nombre si no está definido
        if self.embedding_status == FontEmbeddingStatus.UNKNOWN:
            self.embedding_status = self._detect_embedding_from_name()
    
    def _detect_embedding_from_name(self) -> FontEmbeddingStatus:
        """Detecta el estado de embedding basándose en el nombre de fuente."""
        if not self.font_name_pdf:
            return FontEmbeddingStatus.UNKNOWN
        
        # Patrón de subset: ABCDEF+FontName
        if "+" in self.font_name_pdf:
            prefix = self.font_name_pdf.split("+")[0]
            # Los prefijos de subset son típicamente 6 letras mayúsculas
            if len(prefix) == 6 and prefix.isupper() and prefix.isalpha():
                return FontEmbeddingStatus.SUBSET
        
        return FontEmbeddingStatus.UNKNOWN
    
    # === Propiedades calculadas ===
    
    @property
    def width(self) -> float:
        """Ancho del span (x1 - x0)."""
        return self.bbox[2] - self.bbox[0]
    
    @property
    def height(self) -> float:
        """Altura del span (y1 - y0)."""
        return self.bbox[3] - self.bbox[1]
    
    @property
    def center(self) -> Tuple[float, float]:
        """Centro del bbox."""
        return (
            (self.bbox[0] + self.bbox[2]) / 2,
            (self.bbox[1] + self.bbox[3]) / 2
        )
    
    @property
    def is_subset_font(self) -> bool:
        """True si la fuente es un subset."""
        return self.embedding_status == FontEmbeddingStatus.SUBSET
    
    @property
    def is_embedded_font(self) -> bool:
        """True si la fuente está embebida (completa o subset)."""
        return self.embedding_status in (
            FontEmbeddingStatus.FULLY_EMBEDDED,
            FontEmbeddingStatus.SUBSET
        )
    
    @property
    def has_transformation(self) -> bool:
        """True si hay transformación no trivial."""
        identity = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        return self.ctm != identity or self.text_matrix != identity
    
    @property
    def has_custom_spacing(self) -> bool:
        """True si hay espaciado personalizado (Tc o Tw)."""
        return self.char_spacing != 0 or self.word_spacing != 0
    
    @property
    def style_summary(self) -> str:
        """Resumen legible del estilo."""
        parts = [f"{self.font_name} {self.font_size:.1f}pt"]
        
        if self.is_bold:
            parts.append("Bold")
        if self.is_italic:
            parts.append("Italic")
        if self.is_superscript:
            parts.append("Superscript")
        if self.is_subscript:
            parts.append("Subscript")
        
        return " ".join(parts)
    
    @property
    def spacing_summary(self) -> str:
        """Resumen del espaciado."""
        parts = []
        if self.char_spacing != 0:
            parts.append(f"Tc={self.char_spacing:.2f}")
        if self.word_spacing != 0:
            parts.append(f"Tw={self.word_spacing:.2f}")
        if self.rise != 0:
            parts.append(f"Rise={self.rise:.2f}")
        
        return ", ".join(parts) if parts else "Normal"
    
    # === Métodos de comparación ===
    
    def has_same_style(self, other: 'TextSpanMetrics', tolerance: float = 0.5) -> bool:
        """
        Compara si dos spans tienen el mismo estilo visual.
        
        Args:
            other: Otro span para comparar
            tolerance: Tolerancia para comparación de tamaños
            
        Returns:
            True si los estilos son visualmente equivalentes
        """
        return (
            self.font_name == other.font_name and
            abs(self.font_size - other.font_size) < tolerance and
            self.fill_color == other.fill_color and
            self.is_bold == other.is_bold and
            self.is_italic == other.is_italic
        )
    
    def has_same_spacing(self, other: 'TextSpanMetrics', tolerance: float = 0.1) -> bool:
        """Compara si dos spans tienen el mismo espaciado."""
        return (
            abs(self.char_spacing - other.char_spacing) < tolerance and
            abs(self.word_spacing - other.word_spacing) < tolerance
        )
    
    def is_on_same_baseline(self, other: 'TextSpanMetrics', tolerance: float = 2.0) -> bool:
        """Verifica si dos spans están en el mismo baseline."""
        return abs(self.baseline_y - other.baseline_y) < tolerance
    
    # === Serialización ===
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización JSON."""
        return {
            # Identificación
            "text": self.text,
            "page_num": self.page_num,
            "span_id": self.span_id,
            
            # Geometría
            "bbox": list(self.bbox),
            "origin": list(self.origin),
            "baseline_y": self.baseline_y,
            
            # Fuente
            "font_name": self.font_name,
            "font_name_pdf": self.font_name_pdf,
            "font_size": self.font_size,
            "font_flags": self.font_flags,
            "embedding_status": self.embedding_status.value,
            "font_bbox": list(self.font_bbox) if self.font_bbox else None,
            
            # Color y render
            "fill_color": self.fill_color,
            "stroke_color": self.stroke_color,
            "render_mode": self.render_mode.value,
            "fill_opacity": self.fill_opacity,
            "stroke_opacity": self.stroke_opacity,
            
            # Transformación
            "ctm": list(self.ctm),
            "text_matrix": list(self.text_matrix),
            "horizontal_scale": self.horizontal_scale,
            "rotation": self.rotation,
            "skew_x": self.skew_x,
            "skew_y": self.skew_y,
            
            # Espaciado
            "char_spacing": self.char_spacing,
            "word_spacing": self.word_spacing,
            "char_widths": self.char_widths,
            "total_width": self.total_width,
            
            # Posición vertical
            "rise": self.rise,
            "leading": self.leading,
            
            # Estilos inferidos
            "is_bold": self.is_bold,
            "is_italic": self.is_italic,
            "is_superscript": self.is_superscript,
            "is_subscript": self.is_subscript,
            
            # Metadatos
            "was_fallback": self.was_fallback,
            "fallback_from": self.fallback_from,
            "confidence": self.confidence,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextSpanMetrics':
        """Crea una instancia desde un diccionario."""
        # Convertir valores especiales
        data = data.copy()
        
        # Convertir listas a tuplas donde corresponde
        if "bbox" in data:
            data["bbox"] = tuple(data["bbox"])
        if "origin" in data:
            data["origin"] = tuple(data["origin"])
        if "ctm" in data:
            data["ctm"] = tuple(data["ctm"])
        if "text_matrix" in data:
            data["text_matrix"] = tuple(data["text_matrix"])
        if "font_bbox" in data and data["font_bbox"]:
            data["font_bbox"] = tuple(data["font_bbox"])
        
        # Convertir enums
        if "embedding_status" in data:
            data["embedding_status"] = FontEmbeddingStatus(data["embedding_status"])
        if "render_mode" in data:
            data["render_mode"] = RenderMode(data["render_mode"])
        
        # Eliminar raw_span_data si viene en el dict (no serializable)
        data.pop("raw_span_data", None)
        
        return cls(**data)
    
    def to_json(self) -> str:
        """Serializa a JSON."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TextSpanMetrics':
        """Deserializa desde JSON."""
        return cls.from_dict(json.loads(json_str))
    
    # === Representación ===
    
    def __repr__(self) -> str:
        text_preview = self.text[:20] + "..." if len(self.text) > 20 else self.text
        return (
            f"TextSpanMetrics('{text_preview}', "
            f"{self.font_name} {self.font_size:.1f}pt, "
            f"page={self.page_num})"
        )
    
    def __str__(self) -> str:
        return f"[{self.span_id}] '{self.text}' - {self.style_summary}"
    
    def detailed_info(self) -> str:
        """Retorna información detallada para debugging/tooltips."""
        lines = [
            f"=== Span [{self.span_id}] ===",
            f"Text: '{self.text}'",
            f"Page: {self.page_num}",
            "",
            "--- Geometría ---",
            f"BBox: ({self.bbox[0]:.2f}, {self.bbox[1]:.2f}, {self.bbox[2]:.2f}, {self.bbox[3]:.2f})",
            f"Origin: ({self.origin[0]:.2f}, {self.origin[1]:.2f})",
            f"Baseline Y: {self.baseline_y:.2f}",
            f"Size: {self.width:.2f} x {self.height:.2f}",
            "",
            "--- Fuente ---",
            f"Font: {self.font_name} ({self.font_name_pdf})",
            f"Size: {self.font_size:.2f}pt",
            f"Flags: {self.font_flags} (0x{self.font_flags:04x})",
            f"Embedding: {self.embedding_status.value}",
            "",
            "--- Color/Render ---",
            f"Fill: {self.fill_color}",
            f"Stroke: {self.stroke_color or 'None'}",
            f"Render Mode: {self.render_mode.name}",
            "",
            "--- Espaciado ---",
            f"Char Spacing (Tc): {self.char_spacing:.3f}pt",
            f"Word Spacing (Tw): {self.word_spacing:.3f}pt",
            f"Rise (Ts): {self.rise:.3f}pt",
            f"Horizontal Scale: {self.horizontal_scale:.1f}%",
            "",
            "--- Estilos ---",
            f"Bold: {self.is_bold}",
            f"Italic: {self.is_italic}",
            f"Superscript: {self.is_superscript}",
            f"Subscript: {self.is_subscript}",
        ]
        
        if self.was_fallback:
            lines.append("")
            lines.append("--- Fallback ---")
            lines.append(f"Original Font: {self.fallback_from}")
            lines.append(f"Confidence: {self.confidence:.2f}")
        
        return "\n".join(lines)


# === Funciones de fábrica ===

def create_span_from_pymupdf(
    span_dict: Dict[str, Any],
    page_num: int,
    font_manager=None
) -> TextSpanMetrics:
    """
    Crea un TextSpanMetrics desde un span dict de PyMuPDF.
    
    Esta función es el puente entre PyMuPDF y nuestro modelo de datos.
    Extrae toda la información disponible del span y aplica detección
    de propiedades cuando es necesario.
    
    Args:
        span_dict: Dict del span de page.get_text("dict")
        page_num: Número de página
        font_manager: Instancia de FontManager para detección de fuentes
        
    Returns:
        TextSpanMetrics con toda la información extraída
    """
    # Extraer datos básicos
    text = span_dict.get("text", "")
    bbox = tuple(span_dict.get("bbox", (0, 0, 0, 0)))
    origin = tuple(span_dict.get("origin", (bbox[0], bbox[3])))
    
    # Fuente
    font_name_pdf = span_dict.get("font", "Helvetica")
    font_size = float(span_dict.get("size", 12.0))
    font_flags = span_dict.get("flags", 0)
    
    # Normalizar nombre de fuente (quitar subset prefix)
    font_name = font_name_pdf
    if "+" in font_name_pdf:
        font_name = font_name_pdf.split("+", 1)[1]
    
    # Color (PyMuPDF devuelve int en formato BGR)
    color_int = span_dict.get("color", 0)
    if isinstance(color_int, int):
        r = (color_int) & 0xFF
        g = (color_int >> 8) & 0xFF
        b = (color_int >> 16) & 0xFF
        fill_color = f"#{r:02x}{g:02x}{b:02x}"
    else:
        fill_color = "#000000"
    
    # Calcular baseline_y (generalmente es y1 - descender)
    # Por defecto usamos el bottom del bbox ajustado
    # Nota: ascender no se usa actualmente pero podría usarse para métricas futuras
    descender = span_dict.get("descender", -0.2)
    baseline_y = bbox[3] + (descender * font_size) if descender else bbox[3]
    
    # Obtener anchos de caracteres si están disponibles
    char_widths = []
    if "chars" in span_dict:
        for char_info in span_dict["chars"]:
            char_bbox = char_info.get("bbox", (0, 0, 0, 0))
            char_widths.append(char_bbox[2] - char_bbox[0])
    
    # Detectar bold/italic usando FontManager si está disponible
    is_bold = None
    is_italic = None
    was_fallback = False
    fallback_from = None
    
    if font_manager:
        descriptor = font_manager.detect_font(span_dict)
        is_bold = descriptor.possible_bold
        was_fallback = descriptor.was_fallback
        fallback_from = descriptor.fallback_from
        if was_fallback:
            font_name = descriptor.name
    else:
        # Detección básica por flags
        # Flag 0x10 (16) = serif, 0x20 (32) = script
        # Flag 0x40 (64) puede indicar bold en algunos PDFs
        if font_flags & 0x40:
            is_bold = True
        
        # Detección por nombre
        name_lower = font_name.lower()
        if any(ind in name_lower for ind in ["bold", "-b", "_b", "heavy", "black"]):
            is_bold = True
        if any(ind in name_lower for ind in ["italic", "oblique", "-i", "_i"]):
            is_italic = True
    
    # Crear el span
    return TextSpanMetrics(
        text=text,
        page_num=page_num,
        bbox=bbox,
        origin=origin,
        baseline_y=baseline_y,
        font_name=font_name,
        font_name_pdf=font_name_pdf,
        font_size=font_size,
        font_flags=font_flags,
        fill_color=fill_color,
        char_widths=char_widths,
        total_width=bbox[2] - bbox[0],
        is_bold=is_bold,
        is_italic=is_italic,
        was_fallback=was_fallback,
        fallback_from=fallback_from,
        raw_span_data=span_dict,
    )


def create_empty_span(
    page_num: int = 0,
    font_name: str = "Helvetica",
    font_size: float = 12.0
) -> TextSpanMetrics:
    """
    Crea un span vacío con valores por defecto.
    
    Útil para testing o como placeholder.
    
    Args:
        page_num: Número de página
        font_name: Nombre de fuente
        font_size: Tamaño de fuente
        
    Returns:
        TextSpanMetrics vacío con valores por defecto
    """
    return TextSpanMetrics(
        text="",
        page_num=page_num,
        font_name=font_name,
        font_size=font_size,
    )

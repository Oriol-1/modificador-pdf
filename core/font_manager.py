"""
FontManager - Gestión centralizada de fuentes para PDF Editor Pro

Responsable de:
1. Detectar fuentes en PDFs (nombre, tamaño, color)
2. Mapear fuentes custom a equivalentes estándar (fallback)
3. Detectar negritas (con heurísticas y métricas precisas)
4. Calcular tamaño real de texto usando QFontMetrics
5. Manejar estrategias de fallback para bold/italic
6. Integración con text_engine para extracción precisa de fuentes

Limitación técnica importante:
- PyMuPDF NO puede detectar automáticamente si una fuente es bold
- Usamos heurísticas: nombre contiene "Bold", comparar widths, flags PDF
- Resultado puede ser True (probablemente bold) / False (no bold) / None (incierto)

Fase 3B: Integración con text_engine
- FontDescriptor extendido con métricas precisas
- Detección de estado de embedding (embedded/subset/external)
- Métricas precisas desde el PDF (ascender, descender, widths)
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Any, TYPE_CHECKING
from enum import Enum
import logging

from PyQt5.QtGui import QFont, QFontMetrics

# Import text_engine components (con TYPE_CHECKING para evitar circular imports)
if TYPE_CHECKING:
    from core.text_engine import EmbeddedFontExtractor

# Try to import text_engine components
try:
    from core.text_engine import (
        EmbeddedFontExtractor,
        EmbeddingStatus,
        is_subset_font,
        get_clean_font_name,
    )
    TEXT_ENGINE_AVAILABLE = True
except ImportError:
    TEXT_ENGINE_AVAILABLE = False
    EmbeddingStatus = None  # type: ignore

logger = logging.getLogger(__name__)


class BoldStrategy(Enum):
    """Estrategias para aplicar negritas."""
    EXACT_BOLD = "exact_bold"           # Usar variante Bold exacta
    APPROXIMATE_BOLD = "approximate"     # Fallback: subrayado + oscuro
    WARNING_FALLBACK = "warning"         # Advertencia, no se aplicó


class FontEmbeddingStatus(Enum):
    """Estado de embedding de la fuente en el PDF."""
    EMBEDDED = "embedded"       # Fuente completamente embebida
    SUBSET = "subset"           # Fuente embebida como subset
    EXTERNAL = "external"       # Fuente no embebida (referencia externa)
    UNKNOWN = "unknown"         # No se pudo determinar


@dataclass
class PreciseMetrics:
    """
    Métricas precisas extraídas directamente del PDF.
    
    Estas métricas vienen del diccionario de fuente del PDF,
    no de Qt, por lo que son más precisas para el documento.
    """
    ascender: float = 0.0          # Altura sobre baseline (unidades de fuente)
    descender: float = 0.0         # Profundidad bajo baseline (negativo)
    line_height: float = 0.0       # Altura de línea calculada
    avg_char_width: float = 0.0    # Ancho promedio de caracteres
    cap_height: float = 0.0        # Altura de mayúsculas
    x_height: float = 0.0          # Altura de minúsculas (x)
    stem_v: float = 0.0            # Grosor de stems verticales (indica bold)
    stem_h: float = 0.0            # Grosor de stems horizontales
    italic_angle: float = 0.0      # Ángulo de italics (0 = no italic)
    
    @property
    def is_bold_by_stem(self) -> Optional[bool]:
        """Detecta bold según grosor de stem (>100 generalmente bold)."""
        if self.stem_v <= 0:
            return None  # Sin info
        return self.stem_v > 100
    
    @property  
    def is_italic_by_angle(self) -> bool:
        """Detecta italic según ángulo."""
        return abs(self.italic_angle) > 5


@dataclass
class FontDescriptor:
    """
    Descriptor de fuente extraído de un span de PDF.
    
    Fase 3B: Extendido con métricas precisas y estado de embedding.
    
    Attributes:
        name: Nombre de fuente detectado (ej: "Arial", "MyriadPro")
        size: Tamaño en puntos (ej: 12)
        color: Color como hex (ej: "#000000")
        flags: Flags PDF (indica posibles estilos)
        was_fallback: True si se usó fallback de fuente
        fallback_from: Fuente original si fue reemplazada
        possible_bold: True/False/None (detección heurística)
        
        # Fase 3B - Nuevos campos
        embedding_status: Estado de embedding (embedded/subset/external)
        precise_metrics: Métricas precisas del PDF (no Qt)
        char_spacing: Espaciado entre caracteres (Tc)
        word_spacing: Espaciado entre palabras (Tw)
        baseline_y: Posición Y del baseline
        bbox: Bounding box del texto [x0, y0, x1, y1]
        original_font_name: Nombre exacto en el PDF (puede incluir subset prefix)
        is_subset: True si la fuente es subset (XXXXXX+FontName)
        glyph_widths: Dict de anchos de glifos {char: width}
    """
    name: str
    size: float
    color: str = "#000000"
    flags: int = 0
    was_fallback: bool = False
    fallback_from: Optional[str] = None
    possible_bold: Optional[bool] = None
    
    # Fase 3B - Nuevos campos con valores por defecto
    embedding_status: FontEmbeddingStatus = FontEmbeddingStatus.UNKNOWN
    precise_metrics: Optional[PreciseMetrics] = None
    char_spacing: float = 0.0
    word_spacing: float = 0.0
    baseline_y: Optional[float] = None
    bbox: Optional[Tuple[float, float, float, float]] = None
    original_font_name: Optional[str] = None
    is_subset: bool = False
    glyph_widths: Dict[str, float] = field(default_factory=dict)

    def __repr__(self) -> str:
        fallback_str = f" (fallback from {self.fallback_from})" if self.was_fallback else ""
        embedding = f" [{self.embedding_status.value}]" if self.embedding_status != FontEmbeddingStatus.UNKNOWN else ""
        return f"FontDescriptor({self.name} {self.size}pt{fallback_str}{embedding})"
    
    def has_precise_metrics(self) -> bool:
        """Verifica si tiene métricas precisas disponibles."""
        return self.precise_metrics is not None
    
    def get_line_height(self) -> float:
        """Obtiene altura de línea (precisa si disponible, sino estimada)."""
        if self.precise_metrics and self.precise_metrics.line_height > 0:
            return self.precise_metrics.line_height * self.size / 1000
        return self.size * 1.2  # Estimación estándar
    
    def is_bold_detected(self) -> Optional[bool]:
        """
        Determina si la fuente es bold usando todas las fuentes de info.
        
        Prioridad:
        1. Métricas precisas (stem_v)
        2. possible_bold (heurística de nombre)
        3. flags PDF
        """
        # 1. Métricas precisas (más confiable)
        if self.precise_metrics:
            stem_bold = self.precise_metrics.is_bold_by_stem
            if stem_bold is not None:
                return stem_bold
        
        # 2. Heurística de nombre
        if self.possible_bold is not None:
            return self.possible_bold
            
        # 3. Flags PDF
        if self.flags & 0x40:  # Flag bold típico
            return True
            
        return None


class FontManager:
    """
    Gestión centralizada de fuentes con fallbacks inteligentes.
    
    Fase 3B: Integrado con text_engine para extracción precisa.
    """

    # Tabla de mappeos: nombre PDF → nombre PyMuPDF (estándar)
    FONT_MAPPING: Dict[str, str] = {
        # Arial y variantes
        "ArialMT": "helv",
        "Arial": "helv",
        "Arial-Roman": "helv",
        "Helvetica": "helv",
        "HelveticaNeue": "helv",
        "Helvetica-Roman": "helv",
        "HelveticaNeue-Roman": "helv",

        # Times y variantes
        "TimesNewRomanPSMT": "times",
        "TimesNewRoman": "times",
        "Times-Roman": "times",
        "TimesRoman": "times",
        "Times": "times",

        # Courier y variantes
        "Courier": "cour",
        "CourierNew": "cour",
        "CourierNewPSMT": "cour",
        "Courier-Oblique": "cour",
        "Courier-Bold": "cour",  # Bold será detectado aparte

        # Symbol
        "Symbol": "symbols",
        "ZapfDingbats": "symbols",

        # Fallbacks comunes (mapeo inteligente basado en similaridad)
        "Georgia": "times",              # Serif similar a Times
        "Verdana": "helv",               # Sans-serif similar a Helvetica
        "Trebuchet": "helv",             # Sans-serif similar
        "Comic Sans MS": "helv",         # Fallback seguro (no ideal)
        "Impact": "helv",                # Bold-heavy → sans-serif robusto
        "Calibri": "helv",               # Microsoft sans-serif
        "Cambria": "times",              # Microsoft serif
        "Consolas": "cour",              # Monospace similar a Courier
    }

    def __init__(self, doc: Any = None):
        """
        Inicializar FontManager.
        
        Args:
            doc: Documento fitz (opcional, para extracción de fuentes embebidas)
        """
        self.logger = logger
        self._font_cache: Dict[str, QFont] = {}
        self._doc = doc
        self._font_extractor: Optional[Any] = None
        self._font_info_cache: Dict[str, Any] = {}
        
        # Inicializar extractor si text_engine está disponible
        if TEXT_ENGINE_AVAILABLE and doc is not None:
            try:
                self._font_extractor = EmbeddedFontExtractor(doc)
            except Exception as e:
                self.logger.warning(f"Could not initialize font extractor: {e}")
    
    def set_document(self, doc: Any) -> None:
        """
        Establece el documento PDF para extracción de fuentes.
        
        Args:
            doc: Documento fitz.Document
        """
        self._doc = doc
        self._font_info_cache.clear()
        
        if TEXT_ENGINE_AVAILABLE and doc is not None:
            try:
                self._font_extractor = EmbeddedFontExtractor(doc)
            except Exception as e:
                self.logger.warning(f"Could not initialize font extractor: {e}")
        else:
            self._font_extractor = None

    def detect_font(self, span: dict, page_num: int = 0) -> FontDescriptor:
        """
        Extrae información de fuente de un span de PyMuPDF.
        
        Fase 3B: Ahora extrae métricas precisas y estado de embedding
        cuando text_engine está disponible.

        Args:
            span: Dict del texto extraído con get_text("dict")
                  Contiene: "font", "size", "color", "flags", etc.
            page_num: Número de página (para cache de fuentes)

        Returns:
            FontDescriptor con información detectada y fallback aplicado si es necesario
        """
        try:
            # Extraer datos básicos
            font_name = span.get("font", "helv")
            size = float(span.get("size", 12.0))
            color = span.get("color", 0)  # 0 = negro

            # Convertir color a hex (PyMuPDF usa int)
            color_hex = self._color_to_hex(color)

            flags = span.get("flags", 0)
            
            # Extraer bbox si está disponible
            bbox = None
            if "bbox" in span:
                bbox = tuple(span["bbox"])
            
            # Extraer baseline si está disponible (origin es la posición del texto)
            baseline_y = None
            if "origin" in span:
                baseline_y = span["origin"][1]

            # Detectar si es estándar o custom
            actual_font = self.smart_fallback(font_name)
            was_fallback = actual_font != font_name

            # Detectar posible bold (heurística básica)
            possible_bold = self.detect_possible_bold(span)
            
            # Fase 3B: Extraer información precisa si text_engine está disponible
            embedding_status = FontEmbeddingStatus.UNKNOWN
            precise_metrics = None
            is_subset = False
            original_font_name = font_name
            glyph_widths: Dict[str, float] = {}
            
            if TEXT_ENGINE_AVAILABLE:
                # Detectar subset
                is_subset = is_subset_font(font_name)
                if is_subset:
                    original_font_name = font_name
                    # Limpiar nombre para mapeo
                    clean_name = get_clean_font_name(font_name)
                    actual_font = self.smart_fallback(clean_name)
                
                # Extraer información de fuente embebida
                if self._font_extractor:
                    try:
                        embedding_status = self.detect_embedded_status(font_name, page_num)
                        precise_metrics = self.get_precise_metrics(font_name, page_num)
                        glyph_widths = self._get_glyph_widths_dict(font_name, page_num)
                    except Exception as e:
                        self.logger.debug(f"Could not extract precise metrics: {e}")

            descriptor = FontDescriptor(
                name=actual_font,
                size=size,
                color=color_hex,
                flags=flags,
                was_fallback=was_fallback,
                fallback_from=font_name if was_fallback else None,
                possible_bold=possible_bold,
                # Fase 3B campos
                embedding_status=embedding_status,
                precise_metrics=precise_metrics,
                char_spacing=0.0,  # Se extrae de content stream
                word_spacing=0.0,  # Se extrae de content stream
                baseline_y=baseline_y,
                bbox=bbox,
                original_font_name=original_font_name,
                is_subset=is_subset,
                glyph_widths=glyph_widths,
            )
            
            # Mejorar detección de bold con métricas precisas
            if precise_metrics and precise_metrics.is_bold_by_stem is not None:
                descriptor.possible_bold = precise_metrics.is_bold_by_stem

            # Log si fue fallback
            if was_fallback:
                self.logger.warning(
                    f"Font fallback: '{font_name}' → '{actual_font}' ({size}pt)"
                )

            return descriptor

        except Exception as e:
            self.logger.error(f"Error detectando fuente de span: {e}")
            # Retornar fallback seguro
            return FontDescriptor(
                name="helv",
                size=12.0,
                color="#000000",
                was_fallback=True,
                fallback_from=span.get("font", "unknown"),
            )

    # ========== Fase 3B: Nuevos métodos de integración ==========

    def detect_embedded_status(
        self, font_name: str, page_num: int = 0
    ) -> FontEmbeddingStatus:
        """
        Detecta el estado de embedding de una fuente.
        
        Usa EmbeddedFontExtractor para determinar si la fuente está:
        - Completamente embebida
        - Embebida como subset
        - Es externa (no embebida)
        
        Args:
            font_name: Nombre de la fuente
            page_num: Número de página
            
        Returns:
            FontEmbeddingStatus indicando el estado
        """
        if not TEXT_ENGINE_AVAILABLE or not self._font_extractor:
            return FontEmbeddingStatus.UNKNOWN
        
        try:
            # Usar cache si disponible
            cache_key = f"embed_{font_name}_{page_num}"
            if cache_key in self._font_info_cache:
                return self._font_info_cache[cache_key]
            
            # Obtener info de fuente
            font_info = self._font_extractor.get_font_info(font_name, page_num)
            
            if font_info is None:
                status = FontEmbeddingStatus.EXTERNAL
            elif font_info.embedding_status == EmbeddingStatus.SUBSET:
                status = FontEmbeddingStatus.SUBSET
            elif font_info.embedding_status == EmbeddingStatus.EMBEDDED:
                status = FontEmbeddingStatus.EMBEDDED
            elif font_info.embedding_status == EmbeddingStatus.NOT_EMBEDDED:
                status = FontEmbeddingStatus.EXTERNAL
            else:
                status = FontEmbeddingStatus.UNKNOWN
            
            self._font_info_cache[cache_key] = status
            return status
            
        except Exception as e:
            self.logger.debug(f"Error detecting embedded status: {e}")
            return FontEmbeddingStatus.UNKNOWN

    def get_precise_metrics(
        self, font_name: str, page_num: int = 0
    ) -> Optional[PreciseMetrics]:
        """
        Obtiene métricas precisas de una fuente desde el PDF.
        
        Extrae métricas del diccionario de fuente del PDF,
        que son más precisas que las aproximaciones de Qt.
        
        Args:
            font_name: Nombre de la fuente
            page_num: Número de página
            
        Returns:
            PreciseMetrics con las métricas extraídas, o None si no disponible
        """
        if not TEXT_ENGINE_AVAILABLE or not self._font_extractor:
            return None
        
        try:
            # Usar cache si disponible
            cache_key = f"metrics_{font_name}_{page_num}"
            if cache_key in self._font_info_cache:
                return self._font_info_cache[cache_key]
            
            # Obtener info de fuente
            font_info = self._font_extractor.get_font_info(font_name, page_num)
            
            if font_info is None or font_info.metrics is None:
                return None
            
            metrics = font_info.metrics
            
            precise = PreciseMetrics(
                ascender=metrics.ascender,
                descender=metrics.descender,
                line_height=metrics.ascender - metrics.descender,
                avg_char_width=metrics.avg_width,
                cap_height=metrics.cap_height,
                x_height=metrics.x_height,
                stem_v=metrics.stem_v,
                stem_h=metrics.stem_h,
                italic_angle=metrics.italic_angle,
            )
            
            self._font_info_cache[cache_key] = precise
            return precise
            
        except Exception as e:
            self.logger.debug(f"Error getting precise metrics: {e}")
            return None

    def _get_glyph_widths_dict(
        self, font_name: str, page_num: int = 0
    ) -> Dict[str, float]:
        """
        Obtiene diccionario de anchos de glifos de una fuente.
        
        Args:
            font_name: Nombre de la fuente
            page_num: Número de página
            
        Returns:
            Dict mapping char -> width (en unidades de fuente)
        """
        if not TEXT_ENGINE_AVAILABLE or not self._font_extractor:
            return {}
        
        try:
            # Usar cache si disponible
            cache_key = f"widths_{font_name}_{page_num}"
            if cache_key in self._font_info_cache:
                return self._font_info_cache[cache_key]
            
            # Obtener anchos
            glyph_widths = self._font_extractor.get_glyph_widths(font_name, page_num)
            
            # Convertir a dict de strings si necesario
            result: Dict[str, float] = {}
            for char_code, width in glyph_widths.items():
                if isinstance(char_code, int):
                    try:
                        result[chr(char_code)] = width
                    except ValueError:
                        pass
                else:
                    result[str(char_code)] = width
            
            self._font_info_cache[cache_key] = result
            return result
            
        except Exception as e:
            self.logger.debug(f"Error getting glyph widths: {e}")
            return {}

    def can_reuse_font(self, font_name: str, page_num: int = 0) -> bool:
        """
        Verifica si una fuente puede ser reutilizada para insertar texto.
        
        Una fuente puede ser reutilizada si:
        - Está completamente embebida (no subset)
        - Tiene todos los glifos necesarios
        
        Args:
            font_name: Nombre de la fuente
            page_num: Número de página
            
        Returns:
            True si la fuente puede ser reutilizada
        """
        if not TEXT_ENGINE_AVAILABLE or not self._font_extractor:
            return False
        
        try:
            return self._font_extractor.can_reuse_font(font_name, page_num)
        except Exception:
            return False

    def get_font_info_for_text(
        self, text: str, font_name: str, page_num: int = 0
    ) -> Optional[Any]:
        """
        Obtiene información completa de fuente para un texto específico.
        
        Args:
            text: Texto a renderizar
            font_name: Nombre de la fuente
            page_num: Número de página
            
        Returns:
            FontInfo del text_engine o None
        """
        if not TEXT_ENGINE_AVAILABLE or not self._font_extractor:
            return None
        
        try:
            return self._font_extractor.get_font_info(font_name, page_num)
        except Exception:
            return None

    # ========== Fin métodos Fase 3B ==========

    def smart_fallback(self, font_name: str) -> str:
        """
        Mapea nombre de fuente a equivalente estándar con heurísticas.

        Estrategia:
        1. Búsqueda exacta en tabla
        2. Búsqueda parcial (prefijos)
        3. Análisis de "serif" vs "sans-serif"
        4. Default seguro: "helv" (Helvetica)

        Args:
            font_name: Nombre de fuente del PDF (ej: "MyriadPro")

        Returns:
            Nombre de fuente estándar (ej: "helv", "times", "cour")
        """
        if not font_name:
            return "helv"

        # 1. Búsqueda exacta
        if font_name in self.FONT_MAPPING:
            return self.FONT_MAPPING[font_name]

        # 2. Búsqueda parcial (prefijos)
        for key, value in self.FONT_MAPPING.items():
            if font_name.lower().startswith(key.lower()):
                self.logger.debug(f"Font match (prefix): {font_name} → {value}")
                return value

        # 3. Heurística: contiene "serif"?
        lower_name = font_name.lower()
        if "serif" in lower_name:
            self.logger.debug(f"Font heuristic (serif detected): {font_name} → times")
            return "times"

        # 4. Default seguro
        self.logger.debug(f"Font fallback (unknown): {font_name} → helv (default)")
        return "helv"

    def detect_possible_bold(
        self, span: dict, use_metrics: bool = True
    ) -> Optional[bool]:
        """
        Intenta detectar si fuente es bold usando heurísticas y métricas.

        Fase 3B: Ahora puede usar métricas precisas del PDF.
        
        IMPORTANTE: PyMuPDF NO expone directamente el weight de la fuente.
        Usamos múltiples estrategias en orden de confiabilidad:
        1. Métricas precisas (stem_v > 100 indica bold) - MÁS CONFIABLE
        2. Nombre contiene "Bold" / "B" / "Heavy"
        3. Flags PDF si están disponibles
        
        Args:
            span: Dict del span con información de fuente
            use_metrics: Si True, intenta usar métricas precisas (default True)

        Returns:
            True (probablemente bold)
            False (probablemente no bold)
            None (incierto, preguntar al usuario)
        """
        font_name = span.get("font", "")
        
        # Fase 3B: Usar métricas precisas si disponibles (más confiable)
        if use_metrics and TEXT_ENGINE_AVAILABLE and self._font_extractor:
            try:
                precise = self.get_precise_metrics(font_name)
                if precise and precise.is_bold_by_stem is not None:
                    self.logger.debug(
                        f"Bold detected by stem_v={precise.stem_v}: {font_name}"
                    )
                    return precise.is_bold_by_stem
            except Exception:
                pass  # Fallback a heurísticas

        # Heurística 1: Nombre contiene indicadores de bold
        bold_indicators = ["bold", "-b", "_b", "heavy", "black", "extra", "demi", "semi"]
        if any(ind in font_name.lower() for ind in bold_indicators):
            self.logger.debug(f"Bold detected by name: {font_name}")
            return True

        # Heurística 2: Comparar widths (limitado sin acceso a métricas exactas)
        # En PDFs con estilos embebidos, font_name puede incluir -Bold
        if "-Bold" in font_name or "-B" in font_name:
            self.logger.debug(f"Bold detected by name suffix: {font_name}")
            return True

        # Heurística 3: Flags PDF (si están disponibles)
        flags = span.get("flags", 0)
        # Flag 0x40 puede indicar bold en algunos PDFs
        if flags & 0x40:
            self.logger.debug(f"Bold detected by flags: {flags}")
            return True
        
        # Heurística 4: Verificar si font_name limpio tiene indicadores
        if TEXT_ENGINE_AVAILABLE:
            try:
                clean_name = get_clean_font_name(font_name)
                if any(ind in clean_name.lower() for ind in bold_indicators):
                    self.logger.debug(f"Bold detected by clean name: {clean_name}")
                    return True
            except Exception:
                pass

        # No se pudo determinar → retornar None (incierto)
        return None

    def get_bounding_rect(
        self, text: str, descriptor: FontDescriptor
    ) -> Tuple[float, float]:
        """
        Calcula tamaño real de texto usando QFontMetrics.

        Usa QFont + QFontMetrics para obtener ancho × alto exactos
        que el texto ocupará en la UI.

        Args:
            text: Texto a medir (ej: "Hola mundo")
            descriptor: FontDescriptor con información de fuente

        Returns:
            (ancho, alto) en píxeles
        """
        try:
            # Verificar si hay QApplication activa (necesaria para QFontMetrics)
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                # Sin aplicación Qt, usar estimación
                estimated_width = len(text) * descriptor.size * 0.5
                estimated_height = descriptor.size * 1.2
                return (float(estimated_width), float(estimated_height))
            
            # Crear QFont (buscar en cache si existe)
            cache_key = f"{descriptor.name}_{int(descriptor.size)}"
            if cache_key not in self._font_cache:
                try:
                    qfont = QFont(descriptor.name, int(descriptor.size))
                    self._font_cache[cache_key] = qfont
                except Exception:
                    # Sin aplicación Qt, saltamos cache
                    qfont = QFont(descriptor.name, int(descriptor.size))
            else:
                qfont = self._font_cache[cache_key]

            # Calcular métricas
            try:
                metrics = QFontMetrics(qfont)
                width = metrics.horizontalAdvance(text)
                height = metrics.height()
            except Exception:
                # Fallback si QFontMetrics falla (sin app Qt)
                estimated_width = len(text) * descriptor.size * 0.5
                estimated_height = descriptor.size
                return (float(estimated_width), float(estimated_height))

            return (float(width), float(height))

        except Exception as e:
            self.logger.error(f"Error calculating bounding rect: {e}")
            # Fallback: estimar ancho basado en caracteres
            estimated_width = len(text) * descriptor.size * 0.5
            estimated_height = descriptor.size * 1.2
            return (estimated_width, estimated_height)

    def handle_bold(
        self,
        text: str,
        descriptor: FontDescriptor,
        should_bold: bool,
    ) -> Tuple[str, str]:
        """
        Maneja aplicación de negritas con fallback inteligente.

        Estrategia:
        1. Si should_bold=True:
           - Intentar usar variante Bold exacta
           - Si no está disponible: usar aproximación visual (subrayado + color oscuro)
           - Si ambas fallan: retornar warning

        Args:
            text: Texto a aplicar estilo (ej: "importante")
            descriptor: FontDescriptor
            should_bold: ¿Aplicar negrita?

        Returns:
            (texto_renderizado, estrategia_usada)
            estrategia_usada: "exact_bold" | "approximate_bold" | "warning"
        """
        if not should_bold:
            return (text, BoldStrategy.EXACT_BOLD.value)

        try:
            # Estrategia 1: Intentar usar variante Bold
            # Crear QFont con bold
            qfont = QFont(descriptor.name, int(descriptor.size), QFont.Bold)

            if qfont.bold():
                self.logger.debug(f"Bold aplicado exitosamente: {descriptor.name}")
                return (text, BoldStrategy.EXACT_BOLD.value)

        except Exception as e:
            self.logger.warning(f"Could not apply exact bold: {e}")

        # Estrategia 2: Fallback visual (subrayado + color más oscuro)
        self.logger.warning(
            "Bold fallback (approximate): usando subrayado en lugar de negrita"
        )
        return (text, BoldStrategy.APPROXIMATE_BOLD.value)

    def validate_text_fits(
        self, text: str, descriptor: FontDescriptor, max_width: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida si el texto cabe en el área disponible.

        Args:
            text: Texto a validar
            descriptor: FontDescriptor
            max_width: Ancho máximo disponible (píxeles)

        Returns:
            (cabe, mensaje_si_no_cabe)
        """
        actual_width, _ = self.get_bounding_rect(text, descriptor)

        if actual_width <= max_width:
            return (True, None)

        percentage = int((actual_width / max_width) * 100)
        message = f"Texto no cabe: ocupa {percentage}% del área disponible"
        return (False, message)

    def reduce_tracking(
        self, text: str, descriptor: FontDescriptor, percent_reduction: float
    ) -> str:
        """
        Reduce espaciado entre letras (tracking).

        Args:
            text: Texto original
            descriptor: FontDescriptor
            percent_reduction: Porcentaje de reducción (ej: 15 para -15%)

        Returns:
            Texto con espaciado reducido (simulado)
        """
        # Nota: PyMuPDF tiene soporte limitado para tracking
        # Esta es una versión simulada para demostración
        if percent_reduction <= 0:
            return text

        self.logger.info(f"Reducing tracking by {percent_reduction}%")

        return text  # En producción, aplicar en PDF real

    def _color_to_hex(self, color_int: int) -> str:
        """Convierte color int de PyMuPDF a hex string."""
        try:
            if isinstance(color_int, int):
                # Formato: 0xBBGGRR (BGR inverso)
                r = (color_int) & 0xFF
                g = (color_int >> 8) & 0xFF
                b = (color_int >> 16) & 0xFF
                return f"#{r:02x}{g:02x}{b:02x}"
            return "#000000"
        except Exception:
            return "#000000"

    def clear_cache(self):
        """Limpiar cache de fuentes (liberar memoria)."""
        self._font_cache.clear()
        self.logger.debug("Font cache cleared")


# Instancia global (singleton)
_font_manager = None


def get_font_manager() -> FontManager:
    """Obtener instancia global de FontManager."""
    global _font_manager
    if _font_manager is None:
        _font_manager = FontManager()
    return _font_manager

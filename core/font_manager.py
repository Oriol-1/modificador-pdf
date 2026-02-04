"""
FontManager - Gestión centralizada de fuentes para PDF Editor Pro

Responsable de:
1. Detectar fuentes en PDFs (nombre, tamaño, color)
2. Mapear fuentes custom a equivalentes estándar (fallback)
3. Detectar negritas (con heurísticas)
4. Calcular tamaño real de texto usando QFontMetrics
5. Manejar estrategias de fallback para bold/italic

Limitación técnica importante:
- PyMuPDF NO puede detectar automáticamente si una fuente es bold
- Usamos heurísticas: nombre contiene "Bold", comparar widths, flags PDF
- Resultado puede ser True (probablemente bold) / False (no bold) / None (incierto)
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from enum import Enum
import logging

from PyQt5.QtGui import QFont, QFontMetrics

logger = logging.getLogger(__name__)


class BoldStrategy(Enum):
    """Estrategias para aplicar negritas."""
    EXACT_BOLD = "exact_bold"           # Usar variante Bold exacta
    APPROXIMATE_BOLD = "approximate"     # Fallback: subrayado + oscuro
    WARNING_FALLBACK = "warning"         # Advertencia, no se aplicó


@dataclass
class FontDescriptor:
    """
    Descriptor de fuente extraído de un span de PDF.
    
    Attributes:
        name: Nombre de fuente detectado (ej: "Arial", "MyriadPro")
        size: Tamaño en puntos (ej: 12)
        color: Color como hex (ej: "#000000")
        flags: Flags PDF (indica posibles estilos)
        was_fallback: True si se usó fallback de fuente
        fallback_from: Fuente original si fue reemplazada
        possible_bold: True/False/None (detección heurística)
    """
    name: str
    size: float
    color: str = "#000000"
    flags: int = 0
    was_fallback: bool = False
    fallback_from: Optional[str] = None
    possible_bold: Optional[bool] = None

    def __repr__(self) -> str:
        fallback_str = f" (fallback from {self.fallback_from})" if self.was_fallback else ""
        return f"FontDescriptor({self.name} {self.size}pt{fallback_str})"


class FontManager:
    """Gestión centralizada de fuentes con fallbacks inteligentes."""

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

    def __init__(self):
        """Inicializar FontManager."""
        self.logger = logger
        self._font_cache = {}  # Cache de QFont para evitar recrear

    def detect_font(self, span: dict) -> FontDescriptor:
        """
        Extrae información de fuente de un span de PyMuPDF.

        Args:
            span: Dict del texto extraído con get_text("dict")
                  Contiene: "font", "size", "color", "flags", etc.

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

            # Detectar si es estándar o custom
            actual_font = self.smart_fallback(font_name)
            was_fallback = actual_font != font_name

            # Detectar posible bold
            possible_bold = self.detect_possible_bold(span)

            descriptor = FontDescriptor(
                name=actual_font,
                size=size,
                color=color_hex,
                flags=flags,
                was_fallback=was_fallback,
                fallback_from=font_name if was_fallback else None,
                possible_bold=possible_bold,
            )

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

    def detect_possible_bold(self, span: dict) -> Optional[bool]:
        """
        Intenta detectar si fuente es bold usando heurísticas.

        IMPORTANTE: PyMuPDF NO expone directamente el weight de la fuente.
        Usamos heurísticas basadas en:
        1. Nombre contiene "Bold" / "B" / "Heavy"
        2. Comparar ancho esperado vs. actual (widths)
        3. Flags PDF si están disponibles

        Returns:
            True (probablemente bold)
            False (probablemente no bold)
            None (incierto, preguntar al usuario)
        """
        font_name = span.get("font", "")

        # Heurística 1: Nombre contiene indicadores de bold
        bold_indicators = ["bold", "-b", "_b", "heavy", "black", "extra"]
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

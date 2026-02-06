"""
FitValidator - Validación "cabe/no cabe" con métricas reales.

PHASE3-3C07: Implementación de validación de ajuste de texto usando
métricas reales del PDF (Tc, Tw, font metrics, etc.).

Este módulo proporciona:
- FitValidationStatus: Estado de validación (FITS, TIGHT, OVERFLOW)
- FitMetrics: Métricas detalladas de ajuste
- FitValidationResult: Resultado completo de validación
- FitSuggestion: Sugerencia de ajuste
- FitValidator: Validador principal con integración de métricas PDF
- Funciones factory para validación rápida
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, Any, Tuple

from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QProgressBar
)


# ================== Enums ==================


class FitValidationStatus(Enum):
    """Estado de validación del ajuste de texto."""
    
    FITS = auto()           # El texto cabe perfectamente
    TIGHT = auto()          # El texto cabe pero está ajustado (>90%)
    OVERFLOW = auto()       # El texto no cabe
    UNKNOWN = auto()        # Estado indeterminado
    
    def __str__(self) -> str:
        return self.name.lower()
    
    @property
    def is_acceptable(self) -> bool:
        """True si el texto es aceptable (cabe o está ajustado)."""
        return self in (FitValidationStatus.FITS, FitValidationStatus.TIGHT)
    
    @classmethod
    def from_percentage(cls, percentage: float, tight_threshold: float = 90.0) -> "FitValidationStatus":
        """
        Determina el estado basándose en el porcentaje de uso.
        
        Args:
            percentage: Porcentaje de uso del espacio disponible
            tight_threshold: Umbral para considerar "TIGHT" (default 90%)
        """
        if percentage <= tight_threshold:
            return cls.FITS
        elif percentage <= 100.0:
            return cls.TIGHT
        else:
            return cls.OVERFLOW


class SuggestionType(Enum):
    """Tipo de sugerencia de ajuste."""
    
    REDUCE_TRACKING = auto()     # Reducir espaciado entre caracteres
    REDUCE_SIZE = auto()         # Reducir tamaño de fuente
    SCALE_HORIZONTAL = auto()    # Escalar horizontalmente
    TRUNCATE = auto()            # Truncar texto
    USE_ABBREVIATION = auto()    # Usar abreviación
    SPLIT_LINE = auto()          # Dividir en líneas
    CHANGE_FONT = auto()         # Cambiar a fuente más condensada
    
    def __str__(self) -> str:
        labels = {
            SuggestionType.REDUCE_TRACKING: "Reducir espaciado",
            SuggestionType.REDUCE_SIZE: "Reducir tamaño",
            SuggestionType.SCALE_HORIZONTAL: "Escalar ancho",
            SuggestionType.TRUNCATE: "Truncar texto",
            SuggestionType.USE_ABBREVIATION: "Usar abreviación",
            SuggestionType.SPLIT_LINE: "Dividir línea",
            SuggestionType.CHANGE_FONT: "Fuente condensada",
        }
        return labels.get(self, self.name)


# ================== Dataclasses ==================


@dataclass
class FitMetrics:
    """
    Métricas detalladas para validación de ajuste.
    
    Agrupa todas las métricas relevantes del texto original y
    el texto editado para comparación.
    """
    # Dimensiones originales
    original_width: float = 0.0
    original_height: float = 0.0
    original_bbox: Optional[Tuple[float, float, float, float]] = None
    
    # Dimensiones del texto editado
    current_width: float = 0.0
    current_height: float = 0.0
    
    # Espacio disponible
    available_width: float = 0.0
    available_height: float = 0.0
    
    # Propiedades tipográficas originales
    original_font_name: str = ""
    original_font_size: float = 0.0
    original_char_spacing: float = 0.0  # Tc
    original_word_spacing: float = 0.0  # Tw
    original_scale_x: float = 1.0       # Escala horizontal
    
    # Propiedades tipográficas actuales
    current_font_name: str = ""
    current_font_size: float = 0.0
    current_char_spacing: float = 0.0
    current_word_spacing: float = 0.0
    current_scale_x: float = 1.0
    
    @property
    def width_difference(self) -> float:
        """Diferencia de ancho (positivo = más ancho)."""
        return self.current_width - self.available_width
    
    @property
    def width_ratio(self) -> float:
        """Ratio de uso de ancho (1.0 = exacto, >1.0 = overflow)."""
        if self.available_width <= 0:
            return float('inf')
        return self.current_width / self.available_width
    
    @property
    def usage_percentage(self) -> float:
        """Porcentaje de uso del espacio disponible."""
        return self.width_ratio * 100.0
    
    @property
    def overflow_amount(self) -> float:
        """Cantidad de overflow en puntos (0 si cabe)."""
        return max(0.0, self.width_difference)
    
    @property
    def overflow_percentage(self) -> float:
        """Porcentaje de overflow (0 si cabe)."""
        if self.available_width <= 0:
            return 0.0
        return max(0.0, (self.current_width - self.available_width) / self.available_width * 100.0)
    
    @property
    def remaining_space(self) -> float:
        """Espacio restante en puntos (negativo si overflow)."""
        return self.available_width - self.current_width
    
    @property
    def char_count_diff(self) -> int:
        """Diferencia en conteo de caracteres."""
        # Este valor se establece externamente si es necesario
        return getattr(self, '_char_count_diff', 0)
    
    @classmethod
    def from_span_data(
        cls,
        span_data: Dict[str, Any],
        new_text: str,
        new_width: float
    ) -> "FitMetrics":
        """
        Crea FitMetrics desde datos de span y texto nuevo.
        
        Args:
            span_data: Diccionario con datos del span original
            new_text: Texto nuevo a validar
            new_width: Ancho calculado del texto nuevo
        """
        bbox = span_data.get('bbox', (0, 0, 0, 0))
        original_width = bbox[2] - bbox[0] if len(bbox) >= 4 else 0.0
        original_height = bbox[3] - bbox[1] if len(bbox) >= 4 else 0.0
        
        return cls(
            original_width=original_width,
            original_height=original_height,
            original_bbox=tuple(bbox) if bbox else None,
            current_width=new_width,
            current_height=original_height,  # Asumimos altura constante
            available_width=original_width,
            available_height=original_height,
            original_font_name=span_data.get('font', ''),
            original_font_size=span_data.get('size', 12.0),
            original_char_spacing=span_data.get('char_spacing', 0.0),
            original_word_spacing=span_data.get('word_spacing', 0.0),
            original_scale_x=span_data.get('scale_x', 1.0),
            current_font_name=span_data.get('font', ''),
            current_font_size=span_data.get('size', 12.0),
            current_char_spacing=span_data.get('char_spacing', 0.0),
            current_word_spacing=span_data.get('word_spacing', 0.0),
            current_scale_x=span_data.get('scale_x', 1.0),
        )


@dataclass
class FitSuggestion:
    """
    Sugerencia de ajuste para hacer que el texto quepa.
    
    Cada sugerencia incluye el tipo, los parámetros ajustados
    y una estimación del resultado.
    """
    suggestion_type: SuggestionType = SuggestionType.TRUNCATE
    description: str = ""
    
    # Parámetros del ajuste propuesto
    adjusted_text: Optional[str] = None
    adjusted_char_spacing: Optional[float] = None
    adjusted_word_spacing: Optional[float] = None
    adjusted_font_size: Optional[float] = None
    adjusted_scale_x: Optional[float] = None
    
    # Estimaciones del resultado
    estimated_width: float = 0.0
    estimated_fit_percentage: float = 0.0
    
    # Calidad/preferencia de la sugerencia (mayor = mejor)
    priority: int = 0
    preserves_readability: bool = True
    
    @property
    def will_fit(self) -> bool:
        """True si esta sugerencia resultaría en texto que cabe."""
        return self.estimated_fit_percentage <= 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            'type': self.suggestion_type.name,
            'description': self.description,
            'adjusted_text': self.adjusted_text,
            'adjusted_char_spacing': self.adjusted_char_spacing,
            'adjusted_word_spacing': self.adjusted_word_spacing,
            'adjusted_font_size': self.adjusted_font_size,
            'adjusted_scale_x': self.adjusted_scale_x,
            'estimated_width': self.estimated_width,
            'estimated_fit_percentage': self.estimated_fit_percentage,
            'priority': self.priority,
            'preserves_readability': self.preserves_readability,
        }


@dataclass
class FitValidationResult:
    """
    Resultado completo de validación de ajuste.
    
    Incluye el estado, métricas detalladas, y sugerencias
    de ajuste si el texto no cabe.
    """
    status: FitValidationStatus = FitValidationStatus.UNKNOWN
    metrics: FitMetrics = field(default_factory=FitMetrics)
    
    # Texto original y editado
    original_text: str = ""
    edited_text: str = ""
    
    # Sugerencias de ajuste (solo si overflow)
    suggestions: list = field(default_factory=list)
    
    # Mensaje descriptivo
    message: str = ""
    
    @property
    def fits(self) -> bool:
        """True si el texto cabe (status aceptable)."""
        return self.status.is_acceptable
    
    @property
    def percentage(self) -> float:
        """Porcentaje de uso del espacio disponible."""
        return self.metrics.usage_percentage
    
    @property
    def overflow_amount(self) -> float:
        """Cantidad de overflow en puntos."""
        return self.metrics.overflow_amount
    
    @property
    def best_suggestion(self) -> Optional[FitSuggestion]:
        """Mejor sugerencia de ajuste (mayor prioridad)."""
        if not self.suggestions:
            return None
        return max(self.suggestions, key=lambda s: s.priority)
    
    def get_suggestions_by_type(self, suggestion_type: SuggestionType) -> list:
        """Obtiene sugerencias filtradas por tipo."""
        return [s for s in self.suggestions if s.suggestion_type == suggestion_type]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            'status': self.status.name,
            'fits': self.fits,
            'percentage': self.percentage,
            'overflow_amount': self.overflow_amount,
            'original_text': self.original_text,
            'edited_text': self.edited_text,
            'message': self.message,
            'metrics': {
                'available_width': self.metrics.available_width,
                'current_width': self.metrics.current_width,
                'remaining_space': self.metrics.remaining_space,
            },
            'suggestions': [s.to_dict() for s in self.suggestions],
        }


@dataclass
class FitValidatorConfig:
    """Configuración del validador de ajuste."""
    
    # Umbral para considerar "TIGHT" (porcentaje)
    tight_threshold: float = 90.0
    
    # Límites para sugerencias
    min_tracking: float = -2.0          # Mínimo espaciado entre caracteres
    max_tracking: float = 5.0           # Máximo espaciado entre caracteres
    min_size_factor: float = 0.7        # Mínimo factor de tamaño (70%)
    min_scale_x: float = 0.75           # Mínima escala horizontal (75%)
    
    # Preferencias de sugerencias
    prefer_tracking_over_size: bool = True
    allow_truncation: bool = True
    max_truncation_percent: float = 25.0  # Máximo 25% del texto truncado
    
    # Ajuste fino
    tracking_step: float = 0.1          # Paso de ajuste de tracking
    size_step: float = 0.5              # Paso de ajuste de tamaño
    scale_step: float = 0.01            # Paso de ajuste de escala


# ================== FitValidator ==================


class FitValidator(QObject):
    """
    Validador de ajuste de texto con métricas reales.
    
    Valida si un texto editado cabe en el espacio disponible
    usando métricas reales del PDF (Tc, Tw, font metrics).
    
    Signals:
        validationComplete: Emitido cuando se completa la validación
        fitStatusChanged: Emitido cuando cambia el estado de ajuste
    """
    
    validationComplete = pyqtSignal(FitValidationResult)
    fitStatusChanged = pyqtSignal(FitValidationStatus)
    
    def __init__(
        self,
        config: Optional[FitValidatorConfig] = None,
        parent: Optional[QObject] = None
    ):
        """
        Inicializa el validador.
        
        Args:
            config: Configuración del validador
            parent: Objeto padre para Qt
        """
        super().__init__(parent)
        self._config = config or FitValidatorConfig()
        self._last_result: Optional[FitValidationResult] = None
        
        # Cache de métricas de fuentes
        self._font_cache: Dict[str, QFontMetrics] = {}
    
    @property
    def config(self) -> FitValidatorConfig:
        """Configuración actual."""
        return self._config
    
    @config.setter
    def config(self, value: FitValidatorConfig) -> None:
        """Establece nueva configuración."""
        self._config = value
    
    @property
    def last_result(self) -> Optional[FitValidationResult]:
        """Último resultado de validación."""
        return self._last_result
    
    def validate(
        self,
        text: str,
        font_name: str,
        font_size: float,
        available_width: float,
        char_spacing: float = 0.0,
        word_spacing: float = 0.0,
        scale_x: float = 1.0,
        original_text: str = "",
        span_data: Optional[Dict[str, Any]] = None
    ) -> FitValidationResult:
        """
        Valida si el texto cabe en el ancho disponible.
        
        Args:
            text: Texto a validar
            font_name: Nombre de la fuente
            font_size: Tamaño de fuente en puntos
            available_width: Ancho disponible en puntos
            char_spacing: Espaciado entre caracteres (Tc)
            word_spacing: Espaciado entre palabras (Tw)
            scale_x: Escala horizontal
            original_text: Texto original (para comparación)
            span_data: Datos adicionales del span
            
        Returns:
            FitValidationResult con estado, métricas y sugerencias
        """
        # Calcular ancho del texto
        text_width = self._calculate_text_width(
            text, font_name, font_size, char_spacing, scale_x
        )
        
        # Crear métricas
        if span_data:
            metrics = FitMetrics.from_span_data(span_data, text, text_width)
        else:
            metrics = FitMetrics(
                original_width=available_width,
                available_width=available_width,
                current_width=text_width,
                original_font_name=font_name,
                original_font_size=font_size,
                original_char_spacing=char_spacing,
                original_word_spacing=word_spacing,
                original_scale_x=scale_x,
                current_font_name=font_name,
                current_font_size=font_size,
                current_char_spacing=char_spacing,
                current_word_spacing=word_spacing,
                current_scale_x=scale_x,
            )
        
        # Determinar estado
        percentage = metrics.usage_percentage
        status = FitValidationStatus.from_percentage(
            percentage, self._config.tight_threshold
        )
        
        # Crear resultado
        result = FitValidationResult(
            status=status,
            metrics=metrics,
            original_text=original_text or text,
            edited_text=text,
            message=self._generate_message(status, metrics)
        )
        
        # Generar sugerencias si hay overflow
        if status == FitValidationStatus.OVERFLOW:
            result.suggestions = self._generate_suggestions(
                text, font_name, font_size, available_width,
                char_spacing, word_spacing, scale_x, metrics
            )
        
        # Guardar y emitir
        self._last_result = result
        self.validationComplete.emit(result)
        self.fitStatusChanged.emit(status)
        
        return result
    
    def validate_span(
        self,
        span_data: Dict[str, Any],
        new_text: str
    ) -> FitValidationResult:
        """
        Valida texto nuevo contra datos de span original.
        
        Args:
            span_data: Diccionario con datos del span
            new_text: Texto nuevo a validar
            
        Returns:
            FitValidationResult
        """
        bbox = span_data.get('bbox', (0, 0, 0, 0))
        available_width = bbox[2] - bbox[0] if len(bbox) >= 4 else 100.0
        
        return self.validate(
            text=new_text,
            font_name=span_data.get('font', 'Helvetica'),
            font_size=span_data.get('size', 12.0),
            available_width=available_width,
            char_spacing=span_data.get('char_spacing', 0.0),
            word_spacing=span_data.get('word_spacing', 0.0),
            scale_x=span_data.get('scale_x', 1.0),
            original_text=span_data.get('text', ''),
            span_data=span_data
        )
    
    def quick_check(
        self,
        text: str,
        font_name: str,
        font_size: float,
        available_width: float
    ) -> bool:
        """
        Verificación rápida de si el texto cabe.
        
        Args:
            text: Texto a verificar
            font_name: Nombre de la fuente
            font_size: Tamaño de fuente
            available_width: Ancho disponible
            
        Returns:
            True si el texto cabe
        """
        width = self._calculate_text_width(text, font_name, font_size)
        return width <= available_width
    
    def _calculate_text_width(
        self,
        text: str,
        font_name: str,
        font_size: float,
        char_spacing: float = 0.0,
        scale_x: float = 1.0
    ) -> float:
        """
        Calcula el ancho del texto.
        
        Args:
            text: Texto a medir
            font_name: Nombre de la fuente
            font_size: Tamaño en puntos
            char_spacing: Espaciado adicional entre caracteres
            scale_x: Escala horizontal
            
        Returns:
            Ancho en puntos
        """
        if not text:
            return 0.0
        
        # Obtener o crear métricas de fuente
        cache_key = f"{font_name}_{font_size}"
        if cache_key not in self._font_cache:
            font = QFont(font_name, int(font_size))
            font.setPointSizeF(font_size)
            self._font_cache[cache_key] = QFontMetrics(font)
        
        fm = self._font_cache[cache_key]
        
        # Ancho base
        base_width = fm.horizontalAdvance(text)
        
        # Añadir char_spacing
        if char_spacing != 0.0 and len(text) > 1:
            base_width += char_spacing * (len(text) - 1)
        
        # Aplicar escala
        return base_width * scale_x
    
    def _generate_message(
        self,
        status: FitValidationStatus,
        metrics: FitMetrics
    ) -> str:
        """Genera mensaje descriptivo del estado."""
        if status == FitValidationStatus.FITS:
            return f"El texto cabe ({metrics.usage_percentage:.1f}% usado)"
        elif status == FitValidationStatus.TIGHT:
            return f"El texto cabe ajustado ({metrics.usage_percentage:.1f}% usado)"
        elif status == FitValidationStatus.OVERFLOW:
            return (
                f"El texto excede el límite en {metrics.overflow_amount:.1f}pt "
                f"({metrics.overflow_percentage:.1f}% overflow)"
            )
        return "Estado desconocido"
    
    def _generate_suggestions(
        self,
        text: str,
        font_name: str,
        font_size: float,
        available_width: float,
        char_spacing: float,
        word_spacing: float,
        scale_x: float,
        metrics: FitMetrics
    ) -> list:
        """
        Genera sugerencias de ajuste para texto que no cabe.
        
        Returns:
            Lista de FitSuggestion ordenadas por prioridad
        """
        suggestions: list = []
        
        # 1. Reducir tracking (espaciado entre caracteres)
        if self._config.prefer_tracking_over_size:
            tracking_suggestion = self._suggest_tracking_reduction(
                text, font_name, font_size, available_width, char_spacing, scale_x
            )
            if tracking_suggestion:
                suggestions.append(tracking_suggestion)
        
        # 2. Escalar horizontalmente
        scale_suggestion = self._suggest_horizontal_scale(
            text, font_name, font_size, available_width, char_spacing, scale_x
        )
        if scale_suggestion:
            suggestions.append(scale_suggestion)
        
        # 3. Reducir tamaño de fuente
        size_suggestion = self._suggest_size_reduction(
            text, font_name, font_size, available_width, char_spacing, scale_x
        )
        if size_suggestion:
            suggestions.append(size_suggestion)
        
        # 4. Truncar texto
        if self._config.allow_truncation:
            truncate_suggestion = self._suggest_truncation(
                text, font_name, font_size, available_width, char_spacing, scale_x
            )
            if truncate_suggestion:
                suggestions.append(truncate_suggestion)
        
        # Ordenar por prioridad
        suggestions.sort(key=lambda s: s.priority, reverse=True)
        
        return suggestions
    
    def _suggest_tracking_reduction(
        self,
        text: str,
        font_name: str,
        font_size: float,
        available_width: float,
        current_spacing: float,
        scale_x: float
    ) -> Optional[FitSuggestion]:
        """Sugiere reducción de tracking."""
        if len(text) <= 1:
            return None
        
        # Buscar el tracking que hace que quepa
        test_spacing = current_spacing
        while test_spacing >= self._config.min_tracking:
            width = self._calculate_text_width(
                text, font_name, font_size, test_spacing, scale_x
            )
            if width <= available_width:
                percentage = (width / available_width) * 100.0
                return FitSuggestion(
                    suggestion_type=SuggestionType.REDUCE_TRACKING,
                    description=f"Reducir espaciado de {current_spacing:.1f} a {test_spacing:.1f}pt",
                    adjusted_char_spacing=test_spacing,
                    estimated_width=width,
                    estimated_fit_percentage=percentage,
                    priority=80 if test_spacing > self._config.min_tracking / 2 else 60,
                    preserves_readability=test_spacing > self._config.min_tracking / 2
                )
            test_spacing -= self._config.tracking_step
        
        return None
    
    def _suggest_horizontal_scale(
        self,
        text: str,
        font_name: str,
        font_size: float,
        available_width: float,
        char_spacing: float,
        current_scale: float
    ) -> Optional[FitSuggestion]:
        """Sugiere escalado horizontal."""
        # Calcular escala necesaria
        base_width = self._calculate_text_width(
            text, font_name, font_size, char_spacing, 1.0
        )
        
        if base_width <= 0 or available_width <= 0:
            return None
        
        needed_scale = available_width / base_width
        
        if needed_scale < self._config.min_scale_x:
            # Usar escala mínima
            needed_scale = self._config.min_scale_x
            width = base_width * needed_scale
            percentage = (width / available_width) * 100.0
            will_fit = percentage <= 100.0
        else:
            width = available_width
            percentage = 100.0
            will_fit = True
        
        if will_fit or needed_scale == self._config.min_scale_x:
            return FitSuggestion(
                suggestion_type=SuggestionType.SCALE_HORIZONTAL,
                description=f"Escalar ancho al {needed_scale * 100:.0f}%",
                adjusted_scale_x=needed_scale,
                estimated_width=width,
                estimated_fit_percentage=percentage,
                priority=70 if needed_scale > 0.85 else 50,
                preserves_readability=needed_scale > 0.85
            )
        
        return None
    
    def _suggest_size_reduction(
        self,
        text: str,
        font_name: str,
        font_size: float,
        available_width: float,
        char_spacing: float,
        scale_x: float
    ) -> Optional[FitSuggestion]:
        """Sugiere reducción de tamaño."""
        test_size = font_size
        min_size = font_size * self._config.min_size_factor
        
        while test_size >= min_size:
            width = self._calculate_text_width(
                text, font_name, test_size, char_spacing, scale_x
            )
            if width <= available_width:
                percentage = (width / available_width) * 100.0
                factor = test_size / font_size
                return FitSuggestion(
                    suggestion_type=SuggestionType.REDUCE_SIZE,
                    description=f"Reducir tamaño a {test_size:.1f}pt ({factor * 100:.0f}%)",
                    adjusted_font_size=test_size,
                    estimated_width=width,
                    estimated_fit_percentage=percentage,
                    priority=60 if factor > 0.85 else 40,
                    preserves_readability=factor > 0.85
                )
            test_size -= self._config.size_step
        
        return None
    
    def _suggest_truncation(
        self,
        text: str,
        font_name: str,
        font_size: float,
        available_width: float,
        char_spacing: float,
        scale_x: float
    ) -> Optional[FitSuggestion]:
        """Sugiere truncamiento de texto."""
        if not text:
            return None
        
        # Buscar el punto de truncamiento
        for i in range(len(text), 0, -1):
            truncated = text[:i] + "..."
            width = self._calculate_text_width(
                truncated, font_name, font_size, char_spacing, scale_x
            )
            if width <= available_width:
                truncation_percent = ((len(text) - i) / len(text)) * 100.0
                
                if truncation_percent > self._config.max_truncation_percent:
                    # Demasiado truncamiento
                    break
                
                percentage = (width / available_width) * 100.0
                return FitSuggestion(
                    suggestion_type=SuggestionType.TRUNCATE,
                    description=f"Truncar texto ({truncation_percent:.0f}% eliminado)",
                    adjusted_text=truncated,
                    estimated_width=width,
                    estimated_fit_percentage=percentage,
                    priority=30,
                    preserves_readability=truncation_percent < 15.0
                )
        
        return None
    
    def clear_cache(self) -> None:
        """Limpia la cache de métricas de fuentes."""
        self._font_cache.clear()


# ================== Widget de indicador ==================


class FitStatusIndicator(QWidget):
    """
    Widget que muestra el estado de ajuste visualmente.
    
    Incluye una barra de progreso coloreada y texto descriptivo.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Inicializa el indicador."""
        super().__init__(parent)
        self._status = FitValidationStatus.UNKNOWN
        self._percentage = 0.0
        self._message = ""
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configura la interfaz."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Barra de progreso
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(16)
        layout.addWidget(self._progress)
        
        # Etiqueta de estado
        self._label = QLabel()
        self._label.setStyleSheet("font-size: 11px;")
        layout.addWidget(self._label)
        
        self._update_display()
    
    def set_result(self, result: FitValidationResult) -> None:
        """
        Actualiza el indicador con un resultado de validación.
        
        Args:
            result: Resultado de FitValidator
        """
        self._status = result.status
        self._percentage = result.percentage
        self._message = result.message
        self._update_display()
    
    def set_percentage(self, percentage: float, fits: bool = True) -> None:
        """
        Actualiza con porcentaje y estado.
        
        Args:
            percentage: Porcentaje de uso
            fits: True si el texto cabe
        """
        self._percentage = percentage
        self._status = FitValidationStatus.from_percentage(percentage)
        self._message = f"{percentage:.1f}% del espacio usado"
        self._update_display()
    
    def reset(self) -> None:
        """Resetea al estado inicial."""
        self._status = FitValidationStatus.UNKNOWN
        self._percentage = 0.0
        self._message = ""
        self._update_display()
    
    def _update_display(self) -> None:
        """Actualiza la visualización."""
        # Actualizar barra
        display_pct = min(100, int(self._percentage))
        self._progress.setValue(display_pct)
        
        # Color según estado
        if self._status == FitValidationStatus.FITS:
            color = "#4CAF50"  # Verde
        elif self._status == FitValidationStatus.TIGHT:
            color = "#FF9800"  # Naranja
        elif self._status == FitValidationStatus.OVERFLOW:
            color = "#F44336"  # Rojo
        else:
            color = "#9E9E9E"  # Gris
        
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f0f0f0;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)
        
        # Actualizar etiqueta
        self._label.setText(self._message)
        self._label.setStyleSheet(f"font-size: 11px; color: {color};")


class FitValidationPanel(QWidget):
    """
    Panel completo de validación de ajuste.
    
    Muestra métricas detalladas y sugerencias de ajuste.
    """
    
    suggestionSelected = pyqtSignal(FitSuggestion)
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Inicializa el panel."""
        super().__init__(parent)
        self._result: Optional[FitValidationResult] = None
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configura la interfaz."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Indicador de estado
        self._indicator = FitStatusIndicator()
        layout.addWidget(self._indicator)
        
        # Métricas detalladas
        metrics_frame = QFrame()
        metrics_frame.setFrameShape(QFrame.Shape.StyledPanel)
        metrics_layout = QVBoxLayout(metrics_frame)
        metrics_layout.setContentsMargins(8, 8, 8, 8)
        
        self._metrics_labels: Dict[str, QLabel] = {}
        for key, label_text in [
            ("available", "Disponible:"),
            ("current", "Actual:"),
            ("remaining", "Restante:"),
        ]:
            row = QHBoxLayout()
            label = QLabel(label_text)
            label.setFixedWidth(80)
            value = QLabel("-")
            value.setAlignment(Qt.AlignmentFlag.AlignRight)
            self._metrics_labels[key] = value
            row.addWidget(label)
            row.addWidget(value)
            metrics_layout.addLayout(row)
        
        layout.addWidget(metrics_frame)
        
        # Sección de sugerencias
        self._suggestions_frame = QFrame()
        self._suggestions_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self._suggestions_layout = QVBoxLayout(self._suggestions_frame)
        self._suggestions_layout.setContentsMargins(8, 8, 8, 8)
        
        self._suggestions_title = QLabel("Sugerencias:")
        self._suggestions_title.setStyleSheet("font-weight: bold;")
        self._suggestions_layout.addWidget(self._suggestions_title)
        
        self._suggestions_container = QVBoxLayout()
        self._suggestions_layout.addLayout(self._suggestions_container)
        
        layout.addWidget(self._suggestions_frame)
        self._suggestions_frame.hide()
        
        layout.addStretch()
    
    def set_result(self, result: FitValidationResult) -> None:
        """
        Actualiza el panel con resultado de validación.
        
        Args:
            result: Resultado de FitValidator
        """
        self._result = result
        
        # Actualizar indicador
        self._indicator.set_result(result)
        
        # Actualizar métricas
        self._metrics_labels["available"].setText(
            f"{result.metrics.available_width:.1f}pt"
        )
        self._metrics_labels["current"].setText(
            f"{result.metrics.current_width:.1f}pt"
        )
        remaining = result.metrics.remaining_space
        remaining_color = "#4CAF50" if remaining >= 0 else "#F44336"
        self._metrics_labels["remaining"].setText(
            f"<span style='color: {remaining_color}'>{remaining:+.1f}pt</span>"
        )
        
        # Actualizar sugerencias
        self._update_suggestions(result.suggestions)
    
    def _update_suggestions(self, suggestions: list) -> None:
        """Actualiza la sección de sugerencias."""
        # Limpiar sugerencias anteriores
        while self._suggestions_container.count():
            item = self._suggestions_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not suggestions:
            self._suggestions_frame.hide()
            return
        
        self._suggestions_frame.show()
        
        for suggestion in suggestions:
            btn = self._create_suggestion_button(suggestion)
            self._suggestions_container.addWidget(btn)
    
    def _create_suggestion_button(self, suggestion: FitSuggestion) -> QWidget:
        """Crea un botón/widget para una sugerencia."""
        from PyQt5.QtWidgets import QPushButton
        
        btn = QPushButton()
        btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 6px 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f8f8;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
            }
        """)
        
        # Icono de estado
        icon = "✓" if suggestion.will_fit else "⚠"
        btn.setText(f"{icon} {suggestion.description}")
        btn.clicked.connect(lambda: self.suggestionSelected.emit(suggestion))
        
        return btn
    
    def reset(self) -> None:
        """Resetea el panel."""
        self._result = None
        self._indicator.reset()
        for label in self._metrics_labels.values():
            label.setText("-")
        self._update_suggestions([])


# ================== Factory Functions ==================


def create_fit_validator(
    config: Optional[FitValidatorConfig] = None
) -> FitValidator:
    """
    Crea un FitValidator con configuración.
    
    Args:
        config: Configuración opcional
        
    Returns:
        FitValidator configurado
    """
    return FitValidator(config=config)


def validate_text_fit(
    text: str,
    font_name: str,
    font_size: float,
    available_width: float,
    char_spacing: float = 0.0,
    scale_x: float = 1.0
) -> FitValidationResult:
    """
    Función de conveniencia para validar ajuste de texto.
    
    Args:
        text: Texto a validar
        font_name: Nombre de la fuente
        font_size: Tamaño en puntos
        available_width: Ancho disponible
        char_spacing: Espaciado entre caracteres
        scale_x: Escala horizontal
        
    Returns:
        FitValidationResult
    """
    validator = FitValidator()
    return validator.validate(
        text=text,
        font_name=font_name,
        font_size=font_size,
        available_width=available_width,
        char_spacing=char_spacing,
        scale_x=scale_x
    )


def quick_fit_check(
    text: str,
    font_name: str,
    font_size: float,
    available_width: float
) -> bool:
    """
    Verificación rápida de si el texto cabe.
    
    Args:
        text: Texto a verificar
        font_name: Nombre de la fuente
        font_size: Tamaño en puntos
        available_width: Ancho disponible
        
    Returns:
        True si el texto cabe
    """
    validator = FitValidator()
    return validator.quick_check(text, font_name, font_size, available_width)


def create_fit_status_indicator(
    parent: Optional[QWidget] = None
) -> FitStatusIndicator:
    """
    Crea un indicador de estado de ajuste.
    
    Args:
        parent: Widget padre
        
    Returns:
        FitStatusIndicator
    """
    return FitStatusIndicator(parent)


def create_fit_validation_panel(
    parent: Optional[QWidget] = None
) -> FitValidationPanel:
    """
    Crea un panel completo de validación.
    
    Args:
        parent: Widget padre
        
    Returns:
        FitValidationPanel
    """
    return FitValidationPanel(parent)

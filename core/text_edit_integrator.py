"""
TextEditIntegrator - Integración del Text Engine con el sistema de edición.

Este módulo conecta los componentes del text_engine con la UI de edición,
proporcionando:
- Reescritura segura de texto (SafeTextRewriter)
- Ajuste de texto al espacio disponible (GlyphWidthPreserver)
- Validación antes de guardar (PreSaveValidator)

Uso:
    integrator = TextEditIntegrator(pdf_document)
    
    # Preparar edición
    result = integrator.prepare_edit(
        page_num=0,
        original_text="Hello",
        new_text="Hello World",
        bbox=(100, 100, 200, 120),
        font_name="Helvetica",
        font_size=12
    )
    
    # Verificar si cabe
    if result.fits:
        integrator.apply_edit(result)
    else:
        # Mostrar advertencia
        print(f"Texto no cabe: {result.warning}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Tuple

# Imports del text_engine
try:
    from core.text_engine import (
        # Reescritura
        SafeTextRewriter,
        OverlayStrategy,
        get_recommended_strategy,
        create_safe_rewriter,
        
        # Ajuste de ancho
        GlyphWidthPreserver,
        FitStrategy,
        fit_text_to_width,
        calculate_text_width,
        
        # Validación
        PreSaveValidator,
        ValidationResult,
        create_validator,
    )
    HAS_TEXT_ENGINE = True
except ImportError:
    HAS_TEXT_ENGINE = False

# Font manager
try:
    from core.font_manager import get_font_manager
    HAS_FONT_MANAGER = True
except ImportError:
    HAS_FONT_MANAGER = False


class EditResult(Enum):
    """Resultado de una operación de edición."""
    SUCCESS = "success"
    FITS_TIGHT = "fits_tight"
    OVERFLOW = "overflow"
    ERROR = "error"


@dataclass
class EditPreparation:
    """Preparación de una edición de texto."""
    original_text: str
    new_text: str
    bbox: Tuple[float, float, float, float]
    font_name: str
    font_size: float
    page_num: int
    
    # Análisis
    fits: bool = True
    fit_strategy: Optional[FitStrategy] = None
    adjusted_text: Optional[str] = None
    adjusted_font_size: Optional[float] = None
    width_ratio: float = 1.0
    
    # Estrategia de overlay
    overlay_strategy: Optional[OverlayStrategy] = None
    
    # Resultado
    result: EditResult = EditResult.SUCCESS
    warning: Optional[str] = None
    error: Optional[str] = None
    
    @property
    def needs_adjustment(self) -> bool:
        """Verifica si el texto necesita ajuste."""
        return self.width_ratio > 1.0 or self.adjusted_font_size is not None


@dataclass 
class ValidationReport:
    """Reporte de validación pre-guardado."""
    is_valid: bool = True
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class TextEditIntegrator:
    """
    Integrador del Text Engine con el sistema de edición.
    
    Proporciona una API unificada para:
    - Preparar ediciones de texto
    - Verificar que el texto cabe
    - Validar antes de guardar
    """
    
    def __init__(self, pdf_document=None):
        """
        Inicializa el integrador.
        
        Args:
            pdf_document: Documento PDF (opcional, se puede establecer después)
        """
        self._pdf_doc = pdf_document
        self._rewriter: Optional[SafeTextRewriter] = None
        self._preserver: Optional[GlyphWidthPreserver] = None
        self._validator: Optional[PreSaveValidator] = None
        self._font_manager = None
        
        self._init_components()
    
    def _init_components(self):
        """Inicializa los componentes del text engine."""
        if not HAS_TEXT_ENGINE:
            return
        
        # Font manager
        if HAS_FONT_MANAGER:
            self._font_manager = get_font_manager()
        
        # Rewriter
        self._rewriter = create_safe_rewriter()
        
        # Width preserver
        self._preserver = GlyphWidthPreserver(font_extractor=self._font_manager)
        
        # Validator
        self._validator = create_validator()
    
    @property
    def is_available(self) -> bool:
        """Verifica si el text engine está disponible."""
        return HAS_TEXT_ENGINE and self._rewriter is not None
    
    def set_document(self, pdf_document):
        """Establece el documento PDF."""
        self._pdf_doc = pdf_document
    
    def prepare_edit(
        self,
        page_num: int,
        original_text: str,
        new_text: str,
        bbox: Tuple[float, float, float, float],
        font_name: str = "Helvetica",
        font_size: float = 12.0,
        is_bold: bool = False,
        color: Tuple[float, float, float] = (0, 0, 0),
    ) -> EditPreparation:
        """
        Prepara una edición de texto.
        
        Analiza si el nuevo texto cabe en el espacio disponible
        y recomienda la mejor estrategia.
        
        Args:
            page_num: Número de página
            original_text: Texto original
            new_text: Nuevo texto
            bbox: Bounding box (x0, y0, x1, y1)
            font_name: Nombre de la fuente
            font_size: Tamaño de fuente
            is_bold: Si es negrita
            color: Color RGB (0-1)
            
        Returns:
            EditPreparation con el análisis
        """
        prep = EditPreparation(
            original_text=original_text,
            new_text=new_text,
            bbox=bbox,
            font_name=font_name,
            font_size=font_size,
            page_num=page_num,
        )
        
        if not self.is_available:
            # Sin text engine, asumir que cabe
            prep.result = EditResult.SUCCESS
            return prep
        
        try:
            # 1. Analizar si el texto cabe
            available_width = bbox[2] - bbox[0]
            
            # Calcular ancho del nuevo texto
            new_width = calculate_text_width(
                text=new_text,
                font_name=font_name,
                font_size=font_size,
            )
            
            # Calcular ratio
            prep.width_ratio = new_width / available_width if available_width > 0 else 999
            
            # 2. Determinar si cabe
            if prep.width_ratio <= 1.0:
                prep.fits = True
                prep.result = EditResult.SUCCESS
            elif prep.width_ratio <= 1.1:
                # Cabe ajustado (10% de overflow aceptable)
                prep.fits = True
                prep.result = EditResult.FITS_TIGHT
                prep.warning = "El texto cabe pero está ajustado"
            else:
                # No cabe, intentar ajuste
                prep.fits = False
                prep.result = EditResult.OVERFLOW
                
                # Intentar ajustar
                fit_result = fit_text_to_width(
                    original_text=original_text,
                    new_text=new_text,
                    font_name=font_name,
                    font_size=font_size,
                )
                
                if fit_result:
                    prep.fit_strategy = fit_result.fit_strategy
                    prep.adjusted_text = fit_result.adjusted_text
                    prep.adjusted_font_size = fit_result.adjusted_font_size
                    
                    if fit_result.fits:
                        prep.fits = True
                        prep.result = EditResult.FITS_TIGHT
                        prep.warning = f"Texto ajustado usando estrategia: {fit_result.fit_strategy.value}"
                    else:
                        prep.warning = f"El texto es {prep.width_ratio:.0%} más largo que el espacio disponible"
            
            # 3. Determinar estrategia de overlay
            text_length_change = len(new_text) - len(original_text)
            has_font_change = False  # TODO: detectar cambios de fuente
            
            prep.overlay_strategy = get_recommended_strategy(
                text_length_change=text_length_change,
                has_font_change=has_font_change,
                pdf_has_signatures=False,
            )
            
        except Exception as e:
            prep.result = EditResult.ERROR
            prep.error = str(e)
        
        return prep
    
    def validate_before_save(self) -> ValidationReport:
        """
        Valida el documento antes de guardar.
        
        Returns:
            ValidationReport con el resultado
        """
        report = ValidationReport()
        
        if not self.is_available or not self._validator:
            return report
        
        if not self._pdf_doc:
            report.warnings.append("No hay documento para validar")
            return report
        
        try:
            # Obtener documento fitz subyacente
            fitz_doc = getattr(self._pdf_doc, '_doc', None)
            if not fitz_doc:
                report.warnings.append("No se pudo acceder al documento interno")
                return report
            
            # Validar
            validation = self._validator.validate_quick(fitz_doc)
            
            if validation.result == ValidationResult.VALID:
                report.is_valid = True
            elif validation.result == ValidationResult.VALID_WITH_WARNINGS:
                report.is_valid = True
                for issue in validation.issues:
                    report.warnings.append(issue.message)
            else:
                report.is_valid = False
                for issue in validation.issues:
                    if issue.severity.value >= 3:  # ERROR
                        report.errors.append(issue.message)
                    else:
                        report.warnings.append(issue.message)
                    if issue.suggestion:
                        report.suggestions.append(issue.suggestion)
                        
        except Exception as e:
            report.warnings.append(f"Error durante validación: {e}")
        
        return report
    
    def estimate_text_width(
        self,
        text: str,
        font_name: str = "Helvetica",
        font_size: float = 12.0,
    ) -> float:
        """
        Estima el ancho de un texto.
        
        Args:
            text: Texto a medir
            font_name: Nombre de la fuente
            font_size: Tamaño de fuente
            
        Returns:
            Ancho estimado en puntos
        """
        if not self.is_available:
            # Estimación básica: ~0.5 x font_size por carácter
            return len(text) * font_size * 0.5
        
        return calculate_text_width(
            text=text,
            font_name=font_name,
            font_size=font_size,
        )
    
    def check_text_fits(
        self,
        text: str,
        available_width: float,
        font_name: str = "Helvetica",
        font_size: float = 12.0,
    ) -> Tuple[bool, float]:
        """
        Verifica si un texto cabe en un ancho dado.
        
        Args:
            text: Texto a verificar
            available_width: Ancho disponible
            font_name: Nombre de la fuente
            font_size: Tamaño de fuente
            
        Returns:
            Tupla (cabe, ratio) donde ratio es text_width/available_width
        """
        text_width = self.estimate_text_width(text, font_name, font_size)
        ratio = text_width / available_width if available_width > 0 else 999
        fits = ratio <= 1.1  # 10% de tolerancia
        return (fits, ratio)


# Singleton global
_integrator: Optional[TextEditIntegrator] = None


def get_text_integrator() -> TextEditIntegrator:
    """Obtiene el integrador global."""
    global _integrator
    if _integrator is None:
        _integrator = TextEditIntegrator()
    return _integrator


def create_text_integrator(pdf_document=None) -> TextEditIntegrator:
    """Crea un nuevo integrador."""
    return TextEditIntegrator(pdf_document)

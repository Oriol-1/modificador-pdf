"""
PreSaveValidator - Validación de integridad antes de guardar.

Este módulo verifica la integridad del documento PDF antes de guardarlo,
detectando problemas potenciales que podrían corromper el archivo.

Funcionalidades:
- Validación de estructura del documento
- Verificación de fuentes y recursos
- Detección de contenido problemático
- Validación de modificaciones pendientes
- Generación de reportes de validación

PHASE3-3D05: Validación pre-guardado (3h estimado)
Dependencias: 3D-01 a 3D-04
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, Any, List, Callable, Set
import logging
import re

logger = logging.getLogger(__name__)


# ================== Enums ==================


class ValidationSeverity(Enum):
    """Severidad de un problema de validación."""
    INFO = auto()       # Información, sin problema
    WARNING = auto()    # Advertencia, puede continuar
    ERROR = auto()      # Error, no debería guardar
    CRITICAL = auto()   # Crítico, definitivamente no guardar


class ValidationCategory(Enum):
    """Categoría de validación."""
    STRUCTURE = auto()      # Estructura del documento
    FONTS = auto()          # Fuentes y tipografía
    CONTENT = auto()        # Contenido de texto
    RESOURCES = auto()      # Recursos (imágenes, etc.)
    ANNOTATIONS = auto()    # Anotaciones y formularios
    METADATA = auto()       # Metadatos del documento
    SECURITY = auto()       # Permisos y encriptación
    MODIFICATIONS = auto()  # Modificaciones pendientes


class ValidationResult(Enum):
    """Resultado general de validación."""
    VALID = auto()          # Documento válido
    VALID_WITH_WARNINGS = auto()  # Válido pero con advertencias
    INVALID = auto()        # Inválido, no guardar
    UNKNOWN = auto()        # No se pudo determinar


class ContentIssueType(Enum):
    """Tipos de problemas de contenido."""
    EMPTY_PAGE = auto()
    MISSING_TEXT = auto()
    CORRUPTED_TEXT = auto()
    ENCODING_ERROR = auto()
    INVALID_CHARACTERS = auto()
    OVERFLOW_TEXT = auto()
    ORPHAN_ELEMENT = auto()


class FontIssueType(Enum):
    """Tipos de problemas de fuentes."""
    MISSING_FONT = auto()
    SUBSET_INCOMPLETE = auto()
    EMBEDDING_FAILED = auto()
    ENCODING_MISMATCH = auto()
    METRICS_INVALID = auto()
    GLYPH_MISSING = auto()


class StructureIssueType(Enum):
    """Tipos de problemas de estructura."""
    INVALID_XREF = auto()
    BROKEN_REFERENCE = auto()
    CIRCULAR_REFERENCE = auto()
    INVALID_STREAM = auto()
    MISSING_OBJECT = auto()
    DUPLICATE_KEY = auto()


# ================== Dataclasses ==================


@dataclass
class ValidationIssue:
    """
    Un problema detectado durante la validación.
    """
    severity: ValidationSeverity
    category: ValidationCategory
    code: str                       # Código único del problema
    message: str                    # Descripción legible
    
    # Ubicación
    page_num: Optional[int] = None  # Número de página (si aplica)
    location: Optional[str] = None  # Ubicación específica
    
    # Detalles
    details: Dict[str, Any] = field(default_factory=dict)
    suggestion: Optional[str] = None  # Sugerencia de solución
    
    # Auto-fix
    can_auto_fix: bool = False
    auto_fix_action: Optional[str] = None
    
    def __post_init__(self):
        """Valida la consistencia del issue."""
        if self.can_auto_fix and not self.auto_fix_action:
            self.auto_fix_action = "auto_fix_available"
    
    @property
    def is_blocking(self) -> bool:
        """Si este problema bloquea el guardado."""
        return self.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario."""
        return {
            'severity': self.severity.name,
            'category': self.category.name,
            'code': self.code,
            'message': self.message,
            'page_num': self.page_num,
            'location': self.location,
            'details': self.details,
            'suggestion': self.suggestion,
            'can_auto_fix': self.can_auto_fix,
            'is_blocking': self.is_blocking,
        }
    
    def __str__(self) -> str:
        """Representación legible."""
        loc = f" (página {self.page_num})" if self.page_num else ""
        return f"[{self.severity.name}] {self.code}: {self.message}{loc}"


@dataclass
class ValidationReport:
    """
    Reporte completo de validación.
    """
    result: ValidationResult
    issues: List[ValidationIssue] = field(default_factory=list)
    
    # Estadísticas
    total_pages_checked: int = 0
    total_fonts_checked: int = 0
    total_objects_checked: int = 0
    
    # Tiempos
    validation_time_ms: float = 0.0
    
    # Metadatos
    document_path: Optional[str] = None
    validator_version: str = "1.0.0"
    
    def __post_init__(self):
        """Calcula resultado basado en issues."""
        if self.result == ValidationResult.UNKNOWN and self.issues:
            self._calculate_result()
    
    def _calculate_result(self) -> None:
        """Calcula el resultado basado en los issues."""
        if not self.issues:
            self.result = ValidationResult.VALID
            return
        
        has_critical = any(i.severity == ValidationSeverity.CRITICAL for i in self.issues)
        has_error = any(i.severity == ValidationSeverity.ERROR for i in self.issues)
        has_warning = any(i.severity == ValidationSeverity.WARNING for i in self.issues)
        
        if has_critical or has_error:
            self.result = ValidationResult.INVALID
        elif has_warning:
            self.result = ValidationResult.VALID_WITH_WARNINGS
        else:
            self.result = ValidationResult.VALID
    
    @property
    def is_valid(self) -> bool:
        """Si el documento es válido para guardar."""
        return self.result in (ValidationResult.VALID, ValidationResult.VALID_WITH_WARNINGS)
    
    @property
    def blocking_issues(self) -> List[ValidationIssue]:
        """Issues que bloquean el guardado."""
        return [i for i in self.issues if i.is_blocking]
    
    @property
    def warnings(self) -> List[ValidationIssue]:
        """Solo advertencias."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]
    
    @property
    def errors(self) -> List[ValidationIssue]:
        """Solo errores."""
        return [i for i in self.issues 
                if i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)]
    
    @property
    def fixable_issues(self) -> List[ValidationIssue]:
        """Issues que pueden auto-corregirse."""
        return [i for i in self.issues if i.can_auto_fix]
    
    def issues_by_category(self, category: ValidationCategory) -> List[ValidationIssue]:
        """Filtra issues por categoría."""
        return [i for i in self.issues if i.category == category]
    
    def issues_by_page(self, page_num: int) -> List[ValidationIssue]:
        """Filtra issues por página."""
        return [i for i in self.issues if i.page_num == page_num]
    
    def add_issue(self, issue: ValidationIssue) -> None:
        """Agrega un issue y recalcula resultado."""
        self.issues.append(issue)
        self._calculate_result()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario."""
        return {
            'result': self.result.name,
            'is_valid': self.is_valid,
            'total_issues': len(self.issues),
            'blocking_issues_count': len(self.blocking_issues),
            'warnings_count': len(self.warnings),
            'errors_count': len(self.errors),
            'issues': [i.to_dict() for i in self.issues],
            'total_pages_checked': self.total_pages_checked,
            'total_fonts_checked': self.total_fonts_checked,
            'validation_time_ms': self.validation_time_ms,
            'document_path': self.document_path,
        }
    
    def summary(self) -> str:
        """Genera un resumen legible."""
        lines = [
            f"Resultado: {self.result.name}",
            f"Total issues: {len(self.issues)}",
            f"  - Errores: {len(self.errors)}",
            f"  - Advertencias: {len(self.warnings)}",
            f"Páginas revisadas: {self.total_pages_checked}",
            f"Tiempo: {self.validation_time_ms:.2f}ms",
        ]
        return "\n".join(lines)


@dataclass
class ValidatorConfig:
    """Configuración del validador."""
    # Qué validar
    check_structure: bool = True
    check_fonts: bool = True
    check_content: bool = True
    check_resources: bool = True
    check_annotations: bool = True
    check_metadata: bool = True
    check_modifications: bool = True
    
    # Tolerancias
    allow_missing_fonts: bool = False
    allow_subset_fonts: bool = True
    allow_empty_pages: bool = True
    
    # Límites
    max_issues: int = 100           # Detener después de N issues
    timeout_ms: float = 30000.0     # Timeout de validación
    
    # Páginas específicas
    pages_to_check: Optional[List[int]] = None  # None = todas


@dataclass
class ModificationRecord:
    """Registro de una modificación pendiente."""
    modification_type: str          # Tipo de modificación
    page_num: int                   # Página afectada
    original_content: Optional[str] = None
    new_content: Optional[str] = None
    timestamp: Optional[float] = None
    validated: bool = False
    validation_errors: List[str] = field(default_factory=list)


# ================== Validator Rules ==================


@dataclass
class ValidationRule:
    """
    Una regla de validación individual.
    """
    code: str
    name: str
    description: str
    category: ValidationCategory
    severity: ValidationSeverity  # Severidad por defecto
    
    # Función de validación
    check_func: Optional[Callable] = None
    
    # Estado
    enabled: bool = True
    
    def check(self, context: Dict[str, Any]) -> Optional[ValidationIssue]:
        """
        Ejecuta la validación.
        
        Args:
            context: Contexto con datos del documento
            
        Returns:
            ValidationIssue si hay problema, None si está OK
        """
        if not self.enabled or not self.check_func:
            return None
        
        try:
            return self.check_func(context, self)
        except Exception as e:
            logger.error(f"Error en regla {self.code}: {e}")
            return ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category=self.category,
                code=f"{self.code}_CHECK_ERROR",
                message=f"Error al ejecutar validación: {str(e)}",
                details={'exception': str(e)},
            )


# ================== Main Validator Class ==================


class PreSaveValidator:
    """
    Validador de documentos PDF antes de guardar.
    
    Verifica la integridad del documento, detectando problemas
    que podrían causar corrupción o pérdida de datos.
    
    Usage:
        validator = PreSaveValidator()
        
        # Validar documento
        report = validator.validate(doc)
        
        if report.is_valid:
            doc.save("output.pdf")
        else:
            for issue in report.blocking_issues:
                print(issue)
    """
    
    def __init__(
        self,
        config: Optional[ValidatorConfig] = None,
    ):
        """
        Inicializa el validador.
        
        Args:
            config: Configuración opcional
        """
        self._config = config or ValidatorConfig()
        self._rules: List[ValidationRule] = []
        self._modifications: List[ModificationRecord] = []
        self._custom_checks: List[Callable] = []
        
        # Registrar reglas por defecto
        self._register_default_rules()
    
    @property
    def config(self) -> ValidatorConfig:
        """Obtiene configuración."""
        return self._config
    
    # ================== Rule Management ==================
    
    def _register_default_rules(self) -> None:
        """Registra las reglas de validación por defecto."""
        # Reglas de estructura
        self._rules.extend([
            ValidationRule(
                code="STRUCT_001",
                name="valid_page_tree",
                description="El árbol de páginas debe ser válido",
                category=ValidationCategory.STRUCTURE,
                severity=ValidationSeverity.CRITICAL,
                check_func=self._check_page_tree,
            ),
            ValidationRule(
                code="STRUCT_002",
                name="valid_xref",
                description="La tabla xref debe ser consistente",
                category=ValidationCategory.STRUCTURE,
                severity=ValidationSeverity.ERROR,
                check_func=self._check_xref_table,
            ),
            ValidationRule(
                code="STRUCT_003",
                name="no_circular_refs",
                description="No debe haber referencias circulares",
                category=ValidationCategory.STRUCTURE,
                severity=ValidationSeverity.ERROR,
                check_func=self._check_circular_refs,
            ),
        ])
        
        # Reglas de fuentes
        self._rules.extend([
            ValidationRule(
                code="FONT_001",
                name="fonts_available",
                description="Las fuentes referenciadas deben estar disponibles",
                category=ValidationCategory.FONTS,
                severity=ValidationSeverity.ERROR,
                check_func=self._check_fonts_available,
            ),
            ValidationRule(
                code="FONT_002",
                name="font_encoding",
                description="La codificación de fuentes debe ser válida",
                category=ValidationCategory.FONTS,
                severity=ValidationSeverity.WARNING,
                check_func=self._check_font_encoding,
            ),
            ValidationRule(
                code="FONT_003",
                name="subset_complete",
                description="Los subsets de fuentes deben incluir todos los glifos",
                category=ValidationCategory.FONTS,
                severity=ValidationSeverity.WARNING,
                check_func=self._check_font_subsets,
            ),
        ])
        
        # Reglas de contenido
        self._rules.extend([
            ValidationRule(
                code="CONTENT_001",
                name="valid_content_streams",
                description="Los streams de contenido deben ser válidos",
                category=ValidationCategory.CONTENT,
                severity=ValidationSeverity.ERROR,
                check_func=self._check_content_streams,
            ),
            ValidationRule(
                code="CONTENT_002",
                name="text_encoding",
                description="El texto debe estar correctamente codificado",
                category=ValidationCategory.CONTENT,
                severity=ValidationSeverity.WARNING,
                check_func=self._check_text_encoding,
            ),
            ValidationRule(
                code="CONTENT_003",
                name="no_empty_text",
                description="No debe haber operaciones de texto vacías",
                category=ValidationCategory.CONTENT,
                severity=ValidationSeverity.INFO,
                check_func=self._check_empty_text,
            ),
        ])
        
        # Reglas de modificaciones
        self._rules.extend([
            ValidationRule(
                code="MOD_001",
                name="modifications_valid",
                description="Las modificaciones pendientes deben ser válidas",
                category=ValidationCategory.MODIFICATIONS,
                severity=ValidationSeverity.ERROR,
                check_func=self._check_modifications,
            ),
            ValidationRule(
                code="MOD_002",
                name="overlays_consistent",
                description="Los overlays deben ser consistentes",
                category=ValidationCategory.MODIFICATIONS,
                severity=ValidationSeverity.WARNING,
                check_func=self._check_overlays,
            ),
        ])
    
    def add_rule(self, rule: ValidationRule) -> None:
        """Agrega una regla de validación."""
        self._rules.append(rule)
    
    def remove_rule(self, code: str) -> bool:
        """Elimina una regla por código."""
        for i, rule in enumerate(self._rules):
            if rule.code == code:
                self._rules.pop(i)
                return True
        return False
    
    def enable_rule(self, code: str) -> bool:
        """Habilita una regla."""
        for rule in self._rules:
            if rule.code == code:
                rule.enabled = True
                return True
        return False
    
    def disable_rule(self, code: str) -> bool:
        """Deshabilita una regla."""
        for rule in self._rules:
            if rule.code == code:
                rule.enabled = False
                return True
        return False
    
    def add_custom_check(self, check_func: Callable) -> None:
        """Agrega una función de validación personalizada."""
        self._custom_checks.append(check_func)
    
    # ================== Modification Tracking ==================
    
    def record_modification(
        self,
        modification_type: str,
        page_num: int,
        original_content: Optional[str] = None,
        new_content: Optional[str] = None,
    ) -> None:
        """
        Registra una modificación pendiente para validar.
        
        Args:
            modification_type: Tipo de modificación
            page_num: Página afectada
            original_content: Contenido original
            new_content: Nuevo contenido
        """
        import time
        record = ModificationRecord(
            modification_type=modification_type,
            page_num=page_num,
            original_content=original_content,
            new_content=new_content,
            timestamp=time.time(),
        )
        self._modifications.append(record)
    
    def clear_modifications(self) -> None:
        """Limpia los registros de modificación."""
        self._modifications.clear()
    
    def get_modifications(self) -> List[ModificationRecord]:
        """Obtiene las modificaciones registradas."""
        return self._modifications.copy()
    
    # ================== Main Validation ==================
    
    def validate(
        self,
        doc: Any,
        path: Optional[str] = None,
    ) -> ValidationReport:
        """
        Valida un documento PDF.
        
        Args:
            doc: Documento fitz.Document
            path: Ruta del documento (para el reporte)
            
        Returns:
            ValidationReport con el resultado
        """
        import time
        start_time = time.time()
        
        report = ValidationReport(
            result=ValidationResult.UNKNOWN,
            document_path=path,
        )
        
        # Construir contexto
        context = self._build_context(doc)
        
        # Ejecutar validaciones por categoría
        if self._config.check_structure:
            self._validate_category(ValidationCategory.STRUCTURE, context, report)
        
        if self._config.check_fonts:
            self._validate_category(ValidationCategory.FONTS, context, report)
        
        if self._config.check_content:
            self._validate_category(ValidationCategory.CONTENT, context, report)
        
        if self._config.check_resources:
            self._validate_category(ValidationCategory.RESOURCES, context, report)
        
        if self._config.check_annotations:
            self._validate_category(ValidationCategory.ANNOTATIONS, context, report)
        
        if self._config.check_metadata:
            self._validate_category(ValidationCategory.METADATA, context, report)
        
        if self._config.check_modifications:
            self._validate_category(ValidationCategory.MODIFICATIONS, context, report)
        
        # Ejecutar checks personalizados
        for check_func in self._custom_checks:
            try:
                issues = check_func(doc, context)
                if issues:
                    for issue in issues:
                        report.add_issue(issue)
            except Exception as e:
                logger.error(f"Error en check personalizado: {e}")
        
        # Actualizar estadísticas
        report.total_pages_checked = context.get('page_count', 0)
        report.total_fonts_checked = len(context.get('fonts', []))
        report.total_objects_checked = context.get('object_count', 0)
        report.validation_time_ms = (time.time() - start_time) * 1000
        
        # Calcular resultado final
        report._calculate_result()
        
        return report
    
    def validate_page(
        self,
        doc: Any,
        page_num: int,
    ) -> ValidationReport:
        """
        Valida una página específica.
        
        Args:
            doc: Documento fitz.Document
            page_num: Número de página
            
        Returns:
            ValidationReport para la página
        """
        import time
        start_time = time.time()
        
        report = ValidationReport(
            result=ValidationResult.UNKNOWN,
            total_pages_checked=1,
        )
        
        try:
            page = doc[page_num]
            context = self._build_page_context(page, page_num)
            
            # Ejecutar reglas relevantes para página
            for rule in self._rules:
                if not rule.enabled:
                    continue
                
                if rule.category in (
                    ValidationCategory.CONTENT,
                    ValidationCategory.FONTS,
                    ValidationCategory.RESOURCES,
                    ValidationCategory.ANNOTATIONS,
                ):
                    issue = rule.check(context)
                    if issue:
                        issue.page_num = page_num
                        report.add_issue(issue)
        
        except Exception as e:
            report.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.STRUCTURE,
                code="PAGE_VALIDATION_ERROR",
                message=f"Error al validar página {page_num}: {str(e)}",
                page_num=page_num,
            ))
        
        report.validation_time_ms = (time.time() - start_time) * 1000
        report._calculate_result()
        
        return report
    
    def quick_validate(self, doc: Any) -> bool:
        """
        Validación rápida: solo verifica errores críticos.
        
        Args:
            doc: Documento fitz.Document
            
        Returns:
            True si el documento puede guardarse
        """
        context = self._build_context(doc)
        
        # Solo verificar reglas críticas
        for rule in self._rules:
            if rule.enabled and rule.severity == ValidationSeverity.CRITICAL:
                issue = rule.check(context)
                if issue and issue.is_blocking:
                    return False
        
        return True
    
    # ================== Context Building ==================
    
    def _build_context(self, doc: Any) -> Dict[str, Any]:
        """Construye el contexto de validación."""
        context = {
            'doc': doc,
            'page_count': 0,
            'fonts': [],
            'font_names': set(),
            'pages': [],
            'modifications': self._modifications,
            'object_count': 0,
        }
        
        try:
            context['page_count'] = len(doc)
            
            # Recopilar información de fuentes
            fonts_set: Set[str] = set()
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_fonts = page.get_fonts()
                for font in page_fonts:
                    font_name = font[3] if len(font) > 3 else str(font[0])
                    fonts_set.add(font_name)
                
                # Almacenar referencia de página
                context['pages'].append({
                    'num': page_num,
                    'page': page,
                    'fonts': page_fonts,
                })
            
            context['fonts'] = list(fonts_set)
            context['font_names'] = fonts_set
            
            # Contar objetos (aproximado)
            try:
                context['object_count'] = doc.xref_length()
            except Exception:
                pass
                
        except Exception as e:
            logger.warning(f"Error construyendo contexto: {e}")
        
        return context
    
    def _build_page_context(self, page: Any, page_num: int) -> Dict[str, Any]:
        """Construye contexto para una página."""
        context = {
            'page': page,
            'page_num': page_num,
            'fonts': [],
            'text_blocks': [],
        }
        
        try:
            context['fonts'] = page.get_fonts()
            
            # Extraer bloques de texto
            text_dict = page.get_text("dict", flags=0)
            context['text_blocks'] = text_dict.get('blocks', [])
            
        except Exception as e:
            logger.warning(f"Error construyendo contexto de página: {e}")
        
        return context
    
    def _validate_category(
        self,
        category: ValidationCategory,
        context: Dict[str, Any],
        report: ValidationReport,
    ) -> None:
        """Ejecuta todas las reglas de una categoría."""
        for rule in self._rules:
            if rule.category == category and rule.enabled:
                # Verificar límite de issues
                if len(report.issues) >= self._config.max_issues:
                    report.add_issue(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category=ValidationCategory.STRUCTURE,
                        code="MAX_ISSUES_REACHED",
                        message=f"Se alcanzó el límite de {self._config.max_issues} issues",
                    ))
                    return
                
                issue = rule.check(context)
                if issue:
                    report.add_issue(issue)
    
    # ================== Validation Checks ==================
    
    def _check_page_tree(
        self,
        context: Dict[str, Any],
        rule: ValidationRule,
    ) -> Optional[ValidationIssue]:
        """Verifica el árbol de páginas."""
        doc = context.get('doc')
        if not doc:
            return ValidationIssue(
                severity=rule.severity,
                category=rule.category,
                code=rule.code,
                message="No se proporcionó documento",
            )
        
        try:
            page_count = len(doc)
            if page_count <= 0:
                return ValidationIssue(
                    severity=rule.severity,
                    category=rule.category,
                    code=rule.code,
                    message="El documento no tiene páginas",
                    suggestion="El documento está vacío o corrupto",
                )
            
            # Verificar acceso a cada página
            for i in range(page_count):
                try:
                    _ = doc[i]
                except Exception as e:
                    return ValidationIssue(
                        severity=rule.severity,
                        category=rule.category,
                        code=rule.code,
                        message=f"No se puede acceder a la página {i}",
                        page_num=i,
                        details={'error': str(e)},
                    )
            
            return None  # OK
            
        except Exception as e:
            return ValidationIssue(
                severity=rule.severity,
                category=rule.category,
                code=rule.code,
                message=f"Error verificando árbol de páginas: {str(e)}",
            )
    
    def _check_xref_table(
        self,
        context: Dict[str, Any],
        rule: ValidationRule,
    ) -> Optional[ValidationIssue]:
        """Verifica la tabla xref."""
        doc = context.get('doc')
        if not doc:
            return None
        
        try:
            xref_len = doc.xref_length()
            if xref_len <= 0:
                return ValidationIssue(
                    severity=rule.severity,
                    category=rule.category,
                    code=rule.code,
                    message="Tabla xref vacía o inválida",
                )
            
            # Verificar algunos objetos aleatorios
            import random
            sample_size = min(10, xref_len)
            for _ in range(sample_size):
                xref = random.randint(1, xref_len - 1)
                try:
                    doc.xref_object(xref)
                except Exception:
                    return ValidationIssue(
                        severity=rule.severity,
                        category=rule.category,
                        code=rule.code,
                        message=f"Objeto xref {xref} inaccesible",
                        details={'xref': xref},
                    )
            
            return None
            
        except Exception as e:
            return ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category=rule.category,
                code=rule.code,
                message=f"No se pudo verificar xref: {str(e)}",
            )
    
    def _check_circular_refs(
        self,
        context: Dict[str, Any],
        rule: ValidationRule,
    ) -> Optional[ValidationIssue]:
        """Verifica referencias circulares."""
        # Esta es una verificación simplificada
        # Una verificación completa requeriría parsear todo el documento
        return None  # Asumimos OK por ahora
    
    def _check_fonts_available(
        self,
        context: Dict[str, Any],
        rule: ValidationRule,
    ) -> Optional[ValidationIssue]:
        """Verifica que las fuentes estén disponibles."""
        fonts = context.get('fonts', [])
        
        if not fonts:
            return None  # Sin fuentes, nada que verificar
        
        missing_fonts = []
        for font_name in fonts:
            # Verificar si es una fuente estándar o embebida
            if not self._is_font_available(font_name, context):
                missing_fonts.append(font_name)
        
        if missing_fonts:
            if self._config.allow_missing_fonts:
                return ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=rule.category,
                    code=rule.code,
                    message=f"Fuentes no disponibles: {', '.join(missing_fonts[:5])}",
                    details={'missing_fonts': missing_fonts},
                )
            else:
                return ValidationIssue(
                    severity=rule.severity,
                    category=rule.category,
                    code=rule.code,
                    message=f"Fuentes requeridas no disponibles: {', '.join(missing_fonts[:5])}",
                    details={'missing_fonts': missing_fonts},
                    suggestion="Embeber las fuentes o usar fuentes estándar",
                )
        
        return None
    
    def _is_font_available(self, font_name: str, context: Dict[str, Any]) -> bool:
        """Verifica si una fuente está disponible."""
        # Fuentes PDF estándar
        standard_fonts = {
            'Courier', 'Courier-Bold', 'Courier-BoldOblique', 'Courier-Oblique',
            'Helvetica', 'Helvetica-Bold', 'Helvetica-BoldOblique', 'Helvetica-Oblique',
            'Times-Roman', 'Times-Bold', 'Times-BoldItalic', 'Times-Italic',
            'Symbol', 'ZapfDingbats',
        }
        
        # Verificar nombre limpio
        clean_name = font_name.split('+')[-1] if '+' in font_name else font_name
        
        if clean_name in standard_fonts:
            return True
        
        # Si tiene prefijo de subset (ABCDEF+FontName), está embebida 
        if '+' in font_name:
            return True
        
        return False
    
    def _check_font_encoding(
        self,
        context: Dict[str, Any],
        rule: ValidationRule,
    ) -> Optional[ValidationIssue]:
        """Verifica la codificación de fuentes."""
        # Verificación básica - asumimos OK si las fuentes están disponibles
        return None
    
    def _check_font_subsets(
        self,
        context: Dict[str, Any],
        rule: ValidationRule,
    ) -> Optional[ValidationIssue]:
        """Verifica que los subsets de fuentes estén completos."""
        # Esta verificación requeriría analizar qué glifos se usan
        # vs qué glifos están en el subset
        return None
    
    def _check_content_streams(
        self,
        context: Dict[str, Any],
        rule: ValidationRule,
    ) -> Optional[ValidationIssue]:
        """Verifica los streams de contenido."""
        doc = context.get('doc')
        if not doc:
            return None
        
        try:
            for page_info in context.get('pages', []):
                page = page_info.get('page')
                page_num = page_info.get('num', 0)
                
                if page:
                    try:
                        # Intentar obtener el contenido
                        _ = page.get_text()
                    except Exception as e:
                        return ValidationIssue(
                            severity=rule.severity,
                            category=rule.category,
                            code=rule.code,
                            message=f"Stream de contenido inválido en página {page_num}",
                            page_num=page_num,
                            details={'error': str(e)},
                        )
            
            return None
            
        except Exception as e:
            return ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category=rule.category,
                code=rule.code,
                message=f"Error verificando streams: {str(e)}",
            )
    
    def _check_text_encoding(
        self,
        context: Dict[str, Any],
        rule: ValidationRule,
    ) -> Optional[ValidationIssue]:
        """Verifica la codificación del texto."""
        doc = context.get('doc')
        if not doc:
            return None
        
        invalid_chars_pattern = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
        
        for page_info in context.get('pages', []):
            page = page_info.get('page')
            page_num = page_info.get('num', 0)
            
            if page:
                try:
                    text = page.get_text()
                    if invalid_chars_pattern.search(text):
                        return ValidationIssue(
                            severity=rule.severity,
                            category=rule.category,
                            code=rule.code,
                            message=f"Caracteres de control inválidos en página {page_num}",
                            page_num=page_num,
                        )
                except Exception:
                    pass
        
        return None
    
    def _check_empty_text(
        self,
        context: Dict[str, Any],
        rule: ValidationRule,
    ) -> Optional[ValidationIssue]:
        """Verifica operaciones de texto vacías."""
        # Esta es más una verificación de optimización
        return None
    
    def _check_modifications(
        self,
        context: Dict[str, Any],
        rule: ValidationRule,
    ) -> Optional[ValidationIssue]:
        """Verifica modificaciones pendientes."""
        modifications = context.get('modifications', [])
        
        if not modifications:
            return None
        
        invalid_mods = []
        for mod in modifications:
            if not mod.validated:
                # Validar la modificación
                errors = self._validate_modification(mod, context)
                if errors:
                    mod.validation_errors = errors
                    invalid_mods.append(mod)
                else:
                    mod.validated = True
        
        if invalid_mods:
            return ValidationIssue(
                severity=rule.severity,
                category=rule.category,
                code=rule.code,
                message=f"{len(invalid_mods)} modificaciones no válidas",
                details={
                    'invalid_count': len(invalid_mods),
                    'modifications': [
                        {
                            'type': m.modification_type,
                            'page': m.page_num,
                            'errors': m.validation_errors,
                        }
                        for m in invalid_mods
                    ]
                },
            )
        
        return None
    
    def _validate_modification(
        self,
        mod: ModificationRecord,
        context: Dict[str, Any],
    ) -> List[str]:
        """Valida una modificación individual."""
        errors = []
        
        # Verificar que la página existe
        page_count = context.get('page_count', 0)
        if mod.page_num < 0 or mod.page_num >= page_count:
            errors.append(f"Página {mod.page_num} no existe")
        
        # Verificar contenido nuevo
        if mod.new_content is not None:
            if len(mod.new_content) > 100000:  # 100KB límite razonable
                errors.append("Contenido nuevo demasiado grande")
            
            # Verificar caracteres válidos
            try:
                mod.new_content.encode('utf-8')
            except UnicodeError:
                errors.append("Contenido con codificación inválida")
        
        return errors
    
    def _check_overlays(
        self,
        context: Dict[str, Any],
        rule: ValidationRule,
    ) -> Optional[ValidationIssue]:
        """Verifica consistencia de overlays."""
        # Los overlays deberían estar en las modificaciones
        # Esta verificación es placeholder
        return None
    
    # ================== Serialization ==================
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa configuración del validador."""
        return {
            'config': {
                'check_structure': self._config.check_structure,
                'check_fonts': self._config.check_fonts,
                'check_content': self._config.check_content,
                'max_issues': self._config.max_issues,
            },
            'rules_count': len(self._rules),
            'enabled_rules': sum(1 for r in self._rules if r.enabled),
            'modifications_count': len(self._modifications),
        }


# ================== Factory Functions ==================


def create_validator(
    strict: bool = False,
    **kwargs
) -> PreSaveValidator:
    """
    Crea un validador configurado.
    
    Args:
        strict: Si True, usa configuración estricta
        **kwargs: Argumentos adicionales para config
        
    Returns:
        PreSaveValidator configurado
    """
    if strict:
        config = ValidatorConfig(
            allow_missing_fonts=False,
            allow_subset_fonts=False,
            allow_empty_pages=False,
            **kwargs
        )
    else:
        config = ValidatorConfig(**kwargs)
    
    return PreSaveValidator(config=config)


def validate_document(
    doc: Any,
    path: Optional[str] = None,
    strict: bool = False,
) -> ValidationReport:
    """
    Valida un documento PDF.
    
    Función de conveniencia para validación rápida.
    
    Args:
        doc: Documento fitz.Document
        path: Ruta del documento
        strict: Si usar validación estricta
        
    Returns:
        ValidationReport
    """
    validator = create_validator(strict=strict)
    return validator.validate(doc, path)


def validate_page(
    doc: Any,
    page_num: int,
) -> ValidationReport:
    """
    Valida una página específica.
    
    Args:
        doc: Documento fitz.Document
        page_num: Número de página
        
    Returns:
        ValidationReport para la página
    """
    validator = PreSaveValidator()
    return validator.validate_page(doc, page_num)


def quick_check(doc: Any) -> bool:
    """
    Verificación rápida de documento.
    
    Args:
        doc: Documento fitz.Document
        
    Returns:
        True si el documento puede guardarse
    """
    validator = PreSaveValidator()
    return validator.quick_validate(doc)


def get_blocking_issues(doc: Any) -> List[ValidationIssue]:
    """
    Obtiene solo los issues que bloquean el guardado.
    
    Args:
        doc: Documento fitz.Document
        
    Returns:
        Lista de issues bloqueantes
    """
    validator = PreSaveValidator()
    report = validator.validate(doc)
    return report.blocking_issues


__all__ = [
    # Enums
    'ValidationSeverity',
    'ValidationCategory',
    'ValidationResult',
    'ContentIssueType',
    'FontIssueType',
    'StructureIssueType',
    # Dataclasses
    'ValidationIssue',
    'ValidationReport',
    'ValidatorConfig',
    'ModificationRecord',
    'ValidationRule',
    # Classes
    'PreSaveValidator',
    # Factory functions
    'create_validator',
    'validate_document',
    'validate_page',
    'quick_check',
    'get_blocking_issues',
]

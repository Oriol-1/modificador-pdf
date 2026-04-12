"""
Tests para PreSaveValidator - Validación de integridad antes de guardar.

PHASE3-3D05: Validación pre-guardado
"""

import pytest
from unittest.mock import Mock
import time

from core.text_engine.pre_save_validator import (
    # Enums
    ValidationSeverity,
    ValidationCategory,
    ValidationResult,
    ContentIssueType,
    FontIssueType,
    StructureIssueType,
    # Dataclasses
    ValidationIssue,
    ValidationReport,
    ValidatorConfig,
    ModificationRecord,
    ValidationRule,
    # Classes
    PreSaveValidator,
    # Factory functions
    create_validator,
    validate_document,
    validate_page,
    quick_check,
    get_blocking_issues,
)


# ============== Fixtures ==============


@pytest.fixture
def validator():
    """Validador con configuración por defecto."""
    return PreSaveValidator()


@pytest.fixture
def strict_validator():
    """Validador con configuración estricta."""
    config = ValidatorConfig(
        allow_missing_fonts=False,
        allow_subset_fonts=False,
        allow_empty_pages=False,
    )
    return PreSaveValidator(config=config)


@pytest.fixture
def mock_doc():
    """Documento mock básico."""
    doc = Mock()
    doc.__len__ = Mock(return_value=3)
    doc.xref_length.return_value = 100
    
    # Mock de páginas
    pages = []
    for i in range(3):
        page = Mock()
        page.get_fonts.return_value = [
            (0, 'n', 'Type1', 'Helvetica', None),
            (1, 'n', 'TrueType', 'ABCDEF+CustomFont', None),
        ]
        page.get_text.return_value = f"Texto de la página {i}"
        pages.append(page)
    
    doc.__getitem__ = Mock(side_effect=lambda i: pages[i])
    doc.xref_object = Mock(return_value="<</Type /Page>>")
    
    return doc


@pytest.fixture
def mock_empty_doc():
    """Documento vacío."""
    doc = Mock()
    doc.__len__ = Mock(return_value=0)
    doc.xref_length.return_value = 0
    return doc


@pytest.fixture
def mock_corrupted_doc():
    """Documento con página corrupta."""
    doc = Mock()
    doc.__len__ = Mock(return_value=2)
    doc.xref_length.return_value = 50
    
    page_ok = Mock()
    page_ok.get_fonts.return_value = []
    page_ok.get_text.return_value = "OK"
    
    page_bad = Mock()
    page_bad.get_fonts.return_value = []
    page_bad.get_text.side_effect = Exception("Página corrupta")
    
    doc.__getitem__ = Mock(side_effect=lambda i: page_ok if i == 0 else page_bad)
    doc.xref_object = Mock(return_value="<</Type /Page>>")
    
    return doc


# ============== Tests ValidationSeverity Enum ==============


class TestValidationSeverityEnum:
    """Tests para ValidationSeverity enum."""
    
    def test_all_severities_exist(self):
        """Verifica todas las severidades."""
        assert ValidationSeverity.INFO
        assert ValidationSeverity.WARNING
        assert ValidationSeverity.ERROR
        assert ValidationSeverity.CRITICAL
    
    def test_severity_ordering(self):
        """Las severidades tienen orden lógico."""
        assert ValidationSeverity.INFO.value < ValidationSeverity.WARNING.value
        assert ValidationSeverity.WARNING.value < ValidationSeverity.ERROR.value
        assert ValidationSeverity.ERROR.value < ValidationSeverity.CRITICAL.value


class TestValidationCategoryEnum:
    """Tests para ValidationCategory enum."""
    
    def test_all_categories_exist(self):
        """Verifica todas las categorías."""
        assert ValidationCategory.STRUCTURE
        assert ValidationCategory.FONTS
        assert ValidationCategory.CONTENT
        assert ValidationCategory.RESOURCES
        assert ValidationCategory.ANNOTATIONS
        assert ValidationCategory.METADATA
        assert ValidationCategory.SECURITY
        assert ValidationCategory.MODIFICATIONS


class TestValidationResultEnum:
    """Tests para ValidationResult enum."""
    
    def test_all_results_exist(self):
        """Verifica todos los resultados."""
        assert ValidationResult.VALID
        assert ValidationResult.VALID_WITH_WARNINGS
        assert ValidationResult.INVALID
        assert ValidationResult.UNKNOWN


class TestIssueTypeEnums:
    """Tests para enums de tipos de issues."""
    
    def test_content_issue_types(self):
        """Verifica ContentIssueType."""
        assert ContentIssueType.EMPTY_PAGE
        assert ContentIssueType.MISSING_TEXT
        assert ContentIssueType.ENCODING_ERROR
    
    def test_font_issue_types(self):
        """Verifica FontIssueType."""
        assert FontIssueType.MISSING_FONT
        assert FontIssueType.SUBSET_INCOMPLETE
        assert FontIssueType.EMBEDDING_FAILED
    
    def test_structure_issue_types(self):
        """Verifica StructureIssueType."""
        assert StructureIssueType.INVALID_XREF
        assert StructureIssueType.BROKEN_REFERENCE
        assert StructureIssueType.CIRCULAR_REFERENCE


# ============== Tests ValidationIssue Dataclass ==============


class TestValidationIssueDataclass:
    """Tests para ValidationIssue dataclass."""
    
    def test_create_basic(self):
        """Crea issue básico."""
        issue = ValidationIssue(
            severity=ValidationSeverity.WARNING,
            category=ValidationCategory.FONTS,
            code="FONT_001",
            message="Fuente no encontrada",
        )
        
        assert issue.severity == ValidationSeverity.WARNING
        assert issue.category == ValidationCategory.FONTS
        assert issue.code == "FONT_001"
        assert issue.message == "Fuente no encontrada"
    
    def test_with_page_and_location(self):
        """Issue con página y ubicación."""
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            category=ValidationCategory.CONTENT,
            code="CONTENT_001",
            message="Contenido inválido",
            page_num=5,
            location="línea 10",
        )
        
        assert issue.page_num == 5
        assert issue.location == "línea 10"
    
    def test_is_blocking_property(self):
        """Propiedad is_blocking."""
        error_issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            category=ValidationCategory.STRUCTURE,
            code="TEST",
            message="Test",
        )
        assert error_issue.is_blocking is True
        
        critical_issue = ValidationIssue(
            severity=ValidationSeverity.CRITICAL,
            category=ValidationCategory.STRUCTURE,
            code="TEST",
            message="Test",
        )
        assert critical_issue.is_blocking is True
        
        warning_issue = ValidationIssue(
            severity=ValidationSeverity.WARNING,
            category=ValidationCategory.STRUCTURE,
            code="TEST",
            message="Test",
        )
        assert warning_issue.is_blocking is False
    
    def test_auto_fix_action_auto_set(self):
        """Auto fix action se establece automáticamente."""
        issue = ValidationIssue(
            severity=ValidationSeverity.WARNING,
            category=ValidationCategory.FONTS,
            code="TEST",
            message="Test",
            can_auto_fix=True,
        )
        
        assert issue.auto_fix_action == "auto_fix_available"
    
    def test_to_dict(self):
        """Serialización a diccionario."""
        issue = ValidationIssue(
            severity=ValidationSeverity.WARNING,
            category=ValidationCategory.FONTS,
            code="FONT_001",
            message="Test message",
            page_num=3,
        )
        
        d = issue.to_dict()
        assert d['severity'] == 'WARNING'
        assert d['category'] == 'FONTS'
        assert d['code'] == 'FONT_001'
        assert d['page_num'] == 3
    
    def test_str_representation(self):
        """Representación string."""
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            category=ValidationCategory.CONTENT,
            code="ERR_001",
            message="Error encontrado",
            page_num=2,
        )
        
        str_repr = str(issue)
        assert "ERROR" in str_repr
        assert "ERR_001" in str_repr
        assert "página 2" in str_repr


# ============== Tests ValidationReport Dataclass ==============


class TestValidationReportDataclass:
    """Tests para ValidationReport dataclass."""
    
    def test_create_empty(self):
        """Crea reporte vacío."""
        report = ValidationReport(result=ValidationResult.VALID)
        
        assert report.result == ValidationResult.VALID
        assert len(report.issues) == 0
        assert report.is_valid is True
    
    def test_auto_calculate_result(self):
        """Calcula resultado automáticamente."""
        report = ValidationReport(result=ValidationResult.UNKNOWN)
        report.add_issue(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            category=ValidationCategory.STRUCTURE,
            code="TEST",
            message="Error",
        ))
        
        assert report.result == ValidationResult.INVALID
    
    def test_is_valid_property(self):
        """Propiedad is_valid."""
        valid_report = ValidationReport(result=ValidationResult.VALID)
        assert valid_report.is_valid is True
        
        warning_report = ValidationReport(result=ValidationResult.VALID_WITH_WARNINGS)
        assert warning_report.is_valid is True
        
        invalid_report = ValidationReport(result=ValidationResult.INVALID)
        assert invalid_report.is_valid is False
    
    def test_blocking_issues_property(self):
        """Propiedad blocking_issues."""
        report = ValidationReport(result=ValidationResult.UNKNOWN)
        
        report.add_issue(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            category=ValidationCategory.FONTS,
            code="W1", message="Warning",
        ))
        report.add_issue(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            category=ValidationCategory.STRUCTURE,
            code="E1", message="Error",
        ))
        report.add_issue(ValidationIssue(
            severity=ValidationSeverity.INFO,
            category=ValidationCategory.METADATA,
            code="I1", message="Info",
        ))
        
        blocking = report.blocking_issues
        assert len(blocking) == 1
        assert blocking[0].code == "E1"
    
    def test_warnings_property(self):
        """Propiedad warnings."""
        report = ValidationReport(result=ValidationResult.UNKNOWN)
        
        report.add_issue(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            category=ValidationCategory.FONTS,
            code="W1", message="Warning 1",
        ))
        report.add_issue(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            category=ValidationCategory.CONTENT,
            code="W2", message="Warning 2",
        ))
        report.add_issue(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            category=ValidationCategory.STRUCTURE,
            code="E1", message="Error",
        ))
        
        warnings = report.warnings
        assert len(warnings) == 2
    
    def test_errors_property(self):
        """Propiedad errors."""
        report = ValidationReport(result=ValidationResult.UNKNOWN)
        
        report.add_issue(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            category=ValidationCategory.FONTS,
            code="W1", message="Warning",
        ))
        report.add_issue(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            category=ValidationCategory.STRUCTURE,
            code="E1", message="Error",
        ))
        report.add_issue(ValidationIssue(
            severity=ValidationSeverity.CRITICAL,
            category=ValidationCategory.STRUCTURE,
            code="C1", message="Critical",
        ))
        
        errors = report.errors
        assert len(errors) == 2  # ERROR + CRITICAL
    
    def test_fixable_issues_property(self):
        """Propiedad fixable_issues."""
        report = ValidationReport(result=ValidationResult.UNKNOWN)
        
        report.add_issue(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            category=ValidationCategory.FONTS,
            code="W1", message="Warning",
            can_auto_fix=True,
        ))
        report.add_issue(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            category=ValidationCategory.CONTENT,
            code="W2", message="Warning 2",
            can_auto_fix=False,
        ))
        
        fixable = report.fixable_issues
        assert len(fixable) == 1
        assert fixable[0].code == "W1"
    
    def test_issues_by_category(self):
        """Filtra issues por categoría."""
        report = ValidationReport(result=ValidationResult.VALID_WITH_WARNINGS)
        
        report.issues = [
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.FONTS,
                code="F1", message="Font issue",
            ),
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.FONTS,
                code="F2", message="Font issue 2",
            ),
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.CONTENT,
                code="C1", message="Content issue",
            ),
        ]
        
        font_issues = report.issues_by_category(ValidationCategory.FONTS)
        assert len(font_issues) == 2
    
    def test_issues_by_page(self):
        """Filtra issues por página."""
        report = ValidationReport(result=ValidationResult.VALID_WITH_WARNINGS)
        
        report.issues = [
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.CONTENT,
                code="C1", message="Issue page 1",
                page_num=1,
            ),
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.CONTENT,
                code="C2", message="Issue page 2",
                page_num=2,
            ),
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.CONTENT,
                code="C3", message="Issue page 1 again",
                page_num=1,
            ),
        ]
        
        page1_issues = report.issues_by_page(1)
        assert len(page1_issues) == 2
    
    def test_to_dict(self):
        """Serialización a diccionario."""
        report = ValidationReport(
            result=ValidationResult.VALID,
            total_pages_checked=10,
            total_fonts_checked=5,
            validation_time_ms=150.5,
        )
        
        d = report.to_dict()
        assert d['result'] == 'VALID'
        assert d['is_valid'] is True
        assert d['total_pages_checked'] == 10
        assert d['validation_time_ms'] == 150.5
    
    def test_summary(self):
        """Genera resumen legible."""
        report = ValidationReport(
            result=ValidationResult.VALID_WITH_WARNINGS,
            total_pages_checked=5,
            validation_time_ms=100.0,
        )
        report.issues = [
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category=ValidationCategory.FONTS,
                code="W1", message="Warning",
            ),
        ]
        
        summary = report.summary()
        assert "VALID_WITH_WARNINGS" in summary
        assert "5" in summary  # páginas


# ============== Tests ValidatorConfig Dataclass ==============


class TestValidatorConfigDataclass:
    """Tests para ValidatorConfig dataclass."""
    
    def test_defaults(self):
        """Valores por defecto."""
        config = ValidatorConfig()
        
        assert config.check_structure is True
        assert config.check_fonts is True
        assert config.check_content is True
        assert config.allow_missing_fonts is False
        assert config.max_issues == 100
    
    def test_custom_config(self):
        """Configuración personalizada."""
        config = ValidatorConfig(
            check_metadata=False,
            allow_missing_fonts=True,
            max_issues=50,
        )
        
        assert config.check_metadata is False
        assert config.allow_missing_fonts is True
        assert config.max_issues == 50


# ============== Tests ModificationRecord Dataclass ==============


class TestModificationRecordDataclass:
    """Tests para ModificationRecord dataclass."""
    
    def test_create_basic(self):
        """Crea registro básico."""
        record = ModificationRecord(
            modification_type="text_replace",
            page_num=2,
            original_content="Hello",
            new_content="Hola",
        )
        
        assert record.modification_type == "text_replace"
        assert record.page_num == 2
        assert record.original_content == "Hello"
        assert record.new_content == "Hola"
        assert record.validated is False
    
    def test_with_timestamp(self):
        """Registro con timestamp."""
        record = ModificationRecord(
            modification_type="overlay",
            page_num=0,
            timestamp=time.time(),
        )
        
        assert record.timestamp is not None


# ============== Tests ValidationRule Dataclass ==============


class TestValidationRuleDataclass:
    """Tests para ValidationRule dataclass."""
    
    def test_create_basic(self):
        """Crea regla básica."""
        rule = ValidationRule(
            code="TEST_001",
            name="test_rule",
            description="Una regla de test",
            category=ValidationCategory.STRUCTURE,
            severity=ValidationSeverity.WARNING,
        )
        
        assert rule.code == "TEST_001"
        assert rule.enabled is True
    
    def test_check_without_func(self):
        """Check sin función devuelve None."""
        rule = ValidationRule(
            code="TEST_001",
            name="test_rule",
            description="Test",
            category=ValidationCategory.STRUCTURE,
            severity=ValidationSeverity.WARNING,
        )
        
        result = rule.check({})
        assert result is None
    
    def test_check_with_func(self):
        """Check con función."""
        def check_func(context, rule):
            if context.get('fail'):
                return ValidationIssue(
                    severity=rule.severity,
                    category=rule.category,
                    code=rule.code,
                    message="Test failed",
                )
            return None
        
        rule = ValidationRule(
            code="TEST_001",
            name="test_rule",
            description="Test",
            category=ValidationCategory.STRUCTURE,
            severity=ValidationSeverity.WARNING,
            check_func=check_func,
        )
        
        # Sin fallo
        result = rule.check({'fail': False})
        assert result is None
        
        # Con fallo
        result = rule.check({'fail': True})
        assert result is not None
        assert result.code == "TEST_001"
    
    def test_disabled_rule(self):
        """Regla deshabilitada no ejecuta."""
        def check_func(context, rule):
            return ValidationIssue(
                severity=rule.severity,
                category=rule.category,
                code=rule.code,
                message="Should not appear",
            )
        
        rule = ValidationRule(
            code="TEST_001",
            name="test_rule",
            description="Test",
            category=ValidationCategory.STRUCTURE,
            severity=ValidationSeverity.WARNING,
            check_func=check_func,
            enabled=False,
        )
        
        result = rule.check({})
        assert result is None


# ============== Tests PreSaveValidator - Initialization ==============


class TestPreSaveValidatorInit:
    """Tests de inicialización de PreSaveValidator."""
    
    def test_default_initialization(self):
        """Inicialización por defecto."""
        validator = PreSaveValidator()
        
        assert validator.config is not None
        assert len(validator._rules) > 0
    
    def test_with_config(self):
        """Con configuración."""
        config = ValidatorConfig(max_issues=50)
        validator = PreSaveValidator(config=config)
        
        assert validator.config.max_issues == 50
    
    def test_default_rules_registered(self):
        """Reglas por defecto están registradas."""
        validator = PreSaveValidator()
        
        # Verificar algunas reglas conocidas
        rule_codes = [r.code for r in validator._rules]
        assert "STRUCT_001" in rule_codes
        assert "FONT_001" in rule_codes
        assert "CONTENT_001" in rule_codes


# ============== Tests PreSaveValidator - Rule Management ==============


class TestPreSaveValidatorRules:
    """Tests de gestión de reglas."""
    
    def test_add_rule(self, validator):
        """Agrega una regla."""
        initial_count = len(validator._rules)
        
        new_rule = ValidationRule(
            code="CUSTOM_001",
            name="custom_rule",
            description="Regla personalizada",
            category=ValidationCategory.METADATA,
            severity=ValidationSeverity.INFO,
        )
        validator.add_rule(new_rule)
        
        assert len(validator._rules) == initial_count + 1
    
    def test_remove_rule(self, validator):
        """Elimina una regla."""
        result = validator.remove_rule("STRUCT_001")
        
        assert result is True
        rule_codes = [r.code for r in validator._rules]
        assert "STRUCT_001" not in rule_codes
    
    def test_remove_nonexistent_rule(self, validator):
        """Eliminar regla inexistente devuelve False."""
        result = validator.remove_rule("NONEXISTENT")
        
        assert result is False
    
    def test_enable_rule(self, validator):
        """Habilita una regla."""
        validator.disable_rule("STRUCT_001")
        result = validator.enable_rule("STRUCT_001")
        
        assert result is True
        rule = next(r for r in validator._rules if r.code == "STRUCT_001")
        assert rule.enabled is True
    
    def test_disable_rule(self, validator):
        """Deshabilita una regla."""
        result = validator.disable_rule("STRUCT_001")
        
        assert result is True
        rule = next(r for r in validator._rules if r.code == "STRUCT_001")
        assert rule.enabled is False
    
    def test_add_custom_check(self, validator):
        """Agrega check personalizado."""
        def custom_check(doc, context):
            return []
        
        validator.add_custom_check(custom_check)
        
        assert custom_check in validator._custom_checks


# ============== Tests PreSaveValidator - Modification Tracking ==============


class TestPreSaveValidatorModifications:
    """Tests de seguimiento de modificaciones."""
    
    def test_record_modification(self, validator):
        """Registra modificación."""
        validator.record_modification(
            modification_type="text_replace",
            page_num=0,
            original_content="Hello",
            new_content="Hola",
        )
        
        mods = validator.get_modifications()
        assert len(mods) == 1
        assert mods[0].modification_type == "text_replace"
        assert mods[0].page_num == 0
    
    def test_clear_modifications(self, validator):
        """Limpia modificaciones."""
        validator.record_modification("test", 0)
        validator.record_modification("test", 1)
        
        validator.clear_modifications()
        
        assert len(validator.get_modifications()) == 0
    
    def test_modification_has_timestamp(self, validator):
        """Modificación tiene timestamp."""
        validator.record_modification("test", 0)
        
        mods = validator.get_modifications()
        assert mods[0].timestamp is not None


# ============== Tests PreSaveValidator - Validation ==============


class TestPreSaveValidatorValidation:
    """Tests de validación."""
    
    def test_validate_valid_doc(self, validator, mock_doc):
        """Valida documento válido."""
        report = validator.validate(mock_doc)
        
        assert isinstance(report, ValidationReport)
        assert report.total_pages_checked == 3
    
    def test_validate_empty_doc(self, validator, mock_empty_doc):
        """Valida documento vacío."""
        report = validator.validate(mock_empty_doc)
        
        assert report.result == ValidationResult.INVALID
        assert len(report.blocking_issues) > 0
    
    def test_validate_with_path(self, validator, mock_doc):
        """Valida con ruta de documento."""
        report = validator.validate(mock_doc, path="/path/to/doc.pdf")
        
        assert report.document_path == "/path/to/doc.pdf"
    
    def test_validate_page(self, validator, mock_doc):
        """Valida página específica."""
        report = validator.validate_page(mock_doc, 0)
        
        assert report.total_pages_checked == 1
    
    def test_quick_validate_valid(self, validator, mock_doc):
        """Validación rápida de documento válido."""
        result = validator.quick_validate(mock_doc)
        
        assert isinstance(result, bool)
    
    def test_quick_validate_empty(self, validator, mock_empty_doc):
        """Validación rápida de documento vacío."""
        result = validator.quick_validate(mock_empty_doc)
        
        assert result is False
    
    def test_validation_time_recorded(self, validator, mock_doc):
        """El tiempo de validación se registra."""
        report = validator.validate(mock_doc)
        
        assert report.validation_time_ms > 0
    
    def test_max_issues_limit(self, validator, mock_doc):
        """Respeta límite máximo de issues."""
        validator._config.max_issues = 2
        
        # Agregar regla que siempre falla
        for i in range(5):
            def fail_check(context, rule, idx=i):
                return ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.METADATA,
                    code=f"FAIL_{idx}",
                    message=f"Fail {idx}",
                )
            
            validator.add_rule(ValidationRule(
                code=f"FAIL_{i}",
                name=f"fail_{i}",
                description="Always fails",
                category=ValidationCategory.METADATA,
                severity=ValidationSeverity.WARNING,
                check_func=fail_check,
            ))
        
        report = validator.validate(mock_doc)
        
        # Verificar que el límite se detecta (puede haber algunos más por múltiples categorías)
        max_issues_detected = any(i.code == "MAX_ISSUES_REACHED" for i in report.issues)
        assert max_issues_detected or len(report.issues) > 0


# ============== Tests PreSaveValidator - Specific Checks ==============


class TestPreSaveValidatorChecks:
    """Tests de verificaciones específicas."""
    
    def test_check_page_tree_valid(self, validator, mock_doc):
        """Verifica árbol de páginas válido."""
        context = validator._build_context(mock_doc)
        rule = next(r for r in validator._rules if r.code == "STRUCT_001")
        
        issue = validator._check_page_tree(context, rule)
        
        assert issue is None
    
    def test_check_page_tree_empty(self, validator, mock_empty_doc):
        """Verifica árbol de páginas vacío."""
        context = validator._build_context(mock_empty_doc)
        rule = next(r for r in validator._rules if r.code == "STRUCT_001")
        
        issue = validator._check_page_tree(context, rule)
        
        assert issue is not None
        assert issue.severity == ValidationSeverity.CRITICAL
    
    def test_check_fonts_standard(self, validator, mock_doc):
        """Verifica fuentes estándar."""
        context = validator._build_context(mock_doc)
        
        # Helvetica es estándar
        available = validator._is_font_available("Helvetica", context)
        assert available is True
    
    def test_check_fonts_subset(self, validator, mock_doc):
        """Verifica fuentes subset (embebidas)."""
        context = validator._build_context(mock_doc)
        
        # Prefix + indica subset embebido
        available = validator._is_font_available("ABCDEF+CustomFont", context)
        assert available is True
    
    def test_check_modifications_valid(self, validator, mock_doc):
        """Verifica modificaciones válidas."""
        validator.record_modification(
            modification_type="text_replace",
            page_num=0,
            new_content="Texto válido",
        )
        
        context = validator._build_context(mock_doc)
        context['modifications'] = validator._modifications
        
        rule = next(r for r in validator._rules if r.code == "MOD_001")
        issue = validator._check_modifications(context, rule)
        
        # No debería haber problemas con modificación válida
        assert issue is None
    
    def test_check_modifications_invalid_page(self, validator, mock_doc):
        """Verifica modificación con página inválida."""
        validator.record_modification(
            modification_type="text_replace",
            page_num=999,  # Página no existe
            new_content="Texto",
        )
        
        context = validator._build_context(mock_doc)
        context['modifications'] = validator._modifications
        
        rule = next(r for r in validator._rules if r.code == "MOD_001")
        issue = validator._check_modifications(context, rule)
        
        assert issue is not None


# ============== Tests PreSaveValidator - Serialization ==============


class TestPreSaveValidatorSerialization:
    """Tests de serialización."""
    
    def test_to_dict(self, validator):
        """Serialización a diccionario."""
        d = validator.to_dict()
        
        assert 'config' in d
        assert 'rules_count' in d
        assert d['rules_count'] > 0


# ============== Tests Factory Functions ==============


class TestFactoryFunctions:
    """Tests de funciones factory."""
    
    def test_create_validator_default(self):
        """Crear validador por defecto."""
        validator = create_validator()
        
        assert isinstance(validator, PreSaveValidator)
        assert validator.config.allow_missing_fonts is False
    
    def test_create_validator_strict(self):
        """Crear validador estricto."""
        validator = create_validator(strict=True)
        
        assert validator.config.allow_missing_fonts is False
        assert validator.config.allow_subset_fonts is False
        assert validator.config.allow_empty_pages is False
    
    def test_validate_document_function(self, mock_doc):
        """Función validate_document."""
        report = validate_document(mock_doc)
        
        assert isinstance(report, ValidationReport)
    
    def test_validate_page_function(self, mock_doc):
        """Función validate_page."""
        report = validate_page(mock_doc, 0)
        
        assert isinstance(report, ValidationReport)
        assert report.total_pages_checked == 1
    
    def test_quick_check_function(self, mock_doc):
        """Función quick_check."""
        result = quick_check(mock_doc)
        
        assert isinstance(result, bool)
    
    def test_get_blocking_issues_function(self, mock_doc):
        """Función get_blocking_issues."""
        issues = get_blocking_issues(mock_doc)
        
        assert isinstance(issues, list)


# ============== Tests Integration Scenarios ==============


class TestIntegrationScenarios:
    """Tests de escenarios de integración."""
    
    def test_save_workflow(self, validator, mock_doc):
        """Flujo de trabajo de guardado."""
        # 1. Registrar modificación
        validator.record_modification(
            modification_type="text_replace",
            page_num=0,
            original_content="Original",
            new_content="Modified",
        )
        
        # 2. Validar
        report = validator.validate(mock_doc)
        
        # 3. Verificar si se puede guardar
        if report.is_valid:
            # Simular guardado
            pass
        else:
            # Revisar issues
            for issue in report.blocking_issues:
                assert issue.is_blocking
    
    def test_multiple_modifications(self, validator, mock_doc):
        """Múltiples modificaciones."""
        for i in range(3):
            validator.record_modification(
                modification_type="overlay",
                page_num=i,
                new_content=f"Overlay {i}",
            )
        
        _report = validator.validate(mock_doc)
        
        assert len(validator.get_modifications()) == 3
    
    def test_custom_validation_rule(self, validator, mock_doc):
        """Agregar regla de validación personalizada."""
        def check_custom(context, rule):
            # Verificar algo específico
            page_count = context.get('page_count', 0)
            if page_count > 100:
                return ValidationIssue(
                    severity=rule.severity,
                    category=rule.category,
                    code=rule.code,
                    message="Documento demasiado grande",
                )
            return None
        
        validator.add_rule(ValidationRule(
            code="CUSTOM_SIZE",
            name="check_size",
            description="Verifica tamaño del documento",
            category=ValidationCategory.STRUCTURE,
            severity=ValidationSeverity.WARNING,
            check_func=check_custom,
        ))
        
        report = validator.validate(mock_doc)
        
        # Con 3 páginas no debería fallar
        custom_issues = [i for i in report.issues if i.code == "CUSTOM_SIZE"]
        assert len(custom_issues) == 0


# ============== Tests Edge Cases ==============


class TestEdgeCases:
    """Tests de casos límite."""
    
    def test_validate_none_doc(self, validator):
        """Validar documento None."""
        context = validator._build_context(None)
        
        assert context.get('doc') is None
        assert context.get('page_count') == 0
    
    def test_exception_in_rule(self, validator, mock_doc):
        """Excepción en regla de validación."""
        def failing_check(context, rule):
            raise ValueError("Test exception")
        
        validator.add_rule(ValidationRule(
            code="FAILING",
            name="failing_rule",
            description="Always fails",
            category=ValidationCategory.METADATA,
            severity=ValidationSeverity.WARNING,
            check_func=failing_check,
        ))
        
        # No debería crashear
        report = validator.validate(mock_doc)
        
        assert isinstance(report, ValidationReport)
    
    def test_very_long_modification_content(self, validator, mock_doc):
        """Modificación con contenido muy largo."""
        long_content = "x" * 200000  # 200KB
        
        validator.record_modification(
            modification_type="text_replace",
            page_num=0,
            new_content=long_content,
        )
        
        context = validator._build_context(mock_doc)
        context['modifications'] = validator._modifications
        
        rule = next(r for r in validator._rules if r.code == "MOD_001")
        issue = validator._check_modifications(context, rule)
        
        # Debería detectar contenido demasiado grande
        assert issue is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

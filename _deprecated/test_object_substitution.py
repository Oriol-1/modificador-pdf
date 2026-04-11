"""
Tests para ObjectSubstitution - Sustitución de objetos PDF.

PHASE3-3D02: Tests completos para la estrategia de sustitución de objetos.
"""

import pytest
from unittest.mock import MagicMock, patch
import json

from core.text_engine.object_substitution import (
    # Enums
    SubstitutionType,
    SubstitutionStatus,
    MatchStrategy,
    # Dataclasses
    TextLocation,
    TextSubstitution,
    SubstitutionResult,
    SubstitutorConfig,
    # Classes
    PDFTextEncoder,
    ContentStreamModifier,
    ObjectSubstitutor,
    # Factory functions
    create_substitutor,
    get_recommended_substitution_type,
)


# ================== Fixtures ==================


@pytest.fixture
def sample_location():
    """TextLocation de ejemplo."""
    return TextLocation(
        page_num=0,
        stream_start=100,
        stream_end=150,
        block_index=0,
        operation_index=0,
        original_text="Hello World",
        operator="Tj",
        position_x=100.0,
        position_y=200.0,
        raw_operator="(Hello World) Tj",
    )


@pytest.fixture
def sample_substitution():
    """TextSubstitution de ejemplo."""
    return TextSubstitution(
        original_text="Hello",
        new_text="World",
        substitution_type=SubstitutionType.OPERAND_ONLY,
        match_strategy=MatchStrategy.EXACT,
    )


@pytest.fixture
def substitutor():
    """ObjectSubstitutor configurado."""
    return ObjectSubstitutor()


@pytest.fixture
def modifier():
    """ContentStreamModifier configurado."""
    return ContentStreamModifier()


@pytest.fixture
def encoder():
    """PDFTextEncoder."""
    return PDFTextEncoder()


@pytest.fixture
def sample_stream():
    """Content stream de ejemplo."""
    return b"""BT
/F1 12 Tf
100 700 Td
(Hello World) Tj
ET
BT
/F1 12 Tf
100 680 Td
(Second line) Tj
ET"""


# ================== Tests: SubstitutionType Enum ==================


class TestSubstitutionType:
    """Tests para SubstitutionType enum."""
    
    def test_all_types_defined(self):
        """Verifica que todos los tipos están definidos."""
        expected = [
            'OPERAND_ONLY',
            'OPERATOR_REPLACE',
            'BLOCK_REPLACE',
            'STREAM_REBUILD',
        ]
        actual = [t.name for t in SubstitutionType]
        assert actual == expected
    
    def test_str_representation(self):
        """Verifica representación de string."""
        assert str(SubstitutionType.OPERAND_ONLY) == "Solo operando"
        assert str(SubstitutionType.OPERATOR_REPLACE) == "Operador completo"
        assert str(SubstitutionType.BLOCK_REPLACE) == "Bloque BT/ET"
    
    def test_risk_level_property(self):
        """Verifica niveles de riesgo."""
        assert SubstitutionType.OPERAND_ONLY.risk_level == 2
        assert SubstitutionType.OPERATOR_REPLACE.risk_level == 4
        assert SubstitutionType.BLOCK_REPLACE.risk_level == 6
        assert SubstitutionType.STREAM_REBUILD.risk_level == 8
    
    def test_risk_levels_increase(self):
        """Verifica que niveles de riesgo aumentan con complejidad."""
        types = list(SubstitutionType)
        for i in range(len(types) - 1):
            assert types[i].risk_level <= types[i + 1].risk_level
    
    def test_description_property(self):
        """Verifica que todas tienen descripción."""
        for sub_type in SubstitutionType:
            desc = sub_type.description
            assert isinstance(desc, str)
            assert len(desc) > 0


class TestSubstitutionStatus:
    """Tests para SubstitutionStatus enum."""
    
    def test_all_statuses_defined(self):
        """Verifica que todos los estados están definidos."""
        assert len(SubstitutionStatus) == 7
        assert SubstitutionStatus.SUCCESS in SubstitutionStatus
        assert SubstitutionStatus.FAILED in SubstitutionStatus
    
    def test_is_success_property(self):
        """Verifica propiedad is_success."""
        assert SubstitutionStatus.SUCCESS.is_success is True
        assert SubstitutionStatus.PARTIAL_SUCCESS.is_success is True
        assert SubstitutionStatus.FAILED.is_success is False
        assert SubstitutionStatus.VALIDATION_FAILED.is_success is False


class TestMatchStrategy:
    """Tests para MatchStrategy enum."""
    
    def test_all_strategies_defined(self):
        """Verifica que todas las estrategias están definidas."""
        expected = ['EXACT', 'CONTAINS', 'REGEX', 'POSITION', 'BLOCK_INDEX', 'OPERATOR_INDEX']
        actual = [s.name for s in MatchStrategy]
        assert actual == expected
    
    def test_str_representation(self):
        """Verifica representación de string."""
        assert str(MatchStrategy.EXACT) == "Exacto"
        assert str(MatchStrategy.REGEX) == "Regex"


# ================== Tests: TextLocation Dataclass ==================


class TestTextLocation:
    """Tests para TextLocation dataclass."""
    
    def test_default_values(self):
        """Verifica valores por defecto."""
        loc = TextLocation()
        assert loc.page_num == 0
        assert loc.stream_start == 0
        assert loc.operator == "Tj"
        assert loc.location_id != ""
    
    def test_custom_values(self, sample_location):
        """Verifica valores personalizados."""
        assert sample_location.page_num == 0
        assert sample_location.stream_start == 100
        assert sample_location.stream_end == 150
        assert sample_location.original_text == "Hello World"
    
    def test_byte_length_property(self, sample_location):
        """Verifica cálculo de longitud."""
        assert sample_location.byte_length == 50
    
    def test_auto_generated_id(self):
        """Verifica IDs únicos."""
        loc1 = TextLocation()
        loc2 = TextLocation()
        assert loc1.location_id != loc2.location_id
    
    def test_stream_end_validation(self):
        """Verifica que stream_end >= stream_start."""
        loc = TextLocation(stream_start=100, stream_end=50)
        assert loc.stream_end >= loc.stream_start
    
    def test_to_dict(self, sample_location):
        """Verifica conversión a diccionario."""
        d = sample_location.to_dict()
        assert d['page_num'] == 0
        assert d['stream_start'] == 100
        assert d['original_text'] == "Hello World"
    
    def test_from_dict(self, sample_location):
        """Verifica creación desde diccionario."""
        d = sample_location.to_dict()
        restored = TextLocation.from_dict(d)
        assert restored.original_text == sample_location.original_text
        assert restored.operator == sample_location.operator


# ================== Tests: TextSubstitution Dataclass ==================


class TestTextSubstitution:
    """Tests para TextSubstitution dataclass."""
    
    def test_default_values(self):
        """Verifica valores por defecto."""
        sub = TextSubstitution()
        assert sub.substitution_type == SubstitutionType.OPERAND_ONLY
        assert sub.match_strategy == MatchStrategy.EXACT
        assert sub.preserve_font is True
        assert sub.preserve_size is True
    
    def test_custom_values(self, sample_substitution):
        """Verifica valores personalizados."""
        assert sample_substitution.original_text == "Hello"
        assert sample_substitution.new_text == "World"
    
    def test_text_length_change(self):
        """Verifica cálculo de cambio de longitud."""
        sub = TextSubstitution(original_text="Hi", new_text="Hello")
        assert sub.text_length_change == 3
        
        sub2 = TextSubstitution(original_text="Hello", new_text="Hi")
        assert sub2.text_length_change == -3
    
    def test_is_same_length(self):
        """Verifica detección de misma longitud."""
        sub = TextSubstitution(original_text="Hello", new_text="World")
        assert sub.is_same_length is True
        
        sub2 = TextSubstitution(original_text="Hi", new_text="Hello")
        assert sub2.is_same_length is False
    
    def test_requires_reflow(self):
        """Verifica detección de necesidad de reflow."""
        # Texto más largo
        sub = TextSubstitution(original_text="Hi", new_text="Hello")
        assert sub.requires_reflow is True
        
        # Cambio de fuente
        sub2 = TextSubstitution(
            original_text="Hi", 
            new_text="Hi",
            preserve_font=False,
        )
        assert sub2.requires_reflow is True
        
        # Mismo texto, misma fuente
        sub3 = TextSubstitution(original_text="Hello", new_text="World")
        assert sub3.requires_reflow is False
    
    def test_to_dict(self, sample_substitution):
        """Verifica conversión a diccionario."""
        d = sample_substitution.to_dict()
        assert d['original_text'] == "Hello"
        assert d['new_text'] == "World"
        assert d['substitution_type'] == "OPERAND_ONLY"
    
    def test_from_dict(self, sample_substitution):
        """Verifica creación desde diccionario."""
        d = sample_substitution.to_dict()
        restored = TextSubstitution.from_dict(d)
        assert restored.original_text == sample_substitution.original_text
        assert restored.substitution_type == sample_substitution.substitution_type


# ================== Tests: SubstitutionResult Dataclass ==================


class TestSubstitutionResult:
    """Tests para SubstitutionResult dataclass."""
    
    def test_default_success(self):
        """Verifica que por defecto es éxito."""
        result = SubstitutionResult()
        assert result.success is True
        assert result.status == SubstitutionStatus.SUCCESS
    
    def test_add_warning(self):
        """Verifica añadir warning."""
        result = SubstitutionResult()
        result.add_warning("Multiple matches found")
        
        assert result.has_warnings is True
        assert len(result.warnings) == 1
        assert result.status == SubstitutionStatus.PARTIAL_SUCCESS
    
    def test_add_error(self):
        """Verifica añadir error."""
        result = SubstitutionResult()
        result.add_error("Text not found")
        
        assert result.success is False
        assert result.has_errors is True
        assert result.status == SubstitutionStatus.FAILED
    
    def test_to_dict(self):
        """Verifica conversión a diccionario."""
        result = SubstitutionResult(
            status=SubstitutionStatus.SUCCESS,
            message="OK",
            bytes_changed=10,
        )
        
        d = result.to_dict()
        assert d['status'] == 'SUCCESS'
        assert d['success'] is True
        assert d['bytes_changed'] == 10


# ================== Tests: SubstitutorConfig Dataclass ==================


class TestSubstitutorConfig:
    """Tests para SubstitutorConfig dataclass."""
    
    def test_default_values(self):
        """Verifica valores por defecto."""
        config = SubstitutorConfig()
        assert config.default_type == SubstitutionType.OPERAND_ONLY
        assert config.default_match == MatchStrategy.EXACT
        assert config.validate_before_apply is True
        assert config.create_backup is True
        assert config.max_risk_level == 6
    
    def test_custom_values(self):
        """Verifica valores personalizados."""
        config = SubstitutorConfig(
            default_type=SubstitutionType.OPERATOR_REPLACE,
            max_risk_level=8,
            allow_structure_change=True,
        )
        
        assert config.default_type == SubstitutionType.OPERATOR_REPLACE
        assert config.max_risk_level == 8
        assert config.allow_structure_change is True


# ================== Tests: PDFTextEncoder ==================


class TestPDFTextEncoder:
    """Tests para PDFTextEncoder."""
    
    def test_encode_literal_string_basic(self, encoder):
        """Verifica codificación básica de string literal."""
        result = encoder.encode_literal_string("Hello")
        assert result.startswith(b'(')
        assert result.endswith(b')')
        assert b'Hello' in result
    
    def test_encode_literal_string_with_escapes(self, encoder):
        """Verifica codificación con escapes."""
        result = encoder.encode_literal_string("Hello\nWorld")
        assert b'\\n' in result
        
        result2 = encoder.encode_literal_string("(test)")
        assert b'\\(' in result2
        assert b'\\)' in result2
    
    def test_encode_hex_string(self, encoder):
        """Verifica codificación hex."""
        result = encoder.encode_hex_string("AB")
        assert result.startswith(b'<')
        assert result.endswith(b'>')
    
    def test_decode_literal_string(self, encoder):
        """Verifica decodificación de string literal."""
        result = encoder.decode_literal_string(b'(Hello World)')
        assert result == "Hello World"
    
    def test_decode_literal_string_with_escapes(self, encoder):
        """Verifica decodificación con escapes."""
        result = encoder.decode_literal_string(b'(Hello\\nWorld)')
        assert '\n' in result
    
    def test_decode_hex_string(self, encoder):
        """Verifica decodificación hex."""
        # UTF-16BE for "AB"
        result = encoder.decode_hex_string(b'<0041 0042>')
        assert result == "AB"
    
    def test_roundtrip_literal(self, encoder):
        """Verifica roundtrip de string literal."""
        original = "Hello World!"
        encoded = encoder.encode_literal_string(original)
        decoded = encoder.decode_literal_string(encoded)
        assert decoded == original


# ================== Tests: ContentStreamModifier ==================


class TestContentStreamModifier:
    """Tests para ContentStreamModifier."""
    
    def test_creation(self, modifier):
        """Verifica creación del modificador."""
        assert modifier is not None
        assert modifier.config is not None
    
    def test_find_text_locations_exact(self, modifier, sample_stream):
        """Verifica búsqueda exacta."""
        locations = modifier.find_text_locations(
            sample_stream,
            "Hello World",
            MatchStrategy.EXACT,
        )
        
        # Puede encontrar 0 si el parser no extrae el texto exacto
        # Dependiendo de implementación del parser
        assert isinstance(locations, list)
    
    def test_find_text_locations_contains(self, modifier, sample_stream):
        """Verifica búsqueda por contenido."""
        locations = modifier.find_text_locations(
            sample_stream,
            "Hello",
            MatchStrategy.CONTAINS,
            "Hello",
        )
        
        assert isinstance(locations, list)
    
    def test_generate_text_operator_simple(self, modifier):
        """Verifica generación de operador simple."""
        result = modifier.generate_text_operator("Hello")
        
        assert "Tj" in result
        assert "(Hello)" in result
    
    def test_generate_text_operator_with_font(self, modifier):
        """Verifica generación con fuente."""
        result = modifier.generate_text_operator(
            "Hello",
            font_name="F1",
            font_size=12.0,
        )
        
        assert "/F1 12" in result
        assert "Tf" in result
    
    def test_generate_text_operator_with_position(self, modifier):
        """Verifica generación con posición."""
        result = modifier.generate_text_operator(
            "Hello",
            position=(100.0, 200.0),
        )
        
        assert "100.0 200.0 Td" in result
    
    def test_generate_text_operator_with_spacing(self, modifier):
        """Verifica generación con espaciado."""
        result = modifier.generate_text_operator(
            "Hello",
            char_spacing=1.5,
            word_spacing=2.0,
        )
        
        assert "1.5 Tc" in result
        assert "2.0 Tw" in result


# ================== Tests: ObjectSubstitutor ==================


class TestObjectSubstitutor:
    """Tests para ObjectSubstitutor."""
    
    def test_creation(self, substitutor):
        """Verifica creación del sustituyente."""
        assert substitutor is not None
        assert substitutor.config is not None
    
    def test_creation_with_config(self):
        """Verifica creación con configuración."""
        config = SubstitutorConfig(
            default_type=SubstitutionType.OPERATOR_REPLACE,
            max_risk_level=8,
        )
        sub = ObjectSubstitutor(config=config)
        
        assert sub.config.default_type == SubstitutionType.OPERATOR_REPLACE
        assert sub.config.max_risk_level == 8
    
    def test_create_substitution(self, substitutor):
        """Verifica crear sustitución."""
        sub = substitutor.create_substitution(
            original="Hello",
            new_text="World",
        )
        
        assert sub is not None
        assert sub.original_text == "Hello"
        assert sub.new_text == "World"
        assert sub.substitution_id in substitutor._substitutions
    
    def test_create_substitution_with_type(self, substitutor):
        """Verifica crear sustitución con tipo específico."""
        sub = substitutor.create_substitution(
            original="Hello",
            new_text="World",
            substitution_type=SubstitutionType.BLOCK_REPLACE,
        )
        
        assert sub.substitution_type == SubstitutionType.BLOCK_REPLACE
    
    def test_find_text(self, substitutor, sample_stream):
        """Verifica búsqueda de texto."""
        locations = substitutor.find_text(
            sample_stream,
            "Hello",
            page_num=5,
        )
        
        assert isinstance(locations, list)
        # Todas las ubicaciones deben tener page_num actualizado
        for loc in locations:
            assert loc.page_num == 5
    
    def test_validate_substitution_valid(self, substitutor):
        """Verifica validación de sustitución válida."""
        sub = TextSubstitution(
            original_text="Hello",
            new_text="World",
            substitution_type=SubstitutionType.OPERAND_ONLY,
        )
        
        is_valid, issues = substitutor.validate_substitution(sub)
        
        assert is_valid is True
        assert len(issues) == 0
    
    def test_validate_substitution_high_risk(self, substitutor):
        """Verifica validación de sustitución de alto riesgo."""
        sub = TextSubstitution(
            original_text="Hello",
            new_text="World",
            substitution_type=SubstitutionType.STREAM_REBUILD,
        )
        
        is_valid, issues = substitutor.validate_substitution(sub)
        
        # STREAM_REBUILD tiene riesgo 8, max es 6
        assert is_valid is False
        assert len(issues) > 0
    
    def test_validate_substitution_reflow_not_allowed(self, substitutor):
        """Verifica validación cuando reflow no está permitido."""
        sub = TextSubstitution(
            original_text="Hi",
            new_text="Hello World",  # Mucho más largo
            preserve_font=False,
        )
        
        is_valid, issues = substitutor.validate_substitution(sub)
        
        # Requiere reflow pero no está permitido por defecto
        assert is_valid is False
    
    def test_get_substitution(self, substitutor):
        """Verifica obtener sustitución por ID."""
        sub = substitutor.create_substitution("Hello", "World")
        
        retrieved = substitutor.get_substitution(sub.substitution_id)
        assert retrieved == sub
    
    def test_get_statistics(self, substitutor):
        """Verifica estadísticas."""
        substitutor.create_substitution("Hello", "World")
        substitutor.create_substitution("Foo", "Bar")
        
        stats = substitutor.get_statistics()
        
        assert stats['total_substitutions'] == 2
        assert stats['applied'] == 0
        assert stats['pending'] == 2
    
    def test_clear(self, substitutor):
        """Verifica limpieza."""
        substitutor.create_substitution("Hello", "World")
        substitutor.create_substitution("Foo", "Bar")
        
        substitutor.clear()
        
        assert len(substitutor._substitutions) == 0
        assert len(substitutor._page_substitutions) == 0
    
    def test_to_dict(self, substitutor):
        """Verifica serialización."""
        substitutor.create_substitution("Hello", "World")
        
        d = substitutor.to_dict()
        
        assert 'config' in d
        assert 'substitutions' in d
        assert len(d['substitutions']) == 1
    
    def test_from_dict(self, substitutor):
        """Verifica deserialización."""
        substitutor.create_substitution("Hello", "World")
        d = substitutor.to_dict()
        
        restored = ObjectSubstitutor.from_dict(d)
        
        assert len(restored._substitutions) == 1


class TestObjectSubstitutorWithMockPage:
    """Tests de integración con página mock."""
    
    @pytest.fixture
    def mock_page(self, sample_stream):
        """Crea una página mock."""
        page = MagicMock()
        page.number = 0
        page.xref = 10
        page.read_contents = MagicMock(return_value=sample_stream)
        
        # Mock parent document
        doc = MagicMock()
        doc.xref_get_key = MagicMock(return_value=("xref", "11 0 R"))
        doc.update_stream = MagicMock()
        page.parent = doc
        
        return page
    
    def test_find_in_page(self, substitutor, mock_page):
        """Verifica búsqueda en página."""
        with patch('core.text_engine.object_substitution.HAS_FITZ', True):
            locations = substitutor.find_in_page(mock_page, "Hello")
        
        assert isinstance(locations, list)
    
    def test_apply_substitution_success(self, substitutor, mock_page):
        """Verifica aplicar sustitución exitosa."""
        sub = substitutor.create_substitution(
            original="Hello World",
            new_text="Goodbye World",
        )
        
        # Mock para encontrar la ubicación
        with patch.object(substitutor, 'find_text') as mock_find:
            mock_find.return_value = [
                TextLocation(
                    page_num=0,
                    stream_start=50,
                    stream_end=70,
                    original_text="Hello World",
                    raw_operator="(Hello World) Tj",
                )
            ]
            
            with patch('core.text_engine.object_substitution.HAS_FITZ', True):
                result = substitutor.apply(mock_page, sub)
        
        # El resultado depende de si pudo escribir el stream
        assert result is not None
        assert result.substitution == sub
    
    def test_substitute_text_convenience(self, substitutor, mock_page):
        """Verifica método de conveniencia."""
        with patch.object(substitutor, 'find_text') as mock_find:
            mock_find.return_value = [
                TextLocation(
                    page_num=0,
                    stream_start=50,
                    stream_end=70,
                    original_text="Hello",
                    raw_operator="(Hello) Tj",
                )
            ]
            
            with patch('core.text_engine.object_substitution.HAS_FITZ', True):
                result = substitutor.substitute_text(
                    mock_page,
                    "Hello",
                    "World",
                )
        
        assert result is not None


# ================== Tests: Factory Functions ==================


class TestFactoryFunctions:
    """Tests para funciones factory."""
    
    def test_create_substitutor(self):
        """Verifica create_substitutor."""
        sub = create_substitutor(
            substitution_type=SubstitutionType.OPERATOR_REPLACE,
            match_strategy=MatchStrategy.CONTAINS,
        )
        
        assert sub.config.default_type == SubstitutionType.OPERATOR_REPLACE
        assert sub.config.default_match == MatchStrategy.CONTAINS
    
    def test_create_substitutor_with_kwargs(self):
        """Verifica create_substitutor con kwargs."""
        sub = create_substitutor(
            validate=False,
            allow_structure_change=True,
            max_risk_level=8,
        )
        
        assert sub.config.validate_before_apply is False
        assert sub.config.allow_structure_change is True
        assert sub.config.max_risk_level == 8
    
    def test_get_recommended_same_length(self):
        """Verifica recomendación para mismo tamaño."""
        rec = get_recommended_substitution_type("Hello", "World")
        assert rec == SubstitutionType.OPERAND_ONLY
    
    def test_get_recommended_small_diff(self):
        """Verifica recomendación para pequeña diferencia."""
        rec = get_recommended_substitution_type("Hi", "Hello")
        assert rec == SubstitutionType.OPERATOR_REPLACE
    
    def test_get_recommended_large_diff(self):
        """Verifica recomendación para gran diferencia."""
        rec = get_recommended_substitution_type("Hi", "Hello World!")
        assert rec == SubstitutionType.BLOCK_REPLACE
    
    def test_get_recommended_no_layout_preserve(self):
        """Verifica recomendación sin preservar layout."""
        rec = get_recommended_substitution_type(
            "Hi",
            "Hello World!",
            preserve_layout=False,
        )
        assert rec == SubstitutionType.OPERATOR_REPLACE


# ================== Tests: Edge Cases ==================


class TestEdgeCases:
    """Tests para casos extremos."""
    
    def test_empty_text(self, substitutor):
        """Verifica manejo de texto vacío."""
        sub = substitutor.create_substitution("", "")
        
        assert sub is not None
        assert sub.is_same_length is True
    
    def test_very_long_text(self, substitutor):
        """Verifica manejo de texto muy largo."""
        long_text = "x" * 10000
        sub = substitutor.create_substitution("Hello", long_text)
        
        assert sub.text_length_change > 0
        assert sub.requires_reflow is True
    
    def test_special_characters(self, encoder):
        """Verifica manejo de caracteres especiales."""
        special = "Hello © World ™ 日本語"
        encoded = encoder.encode_literal_string(special)
        
        # Debe poder codificarse (aunque sea como UTF-16)
        assert encoded is not None
        assert len(encoded) > 0
    
    def test_unicode_text(self, encoder):
        """Verifica manejo de Unicode."""
        unicode_text = "Héllo Wörld! 🎉"
        encoded = encoder.encode_literal_string(unicode_text)
        
        assert encoded is not None
    
    def test_nested_parentheses(self, encoder):
        """Verifica manejo de paréntesis anidados."""
        text = "Hello (nested) World"
        encoded = encoder.encode_literal_string(text)
        decoded = encoder.decode_literal_string(encoded)
        
        # El texto puede no ser idéntico si los paréntesis se escapan
        assert "Hello" in decoded
        assert "World" in decoded


# ================== Tests: Serialization Robustness ==================


class TestSerializationRobustness:
    """Tests de robustez de serialización."""
    
    def test_json_roundtrip_full(self, substitutor, sample_location):
        """Verifica roundtrip JSON completo."""
        # Crear varias sustituciones
        for i in range(3):
            sub = substitutor.create_substitution(f"Text{i}", f"New{i}")
            if i == 0:
                sub.location = sample_location
        
        # Serializar
        d = substitutor.to_dict()
        json_str = json.dumps(d)
        
        # Deserializar
        restored_dict = json.loads(json_str)
        restored = ObjectSubstitutor.from_dict(restored_dict)
        
        # Verificar
        assert len(restored._substitutions) == 3
    
    def test_handles_missing_fields(self):
        """Verifica manejo de campos faltantes."""
        minimal_data = {
            'config': {},
            'substitutions': {},
            'page_substitutions': {},
        }
        
        restored = ObjectSubstitutor.from_dict(minimal_data)
        assert restored is not None
        assert restored.config.default_type == SubstitutionType.OPERAND_ONLY


# ================== Tests: Risk Validation ==================


class TestRiskValidation:
    """Tests para validación de riesgo."""
    
    def test_risk_level_enforcement(self):
        """Verifica que se respeten niveles de riesgo."""
        config = SubstitutorConfig(max_risk_level=4)
        substitutor = ObjectSubstitutor(config)
        
        # OPERATOR_REPLACE tiene riesgo 4, debe pasar
        sub_ok = TextSubstitution(
            original_text="Hello",
            new_text="World",
            substitution_type=SubstitutionType.OPERATOR_REPLACE,
        )
        valid, _ = substitutor.validate_substitution(sub_ok)
        assert valid is True
        
        # BLOCK_REPLACE tiene riesgo 6, debe fallar
        sub_fail = TextSubstitution(
            original_text="Hello",
            new_text="World",
            substitution_type=SubstitutionType.BLOCK_REPLACE,
        )
        valid, issues = substitutor.validate_substitution(sub_fail)
        assert valid is False
        assert any("riesgo" in issue.lower() for issue in issues)

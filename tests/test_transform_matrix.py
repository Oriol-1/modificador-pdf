"""
Tests para TransformMatrix - Matrices de transformación PDF.

Cobertura:
- Creación y factory methods
- Operaciones matriciales (multiplicación, inversa)
- Transformación de puntos y bboxes
- Propiedades y decomposición
- Comparaciones y serialización
"""

import pytest
import math
from core.text_engine.transform_matrix import (
    TransformMatrix,
    TransformationType,
    TextTransformInfo,
    matrix_from_pdf_array,
    compose_matrices,
    interpolate_matrices,
    extract_rotation_angle,
    create_text_matrix,
)


# ============================================================================
# Test Class: TransformMatrix Creation
# ============================================================================

class TestTransformMatrixCreation:
    """Tests para creación de matrices."""
    
    def test_identity_matrix(self):
        """Test matriz identidad."""
        m = TransformMatrix.identity()
        assert m.a == 1.0
        assert m.b == 0.0
        assert m.c == 0.0
        assert m.d == 1.0
        assert m.e == 0.0
        assert m.f == 0.0
        assert m.is_identity
    
    def test_default_constructor_is_identity(self):
        """Test que constructor por defecto es identidad."""
        m = TransformMatrix()
        assert m.is_identity
    
    def test_from_tuple(self):
        """Test creación desde tupla."""
        t = (2.0, 0.5, -0.5, 2.0, 100.0, 200.0)
        m = TransformMatrix.from_tuple(t)
        assert m.a == 2.0
        assert m.b == 0.5
        assert m.c == -0.5
        assert m.d == 2.0
        assert m.e == 100.0
        assert m.f == 200.0
    
    def test_from_tuple_invalid_length(self):
        """Test error con tupla de longitud incorrecta."""
        with pytest.raises(ValueError):
            TransformMatrix.from_tuple((1, 2, 3))
    
    def test_from_list(self):
        """Test creación desde lista."""
        lst = [1.5, 0.0, 0.0, 1.5, 50.0, 50.0]
        m = TransformMatrix.from_list(lst)
        assert m.a == 1.5
        assert m.e == 50.0
    
    def test_from_list_invalid_length(self):
        """Test error con lista de longitud incorrecta."""
        with pytest.raises(ValueError):
            TransformMatrix.from_list([1, 2, 3, 4, 5])
    
    def test_translation_matrix(self):
        """Test creación de matriz de traslación."""
        m = TransformMatrix.translation(100.0, 200.0)
        assert m.a == 1.0
        assert m.d == 1.0
        assert m.e == 100.0
        assert m.f == 200.0
    
    def test_scaling_matrix_uniform(self):
        """Test escala uniforme."""
        m = TransformMatrix.scaling(2.0)
        assert m.a == 2.0
        assert m.d == 2.0
        assert m.b == 0.0
        assert m.c == 0.0
    
    def test_scaling_matrix_non_uniform(self):
        """Test escala no uniforme."""
        m = TransformMatrix.scaling(2.0, 0.5)
        assert m.a == 2.0
        assert m.d == 0.5
    
    def test_rotation_matrix_90_degrees(self):
        """Test rotación de 90 grados."""
        m = TransformMatrix.rotation(90.0)
        assert abs(m.a) < 1e-10  # cos(90) ≈ 0
        assert abs(m.b - 1.0) < 1e-10  # sin(90) = 1
        assert abs(m.c + 1.0) < 1e-10  # -sin(90) = -1
        assert abs(m.d) < 1e-10  # cos(90) ≈ 0
    
    def test_rotation_matrix_45_degrees(self):
        """Test rotación de 45 grados."""
        m = TransformMatrix.rotation(45.0)
        expected = math.sqrt(2) / 2
        assert abs(m.a - expected) < 1e-10
        assert abs(m.b - expected) < 1e-10
    
    def test_rotation_with_center(self):
        """Test rotación alrededor de un punto."""
        m = TransformMatrix.rotation(90.0, cx=50.0, cy=50.0)
        # Punto (100, 50) debería ir a (50, 100)
        x, y = m.transform_point(100.0, 50.0)
        assert abs(x - 50.0) < 1e-6
        assert abs(y - 100.0) < 1e-6
    
    def test_skewing_matrix(self):
        """Test matriz de inclinación."""
        m = TransformMatrix.skewing(45.0, 0.0)
        assert m.a == 1.0
        assert m.d == 1.0
        assert abs(m.c - 1.0) < 1e-10  # tan(45) = 1
        assert m.b == 0.0


# ============================================================================
# Test Class: Matrix Conversions
# ============================================================================

class TestMatrixConversions:
    """Tests para conversiones de formato."""
    
    def test_to_tuple(self):
        """Test conversión a tupla."""
        m = TransformMatrix(1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
        t = m.to_tuple()
        assert t == (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
    
    def test_to_list(self):
        """Test conversión a lista."""
        m = TransformMatrix(1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
        lst = m.to_list()
        assert lst == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    
    def test_to_dict(self):
        """Test conversión a diccionario."""
        m = TransformMatrix(1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
        d = m.to_dict()
        assert d['a'] == 1.0
        assert d['f'] == 6.0
    
    def test_roundtrip_tuple(self):
        """Test ida y vuelta con tupla."""
        original = TransformMatrix(1.5, 0.5, -0.5, 1.5, 100.0, 200.0)
        t = original.to_tuple()
        restored = TransformMatrix.from_tuple(t)
        assert original == restored


# ============================================================================
# Test Class: Matrix Operations
# ============================================================================

class TestMatrixOperations:
    """Tests para operaciones matriciales."""
    
    def test_multiply_identity(self):
        """Test multiplicar por identidad."""
        m = TransformMatrix(2.0, 0.0, 0.0, 2.0, 100.0, 100.0)
        identity = TransformMatrix.identity()
        result = m.multiply(identity)
        assert result == m
    
    def test_multiply_scaling(self):
        """Test multiplicación de escalas."""
        m1 = TransformMatrix.scaling(2.0)
        m2 = TransformMatrix.scaling(3.0)
        result = m1.multiply(m2)
        assert result.a == 6.0  # 2 * 3
        assert result.d == 6.0
    
    def test_multiply_translation(self):
        """Test multiplicación de traslaciones."""
        m1 = TransformMatrix.translation(100.0, 0.0)
        m2 = TransformMatrix.translation(0.0, 100.0)
        result = m1.multiply(m2)
        assert result.e == 100.0
        assert result.f == 100.0
    
    def test_matmul_operator(self):
        """Test operador @ para multiplicación."""
        m1 = TransformMatrix.scaling(2.0)
        m2 = TransformMatrix.translation(50.0, 50.0)
        result = m1 @ m2
        expected = m1.multiply(m2)
        assert result == expected
    
    def test_concat(self):
        """Test concatenación (orden inverso)."""
        m1 = TransformMatrix.scaling(2.0)
        m2 = TransformMatrix.translation(50.0, 50.0)
        result = m1.concat(m2)
        # concat aplica m2 primero, luego m1
        # Esto significa que el punto se traslada primero, luego se escala
        x, y = result.transform_point(0.0, 0.0)
        # m2 traslada (0,0) a (50,50), m1 escala a (100,100)
        assert abs(x - 100.0) < 1e-6
        assert abs(y - 100.0) < 1e-6
    
    def test_inverse_identity(self):
        """Test inversa de identidad."""
        m = TransformMatrix.identity()
        inv = m.inverse()
        assert inv is not None
        assert inv.is_identity
    
    def test_inverse_scaling(self):
        """Test inversa de escala."""
        m = TransformMatrix.scaling(2.0)
        inv = m.inverse()
        assert inv is not None
        assert abs(inv.a - 0.5) < 1e-10
        assert abs(inv.d - 0.5) < 1e-10
    
    def test_inverse_translation(self):
        """Test inversa de traslación."""
        m = TransformMatrix.translation(100.0, 200.0)
        inv = m.inverse()
        assert inv is not None
        assert abs(inv.e + 100.0) < 1e-10
        assert abs(inv.f + 200.0) < 1e-10
    
    def test_inverse_multiply_gives_identity(self):
        """Test que M * M^-1 = I."""
        m = TransformMatrix(2.0, 0.5, -0.5, 2.0, 100.0, 200.0)
        inv = m.inverse()
        assert inv is not None
        result = m.multiply(inv)
        assert result.is_identity
    
    def test_inverse_singular_matrix(self):
        """Test que matriz singular no tiene inversa."""
        m = TransformMatrix(1.0, 0.0, 1.0, 0.0, 0.0, 0.0)  # det = 0
        inv = m.inverse()
        assert inv is None


# ============================================================================
# Test Class: Point Transformation
# ============================================================================

class TestPointTransformation:
    """Tests para transformación de puntos."""
    
    def test_transform_point_identity(self):
        """Test transformar punto con identidad."""
        m = TransformMatrix.identity()
        x, y = m.transform_point(100.0, 200.0)
        assert x == 100.0
        assert y == 200.0
    
    def test_transform_point_translation(self):
        """Test traslación de punto."""
        m = TransformMatrix.translation(50.0, 100.0)
        x, y = m.transform_point(100.0, 100.0)
        assert x == 150.0
        assert y == 200.0
    
    def test_transform_point_scaling(self):
        """Test escala de punto."""
        m = TransformMatrix.scaling(2.0)
        x, y = m.transform_point(50.0, 100.0)
        assert x == 100.0
        assert y == 200.0
    
    def test_transform_point_rotation(self):
        """Test rotación de punto."""
        m = TransformMatrix.rotation(90.0)
        x, y = m.transform_point(100.0, 0.0)
        assert abs(x) < 1e-10
        assert abs(y - 100.0) < 1e-10
    
    def test_transform_points_list(self):
        """Test transformar lista de puntos."""
        m = TransformMatrix.translation(10.0, 20.0)
        points = [(0.0, 0.0), (100.0, 100.0)]
        result = m.transform_points(points)
        assert result[0] == (10.0, 20.0)
        assert result[1] == (110.0, 120.0)
    
    def test_transform_distance(self):
        """Test transformar distancia (sin traslación)."""
        m = TransformMatrix(2.0, 0.0, 0.0, 3.0, 1000.0, 1000.0)
        dx, dy = m.transform_distance(10.0, 10.0)
        assert dx == 20.0  # Solo escala, ignora traslación
        assert dy == 30.0
    
    def test_transform_bbox(self):
        """Test transformar bounding box."""
        m = TransformMatrix.translation(100.0, 100.0)
        bbox = (0.0, 0.0, 50.0, 50.0)
        result = m.transform_bbox(bbox)
        assert result == (100.0, 100.0, 150.0, 150.0)
    
    def test_transform_bbox_with_rotation(self):
        """Test transformar bbox con rotación (bbox crece)."""
        m = TransformMatrix.rotation(45.0)
        bbox = (0.0, 0.0, 100.0, 0.0)  # Línea horizontal
        result = m.transform_bbox(bbox)
        # El bbox resultante debe contener todos los puntos transformados
        # Con rotación de 45°, el ancho proyectado es mayor
        assert result[2] > result[0]


# ============================================================================
# Test Class: Chainable Methods
# ============================================================================

class TestChainableMethods:
    """Tests para métodos encadenables."""
    
    def test_chain_translate(self):
        """Test encadenar translate."""
        m = TransformMatrix.identity()
        m = m.translate(100.0, 200.0)
        assert m.e == 100.0
        assert m.f == 200.0
    
    def test_chain_scale(self):
        """Test encadenar scale."""
        m = TransformMatrix.identity()
        m = m.scale(2.0)
        assert m.a == 2.0
        assert m.d == 2.0
    
    def test_chain_rotate(self):
        """Test encadenar rotate."""
        m = TransformMatrix.identity()
        m = m.rotate(45.0)
        assert m.has_rotation
    
    def test_chain_multiple_operations(self):
        """Test encadenar múltiples operaciones."""
        m = (TransformMatrix.identity()
             .scale(2.0)
             .rotate(45.0)
             .translate(100.0, 100.0))
        
        assert m.has_scale
        assert m.has_rotation


# ============================================================================
# Test Class: Properties
# ============================================================================

class TestMatrixProperties:
    """Tests para propiedades de matriz."""
    
    def test_determinant_identity(self):
        """Test determinante de identidad."""
        m = TransformMatrix.identity()
        assert m.determinant == 1.0
    
    def test_determinant_scaling(self):
        """Test determinante de escala."""
        m = TransformMatrix.scaling(2.0, 3.0)
        assert m.determinant == 6.0  # 2 * 3
    
    def test_is_invertible(self):
        """Test is_invertible."""
        m = TransformMatrix.scaling(2.0)
        assert m.is_invertible
        
        singular = TransformMatrix(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        assert not singular.is_invertible
    
    def test_scale_x_y(self):
        """Test propiedades scale_x y scale_y."""
        m = TransformMatrix.scaling(2.0, 3.0)
        assert abs(m.scale_x - 2.0) < 1e-10
        assert abs(m.scale_y - 3.0) < 1e-10
    
    def test_rotation_angle(self):
        """Test propiedad rotation_angle."""
        m = TransformMatrix.rotation(45.0)
        assert abs(m.rotation_angle - 45.0) < 1e-6
    
    def test_translation_offset_property(self):
        """Test propiedad translation_offset."""
        m = TransformMatrix.translation(100.0, 200.0)
        assert m.translation_offset == (100.0, 200.0)
    
    def test_has_rotation(self):
        """Test has_rotation."""
        m1 = TransformMatrix.rotation(30.0)
        assert m1.has_rotation
        
        m2 = TransformMatrix.scaling(2.0)
        assert not m2.has_rotation
    
    def test_has_scale(self):
        """Test has_scale."""
        m1 = TransformMatrix.scaling(1.5)
        assert m1.has_scale
        
        m2 = TransformMatrix.translation(100.0, 100.0)
        assert not m2.has_scale
    
    def test_has_skew(self):
        """Test has_skew."""
        m1 = TransformMatrix.skewing(30.0)
        assert m1.has_skew
        
        m2 = TransformMatrix.rotation(30.0)
        assert not m2.has_skew
    
    def test_transformation_type_identity(self):
        """Test tipo de transformación: identidad."""
        m = TransformMatrix.identity()
        assert m.transformation_type == TransformationType.IDENTITY
    
    def test_transformation_type_translation(self):
        """Test tipo de transformación: traslación."""
        m = TransformMatrix.translation(100.0, 100.0)
        assert m.transformation_type == TransformationType.TRANSLATION
    
    def test_transformation_type_scale(self):
        """Test tipo de transformación: escala."""
        m = TransformMatrix.scaling(2.0)
        assert m.transformation_type == TransformationType.SCALE
    
    def test_transformation_type_rotation(self):
        """Test tipo de transformación: rotación."""
        m = TransformMatrix.rotation(45.0)
        assert m.transformation_type == TransformationType.ROTATION
    
    def test_transformation_type_skew(self):
        """Test tipo de transformación: inclinación."""
        m = TransformMatrix.skewing(30.0, 0.0)
        assert m.transformation_type == TransformationType.SKEW


# ============================================================================
# Test Class: Decomposition
# ============================================================================

class TestMatrixDecomposition:
    """Tests para decomposición de matrices."""
    
    def test_decompose_identity(self):
        """Test decomposición de identidad."""
        m = TransformMatrix.identity()
        d = m.decompose()
        assert d['translation'] == (0.0, 0.0)
        assert abs(d['rotation']) < 1e-6
        assert abs(d['scale'][0] - 1.0) < 1e-6
        assert abs(d['scale'][1] - 1.0) < 1e-6
    
    def test_decompose_translation(self):
        """Test decomposición de traslación."""
        m = TransformMatrix.translation(100.0, 200.0)
        d = m.decompose()
        assert d['translation'] == (100.0, 200.0)
    
    def test_decompose_scaling(self):
        """Test decomposición de escala."""
        m = TransformMatrix.scaling(2.0, 3.0)
        d = m.decompose()
        assert abs(d['scale'][0] - 2.0) < 1e-6
        assert abs(d['scale'][1] - 3.0) < 1e-6
    
    def test_decompose_rotation(self):
        """Test decomposición de rotación."""
        m = TransformMatrix.rotation(45.0)
        d = m.decompose()
        assert abs(d['rotation'] - 45.0) < 1e-6


# ============================================================================
# Test Class: Comparison and Hashing
# ============================================================================

class TestMatrixComparison:
    """Tests para comparación de matrices."""
    
    def test_is_close_identical(self):
        """Test is_close con matrices idénticas."""
        m1 = TransformMatrix(1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
        m2 = TransformMatrix(1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
        assert m1.is_close(m2)
    
    def test_is_close_within_tolerance(self):
        """Test is_close dentro de tolerancia."""
        m1 = TransformMatrix(1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        m2 = TransformMatrix(1.0 + 1e-8, 0.0, 0.0, 1.0, 0.0, 0.0)
        assert m1.is_close(m2)
    
    def test_is_close_outside_tolerance(self):
        """Test is_close fuera de tolerancia."""
        m1 = TransformMatrix(1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        m2 = TransformMatrix(2.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        assert not m1.is_close(m2)
    
    def test_equality_operator(self):
        """Test operador ==."""
        m1 = TransformMatrix(1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
        m2 = TransformMatrix(1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
        assert m1 == m2
    
    def test_hash_equal_matrices(self):
        """Test hash de matrices iguales."""
        m1 = TransformMatrix(1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
        m2 = TransformMatrix(1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
        assert hash(m1) == hash(m2)
    
    def test_repr(self):
        """Test __repr__."""
        m = TransformMatrix(1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
        r = repr(m)
        assert "TransformMatrix" in r
        assert "1.0000" in r
    
    def test_str(self):
        """Test __str__."""
        m = TransformMatrix(1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
        s = str(m)
        assert "[" in s and "]" in s


# ============================================================================
# Test Class: TextTransformInfo
# ============================================================================

class TestTextTransformInfo:
    """Tests para TextTransformInfo."""
    
    def test_default_creation(self):
        """Test creación por defecto."""
        info = TextTransformInfo()
        assert info.ctm.is_identity
        assert info.text_matrix.is_identity
        assert info.font_size == 12.0
        assert info.horizontal_scale == 100.0
    
    def test_combined_matrix(self):
        """Test matriz combinada."""
        info = TextTransformInfo(
            ctm=TransformMatrix.scaling(2.0),
            text_matrix=TransformMatrix.translation(100.0, 100.0)
        )
        combined = info.combined_matrix
        # text_matrix se aplica primero, luego ctm
        x, y = combined.transform_point(0.0, 0.0)
        assert abs(x - 200.0) < 1e-6  # 100 * 2
        assert abs(y - 200.0) < 1e-6
    
    def test_effective_font_size(self):
        """Test tamaño de fuente efectivo."""
        info = TextTransformInfo(
            ctm=TransformMatrix.scaling(2.0),
            font_size=12.0
        )
        assert abs(info.effective_font_size - 24.0) < 1e-6
    
    def test_effective_horizontal_scale(self):
        """Test escala horizontal efectiva."""
        info = TextTransformInfo(
            horizontal_scale=50.0  # 50%
        )
        assert abs(info.effective_horizontal_scale - 0.5) < 1e-6
    
    def test_is_rotated(self):
        """Test detección de rotación."""
        info1 = TextTransformInfo(text_matrix=TransformMatrix.rotation(10.0))
        assert info1.is_rotated
        
        info2 = TextTransformInfo()
        assert not info2.is_rotated
    
    def test_is_mirrored(self):
        """Test detección de espejo."""
        info = TextTransformInfo(ctm=TransformMatrix.scaling(-1.0, 1.0))
        assert info.is_mirrored
    
    def test_get_glyph_width(self):
        """Test cálculo de ancho de glifo."""
        info = TextTransformInfo(
            horizontal_scale=200.0  # 200%
        )
        width = info.get_glyph_width(10.0)
        assert abs(width - 20.0) < 1e-6
    
    def test_to_dict_and_from_dict(self):
        """Test serialización ida y vuelta."""
        original = TextTransformInfo(
            ctm=TransformMatrix.scaling(2.0),
            text_matrix=TransformMatrix.translation(50.0, 50.0),
            font_size=14.0,
            horizontal_scale=110.0
        )
        d = original.to_dict()
        restored = TextTransformInfo.from_dict(d)
        
        assert restored.font_size == original.font_size
        assert restored.horizontal_scale == original.horizontal_scale


# ============================================================================
# Test Class: Utility Functions
# ============================================================================

class TestUtilityFunctions:
    """Tests para funciones utilitarias."""
    
    def test_matrix_from_pdf_array(self):
        """Test creación desde array PDF."""
        arr = [1.0, 0.0, 0.0, 1.0, 100.0, 200.0]
        m = matrix_from_pdf_array(arr)
        assert m.e == 100.0
        assert m.f == 200.0
    
    def test_matrix_from_pdf_array_invalid(self):
        """Test error con array inválido."""
        with pytest.raises(ValueError):
            matrix_from_pdf_array([1, 2, 3])
    
    def test_compose_matrices_empty(self):
        """Test composición de lista vacía."""
        result = compose_matrices()
        assert result.is_identity
    
    def test_compose_matrices_single(self):
        """Test composición de una matriz."""
        m = TransformMatrix.scaling(2.0)
        result = compose_matrices(m)
        assert result == m
    
    def test_compose_matrices_multiple(self):
        """Test composición de múltiples matrices."""
        m1 = TransformMatrix.scaling(2.0)
        m2 = TransformMatrix.translation(100.0, 100.0)
        result = compose_matrices(m1, m2)
        expected = m1.multiply(m2)
        assert result == expected
    
    def test_interpolate_matrices_start(self):
        """Test interpolación en t=0."""
        m1 = TransformMatrix.identity()
        m2 = TransformMatrix.translation(100.0, 100.0)
        result = interpolate_matrices(m1, m2, 0.0)
        assert result == m1
    
    def test_interpolate_matrices_end(self):
        """Test interpolación en t=1."""
        m1 = TransformMatrix.identity()
        m2 = TransformMatrix.translation(100.0, 100.0)
        result = interpolate_matrices(m1, m2, 1.0)
        assert result == m2
    
    def test_interpolate_matrices_middle(self):
        """Test interpolación en t=0.5."""
        m1 = TransformMatrix.identity()
        m2 = TransformMatrix.translation(100.0, 100.0)
        result = interpolate_matrices(m1, m2, 0.5)
        assert abs(result.e - 50.0) < 1e-6
        assert abs(result.f - 50.0) < 1e-6
    
    def test_interpolate_matrices_clamp(self):
        """Test que t se limita a [0, 1]."""
        m1 = TransformMatrix.identity()
        m2 = TransformMatrix.translation(100.0, 100.0)
        
        result_below = interpolate_matrices(m1, m2, -0.5)
        assert result_below == m1
        
        result_above = interpolate_matrices(m1, m2, 1.5)
        assert result_above == m2
    
    def test_extract_rotation_angle(self):
        """Test extracción de ángulo de rotación."""
        m = TransformMatrix.rotation(60.0)
        angle = extract_rotation_angle(m)
        assert abs(angle - 60.0) < 1e-6
    
    def test_create_text_matrix_basic(self):
        """Test creación de matriz de texto básica."""
        m = create_text_matrix(font_size=12.0, x=100.0, y=200.0)
        assert m.e == 100.0
        assert m.f == 200.0
    
    def test_create_text_matrix_with_scale(self):
        """Test matriz de texto con escala horizontal."""
        m = create_text_matrix(font_size=12.0, horizontal_scale=200.0)
        # horizontal_scale 200% = factor 2.0
        assert abs(m.a - 2.0) < 1e-6
    
    def test_create_text_matrix_with_rotation(self):
        """Test matriz de texto con rotación."""
        m = create_text_matrix(font_size=12.0, rotation=45.0)
        assert m.has_rotation


# ============================================================================
# Test Class: Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests para casos límite."""
    
    def test_very_small_values(self):
        """Test con valores muy pequeños."""
        m = TransformMatrix(1e-10, 0.0, 0.0, 1e-10, 0.0, 0.0)
        assert not m.is_identity
        assert not m.is_invertible  # Determinante ≈ 0
    
    def test_very_large_values(self):
        """Test con valores muy grandes."""
        m = TransformMatrix(1e10, 0.0, 0.0, 1e10, 1e10, 1e10)
        inv = m.inverse()
        assert inv is not None
        result = m.multiply(inv)
        assert result.is_identity
    
    def test_negative_scaling(self):
        """Test escala negativa (espejo)."""
        m = TransformMatrix.scaling(-1.0, 1.0)
        assert m.determinant < 0
        # Transformar punto
        x, y = m.transform_point(100.0, 0.0)
        assert x == -100.0
        assert y == 0.0
    
    def test_zero_translation(self):
        """Test traslación cero."""
        m = TransformMatrix.translation(0.0, 0.0)
        assert m.is_identity
    
    def test_full_rotation_360(self):
        """Test rotación completa de 360°."""
        m = TransformMatrix.rotation(360.0)
        assert m.is_identity
    
    def test_rotation_negative(self):
        """Test rotación negativa."""
        m1 = TransformMatrix.rotation(-45.0)
        m2 = TransformMatrix.rotation(315.0)
        # Deberían ser equivalentes
        assert m1.is_close(m2, tolerance=1e-6)

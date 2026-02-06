"""
TransformMatrix - Operaciones con matrices de transformación PDF.

Este módulo proporciona clases para trabajar con las matrices de
transformación 2D usadas en PDF:

- CTM (Current Transformation Matrix): Transformación del espacio de usuario
- Text Matrix (Tm): Transformación específica del texto
- Glyph Space: Espacio de coordenadas de glifos

Una matriz de transformación PDF es una matriz 3x3 representada por 6 valores:
    [a  b  0]
    [c  d  0]
    [e  f  1]

Donde:
    - a, d: Escala en X e Y
    - b, c: Rotación/inclinación
    - e, f: Traslación

Referencia: PDF 1.7 Specification, Section 4.2.2 - Common Transformations
"""

from dataclasses import dataclass, field
from typing import Tuple, Optional, List, Dict, Any
from enum import Enum
import math


class TransformationType(Enum):
    """Tipos de transformación identificables."""
    IDENTITY = "identity"           # Sin transformación
    TRANSLATION = "translation"     # Solo traslación
    SCALE = "scale"                 # Solo escala
    ROTATION = "rotation"           # Solo rotación
    SCALE_ROTATION = "scale_rotation"  # Escala + rotación
    SKEW = "skew"                   # Inclinación
    GENERAL = "general"             # Transformación general


@dataclass
class TransformMatrix:
    """
    Matriz de transformación 2D para PDF.
    
    Representa una matriz de transformación afín 2D:
        [a  b  0]
        [c  d  0]
        [e  f  1]
    
    Attributes:
        a: Escala X / Coseno de rotación
        b: Seno de rotación (componente Y de la rotación)
        c: Seno negativo de rotación (componente X de la rotación) / Skew X
        d: Escala Y / Coseno de rotación
        e: Traslación X
        f: Traslación Y
    
    Usage:
        >>> m = TransformMatrix.identity()
        >>> m = m.scale(2.0, 1.5)
        >>> m = m.rotate(45)
        >>> point = m.transform_point(100, 100)
    """
    a: float = 1.0  # Scale X / cos(rotation)
    b: float = 0.0  # sin(rotation)
    c: float = 0.0  # -sin(rotation) / skew X
    d: float = 1.0  # Scale Y / cos(rotation)
    e: float = 0.0  # Translation X
    f: float = 0.0  # Translation Y
    
    # === Factory Methods ===
    
    @classmethod
    def identity(cls) -> 'TransformMatrix':
        """Create an identity matrix (no transformation)."""
        return cls(1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    
    @classmethod
    def from_tuple(cls, t: Tuple[float, float, float, float, float, float]) -> 'TransformMatrix':
        """Create from a 6-element tuple (a, b, c, d, e, f)."""
        if len(t) != 6:
            raise ValueError(f"Expected 6 elements, got {len(t)}")
        return cls(a=t[0], b=t[1], c=t[2], d=t[3], e=t[4], f=t[5])
    
    @classmethod
    def from_list(cls, lst: List[float]) -> 'TransformMatrix':
        """Create from a 6-element list [a, b, c, d, e, f]."""
        if len(lst) != 6:
            raise ValueError(f"Expected 6 elements, got {len(lst)}")
        return cls(a=lst[0], b=lst[1], c=lst[2], d=lst[3], e=lst[4], f=lst[5])
    
    @classmethod
    def translation(cls, tx: float, ty: float) -> 'TransformMatrix':
        """Create a translation matrix."""
        return cls(1.0, 0.0, 0.0, 1.0, tx, ty)
    
    @classmethod
    def scaling(cls, sx: float, sy: Optional[float] = None) -> 'TransformMatrix':
        """
        Create a scaling matrix.
        
        Args:
            sx: Scale factor in X
            sy: Scale factor in Y (defaults to sx for uniform scaling)
        """
        if sy is None:
            sy = sx
        return cls(sx, 0.0, 0.0, sy, 0.0, 0.0)
    
    @classmethod
    def rotation(cls, angle_degrees: float, cx: float = 0.0, cy: float = 0.0) -> 'TransformMatrix':
        """
        Create a rotation matrix.
        
        Args:
            angle_degrees: Rotation angle in degrees (counterclockwise positive)
            cx: Center of rotation X (default 0)
            cy: Center of rotation Y (default 0)
        """
        rad = math.radians(angle_degrees)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        
        if cx == 0.0 and cy == 0.0:
            return cls(cos_a, sin_a, -sin_a, cos_a, 0.0, 0.0)
        
        # Rotation around point (cx, cy)
        # T(cx,cy) * R * T(-cx,-cy)
        return cls(
            cos_a,
            sin_a,
            -sin_a,
            cos_a,
            cx - cx * cos_a + cy * sin_a,
            cy - cx * sin_a - cy * cos_a
        )
    
    @classmethod
    def skewing(cls, skew_x_degrees: float, skew_y_degrees: float = 0.0) -> 'TransformMatrix':
        """
        Create a skewing (shear) matrix.
        
        Args:
            skew_x_degrees: Skew angle in X direction (degrees)
            skew_y_degrees: Skew angle in Y direction (degrees)
        """
        tan_x = math.tan(math.radians(skew_x_degrees))
        tan_y = math.tan(math.radians(skew_y_degrees))
        return cls(1.0, tan_y, tan_x, 1.0, 0.0, 0.0)
    
    # === Conversion ===
    
    def to_tuple(self) -> Tuple[float, float, float, float, float, float]:
        """Convert to tuple (a, b, c, d, e, f)."""
        return (self.a, self.b, self.c, self.d, self.e, self.f)
    
    def to_list(self) -> List[float]:
        """Convert to list [a, b, c, d, e, f]."""
        return [self.a, self.b, self.c, self.d, self.e, self.f]
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'a': self.a, 'b': self.b, 'c': self.c,
            'd': self.d, 'e': self.e, 'f': self.f
        }
    
    # === Matrix Operations ===
    
    def multiply(self, other: 'TransformMatrix') -> 'TransformMatrix':
        """
        Multiply this matrix by another: self * other.
        
        The result transforms a point by first applying 'other', then 'self'.
        """
        return TransformMatrix(
            a=self.a * other.a + self.b * other.c,
            b=self.a * other.b + self.b * other.d,
            c=self.c * other.a + self.d * other.c,
            d=self.c * other.b + self.d * other.d,
            e=self.e * other.a + self.f * other.c + other.e,
            f=self.e * other.b + self.f * other.d + other.f
        )
    
    def __matmul__(self, other: 'TransformMatrix') -> 'TransformMatrix':
        """Matrix multiplication operator: self @ other."""
        return self.multiply(other)
    
    def concat(self, other: 'TransformMatrix') -> 'TransformMatrix':
        """
        Concatenate with another matrix: other * self.
        
        This is the PDF concatenation order: the new transformation
        is applied after the existing one.
        """
        return other.multiply(self)
    
    def inverse(self) -> Optional['TransformMatrix']:
        """
        Compute the inverse matrix.
        
        Returns:
            Inverse matrix, or None if matrix is singular (det ≈ 0)
        """
        det = self.determinant
        
        if abs(det) < 1e-10:
            return None
        
        return TransformMatrix(
            a=self.d / det,
            b=-self.b / det,
            c=-self.c / det,
            d=self.a / det,
            e=(self.c * self.f - self.d * self.e) / det,
            f=(self.b * self.e - self.a * self.f) / det
        )
    
    # === Point Transformation ===
    
    def transform_point(self, x: float, y: float) -> Tuple[float, float]:
        """
        Transform a point (x, y) using this matrix.
        
        Returns:
            Transformed point (x', y')
        """
        return (
            self.a * x + self.c * y + self.e,
            self.b * x + self.d * y + self.f
        )
    
    def transform_points(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Transform a list of points."""
        return [self.transform_point(x, y) for x, y in points]
    
    def transform_distance(self, dx: float, dy: float) -> Tuple[float, float]:
        """
        Transform a distance vector (ignores translation).
        
        Useful for transforming dimensions, not positions.
        """
        return (
            self.a * dx + self.c * dy,
            self.b * dx + self.d * dy
        )
    
    def transform_bbox(
        self, 
        bbox: Tuple[float, float, float, float]
    ) -> Tuple[float, float, float, float]:
        """
        Transform a bounding box.
        
        Args:
            bbox: (x0, y0, x1, y1) bounding box
            
        Returns:
            Transformed bounding box (may be larger if rotated)
        """
        x0, y0, x1, y1 = bbox
        
        # Transform all four corners
        corners = [
            self.transform_point(x0, y0),
            self.transform_point(x1, y0),
            self.transform_point(x1, y1),
            self.transform_point(x0, y1)
        ]
        
        # Find bounding box of transformed corners
        xs = [c[0] for c in corners]
        ys = [c[1] for c in corners]
        
        return (min(xs), min(ys), max(xs), max(ys))
    
    # === Chainable Transformation Methods ===
    
    def translate(self, tx: float, ty: float) -> 'TransformMatrix':
        """Return a new matrix with translation applied."""
        return self.multiply(TransformMatrix.translation(tx, ty))
    
    def scale(self, sx: float, sy: Optional[float] = None) -> 'TransformMatrix':
        """Return a new matrix with scaling applied."""
        return self.multiply(TransformMatrix.scaling(sx, sy))
    
    def rotate(self, angle_degrees: float) -> 'TransformMatrix':
        """Return a new matrix with rotation applied."""
        return self.multiply(TransformMatrix.rotation(angle_degrees))
    
    def skew(self, skew_x: float, skew_y: float = 0.0) -> 'TransformMatrix':
        """Return a new matrix with skewing applied."""
        return self.multiply(TransformMatrix.skewing(skew_x, skew_y))
    
    # === Properties ===
    
    @property
    def determinant(self) -> float:
        """Calculate matrix determinant (a*d - b*c)."""
        return self.a * self.d - self.b * self.c
    
    @property
    def is_identity(self) -> bool:
        """Check if this is an identity matrix (no transformation)."""
        return (
            abs(self.a - 1.0) < 1e-6 and
            abs(self.b) < 1e-6 and
            abs(self.c) < 1e-6 and
            abs(self.d - 1.0) < 1e-6 and
            abs(self.e) < 1e-6 and
            abs(self.f) < 1e-6
        )
    
    @property
    def is_invertible(self) -> bool:
        """Check if this matrix can be inverted."""
        return abs(self.determinant) > 1e-10
    
    @property
    def scale_x(self) -> float:
        """Get the effective X scale factor."""
        return math.sqrt(self.a * self.a + self.b * self.b)
    
    @property
    def scale_y(self) -> float:
        """Get the effective Y scale factor."""
        return math.sqrt(self.c * self.c + self.d * self.d)
    
    @property
    def rotation_angle(self) -> float:
        """
        Get the rotation angle in degrees.
        
        Note: Only accurate if no skewing is applied.
        """
        return math.degrees(math.atan2(self.b, self.a))
    
    @property
    def translation_offset(self) -> Tuple[float, float]:
        """Get the translation component (e, f)."""
        return (self.e, self.f)
    
    @property
    def has_rotation(self) -> bool:
        """Check if matrix includes rotation."""
        return abs(self.b) > 1e-6 or abs(self.c) > 1e-6
    
    @property
    def has_scale(self) -> bool:
        """Check if matrix includes non-unit scaling."""
        # Use effective scale factors, not raw a/d values
        return abs(self.scale_x - 1.0) > 1e-6 or abs(self.scale_y - 1.0) > 1e-6
    
    @property
    def has_skew(self) -> bool:
        """
        Check if matrix includes skewing (non-orthogonal).
        
        Skew is detected when rotation components don't match
        the expected rotation pattern (b ≈ -c for pure rotation).
        """
        if not self.has_rotation:
            return False
        # For pure rotation: b ≈ -c (with same magnitude)
        return abs(self.b + self.c) > 1e-6
    
    @property
    def transformation_type(self) -> TransformationType:
        """Identify the type of transformation."""
        if self.is_identity:
            return TransformationType.IDENTITY
        
        if not self.has_rotation and not self.has_scale:
            return TransformationType.TRANSLATION
        
        if self.has_skew:
            return TransformationType.SKEW
        
        if self.has_rotation and not self.has_scale:
            return TransformationType.ROTATION
        
        if self.has_scale and not self.has_rotation:
            return TransformationType.SCALE
        
        if self.has_rotation and self.has_scale:
            return TransformationType.SCALE_ROTATION
        
        return TransformationType.GENERAL
    
    # === Decomposition ===
    
    def decompose(self) -> Dict[str, Any]:
        """
        Decompose the matrix into translation, rotation, scale, and skew.
        
        Returns:
            Dictionary with:
                - translation: (tx, ty)
                - rotation: angle in degrees
                - scale: (sx, sy)
                - skew: (skew_x, skew_y) in degrees
        """
        # Translation
        tx, ty = self.e, self.f
        
        # Scale
        sx = self.scale_x
        sy = self.scale_y
        
        # Check for flip (negative determinant)
        if self.determinant < 0:
            sx = -sx
        
        # Rotation
        rotation = math.degrees(math.atan2(self.b, self.a))
        
        # Skew (calculated from the matrix after removing rotation and scale)
        skew_x = 0.0
        skew_y = 0.0
        
        if abs(sx) > 1e-6 and abs(sy) > 1e-6:
            # Remove scale to isolate rotation + skew
            cos_r = self.a / sx
            sin_r = self.b / sx
            
            # Calculate skew from remaining component
            if abs(cos_r) > 1e-6:
                skew_x = math.degrees(math.atan2(
                    self.c / sy + sin_r,
                    cos_r
                ))
        
        return {
            'translation': (tx, ty),
            'rotation': rotation,
            'scale': (sx, sy),
            'skew': (skew_x, skew_y)
        }
    
    # === Comparison ===
    
    def is_close(self, other: 'TransformMatrix', tolerance: float = 1e-6) -> bool:
        """Check if two matrices are approximately equal."""
        return (
            abs(self.a - other.a) < tolerance and
            abs(self.b - other.b) < tolerance and
            abs(self.c - other.c) < tolerance and
            abs(self.d - other.d) < tolerance and
            abs(self.e - other.e) < tolerance and
            abs(self.f - other.f) < tolerance
        )
    
    def __eq__(self, other: object) -> bool:
        """Equality comparison with tolerance."""
        if not isinstance(other, TransformMatrix):
            return NotImplemented
        return self.is_close(other)
    
    def __hash__(self) -> int:
        """Hash based on rounded values."""
        return hash((
            round(self.a, 6), round(self.b, 6), round(self.c, 6),
            round(self.d, 6), round(self.e, 6), round(self.f, 6)
        ))
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"TransformMatrix(a={self.a:.4f}, b={self.b:.4f}, c={self.c:.4f}, "
            f"d={self.d:.4f}, e={self.e:.4f}, f={self.f:.4f})"
        )
    
    def __str__(self) -> str:
        """Human-readable matrix format."""
        return f"[{self.a:.3f} {self.b:.3f} {self.c:.3f} {self.d:.3f} {self.e:.3f} {self.f:.3f}]"


@dataclass
class TextTransformInfo:
    """
    Complete text transformation information extracted from PDF.
    
    Combines CTM and text matrix to provide full transformation context
    for text positioning and rendering.
    
    Attributes:
        ctm: Current Transformation Matrix (page-level)
        text_matrix: Text-specific matrix from Tm operator
        font_size: Original font size before transformation
        horizontal_scale: Tz value (100 = normal)
    """
    ctm: TransformMatrix = field(default_factory=TransformMatrix.identity)
    text_matrix: TransformMatrix = field(default_factory=TransformMatrix.identity)
    font_size: float = 12.0
    horizontal_scale: float = 100.0  # Percentage
    
    @property
    def combined_matrix(self) -> TransformMatrix:
        """
        Get the combined transformation matrix.
        
        Combined = text_matrix * ctm (text matrix applied first, then CTM)
        """
        return self.text_matrix.multiply(self.ctm)
    
    @property
    def effective_font_size(self) -> float:
        """
        Calculate effective font size after all transformations.
        
        Takes into account text matrix scaling and CTM.
        """
        # Font size is scaled by the Y component of the combined matrix
        combined = self.combined_matrix
        return self.font_size * combined.scale_y
    
    @property
    def effective_horizontal_scale(self) -> float:
        """
        Calculate effective horizontal scale.
        
        Combines Tz value with matrix scaling.
        """
        combined = self.combined_matrix
        return (self.horizontal_scale / 100.0) * combined.scale_x
    
    @property
    def text_rotation(self) -> float:
        """Get text rotation in degrees."""
        return self.combined_matrix.rotation_angle
    
    @property
    def is_rotated(self) -> bool:
        """Check if text is rotated."""
        return abs(self.text_rotation) > 0.5  # More than 0.5 degrees
    
    @property
    def is_scaled(self) -> bool:
        """Check if text is scaled non-uniformly."""
        combined = self.combined_matrix
        return abs(combined.scale_x - combined.scale_y) > 0.01
    
    @property
    def is_mirrored(self) -> bool:
        """Check if text is mirrored (negative determinant)."""
        return self.combined_matrix.determinant < 0
    
    def transform_point(self, x: float, y: float) -> Tuple[float, float]:
        """Transform a point from text space to page space."""
        return self.combined_matrix.transform_point(x, y)
    
    def get_glyph_width(self, width: float) -> float:
        """
        Calculate actual glyph width after transformations.
        
        Args:
            width: Original glyph width in text space
            
        Returns:
            Width in page coordinates
        """
        # Apply horizontal scale and matrix transformation
        scaled_width = width * (self.horizontal_scale / 100.0)
        dx, _ = self.combined_matrix.transform_distance(scaled_width, 0)
        return abs(dx)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'ctm': self.ctm.to_list(),
            'text_matrix': self.text_matrix.to_list(),
            'font_size': self.font_size,
            'horizontal_scale': self.horizontal_scale,
            'effective_font_size': self.effective_font_size,
            'text_rotation': self.text_rotation,
            'is_rotated': self.is_rotated,
            'is_scaled': self.is_scaled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextTransformInfo':
        """Create from dictionary."""
        return cls(
            ctm=TransformMatrix.from_list(data['ctm']),
            text_matrix=TransformMatrix.from_list(data['text_matrix']),
            font_size=data.get('font_size', 12.0),
            horizontal_scale=data.get('horizontal_scale', 100.0)
        )


# === Utility Functions ===

def matrix_from_pdf_array(arr: List[float]) -> TransformMatrix:
    """
    Create TransformMatrix from PDF matrix array.
    
    PDF uses column-major order: [a, b, c, d, e, f]
    """
    if len(arr) != 6:
        raise ValueError(f"PDF matrix must have 6 elements, got {len(arr)}")
    return TransformMatrix.from_list(arr)


def compose_matrices(*matrices: TransformMatrix) -> TransformMatrix:
    """
    Compose multiple matrices in order (left to right).
    
    Result = m1 * m2 * m3 * ...
    """
    if not matrices:
        return TransformMatrix.identity()
    
    result = matrices[0]
    for m in matrices[1:]:
        result = result.multiply(m)
    
    return result


def interpolate_matrices(
    m1: TransformMatrix,
    m2: TransformMatrix,
    t: float
) -> TransformMatrix:
    """
    Linear interpolation between two matrices.
    
    Args:
        m1: Start matrix (t=0)
        m2: End matrix (t=1)
        t: Interpolation factor [0, 1]
        
    Returns:
        Interpolated matrix
    """
    t = max(0.0, min(1.0, t))
    return TransformMatrix(
        a=m1.a + (m2.a - m1.a) * t,
        b=m1.b + (m2.b - m1.b) * t,
        c=m1.c + (m2.c - m1.c) * t,
        d=m1.d + (m2.d - m1.d) * t,
        e=m1.e + (m2.e - m1.e) * t,
        f=m1.f + (m2.f - m1.f) * t
    )


def extract_rotation_angle(matrix: TransformMatrix) -> float:
    """
    Extract rotation angle from a transformation matrix.
    
    Returns:
        Rotation in degrees, counterclockwise positive
    """
    return matrix.rotation_angle


def create_text_matrix(
    font_size: float,
    horizontal_scale: float = 100.0,
    x: float = 0.0,
    y: float = 0.0,
    rotation: float = 0.0
) -> TransformMatrix:
    """
    Create a typical text matrix for PDF.
    
    Args:
        font_size: Font size in points
        horizontal_scale: Horizontal scale percentage (100 = normal)
        x: X position
        y: Y position
        rotation: Rotation in degrees
        
    Returns:
        TransformMatrix suitable for Tm operator
    """
    # Start with font size scaling
    # Note: In PDF, font size is usually applied via Tf, not Tm
    # But Tm can include additional scaling
    sx = horizontal_scale / 100.0
    sy = 1.0
    
    # Create base matrix with scale
    m = TransformMatrix.scaling(sx, sy)
    
    # Apply rotation if needed
    if abs(rotation) > 0.001:
        m = m.rotate(rotation)
    
    # Apply translation
    m = TransformMatrix(m.a, m.b, m.c, m.d, x, y)
    
    return m

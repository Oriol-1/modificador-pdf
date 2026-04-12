"""Preprocesado de imágenes para mejorar la calidad del OCR.

Pipeline de 5 etapas:
1. Corrección de inclinación (deskew)
2. Reducción de ruido
3. Binarización adaptativa
4. Mejora de contraste (CLAHE)
5. Redimensionado a DPI óptimo
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple

import numpy as np

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

logger = logging.getLogger(__name__)


class PreprocessStep(Enum):
    """Etapas del pipeline de preprocesado."""
    DESKEW = "deskew"
    DENOISE = "denoise"
    BINARIZE = "binarize"
    CONTRAST = "contrast"
    RESCALE = "rescale"


@dataclass
class PreprocessConfig:
    """Configuración del pipeline de preprocesado.
    
    Attributes:
        deskew: Corregir inclinación automáticamente.
        denoise: Aplicar reducción de ruido.
        binarize: Convertir a blanco y negro.
        contrast: Mejorar contraste con CLAHE.
        target_dpi: DPI objetivo para redimensionado.
        current_dpi: DPI actual de la imagen (0 = auto-detectar).
        denoise_strength: Fuerza del filtro de ruido (1-20).
        binarize_block_size: Tamaño de bloque para binarización adaptativa.
        binarize_c: Constante de ajuste para binarización.
        clahe_clip_limit: Límite de contraste para CLAHE.
        clahe_grid_size: Tamaño de grilla para CLAHE.
    """
    deskew: bool = True
    denoise: bool = True
    binarize: bool = True
    contrast: bool = True
    target_dpi: int = 300
    current_dpi: int = 0
    denoise_strength: int = 10
    binarize_block_size: int = 11
    binarize_c: int = 2
    clahe_clip_limit: float = 2.0
    clahe_grid_size: Tuple[int, int] = (8, 8)


@dataclass
class PreprocessResult:
    """Resultado del preprocesado.
    
    Attributes:
        image: Imagen procesada como numpy array.
        skew_angle: Ángulo de inclinación detectado (grados).
        steps_applied: Lista de etapas aplicadas.
        original_size: Tamaño original (width, height).
        final_size: Tamaño final (width, height).
    """
    image: np.ndarray
    skew_angle: float = 0.0
    steps_applied: list = field(default_factory=list)
    original_size: Tuple[int, int] = (0, 0)
    final_size: Tuple[int, int] = (0, 0)


def _check_opencv():
    """Verifica que OpenCV está disponible."""
    if not HAS_OPENCV:
        raise ImportError(
            "OpenCV no está instalado. Instalar con: pip install opencv-python-headless"
        )


def detect_skew_angle(image: np.ndarray) -> float:
    """Detecta el ángulo de inclinación de una imagen de texto.
    
    Usa transformada de Hough para detectar líneas horizontales
    y calcular el ángulo predominante.
    
    Args:
        image: Imagen en escala de grises.
        
    Returns:
        Ángulo de inclinación en grados (-45 a 45).
    """
    _check_opencv()
    
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Detectar bordes
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # Transformada de Hough
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=100,
        minLineLength=gray.shape[1] // 4,
        maxLineGap=10
    )
    
    if lines is None or len(lines) == 0:
        return 0.0
    
    # Calcular ángulos de todas las líneas
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 - x1 == 0:
            continue
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        # Solo considerar líneas casi horizontales (-45 a 45 grados)
        if abs(angle) < 45:
            angles.append(angle)
    
    if not angles:
        return 0.0
    
    # Mediana es más robusta que la media
    return float(np.median(angles))


def apply_deskew(image: np.ndarray, angle: Optional[float] = None) -> Tuple[np.ndarray, float]:
    """Corrige la inclinación de una imagen.
    
    Args:
        image: Imagen de entrada.
        angle: Ángulo a corregir. Si es None, se auto-detecta.
        
    Returns:
        Tupla (imagen_corregida, ángulo_detectado).
    """
    _check_opencv()
    
    if angle is None:
        angle = detect_skew_angle(image)
    
    if abs(angle) < 0.3:
        # Inclinación despreciable
        return image.copy(), angle
    
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Calcular nuevo tamaño para no recortar
    cos = np.abs(matrix[0, 0])
    sin = np.abs(matrix[0, 1])
    new_w = int(h * sin + w * cos)
    new_h = int(h * cos + w * sin)
    matrix[0, 2] += (new_w - w) / 2
    matrix[1, 2] += (new_h - h) / 2
    
    # Color de fondo blanco para documentos
    result = cv2.warpAffine(
        image, matrix, (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255) if len(image.shape) == 3 else 255
    )
    
    logger.debug(f"Deskew aplicado: {angle:.2f}°")
    return result, angle


def apply_denoise(image: np.ndarray, strength: int = 10) -> np.ndarray:
    """Reduce el ruido de una imagen usando Non-Local Means.
    
    Args:
        image: Imagen de entrada.
        strength: Fuerza del filtro (1-20).
        
    Returns:
        Imagen con ruido reducido.
    """
    _check_opencv()
    strength = max(1, min(20, strength))
    
    if len(image.shape) == 3:
        return cv2.fastNlMeansDenoisingColored(image, None, strength, strength, 7, 21)
    else:
        return cv2.fastNlMeansDenoising(image, None, strength, 7, 21)


def apply_binarize(
    image: np.ndarray,
    block_size: int = 11,
    c: int = 2
) -> np.ndarray:
    """Binariza una imagen usando umbral adaptativo gaussiano.
    
    Args:
        image: Imagen de entrada.
        block_size: Tamaño de bloque para umbral adaptativo (debe ser impar).
        c: Constante de ajuste.
        
    Returns:
        Imagen binarizada (blanco y negro).
    """
    _check_opencv()
    
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Asegurar block_size impar
    if block_size % 2 == 0:
        block_size += 1
    block_size = max(3, block_size)
    
    return cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size, c
    )


def apply_contrast(
    image: np.ndarray,
    clip_limit: float = 2.0,
    grid_size: Tuple[int, int] = (8, 8)
) -> np.ndarray:
    """Mejora el contraste usando CLAHE.
    
    Args:
        image: Imagen de entrada.
        clip_limit: Límite de contraste.
        grid_size: Tamaño de grilla para el histograma local.
        
    Returns:
        Imagen con contraste mejorado.
    """
    _check_opencv()
    
    if len(image.shape) == 3:
        # Convertir a LAB, aplicar CLAHE al canal L
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0]
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=grid_size)
        lab[:, :, 0] = clahe.apply(l_channel)
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    else:
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=grid_size)
        return clahe.apply(image)


def apply_rescale(
    image: np.ndarray,
    current_dpi: int,
    target_dpi: int = 300
) -> np.ndarray:
    """Redimensiona la imagen al DPI objetivo.
    
    Args:
        image: Imagen de entrada.
        current_dpi: DPI actual de la imagen.
        target_dpi: DPI objetivo (por defecto 300).
        
    Returns:
        Imagen redimensionada.
    """
    _check_opencv()
    
    if current_dpi <= 0 or current_dpi == target_dpi:
        return image.copy()
    
    scale = target_dpi / current_dpi
    if abs(scale - 1.0) < 0.05:
        return image.copy()
    
    new_w = int(image.shape[1] * scale)
    new_h = int(image.shape[0] * scale)
    
    interpolation = cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
    result = cv2.resize(image, (new_w, new_h), interpolation=interpolation)
    
    logger.debug(f"Rescale: {current_dpi} → {target_dpi} DPI (factor {scale:.2f})")
    return result


def preprocess_image(
    image: np.ndarray,
    config: Optional[PreprocessConfig] = None
) -> PreprocessResult:
    """Ejecuta el pipeline completo de preprocesado.
    
    Args:
        image: Imagen de entrada como numpy array.
        config: Configuración del pipeline. Si es None, usa valores por defecto.
        
    Returns:
        PreprocessResult con la imagen procesada y metadata.
    """
    _check_opencv()
    
    if config is None:
        config = PreprocessConfig()
    
    original_h, original_w = image.shape[:2]
    result = PreprocessResult(
        image=image.copy(),
        original_size=(original_w, original_h)
    )
    
    # 1. Deskew
    if config.deskew:
        result.image, result.skew_angle = apply_deskew(result.image)
        result.steps_applied.append(PreprocessStep.DESKEW)
    
    # 2. Denoise
    if config.denoise:
        result.image = apply_denoise(result.image, config.denoise_strength)
        result.steps_applied.append(PreprocessStep.DENOISE)
    
    # 3. Contrast (antes de binarizar)
    if config.contrast:
        result.image = apply_contrast(
            result.image, config.clahe_clip_limit, config.clahe_grid_size
        )
        result.steps_applied.append(PreprocessStep.CONTRAST)
    
    # 4. Binarize
    if config.binarize:
        result.image = apply_binarize(
            result.image, config.binarize_block_size, config.binarize_c
        )
        result.steps_applied.append(PreprocessStep.BINARIZE)
    
    # 5. Rescale
    if config.target_dpi > 0 and config.current_dpi > 0:
        result.image = apply_rescale(
            result.image, config.current_dpi, config.target_dpi
        )
        result.steps_applied.append(PreprocessStep.RESCALE)
    
    final_h, final_w = result.image.shape[:2]
    result.final_size = (final_w, final_h)
    
    logger.info(
        f"Preprocesado completado: {len(result.steps_applied)} etapas, "
        f"{original_w}x{original_h} → {final_w}x{final_h}, "
        f"skew={result.skew_angle:.2f}°"
    )
    
    return result

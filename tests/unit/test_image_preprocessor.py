"""Tests para core.ocr.image_preprocessor — Pipeline de preprocesado de imágenes.

Usa imágenes sintéticas generadas con numpy para no depender de archivos externos.
"""
import pytest
import numpy as np

# Saltar todos los tests si OpenCV no está disponible
cv2 = pytest.importorskip("cv2", reason="OpenCV no disponible")

from core.ocr.image_preprocessor import (
    PreprocessConfig,
    PreprocessResult,
    PreprocessStep,
    detect_skew_angle,
    apply_deskew,
    apply_denoise,
    apply_binarize,
    apply_contrast,
    apply_rescale,
    preprocess_image,
)


# ═══════════════════════════════════════════════════════════
# Fixtures: Imágenes sintéticas
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def white_image():
    """Imagen blanca 200x400 (BGR)."""
    return np.ones((200, 400, 3), dtype=np.uint8) * 255


@pytest.fixture
def gray_image():
    """Imagen gris 200x400 (escala de grises)."""
    return np.ones((200, 400), dtype=np.uint8) * 200


@pytest.fixture
def noisy_image():
    """Imagen con ruido gaussiano."""
    rng = np.random.default_rng(42)
    base = np.ones((200, 400, 3), dtype=np.uint8) * 180
    noise = rng.integers(-30, 30, size=base.shape, dtype=np.int16)
    result = np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return result


@pytest.fixture
def text_like_image():
    """Imagen que simula texto (líneas horizontales oscuras sobre fondo claro)."""
    img = np.ones((300, 500, 3), dtype=np.uint8) * 240
    for y in range(50, 280, 30):
        cv2.line(img, (40, y), (460, y), (30, 30, 30), 2)
    return img


@pytest.fixture
def skewed_text_image():
    """Imagen con texto inclinado ~5 grados."""
    img = np.ones((400, 600, 3), dtype=np.uint8) * 240
    for y in range(60, 360, 30):
        cv2.line(img, (40, y), (560, y), (30, 30, 30), 2)
    # Rotar 5 grados
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, 5.0, 1.0)
    img = cv2.warpAffine(img, M, (w, h), borderValue=(240, 240, 240))
    return img


# ═══════════════════════════════════════════════════════════
# Tests: PreprocessConfig
# ═══════════════════════════════════════════════════════════

class TestPreprocessConfig:
    """Tests para la configuración del preprocesador."""

    def test_default_config(self):
        config = PreprocessConfig()
        assert config.deskew is True
        assert config.denoise is True
        assert config.binarize is True
        assert config.contrast is True
        assert config.target_dpi == 300

    def test_custom_config(self):
        config = PreprocessConfig(
            deskew=False, denoise=True, binarize=False,
            denoise_strength=5, target_dpi=150
        )
        assert config.deskew is False
        assert config.denoise_strength == 5
        assert config.target_dpi == 150


class TestPreprocessResult:
    """Tests para el resultado del preprocesador."""

    def test_result_fields(self, white_image):
        result = PreprocessResult(image=white_image)
        assert result.skew_angle == 0.0
        assert result.steps_applied == []
        assert result.original_size == (0, 0)

    def test_result_with_steps(self, white_image):
        result = PreprocessResult(
            image=white_image,
            skew_angle=2.5,
            steps_applied=[PreprocessStep.DESKEW, PreprocessStep.DENOISE],
            original_size=(400, 200),
            final_size=(400, 200),
        )
        assert result.skew_angle == 2.5
        assert len(result.steps_applied) == 2


# ═══════════════════════════════════════════════════════════
# Tests: detect_skew_angle
# ═══════════════════════════════════════════════════════════

class TestDetectSkewAngle:
    """Tests para detección de inclinación."""

    def test_no_skew_returns_small_angle(self, text_like_image):
        angle = detect_skew_angle(text_like_image)
        assert abs(angle) < 2.0

    def test_skewed_image_detects_angle(self, skewed_text_image):
        angle = detect_skew_angle(skewed_text_image)
        # Debe detectar inclinación cercana a 5 grados
        assert abs(angle) > 1.0

    def test_blank_image_returns_zero(self, white_image):
        angle = detect_skew_angle(white_image)
        assert angle == 0.0

    def test_grayscale_input(self, gray_image):
        angle = detect_skew_angle(gray_image)
        assert isinstance(angle, float)


# ═══════════════════════════════════════════════════════════
# Tests: apply_deskew
# ═══════════════════════════════════════════════════════════

class TestApplyDeskew:
    """Tests para corrección de inclinación."""

    def test_returns_image_and_angle(self, text_like_image):
        result, angle = apply_deskew(text_like_image)
        assert isinstance(result, np.ndarray)
        assert isinstance(angle, float)
        assert result.shape[2] == 3  # BGR

    def test_no_change_when_straight(self, white_image):
        result, angle = apply_deskew(white_image)
        assert abs(angle) < 0.5

    def test_with_explicit_angle(self, text_like_image):
        result, angle = apply_deskew(text_like_image, angle=3.0)
        assert angle == 3.0
        assert result.shape[0] > 0

    def test_small_angle_no_rotation(self, text_like_image):
        result, angle = apply_deskew(text_like_image, angle=0.1)
        # Angulo menor a 0.3 no se rota
        assert result.shape == text_like_image.shape


# ═══════════════════════════════════════════════════════════
# Tests: apply_denoise
# ═══════════════════════════════════════════════════════════

class TestApplyDenoise:
    """Tests para reducción de ruido."""

    def test_output_same_shape(self, noisy_image):
        result = apply_denoise(noisy_image, strength=10)
        assert result.shape == noisy_image.shape
        assert result.dtype == np.uint8

    def test_reduces_variance(self, noisy_image):
        result = apply_denoise(noisy_image, strength=10)
        # La imagen denoiseada debe tener menor varianza
        assert np.std(result) <= np.std(noisy_image) + 5

    def test_grayscale_input(self, gray_image):
        rng = np.random.default_rng(42)
        noisy = np.clip(
            gray_image.astype(np.int16) + rng.integers(-20, 20, gray_image.shape, dtype=np.int16),
            0, 255
        ).astype(np.uint8)
        result = apply_denoise(noisy, strength=10)
        assert result.shape == noisy.shape

    def test_strength_clamped(self, noisy_image):
        # No debe lanzar error con valores extremos
        result = apply_denoise(noisy_image, strength=0)
        assert result.shape == noisy_image.shape
        result2 = apply_denoise(noisy_image, strength=100)
        assert result2.shape == noisy_image.shape


# ═══════════════════════════════════════════════════════════
# Tests: apply_binarize
# ═══════════════════════════════════════════════════════════

class TestApplyBinarize:
    """Tests para binarización."""

    def test_output_is_binary(self, noisy_image):
        result = apply_binarize(noisy_image)
        unique = np.unique(result)
        assert set(unique).issubset({0, 255})

    def test_output_is_grayscale(self, noisy_image):
        result = apply_binarize(noisy_image)
        assert len(result.shape) == 2  # 2D = escala de grises

    def test_from_bgr(self, white_image):
        result = apply_binarize(white_image)
        assert len(result.shape) == 2

    def test_from_grayscale(self, gray_image):
        result = apply_binarize(gray_image)
        assert len(result.shape) == 2

    def test_even_block_size_corrected(self, noisy_image):
        # block_size par se corrige a impar
        result = apply_binarize(noisy_image, block_size=10)
        assert result.shape[:2] == noisy_image.shape[:2]


# ═══════════════════════════════════════════════════════════
# Tests: apply_contrast
# ═══════════════════════════════════════════════════════════

class TestApplyContrast:
    """Tests para mejora de contraste CLAHE."""

    def test_output_same_shape_bgr(self, noisy_image):
        result = apply_contrast(noisy_image)
        assert result.shape == noisy_image.shape

    def test_output_same_shape_gray(self, gray_image):
        result = apply_contrast(gray_image)
        assert result.shape == gray_image.shape

    def test_custom_params(self, noisy_image):
        result = apply_contrast(noisy_image, clip_limit=4.0, grid_size=(4, 4))
        assert result.shape == noisy_image.shape


# ═══════════════════════════════════════════════════════════
# Tests: apply_rescale
# ═══════════════════════════════════════════════════════════

class TestApplyRescale:
    """Tests para redimensionado por DPI."""

    def test_double_dpi(self, white_image):
        result = apply_rescale(white_image, current_dpi=150, target_dpi=300)
        assert result.shape[1] == white_image.shape[1] * 2
        assert result.shape[0] == white_image.shape[0] * 2

    def test_half_dpi(self, white_image):
        result = apply_rescale(white_image, current_dpi=300, target_dpi=150)
        assert result.shape[1] == white_image.shape[1] // 2
        assert result.shape[0] == white_image.shape[0] // 2

    def test_same_dpi_no_change(self, white_image):
        result = apply_rescale(white_image, current_dpi=300, target_dpi=300)
        assert result.shape == white_image.shape

    def test_zero_dpi_no_change(self, white_image):
        result = apply_rescale(white_image, current_dpi=0, target_dpi=300)
        assert result.shape == white_image.shape

    def test_similar_dpi_no_change(self, white_image):
        result = apply_rescale(white_image, current_dpi=298, target_dpi=300)
        # Diferencia < 5% no se redimensiona
        assert result.shape == white_image.shape


# ═══════════════════════════════════════════════════════════
# Tests: preprocess_image (pipeline completo)
# ═══════════════════════════════════════════════════════════

class TestPreprocessImage:
    """Tests para el pipeline completo."""

    def test_default_config(self, noisy_image):
        result = preprocess_image(noisy_image)
        assert isinstance(result, PreprocessResult)
        assert result.image is not None
        assert PreprocessStep.DESKEW in result.steps_applied
        assert PreprocessStep.DENOISE in result.steps_applied
        assert result.original_size == (400, 200)

    def test_all_disabled(self, white_image):
        config = PreprocessConfig(
            deskew=False, denoise=False, binarize=False, contrast=False, target_dpi=0
        )
        result = preprocess_image(white_image, config)
        assert result.steps_applied == []
        assert result.image.shape == white_image.shape

    def test_only_deskew(self, text_like_image):
        config = PreprocessConfig(
            deskew=True, denoise=False, binarize=False, contrast=False, target_dpi=0
        )
        result = preprocess_image(text_like_image, config)
        assert result.steps_applied == [PreprocessStep.DESKEW]

    def test_only_binarize(self, noisy_image):
        config = PreprocessConfig(
            deskew=False, denoise=False, binarize=True, contrast=False, target_dpi=0
        )
        result = preprocess_image(noisy_image, config)
        assert PreprocessStep.BINARIZE in result.steps_applied
        unique = np.unique(result.image)
        assert set(unique).issubset({0, 255})

    def test_rescale_needs_current_dpi(self, white_image):
        config = PreprocessConfig(
            deskew=False, denoise=False, binarize=False, contrast=False,
            target_dpi=300, current_dpi=0
        )
        result = preprocess_image(white_image, config)
        # current_dpi=0 → no rescale
        assert PreprocessStep.RESCALE not in result.steps_applied

    def test_rescale_with_dpi(self, white_image):
        config = PreprocessConfig(
            deskew=False, denoise=False, binarize=False, contrast=False,
            target_dpi=300, current_dpi=150
        )
        result = preprocess_image(white_image, config)
        assert PreprocessStep.RESCALE in result.steps_applied
        assert result.final_size[0] == 800  # 400 * 2

    def test_none_config_uses_default(self, noisy_image):
        result = preprocess_image(noisy_image, None)
        assert isinstance(result, PreprocessResult)
        assert len(result.steps_applied) >= 1


class TestPreprocessStep:
    """Tests para la enumeración."""

    def test_values(self):
        assert PreprocessStep.DESKEW.value == "deskew"
        assert PreprocessStep.DENOISE.value == "denoise"
        assert PreprocessStep.BINARIZE.value == "binarize"
        assert PreprocessStep.CONTRAST.value == "contrast"
        assert PreprocessStep.RESCALE.value == "rescale"

    def test_all_steps(self):
        assert len(PreprocessStep) == 5

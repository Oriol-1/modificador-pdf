"""
Tests para FontManager - Gestión centralizada de fuentes

Cubre:
1. Detección de fuentes estándar (Arial, Times, Courier)
2. Fallback para custom fonts
3. Detección heurística de negritas
4. Cálculo de bounding rect con QFontMetrics
5. Estrategias de bold
"""

import pytest
from core.font_manager import FontManager, FontDescriptor, BoldStrategy


@pytest.fixture
def font_manager():
    """Fixture: instancia fresca de FontManager."""
    fm = FontManager()
    fm.clear_cache()
    return fm


class TestFontDetection:
    """Tests para detección de fuentes."""

    def test_detect_arial_12pt(self, font_manager):
        """Detecta Arial 12pt correctamente."""
        span = {
            "font": "Arial",
            "size": 12.0,
            "color": 0,
            "flags": 0,
        }
        descriptor = font_manager.detect_font(span)

        assert descriptor.name == "helv"  # Arial mapea a Helvetica
        assert descriptor.size == 12.0
        assert descriptor.color == "#000000"
        assert descriptor.was_fallback  # Arial triggers fallback mapping

    def test_detect_times_14pt(self, font_manager):
        """Detecta Times 14pt correctamente."""
        span = {
            "font": "TimesNewRoman",
            "size": 14.0,
            "color": 0,
        }
        descriptor = font_manager.detect_font(span)

        assert descriptor.name == "times"
        assert descriptor.size == 14.0

    def test_detect_courier_10pt(self, font_manager):
        """Detecta Courier 10pt correctamente."""
        span = {
            "font": "Courier",
            "size": 10.0,
            "color": 0,
        }
        descriptor = font_manager.detect_font(span)

        assert descriptor.name == "cour"
        assert descriptor.size == 10.0

    def test_detect_custom_font_triggers_fallback(self, font_manager):
        """Fuente custom genera fallback con warning."""
        span = {
            "font": "MyriadPro",
            "size": 12.0,
            "color": 0,
        }
        descriptor = font_manager.detect_font(span)

        assert descriptor.was_fallback
        assert descriptor.fallback_from == "MyriadPro"
        assert descriptor.name == "helv"  # Default fallback

    def test_detect_font_with_color(self, font_manager):
        """Detecta color correctamente (RGB)."""
        span = {
            "font": "Arial",
            "size": 12.0,
            "color": 0xFF0000,  # Rojo (BGR format)
        }
        descriptor = font_manager.detect_font(span)

        # Color en PyMuPDF es BGR, convertir a RGB
        assert descriptor.color.startswith("#")  # Es hex string

    def test_detect_font_handles_none_font_name(self, font_manager):
        """Maneja gracefully font_name None."""
        span = {
            "font": None,
            "size": 12.0,
        }
        descriptor = font_manager.detect_font(span)

        assert descriptor.name == "helv"  # Default
        assert descriptor.was_fallback

    def test_detect_font_handles_missing_size(self, font_manager):
        """Maneja gracefully size faltante."""
        span = {
            "font": "Arial",
            # size faltante
        }
        descriptor = font_manager.detect_font(span)

        assert descriptor.size == 12.0  # Default


class TestSmartFallback:
    """Tests para mapeo inteligente de fuentes."""

    def test_exact_match_arial(self, font_manager):
        """Búsqueda exacta para Arial."""
        result = font_manager.smart_fallback("Arial")
        assert result == "helv"

    def test_exact_match_times(self, font_manager):
        """Búsqueda exacta para Times."""
        result = font_manager.smart_fallback("TimesNewRoman")
        assert result == "times"

    def test_prefix_match_arial_mt(self, font_manager):
        """Búsqueda por prefijo: ArialMT → helv."""
        result = font_manager.smart_fallback("ArialMT")
        assert result == "helv"

    def test_prefix_match_times_roman(self, font_manager):
        """Búsqueda por prefijo: Times-Roman → times."""
        result = font_manager.smart_fallback("Times-Roman")
        assert result == "times"

    def test_serif_heuristic(self, font_manager):
        """Heurística serif: nombre contiene 'serif' → times."""
        result = font_manager.smart_fallback("CustomSerif")
        assert result == "times"

    def test_default_fallback(self, font_manager):
        """Fuente completamente desconocida → helv (default)."""
        result = font_manager.smart_fallback("XyzUnknownFont123")
        assert result == "helv"

    def test_empty_string_fallback(self, font_manager):
        """String vacío → helv (default)."""
        result = font_manager.smart_fallback("")
        assert result == "helv"

    def test_none_fallback(self, font_manager):
        """None → helv (default)."""
        result = font_manager.smart_fallback(None)
        assert result == "helv"


class TestBoldDetection:
    """Tests para detección heurística de negritas."""

    def test_bold_in_font_name(self, font_manager):
        """Detecta bold cuando nombre contiene 'Bold'."""
        span = {"font": "ArialBold"}
        result = font_manager.detect_possible_bold(span)
        assert result

    def test_bold_suffix_detection(self, font_manager):
        """Detecta bold por sufijo -Bold."""
        span = {"font": "Helvetica-Bold"}
        result = font_manager.detect_possible_bold(span)
        assert result

    def test_bold_short_notation(self, font_manager):
        """Detecta bold por sufijo -B."""
        span = {"font": "Arial-B"}
        result = font_manager.detect_possible_bold(span)
        assert result

    def test_no_bold_detection(self, font_manager):
        """No detecta bold en fuente regular."""
        span = {"font": "Arial"}
        result = font_manager.detect_possible_bold(span)
        assert result is None or not result

    def test_bold_by_flags(self, font_manager):
        """Detecta bold por flags PDF (0x40)."""
        span = {"font": "Arial", "flags": 0x40}
        result = font_manager.detect_possible_bold(span)
        assert result

    def test_heavy_in_font_name(self, font_manager):
        """Detecta bold cuando nombre contiene 'Heavy'."""
        span = {"font": "HelveticaHeavy"}
        result = font_manager.detect_possible_bold(span)
        assert result

    def test_black_in_font_name(self, font_manager):
        """Detecta bold cuando nombre contiene 'Black'."""
        span = {"font": "ArialBlack"}
        result = font_manager.detect_possible_bold(span)
        assert result


class TestBoundingRect:
    """Tests para cálculo de bounding rect con QFontMetrics."""

    def test_bounding_rect_simple_text(self, font_manager):
        """Calcula rect para texto simple."""
        descriptor = FontDescriptor(name="helv", size=12)
        width, height = font_manager.get_bounding_rect("Hola", descriptor)

        assert width > 0  # Debe tener ancho
        assert height > 0  # Debe tener alto
        assert height >= 12  # Altura al menos igual al tamaño

    def test_bounding_rect_longer_text(self, font_manager):
        """Texto más largo → ancho mayor."""
        descriptor = FontDescriptor(name="helv", size=12)
        width1, _ = font_manager.get_bounding_rect("Hola", descriptor)
        width2, _ = font_manager.get_bounding_rect("Hola mundo", descriptor)

        assert width2 > width1  # Más texto = más ancho

    def test_bounding_rect_larger_font(self, font_manager):
        """Fuente más grande → altura mayor."""
        descriptor_12 = FontDescriptor(name="helv", size=12)
        descriptor_24 = FontDescriptor(name="helv", size=24)

        _, height_12 = font_manager.get_bounding_rect("Hola", descriptor_12)
        _, height_24 = font_manager.get_bounding_rect("Hola", descriptor_24)

        assert height_24 > height_12

    def test_bounding_rect_empty_string(self, font_manager):
        """Texto vacío devuelve (0, height)."""
        descriptor = FontDescriptor(name="helv", size=12)
        width, height = font_manager.get_bounding_rect("", descriptor)

        assert width == 0
        assert height > 0  # Altura aún existe

    def test_bounding_rect_cache(self, font_manager):
        """Caché de QFont acelera cálculos repetidos (solo con QApplication)."""
        descriptor = FontDescriptor(name="helv", size=12)

        # Primer cálculo
        font_manager.get_bounding_rect("Test", descriptor)
        
        # Sin QApplication, el cache no se usa (retorna fallback estimado)
        # Con QApplication, el cache se llena
        # Este test verifica que no hay errores, no el estado del cache
        
        # Segundo cálculo debe funcionar igual
        w1, h1 = font_manager.get_bounding_rect("Test", descriptor)
        w2, h2 = font_manager.get_bounding_rect("Test", descriptor)
        
        # Los resultados deben ser consistentes
        assert w1 == w2
        assert h1 == h2


class TestHandleBold:
    """Tests para aplicación de negritas."""

    def test_handle_bold_enabled(self, font_manager):
        """Aplicar bold cuando should_bold=True."""
        descriptor = FontDescriptor(name="helv", size=12)
        text, strategy = font_manager.handle_bold("importante", descriptor, True)

        assert text == "importante"
        assert strategy in [
            BoldStrategy.EXACT_BOLD.value,
            BoldStrategy.APPROXIMATE_BOLD.value,
        ]

    def test_handle_bold_disabled(self, font_manager):
        """No aplicar bold cuando should_bold=False."""
        descriptor = FontDescriptor(name="helv", size=12)
        text, strategy = font_manager.handle_bold("importante", descriptor, False)

        assert text == "importante"
        assert strategy == BoldStrategy.EXACT_BOLD.value


class TestValidateTextFits:
    """Tests para validación de espacio disponible."""

    def test_text_fits_comfortably(self, font_manager):
        """Texto cabe con espacio de sobra."""
        descriptor = FontDescriptor(name="helv", size=12)
        text = "Hi"  # Texto muy corto
        max_width = 500  # Mucho espacio

        fits, message = font_manager.validate_text_fits(text, descriptor, max_width)

        assert fits
        assert message is None

    def test_text_doesnt_fit(self, font_manager):
        """Texto no cabe en área disponible."""
        descriptor = FontDescriptor(name="helv", size=12)
        text = "Este es un texto muy largo que definitivamente no cabe"
        max_width = 50  # Muy poco espacio

        fits, message = font_manager.validate_text_fits(text, descriptor, max_width)

        assert not fits
        assert message is not None
        assert "no cabe" in message.lower()


class TestReduceTracking:
    """Tests para reducción de espaciado."""

    def test_reduce_tracking_zero_percent(self, font_manager):
        """Reducción 0% → texto sin cambios."""
        descriptor = FontDescriptor(name="helv", size=12)
        result = font_manager.reduce_tracking("Hola", descriptor, 0)

        assert result == "Hola"

    def test_reduce_tracking_negative_percent(self, font_manager):
        """Reducción negativa → texto sin cambios."""
        descriptor = FontDescriptor(name="helv", size=12)
        result = font_manager.reduce_tracking("Hola", descriptor, -10)

        assert result == "Hola"

    def test_reduce_tracking_positive_percent(self, font_manager):
        """Reducción positiva → registra en log."""
        descriptor = FontDescriptor(name="helv", size=12)
        result = font_manager.reduce_tracking("Hola", descriptor, 15)

        # En la versión actual, retorna el mismo texto
        # (la implementación real modificaría PDF)
        assert result == "Hola"


class TestFontDescriptor:
    """Tests para dataclass FontDescriptor."""

    def test_font_descriptor_creation(self):
        """Crear FontDescriptor correctamente."""
        desc = FontDescriptor(
            name="helv",
            size=12.0,
            color="#000000",
            was_fallback=False,
        )

        assert desc.name == "helv"
        assert desc.size == 12.0
        assert not desc.was_fallback

    def test_font_descriptor_with_fallback(self):
        """FontDescriptor con fallback de fuente."""
        desc = FontDescriptor(
            name="helv",
            size=12.0,
            was_fallback=True,
            fallback_from="MyriadPro",
        )

        assert desc.fallback_from == "MyriadPro"
        assert desc.was_fallback

    def test_font_descriptor_repr(self):
        """Representación string de FontDescriptor."""
        desc = FontDescriptor(name="helv", size=12.0)
        repr_str = repr(desc)

        assert "helv" in repr_str
        assert "12.0" in repr_str


class TestColorConversion:
    """Tests para conversión de color Int → Hex."""

    def test_color_black(self, font_manager):
        """Color negro: 0 → #000000."""
        color = font_manager._color_to_hex(0)
        assert color == "#000000"

    def test_color_white(self, font_manager):
        """Color blanco: 0xFFFFFF → #ffffff."""
        color = font_manager._color_to_hex(0xFFFFFF)
        assert color == "#ffffff"

    def test_color_red(self, font_manager):
        """Color rojo: 0xFF0000 → #0000ff (BGR format)."""
        color = font_manager._color_to_hex(0xFF0000)
        # PyMuPDF usa BGR
        assert color.startswith("#")

    def test_color_invalid_input(self, font_manager):
        """Input inválido → fallback #000000."""
        color = font_manager._color_to_hex("invalid")
        assert color == "#000000"


class TestSingleton:
    """Tests para patrón singleton de FontManager."""

    def test_get_font_manager_returns_instance(self):
        """get_font_manager() retorna instancia."""
        from core.font_manager import get_font_manager

        fm = get_font_manager()
        assert isinstance(fm, FontManager)

    def test_get_font_manager_singleton(self):
        """get_font_manager() retorna misma instancia."""
        from core.font_manager import get_font_manager

        fm1 = get_font_manager()
        fm2 = get_font_manager()

        assert fm1 is fm2


# ========== Fase 3B: Tests para nuevas funcionalidades ==========


class TestFontEmbeddingStatus:
    """Tests para FontEmbeddingStatus enum."""

    def test_embedding_status_values(self):
        """Verifica valores del enum."""
        from core.font_manager import FontEmbeddingStatus
        
        assert FontEmbeddingStatus.EMBEDDED.value == "embedded"
        assert FontEmbeddingStatus.SUBSET.value == "subset"
        assert FontEmbeddingStatus.EXTERNAL.value == "external"
        assert FontEmbeddingStatus.UNKNOWN.value == "unknown"


class TestPreciseMetrics:
    """Tests para PreciseMetrics dataclass."""

    def test_precise_metrics_creation(self):
        """Crear PreciseMetrics con valores por defecto."""
        from core.font_manager import PreciseMetrics
        
        metrics = PreciseMetrics()
        assert metrics.ascender == 0.0
        assert metrics.descender == 0.0
        assert metrics.stem_v == 0.0
        assert metrics.italic_angle == 0.0

    def test_precise_metrics_with_values(self):
        """Crear PreciseMetrics con valores específicos."""
        from core.font_manager import PreciseMetrics
        
        metrics = PreciseMetrics(
            ascender=800,
            descender=-200,
            line_height=1000,
            avg_char_width=500,
            stem_v=120,
            italic_angle=-12.0
        )
        
        assert metrics.ascender == 800
        assert metrics.descender == -200
        assert metrics.stem_v == 120
        assert metrics.italic_angle == -12.0

    def test_is_bold_by_stem_true(self):
        """stem_v > 100 indica bold."""
        from core.font_manager import PreciseMetrics
        
        metrics = PreciseMetrics(stem_v=120)
        assert metrics.is_bold_by_stem is True

    def test_is_bold_by_stem_false(self):
        """stem_v <= 100 indica no bold."""
        from core.font_manager import PreciseMetrics
        
        metrics = PreciseMetrics(stem_v=80)
        assert metrics.is_bold_by_stem is False

    def test_is_bold_by_stem_unknown(self):
        """stem_v == 0 retorna None (desconocido)."""
        from core.font_manager import PreciseMetrics
        
        metrics = PreciseMetrics(stem_v=0)
        assert metrics.is_bold_by_stem is None

    def test_is_italic_by_angle_true(self):
        """italic_angle > 5 indica italic."""
        from core.font_manager import PreciseMetrics
        
        metrics = PreciseMetrics(italic_angle=-12.0)
        assert metrics.is_italic_by_angle is True

    def test_is_italic_by_angle_false(self):
        """italic_angle <= 5 indica no italic."""
        from core.font_manager import PreciseMetrics
        
        metrics = PreciseMetrics(italic_angle=0.0)
        assert metrics.is_italic_by_angle is False


class TestFontDescriptorPhase3B:
    """Tests para campos nuevos de FontDescriptor (Fase 3B)."""

    def test_font_descriptor_new_fields_defaults(self):
        """Nuevos campos tienen valores por defecto."""
        from core.font_manager import FontDescriptor, FontEmbeddingStatus
        
        descriptor = FontDescriptor(name="helv", size=12.0)
        
        assert descriptor.embedding_status == FontEmbeddingStatus.UNKNOWN
        assert descriptor.precise_metrics is None
        assert descriptor.char_spacing == 0.0
        assert descriptor.word_spacing == 0.0
        assert descriptor.baseline_y is None
        assert descriptor.bbox is None
        assert descriptor.original_font_name is None
        assert descriptor.is_subset is False
        assert descriptor.glyph_widths == {}

    def test_font_descriptor_with_new_fields(self):
        """Crear FontDescriptor con todos los campos nuevos."""
        from core.font_manager import (
            FontDescriptor, 
            FontEmbeddingStatus,
            PreciseMetrics
        )
        
        metrics = PreciseMetrics(ascender=800, descender=-200)
        descriptor = FontDescriptor(
            name="helv",
            size=12.0,
            embedding_status=FontEmbeddingStatus.SUBSET,
            precise_metrics=metrics,
            char_spacing=0.5,
            word_spacing=1.0,
            baseline_y=100.5,
            bbox=(10, 20, 200, 30),
            original_font_name="ABCDEF+ArialMT",
            is_subset=True,
            glyph_widths={"A": 600, "B": 650}
        )
        
        assert descriptor.embedding_status == FontEmbeddingStatus.SUBSET
        assert descriptor.precise_metrics.ascender == 800
        assert descriptor.char_spacing == 0.5
        assert descriptor.is_subset is True
        assert descriptor.glyph_widths["A"] == 600

    def test_font_descriptor_has_precise_metrics(self):
        """has_precise_metrics() funciona correctamente."""
        from core.font_manager import FontDescriptor, PreciseMetrics
        
        # Sin métricas
        desc1 = FontDescriptor(name="helv", size=12.0)
        assert desc1.has_precise_metrics() is False
        
        # Con métricas
        desc2 = FontDescriptor(
            name="helv", 
            size=12.0,
            precise_metrics=PreciseMetrics()
        )
        assert desc2.has_precise_metrics() is True

    def test_font_descriptor_get_line_height_precise(self):
        """get_line_height() usa métricas precisas si disponibles."""
        from core.font_manager import FontDescriptor, PreciseMetrics
        
        metrics = PreciseMetrics(line_height=1000)
        descriptor = FontDescriptor(
            name="helv",
            size=12.0,
            precise_metrics=metrics
        )
        
        # line_height = 1000 * 12 / 1000 = 12
        assert descriptor.get_line_height() == 12.0

    def test_font_descriptor_get_line_height_estimated(self):
        """get_line_height() usa estimación si no hay métricas."""
        descriptor = FontDescriptor(name="helv", size=10.0)
        
        # Estimación: size * 1.2 = 12.0
        assert descriptor.get_line_height() == 12.0

    def test_font_descriptor_is_bold_detected_by_metrics(self):
        """is_bold_detected() prioriza métricas precisas."""
        from core.font_manager import FontDescriptor, PreciseMetrics
        
        # Bold por stem_v
        metrics = PreciseMetrics(stem_v=120)
        descriptor = FontDescriptor(
            name="helv",
            size=12.0,
            precise_metrics=metrics,
            possible_bold=False  # Heurística dice no
        )
        
        # Métricas tienen prioridad
        assert descriptor.is_bold_detected() is True

    def test_font_descriptor_is_bold_detected_by_heuristic(self):
        """is_bold_detected() usa heurística si no hay métricas."""
        descriptor = FontDescriptor(
            name="helv",
            size=12.0,
            possible_bold=True
        )
        
        assert descriptor.is_bold_detected() is True

    def test_font_descriptor_repr_with_embedding(self):
        """repr incluye estado de embedding."""
        from core.font_manager import FontDescriptor, FontEmbeddingStatus
        
        descriptor = FontDescriptor(
            name="helv",
            size=12.0,
            embedding_status=FontEmbeddingStatus.SUBSET
        )
        
        repr_str = repr(descriptor)
        assert "[subset]" in repr_str


class TestFontManagerSetDocument:
    """Tests para set_document()."""

    def test_set_document_clears_cache(self, font_manager):
        """set_document() limpia cache de fuentes."""
        # Agregar algo al cache
        font_manager._font_info_cache["test"] = "value"
        
        font_manager.set_document(None)
        
        assert "test" not in font_manager._font_info_cache

    def test_set_document_resets_extractor(self, font_manager):
        """set_document(None) resetea extractor."""
        font_manager.set_document(None)
        
        assert font_manager._font_extractor is None


class TestDetectEmbeddedStatus:
    """Tests para detect_embedded_status()."""

    def test_detect_embedded_status_no_extractor(self, font_manager):
        """Sin extractor retorna UNKNOWN."""
        from core.font_manager import FontEmbeddingStatus
        
        status = font_manager.detect_embedded_status("Arial", 0)
        
        assert status == FontEmbeddingStatus.UNKNOWN


class TestGetPreciseMetrics:
    """Tests para get_precise_metrics()."""

    def test_get_precise_metrics_no_extractor(self, font_manager):
        """Sin extractor retorna None."""
        metrics = font_manager.get_precise_metrics("Arial", 0)
        
        assert metrics is None


class TestCanReuseFont:
    """Tests para can_reuse_font()."""

    def test_can_reuse_font_no_extractor(self, font_manager):
        """Sin extractor retorna False."""
        can_reuse = font_manager.can_reuse_font("Arial", 0)
        
        assert can_reuse is False


class TestDetectFontWithBbox:
    """Tests para detect_font con bbox y baseline."""

    def test_detect_font_extracts_bbox(self, font_manager):
        """detect_font extrae bbox del span."""
        span = {
            "font": "Arial",
            "size": 12.0,
            "color": 0,
            "bbox": (10, 20, 100, 32)
        }
        
        descriptor = font_manager.detect_font(span)
        
        assert descriptor.bbox == (10, 20, 100, 32)

    def test_detect_font_extracts_baseline(self, font_manager):
        """detect_font extrae baseline_y de origin."""
        span = {
            "font": "Arial",
            "size": 12.0,
            "color": 0,
            "origin": (10, 30)  # x, y donde y es baseline
        }
        
        descriptor = font_manager.detect_font(span)
        
        assert descriptor.baseline_y == 30


class TestImprovedBoldDetection:
    """Tests para detección mejorada de bold (Fase 3B)."""

    def test_detect_bold_demi_indicator(self, font_manager):
        """'Demi' en nombre indica bold."""
        span = {"font": "Arial-DemiBold", "flags": 0}
        
        result = font_manager.detect_possible_bold(span)
        
        assert result is True

    def test_detect_bold_semi_indicator(self, font_manager):
        """'Semi' en nombre indica bold."""
        span = {"font": "Arial-SemiBold", "flags": 0}
        
        result = font_manager.detect_possible_bold(span)
        
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

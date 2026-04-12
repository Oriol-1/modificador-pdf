"""Tests para core.ocr.ocr_engine — Motor OCR con Tesseract.

Tests unitarios que no requieren Tesseract instalado (mock)
y tests de integración marcados con pytest.mark para cuando
Tesseract esté disponible.
"""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from core.ocr.ocr_engine import (
    OCRLanguage,
    OCRWord,
    OCRLine,
    OCRResult,
    OCREngine,
    TesseractEngine,
    create_tesseract_engine,
)


# ═══════════════════════════════════════════════════════════
# Tests: Modelos de datos
# ═══════════════════════════════════════════════════════════

class TestOCRLanguage:
    """Tests para la enumeración de idiomas."""

    def test_spanish(self):
        assert OCRLanguage.SPANISH.value == "spa"

    def test_english(self):
        assert OCRLanguage.ENGLISH.value == "eng"

    def test_all_languages(self):
        assert len(OCRLanguage) >= 7


class TestOCRWord:
    """Tests para OCRWord dataclass."""

    def test_create_word(self):
        word = OCRWord(text="Hola", x=10, y=20, width=50, height=15, confidence=95.5)
        assert word.text == "Hola"
        assert word.x == 10
        assert word.confidence == 95.5

    def test_default_values(self):
        word = OCRWord(text="Test")
        assert word.x == 0
        assert word.confidence == 0.0
        assert word.block_num == 0

    def test_to_dict(self):
        word = OCRWord(text="Hola", x=10, y=20, width=50, height=15, confidence=95.5)
        d = word.to_dict()
        assert d['text'] == "Hola"
        assert d['x'] == 10
        assert d['confidence'] == 95.5

    def test_from_dict(self):
        d = {'text': 'Hola', 'x': 10, 'y': 20, 'width': 50, 'height': 15,
             'confidence': 95.5, 'block_num': 1, 'par_num': 1, 'line_num': 1, 'word_num': 1}
        word = OCRWord.from_dict(d)
        assert word.text == "Hola"
        assert word.x == 10

    def test_round_trip(self):
        word = OCRWord(text="Mundo", x=100, y=200, width=80, height=20,
                       confidence=88.3, block_num=1, par_num=1, line_num=2, word_num=3)
        restored = OCRWord.from_dict(word.to_dict())
        assert restored.text == word.text
        assert restored.confidence == word.confidence


class TestOCRLine:
    """Tests para OCRLine dataclass."""

    def test_text_property(self):
        words = [
            OCRWord(text="Hola", x=10, confidence=90),
            OCRWord(text="Mundo", x=80, confidence=85),
        ]
        line = OCRLine(words=words, x=10, y=20, width=150, height=20)
        assert line.text == "Hola Mundo"

    def test_empty_line(self):
        line = OCRLine()
        assert line.text == ""
        assert line.avg_confidence == 0.0

    def test_avg_confidence(self):
        words = [
            OCRWord(text="A", confidence=90),
            OCRWord(text="B", confidence=80),
        ]
        line = OCRLine(words=words)
        assert line.avg_confidence == 85.0

    def test_skip_empty_words_in_text(self):
        words = [
            OCRWord(text="Hola", x=10),
            OCRWord(text="  ", x=50),
            OCRWord(text="Mundo", x=80),
        ]
        line = OCRLine(words=words)
        assert line.text == "Hola Mundo"


class TestOCRResult:
    """Tests para OCRResult dataclass."""

    def test_default(self):
        result = OCRResult()
        assert result.text == ""
        assert result.words == []
        assert result.lines == []
        assert result.avg_confidence == 0.0

    def test_with_data(self):
        words = [OCRWord(text="Test", confidence=95)]
        result = OCRResult(
            text="Test", words=words, language="eng",
            avg_confidence=95.0, image_size=(800, 600)
        )
        assert result.text == "Test"
        assert result.image_size == (800, 600)

    def test_to_dict(self):
        result = OCRResult(text="Texto", language="spa", avg_confidence=92.0)
        d = result.to_dict()
        assert d['text'] == "Texto"
        assert d['language'] == "spa"


# ═══════════════════════════════════════════════════════════
# Tests: TesseractEngine (con mocks)
# ═══════════════════════════════════════════════════════════

class TestTesseractEngine:
    """Tests para el motor Tesseract con pytesseract mockeado."""

    def test_is_available_without_pytesseract(self):
        engine = TesseractEngine()
        with patch('core.ocr.ocr_engine.HAS_TESSERACT', False):
            assert engine.is_available() is False

    def test_get_languages_not_available(self):
        engine = TesseractEngine()
        with patch.object(engine, 'is_available', return_value=False):
            assert engine.get_available_languages() == []

    @patch('core.ocr.ocr_engine.HAS_TESSERACT', True)
    @patch('core.ocr.ocr_engine.pytesseract')
    def test_recognize_returns_ocr_result(self, mock_pytesseract):
        mock_pytesseract.image_to_string.return_value = "Hola Mundo"
        mock_pytesseract.image_to_data.return_value = {
            'text': ['Hola', 'Mundo', ''],
            'conf': ['95', '88', '-1'],
            'left': [10, 80, 0],
            'top': [20, 20, 0],
            'width': [60, 70, 0],
            'height': [15, 15, 0],
            'block_num': [1, 1, 0],
            'par_num': [1, 1, 0],
            'line_num': [1, 1, 0],
            'word_num': [1, 2, 0],
        }
        mock_pytesseract.Output.DICT = 'dict'

        engine = TesseractEngine()
        img = np.ones((100, 200, 3), dtype=np.uint8) * 255
        result = engine.recognize(img, language="spa")

        assert isinstance(result, OCRResult)
        assert result.text == "Hola Mundo"
        assert len(result.words) == 2
        assert result.words[0].text == "Hola"
        assert result.words[0].confidence == 95.0
        assert result.words[1].text == "Mundo"
        assert result.language == "spa"

    @patch('core.ocr.ocr_engine.HAS_TESSERACT', True)
    @patch('core.ocr.ocr_engine.pytesseract')
    def test_recognize_groups_into_lines(self, mock_pytesseract):
        mock_pytesseract.image_to_string.return_value = "Línea uno\nLínea dos"
        mock_pytesseract.image_to_data.return_value = {
            'text': ['Línea', 'uno', 'Línea', 'dos'],
            'conf': ['90', '88', '92', '85'],
            'left': [10, 80, 10, 80],
            'top': [20, 20, 50, 50],
            'width': [60, 40, 60, 40],
            'height': [15, 15, 15, 15],
            'block_num': [1, 1, 1, 1],
            'par_num': [1, 1, 1, 1],
            'line_num': [1, 1, 2, 2],
            'word_num': [1, 2, 1, 2],
        }
        mock_pytesseract.Output.DICT = 'dict'

        engine = TesseractEngine()
        img = np.ones((100, 200, 3), dtype=np.uint8) * 255
        result = engine.recognize(img)

        assert len(result.lines) == 2
        assert result.lines[0].text == "Línea uno"
        assert result.lines[1].text == "Línea dos"

    @patch('core.ocr.ocr_engine.HAS_TESSERACT', True)
    @patch('core.ocr.ocr_engine.pytesseract')
    def test_recognize_calculates_avg_confidence(self, mock_pytesseract):
        mock_pytesseract.image_to_string.return_value = "Test"
        mock_pytesseract.image_to_data.return_value = {
            'text': ['A', 'B'],
            'conf': ['80', '90'],
            'left': [10, 50],
            'top': [10, 10],
            'width': [30, 30],
            'height': [15, 15],
            'block_num': [1, 1],
            'par_num': [1, 1],
            'line_num': [1, 1],
            'word_num': [1, 2],
        }
        mock_pytesseract.Output.DICT = 'dict'

        engine = TesseractEngine()
        img = np.ones((50, 100), dtype=np.uint8) * 255
        result = engine.recognize(img)

        assert result.avg_confidence == 85.0

    def test_recognize_without_pytesseract(self):
        engine = TesseractEngine()
        img = np.ones((50, 100), dtype=np.uint8) * 255
        with patch('core.ocr.ocr_engine.HAS_TESSERACT', False):
            with pytest.raises(ImportError, match="pytesseract"):
                engine.recognize(img)

    @patch('core.ocr.ocr_engine.HAS_TESSERACT', True)
    @patch('core.ocr.ocr_engine.pytesseract')
    def test_get_languages_returns_list(self, mock_pytesseract):
        mock_pytesseract.get_tesseract_version.return_value = '5.3.0'
        mock_pytesseract.get_languages.return_value = ['eng', 'spa', 'fra', 'osd']

        engine = TesseractEngine()
        langs = engine.get_available_languages()

        assert 'eng' in langs
        assert 'spa' in langs
        assert 'osd' not in langs  # Se filtra


class TestCreateTesseractEngine:
    """Tests para la factory function."""

    def test_creates_engine(self):
        engine = create_tesseract_engine()
        assert isinstance(engine, TesseractEngine)

    def test_with_custom_cmd(self):
        engine = create_tesseract_engine(tesseract_cmd="/usr/bin/tesseract")
        assert isinstance(engine, TesseractEngine)


# ═══════════════════════════════════════════════════════════
# Tests: OCREngine interface
# ═══════════════════════════════════════════════════════════

class TestOCREngineInterface:
    """Tests que verifican que TesseractEngine implementa OCREngine."""

    def test_is_subclass(self):
        assert issubclass(TesseractEngine, OCREngine)

    def test_has_required_methods(self):
        engine = TesseractEngine()
        assert hasattr(engine, 'is_available')
        assert hasattr(engine, 'recognize')
        assert hasattr(engine, 'get_available_languages')

"""Motor OCR con integración Tesseract.

Provee interfaz abstracta OCREngine y implementación concreta
TesseractEngine para reconocimiento de texto en imágenes.
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

import numpy as np

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    pytesseract = None  # type: ignore
    HAS_TESSERACT = False

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

logger = logging.getLogger(__name__)


class OCRLanguage(Enum):
    """Idiomas soportados para OCR."""
    SPANISH = "spa"
    ENGLISH = "eng"
    FRENCH = "fra"
    GERMAN = "deu"
    PORTUGUESE = "por"
    CATALAN = "cat"
    ITALIAN = "ita"


@dataclass
class OCRWord:
    """Palabra reconocida por OCR con su posición.
    
    Attributes:
        text: Texto reconocido.
        x: Coordenada X del bounding box.
        y: Coordenada Y del bounding box.
        width: Ancho del bounding box.
        height: Alto del bounding box.
        confidence: Confianza del reconocimiento (0-100).
        block_num: Número de bloque.
        par_num: Número de párrafo.
        line_num: Número de línea.
        word_num: Número de palabra en la línea.
    """
    text: str
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    confidence: float = 0.0
    block_num: int = 0
    par_num: int = 0
    line_num: int = 0
    word_num: int = 0

    def to_dict(self) -> dict:
        """Serializa a diccionario."""
        return {
            'text': self.text, 'x': self.x, 'y': self.y,
            'width': self.width, 'height': self.height,
            'confidence': self.confidence,
            'block_num': self.block_num, 'par_num': self.par_num,
            'line_num': self.line_num, 'word_num': self.word_num,
        }

    @staticmethod
    def from_dict(d: dict) -> 'OCRWord':
        """Deserializa desde diccionario."""
        return OCRWord(**d)


@dataclass
class OCRLine:
    """Línea de texto reconocida por OCR.
    
    Attributes:
        words: Palabras de la línea.
        x: Coordenada X del bounding box de línea.
        y: Coordenada Y del bounding box de línea.
        width: Ancho total.
        height: Alto total.
    """
    words: List[OCRWord] = field(default_factory=list)
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    
    @property
    def text(self) -> str:
        """Texto completo de la línea."""
        return " ".join(w.text for w in self.words if w.text.strip())
    
    @property
    def avg_confidence(self) -> float:
        """Confianza promedio de la línea."""
        if not self.words:
            return 0.0
        return sum(w.confidence for w in self.words) / len(self.words)


@dataclass
class OCRResult:
    """Resultado completo de OCR para una imagen.
    
    Attributes:
        text: Texto completo reconocido.
        words: Lista de todas las palabras con posiciones.
        lines: Líneas de texto agrupadas.
        language: Idioma utilizado.
        avg_confidence: Confianza promedio.
        image_size: Tamaño de la imagen (width, height).
    """
    text: str = ""
    words: List[OCRWord] = field(default_factory=list)
    lines: List[OCRLine] = field(default_factory=list)
    language: str = "spa"
    avg_confidence: float = 0.0
    image_size: Tuple[int, int] = (0, 0)

    def to_dict(self) -> dict:
        """Serializa a diccionario."""
        return {
            'text': self.text,
            'words': [w.to_dict() for w in self.words],
            'language': self.language,
            'avg_confidence': self.avg_confidence,
            'image_size': self.image_size,
        }


class OCREngine(ABC):
    """Interfaz abstracta para motores OCR."""
    
    @abstractmethod
    def is_available(self) -> bool:
        """Verifica si el motor está disponible."""
        ...
    
    @abstractmethod
    def recognize(
        self,
        image: np.ndarray,
        language: str = "spa",
    ) -> OCRResult:
        """Ejecuta OCR sobre una imagen.
        
        Args:
            image: Imagen como numpy array.
            language: Código de idioma Tesseract.
            
        Returns:
            OCRResult con texto y posiciones.
        """
        ...
    
    @abstractmethod
    def get_available_languages(self) -> List[str]:
        """Retorna los idiomas disponibles."""
        ...


class TesseractEngine(OCREngine):
    """Motor OCR basado en Tesseract.
    
    Requiere Tesseract 5 instalado en el sistema.
    """
    
    def __init__(self, tesseract_cmd: Optional[str] = None):
        """Inicializa el motor Tesseract.
        
        Args:
            tesseract_cmd: Path al ejecutable tesseract.
                Si es None, usa el del PATH del sistema.
        """
        if tesseract_cmd and HAS_TESSERACT:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    
    def is_available(self) -> bool:
        """Verifica si Tesseract está instalado y accesible."""
        if not HAS_TESSERACT:
            return False
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False
    
    def get_available_languages(self) -> List[str]:
        """Retorna los idiomas instalados en Tesseract."""
        if not self.is_available():
            return []
        try:
            langs = pytesseract.get_languages()
            return [l for l in langs if l != 'osd']
        except Exception as e:
            logger.error(f"Error obteniendo idiomas: {e}")
            return []
    
    def recognize(
        self,
        image: np.ndarray,
        language: str = "spa",
    ) -> OCRResult:
        """Ejecuta OCR con Tesseract.
        
        Args:
            image: Imagen como numpy array (BGR o escala de grises).
            language: Código de idioma (ej: 'spa', 'eng', 'spa+eng').
            
        Returns:
            OCRResult con texto, palabras y líneas.
        """
        if not HAS_TESSERACT:
            raise ImportError("pytesseract no está instalado")
        
        h, w = image.shape[:2]
        
        # Texto completo
        text = pytesseract.image_to_string(image, lang=language)
        
        # Datos detallados (TSV)
        data = pytesseract.image_to_data(
            image, lang=language, output_type=pytesseract.Output.DICT
        )
        
        # Construir palabras
        words = []
        n_items = len(data['text'])
        for i in range(n_items):
            word_text = data['text'][i].strip()
            if not word_text:
                continue
            
            conf = float(data['conf'][i]) if data['conf'][i] != '-1' else 0.0
            word = OCRWord(
                text=word_text,
                x=int(data['left'][i]),
                y=int(data['top'][i]),
                width=int(data['width'][i]),
                height=int(data['height'][i]),
                confidence=conf,
                block_num=int(data['block_num'][i]),
                par_num=int(data['par_num'][i]),
                line_num=int(data['line_num'][i]),
                word_num=int(data['word_num'][i]),
            )
            words.append(word)
        
        # Agrupar en líneas
        lines = self._group_into_lines(words)
        
        # Calcular confianza promedio
        valid_confs = [w.confidence for w in words if w.confidence > 0]
        avg_conf = sum(valid_confs) / len(valid_confs) if valid_confs else 0.0
        
        result = OCRResult(
            text=text.strip(),
            words=words,
            lines=lines,
            language=language,
            avg_confidence=avg_conf,
            image_size=(w, h),
        )
        
        logger.info(
            f"OCR completado: {len(words)} palabras, {len(lines)} líneas, "
            f"confianza={avg_conf:.1f}%, idioma={language}"
        )
        
        return result
    
    def _group_into_lines(self, words: List[OCRWord]) -> List[OCRLine]:
        """Agrupa palabras en líneas basándose en block/par/line numbers."""
        from collections import defaultdict
        
        line_groups = defaultdict(list)
        for word in words:
            key = (word.block_num, word.par_num, word.line_num)
            line_groups[key].append(word)
        
        lines = []
        for key in sorted(line_groups.keys()):
            group = line_groups[key]
            if not group:
                continue
            
            min_x = min(w.x for w in group)
            min_y = min(w.y for w in group)
            max_x = max(w.x + w.width for w in group)
            max_y = max(w.y + w.height for w in group)
            
            line = OCRLine(
                words=sorted(group, key=lambda w: w.x),
                x=min_x, y=min_y,
                width=max_x - min_x,
                height=max_y - min_y,
            )
            lines.append(line)
        
        return lines


def create_tesseract_engine(
    tesseract_cmd: Optional[str] = None
) -> TesseractEngine:
    """Factory para crear un motor Tesseract.
    
    Args:
        tesseract_cmd: Path opcional al ejecutable tesseract.
        
    Returns:
        Instancia de TesseractEngine.
    """
    return TesseractEngine(tesseract_cmd=tesseract_cmd)

"""
Modelos de datos para el editor de PDF.
Contiene las clases de datos (dataclasses) usadas en todo el proyecto.
"""

import fitz  # PyMuPDF
from dataclasses import dataclass
from typing import Tuple, Any


@dataclass
class TextBlock:
    """Representa un bloque de texto en el PDF.
    
    Attributes:
        text: El contenido de texto.
        rect: Rectángulo que delimita el texto en coordenadas PDF.
        font_name: Nombre de la fuente.
        font_size: Tamaño de la fuente en puntos.
        color: Color RGB normalizado (0-1).
        flags: Banderas de estilo (bold, italic, etc.).
        page_num: Número de página (0-indexed).
        block_no: Número de bloque en la página.
        line_no: Número de línea en el bloque.
        span_no: Número de span en la línea.
    """
    text: str
    rect: fitz.Rect
    font_name: str
    font_size: float
    color: Tuple[float, float, float]
    flags: int  # bold, italic, etc.
    page_num: int
    block_no: int
    line_no: int
    span_no: int
    
    @property
    def is_bold(self) -> bool:
        """Retorna True si el texto está en negrita."""
        return bool(self.flags & 2 ** 4)
    
    @property
    def is_italic(self) -> bool:
        """Retorna True si el texto está en cursiva."""
        return bool(self.flags & 2 ** 1)


@dataclass
class EditOperation:
    """Representa una operación de edición para deshacer/rehacer.
    
    Attributes:
        operation_type: Tipo de operación ('highlight', 'delete', 'edit').
        page_num: Número de página donde se realizó la operación.
        original_data: Datos originales antes de la operación.
        new_data: Datos nuevos después de la operación.
        rect: Rectángulo del área afectada.
    """
    operation_type: str  # 'highlight', 'delete', 'edit'
    page_num: int
    original_data: Any
    new_data: Any
    rect: fitz.Rect

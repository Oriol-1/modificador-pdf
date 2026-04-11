"""
RichTextWriter - Motor de escritura de texto con formato rico para PDF.

Usa page.insert_htmlbox() de PyMuPDF para escribir texto con formato
mixto (bold/italic/tamaño/color inline) en una sola operación.

Flujo:
1. Recibe lista de EditableSpan con formato original o modificado
2. Genera HTML inline desde los spans
3. Calcula rect exacto desde el bbox del párrafo/línea
4. Llama page.insert_htmlbox(rect, html) para escribir
5. Devuelve resultado con info de overflow
"""

from __future__ import annotations

import html
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import fitz

from .page_document_model import EditableSpan

logger = logging.getLogger(__name__)


@dataclass
class WriteResult:
    """Resultado de una operación de escritura."""
    success: bool
    overflow: bool = False  # True si el texto no cupó en el rect
    overflow_text: str = ""  # Texto que no cupó
    error: Optional[str] = None


class RichTextWriter:
    """
    Escribe texto con formato rico al PDF usando insert_htmlbox().
    
    Soporta spans con:
    - Diferentes tamaños de fuente
    - Bold / Italic
    - Colores variados
    - Espaciado entre caracteres (via letter-spacing CSS)
    """
    
    # Mapeo de fuentes PDF a familias CSS genéricas
    FONT_FAMILY_MAP = {
        'helv': 'Helvetica, Arial, sans-serif',
        'hebo': 'Helvetica, Arial, sans-serif',
        'tiro': 'Times New Roman, Times, serif',
        'tibo': 'Times New Roman, Times, serif',
        'cour': 'Courier New, Courier, monospace',
        'cobo': 'Courier New, Courier, monospace',
        'helvetica': 'Helvetica, Arial, sans-serif',
        'arial': 'Helvetica, Arial, sans-serif',
        'times': 'Times New Roman, Times, serif',
        'courier': 'Courier New, Courier, monospace',
    }
    
    def __init__(self, page: fitz.Page, doc: fitz.Document):
        self._page = page
        self._doc = doc
    
    def write_spans(
        self,
        spans: List[EditableSpan],
        rect: Optional[fitz.Rect] = None,
    ) -> WriteResult:
        """
        Escribe una lista de spans al PDF usando insert_htmlbox.
        
        Args:
            spans: Lista de EditableSpan a escribir
            rect: Rectángulo destino. Si None, se calcula del bbox de los spans.
            
        Returns:
            WriteResult con estado de la operación
        """
        if not spans:
            return WriteResult(success=True)
        
        # Calcular rect si no se proporcionó
        if rect is None:
            rect = self._compute_rect(spans)
        
        # Generar HTML
        html_content = self._spans_to_html(spans)
        
        try:
            overflow = self._page.insert_htmlbox(rect, html_content)
            has_overflow = overflow is not None and overflow > 0
            return WriteResult(
                success=True,
                overflow=has_overflow,
            )
        except Exception as e:
            logger.error("RichTextWriter: insert_htmlbox falló: %s", e)
            return WriteResult(
                success=False,
                error=str(e),
            )
    
    def write_single_span(self, span: EditableSpan) -> WriteResult:
        """Escribe un solo span como HTML."""
        return self.write_spans([span])
    
    def _compute_rect(self, spans: List[EditableSpan]) -> fitz.Rect:
        """Calcula el rectángulo que contiene todos los spans."""
        x0 = min(s.bbox[0] for s in spans)
        y0 = min(s.bbox[1] for s in spans)
        x1 = max(s.bbox[2] for s in spans)
        y1 = max(s.bbox[3] for s in spans)
        # Expandir ligeramente para evitar recorte
        return fitz.Rect(x0 - 0.5, y0 - 0.5, x1 + 0.5, y1 + 0.5)
    
    def _spans_to_html(self, spans: List[EditableSpan]) -> str:
        """
        Convierte una lista de EditableSpan a HTML inline.
        
        Cada span se convierte en un <span> con estilos CSS inline.
        """
        html_parts = []
        
        for span in spans:
            style_parts = []
            
            # Familia de fuente
            font_family = self._resolve_font_family(span.font_name)
            style_parts.append(f"font-family:{font_family}")
            
            # Tamaño
            size = span.effective_font_size
            style_parts.append(f"font-size:{size:.1f}pt")
            
            # Bold
            if span.effective_is_bold:
                style_parts.append("font-weight:bold")
            
            # Italic
            if span.effective_is_italic:
                style_parts.append("font-style:italic")
            
            # Color
            color = span.effective_color
            if color and color != "#000000":
                style_parts.append(f"color:{color}")
            
            # Espaciado entre caracteres (letter-spacing CSS)
            char_sp = span.effective_char_spacing
            if abs(char_sp) > 0.001:
                style_parts.append(f"letter-spacing:{char_sp:.2f}pt")
            
            # Word spacing
            word_sp = span.effective_word_spacing
            if abs(word_sp) > 0.001:
                style_parts.append(f"word-spacing:{word_sp:.2f}pt")
            
            style = ";".join(style_parts)
            text = html.escape(span.text)
            html_parts.append(f'<span style="{style}">{text}</span>')
        
        return "".join(html_parts)
    
    def _resolve_font_family(self, font_name: str) -> str:
        """Resuelve el nombre de fuente a una familia CSS."""
        name_lower = font_name.lower().strip()
        
        # Búsqueda directa
        if name_lower in self.FONT_FAMILY_MAP:
            return self.FONT_FAMILY_MAP[name_lower]
        
        # Búsqueda parcial
        for key, family in self.FONT_FAMILY_MAP.items():
            if key in name_lower:
                return family
        
        # Fallback: usar el nombre original
        return f"'{font_name}', sans-serif"
    
    @staticmethod
    def spans_have_format_changes(spans: List[EditableSpan]) -> bool:
        """True si algún span tiene cambios de formato."""
        return any(s.dirty_format for s in spans)

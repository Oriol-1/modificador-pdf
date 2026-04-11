"""
PageDocumentModel - Modelo de documento por página para edición de texto PDF.

Parsea una página PDF en una estructura editable:
    Page → [Paragraph] → [LineModel] → [EditableSpan]

Cada EditableSpan preserva ~15 atributos tipográficos originales del PDF,
permitiendo reescribir texto sin alterar formato.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
import fitz

from .text_span import TextSpanMetrics, create_span_from_pymupdf
from .text_line import TextLine, group_spans_into_lines
from .text_paragraph import TextParagraph, group_lines_into_paragraphs


@dataclass
class EditableSpan:
    """Un span de texto editable que preserva todas las propiedades originales del PDF.
    
    Es un wrapper ligero sobre TextSpanMetrics con soporte para edición:
    - new_text: texto modificado (None = sin cambios)
    - dirty: indica si fue modificado
    """
    # Identificación
    span_id: str = ""
    page_num: int = 0
    
    # Texto original y editado
    original_text: str = ""
    new_text: Optional[str] = None  # None = sin cambios
    
    # Geometría original
    bbox: Tuple[float, float, float, float] = (0, 0, 0, 0)
    origin: Tuple[float, float] = (0, 0)
    baseline_y: float = 0.0
    
    # Tipografía
    font_name: str = "Helvetica"
    font_name_pdf: str = ""
    font_size: float = 12.0
    is_bold: bool = False
    is_italic: bool = False
    
    # Color
    fill_color: str = "#000000"
    
    # Espaciado
    char_spacing: float = 0.0
    word_spacing: float = 0.0
    horizontal_scale: float = 100.0
    leading: float = 0.0
    
    # Transformación
    rotation: float = 0.0
    
    # Estado de edición  
    dirty: bool = False
    
    # Cambios de formato (None = sin cambios respecto al original)
    new_font_size: Optional[float] = None
    new_is_bold: Optional[bool] = None
    new_is_italic: Optional[bool] = None
    new_color_rgb: Optional[str] = None  # color hex como "#RRGGBB"
    new_char_spacing: Optional[float] = None
    new_word_spacing: Optional[float] = None
    dirty_format: bool = False
    
    @property
    def text(self) -> str:
        """Retorna el texto actual (editado o original)."""
        return self.new_text if self.new_text is not None else self.original_text
    
    @text.setter
    def text(self, value: str):
        """Establece nuevo texto y marca como dirty."""
        if value != self.original_text:
            self.new_text = value
            self.dirty = True
        else:
            self.new_text = None
            self.dirty = False
    
    @property
    def color_rgb(self) -> Tuple[float, float, float]:
        """Retorna el color como tupla RGB (0-1)."""
        try:
            h = self.fill_color.lstrip('#')
            return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))
        except (ValueError, IndexError):
            return (0.0, 0.0, 0.0)
    
    @property
    def is_dirty(self) -> bool:
        """True si hay cualquier cambio (texto o formato)."""
        return self.dirty or self.dirty_format
    
    @property
    def effective_font_size(self) -> float:
        """Tamaño de fuente efectivo (nuevo o original)."""
        return self.new_font_size if self.new_font_size is not None else self.font_size
    
    @property
    def effective_is_bold(self) -> bool:
        """Bold efectivo (nuevo o original)."""
        return self.new_is_bold if self.new_is_bold is not None else self.is_bold
    
    @property
    def effective_is_italic(self) -> bool:
        """Italic efectivo (nuevo o original)."""
        return self.new_is_italic if self.new_is_italic is not None else self.is_italic
    
    @property
    def effective_color(self) -> str:
        """Color efectivo (nuevo o original)."""
        return self.new_color_rgb if self.new_color_rgb is not None else self.fill_color
    
    @property
    def effective_char_spacing(self) -> float:
        """Char spacing efectivo (nuevo o original)."""
        return self.new_char_spacing if self.new_char_spacing is not None else self.char_spacing
    
    @property
    def effective_word_spacing(self) -> float:
        """Word spacing efectivo (nuevo o original)."""
        return self.new_word_spacing if self.new_word_spacing is not None else self.word_spacing
    
    @classmethod
    def from_span_metrics(cls, sm: TextSpanMetrics) -> "EditableSpan":
        """Crea un EditableSpan desde un TextSpanMetrics."""
        return cls(
            span_id=sm.span_id,
            page_num=sm.page_num,
            original_text=sm.text,
            bbox=sm.bbox,
            origin=sm.origin,
            baseline_y=sm.baseline_y,
            font_name=sm.font_name,
            font_name_pdf=sm.font_name_pdf,
            font_size=sm.font_size,
            is_bold=sm.is_bold if sm.is_bold is not None else False,
            is_italic=sm.is_italic if sm.is_italic is not None else False,
            fill_color=sm.fill_color,
            char_spacing=sm.char_spacing,
            word_spacing=sm.word_spacing,
            horizontal_scale=sm.horizontal_scale,
            leading=sm.leading,
            rotation=sm.rotation,
        )


@dataclass
class LineModel:
    """Una línea de texto editable compuesta de EditableSpans.
    
    Preserva la geometría original de la línea (baseline, bbox).
    """
    line_id: str = ""
    spans: List[EditableSpan] = field(default_factory=list)
    baseline_y: float = 0.0
    bbox: Tuple[float, float, float, float] = (0, 0, 0, 0)
    page_num: int = 0
    
    @property
    def text(self) -> str:
        """Texto completo de la línea (concatenación de spans)."""
        return "".join(s.text for s in self.spans)
    
    @property
    def original_text(self) -> str:
        """Texto original de la línea."""
        return "".join(s.original_text for s in self.spans)
    
    @property
    def is_dirty(self) -> bool:
        """True si algún span fue modificado."""
        return any(s.is_dirty for s in self.spans)
    
    @property
    def dominant_font(self) -> str:
        """Fuente dominante de la línea por longitud de texto."""
        if not self.spans:
            return "Helvetica"
        font_weights = {}
        for s in self.spans:
            w = max(len(s.text.strip()), 1)
            font_weights[s.font_name] = font_weights.get(s.font_name, 0) + w
        return max(font_weights, key=font_weights.get)
    
    @property
    def dominant_font_size(self) -> float:
        """Tamaño de fuente dominante de la línea."""
        if not self.spans:
            return 12.0
        size_weights = {}
        for s in self.spans:
            w = max(len(s.text.strip()), 1)
            size_weights[s.font_size] = size_weights.get(s.font_size, 0) + w
        return max(size_weights, key=size_weights.get)
    
    @classmethod
    def from_text_line(cls, tl: TextLine) -> "LineModel":
        """Crea un LineModel desde un TextLine del text_engine."""
        spans = [EditableSpan.from_span_metrics(sm) for sm in tl.spans]
        return cls(
            line_id=tl.line_id,
            spans=spans,
            baseline_y=tl.baseline_y,
            bbox=tl.bbox,
            page_num=tl.page_num,
        )


@dataclass
class Paragraph:
    """Un párrafo editable compuesto de LineModels."""
    paragraph_id: str = ""
    lines: List[LineModel] = field(default_factory=list)
    page_num: int = 0
    bbox: Tuple[float, float, float, float] = (0, 0, 0, 0)
    
    @property
    def text(self) -> str:
        """Texto completo del párrafo."""
        return "\n".join(line.text for line in self.lines)
    
    @property
    def original_text(self) -> str:
        """Texto original del párrafo."""
        return "\n".join(line.original_text for line in self.lines)
    
    @property
    def is_dirty(self) -> bool:
        return any(line.is_dirty for line in self.lines)
    
    @property
    def all_spans(self) -> List[EditableSpan]:
        """Todos los spans del párrafo en orden."""
        spans = []
        for line in self.lines:
            spans.extend(line.spans)
        return spans
    
    @classmethod
    def from_text_paragraph(cls, tp: TextParagraph) -> "Paragraph":
        """Crea un Paragraph desde un TextParagraph del text_engine."""
        lines = [LineModel.from_text_line(tl) for tl in tp.lines]
        return cls(
            paragraph_id=tp.paragraph_id,
            lines=lines,
            page_num=tp.page_num,
            bbox=tp.bbox,
        )


class PageDocumentModel:
    """Modelo de documento para una página PDF.
    
    Parsea una página en paragraphs → lines → spans editables,
    preservando todas las propiedades tipográficas originales.
    
    Uso:
        doc = fitz.open("file.pdf")
        page = doc[0]
        model = PageDocumentModel.from_page(page, page_num=0)
        
        # Editar un span
        span = model.find_span_at(x, y)
        if span:
            span.text = "Nuevo texto"
        
        # Obtener spans modificados
        for span in model.dirty_spans:
            ...
    """
    
    def __init__(self):
        self.page_num: int = 0
        self.page_rect: Optional[fitz.Rect] = None
        self.paragraphs: List[Paragraph] = []
        self._span_index: Dict[str, EditableSpan] = {}
    
    @classmethod
    def from_page(cls, page: fitz.Page, page_num: int = 0) -> "PageDocumentModel":
        """Parsea una página PDF y construye el modelo de documento.
        
        Pipeline: page → raw spans → TextSpanMetrics → TextLine → TextParagraph
                  → Paragraph → LineModel → EditableSpan
        """
        model = cls()
        model.page_num = page_num
        model.page_rect = page.rect
        
        # Extraer texto con dict detallado
        text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        
        # Convertir a TextSpanMetrics
        span_metrics = []
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:  # Solo bloques de texto
                continue
            for line_data in block.get("lines", []):
                for span_data in line_data.get("spans", []):
                    sm = create_span_from_pymupdf(span_data, page_num=page_num)
                    if sm and sm.text.strip():
                        span_metrics.append(sm)
        
        if not span_metrics:
            return model
        
        # Agrupar en líneas
        text_lines = group_spans_into_lines(span_metrics)
        
        # Agrupar en párrafos
        text_paragraphs = group_lines_into_paragraphs(text_lines)
        
        # Convertir a modelo editable
        for tp in text_paragraphs:
            para = Paragraph.from_text_paragraph(tp)
            model.paragraphs.append(para)
        
        # Construir índice de spans
        model._build_span_index()
        
        return model
    
    def _build_span_index(self):
        """Construye un índice para búsqueda rápida de spans."""
        self._span_index.clear()
        for para in self.paragraphs:
            for line in para.lines:
                for span in line.spans:
                    self._span_index[span.span_id] = span
    
    @property
    def all_spans(self) -> List[EditableSpan]:
        """Todos los spans de la página."""
        spans = []
        for para in self.paragraphs:
            spans.extend(para.all_spans)
        return spans
    
    @property
    def all_lines(self) -> List[LineModel]:
        """Todas las líneas de la página."""
        lines = []
        for para in self.paragraphs:
            lines.extend(para.lines)
        return lines
    
    @property
    def dirty_spans(self) -> List[EditableSpan]:
        """Spans que fueron modificados."""
        return [s for s in self.all_spans if s.dirty]
    
    @property
    def is_dirty(self) -> bool:
        """True si hay algún span modificado."""
        return any(p.is_dirty for p in self.paragraphs)
    
    def find_span_at(self, x: float, y: float) -> Optional[EditableSpan]:
        """Encuentra el span en las coordenadas PDF dadas."""
        for span in self.all_spans:
            x0, y0, x1, y1 = span.bbox
            if x0 <= x <= x1 and y0 <= y <= y1:
                return span
        return None
    
    def find_line_at(self, y: float) -> Optional[LineModel]:
        """Encuentra la línea más cercana a la coordenada Y."""
        best_line = None
        best_dist = float('inf')
        for line in self.all_lines:
            _, y0, _, y1 = line.bbox
            if y0 <= y <= y1:
                return line
            dist = min(abs(y - y0), abs(y - y1))
            if dist < best_dist:
                best_dist = dist
                best_line = line
        return best_line
    
    def find_paragraph_at(self, y: float) -> Optional[Paragraph]:
        """Encuentra el párrafo que contiene la coordenada Y."""
        for para in self.paragraphs:
            _, y0, _, y1 = para.bbox
            if y0 <= y <= y1:
                return para
        return None
    
    def get_span_by_id(self, span_id: str) -> Optional[EditableSpan]:
        """Busca un span por su ID."""
        return self._span_index.get(span_id)
    
    def spans_in_rect(self, rect: fitz.Rect) -> List[EditableSpan]:
        """Retorna todos los spans que intersectan con el rectángulo dado."""
        result = []
        for span in self.all_spans:
            x0, y0, x1, y1 = span.bbox
            if (x0 < rect.x1 and x1 > rect.x0 and 
                y0 < rect.y1 and y1 > rect.y0):
                result.append(span)
        return result
    
    def text_in_rect(self, rect: fitz.Rect) -> str:
        """Retorna el texto concatenado de los spans en el rectángulo."""
        spans = self.spans_in_rect(rect)
        return " ".join(s.text for s in spans)
    
    @property
    def full_text(self) -> str:
        """Texto completo de la página."""
        return "\n\n".join(p.text for p in self.paragraphs)

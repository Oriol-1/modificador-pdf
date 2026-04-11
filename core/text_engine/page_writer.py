"""
PageWriter - Escribe spans editados de vuelta al PDF usando fitz.TextWriter.

Implementa la estrategia REDACT_THEN_INSERT con REFLOW:
1. Calcula el nuevo ancho de cada span editado
2. Si hay desbordamiento, desplaza los spans siguientes en la misma línea
3. Si la línea desborda el margen derecho, hace word-wrap a la siguiente línea
4. Desplaza las líneas posteriores hacia abajo si se crearon nuevas líneas
5. Redacta (borra) TODOS los spans afectados
6. Reescribe los spans con TextWriter en sus nuevas posiciones

Uso:
    from core.text_engine.page_writer import PageWriter
    
    writer = PageWriter(doc, page_num=0)
    writer.apply_edits(dirty_spans, paragraph=para)  # con reflow
"""

from typing import List, Tuple, Dict, Optional
import fitz

from .page_document_model import EditableSpan, Paragraph
from .rich_text_writer import RichTextWriter


class PageWriter:
    """Escribe spans editados al PDF con reflow del contenido posterior.
    
    Usa fitz.TextWriter para posicionar texto en las coordenadas
    exactas (originales o desplazadas) preservando tipografía.
    """
    
    # Mapeo de fuentes comunes a nombres base14
    FONT_MAP = {
        'helvetica': 'helv',
        'arial': 'helv',
        'times': 'tiro',
        'times-roman': 'tiro',
        'times new roman': 'tiro',
        'courier': 'cour',
        'courier new': 'cour',
        'symbol': 'symb',
        'zapfdingbats': 'zadb',
    }
    
    def __init__(self, doc: fitz.Document, page_num: int):
        self.doc = doc
        self.page_num = page_num
        self._page: fitz.Page = doc[page_num]
        self._font_cache: Dict[str, fitz.Font] = {}
    
    def apply_edits(self, dirty_spans: List[EditableSpan],
                    paragraph: Optional[Paragraph] = None) -> bool:
        """Aplica ediciones con reflow del párrafo.
        
        Si se proporciona el párrafo, calcula el desplazamiento necesario
        y reescribe TODOS los spans afectados (no solo los dirty).
        
        Args:
            dirty_spans: Spans con dirty=True
            paragraph: Párrafo completo para reflow (opcional)
            
        Returns:
            True si se aplicaron cambios
        """
        if not dirty_spans:
            return False
        
        if paragraph:
            return self._apply_with_reflow(dirty_spans, paragraph)
        
        # Sin párrafo: comportamiento simple (solo dirty spans)
        self._redact_spans(dirty_spans)
        self._write_spans(dirty_spans)
        return True
    
    def _apply_with_reflow(self, dirty_spans: List[EditableSpan],
                           paragraph: Paragraph) -> bool:
        """Aplica ediciones recalculando posiciones de todo el párrafo."""
        
        # 1. Calcular qué spans necesitan reposicionamiento
        reflow_result = self._calculate_reflow(paragraph)
        
        if not reflow_result:
            # Sin desbordamiento: solo reescribir dirty spans
            self._redact_spans(dirty_spans)
            self._write_spans(dirty_spans)
            return True
        
        affected_spans, new_positions = reflow_result
        
        # 2. Redactar TODOS los spans afectados (dirty + desplazados)
        #    Deduplicar por span_id (EditableSpan no es hashable)
        seen = {}
        for s in dirty_spans + affected_spans:
            seen[s.span_id] = s
        all_to_redact = list(seen.values())
        self._redact_spans(all_to_redact)
        
        # 3. Reescribir todos los spans afectados en nuevas posiciones
        self._write_spans_with_positions(dirty_spans, affected_spans, new_positions)
        
        return True
    
    def _calculate_reflow(self, paragraph: Paragraph) -> Optional[
        Tuple[List[EditableSpan], Dict[str, Tuple[float, float]]]
    ]:
        """Calcula si hay desbordamiento y las nuevas posiciones.
        
        Returns:
            None si no hay desbordamiento
            (affected_spans, new_positions) si hay que desplazar
            new_positions es {span_id: (new_origin_x, new_origin_y)}
        """
        page_rect = self._page.rect
        right_margin = page_rect.width - 36  # 36pt = ~0.5 inch margen derecho
        
        affected_spans: List[EditableSpan] = []
        new_positions: Dict[str, Tuple[float, float]] = {}
        has_overflow = False
        
        # Calcular el interlineado del párrafo
        line_spacing = self._get_line_spacing(paragraph)
        
        # Procesar línea por línea
        accumulated_y_shift = 0.0
        
        for line_idx, line in enumerate(paragraph.lines):
            if not line.spans:
                continue
            
            # Calcular desbordamiento horizontal en esta línea
            x_shift = 0.0
            line_left_margin = line.spans[0].bbox[0]  # Margen izquierdo de la línea
            
            for span_idx, span in enumerate(line.spans):
                original_width = span.bbox[2] - span.bbox[0]
                
                if span.is_dirty:
                    # Span editado: calcular delta de ancho
                    new_width = self._measure_text_width(span)
                    width_delta = new_width - original_width
                    
                    # Si hay desplazamiento previo, este dirty span también debe moverse
                    if abs(x_shift) > 0.5 or abs(accumulated_y_shift) > 0.5:
                        new_x = span.origin[0] + x_shift
                        new_y = span.origin[1] + accumulated_y_shift
                        new_positions[span.span_id] = (new_x, new_y)
                        affected_spans.append(span)
                    
                    if abs(width_delta) > 0.5:
                        has_overflow = True
                        x_shift += width_delta
                else:
                    # Span no editado: aplicar desplazamiento acumulado
                    if abs(x_shift) > 0.5 or abs(accumulated_y_shift) > 0.5:
                        new_x = span.origin[0] + x_shift
                        new_y = span.origin[1] + accumulated_y_shift
                        
                        # Verificar desbordamiento del margen derecho
                        span_width = original_width
                        if new_x + span_width > right_margin:
                            # Wrap: mover a nueva línea
                            new_x = line_left_margin
                            accumulated_y_shift += line_spacing
                            new_y = span.origin[1] + accumulated_y_shift
                            x_shift = 0.0
                        
                        new_positions[span.span_id] = (new_x, new_y)
                        affected_spans.append(span)
        
        if not has_overflow:
            return None
        
        return (affected_spans, new_positions)
    
    def _measure_text_width(self, span: EditableSpan) -> float:
        """Mide el ancho del texto actual del span usando la fuente correcta."""
        is_bold = span.effective_is_bold
        font_size = span.effective_font_size
        font = self._resolve_font(span.font_name, span.font_name_pdf, is_bold)
        try:
            width = font.text_length(span.text, fontsize=font_size)
            # Añadir efectos de char_spacing/word_spacing
            char_sp = span.effective_char_spacing
            if abs(char_sp) > 0.001 and len(span.text) > 1:
                width += char_sp * (len(span.text) - 1)
            word_sp = span.effective_word_spacing
            if abs(word_sp) > 0.001:
                width += word_sp * span.text.count(' ')
            return width
        except Exception:
            # Fallback: estimación basada en caracteres
            return len(span.text) * font_size * 0.6
    
    def _get_line_spacing(self, paragraph: Paragraph) -> float:
        """Calcula el interlineado típico del párrafo."""
        if len(paragraph.lines) < 2:
            # Single line: estimar desde font_size
            if paragraph.lines and paragraph.lines[0].spans:
                return paragraph.lines[0].spans[0].font_size * 1.2
            return 14.0
        
        spacings = []
        for i in range(len(paragraph.lines) - 1):
            gap = paragraph.lines[i + 1].baseline_y - paragraph.lines[i].baseline_y
            if gap > 0:
                spacings.append(gap)
        
        if spacings:
            return sum(spacings) / len(spacings)
        return 14.0
    
    def _write_spans_with_positions(
        self,
        dirty_spans: List[EditableSpan],
        affected_spans: List[EditableSpan],
        new_positions: Dict[str, Tuple[float, float]]
    ):
        """Reescribe spans dirty en su posición original y affected en nueva posición."""
        # Combinar todos los spans a escribir (dedup por span_id)
        seen = {}
        for s in dirty_spans + affected_spans:
            seen[s.span_id] = s
        all_spans = list(seen.values())
        
        # Agrupar por color
        color_groups: Dict[Tuple[float, float, float], List[EditableSpan]] = {}
        for span in all_spans:
            color = span.color_rgb
            if color not in color_groups:
                color_groups[color] = []
            color_groups[color].append(span)
        
        for color, group_spans in color_groups.items():
            # Separar spans con/sin cambios de formato
            fmt_spans = [s for s in group_spans if s.dirty_format]
            std_spans = [s for s in group_spans if not s.dirty_format]
            
            # Spans con formato → RichTextWriter
            if fmt_spans:
                rtw = RichTextWriter(self._page, self.doc)
                for span in fmt_spans:
                    if span.span_id in new_positions:
                        # Crear rect desplazado
                        px, py = new_positions[span.span_id]
                        w = span.bbox[2] - span.bbox[0]
                        h = span.bbox[3] - span.bbox[1]
                        rect = fitz.Rect(px - 0.5, py - h, px + w + 0.5, py + 0.5)
                    else:
                        rect = None
                    rtw.write_spans([span], rect=rect)
            
            # Spans sin formato → TextWriter estándar
            if std_spans:
                tw = fitz.TextWriter(self._page.rect)
                
                for span in std_spans:
                    font = self._resolve_font(span.font_name, span.font_name_pdf, span.is_bold)
                    
                    if span.span_id in new_positions:
                        px, py = new_positions[span.span_id]
                        point = fitz.Point(px, py)
                    else:
                        point = fitz.Point(span.origin[0], span.origin[1])
                    
                    try:
                        tw.append(point, span.text, font=font, fontsize=span.font_size)
                    except Exception as e:
                        fallback_font = self._get_font('helv')
                        try:
                            tw.append(point, span.text, font=fallback_font, fontsize=span.font_size)
                        except Exception:
                            print(f"PageWriter: No se pudo escribir span '{span.text[:20]}': {e}")
                            continue
                
                tw.write_text(self._page, color=color)
    
    def _redact_spans(self, spans: List[EditableSpan]):
        """Redacta (borra) las áreas de los spans originales."""
        for span in spans:
            x0, y0, x1, y1 = span.bbox
            rect = fitz.Rect(x0, y0, x1, y1)
            # No expandir para evitar borrar texto adyacente
            # Añadir redaction sin fill visible (transparent)
            self._page.add_redact_annot(rect, fill=False)
        
        # Aplicar todas las redacciones de una vez
        self._page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
    
    def _write_spans(self, spans: List[EditableSpan]):
        """Reescribe los spans editados.
        
        Si hay cambios de formato, usa RichTextWriter (insert_htmlbox).
        Si no, usa TextWriter estándar.
        """
        # Separar spans con y sin cambios de formato
        format_spans = [s for s in spans if s.dirty_format]
        text_only_spans = [s for s in spans if not s.dirty_format]
        
        # Escribir spans con formato usando RichTextWriter
        if format_spans:
            rtw = RichTextWriter(self._page, self.doc)
            for span in format_spans:
                result = rtw.write_single_span(span)
                if not result.success:
                    # Fallback a TextWriter estándar
                    self._write_spans_textwriter([span])
        
        # Escribir spans sin formato usando TextWriter estándar
        if text_only_spans:
            self._write_spans_textwriter(text_only_spans)
    
    def _write_spans_textwriter(self, spans: List[EditableSpan]):
        """Reescribe spans usando TextWriter estándar (sin formato nuevo)."""
        color_groups: Dict[Tuple[float, float, float], List[EditableSpan]] = {}
        for span in spans:
            color = span.color_rgb
            if color not in color_groups:
                color_groups[color] = []
            color_groups[color].append(span)
        
        for color, group_spans in color_groups.items():
            tw = fitz.TextWriter(self._page.rect)
            
            for span in group_spans:
                font = self._resolve_font(span.font_name, span.font_name_pdf, span.is_bold)
                point = fitz.Point(span.origin[0], span.origin[1])
                
                try:
                    tw.append(point, span.text, font=font, fontsize=span.font_size)
                except Exception as e:
                    fallback_font = self._get_font('helv')
                    try:
                        tw.append(point, span.text, font=fallback_font, fontsize=span.font_size)
                    except Exception:
                        print(f"PageWriter: No se pudo escribir span '{span.text[:20]}': {e}")
                        continue
            
            tw.write_text(self._page, color=color)
    
    def write_single_span(self, span: EditableSpan) -> bool:
        """Escribe un solo span al PDF (para uso incremental)."""
        # Usar RichTextWriter si hay cambios de formato
        if span.dirty_format:
            rtw = RichTextWriter(self._page, self.doc)
            result = rtw.write_single_span(span)
            return result.success
        
        font = self._resolve_font(span.font_name, span.font_name_pdf, span.is_bold)
        tw = fitz.TextWriter(self._page.rect)
        point = fitz.Point(span.origin[0], span.origin[1])
        color = span.color_rgb
        
        try:
            tw.append(point, span.text, font=font, fontsize=span.font_size)
            tw.write_text(self._page, color=color)
            return True
        except Exception as e:
            print(f"PageWriter: Error escribiendo span: {e}")
            return False
    
    def erase_rect(self, rect: fitz.Rect):
        """Borra un área rectangular de la página."""
        expanded = rect + (-0.5, -0.5, 0.5, 0.5)
        self._page.add_redact_annot(expanded, fill=(1, 1, 1))
        self._page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
    
    def _resolve_font(self, font_name: str, font_name_pdf: str, is_bold: bool) -> fitz.Font:
        """Resuelve la fuente a usar, intentando la embebida primero."""
        if font_name_pdf:
            try:
                fonts = self._page.get_fonts()
                for f_entry in fonts:
                    xref = f_entry[0]
                    name = f_entry[3] if len(f_entry) > 3 else ''
                    clean_name = name.split('+')[-1] if '+' in name else name
                    if clean_name == font_name_pdf or name == font_name_pdf:
                        cached = self._font_cache.get(f"embedded_{xref}")
                        if cached:
                            return cached
                        try:
                            font = fitz.Font(fontbuffer=self.doc.extract_font(xref)[-1])
                            self._font_cache[f"embedded_{xref}"] = font
                            return font
                        except Exception:
                            break
            except Exception:
                pass
        
        base_name = self._map_to_base14(font_name, is_bold)
        return self._get_font(base_name)
    
    def _map_to_base14(self, font_name: str, is_bold: bool) -> str:
        """Mapea un nombre de fuente a base14."""
        name_lower = font_name.lower().strip()
        
        for key, value in self.FONT_MAP.items():
            if key in name_lower:
                base = value
                if is_bold:
                    bold_map = {'helv': 'hebo', 'tiro': 'tibo', 'cour': 'cobo'}
                    return bold_map.get(base, base)
                return base
        
        return 'hebo' if is_bold else 'helv'
    
    def _get_font(self, base14_name: str) -> fitz.Font:
        """Obtiene una fuente base14, usando cache."""
        if base14_name not in self._font_cache:
            self._font_cache[base14_name] = fitz.Font(base14_name)
        return self._font_cache[base14_name]

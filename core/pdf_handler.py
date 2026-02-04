"""
Módulo de manipulación de PDF usando PyMuPDF (fitz)
Maneja la lectura, edición y guardado de documentos PDF preservando estructura y formularios.
"""

import fitz  # PyMuPDF
from typing import List, Tuple, Optional, Dict, Any
import copy
import tempfile
import os

# Importar modelos de datos
from .models import TextBlock, EditOperation

# Intentar importar pikepdf para reparación de PDFs
try:
    import pikepdf  # type: ignore[import-unresolved]
    PIKEPDF_AVAILABLE = True
except ImportError:
    PIKEPDF_AVAILABLE = False


class PDFDocument:
    """Clase principal para manejar documentos PDF."""
    
    def __init__(self):
        self.doc: Optional[fitz.Document] = None
        self.file_path: Optional[str] = None
        self.modified: bool = False
        # Sistema de deshacer/rehacer basado en snapshots
        # Cada snapshot es una tupla: (pdf_bytes, overlay_data)
        self._undo_snapshots: List[tuple] = []  # Lista de estados anteriores
        self._redo_snapshots: List[tuple] = []  # Lista de estados para rehacer
        self._original_doc_bytes: Optional[bytes] = None
        self._last_error: str = ""
        self._max_undo_levels = 20  # Máximo de niveles de deshacer
        # Callback para obtener/restaurar estado de overlays del viewer
        self._get_overlay_state_callback = None
        self._restore_overlay_state_callback = None
        
    def open(self, file_path: str) -> bool:
        """Abre un documento PDF."""
        try:
            # Cerrar documento anterior si existe
            if self.doc:
                try:
                    self.doc.close()
                except:
                    pass
                self.doc = None
            
            # Limpiar estado
            self.file_path = None
            self.modified = False
            self._undo_snapshots.clear()
            self._redo_snapshots.clear()
            self._original_doc_bytes = None
            self._last_error = ""
            
            # Intentar abrir el documento
            self.doc = fitz.open(file_path)
            
            # Verificar que el documento tiene páginas
            if self.doc.page_count == 0:
                # Intentar reparar el PDF
                self._last_error = "PDF sin páginas, intentando reparar..."
                repaired = self._try_repair_pdf(file_path)
                if repaired:
                    self.doc = repaired
                else:
                    self._last_error = "El PDF está dañado o corrupto y no se pudo reparar."
                    self.doc = None
                    return False
            
            self.file_path = file_path
            # Guardar copia original para restauración (deshacer)
            try:
                self._original_doc_bytes = self.doc.tobytes(garbage=0, deflate=True)
            except Exception as e:
                print(f"No se pudo guardar copia para deshacer: {e}")
                self._original_doc_bytes = None
            return True
        except Exception as e:
            self._last_error = str(e)
            print(f"Error al abrir PDF: {e}")
            self.doc = None
            return False
    
    def _try_repair_pdf(self, file_path: str):
        """Intenta reparar un PDF dañado usando múltiples métodos."""
        
        # Método 1: Usar pikepdf (más tolerante a errores)
        if PIKEPDF_AVAILABLE:
            try:
                pdf = pikepdf.open(file_path)
                if len(pdf.pages) > 0:
                    # Guardar versión reparada a un archivo temporal
                    temp_file = tempfile.mktemp(suffix='.pdf')
                    pdf.save(temp_file, linearize=True)
                    pdf.close()
                    
                    # Abrir con fitz
                    repaired_doc = fitz.open(temp_file)
                    if repaired_doc.page_count > 0:
                        # Leer a memoria y borrar temp
                        pdf_bytes = repaired_doc.tobytes()
                        repaired_doc.close()
                        os.remove(temp_file)
                        
                        # Reabrir desde memoria
                        final_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                        return final_doc
                    
                    repaired_doc.close()
                    os.remove(temp_file)
                pdf.close()
            except Exception as e:
                print(f"pikepdf repair failed: {e}")
        
        # Método 2: fitz con garbage collection
        try:
            doc = fitz.open(file_path)
            pdf_bytes = doc.tobytes(garbage=4, deflate=True, clean=True)
            doc.close()
            
            repaired_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            if repaired_doc.page_count > 0:
                return repaired_doc
            repaired_doc.close()
        except:
            pass
        
        # Método 3: Leer como bytes directamente
        try:
            with open(file_path, 'rb') as f:
                pdf_bytes = f.read()
            
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            if doc.page_count > 0:
                return doc
            doc.close()
        except:
            pass
        
        return None
    
    def get_last_error(self) -> str:
        """Retorna el último error ocurrido."""
        return self._last_error
    
    def close(self):
        """Cierra el documento actual."""
        if self.doc:
            try:
                self.doc.close()
            except:
                pass
        self.doc = None
        self.file_path = None
        self.modified = False
        self._undo_snapshots.clear()
        self._redo_snapshots.clear()
        self._original_doc_bytes = None
    
    def is_open(self) -> bool:
        """Verifica si hay un documento abierto."""
        return self.doc is not None
    
    def has_real_text(self) -> bool:
        """Verifica si el PDF tiene texto real (no es solo imagen)."""
        if not self.doc:
            return False
        
        # Verificar las primeras páginas
        for page_num in range(min(3, self.doc.page_count)):
            page = self.doc[page_num]
            text = page.get_text("text")
            if text.strip():
                return True
        return False
    
    def get_text_content_preview(self) -> str:
        """Obtiene una vista previa del contenido de texto del PDF."""
        if not self.doc:
            return ""
        
        text = ""
        for page_num in range(min(3, self.doc.page_count)):
            page = self.doc[page_num]
            page_text = page.get_text("text")
            if page_text.strip():
                text += f"[Página {page_num + 1}]: {page_text[:200]}...\n"
        return text if text else "No se encontró texto en este PDF"
    
    def page_count(self) -> int:
        """Retorna el número de páginas."""
        return self.doc.page_count if self.doc else 0
    
    def get_page(self, page_num: int) -> Optional[fitz.Page]:
        """Obtiene una página específica."""
        if self.doc and 0 <= page_num < self.doc.page_count:
            return self.doc[page_num]
        return None
    
    def render_page(self, page_num: int, zoom: float = 1.0) -> Optional[fitz.Pixmap]:
        """Renderiza una página como imagen."""
        page = self.get_page(page_num)
        if page:
            mat = fitz.Matrix(zoom, zoom)
            return page.get_pixmap(matrix=mat, alpha=False)
        return None
    
    def get_text_blocks(self, page_num: int, visual_coords: bool = False) -> List[TextBlock]:
        """
        Obtiene todos los bloques de texto de una página con su información de formato.
        
        Args:
            page_num: Número de página
            visual_coords: Si True, transforma las coordenadas internas a visuales
        """
        page = self.get_page(page_num)
        if not page:
            return []
        
        blocks = []
        rotation = page.rotation if page else 0
        
        try:
            text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            
            for block_no, block in enumerate(text_dict.get("blocks", [])):
                if block.get("type") != 0:  # Solo bloques de texto
                    continue
                    
                for line_no, line in enumerate(block.get("lines", [])):
                    for span_no, span in enumerate(line.get("spans", [])):
                        text = span.get("text", "")
                        if not text.strip():  # Saltar spans vacíos
                            continue
                            
                        rect = fitz.Rect(span["bbox"])
                        
                        # Transformar a coordenadas visuales si es necesario
                        if visual_coords and rotation != 0:
                            rect = self.transform_rect_for_page(page_num, rect, from_visual=False)
                        
                        color = span.get("color", 0)
                        # Convertir color entero a RGB
                        if isinstance(color, int):
                            r = ((color >> 16) & 255) / 255.0
                            g = ((color >> 8) & 255) / 255.0
                            b = (color & 255) / 255.0
                        else:
                            r, g, b = 0, 0, 0
                        
                        blocks.append(TextBlock(
                            text=text,
                            rect=rect,
                            font_name=span.get("font", ""),
                            font_size=span.get("size", 12),
                            color=(r, g, b),
                            flags=span.get("flags", 0),
                            page_num=page_num,
                            block_no=block_no,
                            line_no=line_no,
                            span_no=span_no
                        ))
        except Exception as e:
            pass
        
        return blocks
    
    def find_text_at_point(self, page_num: int, point: Tuple[float, float], use_visual_coords: bool = True) -> Optional[TextBlock]:
        """
        Encuentra el texto en un punto específico.
        
        Args:
            page_num: Número de página
            point: Punto en coordenadas (visuales si use_visual_coords=True)
            use_visual_coords: Si True, usa coordenadas visuales para la búsqueda
        
        Returns:
            TextBlock con coordenadas visuales Y coordenadas internas (internal_rect)
        """
        pt = fitz.Point(point)
        
        if use_visual_coords:
            # Obtener bloques con coordenadas visuales transformadas
            visual_blocks = self.get_text_blocks(page_num, visual_coords=True)
            # También obtener bloques con coordenadas internas para referencia
            internal_blocks = self.get_text_blocks(page_num, visual_coords=False)
        else:
            # Bloques con coordenadas internas
            visual_blocks = self.get_text_blocks(page_num, visual_coords=False)
            internal_blocks = visual_blocks
        
        # Buscar en los bloques visuales
        for i, block in enumerate(visual_blocks):
            if block.rect.contains(pt):
                # Añadir las coordenadas internas al bloque encontrado
                if i < len(internal_blocks):
                    block.internal_rect = internal_blocks[i].rect
                else:
                    block.internal_rect = block.rect
                return block
        
        # Si no encontramos con contains, intentar con una búsqueda más tolerante
        # (útil para textos pequeños o bordes)
        tolerance = 5
        for i, block in enumerate(visual_blocks):
            expanded_rect = fitz.Rect(
                block.rect.x0 - tolerance,
                block.rect.y0 - tolerance,
                block.rect.x1 + tolerance,
                block.rect.y1 + tolerance
            )
            if expanded_rect.contains(pt):
                # Añadir las coordenadas internas al bloque encontrado
                if i < len(internal_blocks):
                    block.internal_rect = internal_blocks[i].rect
                else:
                    block.internal_rect = block.rect
                return block
        
        return None
    
    def find_text_in_rect(self, page_num: int, rect: fitz.Rect) -> List[TextBlock]:
        """Encuentra todos los bloques de texto que intersectan con un rectángulo."""
        blocks = self.get_text_blocks(page_num)
        result = []
        
        # Expandir el rectángulo significativamente para mejor detección
        expanded_rect = fitz.Rect(
            rect.x0 - 10,
            rect.y0 - 10,
            rect.x1 + 10,
            rect.y1 + 10
        )
        
        for block in blocks:
            # Verificar si el bloque intersecta con el rectángulo
            if expanded_rect.intersects(block.rect):
                result.append(block)
        
        # Si no encontramos nada, intentar con el método de clip directo de PyMuPDF
        if not result:
            page = self.get_page(page_num)
            if page:
                # Usar el método de texto con clip
                text = page.get_text("text", clip=expanded_rect)
                if text.strip():
                    # Crear un bloque de texto genérico con el texto encontrado
                    result.append(TextBlock(
                        text=text.strip(),
                        rect=rect,
                        font_name="",
                        font_size=12,
                        color=(0, 0, 0),
                        flags=0,
                        page_num=page_num,
                        block_no=0,
                        line_no=0,
                        span_no=0
                    ))
        
        return result
    
    def search_text(self, text: str, page_num: Optional[int] = None) -> List[Tuple[int, fitz.Rect]]:
        """Busca texto en el documento."""
        results = []
        
        if page_num is not None:
            pages = [page_num]
        else:
            pages = range(self.page_count())
        
        for pn in pages:
            page = self.get_page(pn)
            if page:
                for rect in page.search_for(text):
                    results.append((pn, rect))
        
        return results
    
    def highlight_text(self, page_num: int, rect: fitz.Rect, color: Tuple[float, float, float] = (1, 1, 0)) -> bool:
        """
        Resalta un área específica del PDF usando Shape (sin anotaciones para evitar duplicados).
        
        Args:
            page_num: Número de página
            rect: Área a resaltar (en coordenadas visuales)
            color: Color del resaltado (RGB 0-1)
            
        Returns:
            True si se resaltó correctamente
        """
        page = self.get_page(page_num)
        if not page:
            return False
        
        try:
            # Guardar snapshot antes de modificar
            self._save_snapshot()
            
            rotation = page.rotation
            print(f"highlight_text - Rect visual: {rect}, Rotación: {rotation}°")
            
            # Transformar coordenadas de visual a mediabox
            transformed_rect = self.transform_rect_for_page(page_num, rect, from_visual=True)
            print(f"highlight_text - Rect transformado: {transformed_rect}")
            
            # Usar SOLO Shape para dibujar (sin anotaciones que causan duplicados)
            shape = page.new_shape()
            shape.draw_rect(transformed_rect)
            shape.finish(
                color=None,
                fill=color,
                fill_opacity=0.3
            )
            shape.commit(overlay=True)
            
            # Guardar información del highlight en memoria para poder detectarlo después
            if not hasattr(self, '_highlights'):
                self._highlights = {}
            if page_num not in self._highlights:
                self._highlights[page_num] = []
            
            self._highlights[page_num].append({
                'visual_rect': rect,
                'internal_rect': transformed_rect,
                'color': color
            })
            
            self.modified = True
            print(f"Highlight aplicado (solo Shape, sin anotación)")
            return True
                
        except Exception as e:
            print(f"Error al resaltar: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_highlights_at_point(self, page_num: int, point: Tuple[float, float]) -> List[dict]:
        """
        Busca highlights en un punto específico (coordenadas internas).
        """
        if not hasattr(self, '_highlights') or page_num not in self._highlights:
            return []
        
        pt = fitz.Point(point)
        found = []
        for hl in self._highlights[page_num]:
            if hl['internal_rect'].contains(pt):
                found.append(hl)
        return found
    
    def remove_last_highlight(self, page_num: int) -> bool:
        """
        Elimina el último highlight de la página usando undo.
        """
        if hasattr(self, '_highlights') and page_num in self._highlights and self._highlights[page_num]:
            # Quitar de la lista
            self._highlights[page_num].pop()
            # Usar undo para quitar el Shape
            return self.undo()
        return False
    
    def get_highlight_annotations(self, page_num: int) -> List[dict]:
        """
        Obtiene todas las anotaciones de resaltado de una página.
        Busca tanto Highlight (tipo 8) como Square/Rect (tipo 4) con relleno amarillo.
        
        Args:
            page_num: Número de página
            
        Returns:
            Lista de diccionarios con información de cada resaltado
        """
        page = self.get_page(page_num)
        if not page:
            return []
        
        highlights = []
        try:
            annots = page.annots()
            if annots:  # Verificar que no sea None
                for annot in annots:
                    annot_type = annot.type[0]
                    # Tipo 8 = Highlight annotation tradicional
                    # Tipo 4 = Square/Rect annotation (lo que usamos para resaltar PDFs escaneados)
                    if annot_type == 8:
                        highlights.append({
                            'rect': annot.rect,
                            'color': annot.colors.get('stroke', (1, 1, 0)),
                            'xref': annot.xref,
                            'content': annot.info.get('content', ''),
                            'type': 'highlight'
                        })
                    elif annot_type == 4:  # Square annotation - usado para resaltar
                        # Verificar que tiene color de relleno amarillento (es un highlight)
                        fill_color = annot.colors.get('fill', None)
                        if fill_color and len(fill_color) >= 3:
                            # Amarillo o cercano: R alto, G alto, B bajo
                            if fill_color[0] > 0.7 and fill_color[1] > 0.7 and fill_color[2] < 0.5:
                                highlights.append({
                                    'rect': annot.rect,
                                    'color': fill_color,
                                    'xref': annot.xref,
                                    'content': annot.info.get('content', ''),
                                    'type': 'rect_highlight'
                                })
                                print(f"Encontrado rect_highlight: {annot.rect}")
        except Exception as e:
            print(f"Error obteniendo resaltados: {e}")
        
        return highlights
    
    def remove_highlight_at_point(self, page_num: int, point: Tuple[float, float]) -> bool:
        """
        Elimina una anotación de resaltado en un punto específico.
        Detecta tanto Highlight (tipo 8) como Square/Rect (tipo 4) amarillos.
        
        Args:
            page_num: Número de página
            point: Coordenadas (x, y) del punto (en coordenadas visuales)
            
        Returns:
            True si se eliminó algún resaltado
        """
        page = self.get_page(page_num)
        if not page:
            return False
        
        try:
            pt = fitz.Point(point)
            print(f"remove_highlight_at_point - Buscando en punto: {pt}")
            
            annots = page.annots()
            if annots:
                for annot in annots:
                    annot_type = annot.type[0]
                    is_highlight = False
                    
                    # Tipo 8 = Highlight annotation tradicional
                    if annot_type == 8:
                        is_highlight = True
                    # Tipo 4 = Square/Rect annotation amarillo
                    elif annot_type == 4:
                        fill_color = annot.colors.get('fill', None)
                        if fill_color and len(fill_color) >= 3:
                            if fill_color[0] > 0.7 and fill_color[1] > 0.7 and fill_color[2] < 0.5:
                                is_highlight = True
                    
                    if is_highlight:
                        # Las anotaciones usan coordenadas visuales
                        if annot.rect.contains(pt):
                            print(f"remove_highlight_at_point - Encontrado y eliminando: {annot.rect}")
                            self._save_snapshot()
                            page.delete_annot(annot)
                            self.modified = True
                            return True
            
            print(f"remove_highlight_at_point - No se encontró resaltado en el punto")
        except Exception as e:
            print(f"Error eliminando resaltado: {e}")
        
        return False
    
    def remove_highlight_in_rect(self, page_num: int, rect: fitz.Rect) -> bool:
        """
        Elimina todas las anotaciones de resaltado que intersectan con un rectángulo.
        Detecta tanto Highlight (tipo 8) como Square/Rect (tipo 4) amarillos.
        
        Args:
            page_num: Número de página
            rect: Rectángulo de selección
            
        Returns:
            True si se eliminó algún resaltado
        """
        page = self.get_page(page_num)
        if not page:
            return False
        
        try:
            removed = False
            annots_to_remove = []
            
            # Primero recopilar las anotaciones a eliminar
            annots = page.annots()
            if annots:  # Verificar que no sea None
                for annot in annots:
                    annot_type = annot.type[0]
                    is_highlight = False
                    
                    # Tipo 8 = Highlight annotation tradicional
                    if annot_type == 8:
                        is_highlight = True
                    # Tipo 4 = Square/Rect annotation amarillo
                    elif annot_type == 4:
                        fill_color = annot.colors.get('fill', None)
                        if fill_color and len(fill_color) >= 3:
                            if fill_color[0] > 0.7 and fill_color[1] > 0.7 and fill_color[2] < 0.5:
                                is_highlight = True
                    
                    if is_highlight and rect.intersects(annot.rect):
                        annots_to_remove.append(annot)
            
            if annots_to_remove:
                # Guardar snapshot antes de modificar
                self._save_snapshot()
                
                # Eliminar las anotaciones
                for annot in annots_to_remove:
                    page.delete_annot(annot)
                    removed = True
                
                if removed:
                    self.modified = True
            
            return removed
        except Exception as e:
            print(f"Error eliminando resaltados: {e}")
        
        return False

    def delete_text(self, page_num: int, rect: fitz.Rect) -> bool:
        """
        Elimina texto de un área específica de forma permanente.
        El texto se elimina completamente del contenido del PDF.
        """
        page = self.get_page(page_num)
        if not page:
            return False
        
        try:
            # Guardar snapshot antes de modificar
            self._save_snapshot()
            
            # Usar redacción para eliminación real
            redact_annot = page.add_redact_annot(rect, fill=(1, 1, 1))  # Fondo blanco
            page.apply_redactions()
            
            self.modified = True
            return True
        except Exception as e:
            print(f"Error al eliminar texto: {e}")
            return False
    
    def erase_text_transparent(self, page_num: int, rect: fitz.Rect, save_snapshot: bool = True, already_internal: bool = False) -> bool:
        """
        Elimina texto de un área sin dejar marca visible (transparente).
        Útil para mover texto en PDFs con texto editable sin dejar rectángulos blancos.
        
        Args:
            page_num: Número de página
            rect: Área del texto a eliminar
            save_snapshot: Si True, guarda snapshot para undo
            already_internal: Si True, las coordenadas ya están en formato interno del PDF
                              (no se aplica transformación). Usar cuando rect viene de
                              find_text_at_point con internal_rect.
        
        Returns:
            True si se eliminó correctamente
        """
        page = self.get_page(page_num)
        if not page:
            return False
        
        try:
            if save_snapshot:
                self._save_snapshot()
            
            # Transformar coordenadas si hay rotación Y si no son ya internas
            if already_internal:
                transformed_rect = rect
                print(f"erase_text_transparent - Rect ya interno (sin transformar): {rect}")
            else:
                transformed_rect = self.transform_rect_for_page(page_num, rect, from_visual=True)
                print(f"erase_text_transparent - Rect visual: {rect}")
                print(f"erase_text_transparent - Rect transformado: {transformed_rect}")
            
            # NO expandir el rect para evitar borrar texto adyacente
            # El rect debe ser preciso para borrar solo lo necesario
            print(f"erase_text_transparent - Usando rect preciso: {transformed_rect}")
            
            # Verificar qué texto hay en esa área antes de borrar
            text_in_area = page.get_text("text", clip=transformed_rect)
            print(f"erase_text_transparent - Texto en área ANTES de borrar: '{text_in_area.strip()}'")
            
            # Usar redacción SIN color de relleno (transparente)
            # fill=False significa sin relleno
            redact = page.add_redact_annot(transformed_rect, fill=False)
            page.apply_redactions()
            
            # Verificar qué texto hay después de borrar
            text_after = page.get_text("text", clip=transformed_rect)
            print(f"erase_text_transparent - Texto en área DESPUÉS de borrar: '{text_after.strip()}'")
            
            # Refrescar el documento para que los cambios sean visibles
            self._refresh_document()
            
            self.modified = True
            print(f"Texto eliminado transparentemente en: {transformed_rect}")
            return True
            
        except Exception as e:
            print(f"Error en erase_text_transparent: {e}")
            import traceback
            traceback.print_exc()
            return False

    def erase_area(self, page_num: int, rect: fitz.Rect, color: Tuple[float, float, float] = (1, 1, 1), save_snapshot: bool = True, use_redaction: bool = True) -> bool:
        """
        Borra un área del PDF.
        
        Args:
            page_num: Número de página
            rect: Área a borrar (en coordenadas visuales/de pixmap)
            color: Color de relleno (por defecto blanco)
            save_snapshot: Si True, guarda snapshot para undo (por defecto True)
            use_redaction: Si True, usa redacción para eliminar texto realmente (por defecto True)
        
        Returns:
            True si se borró correctamente
        """
        page = self.get_page(page_num)
        if not page:
            return False
        
        try:
            # Guardar snapshot antes de modificar (si se requiere)
            if save_snapshot:
                self._save_snapshot()
            
            # CRUCIAL: Transformar coordenadas si la página tiene rotación
            # Las coordenadas que recibimos son "visuales" (del pixmap)
            # Necesitamos convertirlas a coordenadas internas del PDF
            transformed_rect = self.transform_rect_for_page(page_num, rect, from_visual=True)
            
            print(f"erase_area - Rect original (visual): {rect}")
            print(f"erase_area - Rect transformado (interno): {transformed_rect}")
            
            # Detectar si es un PDF de imagen
            is_image_pdf = self.is_image_based_pdf()
            
            # Para PDFs de texto: usar redacción para ELIMINAR realmente el texto
            # Esto evita que find_text_at_point encuentre el texto "borrado"
            if use_redaction and not is_image_pdf:
                try:
                    redact = page.add_redact_annot(transformed_rect, fill=color)
                    page.apply_redactions()
                    self._refresh_document()
                    self.modified = True
                    print(f"Área borrada con redacción (texto eliminado): {transformed_rect}")
                    return True
                except Exception as e:
                    print(f"Redacción falló: {e}, usando shape como fallback")
            
            # Para PDFs de imagen o como fallback: usar shape
            try:
                shape = page.new_shape()
                shape.draw_rect(transformed_rect)
                shape.finish(color=color, fill=color)
                shape.commit()
                self.modified = True
                print(f"Área cubierta con shape: {transformed_rect}")
                return True
            except Exception as e:
                print(f"Shape falló: {e}")
            
            return False
        except Exception as e:
            print(f"Error al borrar área: {e}")
            return False
    
    def _refresh_document(self):
        """
        Refresca el documento en memoria para que los cambios sean visibles.
        Necesario después de apply_redactions() para actualizar la visualización.
        """
        if not self.doc:
            return
        
        try:
            # Guardar el documento a bytes
            pdf_bytes = self.doc.tobytes(garbage=0)
            
            # Cerrar el documento actual
            self.doc.close()
            
            # Reabrir desde los bytes
            self.doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            print("Documento refrescado para mostrar cambios")
        except Exception as e:
            print(f"Error refrescando documento: {e}")
    
    def is_image_based_pdf(self) -> bool:
        """
        Detecta si el PDF es principalmente basado en imágenes (escaneado).
        
        Un PDF se considera basado en imágenes si:
        1. Tiene imágenes que cubren la mayor parte de la página (típico de escaneos)
        2. Las imágenes son grandes (más de 1000x1000 píxeles)
        
        NO se considera PDF de imagen si solo tiene logos, iconos o imágenes pequeñas.
        
        Returns:
            True si el PDF parece ser escaneado/basado en imágenes
        """
        if not self.doc:
            return False
        
        for page_num in range(min(3, self.doc.page_count)):
            page = self.doc[page_num]
            page_rect = page.rect
            page_area = page_rect.width * page_rect.height
            
            # Analizar imágenes en la página
            images = page.get_images(full=True)
            
            for img in images:
                try:
                    xref = img[0]
                    # Obtener las dimensiones de la imagen
                    img_info = self.doc.extract_image(xref)
                    if img_info:
                        img_width = img_info.get('width', 0)
                        img_height = img_info.get('height', 0)
                        
                        # Una imagen escaneada típicamente tiene alta resolución
                        # Para A4 a 300 DPI: ~2480 x 3508 píxeles
                        # Para A4 a 150 DPI: ~1240 x 1754 píxeles
                        # Usamos un umbral de 1000x1000 para detectar páginas escaneadas
                        if img_width > 1000 and img_height > 1000:
                            print(f"is_image_based_pdf: Detectada imagen grande {img_width}x{img_height} - ES PDF de imagen")
                            return True
                except Exception:
                    continue
        
        # No se encontraron imágenes grandes, es un PDF editable normal
        print(f"is_image_based_pdf: No hay imágenes grandes - NO es PDF de imagen")
        return False
    
    def get_page_images(self, page_num: int) -> List[dict]:
        """
        Obtiene información sobre las imágenes en una página.
        
        Returns:
            Lista de diccionarios con información de cada imagen
        """
        page = self.get_page(page_num)
        if not page:
            return []
        
        images_info = []
        images = page.get_images(full=True)
        
        for img_index, img in enumerate(images):
            xref = img[0]
            try:
                # Obtener el rectángulo de la imagen en la página
                img_rects = page.get_image_rects(xref)
                for img_rect in img_rects:
                    images_info.append({
                        'index': img_index,
                        'xref': xref,
                        'rect': img_rect,
                        'width': img[2],
                        'height': img[3]
                    })
            except:
                pass
        
        return images_info

    def edit_text(self, page_num: int, rect: fitz.Rect, new_text: str, 
                  font_name: str = None, font_size: float = None,
                  color: Tuple[float, float, float] = None) -> bool:
        """
        Edita texto en un área específica, manteniendo el formato original.
        """
        page = self.get_page(page_num)
        if not page:
            return False
        
        try:
            # Guardar snapshot antes de modificar
            self._save_snapshot()
            
            # Obtener información del texto original
            blocks = self.find_text_in_rect(page_num, rect)
            if not blocks:
                return False
            
            # Usar el formato del primer bloque si no se especifica
            original_block = blocks[0]
            font_name = font_name or original_block.font_name
            font_size = font_size or original_block.font_size
            color = color or original_block.color
            
            original_data = [(b.text, b.rect, b.font_name, b.font_size, b.color) for b in blocks]
            
            # Eliminar texto original usando redacción
            redact_annot = page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions()
            
            # Insertar nuevo texto con el mismo formato
            # Mapear fuente a una fuente estándar si no está disponible
            font_mapping = {
                'Helvetica': 'helv',
                'Times': 'tiro',
                'Times-Roman': 'tiro',
                'Courier': 'cour',
                'Symbol': 'symb',
                'ZapfDingbats': 'zadb'
            }
            
            # Intentar obtener una fuente compatible
            base_font = 'helv'  # Por defecto Helvetica
            for key in font_mapping:
                if key.lower() in font_name.lower():
                    base_font = font_mapping[key]
                    break
            
            # Insertar texto
            text_writer = fitz.TextWriter(page.rect)
            font = fitz.Font(base_font)
            
            # Calcular posición
            text_point = fitz.Point(rect.x0, rect.y1 - (rect.height * 0.2))
            
            text_writer.append(text_point, new_text, font=font, fontsize=font_size)
            text_writer.write_text(page, color=color)
            
            # Ya se guardó el snapshot antes con _save_snapshot en erase_area
            self.modified = True
            return True
        except Exception as e:
            print(f"Error al editar texto: {e}")
            return False
    
    def undo(self) -> bool:
        """Deshace la última operación restaurando el estado anterior."""
        if not self._undo_snapshots:
            return False
        
        try:
            # Guardar estado actual para rehacer (PDF + overlays)
            current_bytes = self.doc.tobytes(garbage=0)
            current_overlay = None
            if self._get_overlay_state_callback:
                current_overlay = self._get_overlay_state_callback()
            self._redo_snapshots.append((current_bytes, current_overlay))
            
            # Obtener estado anterior (tupla o bytes legacy)
            previous_state = self._undo_snapshots.pop()
            if isinstance(previous_state, tuple):
                previous_bytes, previous_overlay = previous_state
            else:
                # Compatibilidad con snapshots antiguos (solo bytes)
                previous_bytes = previous_state
                previous_overlay = None
            
            # Cerrar documento actual
            if self.doc:
                self.doc.close()
            
            # Restaurar estado anterior del PDF
            self.doc = fitz.open(stream=previous_bytes, filetype="pdf")
            
            # Restaurar estado de overlays (si hay callback y datos)
            if self._restore_overlay_state_callback and previous_overlay is not None:
                self._restore_overlay_state_callback(previous_overlay)
            
            self.modified = len(self._undo_snapshots) > 0
            return True
        except Exception as e:
            print(f"Error al deshacer: {e}")
            return False
    
    def redo(self) -> bool:
        """Rehace la última operación deshecha."""
        if not self._redo_snapshots:
            return False
        
        try:
            # Guardar estado actual para deshacer (PDF + overlays)
            current_bytes = self.doc.tobytes(garbage=0)
            current_overlay = None
            if self._get_overlay_state_callback:
                current_overlay = self._get_overlay_state_callback()
            self._undo_snapshots.append((current_bytes, current_overlay))
            
            # Obtener estado siguiente (tupla o bytes legacy)
            next_state = self._redo_snapshots.pop()
            if isinstance(next_state, tuple):
                next_bytes, next_overlay = next_state
            else:
                # Compatibilidad con snapshots antiguos (solo bytes)
                next_bytes = next_state
                next_overlay = None
            
            # Cerrar documento actual
            if self.doc:
                self.doc.close()
            
            # Restaurar estado siguiente del PDF
            self.doc = fitz.open(stream=next_bytes, filetype="pdf")
            
            # Restaurar estado de overlays (si hay callback y datos)
            if self._restore_overlay_state_callback and next_overlay is not None:
                self._restore_overlay_state_callback(next_overlay)
            
            self.modified = True
            return True
        except Exception as e:
            print(f"Error al rehacer: {e}")
            return False
    
    def set_overlay_callbacks(self, get_callback, restore_callback):
        """Configura callbacks para manejar el estado de overlays del viewer."""
        self._get_overlay_state_callback = get_callback
        self._restore_overlay_state_callback = restore_callback
    
    def _save_snapshot(self):
        """Guarda un snapshot del estado actual antes de una modificación."""
        if not self.doc:
            return
        
        try:
            # Guardar estado del PDF
            current_bytes = self.doc.tobytes(garbage=0)
            
            # Guardar estado de overlays (si hay callback)
            overlay_state = None
            if self._get_overlay_state_callback:
                overlay_state = self._get_overlay_state_callback()
            
            # Guardar tupla (pdf_bytes, overlay_state)
            self._undo_snapshots.append((current_bytes, overlay_state))
            
            # Limitar el número de niveles de deshacer
            while len(self._undo_snapshots) > self._max_undo_levels:
                self._undo_snapshots.pop(0)
            
            # Limpiar la pila de rehacer cuando se hace una nueva modificación
            self._redo_snapshots.clear()
        except Exception as e:
            print(f"Error guardando snapshot: {e}")
    
    def _apply_operation(self, operation: EditOperation):
        """Aplica una operación de edición."""
        try:
            if operation.operation_type == 'highlight':
                page = self.get_page(operation.page_num)
                if page:
                    highlight = page.add_highlight_annot(operation.rect)
                    highlight.update()
            elif operation.operation_type == 'delete':
                page = self.get_page(operation.page_num)
                if page:
                    redact = page.add_redact_annot(operation.rect, fill=(1, 1, 1))
                    page.apply_redactions()
            elif operation.operation_type == 'erase_area':
                page = self.get_page(operation.page_num)
                if page:
                    color = operation.new_data if operation.new_data else (1, 1, 1)
                    shape = page.new_shape()
                    shape.draw_rect(operation.rect)
                    shape.finish(color=color, fill=color)
                    shape.commit()
            elif operation.operation_type == 'edit':
                new_text, rect, font_name, font_size, color = operation.new_data
                self.edit_text(operation.page_num, rect, new_text, font_name, font_size, color)
            elif operation.operation_type == 'add_text':
                # Para añadir texto en PDFs de imagen
                text, rect, font_size, color = operation.new_data
                self.add_text_to_page(operation.page_num, rect, text, font_size, color)
        except Exception as e:
            print(f"Error aplicando operación {operation.operation_type}: {e}")
    
    def can_undo(self) -> bool:
        """Verifica si se puede deshacer."""
        return len(self._undo_snapshots) > 0
    
    def can_redo(self) -> bool:
        """Verifica si se puede rehacer."""
        return len(self._redo_snapshots) > 0
    
    def save(self, file_path: Optional[str] = None) -> bool:
        """
        Guarda el documento preservando formularios y estructura.
        """
        if not self.doc:
            return False
        
        save_path = file_path or self.file_path
        if not save_path:
            return False
        
        try:
            # Obtener bytes del documento actual
            pdf_bytes = self.doc.tobytes(garbage=0, deflate=True, clean=False)
            
            if save_path == self.file_path:
                # Cerrar el documento primero para liberar el archivo
                self.doc.close()
                self.doc = None
                
                # Escribir el archivo
                with open(save_path, 'wb') as f:
                    f.write(pdf_bytes)
                
                # Reabrir el documento
                self.doc = fitz.open(save_path)
            else:
                # Guardar como nuevo archivo
                with open(save_path, 'wb') as f:
                    f.write(pdf_bytes)
            
            self.file_path = save_path
            self.modified = False
            # Actualizar bytes originales para deshacer
            self._original_doc_bytes = self.doc.tobytes()
            return True
        except Exception as e:
            print(f"Error al guardar: {e}")
            # Intentar reabrir el documento si se cerró
            if self.doc is None and self.file_path:
                try:
                    self.doc = fitz.open(self.file_path)
                except:
                    pass
            return False
    
    def save_as(self, file_path: str) -> bool:
        """Guarda el documento con un nuevo nombre."""
        return self.save(file_path)
    
    def get_document_info(self) -> Dict[str, Any]:
        """Obtiene información del documento."""
        if not self.doc:
            return {}
        
        return {
            'title': self.doc.metadata.get('title', ''),
            'author': self.doc.metadata.get('author', ''),
            'subject': self.doc.metadata.get('subject', ''),
            'keywords': self.doc.metadata.get('keywords', ''),
            'creator': self.doc.metadata.get('creator', ''),
            'producer': self.doc.metadata.get('producer', ''),
            'page_count': self.doc.page_count,
            'is_encrypted': self.doc.is_encrypted,
            'is_pdf': self.doc.is_pdf,
            'has_forms': len(self.doc.get_page_fonts(0)) > 0 if self.doc.page_count > 0 else False
        }
    
    def is_text_selectable(self) -> bool:
        """Verifica si el documento permite selección de texto."""
        # Siempre retornar True para permitir intentar seleccionar
        return True
    
    def get_all_text_rects(self, page_num: int) -> list:
        """Obtiene todos los rectángulos de texto de una página para selección visual."""
        page = self.get_page(page_num)
        if not page:
            return []
        
        rects = []
        # Obtener bloques de texto con sus posiciones
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        
        for block in blocks.get("blocks", []):
            if block.get("type") != 0:  # Solo bloques de texto
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if span.get("text", "").strip():
                        rects.append(fitz.Rect(span["bbox"]))
        
        return rects
    
    def get_page_size(self, page_num: int) -> Optional[Tuple[float, float]]:
        """Obtiene el tamaño de una página."""
        page = self.get_page(page_num)
        if page:
            return (page.rect.width, page.rect.height)
        return None
    
    def get_page_info(self, page_num: int) -> Optional[dict]:
        """
        Obtiene información completa de la página incluyendo rotación y matrices.
        Esto es crucial para la conversión correcta de coordenadas.
        """
        page = self.get_page(page_num)
        if not page:
            return None
        
        return {
            'rect': page.rect,  # Rectángulo de la página (visual, post-rotación)
            'mediabox': page.mediabox,  # MediaBox original (sin rotación)
            'cropbox': page.cropbox,  # CropBox (área visible)
            'rotation': page.rotation,  # Rotación en grados (0, 90, 180, 270)
            'transformation_matrix': page.transformation_matrix,  # Matriz de transformación
            'derotation_matrix': page.derotation_matrix,  # Matriz para deshacer rotación
        }
    
    def transform_rect_for_page(self, page_num: int, rect: fitz.Rect, from_visual: bool = True) -> fitz.Rect:
        """
        Transforma un rectángulo entre coordenadas visuales y coordenadas internas de página.
        
        IMPORTANTE: 
        - Las coordenadas visuales son las del pixmap/page.rect (post-rotación)
        - Las coordenadas internas son las del mediabox (pre-rotación, originales del PDF)
        
        Args:
            page_num: Número de página
            rect: Rectángulo a transformar
            from_visual: Si True, transforma de coordenadas visuales a internas (mediabox)
        
        Returns:
            Rectángulo transformado
        """
        page = self.get_page(page_num)
        if not page:
            return rect
        
        rotation = page.rotation
        
        # Si no hay rotación, las coordenadas son las mismas
        if rotation == 0:
            return rect
        
        # Dimensiones del mediabox (coordenadas originales del PDF)
        mediabox = page.mediabox
        mb_width = mediabox.width   # Ancho original
        mb_height = mediabox.height  # Alto original
        
        # Dimensiones visuales (page.rect, post-rotación)
        visual_width = page.rect.width
        visual_height = page.rect.height
        
        print(f"Transformando rect: {rect}")
        print(f"Rotación de página: {rotation}°")
        print(f"MediaBox (original): {mb_width:.1f} x {mb_height:.1f}")
        print(f"Visual (rotado): {visual_width:.1f} x {visual_height:.1f}")
        
        x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
        
        if from_visual:
            # De coordenadas visuales (pixmap) a coordenadas de mediabox (PDF interno)
            if rotation == 90:
                # Rotado 90° horario: visual es portrait de un landscape original
                # x_mediabox = y_visual
                # y_mediabox = visual_width - x_visual
                new_x0 = y0
                new_y0 = visual_width - x1
                new_x1 = y1
                new_y1 = visual_width - x0
            elif rotation == 180:
                # Rotado 180°: mismo aspect ratio pero invertido
                new_x0 = visual_width - x1
                new_y0 = visual_height - y1
                new_x1 = visual_width - x0
                new_y1 = visual_height - y0
            elif rotation == 270:
                # Rotado 270° horario (= 90° antihorario): 
                # El PDF original es landscape (842 x 595), se muestra como portrait (595 x 842)
                # x_mediabox = visual_height - y_visual
                # y_mediabox = x_visual
                new_x0 = visual_height - y1
                new_y0 = x0
                new_x1 = visual_height - y0
                new_y1 = x1
            else:
                return rect
        else:
            # De coordenadas de mediabox a visuales (inverso)
            if rotation == 90:
                new_x0 = mb_height - y1
                new_y0 = x0
                new_x1 = mb_height - y0
                new_y1 = x1
            elif rotation == 180:
                new_x0 = mb_width - x1
                new_y0 = mb_height - y1
                new_x1 = mb_width - x0
                new_y1 = mb_height - y0
            elif rotation == 270:
                new_x0 = y0
                new_y0 = mb_width - x1
                new_x1 = y1
                new_y1 = mb_width - x0
            else:
                return rect
        
        # Normalizar (asegurar x0 < x1, y0 < y1)
        result = fitz.Rect(
            min(new_x0, new_x1),
            min(new_y0, new_y1),
            max(new_x0, new_x1),
            max(new_y0, new_y1)
        )
        
        print(f"Rect transformado: {result}")
        return result
    
    def add_text_to_page(self, page_num: int, rect: fitz.Rect, text: str, 
                         font_size: float = 12, color: Tuple[float, float, float] = (0, 0, 0),
                         save_snapshot: bool = True, is_bold: bool = False) -> bool:
        """
        Añade texto a una página usando insert_text (más confiable que insert_textbox).
        
        Args:
            page_num: Número de página
            rect: Área donde colocar el texto (en coordenadas visuales)
            text: Texto a añadir
            font_size: Tamaño de fuente
            color: Color del texto (RGB 0-1)
            save_snapshot: Si True, guarda snapshot para undo
            is_bold: Si True, usa fuente negrita
        
        Returns:
            True si se añadió correctamente
        """
        print(f"\n=== ADD_TEXT_TO_PAGE LLAMADO ===")
        print(f"Texto: '{text}', Rect visual: {rect}, Bold: {is_bold}")
        
        page = self.get_page(page_num)
        if not page:
            print("add_text_to_page - ERROR: No se pudo obtener la página")
            return False
        
        try:
            if save_snapshot:
                self._save_snapshot()
            
            rotation = page.rotation
            print(f"add_text_to_page - Rotación: {rotation}°")
            
            # Seleccionar fuente según negrita
            # helv = Helvetica (normal), hebo = Helvetica-Bold (negrita)
            font_name = "hebo" if is_bold else "helv"
            
            # Ajustar tamaño de fuente si el rectángulo es muy pequeño
            rect_height = rect.height
            if rect_height < font_size + 2:
                font_size = max(8, rect_height - 2)
            
            # Calcular el punto de inserción basado en el rectángulo
            # El texto se inserta desde la línea base (baseline)
            # Para que aparezca dentro del rect, el punto Y debe ser rect.y0 + font_size
            
            if rotation == 0:
                # Sin rotación - insertar directamente
                # Punto: esquina superior izquierda + offset para baseline
                insert_point = fitz.Point(rect.x0 + 2, rect.y0 + font_size)
                
                rc = page.insert_text(
                    insert_point,
                    text,
                    fontsize=font_size,
                    fontname=font_name,
                    color=color
                )
                print(f"insert_text (sin rotación) punto={insert_point}, font={font_name}, rc={rc}")
                
            elif rotation == 270:
                # Rotación 270°: transformar coordenadas visuales a mediabox
                visual_height = page.rect.height
                
                # Punto visual donde queremos el texto
                visual_x = rect.x0 + 2
                visual_y = rect.y0 + font_size
                
                # Transformar a coordenadas de mediabox para rotación 270°
                # mediabox_x = visual_height - visual_y
                # mediabox_y = visual_x
                mediabox_x = visual_height - visual_y
                mediabox_y = visual_x
                
                insert_point = fitz.Point(mediabox_x, mediabox_y)
                
                rc = page.insert_text(
                    insert_point,
                    text,
                    fontsize=font_size,
                    fontname=font_name,
                    color=color,
                    rotate=270  # Texto horizontal en vista rotada 270°
                )
                print(f"insert_text (rot 270) visual=({visual_x}, {visual_y}) -> mediabox={insert_point}, font={font_name}, rc={rc}")
                
            elif rotation == 90:
                # Rotación 90°
                visual_width = page.rect.width
                
                visual_x = rect.x0 + 2
                visual_y = rect.y0 + font_size
                
                # Transformar para rotación 90°
                mediabox_x = visual_y
                mediabox_y = visual_width - visual_x
                
                insert_point = fitz.Point(mediabox_x, mediabox_y)
                
                rc = page.insert_text(
                    insert_point,
                    text,
                    fontsize=font_size,
                    fontname=font_name,
                    color=color,
                    rotate=90
                )
                print(f"insert_text (rot 90) font={font_name}, rc={rc}")
                
            elif rotation == 180:
                # Rotación 180°
                visual_width = page.rect.width
                visual_height = page.rect.height
                
                visual_x = rect.x0 + 2
                visual_y = rect.y0 + font_size
                
                # Transformar para rotación 180°
                mediabox_x = visual_width - visual_x
                mediabox_y = visual_height - visual_y
                
                insert_point = fitz.Point(mediabox_x, mediabox_y)
                
                rc = page.insert_text(
                    insert_point,
                    text,
                    fontsize=font_size,
                    fontname=font_name,
                    color=color,
                    rotate=180
                )
                print(f"insert_text (rot 180) font={font_name}, rc={rc}")
                
            else:
                # Rotación no estándar - usar método simple
                insert_point = fitz.Point(rect.x0 + 2, rect.y0 + font_size)
                rc = page.insert_text(
                    insert_point,
                    text,
                    fontsize=font_size,
                    fontname=font_name,
                    color=color
                )
                print(f"insert_text (otra rotación) font={font_name}, rc={rc}")
            
            if rc > 0:
                print(f"=== TEXTO INSERTADO CORRECTAMENTE (rc={rc}) ===\n")
                self.modified = True
                return True
            else:
                print(f"=== ERROR: insert_text falló con rc={rc} ===\n")
                return False
            
        except Exception as e:
            print(f"add_text_to_page - ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def edit_or_add_text(self, page_num: int, rect: fitz.Rect, new_text: str,
                         font_size: float = 12, color: Tuple[float, float, float] = (0, 0, 0)) -> bool:
        """
        Edita texto existente o añade nuevo texto si no hay texto seleccionable.
        Funciona tanto para PDFs con texto como para PDFs de imagen.
        
        Args:
            page_num: Número de página
            rect: Área de edición
            new_text: Nuevo texto
            font_size: Tamaño de fuente
            color: Color del texto
        
        Returns:
            True si la operación fue exitosa
        """
        if not self.doc:
            return False
        
        # Verificar si hay texto existente en el área
        blocks = self.find_text_in_rect(page_num, rect)
        
        if blocks and blocks[0].text.strip():
            # Hay texto existente - editar
            block = blocks[0]
            return self.edit_text(
                page_num, rect, new_text,
                block.font_name, block.font_size or font_size, block.color or color
            )
        else:
            # No hay texto - primero borrar el área y luego añadir texto
            # Guardar snapshot UNA SOLA VEZ antes de ambas operaciones
            self._save_snapshot()
            # Borrar área SIN guardar snapshot adicional
            self.erase_area(page_num, rect, color=(1, 1, 1), save_snapshot=False)
            # Añadir texto SIN guardar snapshot adicional
            return self.add_text_to_page(page_num, rect, new_text, font_size, color, save_snapshot=False)
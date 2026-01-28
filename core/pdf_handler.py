"""
Módulo de manipulación de PDF usando PyMuPDF (fitz)
Maneja la lectura, edición y guardado de documentos PDF preservando estructura y formularios.
"""

import fitz  # PyMuPDF
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
import copy
import tempfile
import os

# Intentar importar pikepdf para reparación de PDFs
try:
    import pikepdf  # type: ignore[import-unresolved]
    PIKEPDF_AVAILABLE = True
except ImportError:
    PIKEPDF_AVAILABLE = False


@dataclass
class TextBlock:
    """Representa un bloque de texto en el PDF."""
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
        return bool(self.flags & 2 ** 4)
    
    @property
    def is_italic(self) -> bool:
        return bool(self.flags & 2 ** 1)


@dataclass
class EditOperation:
    """Representa una operación de edición para deshacer/rehacer."""
    operation_type: str  # 'highlight', 'delete', 'edit'
    page_num: int
    original_data: Any
    new_data: Any
    rect: fitz.Rect


class PDFDocument:
    """Clase principal para manejar documentos PDF."""
    
    def __init__(self):
        self.doc: Optional[fitz.Document] = None
        self.file_path: Optional[str] = None
        self.modified: bool = False
        # Sistema de deshacer/rehacer basado en snapshots
        self._undo_snapshots: List[bytes] = []  # Lista de estados anteriores
        self._redo_snapshots: List[bytes] = []  # Lista de estados para rehacer
        self._original_doc_bytes: Optional[bytes] = None
        self._last_error: str = ""
        self._max_undo_levels = 20  # Máximo de niveles de deshacer
        
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
    
    def get_text_blocks(self, page_num: int) -> List[TextBlock]:
        """Obtiene todos los bloques de texto de una página con su información de formato."""
        page = self.get_page(page_num)
        if not page:
            return []
        
        blocks = []
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
    
    def find_text_at_point(self, page_num: int, point: Tuple[float, float]) -> Optional[TextBlock]:
        """Encuentra el texto en un punto específico."""
        blocks = self.get_text_blocks(page_num)
        pt = fitz.Point(point)
        
        for block in blocks:
            if block.rect.contains(pt):
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
        """Resalta texto en un área específica."""
        page = self.get_page(page_num)
        if not page:
            return False
        
        try:
            # Guardar snapshot antes de modificar
            self._save_snapshot()
            
            # Crear anotación de resaltado
            highlight = page.add_highlight_annot(rect)
            highlight.set_colors(stroke=color)
            highlight.update()
            
            self.modified = True
            return True
        except Exception as e:
            print(f"Error al resaltar: {e}")
            return False
    
    def get_highlight_annotations(self, page_num: int) -> List[dict]:
        """
        Obtiene todas las anotaciones de resaltado de una página.
        
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
                    if annot.type[0] == 8:  # 8 = Highlight annotation
                        highlights.append({
                            'rect': annot.rect,
                            'color': annot.colors.get('stroke', (1, 1, 0)),
                            'xref': annot.xref,  # Referencia única para eliminar
                            'content': annot.info.get('content', '')
                        })
        except Exception as e:
            print(f"Error obteniendo resaltados: {e}")
        
        return highlights
    
    def remove_highlight_at_point(self, page_num: int, point: Tuple[float, float]) -> bool:
        """
        Elimina una anotación de resaltado en un punto específico.
        
        Args:
            page_num: Número de página
            point: Coordenadas (x, y) del punto
            
        Returns:
            True si se eliminó algún resaltado
        """
        page = self.get_page(page_num)
        if not page:
            return False
        
        try:
            pt = fitz.Point(point)
            annots = page.annots()
            if annots:  # Verificar que no sea None
                for annot in annots:
                    if annot.type[0] == 8:  # Highlight annotation
                        if annot.rect.contains(pt):
                            # Guardar snapshot antes de modificar
                            self._save_snapshot()
                            # Eliminar la anotación
                            page.delete_annot(annot)
                            self.modified = True
                            return True
        except Exception as e:
            print(f"Error eliminando resaltado: {e}")
        
        return False
    
    def remove_highlight_in_rect(self, page_num: int, rect: fitz.Rect) -> bool:
        """
        Elimina todas las anotaciones de resaltado que intersectan con un rectángulo.
        
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
                    if annot.type[0] == 8:  # Highlight annotation
                        if rect.intersects(annot.rect):
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
    
    def erase_area(self, page_num: int, rect: fitz.Rect, color: Tuple[float, float, float] = (1, 1, 1), save_snapshot: bool = True) -> bool:
        """
        Borra un área del PDF dibujando un rectángulo sobre ella.
        Funciona tanto para texto como para imágenes.
        
        Args:
            page_num: Número de página
            rect: Área a borrar
            color: Color de relleno (por defecto blanco)
            save_snapshot: Si True, guarda snapshot para undo (por defecto True)
        
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
            
            # Dibujar un rectángulo sólido sobre el área
            shape = page.new_shape()
            shape.draw_rect(rect)
            shape.finish(color=color, fill=color)
            shape.commit()
            
            self.modified = True
            return True
        except Exception as e:
            print(f"Error al borrar área: {e}")
            return False
    
    def is_image_based_pdf(self) -> bool:
        """
        Detecta si el PDF es principalmente basado en imágenes (escaneado).
        
        Returns:
            True si el PDF parece ser escaneado/basado en imágenes
        """
        if not self.doc:
            return False
        
        total_text_length = 0
        total_images = 0
        
        for page_num in range(min(3, self.doc.page_count)):
            page = self.doc[page_num]
            
            # Contar texto
            text = page.get_text("text")
            total_text_length += len(text.strip())
            
            # Contar imágenes
            images = page.get_images()
            total_images += len(images)
        
        # Si hay imágenes pero poco texto, probablemente es escaneado
        if total_images > 0 and total_text_length < 50:
            return True
        
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
            print("No hay nada que deshacer")
            return False
        
        try:
            # Guardar estado actual para rehacer
            current_bytes = self.doc.tobytes(garbage=0)
            self._redo_snapshots.append(current_bytes)
            
            # Obtener estado anterior
            previous_bytes = self._undo_snapshots.pop()
            
            # Cerrar documento actual
            if self.doc:
                self.doc.close()
            
            # Restaurar estado anterior
            self.doc = fitz.open(stream=previous_bytes, filetype="pdf")
            
            self.modified = len(self._undo_snapshots) > 0
            print(f"Deshacer exitoso. Niveles restantes: {len(self._undo_snapshots)}")
            return True
        except Exception as e:
            print(f"Error al deshacer: {e}")
            return False
    
    def redo(self) -> bool:
        """Rehace la última operación deshecha."""
        if not self._redo_snapshots:
            print("No hay nada que rehacer")
            return False
        
        try:
            # Guardar estado actual para deshacer
            current_bytes = self.doc.tobytes(garbage=0)
            self._undo_snapshots.append(current_bytes)
            
            # Obtener estado siguiente
            next_bytes = self._redo_snapshots.pop()
            
            # Cerrar documento actual
            if self.doc:
                self.doc.close()
            
            # Restaurar estado siguiente
            self.doc = fitz.open(stream=next_bytes, filetype="pdf")
            
            self.modified = True
            print(f"Rehacer exitoso. Niveles de rehacer restantes: {len(self._redo_snapshots)}")
            return True
        except Exception as e:
            print(f"Error al rehacer: {e}")
            return False
    
    def _save_snapshot(self):
        """Guarda un snapshot del estado actual antes de una modificación."""
        if not self.doc:
            return
        
        try:
            # Guardar estado actual
            current_bytes = self.doc.tobytes(garbage=0)
            self._undo_snapshots.append(current_bytes)
            
            # Limitar el número de niveles de deshacer
            while len(self._undo_snapshots) > self._max_undo_levels:
                self._undo_snapshots.pop(0)
            
            # Limpiar la pila de rehacer cuando se hace una nueva modificación
            self._redo_snapshots.clear()
            
            print(f"Snapshot guardado. Niveles de deshacer: {len(self._undo_snapshots)}")
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
    def add_text_to_page(self, page_num: int, rect: fitz.Rect, text: str, 
                         font_size: float = 12, color: Tuple[float, float, float] = (0, 0, 0),
                         save_snapshot: bool = True) -> bool:
        """
        Añade texto a una página (útil para PDFs de imagen).
        
        Args:
            page_num: Número de página
            rect: Área donde colocar el texto
            text: Texto a añadir
            font_size: Tamaño de fuente
            color: Color del texto (RGB 0-1)
            save_snapshot: Si True, guarda snapshot para undo (por defecto True)
        
        Returns:
            True si se añadió correctamente
        """
        page = self.get_page(page_num)
        if not page:
            return False
        
        try:
            # Guardar snapshot antes de modificar (si se requiere)
            if save_snapshot:
                self._save_snapshot()
            
            # Ajustar tamaño de fuente si el rectángulo es muy pequeño
            rect_height = rect.height
            if rect_height < font_size + 4:
                font_size = max(8, rect_height - 4)
            
            # Calcular posición Y: centrar verticalmente en el rectángulo si es pequeño
            if rect_height < font_size * 2:
                y_pos = rect.y0 + (rect_height / 2) + (font_size / 3)
            else:
                y_pos = rect.y0 + font_size + 2
            
            # Usar insert_text que es más directo y confiable
            point = fitz.Point(rect.x0 + 2, y_pos)
            
            # Insertar texto directamente en la página
            rc = page.insert_text(
                point,
                text,
                fontsize=font_size,
                fontname="helv",
                color=color,
                render_mode=0  # 0 = fill text
            )
            
            if rc >= 0:
                self.modified = True
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Error al añadir texto: {e}")
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
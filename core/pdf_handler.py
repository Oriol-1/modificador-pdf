"""
Módulo de manipulación de PDF usando PyMuPDF (fitz)
Maneja la lectura, edición y guardado de documentos PDF preservando estructura y formularios.
"""

import fitz  # PyMuPDF
from typing import List, Tuple, Optional, Dict, Any
import copy
import tempfile
import os
import threading

# Importar modelos de datos
from .models import TextBlock, EditOperation
from .font_manager import FontManager, FontDescriptor, get_font_manager
from .page_identity import PageIdentityMap

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
        # Cada snapshot es una tupla: (pdf_bytes, overlay_data, page_map_state)
        self._undo_snapshots: List[tuple] = []  # Lista de estados anteriores
        self._redo_snapshots: List[tuple] = []  # Lista de estados para rehacer
        self._original_doc_bytes: Optional[bytes] = None
        # Snapshot perezoso del PDF para MOVE puro: capturado antes del primer
        # borrado de un span nativo movido, sirve como fuente intacta para
        # show_pdf_page al hacer commit. Preserva glifos, fuentes y kerning
        # exactamente. Se limpia tras cada commit y al abrir/guardar.
        self._move_source_bytes: Optional[bytes] = None
        # Captura asíncrona del snapshot pristine para MOVE puro: se lanza
        # en un hilo en mousePress (cuando hay candidato a drag nativo) y se
        # espera en mouseRelease antes de modificar el doc. Evita el freeze
        # de doc.tobytes() en el primer movimiento.
        self._move_snapshot_lock = threading.Lock()
        self._move_snapshot_thread: Optional[threading.Thread] = None
        # Cache del resultado de is_image_based_pdf(). El analisis de imagenes
        # es caro (recorre 3 paginas, mira anchos/altos) y se llama desde
        # muchos hot paths (cada edicion, hover, render). El "image-based"
        # de un PDF es una propiedad estable durante la sesion -> cacheable.
        # Se invalida al abrir/cerrar/recargar doc.
        self._is_image_based_cache: Optional[bool] = None
        self._last_error: str = ""
        self._max_undo_levels = 20  # Máximo de niveles de deshacer
        # Callback para obtener/restaurar estado de overlays del viewer
        self._get_overlay_state_callback = None
        self._restore_overlay_state_callback = None
        # Mapa de identidad de páginas (UUID ↔ índice)
        self.page_map = PageIdentityMap()
        
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
            self._move_source_bytes = None
            self._is_image_based_cache = None
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
            # Inicializar mapa de identidad de páginas
            self.page_map.initialize(self.doc.page_count)
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
        self._move_source_bytes = None
        self._is_image_based_cache = None
        self.page_map = PageIdentityMap()
    
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
        
        # MOVE seguro: cuando el punto cae dentro de varios spans solapados
        # (kerning, justificado, líneas pegadas), elegir el span MÁS PEQUEÑO,
        # que es siempre el más específico y nunca un agregado vecino.
        contained = []
        for i, block in enumerate(visual_blocks):
            if block.rect.contains(pt):
                area = max(0.0, block.rect.width) * max(0.0, block.rect.height)
                contained.append((area, i, block))
        if contained:
            contained.sort(key=lambda t: t[0])
            _, i, block = contained[0]
            if i < len(internal_blocks):
                block.internal_rect = internal_blocks[i].rect
            else:
                block.internal_rect = block.rect
            return block

        # Fallback: span más cercano por distancia euclídea al centro,
        # acotado a una distancia razonable (1pt) para no capturar
        # nunca un span vecino. Sustituye al antiguo expand-by-2pt que
        # podía agarrar el texto adyacente cuando dos líneas estaban pegadas.
        best = None
        best_dist = 1.0  # umbral máximo
        for i, block in enumerate(visual_blocks):
            r = block.rect
            dx = max(r.x0 - pt.x, 0.0, pt.x - r.x1)
            dy = max(r.y0 - pt.y, 0.0, pt.y - r.y1)
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best = (i, block)
        if best is not None:
            i, block = best
            if i < len(internal_blocks):
                block.internal_rect = internal_blocks[i].rect
            else:
                block.internal_rect = block.rect
            return block

        return None
    
    def find_text_cluster_at_point(
        self,
        page_num: int,
        point: Tuple[float, float],
        gap_factor: float = 0.6,
    ) -> Optional[Tuple[fitz.Rect, str]]:
        """Devuelve el rect interno y el texto del CLÚSTER contiguo de palabras
        alrededor del punto clicado.

        Un clúster es una secuencia de palabras de la misma línea cuyos huecos
        horizontales son menores a ``gap_factor * font_size``. Esto evita que
        el MOVE arrastre textos visualmente separados que comparten span en
        PyMuPDF (espacios anchos internos) o cuyos bboxes se solapan.

        Args:
            page_num: Página.
            point: Punto en coordenadas internas (mediabox) del PDF.
            gap_factor: Hueco máximo permitido para considerar dos palabras
                contiguas, expresado como fracción del alto de palabra.

        Returns:
            (rect_interno, texto_clúster) o None si el punto no cae en una
            palabra detectable.
        """
        page = self.get_page(page_num)
        if page is None:
            return None
        pt = fitz.Point(point)

        try:
            # PyMuPDF: cada tupla es (x0, y0, x1, y1, "word", block_no, line_no, word_no)
            words = page.get_text("words")
        except Exception:
            return None
        if not words:
            return None

        # Buscar la palabra que contiene el punto
        target = None
        for w in words:
            wr = fitz.Rect(w[0], w[1], w[2], w[3])
            if wr.contains(pt):
                target = w
                break
        if target is None:
            return None

        bn, ln = target[5], target[6]
        line_words = sorted(
            [w for w in words if w[5] == bn and w[6] == ln],
            key=lambda w: w[0],
        )
        if not line_words:
            return None

        # Localizar índice del target en la línea
        idx = -1
        for i, w in enumerate(line_words):
            if w is target or (w[7] == target[7] and w[0] == target[0]):
                idx = i
                break
        if idx < 0:
            return None

        # Umbral basado en alto de palabra (proxy del tamaño de fuente)
        height = max(1.0, target[3] - target[1])
        gap_threshold = gap_factor * height

        # Expandir hacia la izquierda mientras los huecos sean estrechos
        start = idx
        while start > 0:
            gap = line_words[start][0] - line_words[start - 1][2]
            if gap > gap_threshold:
                break
            start -= 1

        # Expandir hacia la derecha
        end = idx
        while end < len(line_words) - 1:
            gap = line_words[end + 1][0] - line_words[end][2]
            if gap > gap_threshold:
                break
            end += 1

        cluster = line_words[start:end + 1]
        x0 = min(w[0] for w in cluster)
        y0 = min(w[1] for w in cluster)
        x1 = max(w[2] for w in cluster)
        y1 = max(w[3] for w in cluster)
        text = " ".join(w[4] for w in cluster)
        return fitz.Rect(x0, y0, x1, y1), text

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

    def add_underline_annot(self, page_num: int, rect: fitz.Rect,
                             color: Tuple[float, float, float] = (0, 0, 1)) -> bool:
        """Añade anotación de subrayado en un área.
        
        Args:
            page_num: Número de página (0-based).
            rect: Rectángulo del texto a subrayar (coordenadas PDF).
            color: Color RGB (0-1) del subrayado.
            
        Returns:
            True si se creó correctamente.
        """
        page = self.get_page(page_num)
        if not page:
            return False
        try:
            self._save_snapshot()
            annot = page.add_underline_annot(rect)
            annot.set_colors(stroke=color)
            annot.update()
            self.modified = True
            return True
        except Exception as e:
            print(f"Error añadiendo subrayado: {e}")
            return False

    def add_strikeout_annot(self, page_num: int, rect: fitz.Rect,
                             color: Tuple[float, float, float] = (1, 0, 0)) -> bool:
        """Añade anotación de tachado en un área.
        
        Args:
            page_num: Número de página (0-based).
            rect: Rectángulo del texto a tachar (coordenadas PDF).
            color: Color RGB (0-1) del tachado.
            
        Returns:
            True si se creó correctamente.
        """
        page = self.get_page(page_num)
        if not page:
            return False
        try:
            self._save_snapshot()
            annot = page.add_strikeout_annot(rect)
            annot.set_colors(stroke=color)
            annot.update()
            self.modified = True
            return True
        except Exception as e:
            print(f"Error añadiendo tachado: {e}")
            return False

    def add_text_annot(self, page_num: int, point: Tuple[float, float],
                       text: str, icon: str = "Note") -> bool:
        """Añade una nota adhesiva (sticky note) en un punto.
        
        Args:
            page_num: Número de página (0-based).
            point: Posición (x, y) en coordenadas PDF.
            text: Contenido de la nota.
            icon: Icono de la nota (Note, Comment, Help, Insert, Key, Paragraph).
            
        Returns:
            True si se creó correctamente.
        """
        page = self.get_page(page_num)
        if not page:
            return False
        if not text:
            return False
        try:
            self._save_snapshot()
            annot = page.add_text_annot(fitz.Point(point[0], point[1]), text, icon=icon)
            annot.update()
            self.modified = True
            return True
        except Exception as e:
            print(f"Error añadiendo nota: {e}")
            return False

    def add_freetext_annot(self, page_num: int, rect: fitz.Rect,
                           text: str, font_size: float = 11,
                           text_color: Tuple[float, float, float] = (0, 0, 0),
                           fill_color: Tuple[float, float, float] = (1, 1, 0.8)) -> bool:
        """Añade una anotación de texto libre en un rectángulo.
        
        Args:
            page_num: Número de página (0-based).
            rect: Rectángulo donde colocar el texto.
            text: Contenido del texto.
            font_size: Tamaño de fuente.
            text_color: Color RGB del texto.
            fill_color: Color RGB del fondo.
            
        Returns:
            True si se creó correctamente.
        """
        page = self.get_page(page_num)
        if not page:
            return False
        if not text:
            return False
        try:
            self._save_snapshot()
            annot = page.add_freetext_annot(
                rect, text,
                fontsize=font_size,
                text_color=text_color,
                fill_color=fill_color,
            )
            annot.update()
            self.modified = True
            return True
        except Exception as e:
            print(f"Error añadiendo texto libre: {e}")
            return False

    def get_annotations(self, page_num: int) -> List[dict]:
        """Obtiene todas las anotaciones de una página.
        
        Args:
            page_num: Número de página (0-based).
            
        Returns:
            Lista de diccionarios con info de cada anotación.
        """
        page = self.get_page(page_num)
        if not page:
            return []
        
        result = []
        annots = page.annots()
        if annots:
            for annot in annots:
                result.append({
                    'type': annot.type[0],
                    'type_name': annot.type[1],
                    'rect': annot.rect,
                    'content': annot.info.get('content', ''),
                    'colors': annot.colors,
                })
        return result

    def delete_annotation_at_point(self, page_num: int,
                                    point: Tuple[float, float],
                                    tolerance: float = 5.0) -> bool:
        """Elimina la anotación más cercana a un punto.
        
        Args:
            page_num: Número de página (0-based).
            point: Coordenadas (x, y) en espacio PDF.
            tolerance: Margen de búsqueda en puntos.
            
        Returns:
            True si se eliminó alguna anotación.
        """
        page = self.get_page(page_num)
        if not page:
            return False
        
        search_rect = fitz.Rect(
            point[0] - tolerance, point[1] - tolerance,
            point[0] + tolerance, point[1] + tolerance
        )
        
        annots = page.annots()
        if not annots:
            return False
        
        for annot in annots:
            if search_rect.intersects(annot.rect):
                self._save_snapshot()
                page.delete_annot(annot)
                self.modified = True
                return True
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
    
    def erase_text_transparent(self, page_num: int, rect: fitz.Rect, save_snapshot: bool = True, already_internal: bool = False, refresh: bool = True) -> bool:
        """
        Elimina ÚNICAMENTE los glifos de texto en un área, sin pintar nada
        encima. Preserva imagen, color, degradado, tabla, marca de agua y
        cualquier gráfico vectorial que estuviera debajo del texto.

        Diseñada para el flujo MOVER: el texto se trata como capa independiente
        sobre el contenido original; al moverlo, el fondo debe quedar intacto.

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

            # Expandir ligeramente para compensar imprecisiones de coordenadas
            # Esto evita que queden restos de texto al borde del rect
            # Expansión ampliada para cubrir imprecisión de coordenadas OCR tras escalado DPI
            expanded_rect = transformed_rect + (-2, -1, 2, 1)
            print(f"erase_text_transparent - Usando rect expandido: {expanded_rect}")

            # Verificar qué texto hay en esa área antes de borrar
            text_in_area = page.get_text("text", clip=expanded_rect)
            print(f"erase_text_transparent - Texto en área ANTES de borrar: '{text_in_area.strip()}'")

            # NO destructivo: fill=False no pinta nada (no hay cuadro blanco).
            # Preservamos imágenes y line-art para que el fondo (foto, color,
            # degradado, tabla, marca de agua, gráficos vectoriales) siga
            # intacto. Solo se eliminan los operadores de texto (glifos).
            page.add_redact_annot(expanded_rect, fill=False)
            self._apply_redactions_preserve_background(page)
            
            # Verificar qué texto hay después de borrar (solo si refresh)
            # Saltarse get_text si no hace falta evita parsing extra del doc.
            if refresh:
                text_after = page.get_text("text", clip=expanded_rect)
                print(f"erase_text_transparent - Texto en área DESPUÉS de borrar: '{text_after.strip()}'")
                # Refrescar el documento para que get_text vea la redacción.
                # Solo necesario si subsecuente código consulta texto. Para
                # el flujo de move (donde solo re-renderizamos pixmap)
                # podemos saltarlo: render_page lee directo del doc
                # modificado y muestra la redacción correctamente.
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

            # Para PDFs de imagen: cubrir visualmente con shape blanco PRIMERO
            # (la imagen subyacente sigue mostrando el texto), y luego redactar
            # la capa de texto OCR para que find_text_at_point no la encuentre.
            # Importante: el shape se dibuja antes que la redacción porque
            # apply_redactions() invalida el objeto page.
            try:
                shape = page.new_shape()
                shape.draw_rect(transformed_rect)
                shape.finish(color=color, fill=color)
                shape.commit()
                self.modified = True
                print(f"Área cubierta con shape: {transformed_rect}")
            except Exception as e:
                print(f"Shape falló: {e}")
                return False

            # En PDFs de imagen, además limpiar la capa OCR subyacente para que
            # find_text_at_point no devuelva el texto "borrado" y no reaparezca
            # al hacer clic. Si falla, el visual ya está cubierto.
            if use_redaction and is_image_pdf:
                try:
                    page.add_redact_annot(transformed_rect, fill=None)
                    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
                    self._refresh_document()
                    print(
                        f"Capa OCR eliminada en PDF de imagen: {transformed_rect}"
                    )
                except Exception as e:
                    print(
                        f"Redacción de capa OCR falló (no crítico): {e}"
                    )

            return True

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

        Un PDF se considera basado en imágenes si tiene imágenes grandes
        (más de 1000x1000 píxeles) en alguna de las primeras 3 páginas.

        OPTIMIZACION: el resultado se cachea por sesión (la naturaleza
        image-based del doc no cambia). Anteriormente se llamaba desde
        muchos hot paths (cada edición, hover, render); cada llamada
        decodificaba los píxeles de las imágenes con extract_image,
        causando hasta 10s de bloqueo en docs con imágenes grandes.

        Ahora:
        - Resultado cacheado en self._is_image_based_cache
        - El cálculo usa img[2]/img[3] (ancho/alto directos del listado
          de imágenes) sin decodificar píxeles via extract_image.

        Returns:
            True si el PDF parece ser escaneado/basado en imágenes
        """
        if self._is_image_based_cache is not None:
            return self._is_image_based_cache

        if not self.doc:
            self._is_image_based_cache = False
            return False

        result = False
        try:
            for page_num in range(min(3, self.doc.page_count)):
                page = self.doc[page_num]
                # get_images(full=True) devuelve listas con:
                # [xref, smask, width, height, bpc, colorspace, ...]
                # img[2] = width, img[3] = height. Sin decodificar pixeles.
                for img in page.get_images(full=True):
                    try:
                        img_w = int(img[2])
                        img_h = int(img[3])
                    except (IndexError, TypeError, ValueError):
                        continue
                    if img_w > 1000 and img_h > 1000:
                        print(f"is_image_based_pdf: Detectada imagen grande {img_w}x{img_h} - ES PDF de imagen")
                        result = True
                        break
                if result:
                    break
            else:
                print(f"is_image_based_pdf: No hay imágenes grandes - NO es PDF de imagen")
        except Exception as e:
            print(f"is_image_based_pdf: error analizando ({e}); asumiendo NO image-based")
            result = False

        self._is_image_based_cache = result
        return result
    
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
            # Guardar estado actual para rehacer (PDF + overlays + page_map)
            current_bytes = self.doc.tobytes(garbage=0)
            current_overlay = None
            if self._get_overlay_state_callback:
                current_overlay = self._get_overlay_state_callback()
            current_page_map = self.page_map.to_list()
            self._redo_snapshots.append((current_bytes, current_overlay, current_page_map))
            
            # Obtener estado anterior (tupla de 3, tupla de 2, o bytes legacy)
            previous_state = self._undo_snapshots.pop()
            if isinstance(previous_state, tuple) and len(previous_state) == 3:
                previous_bytes, previous_overlay, previous_page_map = previous_state
            elif isinstance(previous_state, tuple) and len(previous_state) == 2:
                previous_bytes, previous_overlay = previous_state
                previous_page_map = None
            else:
                # Compatibilidad con snapshots antiguos (solo bytes)
                previous_bytes = previous_state
                previous_overlay = None
                previous_page_map = None
            
            # Cerrar documento actual
            if self.doc:
                self.doc.close()
            
            # Restaurar estado anterior del PDF
            self.doc = fitz.open(stream=previous_bytes, filetype="pdf")
            
            # Restaurar estado de overlays (si hay callback y datos)
            if self._restore_overlay_state_callback and previous_overlay is not None:
                self._restore_overlay_state_callback(previous_overlay)
            
            # Restaurar mapa de páginas
            if previous_page_map is not None:
                self.page_map.from_list(previous_page_map)
            
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
            # Guardar estado actual para deshacer (PDF + overlays + page_map)
            current_bytes = self.doc.tobytes(garbage=0)
            current_overlay = None
            if self._get_overlay_state_callback:
                current_overlay = self._get_overlay_state_callback()
            current_page_map = self.page_map.to_list()
            self._undo_snapshots.append((current_bytes, current_overlay, current_page_map))
            
            # Obtener estado siguiente (tupla de 3, tupla de 2, o bytes legacy)
            next_state = self._redo_snapshots.pop()
            if isinstance(next_state, tuple) and len(next_state) == 3:
                next_bytes, next_overlay, next_page_map = next_state
            elif isinstance(next_state, tuple) and len(next_state) == 2:
                next_bytes, next_overlay = next_state
                next_page_map = None
            else:
                # Compatibilidad con snapshots antiguos (solo bytes)
                next_bytes = next_state
                next_overlay = None
                next_page_map = None
            
            # Cerrar documento actual
            if self.doc:
                self.doc.close()
            
            # Restaurar estado siguiente del PDF
            self.doc = fitz.open(stream=next_bytes, filetype="pdf")
            
            # Restaurar estado de overlays (si hay callback y datos)
            if self._restore_overlay_state_callback and next_overlay is not None:
                self._restore_overlay_state_callback(next_overlay)
            
            # Restaurar mapa de páginas
            if next_page_map is not None:
                self.page_map.from_list(next_page_map)
            
            self.modified = True
            return True
        except Exception as e:
            print(f"Error al rehacer: {e}")
            return False
    
    def set_overlay_callbacks(self, get_callback, restore_callback):
        """Configura callbacks para manejar el estado de overlays del viewer."""
        self._get_overlay_state_callback = get_callback
        self._restore_overlay_state_callback = restore_callback
    
    def _save_snapshot(self, pdf_bytes: Optional[bytes] = None):
        """Guarda un snapshot del estado actual antes de una modificación.

        Args:
            pdf_bytes: Si se proporciona, se usa como bytes del doc en vez de
                llamar a doc.tobytes(). Permite reutilizar bytes ya
                capturados (p.ej. el snapshot pristine para MOVE puro)
                evitando una serialización adicional ~50-500ms.
        """
        if not self.doc:
            return

        try:
            # Guardar estado del PDF (reutilizar bytes si están disponibles)
            if pdf_bytes is None:
                current_bytes = self.doc.tobytes(garbage=0)
            else:
                current_bytes = pdf_bytes

            # Guardar estado de overlays (si hay callback)
            overlay_state = None
            if self._get_overlay_state_callback:
                overlay_state = self._get_overlay_state_callback()

            # Guardar estado del mapa de páginas
            page_map_state = self.page_map.to_list()

            # Guardar tupla (pdf_bytes, overlay_state, page_map_state)
            self._undo_snapshots.append((current_bytes, overlay_state, page_map_state))

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

        OPTIMIZACIONES de rendimiento (sin perder cambios del usuario):

        - ``garbage=1`` (era 4): elimina objetos no referenciados sin
          recorrer/deduplicar streams completos. Para un PDF de 5MB pasa
          de ~2-5s a ~200-500ms. Los Form XObjects huerfanos generados
          por MOVE puro (show_pdf_page) son raros porque limpiamos el
          snapshot tras cada commit; si crecen, basta una operacion de
          "compactar PDF" puntual.
        - ``clean=False`` (era True): saltarse la reescritura de content
          streams (operacion mas cara despues de garbage=4).
        - ``doc.save(path)`` directo en vez de ``tobytes()`` + ``write()``:
          evita una copia completa del PDF en memoria.
        - Eliminar el segundo ``tobytes()`` (era ``_original_doc_bytes =
          self.doc.tobytes()``): la variable no se lee en ninguna parte.
        """
        if not self.doc:
            return False

        save_path = file_path or self.file_path
        if not save_path:
            return False

        try:
            # tobytes con garbage=1 (era 4): elimina objetos no
            # referenciados sin recorrer/deduplicar streams completos.
            # ~5x mas rapido. clean=False evita reescribir content
            # streams (otra operacion cara). Total: pasa de ~2-5s a
            # ~200-500ms en docs de 5MB.
            pdf_bytes = self.doc.tobytes(garbage=1, deflate=True, clean=False)

            if save_path == self.file_path:
                # Mismo archivo: cerrar para liberar el lock, escribir y
                # reabrir desde el archivo recien guardado.
                self.doc.close()
                self.doc = None
                with open(save_path, 'wb') as f:
                    f.write(pdf_bytes)
                self.doc = fitz.open(save_path)
            else:
                # Guardar como archivo nuevo: escribir los bytes a disco
                # y luego recargar el doc en memoria desde esos mismos
                # bytes. Esto libera cualquier lock que tuviera al
                # archivo original (el doc pasa a estar memory-backed,
                # sin file lock). El archivo de salida tampoco queda
                # bloqueado, cumpliendo lo que esperan los tests y los
                # consumidores que quieran moverlo/eliminarlo.
                with open(save_path, 'wb') as f:
                    f.write(pdf_bytes)
                self.doc.close()
                self.doc = fitz.open("pdf", pdf_bytes)

            self.file_path = save_path
            self.modified = False
            # _original_doc_bytes se invalida; nadie lo lee actualmente y
            # recapturarlo costaba otro tobytes() entero (~50-500ms).
            self._original_doc_bytes = None
            return True
        except Exception as e:
            print(f"Error al guardar: {e}")
            # Intentar reabrir el documento si se cerró
            if self.doc is None and self.file_path:
                try:
                    self.doc = fitz.open(self.file_path)
                except Exception:
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

    def _ensure_move_source_snapshot(self) -> None:
        """Captura SÍNCRONAMENTE una copia intacta del documento para MOVE
        puro. Idempotente. Bloquea — preferir start_move_source_snapshot_async
        + wait_move_source_snapshot para no congelar la UI."""
        if self._move_source_bytes is not None or self.doc is None:
            return
        try:
            # garbage=0 + deflate=False = serializacion mas rapida posible
            self._move_source_bytes = self.doc.tobytes(garbage=0, deflate=False)
        except Exception as e:
            print(f"_ensure_move_source_snapshot: no se pudo snapshotear: {e}")
            self._move_source_bytes = None

    def start_move_source_snapshot_async(self) -> None:
        """Inicia la captura del snapshot en un hilo de fondo. Idempotente:
        si ya hay snapshot o ya hay un hilo capturando, no hace nada.

        Llamar en mousePress sobre un texto nativo: el doc.tobytes() corre
        en paralelo al drag, eliminando la pausa del primer movimiento.
        """
        with self._move_snapshot_lock:
            if self._move_source_bytes is not None:
                return
            t = self._move_snapshot_thread
            if t is not None and t.is_alive():
                return
            doc_ref = self.doc
            if doc_ref is None:
                return

            holder = {"data": None, "alive": True}

            def _capture(h=holder, d=doc_ref):
                try:
                    h["data"] = d.tobytes(garbage=0, deflate=False)
                except Exception as e:
                    print(f"snapshot async fallo: {e}")
                with self._move_snapshot_lock:
                    # Solo instalamos el resultado si este hilo sigue siendo
                    # el activo (no fue invalidado por clear_move_source_snapshot)
                    if (h["alive"] and h["data"] is not None
                            and self._move_source_bytes is None):
                        self._move_source_bytes = h["data"]

            new_t = threading.Thread(
                target=_capture,
                name="MoveSourceSnapshot",
                daemon=True,
            )
            new_t._mss_holder = holder  # type: ignore[attr-defined]
            self._move_snapshot_thread = new_t
            new_t.start()

    def wait_move_source_snapshot(self, timeout: float = 5.0) -> bool:
        """Espera a que termine la captura asíncrona (si la hay). Si no
        habia hilo lanzado, captura síncronamente. Devuelve True si hay
        snapshot disponible al terminar.

        Llamar en mouseRelease ANTES de modificar el doc, para garantizar
        que el snapshot represente el estado pristine.
        """
        with self._move_snapshot_lock:
            if self._move_source_bytes is not None:
                return True
            t = self._move_snapshot_thread
        if t is not None:
            t.join(timeout=timeout)
        # Si seguimos sin snapshot, fallback síncrono
        if self._move_source_bytes is None:
            self._ensure_move_source_snapshot()
        return self._move_source_bytes is not None

    def clear_move_source_snapshot(self) -> None:
        """Descarta el snapshot pristine usado por move_text_region.

        Si hay una captura asíncrona en curso, se invalida (su resultado se
        descarta al terminar) para que la siguiente tanda parta de cero.
        """
        with self._move_snapshot_lock:
            self._move_source_bytes = None
            t = self._move_snapshot_thread
            if t is not None:
                holder = getattr(t, "_mss_holder", None)
                if holder is not None:
                    holder["alive"] = False
            self._move_snapshot_thread = None

    @staticmethod
    def _apply_redactions_preserve_background(page) -> None:
        """Aplica redacciones eliminando ÚNICAMENTE el texto, preservando
        imágenes y gráficos vectoriales (line-art) que estuvieran debajo.

        Se usa para el flujo MOVER, donde el contenido del PDF debajo del
        texto (fotos, colores, degradados, tablas, marcas de agua) debe
        permanecer intacto tras retirar los glifos.
        """
        kwargs = {"images": fitz.PDF_REDACT_IMAGE_NONE}
        if hasattr(fitz, "PDF_REDACT_LINE_ART_NONE"):
            kwargs["graphics"] = fitz.PDF_REDACT_LINE_ART_NONE
        try:
            page.apply_redactions(**kwargs)
        except TypeError:
            # PyMuPDF antiguo sin parámetro graphics
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

    def move_text_region(
        self,
        page_num: int,
        src_rect_internal: fitz.Rect,
        dest_top_left_internal: Tuple[float, float],
        save_snapshot: bool = True,
    ) -> bool:
        """MOVE puro: clona la región (rect) de la página desde el snapshot
        pristine y la coloca en la nueva posición preservando exactamente
        glifos, fuente embebida, kerning, color, render-mode, etc.

        El método NO reescribe ni reinterpreta el texto: usa
        ``Page.show_pdf_page(clip=...)`` que extrae la región como Form
        XObject y la dibuja en el destino con escala 1:1. Es la única forma
        de garantizar resultado visualmente idéntico al original.

        Args:
            page_num: Página destino (mismo doc).
            src_rect_internal: Rect en coords internas (mediabox) del span
                original a clonar. Debe corresponder al snapshot pristine.
            dest_top_left_internal: (x, y) en coords internas, esquina
                superior izquierda donde colocar el bloque clonado.
            save_snapshot: Si True, guarda snapshot de undo antes de modificar.

        Returns:
            True si la operación se completó.
        """
        if self.doc is None:
            return False
        page = self.get_page(page_num)
        if page is None:
            return False

        # Espera al snapshot asíncrono si esta en marcha; si no hay, lo
        # captura síncronamente como fallback.
        if not self.wait_move_source_snapshot():
            return False

        if save_snapshot:
            self._save_snapshot()

        src_doc = None
        try:
            src_doc = fitz.open("pdf", self._move_source_bytes)
            if page_num < 0 or page_num >= src_doc.page_count:
                return False
            src_rect = fitz.Rect(src_rect_internal)
            if src_rect.is_empty or src_rect.is_infinite:
                return False
            dx = float(dest_top_left_internal[0])
            dy = float(dest_top_left_internal[1])
            dest_rect = fitz.Rect(
                dx, dy,
                dx + src_rect.width,
                dy + src_rect.height,
            )

            # CRÍTICO: limpiar TODO lo que está fuera del span en la página
            # fuente ANTES de clonarla. Sin esto, el Form XObject creado por
            # show_pdf_page contiene la página completa — aunque visualmente
            # se vea solo la región del clip, get_text() y las herramientas
            # de edición pueden detectar el resto del contenido como "texto
            # fantasma con texto invisible". Redactar el complemento del
            # span garantiza que el XObject solo contenga los glifos del
            # bloque movido.
            src_page = src_doc[page_num]
            page_w = src_page.rect.width
            page_h = src_page.rect.height
            # Cuatro bandas que cubren todo lo que está fuera del span:
            outside_rects = [
                fitz.Rect(0, 0, page_w, src_rect.y0),                # arriba
                fitz.Rect(0, src_rect.y1, page_w, page_h),           # abajo
                fitz.Rect(0, src_rect.y0, src_rect.x0, src_rect.y1), # izq
                fitz.Rect(src_rect.x1, src_rect.y0, page_w, src_rect.y1),  # der
            ]
            for r in outside_rects:
                if not r.is_empty and r.width > 0 and r.height > 0:
                    # fill=False: no pintar blanco al limpiar el complemento
                    # del span en el clon (evita slabs blancas en el XObject
                    # si por cualquier razón se renderizara fuera del clip).
                    src_page.add_redact_annot(r, fill=False)
            try:
                self._apply_redactions_preserve_background(src_page)
            except Exception as e:
                print(f"move_text_region: apply_redactions falló: {e}")

            # keep_proportion=True + mismas dimensiones que src ⇒ escala 1:1.
            page.show_pdf_page(
                dest_rect,
                src_doc,
                page_num,
                clip=src_rect,
                keep_proportion=True,
                overlay=True,
            )

            # Eliminar el texto original de la página real SIN tocar el fondo.
            # Esto convierte la operación en un MOVE real (no copia): los
            # glifos desaparecen del origen, pero la imagen/color/degradado/
            # tabla/gráfico que hubiera debajo permanece intacto.
            try:
                page.add_redact_annot(src_rect, fill=False)
                self._apply_redactions_preserve_background(page)
            except Exception as e:
                print(f"move_text_region: limpieza no destructiva del origen falló: {e}")

            self.modified = True
            return True
        except Exception as e:
            print(f"move_text_region ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if src_doc is not None:
                try:
                    src_doc.close()
                except Exception:
                    pass

    def add_text_runs_to_page(
        self,
        page_num: int,
        base_rect: fitz.Rect,
        runs: List[Dict[str, Any]],
        line_spacing: float = None,
        save_snapshot: bool = True
    ) -> bool:
        """
        Añade múltiples runs de texto con diferentes estilos a una página.
        
        Permite escribir texto con partes en diferentes formatos (ej: algunas palabras en negrita).
        Preserva saltos de línea, tabulaciones e indentaciones.
        PRESERVA: tipografía, tamaño, interlineado y estilos originales.
        
        Args:
            page_num: Número de página
            base_rect: Área base donde colocar el texto
            runs: Lista de dicts con: text, is_bold, is_italic, font_size, color, needs_newline, indent, font_name
            line_spacing: Interlineado original (si None, calcula automáticamente)
            save_snapshot: Si True, guarda snapshot para undo
            
        Returns:
            True si se añadió correctamente
        """
        page = self.get_page(page_num)
        if not page or not runs:
            return False
        
        try:
            if save_snapshot:
                self._save_snapshot()
            
            # Posición inicial de inserción
            start_x = base_rect.x0 + 2
            current_x = start_x
            current_y = base_rect.y0
            
            # Calcular altura base para el baseline
            base_font_size = runs[0].get('font_size', 12)
            
            # Usar interlineado proporcionado o calcular uno basado en el tamaño de fuente
            if line_spacing is not None and line_spacing > 0:
                effective_line_height = line_spacing
            else:
                effective_line_height = base_font_size * 1.2  # Estándar si no hay info
            
            current_y += base_font_size
            
            for run in runs:
                text = run.get('text', '')
                if not text:
                    continue
                
                # Manejar salto de línea
                needs_newline = run.get('needs_newline', False)
                if needs_newline:
                    current_y += effective_line_height
                    current_x = start_x
                
                # Manejar indentación
                indent = run.get('indent', 0)
                is_line_start = run.get('is_line_start', False)
                if is_line_start and indent > 0:
                    current_x = start_x + indent
                
                is_bold = run.get('is_bold', run.get('bold', False))
                is_italic = run.get('is_italic', run.get('italic', False))
                font_size = run.get('font_size', base_font_size)
                original_font_name = run.get('font_name', '')
                
                # Convertir color
                color = run.get('color', '#000000')
                if isinstance(color, str) and color.startswith('#'):
                    r = int(color[1:3], 16) / 255.0
                    g = int(color[3:5], 16) / 255.0
                    b = int(color[5:7], 16) / 255.0
                    color_tuple = (r, g, b)
                elif isinstance(color, tuple):
                    color_tuple = color
                else:
                    color_tuple = (0, 0, 0)
                
                # Mapear fuente original a fuente PDF disponible
                font_name = self._map_font_to_pdf(original_font_name, is_bold, is_italic)
                
                # Calcular ancho del texto para posicionar el siguiente run
                from PyQt5.QtGui import QFont, QFontMetrics
                # Usar el nombre de fuente original para métricas más precisas
                qt_font_name = self._get_qt_font_name(original_font_name)
                qfont = QFont(qt_font_name, int(font_size))
                if is_bold:
                    qfont.setBold(True)
                if is_italic:
                    qfont.setItalic(True)
                metrics = QFontMetrics(qfont)
                text_width = metrics.horizontalAdvance(text)
                
                # Insertar el texto
                insert_point = fitz.Point(current_x, current_y)
                rc = page.insert_text(
                    insert_point,
                    text,
                    fontsize=font_size,
                    fontname=font_name,
                    color=color_tuple
                )
                
                if rc <= 0:
                    print(f"Warning: insert_text failed for run '{text}' with rc={rc}")
                
                # Avanzar la posición X
                # Usar factor de escala para ajustar diferencia Qt vs PDF
                current_x += text_width * 0.75  # Factor de ajuste empírico
                
                # Si es fin de línea, preparar para siguiente línea
                is_line_end = run.get('is_line_end', False)
                if is_line_end:
                    # El siguiente run que sea is_line_start manejará el posicionamiento
                    pass
            
            self.modified = True
            return True
            
        except Exception as e:
            print(f"add_text_runs_to_page - ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _map_font_to_pdf(self, original_font_name: str, is_bold: bool, is_italic: bool) -> str:
        """
        Mapea el nombre de fuente original a una fuente PDF base14 disponible.
        Intenta preservar la familia de fuentes original lo mejor posible.
        
        Args:
            original_font_name: Nombre de la fuente original del PDF
            is_bold: Si el texto es negrita
            is_italic: Si el texto es itálica
            
        Returns:
            Nombre de fuente PDF base14 (helv, hebo, heit, hebi, tiro, tibo, tiit, tibi, cour, cobo, coit, cobi)
        """
        if not original_font_name:
            original_font_name = ""
        
        font_lower = original_font_name.lower()
        
        # Detectar familia de fuentes
        is_times = any(x in font_lower for x in ['times', 'tiro', 'serif', 'roman', 'georgia', 'palatino', 'garamond'])
        is_courier = any(x in font_lower for x in ['courier', 'cour', 'mono', 'consolas', 'monaco', 'menlo', 'source code'])
        is_arial = any(x in font_lower for x in ['arial', 'helv', 'helvetica', 'sans', 'verdana', 'tahoma', 'calibri', 'frutiger', 'trebuchet', 'segoe'])
        
        # Si no se detecta familia, usar Helvetica como default
        if not is_times and not is_courier:
            is_arial = True
        
        # Mapear a fuente base14
        if is_times:
            if is_bold and is_italic:
                return "tibi"  # Times-BoldItalic
            elif is_bold:
                return "tibo"  # Times-Bold
            elif is_italic:
                return "tiit"  # Times-Italic
            else:
                return "tiro"  # Times-Roman
        elif is_courier:
            if is_bold and is_italic:
                return "cobi"  # Courier-BoldOblique
            elif is_bold:
                return "cobo"  # Courier-Bold
            elif is_italic:
                return "coit"  # Courier-Oblique
            else:
                return "cour"  # Courier
        else:  # Helvetica/Arial family
            if is_bold and is_italic:
                return "hebi"  # Helvetica-BoldOblique
            elif is_bold:
                return "hebo"  # Helvetica-Bold
            elif is_italic:
                return "heit"  # Helvetica-Oblique
            else:
                return "helv"  # Helvetica

    def _get_qt_font_name(self, original_font_name: str) -> str:
        """
        Obtiene un nombre de fuente Qt equivalente para métricas de texto.
        
        Args:
            original_font_name: Nombre de la fuente original del PDF
            
        Returns:
            Nombre de fuente para usar con QFont
        """
        if not original_font_name:
            return "Helvetica"
        
        font_lower = original_font_name.lower()
        
        # Mapear familias comunes
        if any(x in font_lower for x in ['times', 'tiro', 'roman', 'georgia', 'palatino']):
            return "Times New Roman"
        elif any(x in font_lower for x in ['courier', 'cour', 'mono', 'consolas']):
            return "Courier New"
        elif any(x in font_lower for x in ['arial', 'frutiger', 'trebuchet', 'segoe']):
            return "Arial"
        else:
            return "Helvetica"

    def get_text_spans_in_rect(self, page_num: int, rect: fitz.Rect) -> List[Dict[str, Any]]:
        """
        Extrae todos los spans de texto en un área con su información completa.
        
        Cada span representa un fragmento de texto con estilo consistente.
        Esto permite reconstruir texto con múltiples estilos (ej: parcialmente en negrita).
        Preserva tabulaciones, indentaciones y saltos de línea.
        
        Args:
            page_num: Número de página (0-indexed)
            rect: Rectángulo del área a analizar
            
        Returns:
            Lista de dicts con: text, font_name, font_size, is_bold, is_italic, color, rect, 
                               indent, is_line_start, is_line_end
        """
        spans_info: List[Dict[str, Any]] = []
        
        if not self.doc or page_num >= self.page_count():
            return spans_info
        
        try:
            page = self.doc[page_num]
            text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            
            # Calcular el margen izquierdo mínimo del área para detectar indentación
            area_left = rect.x0
            prev_line_y = None
            
            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                
                block_rect = fitz.Rect(block.get("bbox", (0, 0, 0, 0)))
                if not block_rect.intersects(rect):
                    continue
                
                lines = block.get("lines", [])
                for line_idx, line in enumerate(lines):
                    line_rect = fitz.Rect(line.get("bbox", (0, 0, 0, 0)))
                    
                    # Verificar si la línea está dentro del área
                    if not line_rect.intersects(rect):
                        continue
                    
                    # Calcular indentación de esta línea
                    line_left = line_rect.x0
                    line_indent = max(0, line_left - area_left)
                    
                    # Detectar si hay salto de línea (diferente Y)
                    is_new_line = False
                    if prev_line_y is not None and abs(line_rect.y0 - prev_line_y) > 2:
                        is_new_line = True
                    prev_line_y = line_rect.y0
                    
                    spans = line.get("spans", [])
                    for span_idx, span in enumerate(spans):
                        span_rect = fitz.Rect(span["bbox"])
                        
                        # Verificar si el span intersecta con el área
                        if not span_rect.intersects(rect):
                            continue
                        
                        text = span.get("text", "")
                        if not text:
                            continue
                        
                        # Extraer información de estilo
                        font_name = span.get("font", "")
                        font_size = span.get("size", 12.0)
                        flags = span.get("flags", 0)
                        
                        # Detectar bold/italic desde flags
                        is_bold = bool(flags & 16) or "bold" in font_name.lower() or "bd" in font_name.lower()
                        is_italic = bool(flags & 2) or "italic" in font_name.lower() or "oblique" in font_name.lower()
                        
                        # Convertir color
                        color_val = span.get("color", 0)
                        if isinstance(color_val, int):
                            r = (color_val >> 16) & 255
                            g = (color_val >> 8) & 255
                            b = color_val & 255
                            color = f"#{r:02x}{g:02x}{b:02x}"
                        else:
                            color = "#000000"
                        
                        # Marcar posición en la línea
                        is_line_start = (span_idx == 0)
                        is_line_end = (span_idx == len(spans) - 1)
                        
                        # Si es el primer span de una nueva línea, agregar salto de línea
                        needs_newline = is_new_line and is_line_start
                        
                        spans_info.append({
                            'text': text,
                            'font_name': font_name,
                            'font_size': font_size,
                            'is_bold': is_bold,
                            'is_italic': is_italic,
                            'color': color,
                            'rect': span_rect,
                            'flags': flags,
                            'indent': line_indent,
                            'is_line_start': is_line_start,
                            'is_line_end': is_line_end,
                            'needs_newline': needs_newline,
                            'line_y': line_rect.y0
                        })
                        
                        # Solo marcar nueva línea para el primer span
                        if is_new_line:
                            is_new_line = False
            
            # Ordenar por posición vertical primero, luego horizontal
            spans_info.sort(key=lambda s: (s['line_y'], s['rect'].x0))
            
            return spans_info
        
        except Exception as e:
            self._last_error = f"Error extracting text spans: {str(e)}"
            return []

    def get_text_run_descriptors(self, page_num: int, rect: fitz.Rect) -> List[FontDescriptor]:
        """
        Extrae descriptores de fuente de todas las corridas de texto en un área.
        
        Integración con FontManager para obtener información de fuentes en PDF.
        
        Args:
            page_num: Número de página (0-indexed)
            rect: Rectángulo del área a analizar
            
        Returns:
            Lista de FontDescriptor con información de cada corrida de texto
        """
        descriptors: List[FontDescriptor] = []
        
        if not self.doc or page_num >= self.page_count():
            return descriptors
        
        try:
            page = self.doc[page_num]
            font_manager = get_font_manager()
            
            # Obtener bloques de texto
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if block["type"] != 0:  # Solo bloques de texto
                    continue
                
                # Procesar líneas dentro del bloque
                for line in block.get("lines", []):
                    line_rect = fitz.Rect(line["bbox"])
                    
                    # Verificar si la línea intersecta con el área
                    if not line_rect.intersects(rect):
                        continue
                    
                    # Procesar caracteres en la línea
                    for span in line.get("spans", []):
                        # Crear estructura compatible con font_manager
                        span_dict = {
                            "font": span.get("font", ""),
                            "size": span.get("size", 12.0),
                            "color": span.get("color", 0),
                            "flags": span.get("flags", 0),
                        }
                        
                        # Detectar fuente usando FontManager
                        descriptor = font_manager.detect_font(span_dict)
                        descriptors.append(descriptor)
            
            return descriptors
        
        except Exception as e:
            self._last_error = f"Error extracting font descriptors: {str(e)}"
            return []

    def replace_text_preserving_metrics(
        self, 
        page_num: int, 
        old_text: str, 
        new_text: str,
        preserve_bold: bool = True
    ) -> bool:
        """
        Reemplaza texto preservando métricas de fuente y estilos (bold, itálica).
        
        Integración con FontManager para mantener consistencia visual durante reemplazo.
        
        Args:
            page_num: Número de página
            old_text: Texto a reemplazar
            new_text: Texto nuevo
            preserve_bold: Si True, mantiene bold si fue detectado
            
        Returns:
            True si la operación fue exitosa
        """
        if not self.doc or page_num >= self.page_count():
            return False
        
        try:
            page = self.doc[page_num]
            font_manager = get_font_manager()
            
            # Buscar todas las ocurrencias del texto
            search_results = self.search_text(old_text, page_num)
            
            if not search_results:
                self._last_error = f"Text '{old_text}' not found on page {page_num}"
                return False
            
            self._save_snapshot()
            
            # Procesar cada ocurrencia (de atrás hacia adelante para evitar offset)
            for page_idx, rect in reversed(search_results):
                if page_idx != page_num:
                    continue
                
                # Obtener descriptores del texto original
                descriptors = self.get_text_run_descriptors(page_num, rect)
                
                if not descriptors:
                    # Si no hay descriptores, usar valores por defecto
                    self.edit_text(page_num, rect, new_text)
                else:
                    # Usar el primer descriptor como referencia
                    first_desc = descriptors[0]
                    color = int(first_desc.color.lstrip("#"), 16) if first_desc.color else 0
                    
                    # Aplicar bold si estaba presente y preserve_bold es True
                    if preserve_bold and first_desc.possible_bold:
                        # Usar handle_bold para aplicar el estilo
                        bold_text, _ = font_manager.handle_bold(
                            new_text, 
                            first_desc,
                            True
                        )
                        self.edit_text(
                            page_num, rect, bold_text,
                            first_desc.name, first_desc.size, color
                        )
                    else:
                        self.edit_text(
                            page_num, rect, new_text,
                            first_desc.name, first_desc.size, color
                        )
            
            self.modified = True
            return True
        
        except Exception as e:
            self._last_error = f"Error replacing text with metrics: {str(e)}"
            return False

    def detect_bold_in_span(self, page_num: int, rect: fitz.Rect) -> Optional[bool]:
        """
        Detecta si el texto en un área está en negrita usando heurísticas.
        
        Utiliza FontManager para aplicar heurísticas de detección de bold
        (análisis de nombre de fuente, comparación de ancho, etc.).
        
        Args:
            page_num: Número de página
            rect: Rectángulo del área a analizar
            
        Returns:
            True si parece estar en bold, False si no, None si no se puede determinar
        """
        if not self.doc or page_num >= self.page_count():
            return None
        
        try:
            font_manager = get_font_manager()
            descriptors = self.get_text_run_descriptors(page_num, rect)
            
            if not descriptors:
                return None
            
            # Usar el primer descriptor para análisis
            first_desc = descriptors[0]
            
            # Utilizar método de FontManager para detectar bold
            possible_bold = font_manager.detect_possible_bold({
                "font": first_desc.fallback_from or first_desc.name,
                "size": first_desc.size,
                "flags": 0,
            })
            
            return possible_bold
        
        except Exception as e:
            self._last_error = f"Error detecting bold: {str(e)}"
            return None

    # ================================================================
    # OPERACIONES DE PÁGINA: Insertar, Mover, Reordenar, Eliminar
    # ================================================================
    
    def insert_pdf(self, source_path: str, at_page: int = -1) -> Optional[int]:
        """
        Inserta todas las páginas de un PDF externo en la posición indicada.
        
        Args:
            source_path: Ruta al PDF a insertar.
            at_page: Índice donde insertar (0-based). 
                     -1 = al final del documento.
        
        Returns:
            Número de páginas insertadas, o None si falló.
        """
        if not self.doc:
            self._last_error = "No hay documento abierto"
            return None
        
        try:
            # Abrir como bytes para evitar bloqueo de archivo
            with open(source_path, 'rb') as f:
                source_bytes = f.read()
            source_doc = fitz.open(stream=source_bytes, filetype="pdf")
            
            if source_doc.page_count == 0:
                source_doc.close()
                self._last_error = "El PDF a insertar no tiene páginas"
                return None
            
            insert_count = source_doc.page_count
            
            # Guardar snapshot antes de modificar
            self._save_snapshot()
            
            # Posición de inserción
            if at_page < 0 or at_page > self.doc.page_count:
                effective_page = self.doc.page_count
                start_at = -1  # al final
            else:
                effective_page = at_page
                start_at = at_page  # PyMuPDF: inserta ANTES de esta página
            
            self.doc.insert_pdf(source_doc, start_at=start_at)
            
            source_doc.close()
            
            # Actualizar mapa de identidad
            self.page_map.insert_pages(effective_page, insert_count)
            
            self.modified = True
            return insert_count
        except Exception as e:
            self._last_error = str(e)
            print(f"Error al insertar PDF: {e}")
            return None
    
    def insert_image(self, page_num: int, rect: fitz.Rect, image_path: str = None,
                     keep_proportion: bool = True, overlay: bool = True,
                     image_bytes: bytes = None) -> bool:
        """Inserta una imagen en una página del PDF.
        
        Args:
            page_num: Número de página (0-based).
            rect: Rectángulo donde colocar la imagen (coordenadas PDF).
            image_path: Ruta al archivo de imagen (PNG, JPEG, BMP, etc.).
            keep_proportion: Mantener proporción de la imagen.
            overlay: True para colocar sobre el contenido existente.
            image_bytes: Bytes de la imagen (alternativa a image_path).
            
        Returns:
            True si la imagen se insertó correctamente.
        """
        if not self.doc:
            self._last_error = "No hay documento abierto"
            return False
        
        page = self.get_page(page_num)
        if not page:
            self._last_error = f"Página {page_num} no válida"
            return False
        
        if not image_bytes and not image_path:
            self._last_error = "Se requiere image_path o image_bytes"
            return False
        
        if image_path and not image_bytes and not os.path.isfile(image_path):
            self._last_error = f"Archivo de imagen no encontrado: {image_path}"
            return False
        
        try:
            self._save_snapshot()
            if image_bytes:
                page.insert_image(
                    rect,
                    stream=image_bytes,
                    keep_proportion=keep_proportion,
                    overlay=overlay,
                )
            else:
                page.insert_image(
                    rect,
                    filename=image_path,
                    keep_proportion=keep_proportion,
                    overlay=overlay,
                )
            self.modified = True
            return True
        except Exception as e:
            self._last_error = str(e)
            print(f"Error al insertar imagen: {e}")
            return False
    
    def insert_pages_from_pdf(self, source_path: str,
                               source_pages: List[int],
                               at_page: int = -1) -> Optional[int]:
        """
        Inserta páginas específicas de un PDF externo.
        
        Args:
            source_path: Ruta al PDF fuente.
            source_pages: Lista de índices de páginas a insertar del fuente (0-based).
            at_page: Posición de inserción en el documento actual (0-based). -1=final.
        
        Returns:
            Número de páginas insertadas, o None si falló.
        """
        if not self.doc:
            self._last_error = "No hay documento abierto"
            return None
        
        try:
            with open(source_path, 'rb') as f:
                source_bytes = f.read()
            source_doc = fitz.open(stream=source_bytes, filetype="pdf")
            
            # Validar páginas solicitadas
            valid_pages = [p for p in source_pages if 0 <= p < source_doc.page_count]
            if not valid_pages:
                source_doc.close()
                self._last_error = "Ninguna página válida para insertar"
                return None
            
            # Guardar snapshot antes de modificar
            self._save_snapshot()
            
            if at_page < 0 or at_page > self.doc.page_count:
                at_page = self.doc.page_count
            
            # Insertar cada página individualmente en orden
            start_at = at_page - 1 if at_page > 0 else -1
            for i, src_page in enumerate(valid_pages):
                self.doc.insert_pdf(source_doc, from_page=src_page, to_page=src_page,
                                    start_at=start_at + i if start_at >= 0 else -1 + i)
            
            source_doc.close()
            
            insert_count = len(valid_pages)
            self.page_map.insert_pages(at_page, insert_count)
            
            self.modified = True
            return insert_count
        except Exception as e:
            self._last_error = str(e)
            print(f"Error al insertar páginas: {e}")
            return None
    
    def move_page(self, from_index: int, to_index: int) -> bool:
        """
        Mueve una página de una posición a otra.
        
        Args:
            from_index: Posición actual de la página (0-based).
            to_index: Nueva posición deseada (0-based).
        
        Returns:
            True si se movió correctamente.
        """
        if not self.doc:
            return False
        
        if from_index == to_index:
            return True  # No hacer nada
        
        if not (0 <= from_index < self.doc.page_count):
            self._last_error = f"Índice origen inválido: {from_index}"
            return False
        if not (0 <= to_index < self.doc.page_count):
            self._last_error = f"Índice destino inválido: {to_index}"
            return False
        
        try:
            self._save_snapshot()
            
            # Construir nueva orden
            order = list(range(self.doc.page_count))
            page = order.pop(from_index)
            order.insert(to_index, page)
            
            # Aplicar con select() de PyMuPDF
            self.doc.select(order)
            self.page_map.move_page(from_index, to_index)
            
            self.modified = True
            return True
        except Exception as e:
            self._last_error = str(e)
            print(f"Error al mover página: {e}")
            return False
    
    def reorder_pages(self, new_order: List[int]) -> bool:
        """
        Reordena todas las páginas según la lista dada.
        
        Args:
            new_order: Lista donde new_order[nueva_pos] = vieja_pos.
                       Ejemplo: [2, 0, 1] → la pág 2 pasa a ser la 0.
        
        Returns:
            True si se reordenó correctamente.
        """
        if not self.doc:
            return False
        
        # Validar que es una permutación válida
        if sorted(new_order) != list(range(self.doc.page_count)):
            self._last_error = "La lista de reorden no es una permutación válida"
            return False
        
        # Si el orden no cambia, no hacer nada
        if new_order == list(range(self.doc.page_count)):
            return True
        
        try:
            self._save_snapshot()
            
            self.doc.select(new_order)
            self.page_map.reorder(new_order)
            
            self.modified = True
            return True
        except Exception as e:
            self._last_error = str(e)
            print(f"Error al reordenar páginas: {e}")
            return False
    
    def rotate_page(self, page_num: int, angle: int) -> Optional[tuple]:
        """
        Rota una página del documento.
        
        Args:
            page_num: Índice de la página a rotar (0-based).
            angle: Ángulo de rotación a añadir (90, 180, 270).
        
        Returns:
            Tupla (old_width, old_height, new_rotation) o None si falló.
        """
        if not self.doc:
            return None
        
        page = self.get_page(page_num)
        if not page:
            self._last_error = f"Página {page_num} no encontrada"
            return None
        
        if angle not in (90, 180, 270):
            self._last_error = f"Ángulo inválido: {angle}. Usar 90, 180 o 270."
            return None
        
        try:
            self._save_snapshot()
            
            # Guardar dimensiones visuales OLD antes de rotar
            old_width = page.rect.width
            old_height = page.rect.height
            
            # Aplicar rotación (solo modifica metadato /Rotate)
            new_rotation = (page.rotation + angle) % 360
            page.set_rotation(new_rotation)
            
            self.modified = True
            return (old_width, old_height, new_rotation)
        except Exception as e:
            self._last_error = str(e)
            print(f"Error al rotar página: {e}")
            return None
    
    def delete_page(self, page_index: int) -> Optional[str]:
        """
        Elimina una página del documento.
        
        Args:
            page_index: Índice de la página a eliminar (0-based).
        
        Returns:
            UUID de la página eliminada, o None si falló.
        """
        if not self.doc:
            return None
        
        if self.doc.page_count <= 1:
            self._last_error = "No se puede eliminar la única página del documento"
            return None
        
        if not (0 <= page_index < self.doc.page_count):
            self._last_error = f"Índice de página inválido: {page_index}"
            return None
        
        try:
            self._save_snapshot()
            
            deleted_uuid = self.page_map.remove_page(page_index)
            self.doc.delete_page(page_index)
            
            self.modified = True
            return deleted_uuid
        except Exception as e:
            self._last_error = str(e)
            print(f"Error al eliminar página: {e}")
            return None
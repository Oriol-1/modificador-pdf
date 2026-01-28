"""
Visor de páginas PDF con soporte para zoom, scroll y selección de texto.
"""

from PyQt5.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsRectItem, QMenu, QAction, QInputDialog, QMessageBox,
    QGraphicsTextItem, QGraphicsDropShadowEffect, QToolTip
)
from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QPointF, QTimer
from PyQt5.QtGui import (
    QPixmap, QImage, QPen, QBrush, QColor, QPainter, QCursor,
    QFont, QFontMetrics
)
import fitz


class SelectionRect(QGraphicsRectItem):
    """Rectángulo de selección visual mejorado."""
    
    def __init__(self, rect=QRectF(), mode='select'):
        super().__init__(rect)
        self.mode = mode
        self.update_style()
        self.setZValue(100)
    
    def update_style(self):
        if self.mode == 'delete':
            # Rojo para eliminación
            self.setPen(QPen(QColor(255, 80, 80), 2, Qt.SolidLine))
            self.setBrush(QBrush(QColor(255, 0, 0, 40)))
        elif self.mode == 'highlight':
            # Amarillo para resaltado
            self.setPen(QPen(QColor(255, 200, 0), 2, Qt.SolidLine))
            self.setBrush(QBrush(QColor(255, 255, 0, 60)))
        else:
            # Azul para selección normal
            self.setPen(QPen(QColor(0, 120, 215), 2, Qt.DashLine))
            self.setBrush(QBrush(QColor(0, 120, 215, 40)))
    
    def set_mode(self, mode):
        self.mode = mode
        self.update_style()


class DeletePreviewRect(QGraphicsRectItem):
    """Rectángulo de previsualización de borrado con animación."""
    
    def __init__(self, rect=QRectF()):
        super().__init__(rect)
        self.setPen(QPen(QColor(255, 50, 50), 3, Qt.SolidLine))
        self.setBrush(QBrush(QColor(255, 0, 0, 80)))
        self.setZValue(90)
        
        # Efecto de sombra
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(255, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)


class FloatingLabel(QGraphicsTextItem):
    """Etiqueta flotante para mostrar información."""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setDefaultTextColor(QColor(255, 255, 255))
        font = QFont("Segoe UI", 10, QFont.Bold)
        self.setFont(font)
        self.setZValue(200)
    
    def set_background(self, color):
        pass  # Se maneja en paint


class HighlightRect(QGraphicsRectItem):
    """Rectángulo de resaltado."""
    
    def __init__(self, rect=QRectF(), color=QColor(255, 255, 0, 100)):
        super().__init__(rect)
        self.setPen(QPen(Qt.NoPen))
        self.setBrush(QBrush(color))
        self.setZValue(50)


class PDFPageView(QGraphicsView):
    """Vista de una página de PDF con capacidades de selección y edición."""
    
    # Señales
    selectionChanged = pyqtSignal(QRectF)  # Emitida cuando cambia la selección
    textSelected = pyqtSignal(str, QRectF)  # Texto seleccionado y su rectángulo
    pageClicked = pyqtSignal(QPointF)  # Click en la página
    zoomChanged = pyqtSignal(float)  # Cambio de zoom
    documentModified = pyqtSignal()  # Emitida cuando el documento se modifica
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # Configuración de vista
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setRenderHint(QPainter.TextAntialiasing)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setBackgroundBrush(QBrush(QColor(50, 50, 50)))
        
        # Estilo moderno
        self.setStyleSheet("""
            QGraphicsView {
                border: none;
                background-color: #323232;
            }
            QScrollBar:vertical {
                background-color: #2d2d30;
                width: 12px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #5a5a5a;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #787878;
            }
            QScrollBar:horizontal {
                background-color: #2d2d30;
                height: 12px;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background-color: #5a5a5a;
                border-radius: 6px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #787878;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                height: 0px;
                width: 0px;
            }
        """)
        
        # Estado
        self.pdf_doc = None
        self.current_page = 0
        self.zoom_level = 1.0
        self.min_zoom = 0.25
        self.max_zoom = 5.0
        
        # Items gráficos
        self.page_item = None
        self.selection_rect = None
        self.delete_preview = None
        self.floating_label = None
        self.highlight_items = []
        
        # Modo de herramienta
        self.tool_mode = 'select'  # 'select', 'highlight', 'delete', 'edit'
        
        # Estado de selección
        self.is_selecting = False
        self.selection_start = None
        self.current_selection = None
        
        # Timer para actualizar preview
        self.preview_timer = QTimer()
        self.preview_timer.timeout.connect(self.update_delete_preview)
        
        # Configurar menú contextual
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def set_pdf_document(self, pdf_doc):
        """Establece el documento PDF a mostrar."""
        # Limpiar estado anterior completamente
        self.clear_all_state()
        
        self.pdf_doc = pdf_doc
        if pdf_doc and pdf_doc.is_open():
            self.load_page(0)
    
    def clear_all_state(self):
        """Limpia todo el estado del visor para evitar conflictos."""
        # Detener timers
        if hasattr(self, 'preview_timer'):
            self.preview_timer.stop()
        
        # Limpiar selección
        self.is_selecting = False
        self.selection_start = None
        self.current_selection = None
        
        # Limpiar escena
        self.scene.clear()
        
        # Reiniciar referencias a items gráficos
        self.page_item = None
        self.selection_rect = None
        self.delete_preview = None
        self.floating_label = None
        self.highlight_items = []
        
        # Reiniciar página
        self.current_page = 0
    
    def load_page(self, page_num: int):
        """Carga y muestra una página específica."""
        if not self.pdf_doc or not self.pdf_doc.is_open():
            return
        
        if page_num < 0 or page_num >= self.pdf_doc.page_count():
            return
        
        self.current_page = page_num
        self.render_page()
    
    def render_page(self):
        """Renderiza la página actual con el nivel de zoom actual."""
        if not self.pdf_doc or not self.pdf_doc.is_open():
            return
        
        # Limpiar escena
        self.scene.clear()
        self.highlight_items.clear()
        self.selection_rect = None
        self.delete_preview = None
        self.floating_label = None
        
        # Renderizar página
        pixmap = self.pdf_doc.render_page(self.current_page, self.zoom_level)
        if not pixmap:
            return
        
        # Convertir a QImage
        img = QImage(
            pixmap.samples,
            pixmap.width,
            pixmap.height,
            pixmap.stride,
            QImage.Format_RGB888
        )
        
        # Crear item de imagen
        qpixmap = QPixmap.fromImage(img)
        self.page_item = QGraphicsPixmapItem(qpixmap)
        self.scene.addItem(self.page_item)
        
        # Ajustar escena
        self.scene.setSceneRect(self.page_item.boundingRect())
        
        # Mostrar indicadores de texto seleccionable si está en modo eliminar
        if self.tool_mode == 'delete':
            self.show_text_hints()
        
        # Mostrar indicadores de resaltados existentes si está en modo highlight
        if self.tool_mode == 'highlight':
            self.show_existing_highlights()
    
    def show_existing_highlights(self):
        """Muestra indicadores visuales de los resaltados existentes que pueden eliminarse."""
        if not self.pdf_doc or not self.pdf_doc.is_open():
            return
        
        try:
            highlights = self.pdf_doc.get_highlight_annotations(self.current_page)
            
            for hl in highlights:
                # Convertir a coordenadas de vista
                view_rect = self.pdf_to_view_rect(hl['rect'])
                
                # Crear un indicador visual con borde para mostrar que es eliminable
                indicator = QGraphicsRectItem(view_rect)
                indicator.setPen(QPen(QColor(255, 100, 100, 200), 2, Qt.DashLine))
                indicator.setBrush(QBrush(Qt.NoBrush))
                indicator.setZValue(60)
                indicator.setToolTip("Click para eliminar este resaltado")
                self.scene.addItem(indicator)
        except Exception as e:
            print(f"Error mostrando resaltados: {e}")

    def set_tool_mode(self, mode: str):
        """Establece el modo de herramienta actual."""
        self.tool_mode = mode
        
        if mode == 'select':
            self.setCursor(Qt.IBeamCursor)
            self.setStyleSheet(self.styleSheet())  # Mantener estilo
        elif mode == 'highlight':
            self.setCursor(Qt.CrossCursor)
        elif mode == 'delete':
            # Cursor personalizado para borrado
            self.setCursor(Qt.CrossCursor)
        elif mode == 'edit':
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        
        # Limpiar selección previa al cambiar herramienta
        self.clear_selection()
        
        # Mostrar/ocultar indicadores de texto
        if self.pdf_doc and self.pdf_doc.is_open():
            self.render_page()
    
    def show_text_hints(self):
        """Muestra indicadores sutiles de dónde hay texto seleccionable."""
        if not self.pdf_doc or not self.pdf_doc.is_open():
            return
        
        try:
            # Obtener todos los bloques de texto
            blocks = self.pdf_doc.get_text_blocks(self.current_page)
            
            for block in blocks:
                # Convertir a coordenadas de vista
                view_rect = self.pdf_to_view_rect(block.rect)
                
                # Crear un indicador sutil (borde muy tenue)
                hint = QGraphicsRectItem(view_rect)
                hint.setPen(QPen(QColor(100, 200, 255, 60), 1))
                hint.setBrush(QBrush(QColor(100, 200, 255, 25)))
                hint.setZValue(10)
                self.scene.addItem(hint)
        except Exception as e:
            print(f"Error mostrando hints: {e}")
    
    def zoom_in(self):
        """Aumenta el zoom."""
        new_zoom = min(self.zoom_level * 1.25, self.max_zoom)
        self.set_zoom(new_zoom)
    
    def zoom_out(self):
        """Disminuye el zoom."""
        new_zoom = max(self.zoom_level / 1.25, self.min_zoom)
        self.set_zoom(new_zoom)
    
    def set_zoom(self, zoom: float):
        """Establece un nivel de zoom específico."""
        if zoom == self.zoom_level:
            return
        
        self.zoom_level = max(self.min_zoom, min(zoom, self.max_zoom))
        self.render_page()
        self.zoomChanged.emit(self.zoom_level)
    
    def fit_width(self):
        """Ajusta el zoom para que la página ocupe todo el ancho."""
        if not self.page_item:
            return
        
        view_width = self.viewport().width() - 20  # Margen
        page_width = self.page_item.boundingRect().width()
        
        if page_width > 0:
            new_zoom = (view_width / page_width) * self.zoom_level
            self.set_zoom(new_zoom)
    
    def fit_page(self):
        """Ajusta el zoom para ver la página completa."""
        if not self.page_item:
            return
        
        view_rect = self.viewport().rect()
        page_rect = self.page_item.boundingRect()
        
        if page_rect.width() > 0 and page_rect.height() > 0:
            zoom_x = (view_rect.width() - 20) / page_rect.width()
            zoom_y = (view_rect.height() - 20) / page_rect.height()
            new_zoom = min(zoom_x, zoom_y) * self.zoom_level
            self.set_zoom(new_zoom)
    
    # Eventos del ratón
    
    def mousePressEvent(self, event):
        """Maneja el evento de presionar el ratón."""
        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            
            if self.tool_mode in ['select', 'highlight', 'delete', 'edit']:
                self.is_selecting = True
                self.selection_start = scene_pos
                
                # Crear rectángulo de selección con estilo según modo
                if self.selection_rect:
                    self.scene.removeItem(self.selection_rect)
                
                # Usar estilo azul para edición
                mode_for_style = 'select' if self.tool_mode == 'edit' else self.tool_mode
                self.selection_rect = SelectionRect(QRectF(), mode_for_style)
                self.scene.addItem(self.selection_rect)
                
                # Iniciar timer de preview para modo borrado
                if self.tool_mode == 'delete':
                    self.preview_timer.start(50)
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Maneja el evento de mover el ratón."""
        if self.is_selecting and self.selection_start:
            scene_pos = self.mapToScene(event.pos())
            
            # Actualizar rectángulo de selección
            rect = QRectF(self.selection_start, scene_pos).normalized()
            if self.selection_rect:
                self.selection_rect.setRect(rect)
            
            # Mostrar tooltip con texto seleccionado en modo borrado
            if self.tool_mode == 'delete' and rect.width() > 10 and rect.height() > 10:
                self.show_selection_info(rect, event.pos())
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Maneja el evento de soltar el ratón."""
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False
            self.preview_timer.stop()
            
            # Limpiar preview
            if self.delete_preview:
                self.scene.removeItem(self.delete_preview)
                self.delete_preview = None
            if self.floating_label:
                self.scene.removeItem(self.floating_label)
                self.floating_label = None
            
            if self.selection_rect:
                rect = self.selection_rect.rect()
                
                # Solo procesar si la selección tiene tamaño mínimo
                if rect.width() > 5 and rect.height() > 5:
                    self.current_selection = rect
                    self.process_selection(rect)
                else:
                    # Selección muy pequeña (click simple)
                    self.scene.removeItem(self.selection_rect)
                    self.selection_rect = None
                    
                    # En modo edición, un click simple permite añadir/editar texto
                    if self.tool_mode == 'edit' and self.selection_start:
                        self.handle_edit_click(self.selection_start)
                    
                    # En modo highlight, un click simple permite eliminar resaltados existentes
                    elif self.tool_mode == 'highlight' and self.selection_start:
                        self.handle_highlight_click(self.selection_start)
        
        super().mouseReleaseEvent(event)
    
    def show_selection_info(self, rect: QRectF, mouse_pos):
        """Muestra información sobre el texto seleccionado."""
        if not self.pdf_doc:
            return
        
        pdf_rect = self.view_to_pdf_rect(rect)
        blocks = self.pdf_doc.find_text_in_rect(self.current_page, pdf_rect)
        
        if blocks:
            text = ' '.join([b.text for b in blocks])
            if len(text) > 50:
                text = text[:50] + "..."
            
            # Mostrar tooltip
            global_pos = self.mapToGlobal(mouse_pos)
            QToolTip.showText(global_pos, f"🗑️ Eliminar: \"{text}\"", self)
    
    def update_delete_preview(self):
        """Actualiza la previsualización de borrado."""
        if not self.is_selecting or not self.selection_rect:
            return
        
        # El preview ya está siendo manejado por SelectionRect con estilo rojo
    
    def wheelEvent(self, event):
        """Maneja el evento de la rueda del ratón para zoom."""
        if event.modifiers() == Qt.ControlModifier:
            # Zoom con Ctrl + rueda
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)
    
    def process_selection(self, rect: QRectF):
        """Procesa la selección según el modo actual."""
        if not self.pdf_doc or not self.pdf_doc.is_open():
            self.clear_selection()
            return
        
        # Convertir coordenadas de vista a coordenadas de PDF
        pdf_rect = self.view_to_pdf_rect(rect)
        
        # Buscar texto en la selección
        blocks = self.pdf_doc.find_text_in_rect(self.current_page, pdf_rect)
        
        if self.tool_mode == 'select':
            if blocks:
                text = ' '.join([b.text for b in blocks])
                self.textSelected.emit(text, rect)
            self.clear_selection()
        
        elif self.tool_mode == 'edit':
            self.edit_selection(pdf_rect, blocks)
        
        elif self.tool_mode == 'highlight':
            self.highlight_selection(pdf_rect, blocks)
        
        elif self.tool_mode == 'delete':
            self.delete_selection(pdf_rect, blocks)
        
        if blocks:
            self.selectionChanged.emit(rect)
    
    def view_to_pdf_rect(self, view_rect: QRectF) -> fitz.Rect:
        """Convierte un rectángulo de coordenadas de vista a coordenadas de PDF."""
        # Ajustar por zoom
        return fitz.Rect(
            view_rect.x() / self.zoom_level,
            view_rect.y() / self.zoom_level,
            view_rect.right() / self.zoom_level,
            view_rect.bottom() / self.zoom_level
        )
    
    def pdf_to_view_rect(self, pdf_rect: fitz.Rect) -> QRectF:
        """Convierte un rectángulo de coordenadas de PDF a coordenadas de vista."""
        return QRectF(
            pdf_rect.x0 * self.zoom_level,
            pdf_rect.y0 * self.zoom_level,
            pdf_rect.width * self.zoom_level,
            pdf_rect.height * self.zoom_level
        )
    
    def edit_selection(self, pdf_rect: fitz.Rect, blocks=None):
        """Edita o añade texto en el área seleccionada."""
        if not self.pdf_doc:
            self.clear_selection()
            return
        
        if blocks and blocks[0].text.strip():
            # Hay texto existente - editar
            original_text = ' '.join([b.text for b in blocks])
            
            new_text, ok = QInputDialog.getText(
                self,
                'Editar texto',
                f'Texto original: "{original_text[:50]}{"..." if len(original_text) > 50 else ""}"\n\nNuevo texto:',
                text=original_text
            )
            
            if ok and new_text.strip():
                # Guardar snapshot UNA SOLA VEZ antes de ambas operaciones
                self.pdf_doc._save_snapshot()
                # Borrar el texto original SIN guardar snapshot adicional
                self.pdf_doc.erase_area(self.current_page, pdf_rect, color=(1, 1, 1), save_snapshot=False)
                block = blocks[0]
                # Añadir nuevo texto SIN guardar snapshot adicional
                if self.pdf_doc.add_text_to_page(
                    self.current_page,
                    pdf_rect,
                    new_text,
                    font_size=block.font_size or 12,
                    color=block.color or (0, 0, 0),
                    save_snapshot=False
                ):
                    self.render_page()
                    self.documentModified.emit()
        else:
            # No hay texto - añadir texto nuevo en el área seleccionada
            new_text, ok = QInputDialog.getText(
                self,
                'Añadir texto',
                'Escribe el texto a insertar en el área seleccionada:',
                text=""
            )
            
            if ok and new_text.strip():
                # Aquí sí se guarda snapshot (solo una operación)
                if self.pdf_doc.add_text_to_page(
                    self.current_page,
                    pdf_rect,
                    new_text,
                    font_size=12,
                    color=(0, 0, 0),
                    save_snapshot=True
                ):
                    self.render_page()
                    self.documentModified.emit()
        
        self.clear_selection()
    
    def highlight_selection(self, pdf_rect: fitz.Rect, blocks=None):
        """Resalta la selección actual o elimina resaltado existente."""
        if not self.pdf_doc:
            return
        
        # Verificar si hay resaltados existentes en el área seleccionada
        existing_highlights = self.pdf_doc.get_highlight_annotations(self.current_page)
        highlights_in_area = []
        
        for hl in existing_highlights:
            if pdf_rect.intersects(hl['rect']):
                highlights_in_area.append(hl)
        
        if highlights_in_area:
            # Hay resaltados existentes - preguntar qué hacer
            msg = QMessageBox(self)
            msg.setWindowTitle('Resaltado existente')
            msg.setIcon(QMessageBox.Question)
            msg.setText('<b>Se encontró un resaltado en esta área</b>')
            msg.setInformativeText('¿Qué deseas hacer?')
            
            btn_remove = msg.addButton('🗑️ Eliminar resaltado', QMessageBox.DestructiveRole)
            btn_add = msg.addButton('🖍️ Añadir nuevo resaltado', QMessageBox.AcceptRole)
            btn_cancel = msg.addButton('Cancelar', QMessageBox.RejectRole)
            
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #2d2d30;
                }
                QMessageBox QLabel {
                    color: #ffffff;
                    font-size: 13px;
                }
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-size: 12px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #1084d8;
                }
            """)
            
            msg.exec_()
            clicked = msg.clickedButton()
            
            if clicked == btn_remove:
                # Eliminar resaltados en el área
                if self.pdf_doc.remove_highlight_in_rect(self.current_page, pdf_rect):
                    self.render_page()
                    self.documentModified.emit()
                self.clear_selection()
                return
            elif clicked == btn_cancel:
                self.clear_selection()
                return
            # Si es btn_add, continuar para añadir nuevo resaltado
        
        # Añadir nuevo resaltado
        if self.pdf_doc.highlight_text(self.current_page, pdf_rect):
            # Re-renderizar para mostrar el resaltado
            self.render_page()
            # Limpiar selección visual
            self.clear_selection()
            # Notificar que el documento fue modificado
            self.documentModified.emit()
        else:
            self.clear_selection()

    def delete_selection(self, pdf_rect: fitz.Rect, blocks=None):
        """Elimina el contenido en la selección actual (texto o imagen)."""
        if not self.pdf_doc or not self.pdf_doc.is_open():
            self.clear_selection()
            return
        
        # Obtener texto si existe
        blocks = self.pdf_doc.find_text_in_rect(self.current_page, pdf_rect)
        text_to_delete = ' '.join([b.text for b in blocks]) if blocks else ""
        
        # Preparar mensaje para el diálogo
        if text_to_delete.strip():
            info_text = f'<span style="color: #ff5555; font-size: 14px;">Texto: "{text_to_delete[:100]}{"..." if len(text_to_delete) > 100 else ""}"</span>'
        else:
            info_text = '<span style="color: #888; font-size: 13px;">Área seleccionada (sin texto detectado)</span>'
        
        # Diálogo de confirmación unificado
        msg = QMessageBox(self)
        msg.setWindowTitle('Confirmar eliminación')
        msg.setIcon(QMessageBox.Warning)
        msg.setText('<b>¿Borrar esta área?</b>')
        msg.setInformativeText(info_text)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        msg.button(QMessageBox.Yes).setText('🗑️ Eliminar')
        msg.button(QMessageBox.No).setText('Cancelar')
        
        # Estilo del diálogo
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #2d2d30;
            }
            QMessageBox QLabel {
                color: #ffffff;
                font-size: 13px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton:pressed {
                background-color: #006cbd;
            }
        """)
        
        reply = msg.exec_()
        
        if reply == QMessageBox.Yes:
            # Usar erase_area que funciona para todo (texto e imágenes)
            if self.pdf_doc.erase_area(self.current_page, pdf_rect, color=(1, 1, 1)):
                # Re-renderizar página
                self.render_page()
                self.clear_selection()
                # Notificar que el documento fue modificado
                self.documentModified.emit()
            else:
                QMessageBox.warning(self, 'Error', 'No se pudo borrar el área.')
                self.clear_selection()
        else:
            self.clear_selection()
    
    def erase_image_area(self, pdf_rect):
        """
        Borra un área de una imagen en el PDF pintándola de blanco.
        Útil para PDFs escaneados o basados en imágenes.
        """
        if not self.pdf_doc or not self.pdf_doc.is_open():
            self.clear_selection()
            return
        
        # Diálogo de confirmación
        msg = QMessageBox(self)
        msg.setWindowTitle('Borrar área')
        msg.setIcon(QMessageBox.Question)
        msg.setText('<b>¿Borrar esta área?</b>')
        msg.setInformativeText(
            'Esta función pinta de blanco el área seleccionada.\n'
            'Útil para ocultar contenido en PDFs escaneados o imágenes.'
        )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        msg.button(QMessageBox.Yes).setText('🧹 Borrar área')
        msg.button(QMessageBox.No).setText('Cancelar')
        
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #2d2d30;
            }
            QMessageBox QLabel {
                color: #ffffff;
                font-size: 13px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
        """)
        
        reply = msg.exec_()
        
        if reply == QMessageBox.Yes:
            # Borrar el área con color blanco
            if self.pdf_doc.erase_area(self.current_page, pdf_rect, color=(1, 1, 1)):
                # Re-renderizar página
                self.render_page()
                self.clear_selection()
            else:
                QMessageBox.warning(self, 'Error', 'No se pudo borrar el área.')
        else:
            self.clear_selection()
    
    def show_delete_success(self):
        """Muestra una confirmación visual de eliminación exitosa."""
        # El efecto visual se logra con el re-render de la página
    
    def handle_edit_click(self, scene_pos: QPointF):
        """Maneja un click en modo edición - permite añadir texto en cualquier posición."""
        if not self.pdf_doc:
            return
        
        # Convertir a coordenadas PDF
        pdf_x = scene_pos.x() / self.zoom_level
        pdf_y = scene_pos.y() / self.zoom_level
        pdf_point = (pdf_x, pdf_y)
        
        # Buscar texto en esa posición
        block = self.pdf_doc.find_text_at_point(self.current_page, pdf_point)
        
        if block:
            # Hay texto existente - mostrar diálogo de edición
            new_text, ok = QInputDialog.getText(
                self,
                'Editar texto',
                f'Texto original: "{block.text}"\n\nNuevo texto:',
                text=block.text
            )
            
            if ok and new_text != block.text:
                if self.pdf_doc.edit_text(
                    self.current_page,
                    block.rect,
                    new_text,
                    block.font_name,
                    block.font_size,
                    block.color
                ):
                    self.render_page()
                    self.documentModified.emit()
        else:
            # No hay texto - crear texto nuevo en esta posición
            new_text, ok = QInputDialog.getText(
                self,
                'Añadir texto',
                'Escribe el texto a añadir:',
                text=""
            )
            
            if ok and new_text.strip():
                # Crear un rectángulo pequeño en la posición del click
                rect = fitz.Rect(pdf_x, pdf_y - 15, pdf_x + len(new_text) * 8, pdf_y + 5)
                if self.pdf_doc.add_text_to_page(
                    self.current_page,
                    rect,
                    new_text,
                    font_size=12,
                    color=(0, 0, 0)
                ):
                    self.render_page()
                    self.documentModified.emit()
    
    def handle_highlight_click(self, scene_pos: QPointF):
        """Maneja un click en modo highlight - permite eliminar resaltados existentes."""
        if not self.pdf_doc:
            return
        
        # Convertir a coordenadas PDF
        pdf_x = scene_pos.x() / self.zoom_level
        pdf_y = scene_pos.y() / self.zoom_level
        pdf_point = (pdf_x, pdf_y)
        
        # Buscar resaltado en esa posición
        existing_highlights = self.pdf_doc.get_highlight_annotations(self.current_page)
        
        highlight_at_point = None
        for hl in existing_highlights:
            if hl['rect'].contains(fitz.Point(pdf_x, pdf_y)):
                highlight_at_point = hl
                break
        
        if highlight_at_point:
            # Hay un resaltado - preguntar si quiere eliminarlo
            msg = QMessageBox(self)
            msg.setWindowTitle('Eliminar resaltado')
            msg.setIcon(QMessageBox.Question)
            msg.setText('<b>¿Eliminar este resaltado?</b>')
            msg.setInformativeText('El resaltado se eliminará permanentemente.')
            
            btn_remove = msg.addButton('🗑️ Eliminar', QMessageBox.DestructiveRole)
            btn_cancel = msg.addButton('Cancelar', QMessageBox.RejectRole)
            
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #2d2d30;
                }
                QMessageBox QLabel {
                    color: #ffffff;
                    font-size: 13px;
                }
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-size: 12px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #1084d8;
                }
            """)
            
            msg.exec_()
            
            if msg.clickedButton() == btn_remove:
                if self.pdf_doc.remove_highlight_at_point(self.current_page, pdf_point):
                    self.render_page()
                    self.documentModified.emit()

    def clear_selection(self):
        """Limpia la selección actual."""
        if self.selection_rect:
            self.scene.removeItem(self.selection_rect)
            self.selection_rect = None
        self.current_selection = None
    
    def show_context_menu(self, pos):
        """Muestra el menú contextual."""
        if not self.current_selection:
            return
        
        menu = QMenu(self)
        
        # Acciones del menú
        highlight_action = QAction('Resaltar', self)
        highlight_action.triggered.connect(lambda: self.context_highlight())
        menu.addAction(highlight_action)
        
        delete_action = QAction('Eliminar', self)
        delete_action.triggered.connect(lambda: self.context_delete())
        menu.addAction(delete_action)
        
        edit_action = QAction('Editar', self)
        edit_action.triggered.connect(lambda: self.context_edit())
        menu.addAction(edit_action)
        
        menu.addSeparator()
        
        copy_action = QAction('Copiar', self)
        copy_action.triggered.connect(lambda: self.context_copy())
        menu.addAction(copy_action)
        
        menu.exec_(self.mapToGlobal(pos))
    
    def context_highlight(self):
        """Resalta desde el menú contextual."""
        if self.current_selection:
            pdf_rect = self.view_to_pdf_rect(self.current_selection)
            self.highlight_selection(pdf_rect)
    
    def context_delete(self):
        """Elimina desde el menú contextual."""
        if self.current_selection:
            pdf_rect = self.view_to_pdf_rect(self.current_selection)
            self.delete_selection(pdf_rect)
    
    def context_edit(self):
        """Edita desde el menú contextual - funciona para texto e imágenes."""
        if self.current_selection and self.pdf_doc:
            pdf_rect = self.view_to_pdf_rect(self.current_selection)
            blocks = self.pdf_doc.find_text_in_rect(self.current_page, pdf_rect)
            
            if blocks and blocks[0].text.strip():
                # Hay texto existente - editar
                original_text = ' '.join([b.text for b in blocks])
                
                new_text, ok = QInputDialog.getText(
                    self,
                    'Editar texto',
                    f'Texto original: "{original_text}"\n\nNuevo texto:',
                    text=original_text
                )
                
                if ok and new_text.strip():
                    # Guardar snapshot UNA SOLA VEZ antes de ambas operaciones
                    self.pdf_doc._save_snapshot()
                    # Borrar el texto original SIN guardar snapshot adicional
                    self.pdf_doc.erase_area(self.current_page, pdf_rect, color=(1, 1, 1), save_snapshot=False)
                    block = blocks[0]
                    # Añadir nuevo texto SIN guardar snapshot adicional
                    if self.pdf_doc.add_text_to_page(
                        self.current_page,
                        pdf_rect,
                        new_text,
                        font_size=block.font_size or 12,
                        color=block.color or (0, 0, 0),
                        save_snapshot=False
                    ):
                        self.render_page()
                        self.documentModified.emit()
            else:
                # No hay texto - añadir texto nuevo (para PDFs de imagen)
                new_text, ok = QInputDialog.getText(
                    self,
                    'Añadir texto',
                    'Escribe el texto a añadir en esta área:',
                    text=""
                )
                
                if ok and new_text.strip():
                    # Aquí sí se guarda snapshot (solo una operación)
                    if self.pdf_doc.add_text_to_page(
                        self.current_page,
                        pdf_rect,
                        new_text,
                        font_size=12,
                        color=(0, 0, 0),
                        save_snapshot=True
                    ):
                        self.render_page()
                        self.documentModified.emit()
            
            self.clear_selection()
    
    def context_copy(self):
        """Copia texto desde el menú contextual."""
        if self.current_selection and self.pdf_doc:
            from PyQt5.QtWidgets import QApplication
            
            pdf_rect = self.view_to_pdf_rect(self.current_selection)
            blocks = self.pdf_doc.find_text_in_rect(self.current_page, pdf_rect)
            
            if blocks:
                text = ' '.join([b.text for b in blocks])
                QApplication.clipboard().setText(text)

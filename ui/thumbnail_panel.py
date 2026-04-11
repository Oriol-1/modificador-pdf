"""
Panel de miniaturas de páginas del PDF.
Soporta drag & drop para reordenar páginas y menú contextual.
"""

from PyQt5.QtWidgets import (
    QListWidget, QListWidgetItem, QVBoxLayout, QWidget, QLabel,
    QMenu, QAction, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QImage, QIcon


class ThumbnailPanel(QWidget):
    """Panel con miniaturas de todas las páginas del PDF."""
    
    pageSelected = pyqtSignal(int)   # Señal cuando se selecciona una página
    pagesReordered = pyqtSignal(list)  # Señal con nuevo orden [int] tras drag & drop
    pageDeleteRequested = pyqtSignal(int)  # Solicitar eliminación de página
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.pdf_doc = None
        self.thumbnail_size = 150
        self._dragging = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configura la interfaz del panel."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Título
        title = QLabel("Páginas")
        title.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(title)
        
        # Lista de miniaturas con drag & drop
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.ListMode)
        self.list_widget.setIconSize(QSize(self.thumbnail_size, self.thumbnail_size))
        self.list_widget.setSpacing(5)
        self.list_widget.setWordWrap(True)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        
        # Drag & drop
        self.list_widget.setDragDropMode(QListWidget.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        self.list_widget.setDragEnabled(True)
        self.list_widget.setAcceptDrops(True)
        self.list_widget.model().rowsMoved.connect(self._on_rows_moved)
        
        # Menú contextual
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        
        layout.addWidget(self.list_widget)
    
    def set_pdf_document(self, pdf_doc):
        """Establece el documento PDF y genera las miniaturas."""
        self.pdf_doc = pdf_doc
        self.generate_thumbnails()
    
    def generate_thumbnails(self):
        """Genera miniaturas para todas las páginas."""
        self.list_widget.clear()
        
        if not self.pdf_doc or not self.pdf_doc.is_open():
            return
        
        page_count = self.pdf_doc.page_count()
        
        for page_num in range(page_count):
            # Renderizar miniatura
            pixmap = self.pdf_doc.render_page(page_num, zoom=0.2)
            
            if pixmap:
                # Convertir a QPixmap
                img = QImage(
                    pixmap.samples,
                    pixmap.width,
                    pixmap.height,
                    pixmap.stride,
                    QImage.Format_RGB888
                )
                qpixmap = QPixmap.fromImage(img)
                
                # Escalar si es necesario
                if qpixmap.width() > self.thumbnail_size or qpixmap.height() > self.thumbnail_size:
                    qpixmap = qpixmap.scaled(
                        self.thumbnail_size,
                        self.thumbnail_size,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                
                # Crear item
                item = QListWidgetItem(QIcon(qpixmap), f"Página {page_num + 1}")
                item.setData(Qt.UserRole, page_num)
                item.setSizeHint(QSize(self.thumbnail_size + 20, self.thumbnail_size + 40))
                
                self.list_widget.addItem(item)
    
    def on_item_clicked(self, item):
        """Maneja el click en una miniatura."""
        page_num = item.data(Qt.UserRole)
        self.pageSelected.emit(page_num)
    
    def select_page(self, page_num: int):
        """Selecciona una página en la lista."""
        if page_num < self.list_widget.count():
            self.list_widget.setCurrentRow(page_num)
    
    def refresh_thumbnail(self, page_num: int):
        """Refresca la miniatura de una página específica."""
        if not self.pdf_doc or page_num >= self.list_widget.count():
            return
        
        # Renderizar nueva miniatura
        pixmap = self.pdf_doc.render_page(page_num, zoom=0.2)
        
        if pixmap:
            img = QImage(
                pixmap.samples,
                pixmap.width,
                pixmap.height,
                pixmap.stride,
                QImage.Format_RGB888
            )
            qpixmap = QPixmap.fromImage(img)
            
            if qpixmap.width() > self.thumbnail_size or qpixmap.height() > self.thumbnail_size:
                qpixmap = qpixmap.scaled(
                    self.thumbnail_size,
                    self.thumbnail_size,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            
            item = self.list_widget.item(page_num)
            if item:
                item.setIcon(QIcon(qpixmap))

    def _on_rows_moved(self, parent, start, end, destination, row):
        """Detecta cuando el usuario reordena las miniaturas con drag & drop."""
        new_order = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            original_page = item.data(Qt.UserRole)
            new_order.append(original_page)
        
        # Si el orden no cambió, ignorar
        if new_order == list(range(len(new_order))):
            return
        
        # Calcular posición destino para el mensaje (row puede estar fuera de rango)
        dest_pos = min(row, len(new_order) - 1)
        new_pos = dest_pos + 1  # 1-based para el usuario
        
        reply = QMessageBox.question(
            self, "Mover página",
            f"¿Estás seguro de que quieres mover la página a la posición {new_pos}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Confirmar: actualizar labels y UserRole
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                item.setText(f"Página {i + 1}")
                item.setData(Qt.UserRole, i)
            
            self.pagesReordered.emit(new_order)
        else:
            # Cancelar: restaurar el orden original
            self._restore_order()
    
    def _show_context_menu(self, pos):
        """Muestra menú contextual sobre una miniatura."""
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        
        page_num = item.data(Qt.UserRole)
        menu = QMenu(self)
        
        delete_action = QAction(f"Eliminar página {page_num + 1}", self)
        delete_action.triggered.connect(lambda: self.pageDeleteRequested.emit(page_num))
        
        # No permitir eliminar si solo queda una página
        if self.list_widget.count() <= 1:
            delete_action.setEnabled(False)
        
        menu.addAction(delete_action)
        menu.exec_(self.list_widget.mapToGlobal(pos))

    def _restore_order(self):
        """Restaura las miniaturas al orden original (regenera desde el documento)."""
        self.generate_thumbnails()

    def clear(self):
        """Limpia todas las miniaturas."""
        self.list_widget.clear()
        self.pdf_doc = None
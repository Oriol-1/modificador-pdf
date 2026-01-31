"""
Panel de miniaturas de páginas del PDF.
"""

from PyQt5.QtWidgets import (
    QListWidget, QListWidgetItem, QVBoxLayout, QWidget, QLabel
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QImage, QIcon


class ThumbnailPanel(QWidget):
    """Panel con miniaturas de todas las páginas del PDF."""
    
    pageSelected = pyqtSignal(int)  # Señal cuando se selecciona una página
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.pdf_doc = None
        self.thumbnail_size = 150
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configura la interfaz del panel."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Título
        title = QLabel("Páginas")
        title.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(title)
        
        # Lista de miniaturas
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setIconSize(QSize(self.thumbnail_size, self.thumbnail_size))
        self.list_widget.setSpacing(10)
        self.list_widget.setMovement(QListWidget.Static)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setWordWrap(True)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        
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
    def clear(self):
        """Limpia todas las miniaturas."""
        self.list_widget.clear()
        self.pdf_doc = None
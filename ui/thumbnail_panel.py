"""
Panel de miniaturas de páginas del PDF.
Soporta drag & drop para reordenar páginas y menú contextual.
"""

from PyQt5.QtWidgets import (
    QListWidget, QListWidgetItem, QVBoxLayout, QWidget, QLabel,
    QMenu, QAction, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QPixmap, QImage, QIcon


class ThumbnailPanel(QWidget):
    """Panel con miniaturas de todas las páginas del PDF."""
    
    pageSelected = pyqtSignal(int)   # Señal cuando se selecciona una página
    pagesReordered = pyqtSignal(list)  # Señal con nuevo orden [int] tras drag & drop
    pageDeleteRequested = pyqtSignal(int)  # Solicitar eliminación de página
    pageRotateRequested = pyqtSignal(int, int)  # Solicitar rotación (page_num, angle)
    
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
        """Genera miniaturas para todas las páginas SIN bloquear la UI.

        OPTIMIZACION: anteriormente este metodo renderizaba pagina a
        pagina sincronicamente, congelando la interfaz durante segundos
        en docs grandes (50+ paginas). Ahora:

        1. Crea placeholders inmediatos para todas las paginas (no
           bloquea, el usuario ve la lista al instante).
        2. Renderiza las miniaturas reales en lotes con QApplication.
           processEvents() entre paginas, asi la UI sigue respondiendo
           y se puede arrastrar/cerrar la ventana sin parecer colgada.
        3. Si se cambia de doc durante el render, se cancela el lote
           anterior automaticamente (via _thumbnail_generation_token).
        """
        self.list_widget.clear()

        if not self.pdf_doc or not self.pdf_doc.is_open():
            return

        page_count = self.pdf_doc.page_count()

        # 1) Insertar placeholders inmediatos. La UI muestra la lista al
        # instante; el usuario sabe que el panel esta poblado mientras se
        # generan los pixmaps reales en segundo plano (cooperativo).
        placeholder_size = QSize(self.thumbnail_size, self.thumbnail_size)
        empty_pixmap = QPixmap(placeholder_size)
        empty_pixmap.fill(Qt.transparent)
        empty_icon = QIcon(empty_pixmap)
        for page_num in range(page_count):
            item = QListWidgetItem(empty_icon, f"Página {page_num + 1}")
            item.setData(Qt.UserRole, page_num)
            item.setSizeHint(QSize(self.thumbnail_size + 20, self.thumbnail_size + 40))
            self.list_widget.addItem(item)

        # Token para invalidar este lote si el doc cambia antes de acabar
        self._thumbnail_generation_token = getattr(self, '_thumbnail_generation_token', 0) + 1
        my_token = self._thumbnail_generation_token

        # 2) DEFERRED START: programamos el PRIMER lote tambien con
        # singleShot para devolver control inmediatamente al event loop.
        # Asi set_pdf_document termina al instante (solo placeholders,
        # ~5-30ms) y la UI ya esta lista mientras el primer batch real
        # se renderiza ~10ms despues. Antes el primer lote sincrono
        # bloqueaba 600-900ms en docs grandes.
        QTimer.singleShot(
            0,
            lambda: self._render_thumbnails_cooperatively(my_token, 0, page_count),
        )

    def _render_thumbnails_cooperatively(self, token: int, start: int, total: int):
        """Renderiza miniaturas de UNA en UNA sin bloquear la UI.

        Cada llamada renderiza UNA pagina (~50-200ms) y reprograma la
        siguiente con singleShot. Asi cada lote es lo mas corto posible,
        permitiendo a la UI procesar mouse-move, edicion, etc. entre
        renders. Antes con batch=3 se bloqueaba 150-600ms por lote, lo
        que causaba "tirones" durante el drag/edicion.

        Si el usuario esta interactuando (drag de texto/imagen), la
        generacion se PAUSA y se reintenta 100ms despues hasta que la
        interaccion termine. La UI nunca pelea con el background.
        """
        if token != getattr(self, '_thumbnail_generation_token', None):
            return
        if not self.pdf_doc or not self.pdf_doc.is_open():
            return

        # Si esta marcado como pausado (por interaccion del usuario,
        # ej. drag o edicion), reintentar cuando se despause.
        if getattr(self, '_paused', False):
            QTimer.singleShot(
                200,
                lambda: self._render_thumbnails_cooperatively(token, start, total),
            )
            return

        if start >= total:
            return

        try:
            pixmap = self.pdf_doc.render_page(start, zoom=0.2)
        except Exception:
            pixmap = None
        if pixmap:
            img = QImage(
                pixmap.samples, pixmap.width, pixmap.height,
                pixmap.stride, QImage.Format_RGB888
            )
            qpixmap = QPixmap.fromImage(img)
            if qpixmap.width() > self.thumbnail_size or qpixmap.height() > self.thumbnail_size:
                qpixmap = qpixmap.scaled(
                    self.thumbnail_size, self.thumbnail_size,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            if start < self.list_widget.count():
                item = self.list_widget.item(start)
                if item is not None:
                    item.setIcon(QIcon(qpixmap))

        next_start = start + 1
        if next_start < total:
            # Pequena pausa entre renders (30ms) para que el event
            # loop tenga tiempo de procesar mouse-move/edit/save sin
            # competir con el siguiente render. Mejor que singleShot(0)
            # cuando el usuario esta interactuando.
            QTimer.singleShot(
                30,
                lambda: self._render_thumbnails_cooperatively(token, next_start, total),
            )

    def pause_thumbnails(self):
        """Pausa la generacion en curso. Llamar al iniciar drag/edit."""
        self._paused = True

    def resume_thumbnails(self):
        """Reanuda la generacion en curso."""
        self._paused = False
    
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
        
        # Submenú de rotación
        rotate_menu = QMenu("🔄 Rotar página", self)
        rotate_90r = rotate_menu.addAction("↻ Rotar 90° derecha")
        rotate_90r.triggered.connect(lambda: self.pageRotateRequested.emit(page_num, 90))
        rotate_90l = rotate_menu.addAction("↺ Rotar 90° izquierda")
        rotate_90l.triggered.connect(lambda: self.pageRotateRequested.emit(page_num, 270))
        rotate_180 = rotate_menu.addAction("🔃 Rotar 180°")
        rotate_180.triggered.connect(lambda: self.pageRotateRequested.emit(page_num, 180))
        menu.addMenu(rotate_menu)
        
        menu.exec_(self.list_widget.mapToGlobal(pos))

    def _restore_order(self):
        """Restaura las miniaturas al orden original (regenera desde el documento)."""
        self.generate_thumbnails()

    def clear(self):
        """Limpia todas las miniaturas."""
        self.list_widget.clear()
        self.pdf_doc = None
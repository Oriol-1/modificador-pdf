"""
Visor de páginas PDF con soporte para zoom, scroll y selección de texto.
"""

from PyQt5.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsRectItem, QMenu, QAction, QInputDialog, QMessageBox,
    QToolTip, QDialog
)
from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QPointF, QTimer, QRect
from PyQt5.QtGui import (
    QPixmap, QImage, QPen, QBrush, QColor, QPainter, QCursor,
    QFont, QFontMetrics
)
import fitz

# Importar elementos gráficos y utilidades desde módulos separados
from .graphics_items import (
    SelectionRect, DeletePreviewRect, FloatingLabel, HighlightRect,
    TextEditDialog, EditableTextItem
)
from .coordinate_utils import CoordinateConverter

# Importar diálogo mejorado de edición de texto (Phase 2)
try:
    from .text_editor_dialog import EnhancedTextEditDialog, show_text_edit_dialog
    HAS_ENHANCED_DIALOG = True
except ImportError:
    HAS_ENHANCED_DIALOG = False

# Importar editor de texto enriquecido con soporte para runs (Phase 2.5)
try:
    from .rich_text_editor import (
        RichTextEditDialog, TextRun, TextBlock, show_rich_text_editor
    )
    HAS_RICH_TEXT_EDITOR = True
except ImportError:
    HAS_RICH_TEXT_EDITOR = False

# Importar editor tipo Word (Phase 3)
try:
    from .word_like_editor import (
        WordLikeEditorDialog, TextRunInfo, DocumentStructure, show_word_like_editor
    )
    HAS_WORD_LIKE_EDITOR = True
except ImportError:
    HAS_WORD_LIKE_EDITOR = False

# Importar FontManager para detección de fuentes (Phase 2)
try:
    from core.font_manager import get_font_manager, FontDescriptor
    HAS_FONT_MANAGER = True
except ImportError:
    HAS_FONT_MANAGER = False

# Importar TextHitTester para hit-testing preciso (Phase 3C)
try:
    from core.text_engine import (
        TextHitTester, HitTestResult, HitType,
        TextSpanMetrics, TextLine
    )
    HAS_TEXT_HIT_TESTER = True
except ImportError:
    HAS_TEXT_HIT_TESTER = False

# Importar TextPropertiesTooltip para tooltip de propiedades (Phase 3C)
try:
    from .text_properties_tooltip import (
        TextPropertiesTooltip, TooltipConfig, TooltipStyle,
        create_text_properties_tooltip
    )
    HAS_TEXT_TOOLTIP = True
except ImportError:
    HAS_TEXT_TOOLTIP = False

# Importar TextSelectionOverlay para selección con métricas (Phase 3C-04)
try:
    from .text_selection_overlay import (
        TextSelectionOverlay, SelectionMode, SelectionConfig,
        MetricIndicator, create_selection_overlay
    )
    HAS_SELECTION_OVERLAY = True
except ImportError:
    HAS_SELECTION_OVERLAY = False

# Importar TextEditIntegrator para edición mejorada (Phase 3E)
try:
    from core.text_edit_integrator import (
        TextEditIntegrator, EditPreparation, EditResult,
        get_text_integrator, create_text_integrator
    )
    HAS_TEXT_INTEGRATOR = True
except ImportError:
    HAS_TEXT_INTEGRATOR = False


class PDFPageView(QGraphicsView):
    """Vista de una página de PDF con capacidades de selección y edición."""
    
    # Señales
    selectionChanged = pyqtSignal(QRectF)  # Emitida cuando cambia la selección
    textSelected = pyqtSignal(str, QRectF)  # Texto seleccionado y su rectángulo
    pageClicked = pyqtSignal(QPointF)  # Click en la página
    zoomChanged = pyqtSignal(float)  # Cambio de zoom
    documentModified = pyqtSignal()  # Emitida cuando el documento se modifica
    
    # Señales de hit-testing (Phase 3C)
    spanHovered = pyqtSignal(object)  # TextSpanMetrics cuando el cursor está sobre un span
    spanClicked = pyqtSignal(object)  # TextSpanMetrics cuando se hace clic en un span
    lineHovered = pyqtSignal(object)  # TextLine cuando el cursor está sobre una línea
    hitTestResult = pyqtSignal(object)  # HitTestResult completo
    
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
        
        # Tamaños para conversión de coordenadas
        self.pdf_page_width = 612  # Tamaño por defecto (Letter)
        self.pdf_page_height = 792
        self.pixmap_width = 612
        self.pixmap_height = 792
        
        # Información de transformación de página
        self.page_rotation = 0
        self.page_mediabox = None
        self.page_cropbox = None
        self.page_transform_matrix = None
        self.page_derotation_matrix = None
        
        # Convertidor de coordenadas
        self.coord_converter = CoordinateConverter(self.zoom_level, self.page_rotation)
        
        # Items gráficos
        self.page_item = None
        self.selection_rect = None
        self.delete_preview = None
        self.floating_label = None
        self.highlight_items = []
        
        # Textos editables añadidos por el usuario (por página)
        # Estructura: {page_num: [dict con datos del texto, ...]}
        # Cada dict tiene: text, pdf_rect, font_size, color, view_rect
        self.editable_texts_data = {}
        self.editable_text_items = []  # Items gráficos actuales (se recrean al renderizar)
        self.selected_text_item = None  # Texto actualmente seleccionado
        self.dragging_text = False  # Si estamos arrastrando un texto
        self.drag_start_pos = None  # Posición inicial del arrastre
        self.drag_original_rect = None  # Rectángulo original antes de mover
        self.text_was_moved = False  # Si el texto realmente se movió
        
        # Modo de herramienta
        self.tool_mode = 'select'  # 'select', 'highlight', 'delete', 'edit'
        
        # Estado de selección
        self.is_selecting = False
        self.selection_start = None
        self.current_selection = None
        
        # Timer para actualizar preview
        self.preview_timer = QTimer()
        self.preview_timer.timeout.connect(self.update_delete_preview)
        
        # Hit-tester para texto (Phase 3C)
        self._hit_tester = None
        self._last_hit_result = None
        self._hover_span = None  # Span actualmente bajo el cursor
        self._init_hit_tester()
        
        # Tooltip de propiedades tipográficas (Phase 3C-03)
        self._properties_tooltip = None
        self._init_properties_tooltip()
        
        # Overlay de selección con métricas (Phase 3C-04)
        self._selection_overlay = None
        self._init_selection_overlay()
        
        # Integrador de edición de texto (Phase 3E)
        self._text_integrator = None
        self._init_text_integrator()
        
        # Habilitar tracking del mouse para hit-testing en hover
        self.setMouseTracking(True)
        
        # Configurar menú contextual
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    # ========== Hit-Testing Methods (Phase 3C) ==========
    
    def _init_hit_tester(self) -> None:
        """Inicializar el hit-tester si está disponible."""
        if not HAS_TEXT_HIT_TESTER:
            return
        
        font_manager = None
        if HAS_FONT_MANAGER:
            font_manager = get_font_manager()
        
        self._hit_tester = TextHitTester(font_manager=font_manager)
    
    def _init_properties_tooltip(self) -> None:
        """Inicializar el tooltip de propiedades tipográficas."""
        if not HAS_TEXT_TOOLTIP:
            return
        
        # Crear tooltip con configuración estándar
        self._properties_tooltip = create_text_properties_tooltip(
            parent=self,
            style=TooltipStyle.STANDARD,
            dark_theme=True
        )
        
        # Conectar señal de hover
        self.spanHovered.connect(self._properties_tooltip.on_span_hovered)
    
    def set_tooltip_style(self, style: 'TooltipStyle') -> None:
        """
        Cambiar el estilo del tooltip de propiedades.
        
        Args:
            style: TooltipStyle (COMPACT, STANDARD, DETAILED)
        """
        if self._properties_tooltip and HAS_TEXT_TOOLTIP:
            self._properties_tooltip.set_style(style)
    
    def set_tooltip_enabled(self, enabled: bool) -> None:
        """
        Habilitar/deshabilitar el tooltip de propiedades.
        
        Args:
            enabled: Si el tooltip está habilitado
        """
        if self._properties_tooltip:
            self._properties_tooltip.enabled = enabled

    def _init_selection_overlay(self) -> None:
        """Inicializar el overlay de selección con métricas."""
        if not HAS_SELECTION_OVERLAY:
            return
        
        # Crear overlay con configuración por defecto
        self._selection_overlay = create_selection_overlay(
            scene=self.scene,
            mode=SelectionMode.SPAN,
            multi_select=True,
            preset='standard'
        )
        
        # Conectar señales
        self.spanClicked.connect(self._on_span_clicked_for_selection)
        self.spanHovered.connect(self._on_span_hovered_for_selection)
    
    def _init_text_integrator(self) -> None:
        """Inicializar el integrador de edición de texto."""
        if not HAS_TEXT_INTEGRATOR:
            return
        
        self._text_integrator = get_text_integrator()
    
    def _update_text_integrator_document(self) -> None:
        """Actualizar el documento en el integrador."""
        if self._text_integrator and self.pdf_doc:
            self._text_integrator.set_document(self.pdf_doc)
    
    def _check_text_fits(self, text: str, available_width: float, 
                         font_name: str = "Helvetica", font_size: float = 12.0) -> tuple:
        """
        Verifica si un texto cabe en el ancho disponible.
        
        Args:
            text: Texto a verificar
            available_width: Ancho disponible en puntos
            font_name: Nombre de la fuente
            font_size: Tamaño de fuente
            
        Returns:
            Tupla (cabe: bool, ratio: float, warning: str o None)
        """
        if not self._text_integrator or not HAS_TEXT_INTEGRATOR:
            return (True, 1.0, None)
        
        fits, ratio = self._text_integrator.check_text_fits(
            text=text,
            available_width=available_width,
            font_name=font_name,
            font_size=font_size,
        )
        
        warning = None
        if not fits:
            overflow_percent = int((ratio - 1) * 100)
            warning = f"El texto es {overflow_percent}% más largo que el espacio disponible"
        elif ratio > 0.9:
            warning = "El texto cabe pero está muy ajustado"
        
        return (fits, ratio, warning)
    
    def _prepare_text_edit(
        self, 
        original_text: str, 
        new_text: str,
        bbox: tuple,
        font_name: str = "Helvetica",
        font_size: float = 12.0,
    ) -> 'EditPreparation':
        """
        Prepara una edición de texto con análisis completo.
        
        Args:
            original_text: Texto original
            new_text: Nuevo texto
            bbox: Bounding box (x0, y0, x1, y1)
            font_name: Nombre de la fuente
            font_size: Tamaño de fuente
            
        Returns:
            EditPreparation con el análisis o None si no está disponible
        """
        if not self._text_integrator or not HAS_TEXT_INTEGRATOR:
            return None
        
        return self._text_integrator.prepare_edit(
            page_num=self.current_page,
            original_text=original_text,
            new_text=new_text,
            bbox=bbox,
            font_name=font_name,
            font_size=font_size,
        )
    
    def _validate_before_save(self) -> tuple:
        """
        Valida el documento antes de guardar.
        
        Returns:
            Tupla (is_valid: bool, warnings: list, errors: list)
        """
        if not self._text_integrator or not HAS_TEXT_INTEGRATOR:
            return (True, [], [])
        
        report = self._text_integrator.validate_before_save()
        return (report.is_valid, report.warnings, report.errors)
    
    def _on_span_clicked_for_selection(self, span) -> None:
        """Manejar clic en span para selección."""
        if not self._selection_overlay or not span:
            return
        
        # Convertir span a dict si es necesario
        if hasattr(span, 'to_dict'):
            span_data = span.to_dict()
        else:
            span_data = span if isinstance(span, dict) else {'span_id': str(id(span))}
        
        # Determinar si es multi-selección (Ctrl presionado)
        from PyQt5.QtWidgets import QApplication
        modifiers = QApplication.keyboardModifiers()
        add_to_selection = modifiers == Qt.ControlModifier
        
        self._selection_overlay.select_span(span_data, add_to_selection=add_to_selection)
    
    def _on_span_hovered_for_selection(self, span) -> None:
        """Manejar hover sobre span para visualización."""
        if not self._selection_overlay:
            return
        
        if span is None:
            self._selection_overlay.clear_hover()
            return
        
        # Convertir span a dict si es necesario
        if hasattr(span, 'to_dict'):
            span_data = span.to_dict()
        else:
            span_data = span if isinstance(span, dict) else {'span_id': str(id(span))}
        
        self._selection_overlay.set_hover_span(span_data)
    
    def set_selection_mode(self, mode: 'SelectionMode') -> None:
        """
        Cambiar el modo de selección.
        
        Args:
            mode: SelectionMode (SPAN, LINE, PARAGRAPH, CHARACTER)
        """
        if self._selection_overlay and HAS_SELECTION_OVERLAY:
            self._selection_overlay.selection_mode = mode
    
    def set_selection_overlay_enabled(self, enabled: bool) -> None:
        """
        Habilitar/deshabilitar el overlay de selección.
        
        Args:
            enabled: Si el overlay está habilitado
        """
        if self._selection_overlay:
            self._selection_overlay.enabled = enabled
    
    def set_metrics_preset(self, preset: str) -> None:
        """
        Aplicar un preset de métricas visuales.
        
        Args:
            preset: 'minimal', 'standard', 'detailed', 'all'
        """
        if self._selection_overlay:
            self._selection_overlay.set_metrics_preset(preset)
    
    def set_metric_visibility(self, metric: 'MetricIndicator', visible: bool) -> None:
        """
        Establecer visibilidad de un indicador de métrica.
        
        Args:
            metric: MetricIndicator (BBOX, BASELINE, ASCENDER, etc.)
            visible: Si debe ser visible
        """
        if self._selection_overlay and HAS_SELECTION_OVERLAY:
            self._selection_overlay.set_metric_visibility(metric, visible)
    
    def clear_selection(self) -> None:
        """Limpiar toda la selección de texto."""
        if self._selection_overlay:
            self._selection_overlay.clear_all()
    
    def get_selected_spans(self) -> list:
        """Obtener lista de spans seleccionados."""
        if not self._selection_overlay:
            return []
        return self._selection_overlay.get_selected_spans_data()
    
    def has_text_selection(self) -> bool:
        """Verificar si hay texto seleccionado."""
        if not self._selection_overlay:
            return False
        return self._selection_overlay.has_selection

    def _update_hit_tester_document(self) -> None:
        """Actualizar el documento en el hit-tester."""
        if not self._hit_tester:
            return
        
        if self.pdf_doc and hasattr(self.pdf_doc, '_doc'):
            # Acceder al documento fitz subyacente
            self._hit_tester.set_document(self.pdf_doc._doc)
        else:
            self._hit_tester.set_document(None)
    
    def invalidate_hit_test_cache(self, page_num: int = None) -> None:
        """
        Invalidar la caché de hit-testing.
        
        Args:
            page_num: Página específica o None para todas
        """
        if not self._hit_tester:
            return
        
        if page_num is not None:
            self._hit_tester.invalidate_page(page_num)
        else:
            self._hit_tester.clear_cache()
    
    def hit_test_at_point(self, view_x: float, view_y: float) -> 'HitTestResult':
        """
        Realizar hit-testing en coordenadas de vista.
        
        Args:
            view_x: Coordenada X en espacio de vista
            view_y: Coordenada Y en espacio de vista
            
        Returns:
            HitTestResult con el resultado
        """
        if not self._hit_tester or not HAS_TEXT_HIT_TESTER:
            # Retornar resultado vacío
            return HitTestResult() if HAS_TEXT_HIT_TESTER else None
        
        # Convertir de coordenadas de vista a PDF
        pdf_point = self.view_to_pdf_point(QPointF(view_x, view_y))
        
        # Realizar hit-test
        result = self._hit_tester.hit_test(
            self.current_page,
            pdf_point.x(),
            pdf_point.y(),
            tolerance=5.0 / self.zoom_level  # Ajustar por zoom
        )
        
        return result
    
    def hit_test_at_scene_pos(self, scene_pos: QPointF) -> 'HitTestResult':
        """
        Realizar hit-testing en coordenadas de escena.
        
        Args:
            scene_pos: Posición en la escena
            
        Returns:
            HitTestResult con el resultado
        """
        return self.hit_test_at_point(scene_pos.x(), scene_pos.y())
    
    def get_span_at_point(self, view_x: float, view_y: float) -> 'TextSpanMetrics':
        """
        Obtener el span en una coordenada de vista.
        
        Args:
            view_x, view_y: Coordenadas en espacio de vista
            
        Returns:
            TextSpanMetrics o None
        """
        result = self.hit_test_at_point(view_x, view_y)
        return result.span if result and result.found else None
    
    def get_line_at_point(self, view_x: float, view_y: float) -> 'TextLine':
        """
        Obtener la línea en una coordenada de vista.
        
        Args:
            view_x, view_y: Coordenadas en espacio de vista
            
        Returns:
            TextLine o None
        """
        result = self.hit_test_at_point(view_x, view_y)
        return result.line if result and result.found else None
    
    def get_all_spans(self, page_num: int = None) -> list:
        """
        Obtener todos los spans de una página.
        
        Args:
            page_num: Número de página o None para página actual
            
        Returns:
            Lista de TextSpanMetrics
        """
        if not self._hit_tester:
            return []
        
        if page_num is None:
            page_num = self.current_page
        
        return self._hit_tester.get_all_spans(page_num)
    
    def get_all_lines(self, page_num: int = None) -> list:
        """
        Obtener todas las líneas de una página.
        
        Args:
            page_num: Número de página o None para página actual
            
        Returns:
            Lista de TextLine
        """
        if not self._hit_tester:
            return []
        
        if page_num is None:
            page_num = self.current_page
        
        return self._hit_tester.get_all_lines(page_num)
    
    def _handle_hover_hit_test(self, scene_pos: QPointF) -> None:
        """
        Manejar hit-testing durante hover del mouse.
        
        Args:
            scene_pos: Posición actual del cursor en la escena
        """
        if not self._hit_tester or not HAS_TEXT_HIT_TESTER:
            return
        
        # Solo hacer hit-testing si estamos sobre la página
        if not self.page_item or not self.page_item.contains(scene_pos):
            if self._hover_span is not None:
                self._hover_span = None
                self.spanHovered.emit(None)
            return
        
        result = self.hit_test_at_scene_pos(scene_pos)
        self._last_hit_result = result
        
        # Emitir señal de resultado completo
        self.hitTestResult.emit(result)
        
        # Manejar cambio de span
        new_span = result.span if result and result.found else None
        
        if new_span != self._hover_span:
            self._hover_span = new_span
            self.spanHovered.emit(new_span)
            
            # Cambiar cursor si hay span
            if new_span and self.tool_mode in ['select', 'edit']:
                self.setCursor(Qt.IBeamCursor)
            elif self.tool_mode == 'edit':
                self.setCursor(Qt.PointingHandCursor)
        
        # Emitir señal de línea
        if result and result.line:
            self.lineHovered.emit(result.line)
    
    def _handle_click_hit_test(self, scene_pos: QPointF) -> bool:
        """
        Manejar hit-testing durante clic del mouse.
        
        Args:
            scene_pos: Posición del clic en la escena
            
        Returns:
            True si se encontró un span y se emitió la señal
        """
        if not self._hit_tester or not HAS_TEXT_HIT_TESTER:
            return False
        
        result = self.hit_test_at_scene_pos(scene_pos)
        
        if result and result.span:
            self.spanClicked.emit(result.span)
            return True
        
        return False
    
    # ========== End Hit-Testing Methods ==========
    
    def set_pdf_document(self, pdf_doc):
        """Establece el documento PDF a mostrar."""
        # Limpiar estado anterior completamente
        self.clear_all_state()
        
        self.pdf_doc = pdf_doc
        if pdf_doc and pdf_doc.is_open():
            # Conectar callbacks para el sistema de undo con overlays
            pdf_doc.set_overlay_callbacks(
                self.get_overlay_state,
                self.restore_overlay_state
            )
            # Actualizar hit-tester con el nuevo documento
            self._update_hit_tester_document()
            # Actualizar integrador de texto con el nuevo documento
            self._update_text_integrator_document()
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
        
        # Limpiar textos editables
        self.clear_editable_texts_data()
        
        # Reiniciar página
        self.current_page = 0
    
    def clear_editable_texts_data(self):
        """Limpia los datos de textos editables (usado al hacer undo/redo)."""
        self.editable_texts_data = {}
        self.editable_text_items = []
        self.selected_text_item = None
        self.dragging_text = False
        self.drag_start_pos = None
        self.drag_original_rect = None
        self.text_was_moved = False
    
    def get_overlay_state(self) -> dict:
        """Obtiene una copia del estado actual de overlays para el sistema de undo."""
        import copy
        return copy.deepcopy(self.editable_texts_data)
    
    def restore_overlay_state(self, state: dict):
        """Restaura el estado de overlays desde un snapshot del sistema de undo."""
        import copy
        self.editable_texts_data = copy.deepcopy(state) if state else {}
        # Nota: los items visuales se recrearán al renderizar la página
    
    def load_page(self, page_num: int):
        """Carga y muestra una página específica."""
        if not self.pdf_doc or not self.pdf_doc.is_open():
            return
        
        if page_num < 0 or page_num >= self.pdf_doc.page_count():
            return
        
        # Limpiar selección al cambiar de página
        if self._selection_overlay:
            self._selection_overlay.clear_all()
        
        self.current_page = page_num
        self.render_page()
    
    def _update_pdf_image_only(self):
        """Actualiza solo la imagen del PDF sin destruir los items gráficos existentes.
        
        Esto es útil cuando se borra texto del PDF y queremos refrescar la imagen
        pero mantener los EditableTextItems activos.
        """
        if not self.pdf_doc or not self.pdf_doc.is_open():
            return
        
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
        
        # Actualizar el pixmap existente o crear uno nuevo
        qpixmap = QPixmap.fromImage(img)
        if self.page_item:
            self.page_item.setPixmap(qpixmap)
        else:
            self.page_item = QGraphicsPixmapItem(qpixmap)
            self.scene.addItem(self.page_item)
            # Asegurar que esté detrás de todo
            self.page_item.setZValue(-1)
    
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
        
        # Obtener información completa de la página (incluyendo rotación)
        page_info = self.pdf_doc.get_page_info(self.current_page)
        if page_info:
            self.pdf_page_width = page_info['rect'].width
            self.pdf_page_height = page_info['rect'].height
            self.page_rotation = page_info['rotation']
            self.page_mediabox = page_info['mediabox']
            self.page_cropbox = page_info['cropbox']
            self.page_transform_matrix = page_info['transformation_matrix']
            self.page_derotation_matrix = page_info['derotation_matrix']
        else:
            self.pdf_page_width, self.pdf_page_height = 612, 792  # Tamaño por defecto (Letter)
            self.page_rotation = 0
            self.page_mediabox = None
            self.page_cropbox = None
            self.page_transform_matrix = None
            self.page_derotation_matrix = None
        
        # Actualizar convertidor de coordenadas
        self.coord_converter.update(zoom_level=self.zoom_level, page_rotation=self.page_rotation)
        
        # Renderizar página
        pixmap = self.pdf_doc.render_page(self.current_page, self.zoom_level)
        if not pixmap:
            return
        
        # Guardar tamaño del pixmap para conversión de coordenadas
        self.pixmap_width = pixmap.width
        self.pixmap_height = pixmap.height
        
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
        
        # Restaurar textos editables para esta página
        self._restore_editable_texts_for_page()
    
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
        self.coord_converter.update(zoom_level=self.zoom_level)
        
        # Actualizar zoom en el overlay de selección
        if self._selection_overlay:
            self._selection_overlay.set_zoom(self.zoom_level)
        
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
            
            # Hit-testing para emitir señales de clic (Phase 3C)
            self._handle_click_hit_test(scene_pos)
            
            # En modo edición, primero verificar si se hace clic en un texto editable
            if self.tool_mode == 'edit':
                # Primero buscar en textos editables ya registrados
                clicked_text = self._find_text_at_position(scene_pos)
                if clicked_text:
                    # Clic en un texto editable existente
                    self._select_text_item(clicked_text)
                    self.dragging_text = True
                    self.drag_start_pos = scene_pos
                    self.drag_original_rect = QRectF(clicked_text.rect())  # Guardar posición original
                    self.text_was_moved = False  # Marcar que aún no se movió
                    event.accept()
                    return
                
                # Si no hay texto editable, buscar texto del PDF en esa posición
                pdf_text = self._find_pdf_text_at_position(scene_pos)
                if pdf_text:
                    # Convertir el texto del PDF en un texto editable
                    text_item = self._convert_pdf_text_to_editable(pdf_text)
                    if text_item:
                        self._select_text_item(text_item)
                        self.dragging_text = True
                        self.drag_start_pos = scene_pos
                        self.drag_original_rect = QRectF(text_item.rect())  # Guardar posición original
                        self.text_was_moved = False  # Marcar que aún no se movió
                        event.accept()
                        return
                
                # Deseleccionar cualquier texto previamente seleccionado
                self._deselect_all_texts()
            
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
        scene_pos = self.mapToScene(event.pos())
        
        # Manejar arrastre de texto editable
        if self.dragging_text and self.selected_text_item and self.drag_start_pos:
            delta = scene_pos - self.drag_start_pos
            # Mover el item usando setPos() en lugar de modificar el rect
            new_pos = self.selected_text_item.pos() + delta
            self.selected_text_item.setPos(new_pos)
            self.drag_start_pos = scene_pos
            self.text_was_moved = True  # Marcar que hubo movimiento real
            event.accept()
            return
        
        if self.is_selecting and self.selection_start:
            # Actualizar rectángulo de selección
            rect = QRectF(self.selection_start, scene_pos).normalized()
            if self.selection_rect:
                self.selection_rect.setRect(rect)
            
            # Mostrar tooltip con texto seleccionado en modo borrado
            if self.tool_mode == 'delete' and rect.width() > 10 and rect.height() > 10:
                self.show_selection_info(rect, event.pos())
        else:
            # Hit-testing durante hover (cuando no se está seleccionando)
            self._handle_hover_hit_test(scene_pos)
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Maneja el evento de soltar el ratón."""
        if event.button() == Qt.LeftButton:
            # Manejar fin del arrastre de texto
            if self.dragging_text and self.selected_text_item:
                self.dragging_text = False
                self.drag_start_pos = None
                # Solo actualizar el PDF si realmente hubo movimiento
                if getattr(self, 'text_was_moved', False):
                    self._update_text_in_pdf(self.selected_text_item)
                    self.text_was_moved = False
                self.drag_original_rect = None
                event.accept()
                super().mouseReleaseEvent(event)
                return
            
            if self.is_selecting:
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
                        # Selección muy pequeña (click simple) - limpiar el rectángulo
                        self.scene.removeItem(self.selection_rect)
                        self.selection_rect = None
                        
                        # Guardar posición del clic
                        click_pos = self.selection_start
                        
                        # En modo highlight, un click simple permite eliminar resaltados existentes
                        if self.tool_mode == 'highlight' and click_pos:
                            self.handle_highlight_click(click_pos)
                        
                        # En modo edición, un click simple permite añadir/editar texto
                        elif self.tool_mode == 'edit' and click_pos:
                            self.handle_edit_click(click_pos)
        
        super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """Maneja el doble clic - editar texto seleccionado."""
        if event.button() == Qt.LeftButton and self.tool_mode == 'edit':
            scene_pos = self.mapToScene(event.pos())
            clicked_text = self._find_text_at_position(scene_pos)
            
            if clicked_text:
                # Doble clic en un texto editable - abrir diálogo de edición
                self._edit_text_content(clicked_text)
                event.accept()
                return
        
        super().mouseDoubleClickEvent(event)
    
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
    
    def keyPressEvent(self, event):
        """Maneja eventos de teclado."""
        # Eliminar texto seleccionado con Delete o Backspace
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            if self.selected_text_item and self.tool_mode == 'edit':
                self._delete_selected_text()
                event.accept()
                return
        
        super().keyPressEvent(event)
    
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
    
    def view_to_pdf_rect(self, view_rect: QRectF, debug: bool = False) -> fitz.Rect:
        """
        Convierte un rectángulo de coordenadas de vista (pixmap) a coordenadas de PDF.
        Usa CoordinateConverter internamente.
        """
        return self.coord_converter.view_to_pdf_rect(view_rect, debug=debug)
    
    def pdf_to_view_rect(self, pdf_rect: fitz.Rect) -> QRectF:
        """
        Convierte un rectángulo de coordenadas de PDF a coordenadas de vista.
        Usa CoordinateConverter internamente.
        """
        return self.coord_converter.pdf_to_view_rect(pdf_rect)
    
    def view_to_pdf_point(self, view_point: QPointF) -> QPointF:
        """
        Convierte un punto de coordenadas de vista a coordenadas de PDF.
        
        Args:
            view_point: Punto en coordenadas de vista/escena
            
        Returns:
            QPointF en coordenadas PDF
        """
        pdf_coords = self.coord_converter.view_to_pdf_point(view_point)
        return QPointF(pdf_coords[0], pdf_coords[1])
    
    def pdf_to_view_point(self, pdf_x: float, pdf_y: float) -> QPointF:
        """
        Convierte un punto de coordenadas de PDF a coordenadas de vista.
        
        Args:
            pdf_x, pdf_y: Coordenadas en espacio PDF
            
        Returns:
            QPointF en coordenadas de vista
        """
        return self.coord_converter.pdf_to_view_point(pdf_x, pdf_y)
    
    def edit_selection(self, pdf_rect: fitz.Rect, blocks=None):
        """Edita texto en el área seleccionada - VERSIÓN SIMPLIFICADA.
        
        Comportamiento simple:
        1. Obtiene el texto que intersecta con el área seleccionada
        2. Muestra editor con ese texto
        3. El texto editado reemplaza al original EN ESA ÁREA
        
        NO se expande la selección. NO se conectan textos separados.
        El área seleccionada es EXACTAMENTE lo que el usuario quiere editar.
        """
        if not self.pdf_doc:
            self.clear_selection()
            return
        
        is_image_pdf = self.pdf_doc.is_image_based_pdf()
        
        # Obtener spans que intersectan con la selección
        spans = self.pdf_doc.get_text_spans_in_rect(self.current_page, pdf_rect)
        
        # Filtrar solo los que realmente intersectan
        intersecting_spans = []
        for span in (spans or []):
            span_rect = span.get('rect')
            if span_rect and span_rect.intersects(pdf_rect):
                intersecting_spans.append(span)
        
        # Ordenar por posición (arriba-abajo, izquierda-derecha)
        intersecting_spans.sort(key=lambda s: (s.get('rect').y0, s.get('rect').x0))
        
        # Construir texto original
        original_text = ''
        for span in intersecting_spans:
            if span.get('needs_newline', False) and original_text:
                original_text += '\n'
            original_text += span.get('text', '')
        
        # Obtener estilos del primer span o usar defaults
        if intersecting_spans:
            first_span = intersecting_spans[0]
            base_font_size = first_span.get('font_size', 12)
            base_is_bold = first_span.get('is_bold', False)
            base_font_name = first_span.get('font_name', 'helv')
            color_str = first_span.get('color', '#000000')
            try:
                base_color = tuple(int(color_str.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            except:
                base_color = (0, 0, 0)
            
            # CALCULAR INTERLINEADO REAL desde las posiciones line_y de los spans
            line_spacing = None
            line_y_values = sorted(set(s.get('line_y', 0) for s in intersecting_spans))
            if len(line_y_values) >= 2:
                # Calcular el promedio de diferencias entre líneas consecutivas
                diffs = [line_y_values[i+1] - line_y_values[i] for i in range(len(line_y_values)-1)]
                line_spacing = sum(diffs) / len(diffs) if diffs else None
        else:
            base_font_size = 12
            base_is_bold = False
            base_font_name = 'helv'
            base_color = (0, 0, 0)
            line_spacing = None
        
        # USAR WORDLIKE EDITOR si está disponible
        if HAS_WORD_LIKE_EDITOR:
            try:
                if original_text.strip():
                    result = self._show_word_editor_for_selection(
                        pdf_rect, intersecting_spans, original_text, base_font_size
                    )
                else:
                    result = self._show_word_editor_for_new_text(pdf_rect)
                
                if result:
                    new_text, runs_data, metadata = result
                    # Agregar interlineado original a metadata para preservarlo
                    metadata['original_line_spacing'] = line_spacing
                    metadata['original_font_name'] = base_font_name
                    
                    if original_text.strip():
                        self._apply_selection_edit(
                            pdf_rect, new_text, runs_data, metadata,
                            is_image_pdf, base_font_size, base_color
                        )
                    else:
                        self._apply_new_text_from_editor(
                            pdf_rect, new_text, runs_data, metadata, is_image_pdf
                        )
                
                self.clear_selection()
                return
                
            except Exception as e:
                print(f"WordLikeEditor falló: {e}")
                import traceback
                traceback.print_exc()
        
        # FALLBACK: Diálogo simple
        if original_text.strip():
            dialog_title = 'Editar texto'
            dialog_msg = f'Texto original: "{original_text[:50]}{"..." if len(original_text) > 50 else ""}"\n\nNuevo texto:'
        else:
            dialog_title = 'Añadir texto'
            dialog_msg = 'Escribe el texto a insertar:'
        
        new_text, ok = QInputDialog.getText(
            self,
            dialog_title,
            dialog_msg,
            text=original_text
        )
        
        if ok and new_text.strip():
            # Guardar snapshot
            self.pdf_doc._save_snapshot()
            
            # Borrar área original (si había texto)
            if original_text.strip():
                self.pdf_doc.erase_text_transparent(self.current_page, pdf_rect, save_snapshot=False)
            
            # Añadir nuevo texto
            success = self.pdf_doc.add_text_to_page(
                self.current_page,
                pdf_rect,
                new_text,
                font_size=base_font_size,
                color=base_color,
                is_bold=base_is_bold,
                save_snapshot=False
            )
            
            if success:
                self.render_page()
                self.documentModified.emit()
        
        self.clear_selection()
    
    def highlight_selection(self, pdf_rect: fitz.Rect, blocks=None):
        """Resalta la selección actual."""
        if not self.pdf_doc:
            return
        
        # Añadir resaltado usando Shape (funciona para texto e imágenes)
        is_image_pdf = self.pdf_doc.is_image_based_pdf()
        
        if self.pdf_doc.highlight_text(self.current_page, pdf_rect):
            # Re-renderizar para mostrar el resaltado
            self.render_page()
            # Limpiar selección visual
            self.clear_selection()
            # Notificar que el documento fue modificado
            self.documentModified.emit()
            
            # Mostrar mensaje informativo si es PDF de imagen
            if is_image_pdf and not blocks:
                # Tooltip breve para no molestar al usuario
                QToolTip.showText(
                    self.mapToGlobal(self.rect().center()),
                    "📷 Resaltado aplicado sobre PDF escaneado",
                    self
                )
        else:
            self.clear_selection()

    def delete_selection(self, pdf_rect: fitz.Rect, blocks=None):
        """Elimina el contenido en la selección actual (texto, imagen o textos editables/overlays)."""
        if not self.pdf_doc or not self.pdf_doc.is_open():
            self.clear_selection()
            return
        
        # Convertir pdf_rect a view_rect para buscar textos editables
        view_rect = self.pdf_to_view_rect(pdf_rect)
        
        # Buscar textos editables/overlays que intersecten con el área seleccionada
        editable_texts_in_area = []
        for text_item in self.editable_text_items:
            item_rect = text_item.sceneBoundingRect()
            if view_rect.intersects(QRectF(item_rect)):
                editable_texts_in_area.append(text_item)
        
        # Obtener texto del PDF si existe
        blocks = self.pdf_doc.find_text_in_rect(self.current_page, pdf_rect)
        text_to_delete = ' '.join([b.text for b in blocks]) if blocks else ""
        
        # También incluir texto de overlays encontrados
        overlay_texts = [t.text for t in editable_texts_in_area]
        
        # Detectar si es un PDF de imagen
        is_image_pdf = self.pdf_doc.is_image_based_pdf()
        
        # Preparar mensaje para el diálogo
        if editable_texts_in_area:
            # Hay textos editables en el área
            all_texts = overlay_texts + ([text_to_delete] if text_to_delete.strip() else [])
            combined_text = ' | '.join(all_texts)
            if len(combined_text) > 100:
                combined_text = combined_text[:100] + "..."
            info_text = f'<span style="color: #ff5555; font-size: 14px;">Texto(s): "{combined_text}"</span>'
        elif text_to_delete.strip():
            info_text = f'<span style="color: #ff5555; font-size: 14px;">Texto: "{text_to_delete[:100]}{"..." if len(text_to_delete) > 100 else ""}"</span>'
        elif is_image_pdf:
            info_text = '<span style="color: #ffa500; font-size: 13px;">📷 PDF escaneado - Se borrará el área seleccionada</span>'
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
            # Copiar la lista para evitar problemas de iteración
            texts_to_remove = list(editable_texts_in_area)
            
            # Primero eliminar textos editables/overlays encontrados (sin renderizar)
            for text_item in texts_to_remove:
                # Verificar que el item aún es válido
                try:
                    if text_item and text_item in self.editable_text_items:
                        self._delete_text_item(text_item, is_empty=False, skip_render=True)
                except RuntimeError:
                    # El objeto ya fue eliminado, continuar
                    continue
            
            # Luego borrar el área del PDF (para texto del PDF o imágenes)
            if text_to_delete.strip() or is_image_pdf or not texts_to_remove:
                if self.pdf_doc.erase_area(self.current_page, pdf_rect, color=(1, 1, 1)):
                    # Re-renderizar página una sola vez al final
                    self.render_page()
                    self.clear_selection()
                    # Notificar que el documento fue modificado
                    self.documentModified.emit()
                else:
                    if not texts_to_remove:
                        QMessageBox.warning(self, 'Error', 'No se pudo borrar el área.')
                    else:
                        # Hubo textos eliminados, renderizar de todos modos
                        self.render_page()
                    self.clear_selection()
            else:
                # Solo había textos editables, renderizar una vez al final
                self.render_page()
                self.clear_selection()
                self.documentModified.emit()
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
        """Maneja un click en modo edición - permite añadir texto en cualquier posición.
        
        Para PDFs de imagen, funciona igual que para PDFs editables:
        1. Primero busca textos overlay/editables existentes (añadidos por el usuario)
        2. Si no hay overlay, busca texto del PDF (si existe)
        3. Si no hay nada, permite añadir texto nuevo
        """
        if not self.pdf_doc:
            return
        
        # PRIMERO: Buscar en textos editables/overlay existentes
        # Esto es crucial para PDFs de imagen donde el usuario ya añadió texto
        existing_editable = self._find_text_at_position(scene_pos)
        if existing_editable:
            # Ya existe un texto editable aquí - editarlo con _edit_text_content
            self._select_text_item(existing_editable)
            self._edit_text_content(existing_editable)
            return
        
        # Convertir a coordenadas PDF
        pdf_x = scene_pos.x() / self.zoom_level
        pdf_y = scene_pos.y() / self.zoom_level
        pdf_point = (pdf_x, pdf_y)
        
        # SEGUNDO: Buscar texto del PDF (solo funciona si el PDF tiene texto real)
        block = self.pdf_doc.find_text_at_point(self.current_page, pdf_point)
        
        if block:
            # Hay texto existente - mostrar diálogo de edición
            
            # Detectar si es PDF de imagen
            is_image_pdf = self.pdf_doc.is_image_based_pdf()
            
            # Obtener spans del PDF para preservar estilos
            spans = self._get_text_spans_in_selection(block.rect)
            text_runs = None
            if spans and len(spans) >= 1:
                text_runs = []
                for span in spans:
                    text_runs.append({
                        'text': span.get('text', ''),
                        'font_name': span.get('font_name', 'Helvetica'),
                        'font_size': span.get('font_size', block.font_size or 12),
                        'is_bold': span.get('is_bold', block.is_bold),
                        'is_italic': span.get('is_italic', False),
                        'color': span.get('color', '#000000'),
                        'indent': span.get('indent', 0.0),
                        'needs_newline': span.get('needs_newline', False),
                        'line_y': span.get('line_y', 0)
                    })
            
            new_text, ok = QInputDialog.getText(
                self,
                'Editar texto',
                f'Texto original: "{block.text}"\n\nNuevo texto:',
                text=block.text
            )
            
            if ok and new_text != block.text:
                if is_image_pdf:
                    # PDF de imagen: PRIMERO borrar, LUEGO crear overlay
                    # CRÍTICO: Borrar el texto original del PDF
                    if self.pdf_doc:
                        self.pdf_doc._save_snapshot()
                        self.pdf_doc.erase_text_transparent(
                            self.current_page,
                            block.rect,
                            save_snapshot=False
                        )
                    
                    view_rect = self.pdf_to_view_rect(block.rect)
                    text_item = self._add_editable_text(
                        view_rect,
                        new_text,
                        font_size=block.font_size or 12,
                        color=block.color or (0, 0, 0),
                        pdf_rect=block.rect,
                        is_from_pdf=True,  # Viene del PDF, guardar posición original
                        font_name=block.font_name or 'helv',
                        is_bold=block.is_bold,
                        text_runs=text_runs
                    )
                    if text_item:
                        # Marcar como overlay
                        text_item.is_overlay = True
                        text_item.pending_write = True
                        text_item.needs_erase = False  # Ya lo borramos
                        text_item.internal_pdf_rect = block.rect
                        self._update_text_data(text_item)
                    
                    # Actualizar solo la imagen del PDF
                    self._update_pdf_image_only()
                    self.documentModified.emit()
                else:
                    # PDF normal: editar directamente
                    result = self.pdf_doc.edit_text(
                        self.current_page,
                        block.rect,
                        new_text,
                        block.font_name,
                        block.font_size,
                        block.color
                    )
                    if result:
                        # Registrar el texto como editable para poder moverlo
                        view_rect = self.pdf_to_view_rect(block.rect)
                        self._add_editable_text(
                            view_rect,
                            new_text,
                            font_size=block.font_size or 12,
                            color=block.color or (0, 0, 0),
                            pdf_rect=block.rect,
                            font_name=block.font_name or 'helv',
                            is_bold=block.is_bold,
                            text_runs=text_runs
                        )
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
                # Crear un rectángulo con tamaño CORRECTO basado en QFontMetrics
                # CRÍTICO: Para PDFs de imagen, el tamaño debe ser exacto o habrá fragmentación
                view_pos = scene_pos  # Posición en vista donde hacer clic
                view_rect = self._calculate_text_rect_for_view(
                    new_text,
                    font_size=12,
                    is_bold=False,
                    base_position=view_pos
                )
                
                # Convertir a coordenadas PDF
                rect = self.view_to_pdf_rect(view_rect)
                
                # Detectar si es PDF de imagen
                is_image_pdf = self.pdf_doc.is_image_based_pdf()
                
                if is_image_pdf:
                    # PDF de imagen: crear texto como OVERLAY (capa visual)
                    # NO escribir al PDF hasta que se guarde
                    view_rect = self.pdf_to_view_rect(rect)
                    text_item = self._add_editable_text(
                        view_rect,
                        new_text,
                        font_size=12,
                        color=(0, 0, 0),
                        pdf_rect=rect,
                        is_from_pdf=False
                    )
                    if text_item:
                        # Marcar como overlay
                        text_item.is_overlay = True
                        text_item.pending_write = True
                        self._update_text_data(text_item)
                    self.documentModified.emit()
                else:
                    # PDF normal: escribir directamente al PDF
                    result = self.pdf_doc.add_text_to_page(
                        self.current_page,
                        rect,
                        new_text,
                        font_size=12,
                        color=(0, 0, 0)
                    )
                    if result:
                        # Registrar el texto como editable para poder moverlo
                        # IMPORTANTE: is_from_pdf=True porque el texto YA está en el PDF
                        view_rect = self.pdf_to_view_rect(rect)
                        self._add_editable_text(
                            view_rect,
                            new_text,
                            font_size=12,
                            color=(0, 0, 0),
                            pdf_rect=rect,
                            is_from_pdf=True  # El texto ya existe en el PDF
                        )
                        self.render_page()
                        self.documentModified.emit()
    
    def handle_highlight_click(self, scene_pos: QPointF):
        """Maneja un click en modo highlight - permite eliminar resaltados con UN SOLO CLIC."""
        if not self.pdf_doc:
            return
        
        # Convertir a coordenadas PDF visuales
        pdf_x = scene_pos.x() / self.zoom_level
        pdf_y = scene_pos.y() / self.zoom_level
        
        
        # Transformar el punto a coordenadas internas
        visual_rect = fitz.Rect(pdf_x, pdf_y, pdf_x + 1, pdf_y + 1)
        transformed_rect = self.pdf_doc.transform_rect_for_page(self.current_page, visual_rect, from_visual=True)
        internal_point = (transformed_rect.x0, transformed_rect.y0)
        
        
        # Buscar highlight en esa posición
        found_highlights = self.pdf_doc.get_highlights_at_point(self.current_page, internal_point)
        
        if found_highlights:
            # Hay un resaltado - preguntar si quiere eliminarlo
            msg = QMessageBox(self)
            msg.setWindowTitle('Eliminar resaltado')
            msg.setIcon(QMessageBox.Question)
            msg.setText('<b>¿Eliminar este resaltado?</b>')
            msg.setInformativeText('El resaltado se eliminará.')
            
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
                # Eliminar usando undo
                if self.pdf_doc.remove_last_highlight(self.current_page):
                    self.render_page()
                    self.documentModified.emit()
                    QToolTip.showText(
                        self.mapToGlobal(self.rect().center()),
                        "✅ Resaltado eliminado",
                        self,
                        QRect(),
                        1500
                    )

    def clear_selection(self):
        """Limpia la selección actual."""
        if self.selection_rect:
            self.scene.removeItem(self.selection_rect)
            self.selection_rect = None
        self.current_selection = None
    
    def show_context_menu(self, pos):
        """Muestra el menú contextual."""
        scene_pos = self.mapToScene(pos)
        
        # Verificar si hay un texto editable en la posición del clic derecho
        clicked_text = self._find_text_at_position(scene_pos)
        
        if clicked_text:
            # Menú contextual para texto editable
            self._select_text_item(clicked_text)
            menu = QMenu(self)
            
            # Guardar referencia al texto para usar en las acciones
            text_to_edit = clicked_text
            
            edit_action = QAction('✏️ Editar texto', self)
            edit_action.triggered.connect(lambda checked, t=text_to_edit: self._edit_text_content(t))
            menu.addAction(edit_action)
            
            delete_action = QAction('🗑️ Eliminar texto', self)
            delete_action.triggered.connect(lambda checked, t=text_to_edit: self._delete_text_item_with_confirmation(t))
            menu.addAction(delete_action)
            
            menu.exec_(self.mapToGlobal(pos))
            return
        
        # Menú contextual para selección de área (comportamiento original)
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
            is_image_pdf = self.pdf_doc.is_image_based_pdf()
            
            if blocks and blocks[0].text.strip():
                # Hay texto existente - editar
                # Obtener spans para preservar estructura
                spans = self._get_text_spans_in_selection(pdf_rect)
                
                # Reconstruir texto con saltos de línea desde los spans
                if spans:
                    original_text = ''
                    for span in spans:
                        if span.get('needs_newline', False) and original_text:
                            original_text += '\n'
                        original_text += span.get('text', '')
                else:
                    original_text = '\n'.join([b.text for b in blocks])
                
                new_text, ok = QInputDialog.getText(
                    self,
                    'Editar texto',
                    f'Texto original: "{original_text}"\n\nNuevo texto:',
                    text=original_text
                )
                
                if ok and new_text.strip():
                    block = blocks[0]
                    font_size = block.font_size or 12
                    color = block.color or (0, 0, 0)
                    
                    # Crear text_runs para preservar estilos y saltos de línea
                    text_runs = None
                    if spans and len(spans) >= 1:
                        text_runs = []
                        for span in spans:
                            text_runs.append({
                                'text': span.get('text', ''),
                                'font_name': span.get('font_name', 'Helvetica'),
                                'font_size': span.get('font_size', font_size),
                                'is_bold': span.get('is_bold', False),
                                'is_italic': span.get('is_italic', False),
                                'color': span.get('color', '#000000'),
                                'indent': span.get('indent', 0.0),
                                'needs_newline': span.get('needs_newline', False),
                                'line_y': span.get('line_y', 0)
                            })
                    
                    if is_image_pdf:
                        # PDF de imagen: usar overlay
                        view_rect = self.pdf_to_view_rect(pdf_rect)
                        text_item = self._add_editable_text(
                            view_rect,
                            new_text,
                            font_size=font_size,
                            color=color,
                            pdf_rect=pdf_rect,
                            is_from_pdf=True,
                            text_runs=text_runs
                        )
                        if text_item:
                            text_item.is_overlay = True
                            text_item.pending_write = True
                            self._update_text_data(text_item)
                        self.documentModified.emit()
                    else:
                        # PDF normal: editar directamente
                        self.pdf_doc._save_snapshot()
                        self.pdf_doc.erase_text_transparent(self.current_page, pdf_rect, save_snapshot=False)
                        if self.pdf_doc.add_text_to_page(
                            self.current_page,
                            pdf_rect,
                            new_text,
                            font_size=font_size,
                            color=color,
                            save_snapshot=False
                        ):
                            # Registrar el texto como editable para poder moverlo
                            view_rect = self.pdf_to_view_rect(pdf_rect)
                            self._add_editable_text(
                                view_rect,
                                new_text,
                                font_size=font_size,
                                color=color,
                                pdf_rect=pdf_rect,
                                is_from_pdf=True,  # El texto ya existe en el PDF
                                text_runs=text_runs
                            )
                            self.render_page()
                            self.documentModified.emit()
            else:
                # No hay texto - añadir texto nuevo
                if is_image_pdf:
                    dialog_title = 'Añadir texto (PDF escaneado)'
                    dialog_msg = '📷 Este es un PDF escaneado.\nEl texto se añadirá sobre la imagen.\n\nEscribe el texto:'
                else:
                    dialog_title = 'Añadir texto'
                    dialog_msg = 'Escribe el texto a añadir en esta área:'
                
                new_text, ok = QInputDialog.getText(
                    self,
                    dialog_title,
                    dialog_msg,
                    text=""
                )
                
                if ok and new_text.strip():
                    if is_image_pdf:
                        # PDF de imagen: usar overlay
                        view_rect = self.pdf_to_view_rect(pdf_rect)
                        text_item = self._add_editable_text(
                            view_rect,
                            new_text,
                            font_size=12,
                            color=(0, 0, 0),
                            pdf_rect=pdf_rect,
                            is_from_pdf=False
                        )
                        if text_item:
                            text_item.is_overlay = True
                            text_item.pending_write = True
                            self._update_text_data(text_item)
                        self.documentModified.emit()
                    else:
                        # PDF normal: añadir directamente
                        success = self.pdf_doc.add_text_to_page(
                            self.current_page,
                            pdf_rect,
                            new_text,
                            font_size=12,
                            color=(0, 0, 0),
                            save_snapshot=True
                        )
                        if success:
                            # Registrar el texto como editable para poder moverlo
                            view_rect = self.pdf_to_view_rect(pdf_rect)
                            self._add_editable_text(
                                view_rect,
                                new_text,
                                font_size=12,
                                color=(0, 0, 0),
                                pdf_rect=pdf_rect,
                                is_from_pdf=True  # El texto ya existe en el PDF
                            )
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
    
    # =====================================================
    # Funciones para manejar textos editables
    # =====================================================
    
    def _find_text_at_position(self, scene_pos: QPointF):
        """Busca un texto editable en la posición dada, ignorando textos vacíos.
        
        IMPORTANTE - INDEPENDENCIA DE MÓDULOS:
        - Cada EditableTextItem es un módulo INDEPENDIENTE con un module_id único
        - El rect de cada módulo se ajusta automáticamente a su contenido
        - Los módulos NUNCA se mezclan entre sí
        - Si el texto crece fuera del área inicial, sigue perteneciendo al mismo módulo
        """
        for text_item in self.editable_text_items:
            # Ignorar textos vacíos
            if not text_item.text or not text_item.text.strip():
                continue
            
            # Usar sceneBoundingRect() para obtener el rect ACTUAL en coordenadas de escena
            # El rect ya refleja el tamaño del contenido (ajustado automáticamente)
            scene_rect = text_item.sceneBoundingRect()
            if scene_rect.contains(scene_pos):
                return text_item
        return None
    
    def _find_pdf_text_at_position(self, scene_pos: QPointF):
        """Busca cualquier texto del PDF en la posición dada."""
        if not self.pdf_doc:
            return None
        
        # Convertir a coordenadas PDF
        pdf_x = scene_pos.x() / self.zoom_level
        pdf_y = scene_pos.y() / self.zoom_level
        pdf_point = (pdf_x, pdf_y)
        
        
        # Buscar texto en esa posición usando find_text_at_point
        block = self.pdf_doc.find_text_at_point(self.current_page, pdf_point)
        
        if block:
            return block
        
        return None
    
    def _convert_pdf_text_to_editable(self, block):
        """Convierte un bloque de texto del PDF en un EditableTextItem.
        
        SIMPLIFICADO: Solo captura el span exacto que el usuario clicó.
        NO expande a spans adyacentes para evitar conflictos con tabulaciones.
        """
        if not block:
            return None
        
        # No convertir textos vacíos
        if not block.text or not block.text.strip():
            return None
        
        # Obtener el rectángulo inicial del bloque clicado
        initial_rect = block.rect
        pdf_rect = initial_rect
        combined_text = block.text
        
        # Obtener el span exacto para preservar estilos
        page = self.pdf_doc.get_page(self.current_page) if self.pdf_doc else None
        
        if page and self.pdf_doc:
            # Buscar spans que intersectan con el bloque clicado
            search_rect = fitz.Rect(
                initial_rect.x0 - 2,
                initial_rect.y0 - 2,
                initial_rect.x1 + 2,
                initial_rect.y1 + 2
            )
            
            nearby_spans = self.pdf_doc.get_text_spans_in_rect(self.current_page, search_rect)
            
            if nearby_spans:
                # Filtrar solo los que realmente intersectan
                intersecting_spans = []
                for span in nearby_spans:
                    span_rect = span.get('rect')
                    if span_rect and span_rect.intersects(initial_rect):
                        intersecting_spans.append(span)
                
                if intersecting_spans:
                    # Usar solo los spans que intersectan directamente
                    # Sin expansión - respeta tabulaciones automáticamente
                    connected_spans = sorted(intersecting_spans, key=lambda s: s.get('rect', initial_rect).x0)
                    
                    # Calcular rect combinado solo de spans que intersectan
                    combined_rect = initial_rect
                    all_text_parts = []
                    for span in connected_spans:
                        span_rect = span.get('rect')
                        if span_rect:
                            combined_rect = fitz.Rect(
                                min(combined_rect.x0, span_rect.x0),
                                min(combined_rect.y0, span_rect.y0),
                                max(combined_rect.x1, span_rect.x1),
                                max(combined_rect.y1, span_rect.y1)
                            )
                        all_text_parts.append(span.get('text', ''))
                    
                    pdf_rect = combined_rect
                    combined_text = ''.join(all_text_parts)
        
        # Expandir ligeramente el rect para asegurar que capture todo el texto
        expanded_pdf_rect = fitz.Rect(
            pdf_rect.x0 - 2,
            pdf_rect.y0 - 1,
            pdf_rect.x1 + 5,
            pdf_rect.y1 + 2
        )
        view_rect = self.pdf_to_view_rect(expanded_pdf_rect)
        
        # El rect interno para borrado es el rect combinado
        internal_rect = pdf_rect
        
        
        # Detectar si el texto original es negrita basándose en el nombre de fuente
        # Las fuentes bold suelen tener "Bold", "bold", "Heavy", "Black" en el nombre
        font_name = getattr(block, 'font_name', '') or ''
        is_bold = any(bold_marker in font_name.lower() for bold_marker in ['bold', 'heavy', 'black', 'demi'])
        
        # Detectar también por flags (bit 4 indica bold en PyMuPDF)
        flags = getattr(block, 'flags', 0) or 0
        if flags & (1 << 4):  # Bit 4 = superscript/bold indicator
            is_bold = True
        
        # CRÍTICO: Obtener spans del PDF para preservar estilos (negritas, tamaños, colores)
        # Esto permite que al mover el texto se mantengan todos los estilos originales
        # Usamos pdf_rect que ya contiene toda la línea
        spans = []
        text_runs = None
        # Variables para usar los valores REALES de los spans
        real_font_size = block.font_size or 12
        real_font_name = font_name
        real_is_bold = is_bold
        line_spacing = 0.0  # Interlineado calculado
        
        if self.pdf_doc:
            try:
                spans = self.pdf_doc.get_text_spans_in_rect(self.current_page, pdf_rect)
                if spans and len(spans) >= 1:
                    text_runs = []
                    combined_text_from_runs = ''
                    
                    # Extraer valores del primer span como referencia base
                    first_span = spans[0]
                    real_font_size = first_span.get('font_size', block.font_size or 12)
                    real_font_name = first_span.get('font_name', font_name) or font_name
                    real_is_bold = first_span.get('is_bold', is_bold)
                    
                    # Calcular interlineado: diferencia entre line_y de spans consecutivos
                    line_y_values = []
                    for span in spans:
                        line_y = span.get('line_y', 0)
                        if line_y not in line_y_values:
                            line_y_values.append(line_y)
                    
                    if len(line_y_values) > 1:
                        line_y_values.sort()
                        spacings = []
                        for i in range(1, len(line_y_values)):
                            spacings.append(line_y_values[i] - line_y_values[i-1])
                        if spacings:
                            line_spacing = sum(spacings) / len(spacings)
                    
                    for span in spans:
                        span_text = span.get('text', '')
                        combined_text_from_runs += span_text
                        text_runs.append({
                            'text': span_text,
                            'font_name': span.get('font_name', 'Helvetica'),
                            'font_size': span.get('font_size', real_font_size),
                            'is_bold': span.get('is_bold', real_is_bold),
                            'is_italic': span.get('is_italic', False),
                            'color': span.get('color', '#000000'),
                            'indent': span.get('indent', 0.0),
                            'needs_newline': span.get('needs_newline', False),
                            'line_y': span.get('line_y', 0)
                        })
                    # Usar el texto combinado de los runs para el item
                    combined_text = combined_text_from_runs
            except Exception as e:
                print(f"Error obteniendo spans: {e}")
        
        # Crear el texto editable usando los valores REALES detectados de los spans
        text_item = self._add_editable_text(
            view_rect,
            combined_text,  # Usar texto de toda la línea, no solo block.text
            font_size=real_font_size,  # Usar tamaño REAL del PDF
            color=block.color or (0, 0, 0),
            pdf_rect=pdf_rect,
            is_from_pdf=True,  # Marcar que viene del PDF y aún no ha sido modificado
            font_name=real_font_name,  # Usar nombre de fuente REAL del PDF
            is_bold=real_is_bold,  # Usar bold REAL del PDF
            text_runs=text_runs,  # CRÍTICO: Pasar text_runs para preservar estilos
            line_spacing=line_spacing  # Pasar interlineado calculado
        )
        
        # Guardar las coordenadas para el borrado (pdf_rect es de toda la línea)
        if text_item:
            text_item.internal_pdf_rect = internal_rect
            # También actualizar los datos guardados
            page_data = self.editable_texts_data.get(self.current_page, [])
            if page_data:
                page_data[-1]['internal_pdf_rect'] = internal_rect
            
            # CRÍTICO: Borrar el texto original del PDF INMEDIATAMENTE para evitar
            # el efecto de doble renderizado (dos tamaños superpuestos)
            # El texto se redibujará como overlay
            # NOTA: internal_rect es el rect combinado de toda la línea
            if self.pdf_doc:
                self.pdf_doc._save_snapshot()
                self.pdf_doc.erase_text_transparent(
                    self.current_page,
                    internal_rect,
                    save_snapshot=False,
                    already_internal=False  # Transformar coordenadas porque pdf_rect es visual
                )
            
            # Marcar como overlay para que se dibuje y se escriba al guardar
            text_item.is_overlay = True
            text_item.pending_write = True
            text_item.needs_erase = False  # Ya lo borramos
            
            # CRÍTICO: Limpiar internal_pdf_rect para evitar borrados futuros incorrectos
            # El texto original YA fue borrado, no necesitamos este rect más
            text_item.internal_pdf_rect = None
            
            # CRÍTICO: Sincronizar los flags con los datos guardados
            page_data = self.editable_texts_data.get(self.current_page, [])
            if page_data:
                page_data[-1]['is_overlay'] = True
                page_data[-1]['pending_write'] = True
                page_data[-1]['needs_erase'] = False
                page_data[-1]['internal_pdf_rect'] = None  # Ya no necesitamos este rect
            
            # Actualizar solo la imagen del PDF (sin destruir los items gráficos)
            # Esto evita el RuntimeError de "object deleted"
            self._update_pdf_image_only()
        
        return text_item
    
    def _select_text_item(self, text_item: EditableTextItem):
        """Selecciona un texto editable.
        
        IMPORTANTE - INDEPENDENCIA DE MÓDULOS:
        - Cada módulo de texto es INDEPENDIENTE y tiene un module_id único
        - Al seleccionar, NO se recalcula el tamaño (ya está calculado)
        - El texto editado SIEMPRE pertenece a su módulo, nunca se mezcla con otros
        
        CRÍTICO: No llamar a adjust_rect_to_content aquí - causa el "salto" de tamaño
        al seleccionar. El tamaño solo debe recalcularse al EDITAR, no al seleccionar.
        """
        # Deseleccionar el anterior
        if self.selected_text_item and self.selected_text_item != text_item:
            self.selected_text_item.set_selected(False)
        
        # CRÍTICO: NO recalcular bounds al seleccionar - causa el salto de tamaño
        # Solo ajustar si NO está finalizado (primera vez que se crea)
        if not getattr(text_item, '_bounds_finalized', False):
            text_item.adjust_rect_to_content()
        
        # Bloquear bounds para evitar recálculos durante movimiento
        text_item.lock_bounds()
        
        # Seleccionar el nuevo
        text_item.set_selected(True)
        self.selected_text_item = text_item
    
    def _deselect_all_texts(self):
        """Deselecciona todos los textos editables."""
        if self.selected_text_item:
            self.selected_text_item.set_selected(False)
            self.selected_text_item = None
    
    def _calculate_text_rect_for_view(self, text: str, font_size: float = 12, 
                                      is_bold: bool = False, base_position: QPointF = None) -> QRectF:
        """Calcula el rect exacto necesario para mostrar texto basado en QFontMetrics.
        
        CRÍTICO para PDFs de imagen: asegura que el rect sea lo suficientemente grande
        para contener COMPLETAMENTE el texto sin fragmentación.
        Soporta texto multilínea con saltos de línea (\n).
        
        Args:
            text: Contenido del texto
            font_size: Tamaño de fuente en puntos
            is_bold: Si es negrita
            base_position: Posición superior-izquierda del rect (en coordenadas de vista)
                          Si None, usa (0, 0)
        
        Returns:
            QRectF con el tamaño exacto necesario
        """
        if not text or not text.strip():
            return QRectF(0, 0, 0, 0)
        
        # Crear fuente con los parámetros especificados
        font = QFont("Helvetica", int(font_size))
        if is_bold:
            font.setBold(True)
        
        # Obtener métricas exactas
        metrics = QFontMetrics(font)
        
        # FIX: Calcular correctamente para texto multilínea
        lines = text.split('\n')
        max_line_width = 0
        for line in lines:
            line_width = metrics.horizontalAdvance(line)
            max_line_width = max(max_line_width, line_width)
        
        # Agregar padding para márgenes seguros
        total_width = max_line_width + 6
        
        # Calcular alto: height da la altura de línea * número de líneas
        text_height = metrics.height() * len(lines)
        # Agregar padding para márgenes seguros
        total_height = text_height + 4
        
        # Usar posición base o (0, 0)
        if base_position is None:
            base_position = QPointF(0, 0)
        
        return QRectF(base_position.x(), base_position.y(), total_width, total_height)
    
    def _add_editable_text(self, view_rect: QRectF, text: str, font_size: float = 12, 
                           color: tuple = (0, 0, 0), pdf_rect=None, is_from_pdf: bool = False,
                           font_name: str = "helv", is_bold: bool = False, text_runs: list = None,
                           line_spacing: float = 0.0):
        """
        Añade un texto editable y lo registra en los datos.
        
        Args:
            view_rect: Rectángulo en coordenadas de vista
            text: Contenido del texto
            font_size: Tamaño de fuente
            color: Color RGB
            pdf_rect: Rectángulo en coordenadas de PDF
            is_from_pdf: True si el texto fue capturado del PDF y aún no se ha borrado
            font_name: Nombre de la fuente (ej: "helv", "hebo" para bold)
            is_bold: Si el texto es negrita
            text_runs: Lista de runs con estilos individuales (opcional)
            line_spacing: Interlineado del texto original (en puntos PDF)
        """
        # NO agregar textos vacíos
        if not text or not text.strip():
            return None
        
        # CRÍTICO: Si viene del PDF y no tiene text_runs, obtenerlos automáticamente
        # Esto asegura que TODOS los caminos preserven estilos (negritas, tamaños, etc.)
        if is_from_pdf and text_runs is None and pdf_rect is not None and self.pdf_doc:
            try:
                spans = self.pdf_doc.get_text_spans_in_rect(self.current_page, pdf_rect)
                if spans and len(spans) >= 1:
                    text_runs = []
                    # Calcular line_spacing si no está definido
                    if line_spacing <= 0:
                        line_y_values = sorted(set(s.get('line_y', 0) for s in spans))
                        if len(line_y_values) > 1:
                            spacings = [line_y_values[i+1] - line_y_values[i] for i in range(len(line_y_values)-1)]
                            line_spacing = sum(spacings) / len(spacings)
                    
                    for span in spans:
                        text_runs.append({
                            'text': span.get('text', ''),
                            'font_name': span.get('font_name', 'Helvetica'),
                            'font_size': span.get('font_size', font_size),
                            'is_bold': span.get('is_bold', is_bold),
                            'is_italic': span.get('is_italic', False),
                            'color': span.get('color', '#000000'),
                            'indent': span.get('indent', 0.0),
                            'needs_newline': span.get('needs_newline', False),
                            'line_y': span.get('line_y', 0)
                        })
            except Exception as e:
                pass  # Silently handle span retrieval errors
        
        # Guardar los datos del texto (no el objeto gráfico)
        text_data = {
            'text': text,
            'font_size': font_size,
            'color': color,
            'pdf_rect': pdf_rect,
            'view_rect': view_rect,
            'original_pdf_rect': pdf_rect if is_from_pdf else None,  # Guardar posición original
            'needs_erase': is_from_pdf,  # Marcar si necesita borrar el texto original del PDF
            'font_name': font_name,
            'is_bold': is_bold,
            'is_overlay': False,  # Se establece después si es necesario
            'pending_write': False,
            'text_runs': text_runs,  # Runs con estilos individuales
            'has_mixed_styles': text_runs is not None and len(text_runs) > 1,
            'line_spacing': line_spacing  # Interlineado del texto original
        }
        
        if self.current_page not in self.editable_texts_data:
            self.editable_texts_data[self.current_page] = []
        self.editable_texts_data[self.current_page].append(text_data)
        
        # Crear y añadir el item gráfico
        text_item = self._create_text_item_from_data(text_data)
        self.editable_text_items.append(text_item)
        self.scene.addItem(text_item)
        
        
        return text_item
    
    def _create_text_item_from_data(self, text_data: dict) -> EditableTextItem:
        """Crea un EditableTextItem a partir de datos guardados."""
        view_rect = text_data['view_rect']
        
        # CRÍTICO: Extraer posición y crear rect normalizado (0, 0, w, h)
        # La posición se establece con setPos(), no en el rect
        pos_x = view_rect.x()
        pos_y = view_rect.y()
        normalized_rect = QRectF(0, 0, view_rect.width(), view_rect.height())
        
        text_item = EditableTextItem(
            normalized_rect,  # Rect normalizado sin posición
            text_data['text'],
            text_data['font_size'],
            text_data['color'],
            self.current_page,
            font_name=text_data.get('font_name', 'helv'),
            is_bold=text_data.get('is_bold', False),
            zoom_level=self.zoom_level,  # Pasar zoom para escalar al dibujar
            line_spacing=text_data.get('line_spacing', 0.0)  # Interlineado del PDF
        )
        
        # CRÍTICO: Establecer la posición del item
        text_item.setPos(pos_x, pos_y)
        
        text_item.pdf_rect = text_data['pdf_rect']
        text_item.original_pdf_rect = text_data.get('original_pdf_rect')
        text_item.needs_erase = text_data.get('needs_erase', False)
        text_item.is_overlay = text_data.get('is_overlay', False)
        text_item.pending_write = text_data.get('pending_write', False)
        text_item.data_index = len(self.editable_texts_data.get(self.current_page, [])) - 1
        # CRÍTICO: Preservar text_runs y has_mixed_styles para estilos al mover
        text_item.text_runs = text_data.get('text_runs')
        text_item.has_mixed_styles = text_data.get('has_mixed_styles', False)
        # Guardar tamaño original para poder escalar al editar
        text_item._original_font_size = text_data['font_size']
        
        # CRÍTICO: Para overlays, NO recalcular - ya tienen el tamaño correcto
        if text_data.get('is_overlay', False):
            text_item._bounds_finalized = True
            text_item.lock_bounds()
        else:
            # Ajustar caja al tamaño del contenido
            text_item.adjust_rect_to_content()
        
        return text_item
    
    def _get_text_spans_in_selection(self, pdf_rect: fitz.Rect) -> list:
        """
        Obtiene los spans de texto del PDF para un área seleccionada.
        Preserva tipografía, tamaños, negritas, colores y estructura.
        """
        if not self.pdf_doc:
            return []
        
        try:
            spans = self.pdf_doc.get_text_spans_in_rect(
                self.current_page, 
                pdf_rect
            )
            return spans
        except Exception:
            return []
    
    def _show_word_editor_for_selection(
        self, pdf_rect: fitz.Rect, spans: list, original_text: str, base_font_size: float
    ):
        """
        Muestra el WordLikeEditor para editar texto seleccionado,
        preservando la estructura, estilos, tabulaciones y saltos de línea.
        """
        max_width = pdf_rect.width if pdf_rect else 500.0
        
        # Crear DocumentStructure desde los spans
        doc_structure = DocumentStructure(
            base_font_name='Helvetica',
            base_font_size=base_font_size,
            max_width=max_width
        )
        
        # Agregar runs desde los spans preservando estructura completa
        if spans:
            for span in spans:
                doc_structure.runs.append(TextRunInfo(
                    text=span.get('text', ''),
                    font_name=span.get('font_name', 'Helvetica'),
                    font_size=span.get('font_size', base_font_size),
                    is_bold=span.get('is_bold', False),
                    is_italic=span.get('is_italic', False),
                    color=span.get('color', '#000000'),
                    indent=span.get('indent', 0.0),
                    alignment=span.get('alignment', 'left'),
                    is_line_start=span.get('is_line_start', False),
                    is_line_end=span.get('is_line_end', False),
                    needs_newline=span.get('needs_newline', False),
                    line_y=span.get('line_y', 0.0)
                ))
        else:
            # Si no hay spans, usar el texto original
            doc_structure.runs.append(TextRunInfo(
                text=original_text,
                font_name='Helvetica',
                font_size=base_font_size,
                is_bold=False,
                is_italic=False,
                color='#000000'
            ))
        
        # Mostrar el editor
        return show_word_like_editor(
            parent=self,
            document=doc_structure,
            title="Editar Texto Seleccionado"
        )
    
    def _show_word_editor_for_new_text(self, pdf_rect: fitz.Rect):
        """
        Muestra el WordLikeEditor para añadir nuevo texto.
        """
        max_width = pdf_rect.width if pdf_rect else 500.0
        
        # Crear DocumentStructure vacío
        doc_structure = DocumentStructure(
            base_font_name='Helvetica',
            base_font_size=12.0,
            max_width=max_width
        )
        
        # Mostrar el editor
        return show_word_like_editor(
            parent=self,
            document=doc_structure,
            title="Añadir Texto"
        )
    
    def _apply_selection_edit(
        self, pdf_rect: fitz.Rect, new_text: str, runs_data: list, 
        metadata: dict, is_image_pdf: bool, base_font_size: float, base_color: tuple
    ):
        """
        Aplica los cambios del editor al texto seleccionado,
        soportando múltiples runs con diferentes estilos.
        PRESERVA: tipografía, tamaño, interlineado y estilos originales.
        """
        if not new_text.strip():
            return
        
        view_rect = self.pdf_to_view_rect(pdf_rect)
        
        # Obtener interlineado y fuente originales de metadata
        original_line_spacing = metadata.get('original_line_spacing')
        original_font_name = metadata.get('original_font_name', 'Helvetica')
        
        # SIEMPRE considerar como estilos mixtos si tenemos runs (para preservar formato)
        # No importa si los estilos son "iguales", usar runs preserva mejor la estructura
        has_runs = len(runs_data) > 0
        
        # Obtener el estilo principal (primer run o estilo uniforme)
        if runs_data:
            first_run = runs_data[0]
            font_size = first_run.get('font_size', base_font_size)
            is_bold = first_run.get('is_bold', False)
            # Usar la fuente original del PDF si el run no especifica una diferente
            font_name = first_run.get('font_name') or original_font_name or 'Helvetica'
            color_str = first_run.get('color', '#000000')
            # Convertir color hex a tuple RGB
            try:
                color = tuple(int(color_str.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            except:
                color = base_color
        else:
            font_size = base_font_size
            is_bold = False
            font_name = original_font_name or 'helv'
            color = base_color
        
        if is_image_pdf:
            # PDF de imagen: PRIMERO borrar el texto original, LUEGO crear overlay
            # CRÍTICO: Borrar el texto original del PDF para evitar duplicados
            if self.pdf_doc:
                self.pdf_doc._save_snapshot()
                self.pdf_doc.erase_text_transparent(
                    self.current_page,
                    pdf_rect,
                    save_snapshot=False
                )
            
            # Ahora crear el overlay con los runs
            text_item = self._add_editable_text(
                view_rect,
                new_text,
                font_size=font_size,
                color=color,
                pdf_rect=pdf_rect,
                is_from_pdf=True,
                font_name=font_name,
                is_bold=is_bold,
                text_runs=runs_data if has_runs else None
            )
            if text_item:
                text_item.is_overlay = True
                text_item.pending_write = True
                text_item.needs_erase = False  # Ya lo borramos
                
                # CRÍTICO: Ajustar rect al contenido real y actualizar TODOS los rects
                # Usamos force=True porque es una EDICIÓN real, no un movimiento
                text_item.adjust_rect_to_content(force=True)
                adjusted_rect = text_item.rect()
                adjusted_scene_rect = QRectF(
                    text_item.pos().x(),
                    text_item.pos().y(),
                    adjusted_rect.width(),
                    adjusted_rect.height()
                )
                expanded_pdf_rect = self.view_to_pdf_rect(adjusted_scene_rect)
                
                # CRÍTICO: Para overlays, solo actualizar pdf_rect
                # NO establecer internal_pdf_rect - solo se usa para textos que vienen del PDF
                # internal_pdf_rect se establecerá cuando se escriba al PDF (commit)
                text_item.pdf_rect = expanded_pdf_rect
                # text_item.internal_pdf_rect = None  # Los overlays nuevos no tienen esto
                
                self._update_text_data(text_item)
            
            # Actualizar solo la imagen del PDF (sin destruir los items gráficos)
            self._update_pdf_image_only()
            self.documentModified.emit()
        else:
            # PDF normal: editar directamente
            self.pdf_doc._save_snapshot()
            self.pdf_doc.erase_text_transparent(self.current_page, pdf_rect, save_snapshot=False)
            
            # SIEMPRE usar add_text_runs_to_page para preservar estilos
            if has_runs:
                try:
                    success = self.pdf_doc.add_text_runs_to_page(
                        self.current_page,
                        pdf_rect,
                        runs_data,
                        line_spacing=original_line_spacing,  # Preservar interlineado original
                        save_snapshot=False
                    )
                except (AttributeError, TypeError) as e:
                    # Fallback si el método no existe o no acepta line_spacing
                    try:
                        success = self.pdf_doc.add_text_runs_to_page(
                            self.current_page,
                            pdf_rect,
                            runs_data,
                            save_snapshot=False
                        )
                    except AttributeError:
                        success = self.pdf_doc.add_text_to_page(
                            self.current_page,
                            pdf_rect,
                            new_text,
                            font_size=font_size,
                            color=color,
                            is_bold=is_bold,
                            save_snapshot=False
                        )
            else:
                # Sin runs_data - usar add_text_to_page con estilo base
                success = self.pdf_doc.add_text_to_page(
                    self.current_page,
                    pdf_rect,
                    new_text,
                    font_size=font_size,
                    color=color,
                    is_bold=is_bold,
                    save_snapshot=False
                )
            
            if success:
                # PDF NORMAL: El texto ya está escrito en el PDF
                # NO crear overlay - solo renderizar para ver el cambio
                # El texto puede volver a seleccionarse/editarse del PDF directamente
                self.render_page()
                self.documentModified.emit()
    
    def _apply_new_text_from_editor(
        self, pdf_rect: fitz.Rect, new_text: str, runs_data: list, 
        metadata: dict, is_image_pdf: bool
    ):
        """
        Aplica el nuevo texto creado desde el editor.
        CRÍTICO: Después de crear el texto, actualiza pdf_rect al tamaño REAL del contenido.
        """
        if not new_text.strip():
            return
        
        view_rect = self.pdf_to_view_rect(pdf_rect)
        
        # Obtener estilo del primer run
        if runs_data:
            first_run = runs_data[0]
            font_size = first_run.get('font_size', 12.0)
            is_bold = first_run.get('is_bold', False)
            color_str = first_run.get('color', '#000000')
            try:
                color = tuple(int(color_str.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            except:
                color = (0, 0, 0)
        else:
            font_size = 12.0
            is_bold = False
            color = (0, 0, 0)
        
        has_mixed_styles = metadata.get('has_mixed_styles', False) and len(runs_data) > 1
        
        if is_image_pdf:
            # PDF de imagen: crear overlay
            text_item = self._add_editable_text(
                view_rect, 
                new_text, 
                font_size=font_size, 
                color=color, 
                pdf_rect=pdf_rect,
                is_from_pdf=False,
                is_bold=is_bold
            )
            if text_item:
                text_item.is_overlay = True
                text_item.pending_write = True
                if has_mixed_styles:
                    text_item.text_runs = runs_data
                
                # CRÍTICO: Ajustar rect al contenido real y actualizar TODOS los rects
                # Usamos force=True para asegurar recálculo correcto
                text_item.adjust_rect_to_content(force=True)
                adjusted_rect = text_item.rect()
                adjusted_scene_rect = QRectF(
                    text_item.pos().x(),
                    text_item.pos().y(),
                    adjusted_rect.width(),
                    adjusted_rect.height()
                )
                expanded_pdf_rect = self.view_to_pdf_rect(adjusted_scene_rect)
                
                # CRÍTICO: Actualizar solo pdf_rect, NO internal_pdf_rect
                # Los overlays nuevos no necesitan internal_pdf_rect hasta commit
                text_item.pdf_rect = expanded_pdf_rect
                # Para overlays nuevos, no hay original_pdf_rect ni internal_pdf_rect
                
                self._update_text_data(text_item)
            self.documentModified.emit()
        else:
            # PDF normal - AHORA TAMBIÉN USA OVERLAY para consistencia
            # El texto se escribe al PDF solo cuando se GUARDA (commit_overlay_texts)
            # Esto evita el problema de rect pequeño vs expandido
            text_item = self._add_editable_text(
                view_rect, 
                new_text, 
                font_size=font_size, 
                color=color, 
                pdf_rect=pdf_rect,
                is_from_pdf=False,  # NO viene del PDF, es nuevo
                is_bold=is_bold
            )
            if text_item:
                text_item.is_overlay = True
                text_item.pending_write = True
                if has_mixed_styles:
                    text_item.text_runs = runs_data
                
                # CRÍTICO: Ajustar rect al contenido real y actualizar TODOS los rects
                # Usamos force=True para asegurar recálculo correcto
                text_item.adjust_rect_to_content(force=True)
                adjusted_rect = text_item.rect()
                adjusted_scene_rect = QRectF(
                    text_item.pos().x(),
                    text_item.pos().y(),
                    adjusted_rect.width(),
                    adjusted_rect.height()
                )
                expanded_pdf_rect = self.view_to_pdf_rect(adjusted_scene_rect)
                
                # CRÍTICO: Solo actualizar pdf_rect, NO internal_pdf_rect expandido
                # Los overlays no necesitan internal_pdf_rect hasta commit
                text_item.pdf_rect = expanded_pdf_rect
                
                self._update_text_data(text_item)
            
            self.documentModified.emit()

    def _get_text_spans_for_item(self, text_item: EditableTextItem) -> list:
        """
        Obtiene los spans de texto para un item editable.
        PRIORIDAD: Usa text_runs guardados si existen (texto ya editado).
        Solo busca en PDF si no hay text_runs (texto original no editado).
        
        Esto preserva estilos cuando se re-edita texto que ya fue modificado.
        """
        # PRIORIDAD 1: Usar text_runs guardados si existen
        # Esto preserva estilos de textos que ya fueron editados/movidos
        text_runs = getattr(text_item, 'text_runs', None)
        if text_runs and len(text_runs) > 0:
            # Convertir text_runs al formato de spans esperado
            spans = []
            for run in text_runs:
                spans.append({
                    'text': run.get('text', ''),
                    'font_name': run.get('font_name', 'Helvetica'),
                    'font_size': run.get('font_size', 12),
                    'is_bold': run.get('is_bold', False),
                    'is_italic': run.get('is_italic', False),
                    'color': run.get('color', '#000000'),
                    'indent': run.get('indent', 0.0),
                    'needs_newline': run.get('needs_newline', False),
                    'line_y': run.get('line_y', 0)
                })
            return spans
        
        # PRIORIDAD 2: Buscar en el PDF original
        if not self.pdf_doc or not text_item.pdf_rect:
            return []
        
        try:
            spans = self.pdf_doc.get_text_spans_in_rect(
                self.current_page, 
                text_item.pdf_rect
            )
            return spans
        except Exception:
            return []
    
    def _edit_text_content(self, text_item: EditableTextItem):
        """Abre un diálogo para editar el contenido del texto con opciones de formato.
        
        Detecta automáticamente si el texto tiene múltiples estilos (runs) y
        usa el editor apropiado:
        - WordLikeEditorDialog (prioridad máxima) - Editor completo tipo Word
        - RichTextEditDialog si hay múltiples spans con diferentes estilos
        - EnhancedTextEditDialog para texto simple
        - TextEditDialog como fallback básico
        """
        # Obtener valores actuales
        current_text = text_item.text
        current_font_size = text_item.font_size
        current_is_bold = getattr(text_item, 'is_bold', False)
        current_font_name = getattr(text_item, 'font_name', 'helv')
        
        # Calcular ancho máximo disponible
        max_width = 200  # Default
        if text_item.pdf_rect:
            max_width = text_item.pdf_rect.width
        
        # Obtener spans del PDF para detectar múltiples estilos
        spans = self._get_text_spans_for_item(text_item)
        has_mixed_styles = len(spans) > 1
        
        # PRIORIDAD 0: Usar WordLikeEditorDialog - Editor completo tipo Word
        if HAS_WORD_LIKE_EDITOR:
            try:
                # Crear DocumentStructure desde los spans del PDF
                doc_structure = DocumentStructure(
                    base_font_name=current_font_name.replace('hebo', 'Helvetica').replace('helv', 'Helvetica'),
                    base_font_size=current_font_size,
                    max_width=max_width
                )
                
                # Agregar runs desde los spans
                if spans:
                    for span in spans:
                        doc_structure.runs.append(TextRunInfo(
                            text=span['text'],
                            font_name=span.get('font_name', 'Helvetica'),
                            font_size=span.get('font_size', current_font_size),
                            is_bold=span.get('is_bold', False),
                            is_italic=span.get('is_italic', False),
                            color=span.get('color', '#000000'),
                            indent=span.get('indent', 0.0),
                            needs_newline=span.get('needs_newline', False),
                            line_y=span.get('line_y', 0.0),
                            is_line_start=span.get('is_line_start', False),
                            is_line_end=span.get('is_line_end', False)
                        ))
                else:
                    # Si no hay spans, crear uno con el texto actual
                    doc_structure.runs.append(TextRunInfo(
                        text=current_text,
                        font_name=current_font_name.replace('hebo', 'Helvetica').replace('helv', 'Helvetica'),
                        font_size=current_font_size,
                        is_bold=current_is_bold,
                        is_italic=False,
                        color='#000000'
                    ))
                
                # Abrir editor tipo Word
                result = show_word_like_editor(
                    parent=self,
                    document=doc_structure,
                    title="Editar Texto"
                )
                
                if result:
                    new_text, runs_data, metadata = result
                    
                    # Si el usuario aplicó múltiples estilos, guardar como runs
                    if metadata.get('has_mixed_styles', False) and len(runs_data) > 1:
                        # Guardar los runs para aplicarlos al PDF
                        self._apply_rich_text_edit(text_item, new_text, runs_data, metadata)
                    else:
                        # Estilo uniforme - usar método simple
                        new_is_bold = runs_data[0].get('is_bold', False) if runs_data else current_is_bold
                        new_font_size = runs_data[0].get('font_size', current_font_size) if runs_data else current_font_size
                        self._apply_text_edit(text_item, new_text, new_font_size, new_is_bold)
                return
                
            except Exception as e:
                print(f"WordLikeEditorDialog falló: {e}")
                import traceback
                traceback.print_exc()
                # Continuar con siguiente opción
        
        # PRIORIDAD 1: Usar RichTextEditDialog si hay múltiples estilos
        if HAS_RICH_TEXT_EDITOR and has_mixed_styles:
            try:
                # Crear TextBlock desde los spans del PDF
                text_block = TextBlock(max_width=max_width)
                for span in spans:
                    text_block.add_run(TextRun(
                        text=span['text'],
                        font_name=span.get('font_name', 'Helvetica'),
                        font_size=span.get('font_size', current_font_size),
                        is_bold=span.get('is_bold', False),
                        is_italic=span.get('is_italic', False),
                        color=span.get('color', '#000000')
                    ))
                
                # Abrir editor enriquecido
                result = show_rich_text_editor(
                    parent=self,
                    text_block=text_block,
                    original_text=current_text,
                    font_name=current_font_name.replace('hebo', 'Helvetica').replace('helv', 'Helvetica'),
                    font_size=current_font_size,
                    is_bold=current_is_bold,
                    max_width=max_width
                )
                
                if result:
                    new_text, runs_data, metadata = result
                    
                    # Si el usuario aplicó múltiples estilos, guardar como runs
                    if metadata.get('has_mixed_styles', False) and len(runs_data) > 1:
                        # Guardar los runs para aplicarlos al PDF
                        self._apply_rich_text_edit(text_item, new_text, runs_data, metadata)
                    else:
                        # Estilo uniforme - usar método simple
                        new_is_bold = runs_data[0].get('is_bold', False) if runs_data else current_is_bold
                        new_font_size = runs_data[0].get('font_size', current_font_size) if runs_data else current_font_size
                        self._apply_text_edit(text_item, new_text, new_font_size, new_is_bold)
                return
                
            except Exception as e:
                print(f"RichTextEditDialog falló: {e}")
                # Continuar con siguiente opción
        
        # PRIORIDAD 2: Usar EnhancedTextEditDialog
        if HAS_ENHANCED_DIALOG:
            try:
                # Crear descriptor de fuente para el diálogo
                font_descriptor = None
                detected_bold = current_is_bold
                
                if HAS_FONT_MANAGER:
                    # Usar FontManager para detectar info de fuente
                    try:
                        font_manager = get_font_manager()
                        # Crear FontDescriptor básico
                        font_descriptor = FontDescriptor(
                            name=current_font_name.replace('hebo', 'Helvetica-Bold').replace('helv', 'Helvetica'),
                            size=current_font_size,
                            possible_bold=current_is_bold,
                            color='#000000'
                        )
                    except Exception:
                        pass
                
                # Abrir diálogo mejorado
                result = show_text_edit_dialog(
                    parent=self,
                    original_text=current_text,
                    max_width=max_width,
                    font_descriptor=font_descriptor,
                    detected_bold=detected_bold
                )
                
                if result:
                    new_text, change_report = result
                    new_text = new_text.strip()
                    
                    # Obtener opciones de estilo
                    new_is_bold = change_report.get('bold_applied', current_is_bold)
                    new_font_size = change_report.get('font_size', current_font_size)
                    
                    # Si hay reducción de tamaño
                    size_reduction = change_report.get('size_reduced', 0)
                    if size_reduction > 0:
                        new_font_size = current_font_size * (1 - size_reduction / 100)
                    
                    # Aplicar cambios
                    self._apply_text_edit(
                        text_item, 
                        new_text, 
                        new_font_size, 
                        new_is_bold,
                        change_report.get('was_truncated', False),
                        change_report.get('warnings', [])
                    )
                return
                
            except Exception as e:
                # Si falla, usar el diálogo básico
                print(f"EnhancedTextEditDialog falló, usando básico: {e}")
        
        # Fallback: usar diálogo básico
        dialog = TextEditDialog(
            text=current_text,
            font_size=current_font_size,
            is_bold=current_is_bold,
            title='Editar texto',
            parent=self
        )
        
        if dialog.exec_() == QDialog.Accepted:
            values = dialog.get_values()
            new_text = values['text'].strip()
            new_font_size = values['font_size']
            new_is_bold = values['is_bold']
            
            self._apply_text_edit(text_item, new_text, new_font_size, new_is_bold)
    
    def _apply_text_edit(
        self, 
        text_item: EditableTextItem, 
        new_text: str, 
        new_font_size: float, 
        new_is_bold: bool,
        was_truncated: bool = False,
        warnings: list = None
    ):
        """Aplica los cambios de edición al texto.
        
        Extraído de _edit_text_content para poder ser usado tanto
        por el diálogo básico como por el mejorado.
        """
        # Si el texto está vacío, ELIMINAR el texto del PDF y el item
        if not new_text:
            self._remove_empty_text_item(text_item)
            self.documentModified.emit()
            return
        
        current_is_bold = getattr(text_item, 'is_bold', False)
        
        # Verificar si hay cambios (tolerancia de 0.5 para tamaño de fuente)
        text_changed = new_text != text_item.text
        size_changed = abs(new_font_size - text_item.font_size) > 0.5
        bold_changed = new_is_bold != current_is_bold
        
        print(f"  text_changed = {text_changed}")
        print(f"  size_changed = {size_changed}")
        print(f"  bold_changed = {bold_changed}")
        
        if not (text_changed or size_changed or bold_changed):
            print("  NO HAY CAMBIOS - retornando")
            return
        
        # CRÍTICO: Guardar tamaño actual ANTES de actualizarlo (para calcular escala)
        current_font_size_before = text_item.font_size
        original_font_size = getattr(text_item, '_original_font_size', current_font_size_before)
        
        # CRÍTICO: Si el TEXTO cambió, los text_runs ya no son válidos porque contienen
        # el texto viejo. Limpiarlos PRIMERO, ANTES de cambiar el texto.
        # De lo contrario, el setter de text llama a adjust_rect_to_content() con los runs viejos.
        text_runs = getattr(text_item, 'text_runs', None)
        if text_runs and text_changed:
            print(f"  TEXTO CAMBIÓ - limpiando text_runs ANTES de actualizar texto")
            text_item.text_runs = None
            text_item.has_mixed_styles = False
            text_runs = None  # Para que no entre en los bloques siguientes
        
        # Actualizar propiedades del item
        # NOTA: El setter de text llama a adjust_rect_to_content() automáticamente
        text_item._text = new_text  # Establecer directamente sin disparar el setter aún
        text_item.font_size = new_font_size
        text_item.is_bold = new_is_bold
        
        # Si cambió el tamaño de fuente (pero NO el texto), actualizar los text_runs
        # para que conserven sus proporciones relativas
        if text_runs and size_changed:
            # Calcular el factor de escala usando el tamaño ORIGINAL antes del cambio
            if original_font_size and original_font_size > 0:
                scale_factor = new_font_size / original_font_size
            else:
                scale_factor = 1.0
            
            print(f"  original_font_size={original_font_size}, new_font_size={new_font_size}")
            print(f"  Actualizando text_runs con scale_factor={scale_factor}")
            
            # Actualizar cada run con el nuevo tamaño proporcional
            for run in text_runs:
                original_run_size = run.get('font_size', original_font_size)
                run['font_size'] = original_run_size * scale_factor
                # También actualizar bold si cambió
                if bold_changed:
                    run['is_bold'] = new_is_bold
            
            # Guardar el nuevo tamaño como referencia para futuros cambios
            text_item._original_font_size = new_font_size
        elif text_runs and bold_changed:
            # Solo cambió bold, actualizar todos los runs
            for run in text_runs:
                run['is_bold'] = new_is_bold
        
        # Preservar nombre de fuente original si es posible
        # Solo usar helv/hebo como fallback si no hay fuente original
        current_font_name = getattr(text_item, 'font_name', None)
        if current_font_name and current_font_name not in ('helv', 'hebo'):
            # Preservar fuente original del PDF (ej: Arial, Times, etc.)
            # La negrita se maneja por separado con is_bold
            pass  # Mantener text_item.font_name
        else:
            # Fallback para fuentes estándar
            text_item.font_name = "hebo" if new_is_bold else "helv"
        
        # Detectar si es PDF de imagen
        is_image_pdf = self.pdf_doc.is_image_based_pdf() if self.pdf_doc else False
        
        # CRÍTICO: Guardar la posición actual del item ANTES de cualquier ajuste
        # Ahora que el rect es normalizado (0,0,w,h), la posición real está en pos()
        current_scene_rect = text_item.sceneBoundingRect()
        current_pos = text_item.pos()
        current_pos_x = current_pos.x()
        current_pos_y = current_pos.y()
        
        # Determinar si es overlay ANTES de cualquier cambio
        is_overlay_now = getattr(text_item, 'is_overlay', False)
        
        # CRÍTICO: Llamar a adjust_rect_to_content PRIMERO para calcular el tamaño correcto
        # Este método ya maneja tabulaciones, múltiples líneas y text_runs
        # Usamos force=True porque es una EDICIÓN real, no un movimiento
        text_item.adjust_rect_to_content(force=True)
        
        # Obtener el rect ajustado al contenido
        adjusted_rect = text_item.rect()
        
        # Establecer la posición correcta (mantener posición original)
        text_item.setPos(current_pos_x, current_pos_y)
        
        
        # SISTEMA UNIFICADO: SIEMPRE usar overlay para ediciones
        # El texto solo se escribe al PDF cuando se GUARDA el documento
        # Esto evita duplicación y cambios de formato
        
        needs_erase = getattr(text_item, 'needs_erase', False)
        
        # Si el texto viene del PDF original y nunca fue modificado, borrar el original
        if needs_erase and not is_overlay_now:
            
            internal_pdf_rect = getattr(text_item, 'internal_pdf_rect', None)
            original_pdf_rect = getattr(text_item, 'original_pdf_rect', None)
            
            if internal_pdf_rect:
                rect_to_erase = internal_pdf_rect
                already_internal = True
            elif original_pdf_rect:
                rect_to_erase = original_pdf_rect
                already_internal = False
            else:
                rect_to_erase = None
                already_internal = False
            
            if rect_to_erase and self.pdf_doc:
                self.pdf_doc._save_snapshot()
                self.pdf_doc.erase_text_transparent(
                    self.current_page,
                    rect_to_erase,
                    save_snapshot=False,
                    already_internal=already_internal
                )
        
        # Convertir a overlay (si no lo era)
        if not is_overlay_now:
            text_item.is_overlay = True
        
        # Actualizar propiedades
        text_item.pending_write = True
        text_item.needs_erase = False  # Ya borramos el original (si había)
        
        # CRÍTICO: Limpiar internal_pdf_rect después de borrar para evitar borrados futuros
        text_item.internal_pdf_rect = None
        
        # CRÍTICO: Llamar a adjust_rect_to_content para que la caja se adapte al nuevo tamaño
        # Usamos force=True porque es una EDICIÓN real, no un movimiento
        text_item.adjust_rect_to_content(force=True)
        
        # IMPORTANTE: Actualizar pdf_rect DESPUÉS de adjust_rect_to_content
        # para que refleje el tamaño real del texto ajustado
        adjusted_rect = text_item.rect()
        adjusted_scene_rect = QRectF(
            text_item.pos().x(),
            text_item.pos().y(),
            adjusted_rect.width(),
            adjusted_rect.height()
        )
        text_item.pdf_rect = self.view_to_pdf_rect(adjusted_scene_rect)
        
        # Actualizar los datos guardados
        self._update_text_data(text_item)
        
        # Re-renderizar para mostrar el PDF actualizado (sin el texto original)
        if needs_erase and not is_overlay_now:
            self.render_page()
        else:
            # Solo forzar repintado del item
            text_item.update()
        
        self.documentModified.emit()
    
    def _apply_rich_text_edit(
        self, 
        text_item: EditableTextItem, 
        new_text: str, 
        runs_data: list,
        metadata: dict
    ):
        """
        Aplica cambios de texto con múltiples estilos (runs).
        
        Este método se usa cuando el usuario edita texto y aplica diferentes
        estilos a diferentes partes (ej: algunas palabras en negrita).
        
        Args:
            text_item: El item de texto a actualizar
            new_text: El texto completo concatenado
            runs_data: Lista de runs con estilos individuales
            metadata: Información adicional del editor
        """
        if not new_text:
            self._remove_empty_text_item(text_item)
            self.documentModified.emit()
            return
        
        # CRÍTICO: Guardar la posición actual del item ANTES de cualquier ajuste
        # Ahora que el rect es normalizado (0,0,w,h), la posición real está en pos()
        current_pos = text_item.pos()
        current_pos_x = current_pos.x()
        current_pos_y = current_pos.y()
        
        is_overlay_now = getattr(text_item, 'is_overlay', False)
        needs_erase = getattr(text_item, 'needs_erase', False)
        
        # CRÍTICO: Actualizar los runs PRIMERO, luego el texto
        # Así cuando adjust_rect_to_content() se llame, usará los runs correctos
        text_item.text_runs = runs_data
        text_item.has_mixed_styles = True
        text_item._text = new_text  # Establecer directamente sin disparar el setter
        
        # Obtener propiedades de estilo de los runs
        base_font_size = runs_data[0].get('font_size', 12) if runs_data else 12
        has_any_bold = any(r.get('is_bold', False) for r in runs_data)
        
        # CRÍTICO: Actualizar propiedades de fuente
        text_item.font_size = base_font_size
        text_item.is_bold = has_any_bold
        
        # CRÍTICO: Ajustar rect al tamaño exacto del texto AHORA
        # Con los runs correctos ya establecidos
        # Usamos force=True porque es una EDICIÓN real, no un movimiento
        text_item.adjust_rect_to_content(force=True)
        
        # Establecer la posición correcta (mantener posición original)
        text_item.setPos(current_pos_x, current_pos_y)
        
        # Borrar texto original si es necesario
        if needs_erase and not is_overlay_now and self.pdf_doc:
            internal_pdf_rect = getattr(text_item, 'internal_pdf_rect', None)
            original_pdf_rect = getattr(text_item, 'original_pdf_rect', None)
            
            rect_to_erase = internal_pdf_rect or original_pdf_rect
            if rect_to_erase:
                self.pdf_doc._save_snapshot()
                self.pdf_doc.erase_text_transparent(
                    self.current_page,
                    rect_to_erase,
                    save_snapshot=False,
                    already_internal=bool(internal_pdf_rect)
                )
        
        # Convertir a overlay
        text_item.is_overlay = True
        text_item.pending_write = True
        text_item.needs_erase = False
        
        # CRÍTICO: Limpiar internal_pdf_rect después de borrar para evitar borrados futuros
        text_item.internal_pdf_rect = None
        
        # IMPORTANTE: Actualizar pdf_rect DESPUÉS de ajustar el rect visual
        # para que refleje el tamaño real del texto ajustado
        adjusted_rect = text_item.rect()
        adjusted_scene_rect = QRectF(
            text_item.pos().x(),
            text_item.pos().y(),
            adjusted_rect.width(),
            adjusted_rect.height()
        )
        text_item.pdf_rect = self.view_to_pdf_rect(adjusted_scene_rect)
        
        # Actualizar datos guardados
        self._update_text_data(text_item)
        
        # Re-renderizar
        if needs_erase and not is_overlay_now:
            self.render_page()
        else:
            text_item.update()
        
        self.documentModified.emit()
    
    def _update_text_in_pdf(self, text_item: EditableTextItem):
        """Actualiza la posición del texto en el PDF después de moverlo.
        
        NUEVO SISTEMA SIMPLIFICADO:
        - TODO el movimiento es visual (overlay) - NUNCA se escribe al PDF durante el arrastre
        - El texto original del PDF se borra UNA SOLA VEZ (en el primer movimiento)
        - El texto se escribe al PDF solo cuando se GUARDA el documento (commit_overlay_texts)
        
        Esto evita:
        1. Duplicación (texto en PDF + overlay visual)
        2. Borrar contenido de otros textos al mover
        """
        if not text_item or not self.pdf_doc:
            return
        
        # IMPORTANTE: No procesar textos vacíos
        if not text_item.text or not text_item.text.strip():
            self._remove_empty_text_item(text_item)
            return
        
        # Calcular nueva posición PDF desde la posición visual actual
        scene_rect = text_item.sceneBoundingRect()
        new_view_rect = QRectF(scene_rect.x(), scene_rect.y(), scene_rect.width(), scene_rect.height())
        new_pdf_rect = self.view_to_pdf_rect(new_view_rect)
        
        is_overlay = getattr(text_item, 'is_overlay', False)
        needs_erase = getattr(text_item, 'needs_erase', False)
        
        # CASO 1: Ya es un overlay - actualizar posición SIN RECALCULAR TAMAÑO
        if is_overlay:
            
            # CRÍTICO: NO recalcular bounds durante movimiento
            # El tamaño ya está calculado y bloqueado - solo actualizar posición
            # text_item.adjust_rect_to_content()  # ELIMINADO - causa salto de tamaño
            
            # Obtener el rect actual (sin recalcular)
            adjusted_rect = text_item.rect()
            
            # Usar la posición actual de la escena (donde se movió) y el tamaño ajustado
            updated_pdf_rect = fitz.Rect(
                new_pdf_rect.x0,
                new_pdf_rect.y0,
                new_pdf_rect.x0 + (adjusted_rect.width() / self.zoom_level),
                new_pdf_rect.y0 + (adjusted_rect.height() / self.zoom_level)
            )
            text_item.pdf_rect = updated_pdf_rect
            
            text_item.pending_write = True
            self._update_text_data(text_item)
            # NO re-renderizar - el texto ya se mueve visualmente
            self.documentModified.emit()
            return
        
        # CASO 2: Primera vez que se mueve (viene del PDF y needs_erase=True)
        if needs_erase:
            
            # Obtener el rect correcto para borrar
            internal_pdf_rect = getattr(text_item, 'internal_pdf_rect', None)
            original_pdf_rect = getattr(text_item, 'original_pdf_rect', None)
            
            if internal_pdf_rect:
                rect_to_erase = internal_pdf_rect
                already_internal = True
            elif original_pdf_rect:
                rect_to_erase = original_pdf_rect
                already_internal = False
            else:
                print(f"     ERROR: No hay rect para borrar")
                return
            
            # Borrar el texto ORIGINAL del PDF (solo una vez)
            self.pdf_doc._save_snapshot()
            self.pdf_doc.erase_text_transparent(
                self.current_page,
                rect_to_erase,
                save_snapshot=False,
                already_internal=already_internal
            )
            
            # CRÍTICO: NO recalcular bounds durante movimiento
            # El tamaño ya está calculado - solo usar el rect actual
            # text_item.adjust_rect_to_content()  # ELIMINADO - causa salto de tamaño
            
            # Obtener el rect actual (sin recalcular)
            adjusted_rect = text_item.rect()
            
            # Usar la posición nueva y el tamaño ajustado al contenido (no el tamaño antiguo)
            updated_pdf_rect = fitz.Rect(
                new_pdf_rect.x0,
                new_pdf_rect.y0,
                new_pdf_rect.x0 + (adjusted_rect.width() / self.zoom_level),
                new_pdf_rect.y0 + (adjusted_rect.height() / self.zoom_level)
            )
            
            text_item.is_overlay = True
            text_item.pending_write = True
            text_item.needs_erase = False  # Ya borramos el original
            text_item.pdf_rect = updated_pdf_rect
            # CRÍTICO: Limpiar internal_pdf_rect para evitar borrados futuros
            text_item.internal_pdf_rect = None
            
            self._update_text_data(text_item)
            self.render_page()  # Re-renderizar para mostrar el PDF sin el texto original
            self.documentModified.emit()
            return
        
        # CASO 3: Texto que YA FUE ESCRITO al PDF (después de guardar) y se mueve de nuevo
        # CRÍTICO: Necesitamos borrar la posición ACTUAL (donde está en el PDF)
        # porque el texto ya fue escrito ahí previamente
        
        # Obtener la posición actual donde el texto está escrito en el PDF
        current_pdf_rect = getattr(text_item, 'pdf_rect', None)
        
        if current_pdf_rect and self.pdf_doc:
            print(f"     CASO 3: Texto ya escrito al PDF, borrando posición actual")
            
            # Borrar el texto de su posición actual en el PDF
            self.pdf_doc._save_snapshot()
            self.pdf_doc.erase_text_transparent(
                self.current_page,
                current_pdf_rect,
                save_snapshot=False,
                already_internal=False
            )
        
        # CRÍTICO: NO recalcular bounds durante movimiento - usar rect actual
        # text_item.adjust_rect_to_content()  # ELIMINADO - causa salto de tamaño
        adjusted_rect = text_item.rect()
        updated_pdf_rect = fitz.Rect(
            new_pdf_rect.x0,
            new_pdf_rect.y0,
            new_pdf_rect.x0 + (adjusted_rect.width() / self.zoom_level),
            new_pdf_rect.y0 + (adjusted_rect.height() / self.zoom_level)
        )
        
        text_item.is_overlay = True
        text_item.pending_write = True
        text_item.pdf_rect = updated_pdf_rect
        self._update_text_data(text_item)
        
        # Re-renderizar para mostrar el PDF sin el texto en la posición anterior
        if current_pdf_rect:
            self.render_page()
        
        self.documentModified.emit()
    
    def _remove_empty_text_item(self, text_item: EditableTextItem):
        """Elimina un item de texto vacío de la escena y de los datos, borrando el texto original del PDF si es necesario."""
        self._delete_text_item(text_item, is_empty=True)
    
    def _delete_text_item(self, text_item: EditableTextItem, is_empty: bool = False, skip_render: bool = False):
        """Elimina un item de texto de la escena y de los datos.
        
        Args:
            text_item: El item de texto a eliminar
            is_empty: True si se está eliminando porque el texto está vacío
            skip_render: Si True, no re-renderiza la página (útil para eliminación múltiple)
        """
        # IMPORTANTE: Si el item viene del PDF y necesita borrado, borrar el texto original PRIMERO
        needs_erase = getattr(text_item, 'needs_erase', False)
        original_pdf_rect = getattr(text_item, 'original_pdf_rect', None)
        internal_pdf_rect = getattr(text_item, 'internal_pdf_rect', None)
        is_overlay = getattr(text_item, 'is_overlay', False)
        
        # Si es un texto del PDF que no ha sido movido (needs_erase=True), borrar del PDF
        if needs_erase and not is_overlay:
            rect_to_erase = internal_pdf_rect or original_pdf_rect
            if rect_to_erase:
                try:
                    if self.pdf_doc:
                        self.pdf_doc._save_snapshot()
                        self.pdf_doc.erase_text_transparent(
                            self.current_page,
                            rect_to_erase,
                            save_snapshot=False,
                            already_internal=bool(internal_pdf_rect)
                        )
                except Exception as e:
                    print(f"  Error al borrar texto original: {e}")
        
        # Eliminar de la lista de items gráficos
        if text_item in self.editable_text_items:
            self.editable_text_items.remove(text_item)
        
        # Eliminar de la escena
        if text_item.scene():
            self.scene.removeItem(text_item)
        
        # Eliminar de los datos guardados usando data_index
        data_index = getattr(text_item, 'data_index', None)
        page_data = self.editable_texts_data.get(self.current_page, [])
        
        if data_index is not None and 0 <= data_index < len(page_data):
            del page_data[data_index]
            # Reindexar los items restantes
            for i, item in enumerate(self.editable_text_items):
                if hasattr(item, 'data_index') and item.data_index > data_index:
                    item.data_index -= 1
        
        # Deseleccionar si estaba seleccionado
        if self.selected_text_item == text_item:
            self.selected_text_item = None
        
        # Renderizar la página para mostrar los cambios (si no se omite)
        if not skip_render:
            self.render_page()
            # Emitir señal de documento modificado
            self.documentModified.emit()
    
    def _delete_selected_text(self):
        """Elimina el texto actualmente seleccionado después de confirmación."""
        if not self.selected_text_item:
            return
        
        text_item = self.selected_text_item
        text_preview = text_item.text[:50] + "..." if len(text_item.text) > 50 else text_item.text
        
        # Diálogo de confirmación
        msg = QMessageBox(self)
        msg.setWindowTitle('Eliminar texto')
        msg.setIcon(QMessageBox.Warning)
        msg.setText('<b>¿Eliminar este texto?</b>')
        msg.setInformativeText(f'<span style="color: #ff5555;">"{text_preview}"</span>')
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        msg.button(QMessageBox.Yes).setText('🗑️ Eliminar')
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
        
        if msg.exec_() == QMessageBox.Yes:
            self._delete_text_item(text_item, is_empty=False)
    
    def _delete_text_item_with_confirmation(self, text_item: EditableTextItem):
        """Elimina un texto específico después de confirmación (usado desde menú contextual)."""
        if not text_item:
            return
        
        text_preview = text_item.text[:50] + "..." if len(text_item.text) > 50 else text_item.text
        
        # Diálogo de confirmación
        msg = QMessageBox(self)
        msg.setWindowTitle('Eliminar texto')
        msg.setIcon(QMessageBox.Warning)
        msg.setText('<b>¿Eliminar este texto?</b>')
        msg.setInformativeText(f'<span style="color: #ff5555;">"{text_preview}"</span>')
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        msg.button(QMessageBox.Yes).setText('🗑️ Eliminar')
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
        
        if msg.exec_() == QMessageBox.Yes:
            self._delete_text_item(text_item, is_empty=False)

    def _update_text_data(self, text_item: EditableTextItem):
        """Actualiza los datos guardados del texto usando el índice directo."""
        page_data = self.editable_texts_data.get(self.current_page, [])
        
        # Usar data_index si está disponible (método más confiable)
        data_index = getattr(text_item, 'data_index', None)
        
        # Obtener el rectángulo visual completo (posición + tamaño)
        scene_rect = text_item.sceneBoundingRect()
        
        # Para overlays: calcular tamaño basado en QFontMetrics para evitar recortes
        is_overlay = getattr(text_item, 'is_overlay', False)
        if is_overlay and text_item.text:
            font = QFont("Helvetica", int(text_item.font_size))
            if getattr(text_item, 'is_bold', False):
                font.setBold(True)
            metrics = QFontMetrics(font)
            
            # FIX: Calcular correctamente para texto multilínea
            lines = text_item.text.split('\n')
            max_line_width = 0
            for line in lines:
                line_width = metrics.horizontalAdvance(line)
                max_line_width = max(max_line_width, line_width)
            
            text_width = max_line_width + 10  # padding
            text_height = metrics.height() * len(lines) + 4  # altura por cada línea + padding
            
            # Usar el tamaño máximo entre el actual y el calculado
            view_rect = QRectF(
                scene_rect.x(),
                scene_rect.y(),
                max(scene_rect.width(), text_width),
                max(scene_rect.height(), text_height)
            )
        else:
            view_rect = QRectF(scene_rect.x(), scene_rect.y(), scene_rect.width(), scene_rect.height())
        
        if data_index is not None and 0 <= data_index < len(page_data):
            # Actualización directa por índice
            data = page_data[data_index]
            # DEBUG: Verificar text_runs antes de guardar
            current_text_runs = getattr(text_item, 'text_runs', None)
            data['text'] = text_item.text
            data['pdf_rect'] = text_item.pdf_rect
            data['view_rect'] = view_rect
            data['font_size'] = text_item.font_size
            data['font_name'] = getattr(text_item, 'font_name', 'helv')
            data['is_bold'] = getattr(text_item, 'is_bold', False)
            # CRÍTICO: Preservar color al mover
            data['color'] = getattr(text_item, 'text_color', (0, 0, 0))
            data['needs_erase'] = getattr(text_item, 'needs_erase', False)
            data['original_pdf_rect'] = getattr(text_item, 'original_pdf_rect', None)
            data['internal_pdf_rect'] = getattr(text_item, 'internal_pdf_rect', None)
            data['is_overlay'] = getattr(text_item, 'is_overlay', False)
            data['pending_write'] = getattr(text_item, 'pending_write', False)
            # CRÍTICO: Preservar text_runs y has_mixed_styles para mantener estilos al mover
            data['text_runs'] = getattr(text_item, 'text_runs', None)
            data['has_mixed_styles'] = getattr(text_item, 'has_mixed_styles', False)
            return
        
        # Fallback: buscar por posición PDF si no hay índice válido
        for i, data in enumerate(page_data):
            data_rect = data.get('pdf_rect')
            item_rect = text_item.pdf_rect
            
            if (data_rect and item_rect and 
                abs(data_rect.x0 - item_rect.x0) < 5 and 
                abs(data_rect.y0 - item_rect.y0) < 5):
                data['text'] = text_item.text
                data['pdf_rect'] = text_item.pdf_rect
                data['view_rect'] = view_rect
                data['font_size'] = text_item.font_size
                data['font_name'] = getattr(text_item, 'font_name', 'helv')
                data['is_bold'] = getattr(text_item, 'is_bold', False)
                # CRÍTICO: Preservar color al mover
                data['color'] = getattr(text_item, 'text_color', (0, 0, 0))
                data['needs_erase'] = getattr(text_item, 'needs_erase', False)
                data['original_pdf_rect'] = getattr(text_item, 'original_pdf_rect', None)
                data['internal_pdf_rect'] = getattr(text_item, 'internal_pdf_rect', None)
                data['is_overlay'] = getattr(text_item, 'is_overlay', False)
                data['pending_write'] = getattr(text_item, 'pending_write', False)
                # CRÍTICO: Preservar text_runs y has_mixed_styles para mantener estilos al mover
                data['text_runs'] = getattr(text_item, 'text_runs', None)
                data['has_mixed_styles'] = getattr(text_item, 'has_mixed_styles', False)
                text_item.data_index = i  # Actualizar el índice para futuras operaciones
                return
    
    def _clean_empty_texts(self, page_num: int = None):
        """
        Elimina los registros de textos vacíos de editable_texts_data.
        
        Args:
            page_num: Página específica a limpiar, o None para limpiar todas
        """
        if page_num is not None:
            # Limpiar solo una página
            if page_num in self.editable_texts_data:
                original_count = len(self.editable_texts_data[page_num])
                self.editable_texts_data[page_num] = [
                    data for data in self.editable_texts_data[page_num]
                    if data.get('text') and data.get('text').strip()
                ]
                removed = original_count - len(self.editable_texts_data[page_num])
                # Textos vacíos eliminados silenciosamente
        else:
            # Limpiar todas las páginas
            for pnum in list(self.editable_texts_data.keys()):
                self._clean_empty_texts(pnum)
    
    def _restore_editable_texts_for_page(self):
        """Restaura los items editables para la página actual después de re-renderizar."""
        # Primero limpiar textos vacíos de los datos
        self._clean_empty_texts(self.current_page)
        
        # Limpiar la lista de items gráficos (ya fueron eliminados por scene.clear())
        self.editable_text_items = []
        self.selected_text_item = None
        
        # Recrear los items gráficos desde los datos guardados
        page_data = self.editable_texts_data.get(self.current_page, [])
        
        for i, text_data in enumerate(page_data):
            # Doble verificación: ignorar textos vacíos
            text_content = text_data.get('text', '')
            if not text_content or not text_content.strip():
                continue
            
            is_overlay = text_data.get('is_overlay', False)
            font_size = text_data.get('font_size', 12)
            is_bold = text_data.get('is_bold', False)
            
            # Calcular view_rect
            saved_view_rect = text_data.get('view_rect')
            
            # Para overlays: usar el view_rect guardado si está disponible
            # ya que tiene el tamaño correcto calculado cuando se editó/movió
            if is_overlay and saved_view_rect and isinstance(saved_view_rect, QRectF):
                # Usar el view_rect guardado directamente
                view_rect = saved_view_rect
            elif text_data.get('pdf_rect'):
                # Obtener posición desde pdf_rect
                base_view_rect = self.pdf_to_view_rect(text_data['pdf_rect'])
                
                # Para overlays: calcular tamaño basado en métricas de Qt para evitar recorte
                if is_overlay:
                    font = QFont("Helvetica", int(font_size))
                    if is_bold:
                        font.setBold(True)
                    metrics = QFontMetrics(font)
                    
                    # FIX: Calcular correctamente para texto multilínea
                    lines = text_content.split('\n')
                    max_line_width = 0
                    for line in lines:
                        line_width = metrics.horizontalAdvance(line)
                        max_line_width = max(max_line_width, line_width)
                    
                    text_width = max_line_width + 10  # padding
                    text_height = metrics.height() * len(lines) + 4  # altura por cada línea + padding
                    
                    # Para overlays: SIEMPRE usar EXACTAMENTE el tamaño calculado por Qt
                    # No usar max() porque eso puede causar fragmentación
                    view_rect = QRectF(
                        base_view_rect.x(),
                        base_view_rect.y(),
                        text_width,
                        text_height
                    )
                else:
                    view_rect = base_view_rect
                
                text_data['view_rect'] = view_rect
            else:
                view_rect = saved_view_rect if saved_view_rect else QRectF(0, 0, 100, 20)
            
            # CRÍTICO: Extraer posición y crear rect normalizado (0, 0, w, h)
            # La posición se establece con setPos(), no en el rect
            pos_x = view_rect.x()
            pos_y = view_rect.y()
            normalized_rect = QRectF(0, 0, view_rect.width(), view_rect.height())
            
            text_item = EditableTextItem(
                normalized_rect,  # Rect normalizado sin posición
                text_data['text'],
                font_size,
                text_data.get('color', (0, 0, 0)),
                self.current_page,
                font_name=text_data.get('font_name', 'helv'),
                is_bold=is_bold,
                zoom_level=self.zoom_level,  # Pasar zoom para escalar al dibujar
                line_spacing=text_data.get('line_spacing', 0.0)  # Interlineado del PDF
            )
            
            # CRÍTICO: Establecer la posición del item
            text_item.setPos(pos_x, pos_y)
            
            text_item.pdf_rect = text_data.get('pdf_rect')
            # Restaurar también los nuevos campos
            text_item.original_pdf_rect = text_data.get('original_pdf_rect')
            text_item.internal_pdf_rect = text_data.get('internal_pdf_rect')
            text_item.needs_erase = text_data.get('needs_erase', False)
            text_item.is_overlay = is_overlay
            text_item.pending_write = text_data.get('pending_write', False)
            text_item.data_index = i  # Asignar índice para poder actualizar datos después
            # CRÍTICO: Restaurar text_runs y has_mixed_styles para mantener estilos
            text_item.text_runs = text_data.get('text_runs', None)
            text_item.has_mixed_styles = text_data.get('has_mixed_styles', False)
            # Guardar tamaño original para poder escalar al editar
            text_item._original_font_size = font_size
            
            # CRÍTICO: Para overlays, NO recalcular - ya tienen el tamaño correcto guardado
            # Solo recalcular para textos que vienen del PDF original (no overlays)
            if is_overlay:
                # El view_rect ya tiene el tamaño correcto - marcar como finalizado
                text_item._bounds_finalized = True
                text_item.lock_bounds()  # Bloquear para evitar recálculos
            else:
                # Textos del PDF original - ajustar caja al contenido
                text_item.adjust_rect_to_content()
            
            self.editable_text_items.append(text_item)
            self.scene.addItem(text_item)
    
    def commit_overlay_texts(self) -> bool:
        """
        Escribe todos los textos overlay pendientes al PDF.
        Debe llamarse antes de guardar el documento.
        
        Para textos que fueron movidos desde otra posición (tienen original_pdf_rect),
        primero se cubre la posición original con una redacción/borrado.
        
        Soporta textos con múltiples runs (diferentes estilos en el mismo bloque).
        
        Returns:
            True si todos los textos se escribieron correctamente
        """
        print("\n=== COMMIT OVERLAY TEXTS ===")
        
        if not self.pdf_doc:
            print("No hay pdf_doc, retornando True")
            return True
        
        # Validación pre-guardado con el integrador (si está disponible)
        is_valid, warnings, errors = self._validate_before_save()
        if warnings:
            print(f"Advertencias de validación: {warnings}")
        if errors:
            print(f"Errores de validación: {errors}")
            # Solo informativo, no bloquea el guardado
        
        success_count = 0
        error_count = 0
        total_processed = 0
        
        # Recorrer todas las páginas con textos
        for page_num, page_texts in self.editable_texts_data.items():
            for text_data in page_texts:
                # Solo procesar textos overlay pendientes
                if text_data.get('is_overlay') and text_data.get('pending_write'):
                    total_processed += 1
                    print(f"\nProcesando overlay en página {page_num}: '{text_data.get('text', '')[:30]}'...")
                    
                    pdf_rect = text_data.get('pdf_rect')
                    if not pdf_rect:
                        print(f"    ERROR: No hay pdf_rect")
                        error_count += 1
                        continue
                    
                    # Si el texto fue movido desde otra posición, cubrir la posición original
                    original_rect = text_data.get('original_pdf_rect')
                    if original_rect:
                        try:
                            self.pdf_doc.erase_text_transparent(
                                page_num,
                                original_rect,
                                save_snapshot=False
                            )
                            print(f"    ✓ Posición original cubierta")
                        except Exception as e:
                            print(f"    Advertencia: No se pudo cubrir posición original: {e}")
                        text_data['original_pdf_rect'] = None
                    
                    # Verificar si tiene múltiples runs con estilos
                    text_runs = text_data.get('text_runs', [])
                    has_mixed_styles = text_data.get('has_mixed_styles', False)
                    
                    if has_mixed_styles and text_runs and len(text_runs) > 1:
                        # Escribir cada run con su estilo individual
                        result = self.pdf_doc.add_text_runs_to_page(
                            page_num,
                            pdf_rect,
                            text_runs,
                            save_snapshot=False
                        )
                        print(f"    Escribiendo {len(text_runs)} runs con estilos mixtos")
                    else:
                        # Escribir texto simple
                        result = self.pdf_doc.add_text_to_page(
                            page_num,
                            pdf_rect,
                            text_data['text'],
                            font_size=text_data.get('font_size', 12),
                            color=text_data.get('color', (0, 0, 0)),
                            is_bold=text_data.get('is_bold', False),
                            save_snapshot=False
                        )
                    
                    if result:
                        # CRÍTICO: Después de escribir al PDF, el texto ya NO es overlay
                        # Si se mueve de nuevo, HAY QUE BORRAR donde está escrito
                        text_data['is_overlay'] = False
                        text_data['pending_write'] = False
                        text_data['needs_erase'] = True  # Si se mueve, borrar del PDF
                        
                        # CRÍTICO: Calcular rect preciso para borrado futuro
                        # Basado en el texto real escrito, no en el rect expandido
                        text_content = text_data.get('text', '')
                        font_size = text_data.get('font_size', 12)
                        lines = text_content.split('\n')
                        num_lines = len(lines)
                        max_chars = max(len(line) for line in lines) if lines else 0
                        
                        # Estimar rect basado en texto (más conservador)
                        # ~6 puntos por carácter, altura de línea ~1.2 * font_size
                        estimated_width = max_chars * font_size * 0.6 + 10
                        estimated_height = num_lines * font_size * 1.3 + 5
                        
                        precise_rect = fitz.Rect(
                            pdf_rect.x0,
                            pdf_rect.y0,
                            pdf_rect.x0 + estimated_width,
                            pdf_rect.y0 + estimated_height
                        )
                        text_data['internal_pdf_rect'] = precise_rect
                        success_count += 1
                        print(f"    ✓ Texto escrito al PDF en {precise_rect} (preciso)")
                    else:
                        print(f"    ERROR al escribir texto al PDF")
                        error_count += 1
        
        # CRÍTICO: Actualizar los EditableTextItems en escena con los nuevos valores
        # para que al mover sepan que hay que borrar del PDF
        for item in self.scene.items():
            if isinstance(item, EditableTextItem):
                data_index = getattr(item, 'data_index', None)
                page_data = self.editable_texts_data.get(self.current_page, [])
                if data_index is not None and 0 <= data_index < len(page_data):
                    data = page_data[data_index]
                    item.is_overlay = data.get('is_overlay', False)
                    item.pending_write = data.get('pending_write', False)
                    item.needs_erase = data.get('needs_erase', False)
                    item.internal_pdf_rect = data.get('internal_pdf_rect')
        
        print(f"\n=== RESULTADO COMMIT ===")
        print(f"Total procesados: {total_processed}")
        print(f"Exitosos: {success_count}")
        print(f"Errores: {error_count}")
        
        return error_count == 0
    
    def has_pending_overlays(self) -> bool:
        """Verifica si hay textos overlay pendientes de escribir."""
        for page_texts in self.editable_texts_data.values():
            for text_data in page_texts:
                if text_data.get('is_overlay') and text_data.get('pending_write'):
                    return True
        return False
    
    def sync_all_text_items_to_data(self):
        """
        Sincroniza TODOS los items visuales de texto con editable_texts_data.
        Asegura que los datos estén actualizados con el estado visual.
        Esto es crítico antes de guardar para no perder cambios.
        """
        print("\n=== SINCRONIZACIÓN DE TEXTOS VISUALES ===")
        synced_count = 0
        
        # Recorrer todos los items de la escena actual
        for item in self.scene.items():
            if isinstance(item, EditableTextItem):
                # Asegurarse que este item tiene los datos actualizados
                self._update_text_data(item)
                synced_count += 1
        
        # Verificar estado de overlays pendientes
        pending_count = 0
        for page_texts in self.editable_texts_data.values():
            for text_data in page_texts:
                if text_data.get('is_overlay') and text_data.get('pending_write'):
                    pending_count += 1
        
        print(f"Items sincronizados: {synced_count}")
        print(f"Overlays pendientes de escribir: {pending_count}")

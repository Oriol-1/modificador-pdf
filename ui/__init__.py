"""Módulo de interfaz de usuario del editor de PDF."""
from .main_window import MainWindow
from .pdf_viewer import PDFPageView
from .thumbnail_panel import ThumbnailPanel
from .toolbar import EditorToolBar
from .graphics_items import (
    SelectionRect, DeletePreviewRect, FloatingLabel, 
    HighlightRect, TextEditDialog, EditableTextItem
)

__all__ = [
    'MainWindow', 'PDFPageView', 'ThumbnailPanel', 'EditorToolBar',
    'SelectionRect', 'DeletePreviewRect', 'FloatingLabel',
    'HighlightRect', 'TextEditDialog', 'EditableTextItem'
]

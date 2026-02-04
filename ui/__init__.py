"""Módulo de interfaz de usuario del editor de PDF."""
from .main_window import MainWindow
from .pdf_viewer import PDFPageView
from .thumbnail_panel import ThumbnailPanel
from .toolbar import EditorToolBar
from .graphics_items import (
    SelectionRect, DeletePreviewRect, FloatingLabel, 
    HighlightRect, TextEditDialog, EditableTextItem
)
from .coordinate_utils import CoordinateConverter
from .font_dialog import FontDialog, TextFormatDialog, FontPreviewWidget, ColorButton
from .summary_dialog import SummaryDialog, QuickStatsWidget, StatWidget

__all__ = [
    'MainWindow', 'PDFPageView', 'ThumbnailPanel', 'EditorToolBar',
    'SelectionRect', 'DeletePreviewRect', 'FloatingLabel',
    'HighlightRect', 'TextEditDialog', 'EditableTextItem',
    'CoordinateConverter',
    'FontDialog', 'TextFormatDialog', 'FontPreviewWidget', 'ColorButton',
    'SummaryDialog', 'QuickStatsWidget', 'StatWidget'
]

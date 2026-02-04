"""Módulo core del editor de PDF."""
from .models import TextBlock, EditOperation
from .pdf_handler import PDFDocument
from .logger import (
    DEBUG_NONE, DEBUG_RENDER, DEBUG_COORDS, DEBUG_EDIT, 
    DEBUG_UNDO, DEBUG_SELECTION, DEBUG_OVERLAY, DEBUG_ALL,
    set_debug_level, get_debug_level,
    debug_print, debug_render, debug_coords, debug_edit,
    debug_undo, debug_selection, debug_overlay
)
from .change_report import (
    ChangeType, ChangePosition, FontInfo, Change, ChangeReport,
    get_change_report, reset_change_report
)

__all__ = [
    'PDFDocument', 'TextBlock', 'EditOperation',
    'DEBUG_NONE', 'DEBUG_RENDER', 'DEBUG_COORDS', 'DEBUG_EDIT',
    'DEBUG_UNDO', 'DEBUG_SELECTION', 'DEBUG_OVERLAY', 'DEBUG_ALL',
    'set_debug_level', 'get_debug_level',
    'debug_print', 'debug_render', 'debug_coords', 'debug_edit',
    'debug_undo', 'debug_selection', 'debug_overlay',
    'ChangeType', 'ChangePosition', 'FontInfo', 'Change', 'ChangeReport',
    'get_change_report', 'reset_change_report'
]

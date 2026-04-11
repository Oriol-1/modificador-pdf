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
from .unified_text_editor import (
    UnifiedTextEditorDialog, SpanEditWidget, show_unified_editor
)
from .property_inspector import (
    PropertyInspector, CollapsibleSection, ColorSwatch,
    Property, PropertyType, create_property_inspector_dock
)
from .text_properties_tooltip import (
    TextPropertiesTooltip, TooltipConfig, TooltipStyle,
    format_span_tooltip, format_line_tooltip, create_text_properties_tooltip
)
from .text_selection_overlay import (
    TextSelectionOverlay, SelectionMode, SelectionStyle, SelectionConfig,
    MetricIndicator, SpanSelectionItem, LineSelectionItem,
    create_selection_overlay, create_dark_theme_style, create_light_theme_style
)
from .pdf_text_editor import (
    PDFTextEditor, PDFTextEditorDialog, EditMode, FitStatus,
    EditedSpan, EditorConfig, MetricsStatusBar, SpanComparisonWidget,
    EditorToolBar as PDFEditorToolBar, TextEditArea,
    create_pdf_text_editor, show_pdf_text_editor
)

from .fit_validator import (
    FitValidationStatus, SuggestionType, FitMetrics, FitSuggestion,
    FitValidationResult, FitValidatorConfig, FitValidator,
    FitStatusIndicator, FitValidationPanel,
    create_fit_validator, validate_text_fit, quick_fit_check,
    create_fit_status_indicator, create_fit_validation_panel
)


__all__ = [
    'MainWindow', 'PDFPageView', 'ThumbnailPanel', 'EditorToolBar',
    'SelectionRect', 'DeletePreviewRect', 'FloatingLabel',
    'HighlightRect', 'TextEditDialog', 'EditableTextItem',
    'CoordinateConverter',
    'FontDialog', 'TextFormatDialog', 'FontPreviewWidget', 'ColorButton',
    'SummaryDialog', 'QuickStatsWidget', 'StatWidget',

    # Phase 3C: Property Inspector
    'PropertyInspector', 'CollapsibleSection', 'ColorSwatch',
    'Property', 'PropertyType', 'create_property_inspector_dock',
    # Phase 3C-03: Text Properties Tooltip
    'TextPropertiesTooltip', 'TooltipConfig', 'TooltipStyle',
    'format_span_tooltip', 'format_line_tooltip', 'create_text_properties_tooltip',
    # Phase 3C-04: Text Selection Overlay
    'TextSelectionOverlay', 'SelectionMode', 'SelectionStyle', 'SelectionConfig',
    'MetricIndicator', 'SpanSelectionItem', 'LineSelectionItem',
    'create_selection_overlay', 'create_dark_theme_style', 'create_light_theme_style',
    # Phase 3C-05: PDF Text Editor
    'PDFTextEditor', 'PDFTextEditorDialog', 'EditMode', 'FitStatus',
    'EditedSpan', 'EditorConfig', 'MetricsStatusBar', 'SpanComparisonWidget',
    'PDFEditorToolBar', 'TextEditArea',
    'create_pdf_text_editor', 'show_pdf_text_editor',

    # Phase 3C-07: Fit Validator
    'FitValidationStatus', 'SuggestionType', 'FitMetrics', 'FitSuggestion',
    'FitValidationResult', 'FitValidatorConfig', 'FitValidator',
    'FitStatusIndicator', 'FitValidationPanel',
    'create_fit_validator', 'validate_text_fit', 'quick_fit_check',
    'create_fit_status_indicator', 'create_fit_validation_panel',
    # UnifiedTextEditor
    'UnifiedTextEditorDialog', 'SpanEditWidget', 'show_unified_editor',
]

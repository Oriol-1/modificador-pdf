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
from .text_editor_dialog import (
    EnhancedTextEditDialog, TextEditResult, TextPreviewWidget,
    FitStatusWidget, AdjustmentOptionsWidget, show_text_edit_dialog
)
from .rich_text_editor import (
    RichTextEditDialog, RichTextEditor, RichTextPreview,
    TextRun, TextBlock, show_rich_text_editor
)
from .word_like_editor import (
    WordLikeEditorDialog, WordLikeToolBar, RichDocumentEditor,
    TextRunInfo, DocumentStructure, show_word_like_editor
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
from .no_reflow_editor import (
    OverflowStrategy, BboxDisplayMode, BboxConstraints, AdjustmentResult,
    NoReflowConfig, BboxOverlay, FitIndicatorWidget, TrackingAdjuster,
    SizeAdjuster, HorizontalScaleAdjuster, OverflowOptionsPanel,
    NoReflowEditorPanel, TextFitCalculator,
    create_no_reflow_panel, calculate_best_fit
)
from .fit_validator import (
    FitValidationStatus, SuggestionType, FitMetrics, FitSuggestion,
    FitValidationResult, FitValidatorConfig, FitValidator,
    FitStatusIndicator, FitValidationPanel,
    create_fit_validator, validate_text_fit, quick_fit_check,
    create_fit_status_indicator, create_fit_validation_panel
)
from .adjustment_options import (
    AdjustmentMode, PreviewQuality, AdjustmentPreset, AdjustmentState,
    BUILTIN_PRESETS, AdjustmentPreviewWidget, TrackingSlider, SizeSlider,
    ScaleSlider, PresetSelector, ModeSelector, AdjustmentControlsPanel,
    TruncationPanel, AdjustmentOptionsDialog,
    create_adjustment_dialog, show_adjustment_dialog, create_adjustment_controls,
    create_preset_selector, get_builtin_presets
)

__all__ = [
    'MainWindow', 'PDFPageView', 'ThumbnailPanel', 'EditorToolBar',
    'SelectionRect', 'DeletePreviewRect', 'FloatingLabel',
    'HighlightRect', 'TextEditDialog', 'EditableTextItem',
    'CoordinateConverter',
    'FontDialog', 'TextFormatDialog', 'FontPreviewWidget', 'ColorButton',
    'SummaryDialog', 'QuickStatsWidget', 'StatWidget',
    'EnhancedTextEditDialog', 'TextEditResult', 'TextPreviewWidget',
    'FitStatusWidget', 'AdjustmentOptionsWidget', 'show_text_edit_dialog',
    'RichTextEditDialog', 'RichTextEditor', 'RichTextPreview',
    'TextRun', 'TextBlock', 'show_rich_text_editor',
    'WordLikeEditorDialog', 'WordLikeToolBar', 'RichDocumentEditor',
    'TextRunInfo', 'DocumentStructure', 'show_word_like_editor',
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
    # Phase 3C-06: No-Reflow Editor
    'OverflowStrategy', 'BboxDisplayMode', 'BboxConstraints', 'AdjustmentResult',
    'NoReflowConfig', 'BboxOverlay', 'FitIndicatorWidget', 'TrackingAdjuster',
    'SizeAdjuster', 'HorizontalScaleAdjuster', 'OverflowOptionsPanel',
    'NoReflowEditorPanel', 'TextFitCalculator',
    'create_no_reflow_panel', 'calculate_best_fit',
    # Phase 3C-07: Fit Validator
    'FitValidationStatus', 'SuggestionType', 'FitMetrics', 'FitSuggestion',
    'FitValidationResult', 'FitValidatorConfig', 'FitValidator',
    'FitStatusIndicator', 'FitValidationPanel',
    'create_fit_validator', 'validate_text_fit', 'quick_fit_check',
    'create_fit_status_indicator', 'create_fit_validation_panel',
    # Phase 3C-08: Adjustment Options
    'AdjustmentMode', 'PreviewQuality', 'AdjustmentPreset', 'AdjustmentState',
    'BUILTIN_PRESETS', 'AdjustmentPreviewWidget', 'TrackingSlider', 'SizeSlider',
    'ScaleSlider', 'PresetSelector', 'ModeSelector', 'AdjustmentControlsPanel',
    'TruncationPanel', 'AdjustmentOptionsDialog',
    'create_adjustment_dialog', 'show_adjustment_dialog', 'create_adjustment_controls',
    'create_preset_selector', 'get_builtin_presets',
]

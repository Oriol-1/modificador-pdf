"""
PDF Text Engine - Motor de extracción y análisis de texto de PDF.

Este módulo proporciona herramientas avanzadas para:
- Extraer propiedades tipográficas completas de spans de texto
- Agrupar texto en líneas y párrafos
- Detectar espaciado, interlineado y estructura
- Preservar métricas originales al editar
- Manejar transformaciones de texto (matrices CTM y Tm)
- Mapear y analizar espacios en texto PDF

Componentes principales:
- TextSpanMetrics: Métricas completas de un span de texto
- TextLine: Agrupación de spans en líneas
- TextParagraph: Agrupación de líneas en párrafos con detección de tipos
- LineGrouper: Algoritmo de agrupación de spans
- ParagraphDetector: Algoritmo de detección de párrafos y tipos
- SpaceMapper: Análisis y mapeo de espacios en texto
- TransformMatrix: Operaciones con matrices de transformación
- ContentStreamParser: Parser de operadores PDF
- BaselineTracker: Rastreo de líneas base e interlineado
- EmbeddedFontExtractor: Extracción de fuentes embebidas
"""

from .text_span import (
    TextSpanMetrics,
    RenderMode,
    FontEmbeddingStatus,
    create_span_from_pymupdf,
    create_empty_span,
)

from .content_stream_parser import (
    TextOperator,
    TextState,
    TextShowOperation,
    ParsedTextBlock,
    ContentStreamParser,
    parse_content_stream,
    extract_text_state_from_page,
    get_spacing_info_for_text,
)

from .transform_matrix import (
    TransformMatrix,
    TransformationType,
    TextTransformInfo,
    matrix_from_pdf_array,
    compose_matrices,
    interpolate_matrices,
    extract_rotation_angle,
    create_text_matrix,
)

from .text_line import (
    TextLine,
    LineGrouper,
    LineGroupingConfig,
    ReadingDirection,
    LineAlignment,
    group_spans_into_lines,
    find_line_at_point,
    calculate_line_statistics,
)

from .text_paragraph import (
    TextParagraph,
    ParagraphType,
    ParagraphAlignment,
    ListType,
    ListMarkerInfo,
    ParagraphStyle,
    ParagraphDetectionConfig,
    ParagraphDetector,
    group_lines_into_paragraphs,
    find_paragraph_at_point,
    find_paragraphs_in_region,
    calculate_paragraph_statistics,
    merge_paragraphs,
    split_paragraph_at_line,
)

from .space_mapper import (
    SpaceType,
    SpaceInfo,
    WordBoundary,
    SpaceAnalysis,
    SpaceMapperConfig,
    SpaceMapper,
    analyze_line_spacing,
    reconstruct_line_text,
    count_words_in_line,
    estimate_character_positions,
    find_char_at_x,
    calculate_space_metrics,
)

from .baseline_tracker import (
    LeadingType,
    AlignmentGrid,
    BaselineInfo,
    ParagraphBreak,
    BaselineAnalysis,
    LeadingAnalysis,
    BaselineTrackerConfig,
    BaselineTracker,
    analyze_page_baselines,
    calculate_leading,
    snap_to_grid,
    generate_baseline_grid,
    estimate_baseline_from_bbox,
    classify_leading_type,
    find_paragraph_breaks_in_baselines,
    validate_baseline_consistency,
)

from .embedded_font_extractor import (
    FontType,
    EmbeddingStatus,
    FontEncoding,
    FontMetrics,
    GlyphInfo,
    FontInfo,
    FontExtractorConfig,
    EmbeddedFontExtractor,
    extract_font_info,
    is_font_embedded,
    is_subset_font,
    get_clean_font_name,
    get_font_type_from_name,
    calculate_text_width_simple,
    list_embedded_fonts,
    list_subset_fonts,
    get_font_embedding_status,
)

from .text_hit_tester import (
    HitType,
    HitTestResult,
    PageTextCache,
    TextHitTester,
    create_hit_tester,
    hit_test_point,
    get_span_at_point,
    get_line_at_point,
)

from .safe_text_rewriter import (
    OverlayStrategy,
    RewriteMode,
    OverlayType,
    RewriteStatus,
    OverlayLayer,
    TextOverlayInfo,
    RewriteResult,
    RewriterConfig,
    ZOrderManager,
    SafeTextRewriter,
    create_safe_rewriter,
    rewrite_text_safe,
    get_recommended_strategy,
)

from .object_substitution import (
    SubstitutionType,
    SubstitutionStatus,
    MatchStrategy,
    TextLocation,
    TextSubstitution,
    SubstitutionResult,
    SubstitutorConfig,
    PDFTextEncoder,
    ContentStreamModifier,
    ObjectSubstitutor,
    create_substitutor,
    substitute_text_in_page,
    get_recommended_substitution_type,
)

from .z_order_manager import (
    LayerLevel,
    CollisionType,
    ReorderOperation,
    LayerInfo,
    CollisionInfo,
    LayerGroup,
    ReorderHistoryEntry,
    ZOrderConfig,
    AdvancedZOrderManager,
    create_z_order_manager,
    get_layer_level_for_type,
    resolve_z_order_conflict,
)

from .glyph_width_preserver import (
    FitStrategy,
    FitResult,
    AdjustmentType,
    WidthUnit,
    GlyphWidth,
    TextWidthInfo,
    SpacingAdjustment,
    FitAnalysis,
    PreserverConfig,
    TJArrayEntry,
    GlyphWidthPreserver,
    create_width_preserver,
    calculate_text_width,
    fit_text_to_width,
    get_spacing_adjustment,
)

from .pre_save_validator import (
    ValidationSeverity,
    ValidationCategory,
    ValidationResult,
    ContentIssueType,
    FontIssueType,
    StructureIssueType,
    ValidationIssue,
    ValidationReport,
    ValidatorConfig,
    ModificationRecord,
    ValidationRule,
    PreSaveValidator,
    create_validator,
    validate_document,
    validate_page,
    quick_check,
    get_blocking_issues,
)

__all__ = [
    # TextSpan
    "TextSpanMetrics",
    "RenderMode",
    "FontEmbeddingStatus",
    "create_span_from_pymupdf",
    "create_empty_span",
    # ContentStreamParser
    "TextOperator",
    "TextState",
    "TextShowOperation",
    "ParsedTextBlock",
    "ContentStreamParser",
    "parse_content_stream",
    "extract_text_state_from_page",
    "get_spacing_info_for_text",
    # TransformMatrix
    "TransformMatrix",
    "TransformationType",
    "TextTransformInfo",
    "matrix_from_pdf_array",
    "compose_matrices",
    "interpolate_matrices",
    "extract_rotation_angle",
    "create_text_matrix",
    # TextLine
    "TextLine",
    "LineGrouper",
    "LineGroupingConfig",
    "ReadingDirection",
    "LineAlignment",
    "group_spans_into_lines",
    "find_line_at_point",
    "calculate_line_statistics",
    # TextParagraph
    "TextParagraph",
    "ParagraphType",
    "ParagraphAlignment",
    "ListType",
    "ListMarkerInfo",
    "ParagraphStyle",
    "ParagraphDetectionConfig",
    "ParagraphDetector",
    "group_lines_into_paragraphs",
    "find_paragraph_at_point",
    "find_paragraphs_in_region",
    "calculate_paragraph_statistics",
    "merge_paragraphs",
    "split_paragraph_at_line",
    # SpaceMapper
    "SpaceType",
    "SpaceInfo",
    "WordBoundary",
    "SpaceAnalysis",
    "SpaceMapperConfig",
    "SpaceMapper",
    "analyze_line_spacing",
    "reconstruct_line_text",
    "count_words_in_line",
    "estimate_character_positions",
    "find_char_at_x",
    "calculate_space_metrics",
    # BaselineTracker
    "LeadingType",
    "AlignmentGrid",
    "BaselineInfo",
    "ParagraphBreak",
    "BaselineAnalysis",
    "LeadingAnalysis",
    "BaselineTrackerConfig",
    "BaselineTracker",
    "analyze_page_baselines",
    "calculate_leading",
    "snap_to_grid",
    "generate_baseline_grid",
    "estimate_baseline_from_bbox",
    "classify_leading_type",
    "find_paragraph_breaks_in_baselines",
    "validate_baseline_consistency",
    # EmbeddedFontExtractor
    "FontType",
    "EmbeddingStatus",
    "FontEncoding",
    "FontMetrics",
    "GlyphInfo",
    "FontInfo",
    "FontExtractorConfig",
    "EmbeddedFontExtractor",
    "extract_font_info",
    "is_font_embedded",
    "is_subset_font",
    "get_clean_font_name",
    "get_font_type_from_name",
    "calculate_text_width_simple",
    "list_embedded_fonts",
    "list_subset_fonts",
    "get_font_embedding_status",
    # TextHitTester
    "HitType",
    "HitTestResult",
    "PageTextCache",
    "TextHitTester",
    "create_hit_tester",
    "hit_test_point",
    "get_span_at_point",
    "get_line_at_point",
    # SafeTextRewriter
    "OverlayStrategy",
    "RewriteMode",
    "OverlayType",
    "RewriteStatus",
    "OverlayLayer",
    "TextOverlayInfo",
    "RewriteResult",
    "RewriterConfig",
    "ZOrderManager",
    "SafeTextRewriter",
    "create_safe_rewriter",
    "rewrite_text_safe",
    "get_recommended_strategy",
    # ObjectSubstitution
    "SubstitutionType",
    "SubstitutionStatus",
    "MatchStrategy",
    "TextLocation",
    "TextSubstitution",
    "SubstitutionResult",
    "SubstitutorConfig",
    "PDFTextEncoder",
    "ContentStreamModifier",
    "ObjectSubstitutor",
    "create_substitutor",
    "substitute_text_in_page",
    "get_recommended_substitution_type",
    # ZOrderManager
    "LayerLevel",
    "CollisionType",
    "ReorderOperation",
    "LayerInfo",
    "CollisionInfo",
    "LayerGroup",
    "ReorderHistoryEntry",
    "ZOrderConfig",
    "AdvancedZOrderManager",
    "create_z_order_manager",
    "get_layer_level_for_type",
    "resolve_z_order_conflict",
    # GlyphWidthPreserver
    "FitStrategy",
    "FitResult",
    "AdjustmentType",
    "WidthUnit",
    "GlyphWidth",
    "TextWidthInfo",
    "SpacingAdjustment",
    "FitAnalysis",
    "PreserverConfig",
    "TJArrayEntry",
    "GlyphWidthPreserver",
    "create_width_preserver",
    "calculate_text_width",
    "fit_text_to_width",
    "get_spacing_adjustment",
    # PreSaveValidator
    "ValidationSeverity",
    "ValidationCategory",
    "ValidationResult",
    "ContentIssueType",
    "FontIssueType",
    "StructureIssueType",
    "ValidationIssue",
    "ValidationReport",
    "ValidatorConfig",
    "ModificationRecord",
    "ValidationRule",
    "PreSaveValidator",
    "create_validator",
    "validate_document",
    "validate_page",
    "quick_check",
    "get_blocking_issues",
]

__version__ = "0.11.0"

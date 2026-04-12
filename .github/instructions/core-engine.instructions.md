---
description: "Use when modifying PDF engine, text_engine pipeline, font management, clipboard, change tracking, or PDF handler. Covers SafeTextRewriter, FitStrategy, EditableSpan, PageDocumentModel, and all core patterns."
applyTo: "core/**/*.py"
---
# Core Engine Guidelines

## Architecture
The text editing pipeline flows:
`ContentStreamParser → TextSpanMetrics → TextLine → TextParagraph → PageDocumentModel → SafeTextRewriter → PageWriter`

**Never modify PDF content streams directly.** Always use `SafeTextRewriter`.

## Key Patterns

### Enum + DataClass
```python
class FitStrategy(Enum):
    EXACT = "exact"
    COMPRESS = "compress"
    EXPAND = "expand"
    # ...

@dataclass
class EditableSpan:
    text: str
    page_num: int
    bbox: Tuple[float, float, float, float]
    font_name: str
    font_size: float
```

### Factory Functions
Every major component exposes `create_*()` at module level:
```python
def create_width_preserver(font_metrics: dict) -> GlyphWidthPreserver:
    """Crea un preservador de anchos de glifos."""
    return GlyphWidthPreserver(font_metrics)
```

### Serialization
All functional dataclasses MUST implement:
```python
def to_dict(self) -> dict:
    """Serializa a diccionario."""
    
@classmethod
def from_dict(cls, data: dict) -> 'ClassName':
    """Deserializa desde diccionario."""
```

## Safety Rules
- `EditableSpan` always stores `page_num` — edits are tied to pages
- OverlayStrategy options: REDACT_THEN_INSERT, WHITE_BACKGROUND, PRESERVE_BACKGROUND
- Z-order management prevents visual artifacts in overlays
- Font fallback: always provide a substitute when the original font is unavailable

## Error Handling
```python
try:
    result = specific_operation()
except fitz.FileNotFoundError:
    logger.error(f"Archivo no encontrado: {path}")
except ValueError as e:
    logger.warning(f"Valor inválido: {e}")
except Exception as e:
    logger.error(f"Error inesperado: {e}")
```

# PDF Text Editing Skill

Expert knowledge for editing text in PDF documents using the SafeTextRewriter pipeline.

## When to Use
- Editing existing text in a PDF (character replacement, font changes, styling)
- Working with `core/text_engine/` modules
- Implementing new FitStrategy options
- Debugging text rendering issues (wrong position, missing glyphs, overflow)

## Pipeline Overview

```
PDF Page
  ↓ ContentStreamParser.parse(page)
  ↓ → raw spans with (text, font, size, origin, color)
  ↓ TextSpanMetrics.from_raw_span(span)
  ↓ → enriched span with bbox, width, ascent, descent
  ↓ TextLine.from_spans([spans])
  ↓ → grouped spans on same baseline
  ↓ TextParagraph.from_lines([lines])
  ↓ → lines with shared alignment/indent
  ↓ PageDocumentModel.from_page(page)
  ↓ → full page model: paragraphs → lines → spans
  ↓ SafeTextRewriter.rewrite(model, edits)
  ↓ → applies edits respecting width/position constraints
  ↓ PageWriter.write(page, result)
  ↓ → commits changes to PDF page
```

## FitStrategy Selection Guide

| Strategy | Use When | Risk |
|----------|----------|------|
| EXACT | Text has identical width | None |
| COMPRESS | New text slightly wider | Minor visual compression |
| EXPAND | New text slightly narrower | Minor visual expansion |
| TRUNCATE | Text doesn't fit, can lose end | Data loss |
| ELLIPSIS | Text doesn't fit, add "..." | Data loss with indicator |
| SCALE | Use font scaling to fit | May look inconsistent |
| ALLOW_OVERFLOW | Overflow is acceptable | Visual overlap |

## Common Patterns

### Edit a single span
```python
from core.text_engine.safe_text_rewriter import SafeTextRewriter, TextEdit
from core.text_engine.page_document_model import PageDocumentModel

model = PageDocumentModel.from_page(page)
edit = TextEdit(
    span_id=target_span.id,
    new_text="nuevo texto",
    fit_strategy=FitStrategy.COMPRESS
)
result = SafeTextRewriter.rewrite(model, [edit])
PageWriter.write(page, result)
```

### Preserve glyph widths
```python
from core.text_engine.glyph_width_preserver import create_width_preserver

preserver = create_width_preserver(font_metrics)
adjusted = preserver.adjust(new_text, original_width)
```

## Debugging
- `DEBUG_RENDER=1` — Visualize span bounding boxes
- `DEBUG_COORDS=1` — Log coordinate transformations
- `DEBUG_EDIT=1` — Log edit operations step by step

## Pitfalls
1. **Subset fonts**: Can't add characters not in the original subset → use font fallback
2. **CID fonts**: Width calculation differs from simple fonts → use CIDWidthMapper
3. **RTL text**: Requires reversed glyph order → check text direction first
4. **Vertical text**: origin.y changes, not origin.x → detect writing mode

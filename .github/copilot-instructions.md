# PDF Editor Pro — Project Guidelines

## Stack
- **Python** 3.8+ | **PyQt5** ≥5.15 | **PyMuPDF (fitz)** ≥1.23
- **pytest** ≥9.0 for testing | **PyInstaller** ≥6.0 for packaging
- Optional: `pikepdf` for PDF repair (try/except import)

## Architecture
- `core/` — PDF engine, font management, clipboard, change tracking
- `core/text_engine/` — 16-module text analysis/editing pipeline (1,100+ tests)
- `ui/` — PyQt5 interface with Fusion style, dark theme (#1e1e1e, #2d2d30, #0078d4)
- `tests/` — Organized: `unit/`, `text_engine/`, `ui/`, `integration/`

Key pipeline: `ContentStreamParser → TextSpanMetrics → TextLine → TextParagraph → PageDocumentModel → SafeTextRewriter → PageWriter`

## Code Style

### Naming
- Classes: `CamelCase` (`FontManager`, `TextSpanMetrics`, `SafeTextRewriter`)
- Functions/methods: `snake_case` (`detect_font()`, `create_span()`)
- Private: prefix `_` (`_try_repair_pdf()`, `_on_cursor_moved()`)
- Constants: `UPPER_SNAKE` (`DEBUG_RENDER`, `FIXTURES_DIR`)

### Patterns
- **Enum + @dataclass**: All domain models use this combination
- **Factory functions**: `create_*()` at module level (e.g., `create_width_preserver()`)
- **Serialization**: `to_dict()` / `from_dict()` on functional dataclasses
- **IntEnum** for numeric values, **Enum** with string values for descriptive names

### Imports
```python
# 1. Standard library
import sys, os, logging
from typing import Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, IntEnum

# 2. Third-party
import fitz  # PyMuPDF
from PyQt5.QtWidgets import QMainWindow

# 3. Local (absolute imports)
from core.font_manager import FontManager
from core.text_engine.text_span import TextSpanMetrics

# 4. Optional (try/except)
try:
    import pikepdf
    PIKEPDF_AVAILABLE = True
except ImportError:
    PIKEPDF_AVAILABLE = False
```

### Docstrings
Google-style, in **Spanish** for descriptions, English for class/function names:
```python
class FontManager:
    """Gestor de fuentes para detección y sustitución.
    
    Attributes:
        cache: Caché de fuentes detectadas.
    """
    
    def detect_font(self, span: dict) -> FontDescriptor:
        """Detecta la fuente de un span de texto PDF."""
```

### Logging
```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"PDF abierto: {file_path}")
logger.debug(f"Span detectado: {span.text}")
logger.error(f"Error guardando: {e}")
```

## Build and Test
```bash
# Run all tests
python -m pytest tests/ -q

# Run specific category
python -m pytest tests/text_engine/ -q
python -m pytest tests/unit/ -q
python -m pytest tests/ui/ -q
python -m pytest tests/integration/ -q

# Run application
python main.py
```

## Conventions
- Every new module MUST have a corresponding `tests/<category>/test_<module>.py`
- UI language: **Spanish** (labels, tooltips, status messages)
- Code language: **English** (class names, function names, variable names)
- PyQt5 signals: `pyqtSignal()` | Slots: `_on_<event>()` pattern
- Error handling: specific exceptions first, generic `Exception` last, always log
- Text editing: always use `SafeTextRewriter` — never modify PDF content stream directly
- FitStrategy (7 options): EXACT, COMPRESS, EXPAND, TRUNCATE, ELLIPSIS, SCALE, ALLOW_OVERFLOW
- Debug categories: DEBUG_RENDER, DEBUG_COORDS, DEBUG_EDIT, DEBUG_UNDO, DEBUG_SELECTION

## Documentation
See `docs/` for architecture details, guides, and historical records.

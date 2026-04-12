---
description: "Use when writing, modifying, or reviewing tests. Covers pytest conventions, fixture patterns, test organization, mocking PyMuPDF, and coverage requirements."
applyTo: "tests/**/*.py"
---
# Testing Guidelines

## Organization
```
tests/
├── conftest.py          # Shared fixtures and path config
├── fixtures/            # Test PDF files
├── unit/                # Core module tests (font_manager, change_report...)
├── text_engine/         # Text engine tests (text_span, parser, rewriter...)
├── ui/                  # UI component tests (dialogs, panels, overlay...)
└── integration/         # End-to-end and cross-module tests
```

## Test Structure
```python
import pytest
from core.module_name import ClassName

@pytest.fixture
def instance():
    """Fixture: instancia fresca del componente."""
    return ClassName()

class TestFeatureName:
    """Tests para la funcionalidad X."""
    
    def test_happy_path(self, instance):
        """Descripción clara del comportamiento esperado."""
        result = instance.method(valid_input)
        assert result == expected_value
    
    def test_edge_case_empty(self, instance):
        """Maneja input vacío correctamente."""
        result = instance.method("")
        assert result is None
    
    def test_error_invalid_input(self, instance):
        """Lanza excepción con input inválido."""
        with pytest.raises(ValueError):
            instance.method(invalid_input)
```

## Minimum Coverage Per Module
- **Happy path**: At least 3 tests for normal operation
- **Edge cases**: At least 3 tests (empty, boundary, special characters)
- **Error cases**: At least 2 tests (invalid input, missing data)
- **Total minimum**: 10 tests per module

## Naming
- File: `test_<module_name>.py`
- Class: `Test<FeatureName>` (e.g., `TestFontDetection`)
- Method: `test_<what_it_tests>` with descriptive docstring in Spanish

## Mocking PyMuPDF
```python
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_page():
    """Mock de una página PDF."""
    page = MagicMock()
    page.rect = fitz.Rect(0, 0, 595, 842)
    page.get_text.return_value = {"blocks": [...]}
    return page
```

## Rules
- Unit tests MUST NOT access real PDF files (use mocks)
- Integration tests CAN use fixtures from `tests/fixtures/test_pdfs/`
- Docstrings in **Spanish** describing what is tested
- Never use `time.sleep()` in tests
- Use `@pytest.mark.skip(reason="...")` for known issues, not silent skips

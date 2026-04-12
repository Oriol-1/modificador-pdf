---
description: "Generate a comprehensive test suite for an existing module. Ensures pytest conventions, mocking patterns, and minimum coverage."
mode: "agent"
---
# Add Tests for Module

Write a comprehensive pytest test suite for the specified module.

## Process
1. **Read** the target module completely — understand every public method
2. **Identify** dependencies that need mocking (fitz, PyQt5, file system)
3. **Create** test file at `tests/<category>/test_<module>.py`
4. **Write** tests following this structure:

```python
import pytest
from core.module_name import ClassName

class TestClassName:
    """Tests para ClassName."""
    
    # Happy path (3+ tests)
    def test_basic_operation(self): ...
    def test_with_valid_params(self): ...
    def test_returns_expected_type(self): ...
    
    # Edge cases (3+ tests) 
    def test_empty_input(self): ...
    def test_boundary_values(self): ...
    def test_special_characters(self): ...
    
    # Error handling (2+ tests)
    def test_invalid_input_raises(self): ...
    def test_missing_required_field(self): ...
    
    # Integration within class (2+ tests)
    def test_method_chain(self): ...
    def test_state_after_operations(self): ...
```

5. **Run**: `python -m pytest tests/<category>/test_<module>.py -v`
6. **Fix** any failures until all pass
7. **Report** coverage: methods tested / total methods

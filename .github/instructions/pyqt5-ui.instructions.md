---
description: "Use when creating or editing PyQt5 UI components: dialogs, panels, widgets, toolbars, menus, stylesheets, signals/slots, layouts. Covers dark theme, Fusion style, and widget patterns."
applyTo: "ui/**/*.py"
---
# PyQt5 UI Development Guidelines

## Theme & Style
- App uses **Fusion** style with dark theme
- Colors: background `#1e1e1e`, panels `#2d2d30`, accent `#0078d4`, text `#ffffff`
- All widgets MUST apply dark stylesheet — never leave default Qt colors
- Use `setStyleSheet()` inline or reference `ThemeManager` when available

## Widget Patterns

### Signals & Slots
```python
# Signal definition
formatChanged = pyqtSignal()
pageSelected = pyqtSignal(int)

# Slot naming: _on_<source>_<event>()
def _on_zoom_changed(self, value: int):
    """Maneja cambio de zoom."""

# Connection
self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
```

### Dialog Template
```python
class MyDialog(QDialog):
    """Descripción del diálogo en español."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Título en Español")
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        # ... build UI
        self.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")
```

### Layout Rules
- `QVBoxLayout` for vertical stacking, `QHBoxLayout` for horizontal
- `setContentsMargins(8, 8, 8, 8)` standard margins
- `setSpacing(4)` for compact layouts, `8` for standard

## Labels & Text
- All user-visible text in **Spanish**
- Tooltips in Spanish: `btn.setToolTip("Guardar documento")`
- Status messages in Spanish: `self.statusBar().showMessage("PDF abierto correctamente")`

## Reference Files
- [ui/font_dialog.py](../../ui/font_dialog.py) — Dialog pattern exemplar
- [ui/property_inspector.py](../../ui/property_inspector.py) — Panel with collapsible sections
- [ui/main_window.py](../../ui/main_window.py) — Main window structure and dark stylesheet

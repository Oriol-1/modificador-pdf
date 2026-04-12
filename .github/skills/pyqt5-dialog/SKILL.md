# PyQt5 Dialog Skill

Expert knowledge for building PyQt5 dialogs and panels with the project's dark theme and conventions.

## When to Use
- Creating new dialog windows (QDialog)
- Building panels or sidebars (QWidget, QDockWidget)
- Adding toolbar actions with dropdown menus
- Implementing form-style interfaces with labels + inputs

## Dialog Template

```python
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QGroupBox
)
from PyQt5.QtCore import pyqtSignal, Qt

class FeatureDialog(QDialog):
    """Diálogo para configurar la funcionalidad X."""
    
    # Signals
    accepted_with_data = pyqtSignal(dict)
    
    def __init__(self, parent=None, initial_data=None):
        super().__init__(parent)
        self.setWindowTitle("Título en Español")
        self.setMinimumSize(400, 300)
        self._data = initial_data or {}
        self._init_ui()
        self._connect_signals()
        self._apply_theme()
    
    def _init_ui(self):
        """Construye la interfaz."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Group box for related controls
        group = QGroupBox("Opciones")
        group_layout = QVBoxLayout(group)
        
        # Input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Escribir aquí...")
        group_layout.addWidget(QLabel("Etiqueta:"))
        group_layout.addWidget(self.input_field)
        
        layout.addWidget(group)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_accept = QPushButton("Aceptar")
        self.btn_accept.setDefault(True)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_accept)
        layout.addLayout(btn_layout)
    
    def _connect_signals(self):
        """Conecta señales a slots."""
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_accept.clicked.connect(self._on_accept_clicked)
    
    def _on_accept_clicked(self):
        """Valida y emite datos."""
        data = {"value": self.input_field.text()}
        self.accepted_with_data.emit(data)
        self.accept()
    
    def _apply_theme(self):
        """Aplica tema oscuro."""
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #ffffff; }
            QGroupBox { 
                border: 1px solid #3e3e42; border-radius: 4px;
                margin-top: 8px; padding-top: 12px;
                color: #ffffff; font-weight: bold;
            }
            QLabel { color: #cccccc; }
            QLineEdit {
                background-color: #2d2d30; color: #ffffff;
                border: 1px solid #3e3e42; border-radius: 3px;
                padding: 4px 8px;
            }
            QLineEdit:focus { border-color: #0078d4; }
            QPushButton {
                background-color: #0078d4; color: #ffffff;
                border: none; border-radius: 3px;
                padding: 6px 16px; min-width: 80px;
            }
            QPushButton:hover { background-color: #1a8ad4; }
            QPushButton:pressed { background-color: #005a9e; }
        """)
```

## Stylesheet Reference

### Core Colors
| Token | Hex | Use |
|-------|-----|-----|
| bg-primary | `#1e1e1e` | Main backgrounds |
| bg-secondary | `#2d2d30` | Input fields, panels |
| bg-hover | `#3e3e42` | Hover states |
| accent | `#0078d4` | Focus borders, primary buttons |
| accent-hover | `#1a8ad4` | Button hover |
| accent-press | `#005a9e` | Button pressed |
| text-primary | `#ffffff` | Main text |
| text-secondary | `#cccccc` | Labels, secondary text |
| border | `#3e3e42` | Borders and dividers |
| error | `#f44747` | Error states |
| success | `#89d185` | Success states |

### Common Widget Styles
```css
/* Scrollbar */
QScrollBar:vertical { background: #1e1e1e; width: 12px; }
QScrollBar::handle:vertical { background: #3e3e42; min-height: 20px; border-radius: 6px; }
QScrollBar::handle:vertical:hover { background: #5a5a5e; }

/* Tab widget */
QTabWidget::pane { border: 1px solid #3e3e42; }
QTabBar::tab { background: #2d2d30; color: #cccccc; padding: 6px 12px; }
QTabBar::tab:selected { background: #1e1e1e; color: #ffffff; border-bottom: 2px solid #0078d4; }

/* Table */
QTableWidget { background: #1e1e1e; gridline-color: #3e3e42; }
QHeaderView::section { background: #2d2d30; color: #ffffff; border: 1px solid #3e3e42; }
```

## Panel Template (Dockable)
```python
class FeaturePanel(QDockWidget):
    """Panel lateral para funcionalidad X."""
    
    def __init__(self, parent=None):
        super().__init__("Título Panel", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        container = QWidget()
        self.setWidget(container)
        layout = QVBoxLayout(container)
        # ... build panel content
```

## Testing Dialog
```python
@pytest.fixture
def dialog(qtbot):
    """Crea diálogo para testing."""
    dlg = FeatureDialog()
    qtbot.addWidget(dlg)
    return dlg

def test_accept_emits_data(dialog, qtbot):
    """Aceptar emite datos correctos."""
    dialog.input_field.setText("test")
    with qtbot.waitSignal(dialog.accepted_with_data) as blocker:
        dialog.btn_accept.click()
    assert blocker.args[0] == {"value": "test"}
```

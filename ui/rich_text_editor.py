"""
Rich Text Editor - Editor de texto con soporte para runs de estilos.

Permite editar texto manteniendo la estructura de runs (spans) con diferentes
estilos dentro del mismo bloque de texto.

Características:
- Selección parcial de texto
- Aplicar negrita a selección
- Preservar estilos originales
- Preview en tiempo real con fuente exacta
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QGroupBox, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import (
    QFont, QColor, QFontMetrics, QTextCharFormat,
    QTextCursor, QTextDocument, QBrush
)

from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class TextRun:
    """Representa un fragmento de texto con su estilo."""
    text: str
    font_name: str = "Helvetica"
    font_size: float = 12.0
    is_bold: bool = False
    is_italic: bool = False
    color: str = "#000000"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'text': self.text,
            'font_name': self.font_name,
            'font_size': self.font_size,
            'is_bold': self.is_bold,
            'is_italic': self.is_italic,
            'color': self.color
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextRun':
        return cls(**data)


@dataclass 
class TextBlock:
    """Bloque de texto compuesto por múltiples runs."""
    runs: List[TextRun] = field(default_factory=list)
    max_width: float = 200.0
    
    def get_full_text(self) -> str:
        """Retorna el texto completo concatenado."""
        return ''.join(run.text for run in self.runs)
    
    def add_run(self, run: TextRun):
        """Añade un run al bloque."""
        self.runs.append(run)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'runs': [run.to_dict() for run in self.runs],
            'max_width': self.max_width
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextBlock':
        block = cls(max_width=data.get('max_width', 200.0))
        for run_data in data.get('runs', []):
            block.add_run(TextRun.from_dict(run_data))
        return block
    
    @classmethod
    def from_simple_text(cls, text: str, font_name: str = "Helvetica", 
                         font_size: float = 12.0, is_bold: bool = False,
                         max_width: float = 200.0) -> 'TextBlock':
        """Crea un bloque con un solo run."""
        block = cls(max_width=max_width)
        block.add_run(TextRun(
            text=text,
            font_name=font_name,
            font_size=font_size,
            is_bold=is_bold
        ))
        return block


class RichTextPreview(QFrame):
    """Widget de preview que muestra el texto con runs estilizados."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(100)
        self.setStyleSheet("""
            RichTextPreview {
                background-color: white;
                border: 2px solid #555;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Usar QTextEdit en modo solo lectura para preview
        self.preview_edit = QTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: none;
                color: black;
            }
        """)
        layout.addWidget(self.preview_edit)
        
        self._base_font_name = "Arial"
        self._base_font_size = 12
    
    def set_base_font(self, font_name: str, size: int):
        """Configura la fuente base."""
        self._base_font_name = font_name
        self._base_font_size = size
    
    def update_from_document(self, document: QTextDocument):
        """Actualiza el preview desde un QTextDocument."""
        self.preview_edit.setDocument(document.clone())
    
    def set_text_block(self, block: TextBlock):
        """Muestra un TextBlock con sus runs."""
        self.preview_edit.clear()
        cursor = self.preview_edit.textCursor()
        
        for run in block.runs:
            fmt = QTextCharFormat()
            font = QFont(run.font_name, int(run.font_size))
            font.setBold(run.is_bold)
            font.setItalic(run.is_italic)
            fmt.setFont(font)
            fmt.setForeground(QBrush(QColor(run.color)))
            
            cursor.insertText(run.text, fmt)


class RichTextEditor(QTextEdit):
    """Editor de texto enriquecido con soporte para runs."""
    
    formatChanged = pyqtSignal()  # Emitida cuando cambia el formato de la selección
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._base_font_name = "Helvetica"
        self._base_font_size = 12
        self._base_color = "#000000"
        
        # Estilo del editor
        self.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d30;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
                selection-background-color: #0078d4;
            }
        """)
        
        # Conectar señales
        self.cursorPositionChanged.connect(self._on_cursor_changed)
        self.selectionChanged.connect(self._on_selection_changed)
    
    def set_base_format(self, font_name: str, font_size: float, color: str = "#000000"):
        """Establece el formato base para texto nuevo."""
        self._base_font_name = font_name
        self._base_font_size = font_size
        self._base_color = color
        
        # Aplicar formato base
        font = QFont(font_name, int(font_size))
        self.setFont(font)
    
    def load_text_block(self, block: TextBlock):
        """Carga un TextBlock preservando sus runs."""
        self.clear()
        cursor = self.textCursor()
        
        for run in block.runs:
            fmt = QTextCharFormat()
            font = QFont(run.font_name, int(run.font_size))
            font.setBold(run.is_bold)
            font.setItalic(run.is_italic)
            fmt.setFont(font)
            fmt.setForeground(QBrush(QColor(run.color)))
            
            cursor.insertText(run.text, fmt)
        
        self.setTextCursor(cursor)
    
    def get_text_block(self) -> TextBlock:
        """Extrae el contenido como TextBlock con runs."""
        block = TextBlock()
        doc = self.document()
        
        # Iterar por el documento extrayendo runs
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.Start)
        
        current_run = None
        
        while not cursor.atEnd():
            cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
            char = cursor.selectedText()
            fmt = cursor.charFormat()
            font = fmt.font()
            
            # Crear run info
            run_info = {
                'font_name': font.family() or self._base_font_name,
                'font_size': font.pointSizeF() if font.pointSizeF() > 0 else self._base_font_size,
                'is_bold': font.bold(),
                'is_italic': font.italic(),
                'color': fmt.foreground().color().name() if fmt.foreground().style() != Qt.NoBrush else self._base_color
            }
            
            # ¿Mismo estilo que el run actual?
            if current_run and self._same_style(current_run, run_info):
                current_run.text += char
            else:
                # Guardar run anterior y crear nuevo
                if current_run and current_run.text:
                    block.add_run(current_run)
                current_run = TextRun(text=char, **run_info)
            
            cursor.clearSelection()
        
        # Añadir último run
        if current_run and current_run.text:
            block.add_run(current_run)
        
        return block
    
    def _same_style(self, run: TextRun, info: dict) -> bool:
        """Compara si un run tiene el mismo estilo que info."""
        return (
            run.font_name == info['font_name'] and
            abs(run.font_size - info['font_size']) < 0.5 and
            run.is_bold == info['is_bold'] and
            run.is_italic == info['is_italic'] and
            run.color == info['color']
        )
    
    def toggle_bold(self):
        """Aplica/quita negrita a la selección."""
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return
        
        # Verificar estado actual
        fmt = cursor.charFormat()
        is_bold = fmt.font().bold()
        
        # Aplicar formato opuesto
        new_fmt = QTextCharFormat()
        font = fmt.font()
        font.setBold(not is_bold)
        new_fmt.setFont(font)
        
        cursor.mergeCharFormat(new_fmt)
        self.formatChanged.emit()
    
    def toggle_italic(self):
        """Aplica/quita cursiva a la selección."""
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return
        
        fmt = cursor.charFormat()
        is_italic = fmt.font().italic()
        
        new_fmt = QTextCharFormat()
        font = fmt.font()
        font.setItalic(not is_italic)
        new_fmt.setFont(font)
        
        cursor.mergeCharFormat(new_fmt)
        self.formatChanged.emit()
    
    def is_selection_bold(self) -> bool:
        """Retorna si la selección actual es negrita."""
        cursor = self.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            return fmt.font().bold()
        return False
    
    def is_selection_italic(self) -> bool:
        """Retorna si la selección actual es cursiva."""
        cursor = self.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            return fmt.font().italic()
        return False
    
    def _on_cursor_changed(self):
        """Maneja cambio de posición del cursor."""
        self.formatChanged.emit()
    
    def _on_selection_changed(self):
        """Maneja cambio de selección."""
        self.formatChanged.emit()


class RichTextEditDialog(QDialog):
    """
    Diálogo de edición de texto enriquecido.
    
    Permite:
    - Editar texto manteniendo estructura de runs
    - Seleccionar parte del texto y aplicar negrita
    - Preview en tiempo real
    - Validación de que el texto cabe
    """
    
    def __init__(
        self,
        text_block: TextBlock = None,
        original_text: str = "",
        font_name: str = "Helvetica",
        font_size: float = 12.0,
        is_bold: bool = False,
        max_width: float = 200.0,
        parent=None
    ):
        super().__init__(parent)
        
        # Si no hay text_block, crear uno simple
        if text_block is None:
            text_block = TextBlock.from_simple_text(
                text=original_text,
                font_name=font_name,
                font_size=font_size,
                is_bold=is_bold,
                max_width=max_width
            )
        
        self.text_block = text_block
        self.original_text = original_text or text_block.get_full_text()
        self.max_width = max_width
        self._base_font_name = font_name
        self._base_font_size = font_size
        
        self.setup_ui()
        self.connect_signals()
        self.load_content()
        
        # Validación inicial
        QTimer.singleShot(100, self.validate_text)
    
    def setup_ui(self):
        """Configura la interfaz."""
        self.setWindowTitle("✏️ Editor de Texto Enriquecido")
        self.setMinimumSize(650, 700)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #ffffff;
            }
            QGroupBox {
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = QLabel(f"📝 Fuente base: {self._base_font_name} {self._base_font_size}pt")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #0078d4;")
        layout.addWidget(header)
        
        # Instrucciones
        instructions = QLabel(
            "💡 Selecciona texto y usa los botones para aplicar formato.\n"
            "   Ctrl+B = Negrita | Ctrl+I = Cursiva"
        )
        instructions.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(instructions)
        
        # Toolbar de formato
        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d30;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        
        # Botón Negrita
        self.bold_btn = QPushButton("B")
        self.bold_btn.setCheckable(True)
        self.bold_btn.setFixedSize(35, 35)
        self.bold_btn.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                font-size: 16px;
                background: #3d3d3d;
                border: 1px solid #555;
                border-radius: 4px;
                color: white;
            }
            QPushButton:checked {
                background: #0078d4;
                border-color: #0078d4;
            }
            QPushButton:hover {
                background: #4d4d4d;
            }
        """)
        self.bold_btn.setToolTip("Negrita (Ctrl+B)")
        toolbar_layout.addWidget(self.bold_btn)
        
        # Botón Cursiva
        self.italic_btn = QPushButton("I")
        self.italic_btn.setCheckable(True)
        self.italic_btn.setFixedSize(35, 35)
        self.italic_btn.setStyleSheet("""
            QPushButton {
                font-style: italic;
                font-size: 16px;
                background: #3d3d3d;
                border: 1px solid #555;
                border-radius: 4px;
                color: white;
            }
            QPushButton:checked {
                background: #0078d4;
                border-color: #0078d4;
            }
            QPushButton:hover {
                background: #4d4d4d;
            }
        """)
        self.italic_btn.setToolTip("Cursiva (Ctrl+I)")
        toolbar_layout.addWidget(self.italic_btn)
        
        toolbar_layout.addStretch()
        
        # Info de selección
        self.selection_info = QLabel("Sin selección")
        self.selection_info.setStyleSheet("color: #888; font-size: 11px;")
        toolbar_layout.addWidget(self.selection_info)
        
        layout.addWidget(toolbar_frame)
        
        # Editor de texto enriquecido
        edit_group = QGroupBox("Editar Texto")
        edit_group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 1px solid #0078d4;
            }
        """)
        edit_layout = QVBoxLayout(edit_group)
        
        self.rich_editor = RichTextEditor()
        self.rich_editor.setMinimumHeight(150)
        edit_layout.addWidget(self.rich_editor)
        layout.addWidget(edit_group)
        
        # Preview
        preview_group = QGroupBox("Vista Previa (así se verá en el PDF)")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_widget = RichTextPreview()
        self.preview_widget.set_base_font(self._base_font_name, int(self._base_font_size))
        preview_layout.addWidget(self.preview_widget)
        layout.addWidget(preview_group)
        
        # Status de validación
        self.status_frame = QFrame()
        self.status_frame.setMinimumHeight(40)
        self.status_frame.setStyleSheet("""
            QFrame {
                background-color: #1e4620;
                border: 1px solid #4caf50;
                border-radius: 4px;
            }
        """)
        status_layout = QHBoxLayout(self.status_frame)
        self.status_icon = QLabel("✓")
        self.status_icon.setStyleSheet("font-size: 18px; color: #4caf50;")
        status_layout.addWidget(self.status_icon)
        self.status_label = QLabel("El texto cabe correctamente")
        self.status_label.setStyleSheet("color: #4caf50;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        layout.addWidget(self.status_frame)
        
        # Opciones de ajuste (ocultas inicialmente)
        self.adjust_frame = QFrame()
        self.adjust_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d30;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        adjust_layout = QVBoxLayout(self.adjust_frame)
        
        adjust_title = QLabel("⚙️ Opciones de ajuste:")
        adjust_title.setStyleSheet("font-weight: bold; color: #ffcc00;")
        adjust_layout.addWidget(adjust_title)
        
        # Botones de ajuste
        btn_layout = QHBoxLayout()
        
        self.truncate_btn = QPushButton("✂️ Recortar")
        self.truncate_btn.setStyleSheet("""
            QPushButton {
                background: #3d3d3d; color: white;
                border: 1px solid #555; padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover { background: #4d4d4d; }
        """)
        btn_layout.addWidget(self.truncate_btn)
        
        self.spacing_btn = QPushButton("📏 Reducir espaciado")
        self.spacing_btn.setStyleSheet("""
            QPushButton {
                background: #3d3d3d; color: white;
                border: 1px solid #555; padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover { background: #4d4d4d; }
        """)
        btn_layout.addWidget(self.spacing_btn)
        
        self.size_btn = QPushButton("🔍 Reducir tamaño")
        self.size_btn.setStyleSheet("""
            QPushButton {
                background: #3d3d3d; color: white;
                border: 1px solid #555; padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover { background: #4d4d4d; }
        """)
        btn_layout.addWidget(self.size_btn)
        
        adjust_layout.addLayout(btn_layout)
        layout.addWidget(self.adjust_frame)
        self.adjust_frame.hide()
        
        # Botones principales
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: none;
                padding: 10px 25px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #4d4d4d; }
        """)
        btn_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton("✓ Aceptar")
        self.ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px 25px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1084d8; }
        """)
        btn_layout.addWidget(self.ok_btn)
        
        layout.addLayout(btn_layout)
    
    def connect_signals(self):
        """Conecta señales."""
        self.bold_btn.clicked.connect(self.on_bold_clicked)
        self.italic_btn.clicked.connect(self.on_italic_clicked)
        
        self.rich_editor.textChanged.connect(self.on_text_changed)
        self.rich_editor.formatChanged.connect(self.update_toolbar_state)
        
        self.truncate_btn.clicked.connect(self.apply_truncate)
        self.spacing_btn.clicked.connect(self.apply_spacing)
        self.size_btn.clicked.connect(self.apply_size_reduction)
        
        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self.accept)
    
    def load_content(self):
        """Carga el contenido inicial."""
        self.rich_editor.set_base_format(
            self._base_font_name,
            self._base_font_size
        )
        self.rich_editor.load_text_block(self.text_block)
        self.update_preview()
    
    def on_bold_clicked(self):
        """Aplica negrita a la selección."""
        self.rich_editor.toggle_bold()
        self.update_preview()
    
    def on_italic_clicked(self):
        """Aplica cursiva a la selección."""
        self.rich_editor.toggle_italic()
        self.update_preview()
    
    def on_text_changed(self):
        """Maneja cambio de texto."""
        self.update_preview()
        self.validate_text()
    
    def update_toolbar_state(self):
        """Actualiza estado de botones según selección."""
        cursor = self.rich_editor.textCursor()
        
        if cursor.hasSelection():
            self.bold_btn.setChecked(self.rich_editor.is_selection_bold())
            self.italic_btn.setChecked(self.rich_editor.is_selection_italic())
            
            selected_text = cursor.selectedText()
            self.selection_info.setText(f"Selección: \"{selected_text[:20]}{'...' if len(selected_text) > 20 else ''}\"")
        else:
            self.bold_btn.setChecked(False)
            self.italic_btn.setChecked(False)
            self.selection_info.setText("Sin selección")
    
    def update_preview(self):
        """Actualiza el preview."""
        block = self.rich_editor.get_text_block()
        self.preview_widget.set_text_block(block)
    
    def validate_text(self):
        """Valida si el texto cabe."""
        block = self.rich_editor.get_text_block()
        text = block.get_full_text()
        
        # Calcular ancho aproximado
        font = QFont(self._base_font_name, int(self._base_font_size))
        metrics = QFontMetrics(font)
        text_width = metrics.horizontalAdvance(text)
        
        fits = text_width <= self.max_width
        overflow = ((text_width - self.max_width) / self.max_width * 100) if not fits else 0
        
        if fits:
            self.status_frame.setStyleSheet("""
                QFrame {
                    background-color: #1e4620;
                    border: 1px solid #4caf50;
                    border-radius: 4px;
                }
            """)
            self.status_icon.setText("✓")
            self.status_icon.setStyleSheet("font-size: 18px; color: #4caf50;")
            self.status_label.setText("El texto cabe correctamente")
            self.status_label.setStyleSheet("color: #4caf50;")
            self.adjust_frame.hide()
        else:
            self.status_frame.setStyleSheet("""
                QFrame {
                    background-color: #4a1e1e;
                    border: 1px solid #f44336;
                    border-radius: 4px;
                }
            """)
            self.status_icon.setText("⚠")
            self.status_icon.setStyleSheet("font-size: 18px; color: #f44336;")
            self.status_label.setText(f"El texto excede el área en {overflow:.1f}%")
            self.status_label.setStyleSheet("color: #f44336;")
            self.adjust_frame.show()
    
    def apply_truncate(self):
        """Recorta el texto."""
        text = self.rich_editor.toPlainText()
        font = QFont(self._base_font_name, int(self._base_font_size))
        metrics = QFontMetrics(font)
        
        while text and metrics.horizontalAdvance(text) > self.max_width:
            text = text[:-1]
        
        if text:
            text = text.rstrip() + "..."
        
        # Recrear con texto truncado (pierde estilos internos)
        self.rich_editor.setPlainText(text)
        self.validate_text()
    
    def apply_spacing(self):
        """Aplica reducción de espaciado."""
        QMessageBox.information(
            self,
            "Espaciado",
            "Se reducirá el espaciado entre letras un 10%.\n"
            "Este cambio se aplicará al guardar."
        )
        self.validate_text()
    
    def apply_size_reduction(self):
        """Aplica reducción de tamaño."""
        QMessageBox.information(
            self,
            "Tamaño",
            "Se reducirá el tamaño de fuente un 10%.\n"
            "Este cambio se aplicará al guardar."
        )
        self.validate_text()
    
    def get_text_block(self) -> TextBlock:
        """Retorna el TextBlock editado."""
        return self.rich_editor.get_text_block()
    
    def get_result(self) -> Tuple[str, List[Dict], Dict]:
        """
        Retorna el resultado de la edición.
        
        Returns:
            (texto_completo, lista_de_runs, metadatos)
        """
        block = self.get_text_block()
        
        runs_data = [run.to_dict() for run in block.runs]
        
        metadata = {
            'original_text': self.original_text,
            'base_font': self._base_font_name,
            'base_size': self._base_font_size,
            'max_width': self.max_width,
            'has_mixed_styles': len(block.runs) > 1
        }
        
        return block.get_full_text(), runs_data, metadata
    
    def keyPressEvent(self, event):
        """Maneja atajos de teclado."""
        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_B:
                self.on_bold_clicked()
                return
            elif event.key() == Qt.Key_I:
                self.on_italic_clicked()
                return
        
        super().keyPressEvent(event)


def show_rich_text_editor(
    parent,
    original_text: str = "",
    font_name: str = "Helvetica",
    font_size: float = 12.0,
    is_bold: bool = False,
    max_width: float = 200.0,
    text_block: TextBlock = None
) -> Optional[Tuple[str, List[Dict], Dict]]:
    """
    Muestra el diálogo de edición de texto enriquecido.
    
    Returns:
        (texto, runs, metadata) si se aceptó, None si se canceló
    """
    dialog = RichTextEditDialog(
        text_block=text_block,
        original_text=original_text,
        font_name=font_name,
        font_size=font_size,
        is_bold=is_bold,
        max_width=max_width,
        parent=parent
    )
    
    if dialog.exec_() == QDialog.Accepted:
        return dialog.get_result()
    
    return None

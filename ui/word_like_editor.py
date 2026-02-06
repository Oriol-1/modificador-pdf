"""
Word-Like Text Editor - Editor de texto enriquecido estilo Word.

Un editor completo que preserva el formato original del PDF:
- Tipografía y tamaño originales
- Estructura (tabulaciones, sangrías, alineación)
- Negritas, cursivas y estilos
- Selección parcial para aplicar formato
- Copy/paste con preservación de formato
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QToolBar, QAction, QFontComboBox, QSpinBox,
    QColorDialog, QFrame, QSplitter, QWidget, QToolButton
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import (
    QFont, QColor, QTextCharFormat, QTextCursor, QTextBlockFormat,
    QTextListFormat, QTextDocument, QFontMetrics, QBrush, QKeySequence
)

from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class TextRunInfo:
    """Información de un fragmento de texto con estilo."""
    text: str
    font_name: str = "Helvetica"
    font_family: str = ""  # Alias para compatibilidad
    font_size: float = 12.0
    is_bold: bool = False
    bold: bool = False  # Alias para compatibilidad
    is_italic: bool = False
    italic: bool = False  # Alias para compatibilidad
    underline: bool = False
    color: str = "#000000"
    alignment: str = "left"  # left, center, right, justify
    indent: float = 0.0
    # Campos para preservar estructura de líneas
    is_line_start: bool = False
    is_line_end: bool = False
    needs_newline: bool = False
    line_y: float = 0.0
    
    def __post_init__(self):
        # Sincronizar aliases
        if self.font_family and not self.font_name:
            self.font_name = self.font_family
        elif self.font_name and not self.font_family:
            self.font_family = self.font_name
        
        if self.bold and not self.is_bold:
            self.is_bold = self.bold
        elif self.is_bold and not self.bold:
            self.bold = self.is_bold
            
        if self.italic and not self.is_italic:
            self.is_italic = self.italic
        elif self.is_italic and not self.is_italic:
            self.italic = self.is_italic
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'text': self.text,
            'font_name': self.font_name,
            'font_family': self.font_name,
            'font_size': self.font_size,
            'is_bold': self.is_bold,
            'bold': self.is_bold,
            'is_italic': self.is_italic,
            'italic': self.is_italic,
            'underline': self.underline,
            'color': self.color,
            'alignment': self.alignment,
            'indent': self.indent,
            'is_line_start': self.is_line_start,
            'is_line_end': self.is_line_end,
            'needs_newline': self.needs_newline
        }


@dataclass
class DocumentStructure:
    """Estructura completa del documento con runs."""
    runs: List[TextRunInfo] = field(default_factory=list)
    base_font: str = "Helvetica"
    base_font_name: str = ""  # Alias para compatibilidad
    base_size: float = 12.0
    base_font_size: float = 0.0  # Alias para compatibilidad
    max_width: float = 500.0
    
    def __post_init__(self):
        # Sincronizar aliases
        if self.base_font_name and not self.base_font:
            self.base_font = self.base_font_name
        elif self.base_font and not self.base_font_name:
            self.base_font_name = self.base_font
            
        if self.base_font_size > 0 and self.base_size == 12.0:
            self.base_size = self.base_font_size
        elif self.base_size != 12.0 and self.base_font_size == 0.0:
            self.base_font_size = self.base_size
    
    def get_full_text(self) -> str:
        return ''.join(run.text for run in self.runs)
    
    def add_run(self, run: TextRunInfo):
        self.runs.append(run)


class WordLikeToolBar(QToolBar):
    """Barra de herramientas estilo Word."""
    
    # Señales
    fontFamilyChanged = pyqtSignal(str)
    fontSizeChanged = pyqtSignal(int)
    boldToggled = pyqtSignal(bool)
    italicToggled = pyqtSignal(bool)
    underlineToggled = pyqtSignal(bool)
    alignmentChanged = pyqtSignal(str)
    colorChanged = pyqtSignal(QColor)
    listToggled = pyqtSignal(str)  # 'bullet', 'number', 'none'
    indentChanged = pyqtSignal(int)  # +1 o -1
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(False)
        self.setStyleSheet("""
            QToolBar {
                background: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px;
                spacing: 2px;
            }
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 3px;
                padding: 4px 6px;
                min-width: 28px;
                min-height: 28px;
            }
            QToolButton:hover {
                background: #e0e0e0;
                border-color: #ccc;
            }
            QToolButton:pressed, QToolButton:checked {
                background: #d0d0d0;
                border-color: #999;
            }
            QComboBox, QSpinBox {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 3px 6px;
                background: white;
                min-height: 24px;
            }
            QComboBox:hover, QSpinBox:hover {
                border-color: #0078d4;
            }
        """)
        
        self._setup_toolbar()
    
    def _setup_toolbar(self):
        """Configura todos los elementos de la barra."""
        
        # === SECCIÓN: Fuente ===
        # Selector de fuente
        self.font_combo = QFontComboBox()
        self.font_combo.setMaximumWidth(150)
        self.font_combo.setToolTip("Fuente")
        self.font_combo.currentFontChanged.connect(
            lambda f: self.fontFamilyChanged.emit(f.family())
        )
        self.addWidget(self.font_combo)
        
        # Tamaño de fuente - permitir desde 1pt para máxima flexibilidad
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 144)  # Rango ampliado: 1pt a 144pt
        self.size_spin.setValue(12)
        self.size_spin.setMaximumWidth(60)
        self.size_spin.setToolTip("Tamaño de fuente (1-144 pt)")
        self.size_spin.valueChanged.connect(self.fontSizeChanged.emit)
        self.addWidget(self.size_spin)
        
        self.addSeparator()
        
        # === SECCIÓN: Formato de texto ===
        # Negrita
        self.bold_action = QAction("B", self)
        self.bold_action.setCheckable(True)
        self.bold_action.setToolTip("Negrita (Ctrl+B)")
        self.bold_action.setShortcut(QKeySequence.Bold)
        self.bold_action.setFont(QFont("Arial", 10, QFont.Bold))
        self.bold_action.toggled.connect(self.boldToggled.emit)
        self.addAction(self.bold_action)
        
        # Cursiva
        self.italic_action = QAction("I", self)
        self.italic_action.setCheckable(True)
        self.italic_action.setToolTip("Cursiva (Ctrl+I)")
        self.italic_action.setShortcut(QKeySequence.Italic)
        font = QFont("Arial", 10)
        font.setItalic(True)
        self.italic_action.setFont(font)
        self.italic_action.toggled.connect(self.italicToggled.emit)
        self.addAction(self.italic_action)
        
        # Subrayado
        self.underline_action = QAction("U", self)
        self.underline_action.setCheckable(True)
        self.underline_action.setToolTip("Subrayado (Ctrl+U)")
        self.underline_action.setShortcut(QKeySequence.Underline)
        font = QFont("Arial", 10)
        font.setUnderline(True)
        self.underline_action.setFont(font)
        self.underline_action.toggled.connect(self.underlineToggled.emit)
        self.addAction(self.underline_action)
        
        # Color de texto
        self.color_btn = QToolButton()
        self.color_btn.setText("A")
        self.color_btn.setToolTip("Color de texto")
        self.color_btn.setStyleSheet("""
            QToolButton {
                font-weight: bold;
                border-bottom: 3px solid #000000;
            }
        """)
        self.color_btn.clicked.connect(self._choose_color)
        self._current_color = QColor("#000000")
        self.addWidget(self.color_btn)
        
        self.addSeparator()
        
        # === SECCIÓN: Alineación ===
        # Alinear izquierda
        self.align_left = QAction("≡←", self)
        self.align_left.setCheckable(True)
        self.align_left.setChecked(True)
        self.align_left.setToolTip("Alinear izquierda")
        self.align_left.triggered.connect(lambda: self._set_alignment("left"))
        self.addAction(self.align_left)
        
        # Centrar
        self.align_center = QAction("≡↔", self)
        self.align_center.setCheckable(True)
        self.align_center.setToolTip("Centrar")
        self.align_center.triggered.connect(lambda: self._set_alignment("center"))
        self.addAction(self.align_center)
        
        # Alinear derecha
        self.align_right = QAction("→≡", self)
        self.align_right.setCheckable(True)
        self.align_right.setToolTip("Alinear derecha")
        self.align_right.triggered.connect(lambda: self._set_alignment("right"))
        self.addAction(self.align_right)
        
        # Justificar
        self.align_justify = QAction("≡≡", self)
        self.align_justify.setCheckable(True)
        self.align_justify.setToolTip("Justificar")
        self.align_justify.triggered.connect(lambda: self._set_alignment("justify"))
        self.addAction(self.align_justify)
        
        self.addSeparator()
        
        # === SECCIÓN: Listas e indentación ===
        # Lista con viñetas
        self.bullet_list = QAction("• —", self)
        self.bullet_list.setCheckable(True)
        self.bullet_list.setToolTip("Lista con viñetas")
        self.bullet_list.triggered.connect(lambda: self.listToggled.emit("bullet"))
        self.addAction(self.bullet_list)
        
        # Lista numerada
        self.number_list = QAction("1. —", self)
        self.number_list.setCheckable(True)
        self.number_list.setToolTip("Lista numerada")
        self.number_list.triggered.connect(lambda: self.listToggled.emit("number"))
        self.addAction(self.number_list)
        
        # Disminuir sangría
        self.decrease_indent = QAction("←|", self)
        self.decrease_indent.setToolTip("Disminuir sangría")
        self.decrease_indent.triggered.connect(lambda: self.indentChanged.emit(-1))
        self.addAction(self.decrease_indent)
        
        # Aumentar sangría
        self.increase_indent = QAction("|→", self)
        self.increase_indent.setToolTip("Aumentar sangría")
        self.increase_indent.triggered.connect(lambda: self.indentChanged.emit(1))
        self.addAction(self.increase_indent)
    
    def _choose_color(self):
        """Abre el selector de color."""
        color = QColorDialog.getColor(self._current_color, self, "Seleccionar color")
        if color.isValid():
            self._current_color = color
            self.color_btn.setStyleSheet(f"""
                QToolButton {{
                    font-weight: bold;
                    border-bottom: 3px solid {color.name()};
                }}
            """)
            self.colorChanged.emit(color)
    
    def _set_alignment(self, alignment: str):
        """Establece la alineación y actualiza los botones."""
        self.align_left.setChecked(alignment == "left")
        self.align_center.setChecked(alignment == "center")
        self.align_right.setChecked(alignment == "right")
        self.align_justify.setChecked(alignment == "justify")
        self.alignmentChanged.emit(alignment)
    
    def update_format_state(self, fmt: QTextCharFormat, block_fmt: QTextBlockFormat):
        """Actualiza el estado de los botones según el formato actual."""
        # Bloquear señales temporalmente
        self.bold_action.blockSignals(True)
        self.italic_action.blockSignals(True)
        self.underline_action.blockSignals(True)
        self.font_combo.blockSignals(True)
        self.size_spin.blockSignals(True)
        
        # Actualizar estados
        font = fmt.font()
        self.bold_action.setChecked(font.bold())
        self.italic_action.setChecked(font.italic())
        self.underline_action.setChecked(font.underline())
        
        if font.family():
            self.font_combo.setCurrentFont(font)
        if font.pointSize() > 0:
            self.size_spin.setValue(font.pointSize())
        
        # Alineación
        alignment = block_fmt.alignment()
        self.align_left.setChecked(alignment == Qt.AlignLeft)
        self.align_center.setChecked(alignment == Qt.AlignCenter)
        self.align_right.setChecked(alignment == Qt.AlignRight)
        self.align_justify.setChecked(alignment == Qt.AlignJustify)
        
        # Restaurar señales
        self.bold_action.blockSignals(False)
        self.italic_action.blockSignals(False)
        self.underline_action.blockSignals(False)
        self.font_combo.blockSignals(False)
        self.size_spin.blockSignals(False)


class RichDocumentEditor(QTextEdit):
    """Editor de texto enriquecido que preserva formato."""
    
    formatChanged = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuración base
        self._base_font_family = "Helvetica"
        self._base_font_size = 12
        self._original_structure: Optional[DocumentStructure] = None
        
        # Estilo del editor - fondo claro para edición tipo Word
        self.setStyleSheet("""
            QTextEdit {
                background-color: white;
                color: black;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 10px;
                selection-background-color: #0078d4;
                selection-color: white;
            }
        """)
        
        # Configurar documento
        self.document().setDefaultFont(QFont(self._base_font_family, self._base_font_size))
        
        # Conectar señales
        self.cursorPositionChanged.connect(self._on_cursor_changed)
        self.selectionChanged.connect(self._on_selection_changed)
    
    def set_base_format(self, font_family: str, font_size: float):
        """Establece el formato base del documento."""
        self._base_font_family = font_family
        self._base_font_size = int(font_size)
        self.document().setDefaultFont(QFont(font_family, int(font_size)))
    
    def load_document_structure(self, structure: DocumentStructure):
        """Carga una estructura de documento preservando formato, tabulaciones y saltos de línea."""
        self._original_structure = structure
        self.clear()
        
        cursor = self.textCursor()
        
        for i, run in enumerate(structure.runs):
            # Verificar si necesita salto de línea antes del texto
            needs_newline = getattr(run, 'needs_newline', False)
            if needs_newline and i > 0:
                cursor.insertText('\n')
            
            # Aplicar indentación si es inicio de línea
            is_line_start = getattr(run, 'is_line_start', False)
            indent = getattr(run, 'indent', 0)
            if is_line_start and indent > 0:
                # Convertir indentación en pixeles a tabulaciones/espacios
                # Aproximadamente 1 tab = 40 pixels
                num_tabs = int(indent / 40)
                if num_tabs > 0:
                    cursor.insertText('\t' * num_tabs)
                else:
                    # Para indentaciones menores, usar espacios
                    num_spaces = int(indent / 6)  # aprox 6px por espacio
                    if num_spaces > 0:
                        cursor.insertText(' ' * num_spaces)
            
            # Crear formato para este run
            fmt = QTextCharFormat()
            font = QFont(run.font_name or run.font_family, int(run.font_size))
            font.setBold(run.is_bold or run.bold)
            font.setItalic(run.is_italic or run.italic)
            font.setUnderline(run.underline)
            fmt.setFont(font)
            fmt.setForeground(QBrush(QColor(run.color)))
            
            # Insertar texto con formato
            cursor.insertText(run.text, fmt)
        
        self.setTextCursor(cursor)
        self.moveCursor(QTextCursor.Start)
    
    def load_html_content(self, html: str, base_font: str = "Helvetica", base_size: int = 12):
        """Carga contenido HTML preservando formato."""
        self._base_font_family = base_font
        self._base_font_size = base_size
        self.setHtml(html)
    
    def load_plain_text_with_format(self, text: str, font_family: str, font_size: float, 
                                     is_bold: bool = False):
        """Carga texto plano con un formato específico."""
        self.clear()
        
        # Crear formato
        fmt = QTextCharFormat()
        font = QFont(font_family, int(font_size))
        font.setBold(is_bold)
        fmt.setFont(font)
        
        cursor = self.textCursor()
        cursor.insertText(text, fmt)
        self.moveCursor(QTextCursor.Start)
    
    def get_document_structure(self) -> DocumentStructure:
        """Extrae la estructura del documento con todos los runs, preservando saltos de línea."""
        structure = DocumentStructure(
            base_font=self._base_font_family,
            base_size=self._base_font_size
        )
        
        doc = self.document()
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.Start)
        
        current_run: Optional[TextRunInfo] = None
        is_line_start = True
        line_count = 0
        
        while not cursor.atEnd():
            cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
            char = cursor.selectedText()
            fmt = cursor.charFormat()
            font = fmt.font()
            
            # Detectar salto de línea (QTextDocument usa \u2029 para párrafos)
            is_newline = char in ('\n', '\r', '\u2029')
            
            if is_newline:
                # Guardar run actual si existe
                if current_run and current_run.text:
                    current_run.is_line_end = True
                    structure.add_run(current_run)
                    current_run = None
                
                is_line_start = True
                line_count += 1
                cursor.clearSelection()
                continue
            
            # Información del run actual
            run_info = {
                'font_family': font.family() or self._base_font_family,
                'font_size': font.pointSizeF() if font.pointSizeF() > 0 else self._base_font_size,
                'bold': font.bold(),
                'italic': font.italic(),
                'underline': font.underline(),
                'color': fmt.foreground().color().name() if fmt.foreground().style() != Qt.NoBrush else "#000000"
            }
            
            # ¿Mismo estilo que el run actual?
            if current_run and self._same_format(current_run, run_info) and not is_line_start:
                current_run.text += char
            else:
                # Guardar run anterior y crear nuevo
                if current_run and current_run.text:
                    structure.add_run(current_run)
                
                current_run = TextRunInfo(
                    text=char,
                    is_line_start=is_line_start,
                    needs_newline=(is_line_start and line_count > 0),
                    **run_info
                )
                is_line_start = False
            
            cursor.clearSelection()
        
        # Añadir último run
        if current_run and current_run.text:
            current_run.is_line_end = True
            structure.add_run(current_run)
        
        return structure
    
    def _same_format(self, run: TextRunInfo, info: dict) -> bool:
        """Compara si un run tiene el mismo formato."""
        return (
            run.font_family == info['font_family'] and
            abs(run.font_size - info['font_size']) < 0.5 and
            run.bold == info['bold'] and
            run.italic == info['italic'] and
            run.underline == info['underline'] and
            run.color == info['color']
        )
    
    # === Métodos de formato ===
    
    def set_bold(self, bold: bool):
        """Aplica/quita negrita a la selección."""
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Bold if bold else QFont.Normal)
        self._merge_format(fmt)
    
    def set_italic(self, italic: bool):
        """Aplica/quita cursiva a la selección."""
        fmt = QTextCharFormat()
        fmt.setFontItalic(italic)
        self._merge_format(fmt)
    
    def set_underline(self, underline: bool):
        """Aplica/quita subrayado a la selección."""
        fmt = QTextCharFormat()
        fmt.setFontUnderline(underline)
        self._merge_format(fmt)
    
    def set_font_family(self, family: str):
        """Cambia la fuente de la selección."""
        fmt = QTextCharFormat()
        fmt.setFontFamily(family)
        self._merge_format(fmt)
    
    def set_font_size(self, size: int):
        """Cambia el tamaño de la selección."""
        fmt = QTextCharFormat()
        fmt.setFontPointSize(size)
        self._merge_format(fmt)
    
    def set_text_color(self, color: QColor):
        """Cambia el color de la selección."""
        fmt = QTextCharFormat()
        fmt.setForeground(QBrush(color))
        self._merge_format(fmt)
    
    def set_alignment(self, alignment: str):
        """Cambia la alineación del párrafo."""
        cursor = self.textCursor()
        block_fmt = QTextBlockFormat()
        
        if alignment == "left":
            block_fmt.setAlignment(Qt.AlignLeft)
        elif alignment == "center":
            block_fmt.setAlignment(Qt.AlignCenter)
        elif alignment == "right":
            block_fmt.setAlignment(Qt.AlignRight)
        elif alignment == "justify":
            block_fmt.setAlignment(Qt.AlignJustify)
        
        cursor.mergeBlockFormat(block_fmt)
    
    def toggle_list(self, list_type: str):
        """Alterna lista con viñetas o numerada."""
        cursor = self.textCursor()
        
        if list_type == "bullet":
            fmt = QTextListFormat()
            fmt.setStyle(QTextListFormat.ListDisc)
            cursor.createList(fmt)
        elif list_type == "number":
            fmt = QTextListFormat()
            fmt.setStyle(QTextListFormat.ListDecimal)
            cursor.createList(fmt)
    
    def change_indent(self, delta: int):
        """Aumenta o disminuye la sangría."""
        cursor = self.textCursor()
        block_fmt = cursor.blockFormat()
        
        current_indent = block_fmt.indent()
        new_indent = max(0, current_indent + delta)
        
        block_fmt.setIndent(new_indent)
        cursor.setBlockFormat(block_fmt)
    
    def _merge_format(self, fmt: QTextCharFormat):
        """Aplica formato a la selección o al cursor."""
        cursor = self.textCursor()
        if cursor.hasSelection():
            cursor.mergeCharFormat(fmt)
        else:
            self.setCurrentCharFormat(fmt)
        self.formatChanged.emit()
    
    def _on_cursor_changed(self):
        """Emite señal cuando cambia el cursor."""
        self.formatChanged.emit()
    
    def _on_selection_changed(self):
        """Emite señal cuando cambia la selección."""
        self.formatChanged.emit()
    
    def get_current_format(self) -> Tuple[QTextCharFormat, QTextBlockFormat]:
        """Retorna el formato actual del cursor."""
        cursor = self.textCursor()
        return cursor.charFormat(), cursor.blockFormat()


class PreviewPanel(QFrame):
    """Panel de vista previa que muestra cómo quedará en el PDF."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(80)
        self.setStyleSheet("""
            PreviewPanel {
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Etiqueta
        label = QLabel("Vista previa (así se verá en el PDF):")
        label.setStyleSheet("color: #666; font-size: 11px; font-weight: bold;")
        layout.addWidget(label)
        
        # Área de preview
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.preview_text)
    
    def update_preview(self, document: QTextDocument):
        """Actualiza el preview desde el documento."""
        self.preview_text.setDocument(document.clone())


class WordLikeEditorDialog(QDialog):
    """
    Diálogo de edición de texto estilo Word.
    
    Características:
    - Barra de herramientas completa
    - Preservación de formato original
    - Edición WYSIWYG
    - Preview en tiempo real
    """
    
    def __init__(
        self,
        original_text: str = "",
        font_family: str = "Helvetica",
        font_size: float = 12.0,
        is_bold: bool = False,
        max_width: float = 500.0,
        document_structure: Optional[DocumentStructure] = None,
        html_content: str = "",
        parent=None
    ):
        super().__init__(parent)
        
        self._original_text = original_text
        self._base_font = font_family
        self._base_size = font_size
        self._is_bold = is_bold
        self._max_width = max_width
        self._document_structure = document_structure
        self._html_content = html_content
        
        self.setup_ui()
        self.connect_signals()
        self.load_content()
        
        # Actualizar estado inicial
        QTimer.singleShot(100, self._update_toolbar_state)
    
    def setup_ui(self):
        """Configura la interfaz."""
        self.setWindowTitle("✏️ Editor de Texto")
        self.setMinimumSize(700, 600)
        self.resize(800, 650)
        
        # Estilo del diálogo
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Header con info
        header_layout = QHBoxLayout()
        info_label = QLabel(f"📝 Fuente base: {self._base_font} {self._base_size}pt")
        info_label.setStyleSheet("font-weight: bold; color: #0078d4;")
        header_layout.addWidget(info_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Barra de herramientas
        self.toolbar = WordLikeToolBar()
        layout.addWidget(self.toolbar)
        
        # Splitter para editor y preview
        splitter = QSplitter(Qt.Vertical)
        
        # Editor principal
        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        
        editor_label = QLabel("Editar texto:")
        editor_label.setStyleSheet("font-weight: bold; color: #555;")
        editor_layout.addWidget(editor_label)
        
        self.editor = RichDocumentEditor()
        self.editor.setMinimumHeight(200)
        editor_layout.addWidget(self.editor)
        
        splitter.addWidget(editor_container)
        
        # Panel de preview
        self.preview_panel = PreviewPanel()
        splitter.addWidget(self.preview_panel)
        
        # Proporciones del splitter
        splitter.setSizes([400, 150])
        layout.addWidget(splitter)
        
        # Barra de estado
        self.status_bar = QFrame()
        self.status_bar.setStyleSheet("""
            QFrame {
                background-color: #e8f5e9;
                border: 1px solid #4caf50;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(10, 5, 10, 5)
        
        self.status_icon = QLabel("✓")
        self.status_icon.setStyleSheet("color: #4caf50; font-size: 16px;")
        status_layout.addWidget(self.status_icon)
        
        self.status_label = QLabel("Listo para editar")
        self.status_label.setStyleSheet("color: #2e7d32;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        self.char_count = QLabel("0 caracteres")
        self.char_count.setStyleSheet("color: #666;")
        status_layout.addWidget(self.char_count)
        
        layout.addWidget(self.status_bar)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                color: #333;
                border: none;
                padding: 10px 25px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #d0d0d0; }
        """)
        btn_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton("✓ Aplicar cambios")
        self.ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px 25px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1084d8; }
        """)
        btn_layout.addWidget(self.ok_btn)
        
        layout.addLayout(btn_layout)
    
    def connect_signals(self):
        """Conecta todas las señales."""
        # Toolbar -> Editor
        self.toolbar.boldToggled.connect(self.editor.set_bold)
        self.toolbar.italicToggled.connect(self.editor.set_italic)
        self.toolbar.underlineToggled.connect(self.editor.set_underline)
        self.toolbar.fontFamilyChanged.connect(self.editor.set_font_family)
        self.toolbar.fontSizeChanged.connect(self.editor.set_font_size)
        self.toolbar.colorChanged.connect(self.editor.set_text_color)
        self.toolbar.alignmentChanged.connect(self.editor.set_alignment)
        self.toolbar.listToggled.connect(self.editor.toggle_list)
        self.toolbar.indentChanged.connect(self.editor.change_indent)
        
        # Editor -> UI
        self.editor.formatChanged.connect(self._update_toolbar_state)
        self.editor.textChanged.connect(self._on_text_changed)
        
        # Botones
        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self.accept)
    
    def load_content(self):
        """Carga el contenido inicial."""
        self.editor.set_base_format(self._base_font, self._base_size)
        
        if self._document_structure and self._document_structure.runs:
            # Cargar estructura de documento
            self.editor.load_document_structure(self._document_structure)
        elif self._html_content:
            # Cargar HTML
            self.editor.load_html_content(
                self._html_content, 
                self._base_font, 
                int(self._base_size)
            )
        else:
            # Cargar texto plano con formato base
            self.editor.load_plain_text_with_format(
                self._original_text,
                self._base_font,
                self._base_size,
                self._is_bold
            )
        
        # Actualizar preview inicial
        self._update_preview()
    
    def _update_toolbar_state(self):
        """Actualiza el estado de la toolbar según el cursor."""
        char_fmt, block_fmt = self.editor.get_current_format()
        self.toolbar.update_format_state(char_fmt, block_fmt)
    
    def _on_text_changed(self):
        """Maneja cambio de texto."""
        self._update_preview()
        self._update_status()
    
    def _update_preview(self):
        """Actualiza el panel de preview."""
        self.preview_panel.update_preview(self.editor.document())
    
    def _update_status(self):
        """Actualiza la barra de estado."""
        text = self.editor.toPlainText()
        char_count = len(text)
        self.char_count.setText(f"{char_count} caracteres")
        
        # Verificar si cabe (simplificado)
        font = QFont(self._base_font, int(self._base_size))
        metrics = QFontMetrics(font)
        
        # Calcular ancho aproximado de la primera línea
        first_line = text.split('\n')[0] if text else ""
        text_width = metrics.horizontalAdvance(first_line)
        
        if text_width > self._max_width:
            overflow = ((text_width - self._max_width) / self._max_width) * 100
            self.status_bar.setStyleSheet("""
                QFrame {
                    background-color: #fff3e0;
                    border: 1px solid #ff9800;
                    border-radius: 4px;
                    padding: 5px;
                }
            """)
            self.status_icon.setText("⚠")
            self.status_icon.setStyleSheet("color: #ff9800; font-size: 16px;")
            self.status_label.setText(f"El texto puede exceder el ancho ({overflow:.0f}%)")
            self.status_label.setStyleSheet("color: #e65100;")
        else:
            self.status_bar.setStyleSheet("""
                QFrame {
                    background-color: #e8f5e9;
                    border: 1px solid #4caf50;
                    border-radius: 4px;
                    padding: 5px;
                }
            """)
            self.status_icon.setText("✓")
            self.status_icon.setStyleSheet("color: #4caf50; font-size: 16px;")
            self.status_label.setText("El texto cabe correctamente")
            self.status_label.setStyleSheet("color: #2e7d32;")
    
    def get_result(self) -> Tuple[str, DocumentStructure, str]:
        """
        Obtiene el resultado de la edición.
        
        Returns:
            (texto_plano, estructura_documento, html)
        """
        plain_text = self.editor.toPlainText()
        structure = self.editor.get_document_structure()
        html = self.editor.toHtml()
        
        return plain_text, structure, html
    
    def get_runs_data(self) -> List[Dict[str, Any]]:
        """Obtiene los runs como lista de diccionarios."""
        structure = self.editor.get_document_structure()
        return [run.to_dict() for run in structure.runs]


def show_word_like_editor(
    parent,
    original_text: str = "",
    font_family: str = "Helvetica",
    font_size: float = 12.0,
    is_bold: bool = False,
    max_width: float = 500.0,
    document: Optional[DocumentStructure] = None,
    document_structure: Optional[DocumentStructure] = None,
    html_content: str = "",
    title: str = "Editor de Texto"
) -> Optional[Tuple[str, List[Dict], Dict]]:
    """
    Muestra el editor de texto estilo Word.
    
    Args:
        parent: Widget padre
        original_text: Texto inicial (si no se pasa document)
        font_family: Familia de fuente por defecto
        font_size: Tamaño de fuente por defecto
        is_bold: Si negrita por defecto
        max_width: Ancho máximo disponible
        document: DocumentStructure con la estructura del documento
        document_structure: Alias de document (para compatibilidad)
        html_content: Contenido HTML inicial
        title: Título del diálogo
    
    Returns:
        (texto_plano, runs_data, metadata) si se aceptó, None si se canceló
        donde metadata es un dict con 'has_mixed_styles' y 'html'
    """
    # Usar document o document_structure
    doc_struct = document or document_structure
    
    # Si se pasa un document, extraer la configuración
    if doc_struct:
        font_family = doc_struct.base_font_name
        font_size = doc_struct.base_font_size
        max_width = doc_struct.max_width
        
        # Construir texto original desde los runs si no se proporcionó
        if not original_text and doc_struct.runs:
            original_text = ''.join(run.text for run in doc_struct.runs)
    
    dialog = WordLikeEditorDialog(
        original_text=original_text,
        font_family=font_family,
        font_size=font_size,
        is_bold=is_bold,
        max_width=max_width,
        document_structure=doc_struct,
        html_content=html_content,
        parent=parent
    )
    dialog.setWindowTitle(title)
    
    if dialog.exec_() == QDialog.Accepted:
        plain_text, structure, html = dialog.get_result()
        runs_data = [run.to_dict() for run in structure.runs]
        
        # Determinar si hay estilos mixtos
        has_mixed_styles = False
        if len(runs_data) > 1:
            # Verificar si los estilos son realmente diferentes
            first_style = (
                runs_data[0].get('font_name'),
                runs_data[0].get('font_size'),
                runs_data[0].get('is_bold'),
                runs_data[0].get('is_italic'),
                runs_data[0].get('color')
            )
            for run in runs_data[1:]:
                run_style = (
                    run.get('font_name'),
                    run.get('font_size'),
                    run.get('is_bold'),
                    run.get('is_italic'),
                    run.get('color')
                )
                if run_style != first_style:
                    has_mixed_styles = True
                    break
        
        metadata = {
            'has_mixed_styles': has_mixed_styles,
            'html': html,
            'font_family': font_family,
            'font_size': font_size
        }
        
        return plain_text, runs_data, metadata
    
    return None

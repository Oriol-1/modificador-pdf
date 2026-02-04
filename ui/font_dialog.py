"""
FontDialog - Diálogo de selección de fuentes con preview

PHASE2-201: Enhanced Dialog
Integración de FontManager con UI para selección de fuentes
"""

from typing import Optional, Tuple
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDoubleSpinBox, QPushButton, QFrame, QGroupBox,
    QColorDialog, QCheckBox, QWidget, QGridLayout, QLineEdit
)
from PyQt5.QtGui import QFont, QColor, QFontDatabase
from PyQt5.QtCore import Qt, pyqtSignal

from core.font_manager import FontDescriptor, get_font_manager

import logging
logger = logging.getLogger(__name__)


class FontPreviewWidget(QFrame):
    """Widget de preview de fuente."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(80)
        self.setStyleSheet("""
            FontPreviewWidget {
                background-color: white;
                border: 1px solid #555;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.preview_label = QLabel("AaBbCcDdEe 123")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("color: black; background: transparent;")
        layout.addWidget(self.preview_label)
    
    def update_preview(
        self,
        font_name: str,
        font_size: float,
        color: str = "#000000",
        bold: bool = False,
        italic: bool = False
    ):
        """Actualiza el preview con los parámetros dados."""
        font = QFont(font_name, int(font_size))
        font.setBold(bold)
        font.setItalic(italic)
        
        self.preview_label.setFont(font)
        self.preview_label.setStyleSheet(f"color: {color}; background: transparent;")


class ColorButton(QPushButton):
    """Botón que muestra y permite seleccionar un color."""
    
    colorChanged = pyqtSignal(str)
    
    def __init__(self, color: str = "#000000", parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(40, 25)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self._pick_color)
        self._update_style()
    
    def _update_style(self):
        """Actualiza el estilo del botón."""
        self.setStyleSheet(f"""
            ColorButton {{
                background-color: {self._color};
                border: 2px solid #666;
                border-radius: 3px;
            }}
            ColorButton:hover {{
                border-color: #0078d4;
            }}
        """)
    
    def _pick_color(self):
        """Abre el selector de color."""
        color = QColorDialog.getColor(
            QColor(self._color),
            self,
            "Seleccionar color"
        )
        if color.isValid():
            self._color = color.name()
            self._update_style()
            self.colorChanged.emit(self._color)
    
    def color(self) -> str:
        """Retorna el color actual."""
        return self._color
    
    def setColor(self, color: str):
        """Establece el color."""
        self._color = color
        self._update_style()


class FontDialog(QDialog):
    """
    Diálogo de selección de fuentes con integración FontManager.
    
    Permite:
    - Seleccionar fuente del sistema
    - Ajustar tamaño
    - Seleccionar color
    - Aplicar bold/italic
    - Preview en tiempo real
    - Detectar fuente desde descriptor PDF
    """
    
    def __init__(
        self,
        parent=None,
        current_font: Optional[FontDescriptor] = None,
        title: str = "Seleccionar Fuente"
    ):
        super().__init__(parent)
        self.font_manager = get_font_manager()
        self.current_font = current_font
        
        self.setWindowTitle(title)
        self.setMinimumSize(450, 400)
        self._setup_style()
        self._setup_ui()
        self._connect_signals()
        
        # Cargar valores iniciales si hay descriptor
        if current_font:
            self._load_from_descriptor(current_font)
    
    def _setup_style(self):
        """Configura el estilo del diálogo."""
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #ffffff;
            }
            QGroupBox {
                color: #ffffff;
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
            QComboBox {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #555;
                padding: 5px 10px;
                border-radius: 4px;
                min-height: 25px;
            }
            QComboBox:hover {
                border-color: #0078d4;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d30;
                color: white;
                selection-background-color: #0078d4;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 4px;
            }
            QCheckBox {
                color: white;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #3d3d3d;
                border: 1px solid #555;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border: 1px solid #0078d4;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #555;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
                border-color: #0078d4;
            }
            QPushButton#acceptBtn {
                background-color: #0078d4;
                border-color: #0078d4;
            }
            QPushButton#acceptBtn:hover {
                background-color: #1084d8;
            }
        """)
    
    def _setup_ui(self):
        """Configura la interfaz."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Grupo de fuente
        font_group = QGroupBox("Fuente")
        font_layout = QGridLayout(font_group)
        
        # Selector de fuente
        font_layout.addWidget(QLabel("Familia:"), 0, 0)
        self.font_combo = QComboBox()
        self._populate_fonts()
        font_layout.addWidget(self.font_combo, 0, 1, 1, 2)
        
        # Tamaño
        font_layout.addWidget(QLabel("Tamaño:"), 1, 0)
        self.size_spin = QDoubleSpinBox()
        self.size_spin.setRange(1, 200)
        self.size_spin.setValue(12.0)
        self.size_spin.setSuffix(" pt")
        self.size_spin.setDecimals(1)
        font_layout.addWidget(self.size_spin, 1, 1)
        
        # Color
        font_layout.addWidget(QLabel("Color:"), 1, 2)
        self.color_btn = ColorButton("#000000")
        font_layout.addWidget(self.color_btn, 1, 3)
        
        layout.addWidget(font_group)
        
        # Grupo de estilos
        style_group = QGroupBox("Estilos")
        style_layout = QHBoxLayout(style_group)
        
        self.bold_check = QCheckBox("Negrita")
        self.italic_check = QCheckBox("Cursiva")
        
        style_layout.addWidget(self.bold_check)
        style_layout.addWidget(self.italic_check)
        style_layout.addStretch()
        
        layout.addWidget(style_group)
        
        # Preview
        preview_group = QGroupBox("Vista Previa")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_widget = FontPreviewWidget()
        preview_layout.addWidget(self.preview_widget)
        
        # Texto de preview editable
        self.preview_text = QLineEdit("AaBbCcDdEe 123")
        self.preview_text.setStyleSheet("""
            QLineEdit {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 4px;
            }
        """)
        preview_layout.addWidget(self.preview_text)
        
        layout.addWidget(preview_group)
        
        # Info de fallback (si aplica)
        self.fallback_label = QLabel()
        self.fallback_label.setStyleSheet("color: #ffa500;")  # Naranja
        self.fallback_label.setVisible(False)
        layout.addWidget(self.fallback_label)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        accept_btn = QPushButton("Aceptar")
        accept_btn.setObjectName("acceptBtn")
        accept_btn.clicked.connect(self.accept)
        btn_layout.addWidget(accept_btn)
        
        layout.addLayout(btn_layout)
    
    def _populate_fonts(self):
        """Llena el combo con las fuentes del sistema."""
        font_db = QFontDatabase()
        families = font_db.families()
        
        # Fuentes comunes primero
        common_fonts = [
            "Arial", "Times New Roman", "Courier New", "Helvetica",
            "Verdana", "Georgia", "Tahoma", "Calibri"
        ]
        
        # Añadir fuentes comunes si existen
        added = set()
        for font in common_fonts:
            if font in families:
                self.font_combo.addItem(font)
                added.add(font)
        
        # Separador
        if added:
            self.font_combo.insertSeparator(self.font_combo.count())
        
        # Resto de fuentes
        for family in sorted(families):
            if family not in added:
                self.font_combo.addItem(family)
    
    def _connect_signals(self):
        """Conecta señales."""
        self.font_combo.currentTextChanged.connect(self._update_preview)
        self.size_spin.valueChanged.connect(self._update_preview)
        self.color_btn.colorChanged.connect(self._update_preview)
        self.bold_check.stateChanged.connect(self._update_preview)
        self.italic_check.stateChanged.connect(self._update_preview)
        self.preview_text.textChanged.connect(self._update_preview_text)
        
        # Actualizar preview inicial
        self._update_preview()
    
    def _update_preview(self):
        """Actualiza el preview."""
        self.preview_widget.update_preview(
            font_name=self.font_combo.currentText(),
            font_size=self.size_spin.value(),
            color=self.color_btn.color(),
            bold=self.bold_check.isChecked(),
            italic=self.italic_check.isChecked()
        )
    
    def _update_preview_text(self):
        """Actualiza el texto del preview."""
        text = self.preview_text.text() or "AaBbCcDdEe 123"
        self.preview_widget.preview_label.setText(text)
    
    def _load_from_descriptor(self, descriptor: FontDescriptor):
        """Carga valores desde un FontDescriptor."""
        # Buscar fuente
        font_name = descriptor.name
        index = self.font_combo.findText(font_name, Qt.MatchFixedString)
        
        if index < 0:
            # Intentar fallback
            fallback = self.font_manager.smart_fallback(font_name)
            index = self.font_combo.findText(fallback, Qt.MatchFixedString)
            
            if descriptor.was_fallback or index >= 0:
                self.fallback_label.setText(
                    f"⚠️ Fuente '{font_name}' no disponible. Usando '{fallback}'."
                )
                self.fallback_label.setVisible(True)
        
        if index >= 0:
            self.font_combo.setCurrentIndex(index)
        
        # Tamaño
        self.size_spin.setValue(descriptor.size)
        
        # Color
        self.color_btn.setColor(descriptor.color)
        
        # Bold
        if descriptor.possible_bold:
            self.bold_check.setChecked(True)
    
    def get_font_descriptor(self) -> FontDescriptor:
        """Retorna el FontDescriptor con los valores seleccionados."""
        return FontDescriptor(
            name=self.font_combo.currentText(),
            size=self.size_spin.value(),
            color=self.color_btn.color(),
            flags=0,
            was_fallback=False,
            fallback_from=None,
            possible_bold=self.bold_check.isChecked()
        )
    
    def get_values(self) -> Tuple[str, float, str, bool, bool]:
        """
        Retorna los valores seleccionados como tupla.
        
        Returns:
            (font_name, size, color, bold, italic)
        """
        return (
            self.font_combo.currentText(),
            self.size_spin.value(),
            self.color_btn.color(),
            self.bold_check.isChecked(),
            self.italic_check.isChecked()
        )
    
    @staticmethod
    def get_font(
        parent=None,
        current_font: Optional[FontDescriptor] = None,
        title: str = "Seleccionar Fuente"
    ) -> Optional[FontDescriptor]:
        """
        Método estático para mostrar el diálogo y obtener resultado.
        
        Args:
            parent: Widget padre
            current_font: FontDescriptor actual (opcional)
            title: Título del diálogo
            
        Returns:
            FontDescriptor o None si se canceló
        """
        dialog = FontDialog(parent, current_font, title)
        if dialog.exec_() == QDialog.Accepted:
            return dialog.get_font_descriptor()
        return None


class TextFormatDialog(QDialog):
    """
    Diálogo para formatear texto seleccionado.
    
    Combina selección de fuente con opciones de formato.
    """
    
    def __init__(
        self,
        parent=None,
        text: str = "",
        current_font: Optional[FontDescriptor] = None
    ):
        super().__init__(parent)
        self.text = text
        self.current_font = current_font
        
        self.setWindowTitle("Formato de Texto")
        self.setMinimumSize(500, 500)
        self._setup_style()
        self._setup_ui()
    
    def _setup_style(self):
        """Configura estilo."""
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QLabel { color: #ffffff; }
            QGroupBox {
                color: #ffffff;
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
            QTextEdit {
                background-color: #2d2d30;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #555;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
                border-color: #0078d4;
            }
            QPushButton#acceptBtn {
                background-color: #0078d4;
                border-color: #0078d4;
            }
        """)
    
    def _setup_ui(self):
        """Configura la interfaz."""
        layout = QVBoxLayout(self)
        
        # Texto
        text_group = QGroupBox("Texto")
        text_layout = QVBoxLayout(text_group)
        
        from PyQt5.QtWidgets import QTextEdit
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.text)
        self.text_edit.setMaximumHeight(100)
        text_layout.addWidget(self.text_edit)
        
        layout.addWidget(text_group)
        
        # Embeber FontDialog
        self.font_dialog_widget = QWidget()
        font_layout = QVBoxLayout(self.font_dialog_widget)
        font_layout.setContentsMargins(0, 0, 0, 0)
        
        # Crear elementos de FontDialog manualmente
        font_group = QGroupBox("Fuente")
        font_grid = QGridLayout(font_group)
        
        font_grid.addWidget(QLabel("Familia:"), 0, 0)
        self.font_combo = QComboBox()
        self._populate_fonts()
        font_grid.addWidget(self.font_combo, 0, 1, 1, 2)
        
        font_grid.addWidget(QLabel("Tamaño:"), 1, 0)
        self.size_spin = QDoubleSpinBox()
        self.size_spin.setRange(1, 200)
        self.size_spin.setValue(12.0)
        self.size_spin.setSuffix(" pt")
        font_grid.addWidget(self.size_spin, 1, 1)
        
        font_grid.addWidget(QLabel("Color:"), 1, 2)
        self.color_btn = ColorButton("#000000")
        font_grid.addWidget(self.color_btn, 1, 3)
        
        font_layout.addWidget(font_group)
        
        # Estilos
        style_group = QGroupBox("Estilos")
        style_layout = QHBoxLayout(style_group)
        self.bold_check = QCheckBox("Negrita")
        self.italic_check = QCheckBox("Cursiva")
        style_layout.addWidget(self.bold_check)
        style_layout.addWidget(self.italic_check)
        style_layout.addStretch()
        font_layout.addWidget(style_group)
        
        # Preview
        preview_group = QGroupBox("Vista Previa")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_widget = FontPreviewWidget()
        preview_layout.addWidget(self.preview_widget)
        font_layout.addWidget(preview_group)
        
        layout.addWidget(self.font_dialog_widget)
        
        # Conectar señales
        self.font_combo.currentTextChanged.connect(self._update_preview)
        self.size_spin.valueChanged.connect(self._update_preview)
        self.color_btn.colorChanged.connect(self._update_preview)
        self.bold_check.stateChanged.connect(self._update_preview)
        self.italic_check.stateChanged.connect(self._update_preview)
        self.text_edit.textChanged.connect(self._update_preview_from_text)
        
        # Cargar valores iniciales
        if self.current_font:
            self._load_from_descriptor(self.current_font)
        
        self._update_preview()
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        accept_btn = QPushButton("Aplicar")
        accept_btn.setObjectName("acceptBtn")
        accept_btn.clicked.connect(self.accept)
        btn_layout.addWidget(accept_btn)
        
        layout.addLayout(btn_layout)
    
    def _populate_fonts(self):
        """Llena el combo con fuentes."""
        font_db = QFontDatabase()
        for family in sorted(font_db.families()):
            self.font_combo.addItem(family)
        
        # Seleccionar Arial por defecto
        index = self.font_combo.findText("Arial", Qt.MatchFixedString)
        if index >= 0:
            self.font_combo.setCurrentIndex(index)
    
    def _load_from_descriptor(self, descriptor: FontDescriptor):
        """Carga desde descriptor."""
        index = self.font_combo.findText(descriptor.name, Qt.MatchFixedString)
        if index >= 0:
            self.font_combo.setCurrentIndex(index)
        self.size_spin.setValue(descriptor.size)
        self.color_btn.setColor(descriptor.color)
        if descriptor.possible_bold:
            self.bold_check.setChecked(True)
    
    def _update_preview(self):
        """Actualiza preview."""
        text = self.text_edit.toPlainText() or "AaBbCcDdEe 123"
        self.preview_widget.preview_label.setText(text[:50])  # Limitar
        self.preview_widget.update_preview(
            font_name=self.font_combo.currentText(),
            font_size=self.size_spin.value(),
            color=self.color_btn.color(),
            bold=self.bold_check.isChecked(),
            italic=self.italic_check.isChecked()
        )
    
    def _update_preview_from_text(self):
        """Actualiza preview cuando cambia el texto."""
        self._update_preview()
    
    def get_text(self) -> str:
        """Retorna el texto."""
        return self.text_edit.toPlainText()
    
    def get_font_descriptor(self) -> FontDescriptor:
        """Retorna el FontDescriptor."""
        return FontDescriptor(
            name=self.font_combo.currentText(),
            size=self.size_spin.value(),
            color=self.color_btn.color(),
            flags=0,
            was_fallback=False,
            fallback_from=None,
            possible_bold=self.bold_check.isChecked()
        )
    
    @staticmethod
    def format_text(
        parent=None,
        text: str = "",
        current_font: Optional[FontDescriptor] = None
    ) -> Optional[Tuple[str, FontDescriptor]]:
        """
        Muestra el diálogo y retorna texto y fuente.
        
        Returns:
            (texto, FontDescriptor) o None si cancelado
        """
        dialog = TextFormatDialog(parent, text, current_font)
        if dialog.exec_() == QDialog.Accepted:
            return (dialog.get_text(), dialog.get_font_descriptor())
        return None

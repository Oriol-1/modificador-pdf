"""
EnhancedTextEditDialog - Diálogo de edición de texto con validación en tiempo real.

PHASE2-201: Implementación completa según especificación.

Características:
- Preview en vivo del texto con la fuente exacta
- Validación "cabe/no cabe" en tiempo real
- Opciones [A] Recortar, [B] Espaciado, [C] Tamaño si no cabe
- Checkboxes para mantener/aplicar negrita
- Integración con FontManager y ChangeReport
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QCheckBox, QPushButton, QGroupBox, QFrame,
    QSlider, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QFontMetrics

from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

# Imports de Phase 2
try:
    from core.font_manager import FontDescriptor, get_font_manager
except ImportError:
    # Fallback si no están disponibles
    FontDescriptor = None
    get_font_manager = None


@dataclass
class TextEditResult:
    """Resultado de la edición de texto."""
    text: str
    original_text: str
    font_descriptor: Optional[Any]  # FontDescriptor
    bold_applied: bool
    tracking_reduced: float  # Porcentaje de reducción (0-100)
    size_reduced: float  # Porcentaje de reducción (0-100)
    was_truncated: bool
    warnings: list


class TextPreviewWidget(QFrame):
    """Widget de preview que muestra el texto con la fuente exacta."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(80)
        self.setStyleSheet("""
            TextPreviewWidget {
                background-color: white;
                border: 2px solid #555;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.preview_label = QLabel("Preview del texto")
        self.preview_label.setWordWrap(True)
        self.preview_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.preview_label.setStyleSheet("color: black; background: transparent;")
        layout.addWidget(self.preview_label)
        
        self._font_name = "Arial"
        self._font_size = 12
        self._is_bold = False
        self._color = QColor(0, 0, 0)
    
    def set_font(self, font_name: str, size: int, bold: bool = False, color: QColor = None):
        """Configura la fuente del preview."""
        self._font_name = font_name
        self._font_size = size
        self._is_bold = bold
        self._color = color or QColor(0, 0, 0)
        
        font = QFont(font_name, size)
        font.setBold(bold)
        self.preview_label.setFont(font)
        
        # Aplicar color
        palette = self.preview_label.palette()
        palette.setColor(QPalette.WindowText, self._color)
        self.preview_label.setPalette(palette)
    
    def set_text(self, text: str):
        """Actualiza el texto del preview."""
        self.preview_label.setText(text or "Vista previa...")
    
    def get_text_width(self, text: str) -> int:
        """Calcula el ancho del texto con la fuente actual."""
        font = QFont(self._font_name, self._font_size)
        font.setBold(self._is_bold)
        metrics = QFontMetrics(font)
        return metrics.horizontalAdvance(text)


class FitStatusWidget(QFrame):
    """Widget que muestra si el texto cabe o no."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(40)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        self.status_icon = QLabel("✓")
        self.status_icon.setStyleSheet("font-size: 20px;")
        layout.addWidget(self.status_icon)
        
        self.status_label = QLabel("El texto cabe correctamente")
        self.status_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        self.set_fits(True)
    
    def set_fits(self, fits: bool, overflow_percent: float = 0):
        """Actualiza el estado de si el texto cabe."""
        if fits:
            self.status_icon.setText("✓")
            self.status_label.setText("El texto cabe correctamente")
            self.setStyleSheet("""
                FitStatusWidget {
                    background-color: #1e4620;
                    border: 1px solid #4caf50;
                    border-radius: 4px;
                }
                QLabel { color: #4caf50; }
            """)
        else:
            self.status_icon.setText("⚠")
            self.status_label.setText(f"El texto excede el área en {overflow_percent:.1f}%")
            self.setStyleSheet("""
                FitStatusWidget {
                    background-color: #4a1e1e;
                    border: 1px solid #f44336;
                    border-radius: 4px;
                }
                QLabel { color: #f44336; }
            """)


class AdjustmentOptionsWidget(QFrame):
    """Widget con opciones de ajuste cuando el texto no cabe."""
    
    option_selected = pyqtSignal(str, float)  # (tipo, valor)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            AdjustmentOptionsWidget {
                background-color: #2d2d30;
                border: 1px solid #555;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Título
        title = QLabel("⚙️ Opciones de ajuste:")
        title.setStyleSheet("font-weight: bold; color: #ffcc00; font-size: 14px;")
        layout.addWidget(title)
        
        # Opción A: Recortar
        self.option_a_frame = self._create_option_frame(
            "A", "✂️ Recortar texto", 
            "Elimina caracteres del final hasta que quepa"
        )
        self.btn_truncate = self.option_a_frame.findChild(QPushButton)
        self.btn_truncate.clicked.connect(lambda: self.option_selected.emit("truncate", 0))
        layout.addWidget(self.option_a_frame)
        
        # Opción B: Reducir espaciado
        self.option_b_frame = QFrame()
        self.option_b_frame.setStyleSheet("background: #252526; border-radius: 4px; padding: 8px;")
        b_layout = QVBoxLayout(self.option_b_frame)
        
        b_header = QHBoxLayout()
        b_label = QLabel("B - 📏 Reducir espaciado entre letras")
        b_label.setStyleSheet("font-weight: bold; color: white;")
        b_header.addWidget(b_label)
        self.btn_spacing = QPushButton("Aplicar")
        self.btn_spacing.setStyleSheet("""
            QPushButton {
                background: #0078d4; color: white;
                border: none; padding: 5px 15px; border-radius: 3px;
            }
            QPushButton:hover { background: #1084d8; }
        """)
        b_header.addWidget(self.btn_spacing)
        b_layout.addLayout(b_header)
        
        # Slider para espaciado
        spacing_layout = QHBoxLayout()
        spacing_layout.addWidget(QLabel("Reducción:"))
        self.spacing_slider = QSlider(Qt.Horizontal)
        self.spacing_slider.setRange(0, 30)
        self.spacing_slider.setValue(10)
        spacing_layout.addWidget(self.spacing_slider)
        self.spacing_value = QLabel("10%")
        self.spacing_value.setMinimumWidth(40)
        spacing_layout.addWidget(self.spacing_value)
        b_layout.addLayout(spacing_layout)
        
        self.spacing_slider.valueChanged.connect(
            lambda v: self.spacing_value.setText(f"{v}%")
        )
        self.btn_spacing.clicked.connect(
            lambda: self.option_selected.emit("spacing", self.spacing_slider.value())
        )
        layout.addWidget(self.option_b_frame)
        
        # Opción C: Reducir tamaño
        self.option_c_frame = QFrame()
        self.option_c_frame.setStyleSheet("background: #252526; border-radius: 4px; padding: 8px;")
        c_layout = QVBoxLayout(self.option_c_frame)
        
        c_header = QHBoxLayout()
        c_label = QLabel("C - 🔍 Reducir tamaño de fuente")
        c_label.setStyleSheet("font-weight: bold; color: white;")
        c_header.addWidget(c_label)
        self.btn_size = QPushButton("Aplicar")
        self.btn_size.setStyleSheet("""
            QPushButton {
                background: #0078d4; color: white;
                border: none; padding: 5px 15px; border-radius: 3px;
            }
            QPushButton:hover { background: #1084d8; }
        """)
        c_header.addWidget(self.btn_size)
        c_layout.addLayout(c_header)
        
        # Slider para tamaño
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Reducción:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(0, 30)  # Máximo 30% reducción (mínimo 70% del original)
        self.size_slider.setValue(10)
        size_layout.addWidget(self.size_slider)
        self.size_value = QLabel("10%")
        self.size_value.setMinimumWidth(40)
        size_layout.addWidget(self.size_value)
        c_layout.addLayout(size_layout)
        
        self.size_slider.valueChanged.connect(
            lambda v: self.size_value.setText(f"{v}%")
        )
        self.btn_size.clicked.connect(
            lambda: self.option_selected.emit("size", self.size_slider.value())
        )
        layout.addWidget(self.option_c_frame)
        
        # Inicialmente oculto
        self.hide()
    
    def _create_option_frame(self, letter: str, title: str, desc: str) -> QFrame:
        """Crea un frame para una opción."""
        frame = QFrame()
        frame.setStyleSheet("background: #252526; border-radius: 4px; padding: 8px;")
        layout = QVBoxLayout(frame)
        
        header = QHBoxLayout()
        label = QLabel(f"{letter} - {title}")
        label.setStyleSheet("font-weight: bold; color: white;")
        header.addWidget(label)
        
        btn = QPushButton("Aplicar")
        btn.setStyleSheet("""
            QPushButton {
                background: #0078d4; color: white;
                border: none; padding: 5px 15px; border-radius: 3px;
            }
            QPushButton:hover { background: #1084d8; }
        """)
        header.addWidget(btn)
        layout.addLayout(header)
        
        desc_label = QLabel(desc)
        desc_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(desc_label)
        
        return frame


class EnhancedTextEditDialog(QDialog):
    """
    Diálogo mejorado para edición de texto con validación en tiempo real.
    
    PHASE2-201: Implementación completa.
    
    Features:
    - Preview en vivo del texto con fuente exacta
    - Validación "cabe/no cabe" sin lag
    - Opciones (A) Recortar, (B) Espaciado, (C) Tamaño si no cabe
    - Checkboxes para bold
    - Retorna TextEditResult con todos los cambios
    """
    
    def __init__(
        self, 
        original_text: str,
        max_width: float = 200,
        font_descriptor: Any = None,  # FontDescriptor
        detected_bold: Optional[bool] = None,
        parent=None
    ):
        super().__init__(parent)
        
        self.original_text = original_text
        self.max_width = max_width
        self.font_descriptor = font_descriptor
        self.detected_bold = detected_bold
        
        # Estado
        self._current_text = original_text
        self._tracking_reduction = 0.0
        self._size_reduction = 0.0
        self._was_truncated = False
        self._warnings = []
        
        # Extraer info de fuente
        if font_descriptor:
            self._font_name = getattr(font_descriptor, 'name', 'Arial')
            self._font_size = int(getattr(font_descriptor, 'size', 12))
            self._is_bold = getattr(font_descriptor, 'possible_bold', False) or False
            color_val = getattr(font_descriptor, 'color', '#000000')
            self._color = QColor(color_val) if isinstance(color_val, str) else QColor(0, 0, 0)
        else:
            self._font_name = 'Arial'
            self._font_size = 12
            self._is_bold = False
            self._color = QColor(0, 0, 0)
        
        self.setup_ui()
        self.connect_signals()
        
        # Validación inicial
        QTimer.singleShot(100, self.validate_text)
    
    def setup_ui(self):
        """Configura la interfaz."""
        self.setWindowTitle("✏️ Editar Texto")
        self.setMinimumSize(550, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #ffffff;
            }
            QTextEdit {
                background-color: #2d2d30;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
            }
            QCheckBox {
                color: #ffffff;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton:disabled {
                background-color: #555;
            }
            QPushButton.cancel {
                background-color: #3d3d3d;
            }
            QPushButton.cancel:hover {
                background-color: #4d4d4d;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header con info de fuente
        header = QLabel(f"📝 Fuente: {self._font_name} {self._font_size}pt")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078d4;")
        layout.addWidget(header)
        
        # Texto original (solo lectura)
        orig_group = QGroupBox("Texto Original")
        orig_group.setStyleSheet("""
            QGroupBox {
                color: #888;
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
        orig_layout = QVBoxLayout(orig_group)
        self.original_label = QLabel(self.original_text)
        self.original_label.setWordWrap(True)
        self.original_label.setStyleSheet("color: #888; font-style: italic;")
        orig_layout.addWidget(self.original_label)
        layout.addWidget(orig_group)
        
        # Campo de edición
        edit_group = QGroupBox("Nuevo Texto")
        edit_group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 1px solid #0078d4;
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
        edit_layout = QVBoxLayout(edit_group)
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.original_text)
        self.text_edit.setMaximumHeight(100)
        edit_layout.addWidget(self.text_edit)
        layout.addWidget(edit_group)
        
        # Preview en vivo
        preview_group = QGroupBox("Vista Previa")
        preview_group.setStyleSheet("""
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
        preview_layout = QVBoxLayout(preview_group)
        self.preview_widget = TextPreviewWidget()
        self.preview_widget.set_font(self._font_name, self._font_size, self._is_bold, self._color)
        self.preview_widget.set_text(self.original_text)
        preview_layout.addWidget(self.preview_widget)
        layout.addWidget(preview_group)
        
        # Estado de si cabe
        self.fit_status = FitStatusWidget()
        layout.addWidget(self.fit_status)
        
        # Opciones de ajuste (inicialmente ocultas)
        self.adjustment_options = AdjustmentOptionsWidget()
        layout.addWidget(self.adjustment_options)
        
        # Opciones de negrita
        bold_frame = QFrame()
        bold_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        bold_layout = QVBoxLayout(bold_frame)
        
        bold_title = QLabel("🔤 Opciones de Negrita")
        bold_title.setStyleSheet("font-weight: bold; color: #ffcc00;")
        bold_layout.addWidget(bold_title)
        
        # Checkbox mantener negrita original
        self.keep_bold_checkbox = QCheckBox("Mantener negrita del original")
        if self.detected_bold:
            self.keep_bold_checkbox.setChecked(True)
            self.keep_bold_checkbox.setEnabled(True)
        else:
            self.keep_bold_checkbox.setChecked(False)
            self.keep_bold_checkbox.setEnabled(self.detected_bold is not None)
        bold_layout.addWidget(self.keep_bold_checkbox)
        
        # Checkbox aplicar negrita
        self.apply_bold_checkbox = QCheckBox("Aplicar negrita al nuevo texto")
        self.apply_bold_checkbox.setChecked(self._is_bold)
        bold_layout.addWidget(self.apply_bold_checkbox)
        
        # Info de detección
        if self.detected_bold is True:
            detect_info = QLabel("ℹ️ Se detectó negrita en el texto original")
            detect_info.setStyleSheet("color: #4caf50; font-size: 11px;")
        elif self.detected_bold is False:
            detect_info = QLabel("ℹ️ No se detectó negrita en el texto original")
            detect_info.setStyleSheet("color: #888; font-size: 11px;")
        else:
            detect_info = QLabel("ℹ️ No se pudo determinar si hay negrita")
            detect_info.setStyleSheet("color: #ff9800; font-size: 11px;")
        bold_layout.addWidget(detect_info)
        
        layout.addWidget(bold_frame)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.setProperty("class", "cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        btn_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton("✓ Aceptar")
        btn_layout.addWidget(self.ok_btn)
        
        layout.addLayout(btn_layout)
    
    def connect_signals(self):
        """Conecta las señales."""
        self.text_edit.textChanged.connect(self.on_text_changed)
        self.apply_bold_checkbox.stateChanged.connect(self.on_bold_changed)
        self.keep_bold_checkbox.stateChanged.connect(self.on_keep_bold_changed)
        self.adjustment_options.option_selected.connect(self.apply_adjustment)
        
        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self.accept)
    
    def on_text_changed(self):
        """Maneja el cambio de texto."""
        self._current_text = self.text_edit.toPlainText()
        self.preview_widget.set_text(self._current_text)
        self.validate_text()
    
    def on_bold_changed(self, state):
        """Maneja el cambio del checkbox de bold."""
        self._is_bold = state == Qt.Checked
        self.preview_widget.set_font(
            self._font_name, 
            self._font_size, 
            self._is_bold, 
            self._color
        )
        self.validate_text()
    
    def on_keep_bold_changed(self, state):
        """Maneja el cambio de mantener bold."""
        if state == Qt.Checked and self.detected_bold:
            self.apply_bold_checkbox.setChecked(True)
    
    def validate_text(self):
        """Valida si el texto cabe en el área disponible."""
        text = self._current_text
        
        # Calcular ancho actual (simplificado)
        current_width = self.preview_widget.get_text_width(text)
        
        # Calcular si cabe
        fits = current_width <= self.max_width
        overflow_percent = ((current_width - self.max_width) / self.max_width * 100) if not fits else 0
        
        self.fit_status.set_fits(fits, overflow_percent)
        
        if fits:
            self.adjustment_options.hide()
            self.ok_btn.setEnabled(True)
        else:
            self.adjustment_options.show()
            # Permitir guardar aunque no quepa (el usuario decidió)
            self.ok_btn.setEnabled(True)
    
    def apply_adjustment(self, option_type: str, value: float):
        """Aplica un ajuste al texto."""
        if option_type == "truncate":
            self._apply_truncate()
        elif option_type == "spacing":
            self._apply_spacing_reduction(value)
        elif option_type == "size":
            self._apply_size_reduction(value)
    
    def _apply_truncate(self):
        """Recorta el texto hasta que quepa."""
        text = self._current_text
        while text and self.preview_widget.get_text_width(text) > self.max_width:
            text = text[:-1]
        
        if text != self._current_text:
            text = text.rstrip() + "..."
            self._was_truncated = True
            self._warnings.append(f"Texto recortado de {len(self._current_text)} a {len(text)} caracteres")
        
        self.text_edit.setPlainText(text)
    
    def _apply_spacing_reduction(self, percent: float):
        """Aplica reducción de espaciado."""
        self._tracking_reduction = percent
        self._warnings.append(f"Espaciado reducido {percent}%")
        
        # Notificar al usuario
        QMessageBox.information(
            self,
            "Ajuste Aplicado",
            f"Se reducirá el espaciado entre letras un {percent}%.\n"
            "Este cambio se aplicará al guardar el PDF."
        )
        
        # Re-validar
        self.validate_text()
    
    def _apply_size_reduction(self, percent: float):
        """Aplica reducción de tamaño."""
        if percent > 30:
            percent = 30  # Máximo 30% (mínimo 70% del original)
        
        self._size_reduction = percent
        new_size = int(self._font_size * (1 - percent / 100))
        
        self._warnings.append(f"Tamaño reducido de {self._font_size}pt a {new_size}pt ({percent}%)")
        
        # Actualizar preview
        self.preview_widget.set_font(
            self._font_name,
            new_size,
            self._is_bold,
            self._color
        )
        
        # Re-validar
        self.validate_text()
    
    def get_result(self) -> TextEditResult:
        """Retorna el resultado de la edición."""
        return TextEditResult(
            text=self._current_text,
            original_text=self.original_text,
            font_descriptor=self.font_descriptor,
            bold_applied=self.apply_bold_checkbox.isChecked(),
            tracking_reduced=self._tracking_reduction,
            size_reduced=self._size_reduction,
            was_truncated=self._was_truncated,
            warnings=self._warnings.copy()
        )
    
    def get_final_text(self) -> Tuple[str, Dict[str, Any]]:
        """
        Retorna el texto final y un reporte de cambios.
        
        Returns:
            (texto_final, diccionario_de_cambios)
        """
        result = self.get_result()
        
        change_report = {
            'old_text': result.original_text,
            'new_text': result.text,
            'font_used': self._font_name,
            'font_size': self._font_size * (1 - self._size_reduction / 100),
            'bold_applied': result.bold_applied,
            'tracking_reduced': result.tracking_reduced,
            'size_reduced': result.size_reduced,
            'was_truncated': result.was_truncated,
            'warnings': result.warnings
        }
        
        return result.text, change_report
    
    def get_styling_choices(self) -> Dict[str, Any]:
        """Retorna las opciones de estilo seleccionadas."""
        return {
            'font_name': self._font_name,
            'font_size': self._font_size * (1 - self._size_reduction / 100),
            'bold': self.apply_bold_checkbox.isChecked(),
            'keep_original_bold': self.keep_bold_checkbox.isChecked(),
            'tracking_reduction': self._tracking_reduction,
            'size_reduction': self._size_reduction,
            'color': self._color.name()
        }


def show_text_edit_dialog(
    parent,
    original_text: str,
    max_width: float = 200,
    font_descriptor=None,
    detected_bold: Optional[bool] = None
) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Muestra el diálogo de edición de texto.
    
    Returns:
        (nuevo_texto, reporte_cambios) si se aceptó, None si se canceló
    """
    dialog = EnhancedTextEditDialog(
        original_text=original_text,
        max_width=max_width,
        font_descriptor=font_descriptor,
        detected_bold=detected_bold,
        parent=parent
    )
    
    if dialog.exec_() == QDialog.Accepted:
        return dialog.get_final_text()
    
    return None

"""
Elementos gráficos personalizados para el visor de PDF.
Incluye rectángulos de selección, items de texto editables y diálogos.
"""

from PyQt5.QtWidgets import (
    QGraphicsRectItem, QGraphicsTextItem, QGraphicsDropShadowEffect,
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QSpinBox, QCheckBox, QDialogButtonBox, QGroupBox
)
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPen, QBrush, QColor, QCursor, QFont


class SelectionRect(QGraphicsRectItem):
    """Rectángulo de selección visual mejorado."""
    
    def __init__(self, rect=QRectF(), mode='select'):
        super().__init__(rect)
        self.mode = mode
        self.update_style()
        self.setZValue(100)
    
    def update_style(self):
        if self.mode == 'delete':
            # Rojo para eliminación
            self.setPen(QPen(QColor(255, 80, 80), 2, Qt.SolidLine))
            self.setBrush(QBrush(QColor(255, 0, 0, 40)))
        elif self.mode == 'highlight':
            # Amarillo para resaltado
            self.setPen(QPen(QColor(255, 200, 0), 2, Qt.SolidLine))
            self.setBrush(QBrush(QColor(255, 255, 0, 60)))
        else:
            # Azul para selección normal
            self.setPen(QPen(QColor(0, 120, 215), 2, Qt.DashLine))
            self.setBrush(QBrush(QColor(0, 120, 215, 40)))
    
    def set_mode(self, mode):
        self.mode = mode
        self.update_style()


class DeletePreviewRect(QGraphicsRectItem):
    """Rectángulo de previsualización de borrado con animación."""
    
    def __init__(self, rect=QRectF()):
        super().__init__(rect)
        self.setPen(QPen(QColor(255, 50, 50), 3, Qt.SolidLine))
        self.setBrush(QBrush(QColor(255, 0, 0, 80)))
        self.setZValue(90)
        
        # Efecto de sombra
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(255, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)


class FloatingLabel(QGraphicsTextItem):
    """Etiqueta flotante para mostrar información."""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setDefaultTextColor(QColor(255, 255, 255))
        font = QFont("Segoe UI", 10, QFont.Bold)
        self.setFont(font)
        self.setZValue(200)
    
    def set_background(self, color):
        pass  # Se maneja en paint


class HighlightRect(QGraphicsRectItem):
    """Rectángulo de resaltado."""
    
    def __init__(self, rect=QRectF(), color=QColor(255, 255, 0, 100)):
        super().__init__(rect)
        self.setPen(QPen(Qt.NoPen))
        self.setBrush(QBrush(color))
        self.setZValue(50)


class TextEditDialog(QDialog):
    """
    Diálogo personalizado para editar texto con opciones de formato.
    """
    def __init__(self, text: str = "", font_size: int = 12, is_bold: bool = False, 
                 title: str = "Editar texto", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Grupo de texto
        text_group = QGroupBox("Contenido")
        text_layout = QVBoxLayout(text_group)
        
        self.text_edit = QLineEdit(text)
        self.text_edit.setPlaceholderText("Escribe el texto aquí...")
        self.text_edit.selectAll()
        text_layout.addWidget(self.text_edit)
        layout.addWidget(text_group)
        
        # Grupo de formato
        format_group = QGroupBox("Formato")
        format_layout = QHBoxLayout(format_group)
        
        # Tamaño de fuente - permitir desde 1pt para máxima flexibilidad
        size_layout = QHBoxLayout()
        size_label = QLabel("Tamaño:")
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 144)  # Rango ampliado: 1pt a 144pt
        self.size_spin.setValue(int(font_size))
        self.size_spin.setSuffix(" pt")
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.size_spin)
        format_layout.addLayout(size_layout)
        
        # Checkbox para negrita
        self.bold_check = QCheckBox("Negrita")
        self.bold_check.setChecked(is_bold)
        format_layout.addWidget(self.bold_check)
        
        format_layout.addStretch()
        layout.addWidget(format_group)
        
        # Botones
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Foco inicial en el texto
        self.text_edit.setFocus()
    
    def get_values(self):
        """Retorna los valores del diálogo."""
        return {
            'text': self.text_edit.text(),
            'font_size': self.size_spin.value(),
            'is_bold': self.bold_check.isChecked()
        }


class EditableTextItem(QGraphicsRectItem):
    """
    Representa un texto editable añadido al PDF.
    Permite seleccionar, mover y editar el texto.
    
    Para PDFs de imagen: el texto se muestra visualmente como capa superpuesta
    y solo se escribe al PDF cuando se "confirma" (al guardar o deseleccionar).
    """
    
    def __init__(self, rect: QRectF, text: str, font_size: float = 12, 
                 color: tuple = (0, 0, 0), page_num: int = 0, 
                 font_name: str = "helv", is_bold: bool = False, parent=None):
        super().__init__(rect, parent)
        self.text = text
        self.font_size = font_size
        self.text_color = color
        self.page_num = page_num
        self.font_name = font_name  # Nombre de la fuente
        self.is_bold = is_bold  # Si es negrita
        self.pdf_rect = None  # Se establece después de añadir al PDF
        
        # NUEVO: Flags para manejo en PDFs de imagen
        self.is_overlay = False  # True = solo visual, no escrito al PDF aún
        self.pending_write = False  # True = necesita escribirse al PDF
        
        # Estado visual
        self.is_selected = False
        self.is_hovered = False
        
        # Configuración visual base (invisible hasta hover/select)
        self._update_visual()
        self.setZValue(150)
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        
        # Flags para interacción
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.ItemSendsGeometryChanges, True)
    
    def _update_visual(self):
        """Actualiza el estilo visual según el estado."""
        if self.is_selected:
            # Seleccionado: borde azul sólido
            self.setPen(QPen(QColor(0, 120, 215), 2, Qt.SolidLine))
            self.setBrush(QBrush(QColor(0, 120, 215, 30)))
        elif self.is_hovered:
            # Hover: borde azul punteado
            self.setPen(QPen(QColor(0, 120, 215), 1, Qt.DashLine))
            self.setBrush(QBrush(QColor(0, 120, 215, 15)))
        else:
            # Normal: invisible
            self.setPen(QPen(Qt.NoPen))
            self.setBrush(QBrush(Qt.NoBrush))
    
    def set_selected(self, selected: bool):
        """Establece el estado de selección."""
        self.is_selected = selected
        self._update_visual()
    
    def hoverEnterEvent(self, event):
        """Mouse entra en el área."""
        self.is_hovered = True
        self._update_visual()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """Mouse sale del área."""
        self.is_hovered = False
        self._update_visual()
        super().hoverLeaveEvent(event)
    
    def paint(self, painter, option, widget=None):
        """Dibuja el item. Si es overlay, también dibuja el texto.
        
        CRÍTICO para PDFs de imagen: asegurar que el rect sea lo suficientemente
        grande y que el texto se dibuje COMPLETAMENTE sin fragmentación.
        Soporta texto multilínea con saltos de línea (\n).
        Si tiene text_runs, dibuja cada run con su estilo individual.
        """
        # Primero dibujar el rectángulo base (bordes de selección)
        super().paint(painter, option, widget)
        
        # Si es overlay, dibujar el texto visualmente
        if self.is_overlay and self.text:
            rect = self.rect()
            
            from PyQt5.QtGui import QFontMetrics
            
            # Verificar si tiene estilos mixtos (text_runs)
            text_runs = getattr(self, 'text_runs', None)
            has_mixed = getattr(self, 'has_mixed_styles', False) and text_runs
            
            if has_mixed and text_runs:
                # Dibujar con múltiples estilos usando text_runs
                self._paint_with_runs(painter, rect, text_runs)
            else:
                # Dibujar con estilo uniforme
                self._paint_uniform(painter, rect)
    
    def _paint_uniform(self, painter, rect):
        """Dibuja el texto con estilo uniforme."""
        from PyQt5.QtGui import QFontMetrics
        
        # Configurar fuente
        font = QFont("Helvetica", int(self.font_size))
        if self.is_bold:
            font.setBold(True)
        painter.setFont(font)
        
        metrics = QFontMetrics(font)
        
        # Configurar color
        r, g, b = self.text_color
        # Convertir de 0-1 a 0-255 si es necesario
        if max(r, g, b) <= 1:
            r, g, b = int(r * 255), int(g * 255), int(b * 255)
        painter.setPen(QColor(r, g, b))
        
        # Dibujar texto multilínea línea por línea
        lines = self.text.split('\n')
        line_height = metrics.height()
        y_offset = metrics.ascent()  # Empezar desde el baseline de la primera línea
        
        for i, line in enumerate(lines):
            if line:  # Solo dibujar si la línea tiene contenido
                painter.drawText(
                    int(rect.x()), 
                    int(rect.y() + y_offset + i * line_height), 
                    line
                )
    
    def _paint_with_runs(self, painter, rect, text_runs):
        """Dibuja el texto usando runs con estilos individuales."""
        from PyQt5.QtGui import QFontMetrics
        
        x_offset = int(rect.x())
        current_line_y = 0
        last_line_y = None
        
        # Fuente base para calcular line_height
        base_font = QFont("Helvetica", int(self.font_size))
        base_metrics = QFontMetrics(base_font)
        line_height = base_metrics.height()
        y_offset = base_metrics.ascent()
        
        for run in text_runs:
            run_text = run.get('text', '')
            if not run_text:
                continue
            
            # Detectar cambio de línea
            line_y = run.get('line_y', 0)
            if last_line_y is not None and line_y != last_line_y:
                # Nueva línea - reiniciar x y avanzar y
                x_offset = int(rect.x())
                current_line_y += line_height
            last_line_y = line_y
            
            # Configurar fuente del run
            font_size = run.get('font_size', self.font_size)
            is_bold = run.get('is_bold', False)
            is_italic = run.get('is_italic', False)
            
            font = QFont("Helvetica", int(font_size))
            if is_bold:
                font.setBold(True)
            if is_italic:
                font.setItalic(True)
            painter.setFont(font)
            
            metrics = QFontMetrics(font)
            
            # Configurar color del run
            color_str = run.get('color', '#000000')
            try:
                if isinstance(color_str, str):
                    color = QColor(color_str)
                else:
                    r, g, b = color_str
                    if max(r, g, b) <= 1:
                        r, g, b = int(r * 255), int(g * 255), int(b * 255)
                    color = QColor(r, g, b)
            except:
                color = QColor(0, 0, 0)
            painter.setPen(color)
            
            # Dibujar el texto del run (manejar saltos de línea internos)
            run_lines = run_text.split('\n')
            for i, line in enumerate(run_lines):
                if i > 0:
                    # Salto de línea interno - nueva línea
                    x_offset = int(rect.x())
                    current_line_y += line_height
                
                if line:
                    painter.drawText(
                        x_offset, 
                        int(rect.y() + y_offset + current_line_y), 
                        line
                    )
                    x_offset += metrics.horizontalAdvance(line)


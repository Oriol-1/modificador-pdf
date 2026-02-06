"""
NoReflowEditor - Editor de texto con cajas fijas (sin reflow).

PHASE3-3C06: Modo "no reflow" que preserva la posición exacta de cada línea/span.

Características:
- Cada línea es una "caja" independiente con posición fija
- El texto NO fluye a la siguiente línea al editar
- Visualización de límites del bbox original
- Indicador visual de overflow en tiempo real
- Opciones de ajuste cuando el texto no cabe:
  - Recortar texto
  - Reducir tracking (char_spacing)
  - Reducir tamaño de fuente
  - Escalar horizontalmente

Dependencias:
- 3C-05: PDFTextEditor (EditMode, FitStatus, EditorConfig)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, Tuple

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSlider, QPushButton, QGroupBox, QRadioButton, QButtonGroup,
    QLineEdit, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QRectF
from PyQt5.QtGui import QFont, QColor, QFontMetrics, QPainter, QPen, QBrush


# ================== Enums ==================


class OverflowStrategy(Enum):
    """Estrategia para manejar texto que no cabe."""
    NONE = "none"                   # No hacer nada (solo advertir)
    TRUNCATE = "truncate"           # Recortar texto con elipsis
    REDUCE_TRACKING = "tracking"    # Reducir espaciado entre caracteres
    REDUCE_SIZE = "size"            # Reducir tamaño de fuente
    SCALE_HORIZONTAL = "scale"      # Escalar horizontalmente


class BboxDisplayMode(Enum):
    """Modo de visualización del bbox."""
    HIDDEN = "hidden"           # No mostrar bbox
    OUTLINE = "outline"         # Solo borde
    FILLED = "filled"           # Relleno semitransparente
    GUIDE_LINES = "guide_lines" # Líneas guía extendidas


# ================== Dataclasses ==================


@dataclass
class BboxConstraints:
    """Restricciones del bbox para el modo no-reflow."""
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 20.0
    padding_left: float = 0.0
    padding_right: float = 0.0
    padding_top: float = 0.0
    padding_bottom: float = 0.0
    
    @property
    def inner_width(self) -> float:
        """Ancho interno disponible (sin padding)."""
        return self.width - self.padding_left - self.padding_right
    
    @property
    def inner_height(self) -> float:
        """Alto interno disponible (sin padding)."""
        return self.height - self.padding_top - self.padding_bottom
    
    @property
    def rect(self) -> QRectF:
        """Obtener como QRectF."""
        return QRectF(self.x, self.y, self.width, self.height)
    
    @property
    def inner_rect(self) -> QRectF:
        """Obtener rect interno como QRectF."""
        return QRectF(
            self.x + self.padding_left,
            self.y + self.padding_top,
            self.inner_width,
            self.inner_height
        )
    
    @classmethod
    def from_bbox(cls, bbox: Tuple[float, float, float, float]) -> 'BboxConstraints':
        """Crear desde tuple bbox (x0, y0, x1, y1)."""
        x0, y0, x1, y1 = bbox
        return cls(
            x=x0,
            y=y0,
            width=x1 - x0,
            height=y1 - y0
        )


@dataclass
class AdjustmentResult:
    """Resultado de un ajuste de texto."""
    strategy: OverflowStrategy
    original_text: str
    adjusted_text: str
    fits: bool
    
    # Métricas del ajuste
    original_width: float = 0.0
    adjusted_width: float = 0.0
    available_width: float = 0.0
    
    # Parámetros aplicados
    char_spacing_delta: float = 0.0
    font_size_delta: float = 0.0
    scale_factor: float = 1.0
    truncated_chars: int = 0
    
    @property
    def overflow_amount(self) -> float:
        """Cantidad de overflow (negativo si cabe)."""
        return self.adjusted_width - self.available_width
    
    @property
    def fit_percentage(self) -> float:
        """Porcentaje de uso del espacio disponible."""
        if self.available_width <= 0:
            return 0.0
        return (self.adjusted_width / self.available_width) * 100


@dataclass
class NoReflowConfig:
    """Configuración del modo no-reflow."""
    default_strategy: OverflowStrategy = OverflowStrategy.NONE
    bbox_display: BboxDisplayMode = BboxDisplayMode.OUTLINE
    show_overflow_warning: bool = True
    allow_overflow: bool = False
    
    # Límites para ajustes automáticos
    min_tracking: float = -2.0      # Mínimo char_spacing en pt
    max_tracking: float = 5.0       # Máximo char_spacing en pt
    min_size_factor: float = 0.7    # Mínimo tamaño relativo (70%)
    max_size_factor: float = 1.2    # Máximo tamaño relativo (120%)
    min_scale: float = 0.8          # Mínima escala horizontal (80%)
    max_scale: float = 1.2          # Máxima escala horizontal (120%)
    
    # Visualización
    bbox_color: str = "#3498db"
    overflow_color: str = "#e74c3c"
    fit_color: str = "#27ae60"


# ================== Widgets de Visualización ==================


class BboxOverlay(QWidget):
    """
    Widget overlay que muestra los límites del bbox.
    
    Se superpone sobre el área de edición para mostrar visualmente
    los límites de la caja fija.
    """
    
    def __init__(
        self,
        constraints: Optional[BboxConstraints] = None,
        config: Optional[NoReflowConfig] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._constraints = constraints or BboxConstraints()
        self._config = config or NoReflowConfig()
        self._is_overflow = False
        self._current_width = 0.0
        
        # Transparente para eventos de mouse
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
    
    def set_constraints(self, constraints: BboxConstraints) -> None:
        """Establecer restricciones del bbox."""
        self._constraints = constraints
        self.update()
    
    def set_overflow(self, is_overflow: bool, current_width: float = 0.0) -> None:
        """Actualizar estado de overflow."""
        self._is_overflow = is_overflow
        self._current_width = current_width
        self.update()
    
    def set_display_mode(self, mode: BboxDisplayMode) -> None:
        """Cambiar modo de visualización."""
        self._config.bbox_display = mode
        self.update()
    
    def paintEvent(self, event) -> None:
        """Dibujar el overlay del bbox."""
        if self._config.bbox_display == BboxDisplayMode.HIDDEN:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Determinar color según estado
        if self._is_overflow:
            color = QColor(self._config.overflow_color)
        else:
            color = QColor(self._config.bbox_color)
        
        rect = self._constraints.rect
        
        if self._config.bbox_display == BboxDisplayMode.OUTLINE:
            pen = QPen(color, 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(rect)
            
        elif self._config.bbox_display == BboxDisplayMode.FILLED:
            pen = QPen(color, 2, Qt.SolidLine)
            fill_color = QColor(color)
            fill_color.setAlpha(30)
            painter.setPen(pen)
            painter.setBrush(QBrush(fill_color))
            painter.drawRect(rect)
            
        elif self._config.bbox_display == BboxDisplayMode.GUIDE_LINES:
            pen = QPen(color, 1, Qt.DotLine)
            painter.setPen(pen)
            
            # Líneas horizontales extendidas
            painter.drawLine(0, int(rect.top()), self.width(), int(rect.top()))
            painter.drawLine(0, int(rect.bottom()), self.width(), int(rect.bottom()))
            
            # Líneas verticales extendidas
            painter.drawLine(int(rect.left()), 0, int(rect.left()), self.height())
            painter.drawLine(int(rect.right()), 0, int(rect.right()), self.height())
            
            # Bbox principal
            pen.setStyle(Qt.SolidLine)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(rect)
        
        # Indicador de overflow
        if self._is_overflow and self._current_width > 0:
            # Línea que muestra el desbordamiento
            overflow_pen = QPen(QColor(self._config.overflow_color), 2, Qt.SolidLine)
            painter.setPen(overflow_pen)
            overflow_x = rect.left() + self._current_width
            painter.drawLine(
                int(rect.right()), int(rect.top()),
                int(overflow_x), int(rect.top())
            )
            painter.drawLine(
                int(rect.right()), int(rect.bottom()),
                int(overflow_x), int(rect.bottom())
            )


class FitIndicatorWidget(QFrame):
    """
    Widget que muestra indicador visual de ajuste.
    
    Muestra barra de progreso con el porcentaje de uso del espacio
    y cambia de color según el estado.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.setMinimumHeight(24)
        self.setMaximumHeight(24)
        
        self._percentage = 0.0
        self._fits = True
        
        # Colores
        self._fit_color = QColor("#27ae60")
        self._tight_color = QColor("#f39c12")
        self._overflow_color = QColor("#e74c3c")
    
    def set_percentage(self, percentage: float, fits: bool) -> None:
        """Actualizar porcentaje y estado."""
        self._percentage = percentage
        self._fits = fits
        self.update()
    
    def paintEvent(self, event) -> None:
        """Dibujar indicador."""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fondo
        rect = self.contentsRect()
        painter.fillRect(rect, QColor("#f0f0f0"))
        
        # Determinar color y ancho
        if self._percentage <= 95:
            color = self._fit_color
        elif self._percentage <= 100:
            color = self._tight_color
        else:
            color = self._overflow_color
        
        # Barra de progreso (máximo 100% del ancho visual)
        bar_width = min(rect.width(), rect.width() * self._percentage / 100)
        bar_rect = QRectF(rect.left(), rect.top(), bar_width, rect.height())
        painter.fillRect(bar_rect, color)
        
        # Texto
        painter.setPen(Qt.black if self._percentage < 50 else Qt.white)
        text = f"{self._percentage:.1f}%"
        painter.drawText(rect, Qt.AlignCenter, text)
        
        # Marca de 100%
        if self._percentage > 100:
            painter.setPen(QPen(Qt.black, 2))
            x100 = rect.left() + rect.width()
            painter.drawLine(int(x100), rect.top(), int(x100), rect.bottom())


# ================== Widgets de Ajuste ==================


class TrackingAdjuster(QGroupBox):
    """
    Widget para ajustar el tracking (espaciado entre caracteres).
    """
    
    # Señales
    trackingChanged = pyqtSignal(float)
    
    def __init__(
        self,
        min_value: float = -2.0,
        max_value: float = 5.0,
        parent: Optional[QWidget] = None
    ):
        super().__init__("Tracking (espaciado)", parent)
        self._min = min_value
        self._max = max_value
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configurar UI."""
        layout = QHBoxLayout(self)
        
        # Slider
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(int(self._min * 100), int(self._max * 100))
        self._slider.setValue(0)
        self._slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self._slider, 1)
        
        # SpinBox
        self._spinbox = QDoubleSpinBox()
        self._spinbox.setRange(self._min, self._max)
        self._spinbox.setSingleStep(0.1)
        self._spinbox.setValue(0.0)
        self._spinbox.setSuffix(" pt")
        self._spinbox.valueChanged.connect(self._on_spinbox_changed)
        layout.addWidget(self._spinbox)
        
        # Reset
        self._reset_btn = QPushButton("↺")
        self._reset_btn.setFixedWidth(30)
        self._reset_btn.clicked.connect(self.reset)
        layout.addWidget(self._reset_btn)
    
    def _on_slider_changed(self, value: int) -> None:
        """Manejar cambio en slider."""
        float_value = value / 100.0
        self._spinbox.blockSignals(True)
        self._spinbox.setValue(float_value)
        self._spinbox.blockSignals(False)
        self.trackingChanged.emit(float_value)
    
    def _on_spinbox_changed(self, value: float) -> None:
        """Manejar cambio en spinbox."""
        self._slider.blockSignals(True)
        self._slider.setValue(int(value * 100))
        self._slider.blockSignals(False)
        self.trackingChanged.emit(value)
    
    def get_value(self) -> float:
        """Obtener valor actual."""
        return self._spinbox.value()
    
    def set_value(self, value: float) -> None:
        """Establecer valor."""
        self._spinbox.setValue(value)
    
    def reset(self) -> None:
        """Resetear a 0."""
        self.set_value(0.0)


class SizeAdjuster(QGroupBox):
    """
    Widget para ajustar el tamaño de fuente.
    """
    
    # Señales
    sizeChanged = pyqtSignal(float)  # Factor de escala
    
    def __init__(
        self,
        base_size: float = 12.0,
        min_factor: float = 0.7,
        max_factor: float = 1.2,
        parent: Optional[QWidget] = None
    ):
        super().__init__("Tamaño de fuente", parent)
        self._base_size = base_size
        self._min_factor = min_factor
        self._max_factor = max_factor
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configurar UI."""
        layout = QHBoxLayout(self)
        
        # Label de tamaño original
        self._base_label = QLabel(f"Base: {self._base_size:.1f}pt")
        layout.addWidget(self._base_label)
        
        # Slider
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(
            int(self._min_factor * 100),
            int(self._max_factor * 100)
        )
        self._slider.setValue(100)
        self._slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self._slider, 1)
        
        # Label de resultado
        self._result_label = QLabel(f"{self._base_size:.1f}pt")
        self._result_label.setMinimumWidth(60)
        layout.addWidget(self._result_label)
        
        # Reset
        self._reset_btn = QPushButton("↺")
        self._reset_btn.setFixedWidth(30)
        self._reset_btn.clicked.connect(self.reset)
        layout.addWidget(self._reset_btn)
    
    def _on_slider_changed(self, value: int) -> None:
        """Manejar cambio en slider."""
        factor = value / 100.0
        new_size = self._base_size * factor
        self._result_label.setText(f"{new_size:.1f}pt")
        self.sizeChanged.emit(factor)
    
    def set_base_size(self, size: float) -> None:
        """Establecer tamaño base."""
        self._base_size = size
        self._base_label.setText(f"Base: {size:.1f}pt")
        self._on_slider_changed(self._slider.value())
    
    def get_factor(self) -> float:
        """Obtener factor de escala actual."""
        return self._slider.value() / 100.0
    
    def get_size(self) -> float:
        """Obtener tamaño resultante."""
        return self._base_size * self.get_factor()
    
    def reset(self) -> None:
        """Resetear a 100%."""
        self._slider.setValue(100)


class HorizontalScaleAdjuster(QGroupBox):
    """
    Widget para ajustar la escala horizontal del texto.
    """
    
    # Señales
    scaleChanged = pyqtSignal(float)
    
    def __init__(
        self,
        min_scale: float = 0.8,
        max_scale: float = 1.2,
        parent: Optional[QWidget] = None
    ):
        super().__init__("Escala horizontal", parent)
        self._min_scale = min_scale
        self._max_scale = max_scale
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configurar UI."""
        layout = QHBoxLayout(self)
        
        # Slider
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(
            int(self._min_scale * 100),
            int(self._max_scale * 100)
        )
        self._slider.setValue(100)
        self._slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self._slider, 1)
        
        # Label de porcentaje
        self._label = QLabel("100%")
        self._label.setMinimumWidth(50)
        layout.addWidget(self._label)
        
        # Reset
        self._reset_btn = QPushButton("↺")
        self._reset_btn.setFixedWidth(30)
        self._reset_btn.clicked.connect(self.reset)
        layout.addWidget(self._reset_btn)
    
    def _on_slider_changed(self, value: int) -> None:
        """Manejar cambio en slider."""
        scale = value / 100.0
        self._label.setText(f"{value}%")
        self.scaleChanged.emit(scale)
    
    def get_scale(self) -> float:
        """Obtener escala actual."""
        return self._slider.value() / 100.0
    
    def reset(self) -> None:
        """Resetear a 100%."""
        self._slider.setValue(100)


class OverflowOptionsPanel(QGroupBox):
    """
    Panel con opciones para manejar el overflow.
    """
    
    # Señales
    strategySelected = pyqtSignal(OverflowStrategy)
    applyClicked = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Opciones de ajuste", parent)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configurar UI."""
        layout = QVBoxLayout(self)
        
        # Grupo de botones de radio
        self._button_group = QButtonGroup(self)
        
        # Opciones
        options = [
            (OverflowStrategy.NONE, "No ajustar (solo advertir)"),
            (OverflowStrategy.TRUNCATE, "Recortar texto (...)"),
            (OverflowStrategy.REDUCE_TRACKING, "Reducir espaciado"),
            (OverflowStrategy.REDUCE_SIZE, "Reducir tamaño"),
            (OverflowStrategy.SCALE_HORIZONTAL, "Escalar horizontalmente"),
        ]
        
        for strategy, text in options:
            radio = QRadioButton(text)
            radio.setProperty("strategy", strategy)
            self._button_group.addButton(radio)
            layout.addWidget(radio)
            
            if strategy == OverflowStrategy.NONE:
                radio.setChecked(True)
        
        self._button_group.buttonClicked.connect(self._on_button_clicked)
        
        # Botón aplicar
        self._apply_btn = QPushButton("Aplicar ajuste")
        self._apply_btn.clicked.connect(self.applyClicked.emit)
        layout.addWidget(self._apply_btn)
    
    def _on_button_clicked(self, button: QRadioButton) -> None:
        """Manejar selección de estrategia."""
        strategy = button.property("strategy")
        self.strategySelected.emit(strategy)
    
    def get_selected_strategy(self) -> OverflowStrategy:
        """Obtener estrategia seleccionada."""
        button = self._button_group.checkedButton()
        if button:
            return button.property("strategy")
        return OverflowStrategy.NONE
    
    def set_strategy(self, strategy: OverflowStrategy) -> None:
        """Establecer estrategia seleccionada."""
        for button in self._button_group.buttons():
            if button.property("strategy") == strategy:
                button.setChecked(True)
                break


# ================== Calculador de Ajustes ==================


class TextFitCalculator:
    """
    Calcula ajustes necesarios para que el texto quepa en una caja.
    """
    
    @staticmethod
    def calculate_text_width(
        text: str,
        font_name: str,
        font_size: float,
        char_spacing: float = 0.0,
        scale_x: float = 1.0
    ) -> float:
        """
        Calcular ancho del texto con propiedades dadas.
        
        Args:
            text: Texto a medir
            font_name: Nombre de la fuente
            font_size: Tamaño de fuente en puntos
            char_spacing: Espaciado adicional entre caracteres
            scale_x: Factor de escala horizontal
            
        Returns:
            Ancho estimado en puntos
        """
        font = QFont(font_name, int(font_size))
        metrics = QFontMetrics(font)
        
        # Ancho base
        base_width = metrics.horizontalAdvance(text)
        
        # Convertir pixels a puntos (aproximado, 96 DPI -> 72 pt/inch)
        base_width_pt = base_width * 72 / 96
        
        # Aplicar espaciado entre caracteres
        if char_spacing != 0 and len(text) > 1:
            base_width_pt += char_spacing * (len(text) - 1)
        
        # Aplicar escala horizontal
        base_width_pt *= scale_x
        
        return base_width_pt
    
    @staticmethod
    def fit_by_truncation(
        text: str,
        font_name: str,
        font_size: float,
        available_width: float,
        ellipsis: str = "..."
    ) -> AdjustmentResult:
        """
        Ajustar texto truncando con elipsis.
        """
        original_width = TextFitCalculator.calculate_text_width(
            text, font_name, font_size
        )
        
        if original_width <= available_width:
            return AdjustmentResult(
                strategy=OverflowStrategy.TRUNCATE,
                original_text=text,
                adjusted_text=text,
                fits=True,
                original_width=original_width,
                adjusted_width=original_width,
                available_width=available_width
            )
        
        # Calcular ancho del elipsis
        ellipsis_width = TextFitCalculator.calculate_text_width(
            ellipsis, font_name, font_size
        )
        
        # Buscar cuántos caracteres caben
        target_width = available_width - ellipsis_width
        
        for i in range(len(text), 0, -1):
            truncated = text[:i]
            width = TextFitCalculator.calculate_text_width(
                truncated, font_name, font_size
            )
            if width <= target_width:
                adjusted_text = truncated + ellipsis
                adjusted_width = TextFitCalculator.calculate_text_width(
                    adjusted_text, font_name, font_size
                )
                return AdjustmentResult(
                    strategy=OverflowStrategy.TRUNCATE,
                    original_text=text,
                    adjusted_text=adjusted_text,
                    fits=True,
                    original_width=original_width,
                    adjusted_width=adjusted_width,
                    available_width=available_width,
                    truncated_chars=len(text) - i
                )
        
        # No cabe ni un carácter
        return AdjustmentResult(
            strategy=OverflowStrategy.TRUNCATE,
            original_text=text,
            adjusted_text=ellipsis,
            fits=False,
            original_width=original_width,
            adjusted_width=ellipsis_width,
            available_width=available_width,
            truncated_chars=len(text)
        )
    
    @staticmethod
    def fit_by_tracking(
        text: str,
        font_name: str,
        font_size: float,
        available_width: float,
        min_tracking: float = -2.0,
        max_tracking: float = 5.0
    ) -> AdjustmentResult:
        """
        Ajustar texto modificando el tracking.
        """
        original_width = TextFitCalculator.calculate_text_width(
            text, font_name, font_size
        )
        
        if original_width <= available_width:
            return AdjustmentResult(
                strategy=OverflowStrategy.REDUCE_TRACKING,
                original_text=text,
                adjusted_text=text,
                fits=True,
                original_width=original_width,
                adjusted_width=original_width,
                available_width=available_width
            )
        
        # Calcular tracking necesario
        overflow = original_width - available_width
        num_spaces = len(text) - 1
        
        if num_spaces <= 0:
            return AdjustmentResult(
                strategy=OverflowStrategy.REDUCE_TRACKING,
                original_text=text,
                adjusted_text=text,
                fits=False,
                original_width=original_width,
                adjusted_width=original_width,
                available_width=available_width
            )
        
        needed_tracking = -overflow / num_spaces
        
        # Limitar al mínimo permitido
        actual_tracking = max(needed_tracking, min_tracking)
        
        adjusted_width = TextFitCalculator.calculate_text_width(
            text, font_name, font_size, actual_tracking
        )
        
        return AdjustmentResult(
            strategy=OverflowStrategy.REDUCE_TRACKING,
            original_text=text,
            adjusted_text=text,
            fits=adjusted_width <= available_width,
            original_width=original_width,
            adjusted_width=adjusted_width,
            available_width=available_width,
            char_spacing_delta=actual_tracking
        )
    
    @staticmethod
    def fit_by_size(
        text: str,
        font_name: str,
        font_size: float,
        available_width: float,
        min_factor: float = 0.7
    ) -> AdjustmentResult:
        """
        Ajustar texto reduciendo el tamaño de fuente.
        """
        original_width = TextFitCalculator.calculate_text_width(
            text, font_name, font_size
        )
        
        if original_width <= available_width:
            return AdjustmentResult(
                strategy=OverflowStrategy.REDUCE_SIZE,
                original_text=text,
                adjusted_text=text,
                fits=True,
                original_width=original_width,
                adjusted_width=original_width,
                available_width=available_width
            )
        
        # Calcular factor necesario
        needed_factor = available_width / original_width
        actual_factor = max(needed_factor, min_factor)
        
        new_size = font_size * actual_factor
        adjusted_width = TextFitCalculator.calculate_text_width(
            text, font_name, new_size
        )
        
        return AdjustmentResult(
            strategy=OverflowStrategy.REDUCE_SIZE,
            original_text=text,
            adjusted_text=text,
            fits=adjusted_width <= available_width,
            original_width=original_width,
            adjusted_width=adjusted_width,
            available_width=available_width,
            font_size_delta=new_size - font_size
        )
    
    @staticmethod
    def fit_by_scale(
        text: str,
        font_name: str,
        font_size: float,
        available_width: float,
        min_scale: float = 0.8
    ) -> AdjustmentResult:
        """
        Ajustar texto con escala horizontal.
        """
        original_width = TextFitCalculator.calculate_text_width(
            text, font_name, font_size
        )
        
        if original_width <= available_width:
            return AdjustmentResult(
                strategy=OverflowStrategy.SCALE_HORIZONTAL,
                original_text=text,
                adjusted_text=text,
                fits=True,
                original_width=original_width,
                adjusted_width=original_width,
                available_width=available_width,
                scale_factor=1.0
            )
        
        # Calcular escala necesaria
        needed_scale = available_width / original_width
        actual_scale = max(needed_scale, min_scale)
        
        adjusted_width = original_width * actual_scale
        
        return AdjustmentResult(
            strategy=OverflowStrategy.SCALE_HORIZONTAL,
            original_text=text,
            adjusted_text=text,
            fits=adjusted_width <= available_width,
            original_width=original_width,
            adjusted_width=adjusted_width,
            available_width=available_width,
            scale_factor=actual_scale
        )


# ================== Panel Principal No-Reflow ==================


class NoReflowEditorPanel(QWidget):
    """
    Panel completo para edición en modo no-reflow.
    
    Combina todos los widgets de ajuste con visualización
    de estado y opciones de overflow.
    
    Signals:
        adjustmentApplied: Emitido cuando se aplica un ajuste (AdjustmentResult)
        textChanged: Emitido cuando cambia el texto (str)
    """
    
    # Señales
    adjustmentApplied = pyqtSignal(object)  # AdjustmentResult
    textChanged = pyqtSignal(str)
    
    def __init__(
        self,
        constraints: Optional[BboxConstraints] = None,
        config: Optional[NoReflowConfig] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self._constraints = constraints or BboxConstraints()
        self._config = config or NoReflowConfig()
        self._span_data: Dict[str, Any] = {}
        self._current_text = ""
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self) -> None:
        """Configurar interfaz."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Info de restricciones
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.StyledPanel)
        info_layout = QHBoxLayout(info_frame)
        
        self._constraints_label = QLabel()
        self._update_constraints_label()
        info_layout.addWidget(self._constraints_label)
        
        layout.addWidget(info_frame)
        
        # Indicador de ajuste
        self._fit_indicator = FitIndicatorWidget()
        layout.addWidget(self._fit_indicator)
        
        # Área de texto (solo lectura en este panel, el texto viene del editor principal)
        text_group = QGroupBox("Texto actual")
        text_layout = QVBoxLayout(text_group)
        self._text_display = QLineEdit()
        self._text_display.setReadOnly(True)
        self._text_display.setStyleSheet("background: #f8f8f8;")
        text_layout.addWidget(self._text_display)
        layout.addWidget(text_group)
        
        # Ajustadores
        self._tracking_adjuster = TrackingAdjuster(
            self._config.min_tracking,
            self._config.max_tracking
        )
        layout.addWidget(self._tracking_adjuster)
        
        self._size_adjuster = SizeAdjuster(
            base_size=12.0,
            min_factor=self._config.min_size_factor,
            max_factor=self._config.max_size_factor
        )
        layout.addWidget(self._size_adjuster)
        
        self._scale_adjuster = HorizontalScaleAdjuster(
            self._config.min_scale,
            self._config.max_scale
        )
        layout.addWidget(self._scale_adjuster)
        
        # Opciones de overflow
        self._overflow_options = OverflowOptionsPanel()
        layout.addWidget(self._overflow_options)
        
        layout.addStretch()
    
    def _setup_connections(self) -> None:
        """Configurar conexiones."""
        self._tracking_adjuster.trackingChanged.connect(self._on_adjustment_changed)
        self._size_adjuster.sizeChanged.connect(self._on_adjustment_changed)
        self._scale_adjuster.scaleChanged.connect(self._on_adjustment_changed)
        self._overflow_options.applyClicked.connect(self._on_apply_adjustment)
    
    def _update_constraints_label(self) -> None:
        """Actualizar label de restricciones."""
        c = self._constraints
        self._constraints_label.setText(
            f"Caja fija: {c.width:.1f} × {c.height:.1f} pt "
            f"(disponible: {c.inner_width:.1f} pt)"
        )
    
    def set_constraints(self, constraints: BboxConstraints) -> None:
        """Establecer restricciones de bbox."""
        self._constraints = constraints
        self._update_constraints_label()
        self._recalculate_fit()
    
    def set_span_data(self, span_data: Dict[str, Any]) -> None:
        """
        Establecer datos del span actual.
        
        Args:
            span_data: Diccionario con text, font_name, font_size, bbox, etc.
        """
        self._span_data = span_data
        self._current_text = span_data.get('text', '')
        self._text_display.setText(self._current_text)
        
        # Actualizar tamaño base
        font_size = span_data.get('font_size', 12.0)
        self._size_adjuster.set_base_size(font_size)
        
        # Actualizar constraints desde bbox
        bbox = span_data.get('bbox')
        if bbox:
            self._constraints = BboxConstraints.from_bbox(bbox)
            self._update_constraints_label()
        
        # Resetear ajustadores
        self._tracking_adjuster.reset()
        self._size_adjuster.reset()
        self._scale_adjuster.reset()
        
        self._recalculate_fit()
    
    def set_text(self, text: str) -> None:
        """Actualizar texto actual."""
        self._current_text = text
        self._text_display.setText(text)
        self._recalculate_fit()
    
    def _on_adjustment_changed(self, _value: float) -> None:
        """Manejar cambio en cualquier ajustador."""
        self._recalculate_fit()
    
    def _recalculate_fit(self) -> None:
        """Recalcular si el texto cabe."""
        if not self._span_data or not self._current_text:
            self._fit_indicator.set_percentage(0, True)
            return
        
        font_name = self._span_data.get('font_name', 'Helvetica')
        font_size = self._size_adjuster.get_size()
        tracking = self._tracking_adjuster.get_value()
        scale = self._scale_adjuster.get_scale()
        
        width = TextFitCalculator.calculate_text_width(
            self._current_text,
            font_name,
            font_size,
            tracking,
            scale
        )
        
        available = self._constraints.inner_width
        if available > 0:
            percentage = (width / available) * 100
            fits = percentage <= 100
        else:
            percentage = 0
            fits = True
        
        self._fit_indicator.set_percentage(percentage, fits)
    
    def _on_apply_adjustment(self) -> None:
        """Aplicar el ajuste seleccionado."""
        strategy = self._overflow_options.get_selected_strategy()
        
        if not self._span_data or not self._current_text:
            return
        
        font_name = self._span_data.get('font_name', 'Helvetica')
        font_size = self._span_data.get('font_size', 12.0)
        available_width = self._constraints.inner_width
        
        # Calcular ajuste según estrategia
        if strategy == OverflowStrategy.TRUNCATE:
            result = TextFitCalculator.fit_by_truncation(
                self._current_text, font_name, font_size, available_width
            )
        elif strategy == OverflowStrategy.REDUCE_TRACKING:
            result = TextFitCalculator.fit_by_tracking(
                self._current_text, font_name, font_size, available_width,
                self._config.min_tracking, self._config.max_tracking
            )
        elif strategy == OverflowStrategy.REDUCE_SIZE:
            result = TextFitCalculator.fit_by_size(
                self._current_text, font_name, font_size, available_width,
                self._config.min_size_factor
            )
        elif strategy == OverflowStrategy.SCALE_HORIZONTAL:
            result = TextFitCalculator.fit_by_scale(
                self._current_text, font_name, font_size, available_width,
                self._config.min_scale
            )
        else:
            return
        
        self.adjustmentApplied.emit(result)
    
    def get_current_adjustments(self) -> Dict[str, float]:
        """
        Obtener ajustes actuales.
        
        Returns:
            Dict con tracking, size_factor, scale
        """
        return {
            'tracking': self._tracking_adjuster.get_value(),
            'size_factor': self._size_adjuster.get_factor(),
            'scale': self._scale_adjuster.get_scale(),
        }


# ================== Factory Functions ==================


def create_no_reflow_panel(
    span_data: Optional[Dict[str, Any]] = None,
    config: Optional[NoReflowConfig] = None
) -> NoReflowEditorPanel:
    """
    Crear un panel de edición no-reflow.
    
    Args:
        span_data: Datos del span inicial
        config: Configuración del modo no-reflow
        
    Returns:
        NoReflowEditorPanel configurado
    """
    panel = NoReflowEditorPanel(config=config)
    
    if span_data:
        panel.set_span_data(span_data)
    
    return panel


def calculate_best_fit(
    text: str,
    font_name: str,
    font_size: float,
    available_width: float,
    config: Optional[NoReflowConfig] = None
) -> AdjustmentResult:
    """
    Calcular el mejor ajuste para un texto dado.
    
    Prueba todas las estrategias y retorna la que mejor funciona
    sin modificar demasiado el texto.
    
    Args:
        text: Texto a ajustar
        font_name: Nombre de la fuente
        font_size: Tamaño de fuente
        available_width: Ancho disponible
        config: Configuración con límites
        
    Returns:
        AdjustmentResult con la mejor estrategia
    """
    config = config or NoReflowConfig()
    
    # Verificar si ya cabe
    original_width = TextFitCalculator.calculate_text_width(
        text, font_name, font_size
    )
    
    if original_width <= available_width:
        return AdjustmentResult(
            strategy=OverflowStrategy.NONE,
            original_text=text,
            adjusted_text=text,
            fits=True,
            original_width=original_width,
            adjusted_width=original_width,
            available_width=available_width
        )
    
    # Probar estrategias en orden de preferencia
    results = []
    
    # 1. Reducir tracking (menos invasivo)
    results.append(TextFitCalculator.fit_by_tracking(
        text, font_name, font_size, available_width,
        config.min_tracking, config.max_tracking
    ))
    
    # 2. Escalar horizontalmente
    results.append(TextFitCalculator.fit_by_scale(
        text, font_name, font_size, available_width,
        config.min_scale
    ))
    
    # 3. Reducir tamaño
    results.append(TextFitCalculator.fit_by_size(
        text, font_name, font_size, available_width,
        config.min_size_factor
    ))
    
    # 4. Truncar (último recurso)
    results.append(TextFitCalculator.fit_by_truncation(
        text, font_name, font_size, available_width
    ))
    
    # Retornar el primero que funcione
    for result in results:
        if result.fits:
            return result
    
    # Si ninguno funciona, retornar truncamiento
    return results[-1]

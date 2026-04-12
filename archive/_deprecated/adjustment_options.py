"""
AdjustmentOptions - Opciones interactivas de ajuste de texto.

PHASE3-3C08: UI interactiva para opciones de ajuste cuando el texto
no cabe en el espacio disponible.

Este módulo proporciona:
- AdjustmentMode: Modos de ajuste disponibles
- AdjustmentPreset: Presets predefinidos de ajuste
- AdjustmentPreview: Widget de vista previa del ajuste
- AdjustmentSliders: Controles deslizantes para ajustes finos
- AdjustmentOptionsDialog: Diálogo principal de opciones
- Funciones factory para creación rápida
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Dict, Any, List

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPainter, QPen, QBrush, QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSlider, QPushButton, QRadioButton, QButtonGroup,
    QDialog, QDialogButtonBox, QSplitter, QComboBox, QTabWidget
)

# Importar componentes de módulos relacionados
try:
    from .fit_validator import FitValidator
    from .no_reflow_editor import TextFitCalculator
except ImportError:
    from fit_validator import FitValidator
    from no_reflow_editor import TextFitCalculator


# ================== Enums ==================


class AdjustmentMode(Enum):
    """Modo de ajuste seleccionado por el usuario."""
    
    NONE = auto()              # Sin ajuste (dejar overflow)
    AUTO = auto()              # Ajuste automático (mejor opción)
    TRACKING = auto()          # Solo reducir tracking
    SIZE = auto()              # Solo reducir tamaño
    SCALE = auto()             # Solo escalar horizontalmente
    TRUNCATE = auto()          # Truncar texto
    COMBINED = auto()          # Combinación personalizada
    
    def __str__(self) -> str:
        labels = {
            AdjustmentMode.NONE: "Sin ajuste",
            AdjustmentMode.AUTO: "Automático",
            AdjustmentMode.TRACKING: "Reducir espaciado",
            AdjustmentMode.SIZE: "Reducir tamaño",
            AdjustmentMode.SCALE: "Escalar ancho",
            AdjustmentMode.TRUNCATE: "Truncar texto",
            AdjustmentMode.COMBINED: "Combinado",
        }
        return labels.get(self, self.name)
    
    @property
    def description(self) -> str:
        """Descripción detallada del modo."""
        descriptions = {
            AdjustmentMode.NONE: "Mantener el texto sin cambios (puede desbordar)",
            AdjustmentMode.AUTO: "Selecciona automáticamente la mejor opción",
            AdjustmentMode.TRACKING: "Reduce el espacio entre caracteres",
            AdjustmentMode.SIZE: "Reduce el tamaño de la fuente",
            AdjustmentMode.SCALE: "Comprime el texto horizontalmente",
            AdjustmentMode.TRUNCATE: "Corta el texto y añade '...'",
            AdjustmentMode.COMBINED: "Permite ajustar múltiples parámetros",
        }
        return descriptions.get(self, "")


class PreviewQuality(Enum):
    """Calidad de la vista previa."""
    
    FAST = auto()      # Rápido, menos preciso
    ACCURATE = auto()  # Preciso, más lento
    
    def __str__(self) -> str:
        return "Rápida" if self == PreviewQuality.FAST else "Precisa"


# ================== Dataclasses ==================


@dataclass
class AdjustmentPreset:
    """
    Preset predefinido de ajuste.
    
    Agrupa configuraciones comunes para aplicación rápida.
    """
    name: str = "Default"
    description: str = ""
    mode: AdjustmentMode = AdjustmentMode.AUTO
    
    # Parámetros de ajuste
    tracking_delta: float = 0.0      # Cambio en char_spacing
    size_factor: float = 1.0         # Factor de tamaño (1.0 = sin cambio)
    scale_x: float = 1.0             # Escala horizontal
    truncate_suffix: str = "..."     # Sufijo de truncamiento
    
    # Límites
    min_tracking: float = -2.0
    max_tracking: float = 0.0
    min_size_factor: float = 0.7
    min_scale_x: float = 0.75
    
    # Metadatos
    is_builtin: bool = True
    icon: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            'name': self.name,
            'description': self.description,
            'mode': self.mode.name,
            'tracking_delta': self.tracking_delta,
            'size_factor': self.size_factor,
            'scale_x': self.scale_x,
            'truncate_suffix': self.truncate_suffix,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AdjustmentPreset":
        """Crea desde diccionario."""
        mode_name = data.get('mode', 'AUTO')
        mode = AdjustmentMode[mode_name] if mode_name in AdjustmentMode.__members__ else AdjustmentMode.AUTO
        return cls(
            name=data.get('name', 'Custom'),
            description=data.get('description', ''),
            mode=mode,
            tracking_delta=data.get('tracking_delta', 0.0),
            size_factor=data.get('size_factor', 1.0),
            scale_x=data.get('scale_x', 1.0),
            truncate_suffix=data.get('truncate_suffix', '...'),
            is_builtin=False,
        )


@dataclass
class AdjustmentState:
    """
    Estado actual del ajuste en edición.
    
    Mantiene los valores actuales mientras el usuario experimenta.
    """
    text: str = ""
    font_name: str = "Helvetica"
    font_size: float = 12.0
    available_width: float = 100.0
    
    # Valores originales
    original_char_spacing: float = 0.0
    original_word_spacing: float = 0.0
    original_scale_x: float = 1.0
    
    # Valores actuales (modificados)
    current_char_spacing: float = 0.0
    current_word_spacing: float = 0.0
    current_font_size: float = 12.0
    current_scale_x: float = 1.0
    current_text: str = ""  # Puede ser truncado
    
    # Estado calculado
    current_width: float = 0.0
    fits: bool = True
    overflow_amount: float = 0.0
    
    def reset_to_original(self) -> None:
        """Resetea valores actuales a los originales."""
        self.current_char_spacing = self.original_char_spacing
        self.current_word_spacing = self.original_word_spacing
        self.current_font_size = self.font_size
        self.current_scale_x = self.original_scale_x
        self.current_text = self.text
    
    @property
    def has_changes(self) -> bool:
        """True si hay cambios respecto al original."""
        return (
            self.current_char_spacing != self.original_char_spacing or
            self.current_font_size != self.font_size or
            self.current_scale_x != self.original_scale_x or
            self.current_text != self.text
        )
    
    @property
    def tracking_delta(self) -> float:
        """Delta de tracking aplicado."""
        return self.current_char_spacing - self.original_char_spacing
    
    @property
    def size_factor(self) -> float:
        """Factor de tamaño aplicado."""
        return self.current_font_size / self.font_size if self.font_size > 0 else 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario con los ajustes."""
        return {
            'text': self.current_text,
            'char_spacing': self.current_char_spacing,
            'char_spacing_delta': self.tracking_delta,
            'font_size': self.current_font_size,
            'size_factor': self.size_factor,
            'scale_x': self.current_scale_x,
            'fits': self.fits,
            'width': self.current_width,
        }


# ================== Presets predefinidos ==================


BUILTIN_PRESETS: List[AdjustmentPreset] = [
    AdjustmentPreset(
        name="Automático",
        description="Selecciona la mejor opción automáticamente",
        mode=AdjustmentMode.AUTO,
        icon="⚡",
    ),
    AdjustmentPreset(
        name="Conservador",
        description="Ajustes mínimos, prioriza legibilidad",
        mode=AdjustmentMode.TRACKING,
        min_tracking=-1.0,
        min_size_factor=0.9,
        icon="👁",
    ),
    AdjustmentPreset(
        name="Agresivo",
        description="Mayor compresión para textos largos",
        mode=AdjustmentMode.COMBINED,
        min_tracking=-2.5,
        min_size_factor=0.6,
        min_scale_x=0.7,
        icon="💪",
    ),
    AdjustmentPreset(
        name="Solo tracking",
        description="Reduce solo el espaciado entre caracteres",
        mode=AdjustmentMode.TRACKING,
        min_tracking=-2.0,
        icon="↔",
    ),
    AdjustmentPreset(
        name="Solo tamaño",
        description="Reduce solo el tamaño de fuente",
        mode=AdjustmentMode.SIZE,
        min_size_factor=0.7,
        icon="🔤",
    ),
    AdjustmentPreset(
        name="Truncar",
        description="Corta el texto con '...'",
        mode=AdjustmentMode.TRUNCATE,
        truncate_suffix="...",
        icon="✂",
    ),
]


# ================== Widgets ==================


class AdjustmentPreviewWidget(QWidget):
    """
    Widget de vista previa del ajuste.
    
    Muestra visualmente cómo quedará el texto con el ajuste aplicado,
    incluyendo indicadores de overflow y métricas.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Inicializa el widget de vista previa."""
        super().__init__(parent)
        self._state: Optional[AdjustmentState] = None
        self._show_bbox: bool = True
        self._show_overflow: bool = True
        self._show_metrics: bool = True
        
        self.setMinimumHeight(80)
        self.setMinimumWidth(200)
    
    def set_state(self, state: AdjustmentState) -> None:
        """Establece el estado a previsualizar."""
        self._state = state
        self.update()
    
    def set_show_bbox(self, show: bool) -> None:
        """Muestra/oculta el bounding box."""
        self._show_bbox = show
        self.update()
    
    def set_show_overflow(self, show: bool) -> None:
        """Muestra/oculta indicador de overflow."""
        self._show_overflow = show
        self.update()
    
    def set_show_metrics(self, show: bool) -> None:
        """Muestra/oculta métricas."""
        self._show_metrics = show
        self.update()
    
    def paintEvent(self, event) -> None:
        """Dibuja la vista previa."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fondo
        painter.fillRect(self.rect(), QColor("#FAFAFA"))
        
        if not self._state:
            # Sin estado, mostrar mensaje
            painter.setPen(QColor("#999999"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Sin vista previa"
            )
            return
        
        # Calcular dimensiones
        margin = 10
        preview_width = self._state.available_width
        
        # Escalar si es necesario
        max_width = self.width() - 2 * margin
        if preview_width > max_width:
            preview_width = max_width
        
        y_center = self.height() / 2
        
        # Dibujar bbox disponible
        if self._show_bbox:
            bbox_rect = self.rect().adjusted(
                margin, margin, -margin, -margin
            )
            bbox_rect.setWidth(int(preview_width))
            
            painter.setPen(QPen(QColor("#2196F3"), 1, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor("#E3F2FD")))
            painter.drawRect(bbox_rect)
        
        # Dibujar texto
        font = QFont(self._state.font_name, int(self._state.current_font_size))
        painter.setFont(font)
        
        # Color según estado
        if self._state.fits:
            text_color = QColor("#333333")
        else:
            text_color = QColor("#F44336")
        
        painter.setPen(text_color)
        
        # Dibujar texto
        text_rect = self.rect().adjusted(margin, margin, -margin, -margin)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._state.current_text
        )
        
        # Dibujar indicador de overflow
        if self._show_overflow and not self._state.fits:
            overflow_x = margin + preview_width
            painter.setPen(QPen(QColor("#F44336"), 2))
            painter.drawLine(
                int(overflow_x), margin,
                int(overflow_x), self.height() - margin
            )
            
            # Flecha indicando overflow
            painter.drawText(
                int(overflow_x) + 5,
                int(y_center) + 5,
                f"+{self._state.overflow_amount:.1f}pt"
            )
        
        # Dibujar métricas
        if self._show_metrics:
            metrics_text = f"{self._state.current_width:.1f}/{self._state.available_width:.1f}pt"
            painter.setPen(QColor("#666666"))
            painter.setFont(QFont("Arial", 9))
            painter.drawText(
                margin, self.height() - 5,
                metrics_text
            )


class TrackingSlider(QWidget):
    """
    Slider para ajustar el tracking (espaciado entre caracteres).
    """
    
    valueChanged = pyqtSignal(float)
    
    def __init__(
        self,
        min_value: float = -3.0,
        max_value: float = 3.0,
        parent: Optional[QWidget] = None
    ):
        """Inicializa el slider de tracking."""
        super().__init__(parent)
        self._min = min_value
        self._max = max_value
        self._value = 0.0
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configura la interfaz."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Etiqueta
        header = QHBoxLayout()
        self._label = QLabel("Espaciado (Tracking):")
        self._value_label = QLabel("0.0pt")
        self._value_label.setStyleSheet("font-weight: bold;")
        header.addWidget(self._label)
        header.addStretch()
        header.addWidget(self._value_label)
        layout.addLayout(header)
        
        # Slider
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(-100, 100)  # -3.0 a 3.0 en centésimas
        self._slider.setValue(0)
        self._slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self._slider)
        
        # Botón reset
        self._reset_btn = QPushButton("↺")
        self._reset_btn.setFixedWidth(30)
        self._reset_btn.setToolTip("Resetear a 0")
        self._reset_btn.clicked.connect(self.reset)
        header.addWidget(self._reset_btn)
    
    def _on_slider_changed(self, value: int) -> None:
        """Callback cuando cambia el slider."""
        # Convertir de centésimas a valor real
        self._value = value / 100.0 * (self._max - self._min) / 2
        self._value_label.setText(f"{self._value:+.1f}pt")
        self.valueChanged.emit(self._value)
    
    def value(self) -> float:
        """Obtiene el valor actual."""
        return self._value
    
    def set_value(self, value: float) -> None:
        """Establece el valor."""
        self._value = max(self._min, min(self._max, value))
        slider_value = int(self._value / ((self._max - self._min) / 2) * 100)
        self._slider.blockSignals(True)
        self._slider.setValue(slider_value)
        self._slider.blockSignals(False)
        self._value_label.setText(f"{self._value:+.1f}pt")
    
    def reset(self) -> None:
        """Resetea a valor por defecto."""
        self.set_value(0.0)
        self.valueChanged.emit(0.0)
    
    def set_range(self, min_val: float, max_val: float) -> None:
        """Establece el rango."""
        self._min = min_val
        self._max = max_val


class SizeSlider(QWidget):
    """
    Slider para ajustar el tamaño de fuente.
    """
    
    valueChanged = pyqtSignal(float)
    
    def __init__(
        self,
        base_size: float = 12.0,
        min_factor: float = 0.5,
        max_factor: float = 1.5,
        parent: Optional[QWidget] = None
    ):
        """Inicializa el slider de tamaño."""
        super().__init__(parent)
        self._base_size = base_size
        self._min_factor = min_factor
        self._max_factor = max_factor
        self._factor = 1.0
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configura la interfaz."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Etiqueta
        header = QHBoxLayout()
        self._label = QLabel("Tamaño:")
        self._value_label = QLabel(f"{self._base_size:.1f}pt (100%)")
        self._value_label.setStyleSheet("font-weight: bold;")
        header.addWidget(self._label)
        header.addStretch()
        header.addWidget(self._value_label)
        layout.addLayout(header)
        
        # Slider
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(int(self._min_factor * 100), int(self._max_factor * 100))
        self._slider.setValue(100)
        self._slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self._slider)
        
        # Botón reset
        self._reset_btn = QPushButton("↺")
        self._reset_btn.setFixedWidth(30)
        self._reset_btn.setToolTip("Resetear a 100%")
        self._reset_btn.clicked.connect(self.reset)
        header.addWidget(self._reset_btn)
    
    def _on_slider_changed(self, value: int) -> None:
        """Callback cuando cambia el slider."""
        self._factor = value / 100.0
        current_size = self._base_size * self._factor
        self._value_label.setText(f"{current_size:.1f}pt ({value}%)")
        self.valueChanged.emit(self._factor)
    
    def factor(self) -> float:
        """Obtiene el factor actual."""
        return self._factor
    
    def current_size(self) -> float:
        """Obtiene el tamaño actual."""
        return self._base_size * self._factor
    
    def set_factor(self, factor: float) -> None:
        """Establece el factor."""
        self._factor = max(self._min_factor, min(self._max_factor, factor))
        self._slider.blockSignals(True)
        self._slider.setValue(int(self._factor * 100))
        self._slider.blockSignals(False)
        current_size = self._base_size * self._factor
        self._value_label.setText(f"{current_size:.1f}pt ({int(self._factor * 100)}%)")
    
    def set_base_size(self, size: float) -> None:
        """Establece el tamaño base."""
        self._base_size = size
        self._on_slider_changed(self._slider.value())
    
    def reset(self) -> None:
        """Resetea a 100%."""
        self.set_factor(1.0)
        self.valueChanged.emit(1.0)


class ScaleSlider(QWidget):
    """
    Slider para ajustar la escala horizontal.
    """
    
    valueChanged = pyqtSignal(float)
    
    def __init__(
        self,
        min_scale: float = 0.5,
        max_scale: float = 1.5,
        parent: Optional[QWidget] = None
    ):
        """Inicializa el slider de escala."""
        super().__init__(parent)
        self._min = min_scale
        self._max = max_scale
        self._scale = 1.0
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configura la interfaz."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Etiqueta
        header = QHBoxLayout()
        self._label = QLabel("Escala horizontal:")
        self._value_label = QLabel("100%")
        self._value_label.setStyleSheet("font-weight: bold;")
        header.addWidget(self._label)
        header.addStretch()
        header.addWidget(self._value_label)
        layout.addLayout(header)
        
        # Slider
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(int(self._min * 100), int(self._max * 100))
        self._slider.setValue(100)
        self._slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self._slider)
        
        # Botón reset
        self._reset_btn = QPushButton("↺")
        self._reset_btn.setFixedWidth(30)
        self._reset_btn.setToolTip("Resetear a 100%")
        self._reset_btn.clicked.connect(self.reset)
        header.addWidget(self._reset_btn)
    
    def _on_slider_changed(self, value: int) -> None:
        """Callback cuando cambia el slider."""
        self._scale = value / 100.0
        self._value_label.setText(f"{value}%")
        self.valueChanged.emit(self._scale)
    
    def scale(self) -> float:
        """Obtiene la escala actual."""
        return self._scale
    
    def set_scale(self, scale: float) -> None:
        """Establece la escala."""
        self._scale = max(self._min, min(self._max, scale))
        self._slider.blockSignals(True)
        self._slider.setValue(int(self._scale * 100))
        self._slider.blockSignals(False)
        self._value_label.setText(f"{int(self._scale * 100)}%")
    
    def reset(self) -> None:
        """Resetea a 100%."""
        self.set_scale(1.0)
        self.valueChanged.emit(1.0)


class PresetSelector(QWidget):
    """
    Selector de presets de ajuste.
    """
    
    presetSelected = pyqtSignal(AdjustmentPreset)
    
    def __init__(
        self,
        presets: Optional[List[AdjustmentPreset]] = None,
        parent: Optional[QWidget] = None
    ):
        """Inicializa el selector de presets."""
        super().__init__(parent)
        self._presets = presets or BUILTIN_PRESETS.copy()
        self._current_preset: Optional[AdjustmentPreset] = None
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configura la interfaz."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Etiqueta
        self._label = QLabel("Preset de ajuste:")
        layout.addWidget(self._label)
        
        # Botones de preset
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        
        for i, preset in enumerate(self._presets):
            btn = QRadioButton(f"{preset.icon} {preset.name}")
            btn.setToolTip(preset.description)
            self._button_group.addButton(btn, i)
            layout.addWidget(btn)
            
            if i == 0:
                btn.setChecked(True)
                self._current_preset = preset
        
        self._button_group.idClicked.connect(self._on_preset_selected)
    
    def _on_preset_selected(self, button_id: int) -> None:
        """Callback cuando se selecciona un preset."""
        if 0 <= button_id < len(self._presets):
            self._current_preset = self._presets[button_id]
            self.presetSelected.emit(self._current_preset)
    
    def current_preset(self) -> Optional[AdjustmentPreset]:
        """Obtiene el preset actual."""
        return self._current_preset
    
    def add_preset(self, preset: AdjustmentPreset) -> None:
        """Añade un preset personalizado."""
        self._presets.append(preset)
        btn = QRadioButton(f"{preset.icon} {preset.name}")
        btn.setToolTip(preset.description)
        self._button_group.addButton(btn, len(self._presets) - 1)
        self.layout().addWidget(btn)


class ModeSelector(QWidget):
    """
    Selector de modo de ajuste con descripción.
    """
    
    modeSelected = pyqtSignal(AdjustmentMode)
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Inicializa el selector de modo."""
        super().__init__(parent)
        self._current_mode = AdjustmentMode.AUTO
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configura la interfaz."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Combo de modo
        self._combo = QComboBox()
        for mode in AdjustmentMode:
            self._combo.addItem(str(mode), mode)
        self._combo.currentIndexChanged.connect(self._on_mode_changed)
        layout.addWidget(self._combo)
        
        # Descripción
        self._desc_label = QLabel()
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self._desc_label)
        
        self._update_description()
    
    def _on_mode_changed(self, index: int) -> None:
        """Callback cuando cambia el modo."""
        self._current_mode = self._combo.itemData(index)
        self._update_description()
        self.modeSelected.emit(self._current_mode)
    
    def _update_description(self) -> None:
        """Actualiza la descripción."""
        self._desc_label.setText(self._current_mode.description)
    
    def current_mode(self) -> AdjustmentMode:
        """Obtiene el modo actual."""
        return self._current_mode
    
    def set_mode(self, mode: AdjustmentMode) -> None:
        """Establece el modo."""
        index = self._combo.findData(mode)
        if index >= 0:
            self._combo.setCurrentIndex(index)


class AdjustmentControlsPanel(QWidget):
    """
    Panel de controles de ajuste fino.
    
    Agrupa los sliders para tracking, tamaño y escala.
    """
    
    adjustmentChanged = pyqtSignal(dict)
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Inicializa el panel de controles."""
        super().__init__(parent)
        self._state: Optional[AdjustmentState] = None
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._emit_changes)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configura la interfaz."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Tracking slider
        self._tracking = TrackingSlider()
        self._tracking.valueChanged.connect(self._on_tracking_changed)
        layout.addWidget(self._tracking)
        
        # Size slider
        self._size = SizeSlider()
        self._size.valueChanged.connect(self._on_size_changed)
        layout.addWidget(self._size)
        
        # Scale slider
        self._scale = ScaleSlider()
        self._scale.valueChanged.connect(self._on_scale_changed)
        layout.addWidget(self._scale)
        
        # Botones
        buttons = QHBoxLayout()
        
        self._reset_all_btn = QPushButton("Resetear todo")
        self._reset_all_btn.clicked.connect(self.reset_all)
        buttons.addWidget(self._reset_all_btn)
        
        buttons.addStretch()
        
        self._auto_fit_btn = QPushButton("Auto-ajustar")
        self._auto_fit_btn.clicked.connect(self._on_auto_fit)
        buttons.addWidget(self._auto_fit_btn)
        
        layout.addLayout(buttons)
    
    def set_state(self, state: AdjustmentState) -> None:
        """Establece el estado inicial."""
        self._state = state
        
        # Actualizar sliders
        self._tracking.set_value(state.tracking_delta)
        self._size.set_base_size(state.font_size)
        self._size.set_factor(state.size_factor)
        self._scale.set_scale(state.current_scale_x)
    
    def _on_tracking_changed(self, value: float) -> None:
        """Callback cuando cambia tracking."""
        if self._state:
            self._state.current_char_spacing = self._state.original_char_spacing + value
            self._schedule_emit()
    
    def _on_size_changed(self, factor: float) -> None:
        """Callback cuando cambia tamaño."""
        if self._state:
            self._state.current_font_size = self._state.font_size * factor
            self._schedule_emit()
    
    def _on_scale_changed(self, scale: float) -> None:
        """Callback cuando cambia escala."""
        if self._state:
            self._state.current_scale_x = scale
            self._schedule_emit()
    
    def _schedule_emit(self) -> None:
        """Programa emisión de cambios con debounce."""
        self._debounce_timer.start(100)
    
    def _emit_changes(self) -> None:
        """Emite los cambios actuales."""
        if self._state:
            self.adjustmentChanged.emit(self._state.to_dict())
    
    def _on_auto_fit(self) -> None:
        """Auto-ajusta para que quepa."""
        if not self._state:
            return
        
        # Usar TextFitCalculator para encontrar mejor ajuste
        # Intentar tracking primero
        result = TextFitCalculator.fit_by_tracking(
            self._state.text,
            self._state.font_name,
            self._state.font_size,
            self._state.available_width,
            min_tracking=-2.0
        )
        
        if result.fits:
            self._tracking.set_value(result.char_spacing_delta)
            return
        
        # Si no funciona, intentar escala
        result = TextFitCalculator.fit_by_scale(
            self._state.text,
            self._state.font_name,
            self._state.font_size,
            self._state.available_width,
            min_scale=0.75
        )
        
        if result.fits:
            self._scale.set_scale(result.scale_factor)
            return
        
        # Último recurso: reducir tamaño
        result = TextFitCalculator.fit_by_size(
            self._state.text,
            self._state.font_name,
            self._state.font_size,
            self._state.available_width,
            min_factor=0.7
        )
        
        if result.font_size_delta != 0:
            new_size = self._state.font_size + result.font_size_delta
            factor = new_size / self._state.font_size
            self._size.set_factor(factor)
    
    def reset_all(self) -> None:
        """Resetea todos los controles."""
        self._tracking.reset()
        self._size.reset()
        self._scale.reset()
        
        if self._state:
            self._state.reset_to_original()
            self._emit_changes()
    
    def get_adjustments(self) -> Dict[str, float]:
        """Obtiene los ajustes actuales."""
        return {
            'tracking': self._tracking.value(),
            'size_factor': self._size.factor(),
            'scale_x': self._scale.scale(),
        }


class TruncationPanel(QWidget):
    """
    Panel para configurar truncamiento de texto.
    """
    
    truncationChanged = pyqtSignal(str, str)  # (texto_truncado, sufijo)
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Inicializa el panel de truncamiento."""
        super().__init__(parent)
        self._original_text = ""
        self._truncated_text = ""
        self._suffix = "..."
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configura la interfaz."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Configuración de sufijo
        suffix_row = QHBoxLayout()
        suffix_row.addWidget(QLabel("Sufijo:"))
        self._suffix_combo = QComboBox()
        self._suffix_combo.addItems(["...", "…", "→", "[...]", ""])
        self._suffix_combo.setEditable(True)
        self._suffix_combo.currentTextChanged.connect(self._on_suffix_changed)
        suffix_row.addWidget(self._suffix_combo)
        layout.addLayout(suffix_row)
        
        # Slider de longitud
        length_row = QHBoxLayout()
        length_row.addWidget(QLabel("Longitud:"))
        self._length_slider = QSlider(Qt.Orientation.Horizontal)
        self._length_slider.setRange(1, 100)
        self._length_slider.setValue(100)
        self._length_slider.valueChanged.connect(self._on_length_changed)
        length_row.addWidget(self._length_slider)
        self._length_label = QLabel("100%")
        length_row.addWidget(self._length_label)
        layout.addLayout(length_row)
        
        # Vista previa del texto truncado
        self._preview_label = QLabel()
        self._preview_label.setWordWrap(True)
        self._preview_label.setStyleSheet(
            "background-color: #f5f5f5; padding: 8px; border-radius: 4px;"
        )
        layout.addWidget(self._preview_label)
    
    def set_text(self, text: str) -> None:
        """Establece el texto a truncar."""
        self._original_text = text
        self._length_slider.setRange(1, len(text))
        self._length_slider.setValue(len(text))
        self._update_preview()
    
    def _on_suffix_changed(self, suffix: str) -> None:
        """Callback cuando cambia el sufijo."""
        self._suffix = suffix
        self._update_preview()
    
    def _on_length_changed(self, value: int) -> None:
        """Callback cuando cambia la longitud."""
        percentage = int(value / len(self._original_text) * 100) if self._original_text else 0
        self._length_label.setText(f"{percentage}%")
        self._update_preview()
    
    def _update_preview(self) -> None:
        """Actualiza la vista previa."""
        if not self._original_text:
            self._preview_label.setText("")
            return
        
        length = self._length_slider.value()
        if length >= len(self._original_text):
            self._truncated_text = self._original_text
        else:
            self._truncated_text = self._original_text[:length] + self._suffix
        
        self._preview_label.setText(self._truncated_text)
        self.truncationChanged.emit(self._truncated_text, self._suffix)
    
    def truncated_text(self) -> str:
        """Obtiene el texto truncado."""
        return self._truncated_text
    
    def suffix(self) -> str:
        """Obtiene el sufijo."""
        return self._suffix


# ================== Diálogo principal ==================


class AdjustmentOptionsDialog(QDialog):
    """
    Diálogo principal para opciones de ajuste.
    
    Permite al usuario seleccionar y previsualizar diferentes
    estrategias de ajuste cuando el texto no cabe.
    """
    
    adjustmentApplied = pyqtSignal(dict)
    
    def __init__(
        self,
        text: str,
        font_name: str,
        font_size: float,
        available_width: float,
        char_spacing: float = 0.0,
        parent: Optional[QWidget] = None
    ):
        """
        Inicializa el diálogo de opciones.
        
        Args:
            text: Texto a ajustar
            font_name: Nombre de la fuente
            font_size: Tamaño de fuente
            available_width: Ancho disponible
            char_spacing: Espaciado inicial entre caracteres
            parent: Widget padre
        """
        super().__init__(parent)
        
        # Crear estado
        self._state = AdjustmentState(
            text=text,
            font_name=font_name,
            font_size=font_size,
            available_width=available_width,
            original_char_spacing=char_spacing,
            current_char_spacing=char_spacing,
            current_font_size=font_size,
            current_text=text,
        )
        
        # Validador para calcular métricas
        self._validator = FitValidator()
        
        self._setup_ui()
        self._setup_connections()
        self._update_preview()
    
    def _setup_ui(self) -> None:
        """Configura la interfaz del diálogo."""
        self.setWindowTitle("Opciones de ajuste de texto")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # Splitter principal
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Panel superior: Vista previa
        preview_frame = QFrame()
        preview_frame.setFrameShape(QFrame.Shape.StyledPanel)
        preview_layout = QVBoxLayout(preview_frame)
        
        preview_label = QLabel("Vista previa:")
        preview_label.setStyleSheet("font-weight: bold;")
        preview_layout.addWidget(preview_label)
        
        self._preview = AdjustmentPreviewWidget()
        preview_layout.addWidget(self._preview)
        
        # Indicador de estado
        self._status_label = QLabel()
        self._status_label.setStyleSheet("padding: 8px;")
        preview_layout.addWidget(self._status_label)
        
        splitter.addWidget(preview_frame)
        
        # Panel inferior: Controles
        controls_frame = QFrame()
        controls_frame.setFrameShape(QFrame.Shape.StyledPanel)
        controls_layout = QVBoxLayout(controls_frame)
        
        # Tabs para diferentes modos
        self._tabs = QTabWidget()
        
        # Tab 1: Presets
        presets_widget = QWidget()
        presets_layout = QVBoxLayout(presets_widget)
        self._preset_selector = PresetSelector()
        presets_layout.addWidget(self._preset_selector)
        presets_layout.addStretch()
        self._tabs.addTab(presets_widget, "Presets")
        
        # Tab 2: Ajuste fino
        fine_widget = QWidget()
        fine_layout = QVBoxLayout(fine_widget)
        self._controls = AdjustmentControlsPanel()
        fine_layout.addWidget(self._controls)
        self._tabs.addTab(fine_widget, "Ajuste fino")
        
        # Tab 3: Truncamiento
        truncate_widget = QWidget()
        truncate_layout = QVBoxLayout(truncate_widget)
        self._truncation = TruncationPanel()
        truncate_layout.addWidget(self._truncation)
        truncate_layout.addStretch()
        self._tabs.addTab(truncate_widget, "Truncar")
        
        controls_layout.addWidget(self._tabs)
        
        splitter.addWidget(controls_frame)
        
        # Proporciones del splitter
        splitter.setSizes([200, 300])
        
        layout.addWidget(splitter)
        
        # Botones de diálogo
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Reset
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(
            self._on_reset
        )
        layout.addWidget(buttons)
    
    def _setup_connections(self) -> None:
        """Conecta señales."""
        self._preset_selector.presetSelected.connect(self._on_preset_selected)
        self._controls.adjustmentChanged.connect(self._on_adjustment_changed)
        self._truncation.truncationChanged.connect(self._on_truncation_changed)
        self._tabs.currentChanged.connect(self._on_tab_changed)
    
    def _update_preview(self) -> None:
        """Actualiza la vista previa y estado."""
        # Calcular ancho actual
        self._state.current_width = TextFitCalculator.calculate_text_width(
            self._state.current_text,
            self._state.font_name,
            self._state.current_font_size,
            char_spacing=self._state.current_char_spacing,
            scale_x=self._state.current_scale_x
        )
        
        # Determinar si cabe
        self._state.fits = self._state.current_width <= self._state.available_width
        self._state.overflow_amount = max(
            0, self._state.current_width - self._state.available_width
        )
        
        # Actualizar preview widget
        self._preview.set_state(self._state)
        
        # Actualizar etiqueta de estado
        if self._state.fits:
            if self._state.has_changes:
                status_text = "✅ El texto cabe con los ajustes aplicados"
                status_color = "#4CAF50"
            else:
                status_text = "✅ El texto cabe sin ajustes"
                status_color = "#2196F3"
        else:
            status_text = f"⚠️ El texto excede en {self._state.overflow_amount:.1f}pt"
            status_color = "#F44336"
        
        self._status_label.setText(status_text)
        self._status_label.setStyleSheet(
            f"padding: 8px; color: {status_color}; background-color: {status_color}20;"
        )
    
    def _on_preset_selected(self, preset: AdjustmentPreset) -> None:
        """Callback cuando se selecciona un preset."""
        if preset.mode == AdjustmentMode.AUTO:
            # Aplicar auto-ajuste
            self._controls._on_auto_fit()
        elif preset.mode == AdjustmentMode.TRACKING:
            # Solo tracking
            self._state.reset_to_original()
            result = TextFitCalculator.fit_by_tracking(
                self._state.text,
                self._state.font_name,
                self._state.font_size,
                self._state.available_width,
                min_tracking=preset.min_tracking
            )
            self._state.current_char_spacing = (
                self._state.original_char_spacing + result.char_spacing_delta
            )
        elif preset.mode == AdjustmentMode.SIZE:
            # Solo tamaño
            self._state.reset_to_original()
            result = TextFitCalculator.fit_by_size(
                self._state.text,
                self._state.font_name,
                self._state.font_size,
                self._state.available_width,
                min_factor=preset.min_size_factor
            )
            self._state.current_font_size = (
                self._state.font_size + result.font_size_delta
            )
        elif preset.mode == AdjustmentMode.SCALE:
            # Solo escala
            self._state.reset_to_original()
            result = TextFitCalculator.fit_by_scale(
                self._state.text,
                self._state.font_name,
                self._state.font_size,
                self._state.available_width,
                min_scale=preset.min_scale_x
            )
            self._state.current_scale_x = result.scale_factor
        elif preset.mode == AdjustmentMode.TRUNCATE:
            # Truncar
            self._tabs.setCurrentIndex(2)  # Tab de truncamiento
            return
        elif preset.mode == AdjustmentMode.NONE:
            self._state.reset_to_original()
        
        # Actualizar controles y preview
        self._controls.set_state(self._state)
        self._update_preview()
    
    def _on_adjustment_changed(self, adjustments: Dict[str, Any]) -> None:
        """Callback cuando cambian los ajustes manuales."""
        self._update_preview()
    
    def _on_truncation_changed(self, truncated: str, suffix: str) -> None:
        """Callback cuando cambia el truncamiento."""
        self._state.current_text = truncated
        self._update_preview()
    
    def _on_tab_changed(self, index: int) -> None:
        """Callback cuando cambia el tab."""
        if index == 2:  # Tab de truncamiento
            self._truncation.set_text(self._state.text)
    
    def _on_reset(self) -> None:
        """Resetea todos los ajustes."""
        self._state.reset_to_original()
        self._controls.reset_all()
        self._truncation.set_text(self._state.text)
        self._update_preview()
    
    def _on_accept(self) -> None:
        """Acepta y emite los ajustes."""
        result = self._state.to_dict()
        self.adjustmentApplied.emit(result)
        self.accept()
    
    def get_result(self) -> Dict[str, Any]:
        """Obtiene el resultado del ajuste."""
        return self._state.to_dict()


# ================== Factory Functions ==================


def create_adjustment_dialog(
    text: str,
    font_name: str,
    font_size: float,
    available_width: float,
    char_spacing: float = 0.0,
    parent: Optional[QWidget] = None
) -> AdjustmentOptionsDialog:
    """
    Crea un diálogo de opciones de ajuste.
    
    Args:
        text: Texto a ajustar
        font_name: Nombre de la fuente
        font_size: Tamaño en puntos
        available_width: Ancho disponible
        char_spacing: Espaciado inicial
        parent: Widget padre
        
    Returns:
        AdjustmentOptionsDialog configurado
    """
    return AdjustmentOptionsDialog(
        text=text,
        font_name=font_name,
        font_size=font_size,
        available_width=available_width,
        char_spacing=char_spacing,
        parent=parent
    )


def show_adjustment_dialog(
    text: str,
    font_name: str,
    font_size: float,
    available_width: float,
    char_spacing: float = 0.0,
    parent: Optional[QWidget] = None
) -> Optional[Dict[str, Any]]:
    """
    Muestra el diálogo de ajuste y retorna el resultado.
    
    Args:
        text: Texto a ajustar
        font_name: Nombre de la fuente
        font_size: Tamaño en puntos
        available_width: Ancho disponible
        char_spacing: Espaciado inicial
        parent: Widget padre
        
    Returns:
        Diccionario con ajustes o None si se canceló
    """
    dialog = create_adjustment_dialog(
        text, font_name, font_size, available_width, char_spacing, parent
    )
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_result()
    return None


def create_adjustment_controls(
    parent: Optional[QWidget] = None
) -> AdjustmentControlsPanel:
    """
    Crea un panel de controles de ajuste.
    
    Args:
        parent: Widget padre
        
    Returns:
        AdjustmentControlsPanel
    """
    return AdjustmentControlsPanel(parent)


def create_preset_selector(
    presets: Optional[List[AdjustmentPreset]] = None,
    parent: Optional[QWidget] = None
) -> PresetSelector:
    """
    Crea un selector de presets.
    
    Args:
        presets: Lista de presets (usa built-in si None)
        parent: Widget padre
        
    Returns:
        PresetSelector
    """
    return PresetSelector(presets, parent)


def get_builtin_presets() -> List[AdjustmentPreset]:
    """
    Obtiene los presets predefinidos.
    
    Returns:
        Lista de AdjustmentPreset
    """
    return BUILTIN_PRESETS.copy()

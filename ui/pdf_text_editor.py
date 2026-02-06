"""
PDFTextEditor - Editor de texto PDF integrado con preservación de propiedades.

PHASE3-3C05: Editor principal que integra todos los componentes de Phase 3C.

Características:
- Edición de texto con preservación de propiedades tipográficas originales
- Visualización de métricas en tiempo real (Tc, Tw, Ts, matrices)
- Validación "cabe/no cabe" con feedback visual
- Integración con PropertyInspector para vista de propiedades
- Integración con TextSelectionOverlay para selección visual
- Soporte para modo "no reflow" (cajas fijas)
- Multi-selección de spans

Dependencias:
- 3C-01: PropertyInspector
- 3C-02: TextHitTester
- 3C-03: TextPropertiesTooltip
- 3C-04: TextSelectionOverlay
- 3A-*: text_engine completo
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QTextEdit, QPushButton, QFrame, QToolBar,
    QAction, QGroupBox, QMessageBox, QToolButton, QMenu
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QFontMetrics

if TYPE_CHECKING:
    from core.text_engine import TextSpanMetrics  # noqa: F401


# ================== Imports condicionales ==================


# text_engine
try:
    from core.text_engine import TextSpanMetrics  # noqa: F401
    HAS_TEXT_ENGINE = True
except ImportError:
    HAS_TEXT_ENGINE = False

# FontManager
try:
    import core.font_manager  # noqa: F401
    HAS_FONT_MANAGER = True
except ImportError:
    HAS_FONT_MANAGER = False

# PropertyInspector
try:
    from .property_inspector import PropertyInspector
    HAS_PROPERTY_INSPECTOR = True
except ImportError:
    HAS_PROPERTY_INSPECTOR = False

# TextSelectionOverlay
try:
    from .text_selection_overlay import TextSelectionOverlay
    HAS_SELECTION_OVERLAY = True
except ImportError:
    HAS_SELECTION_OVERLAY = False


# ================== Enums y Configuración ==================


class EditMode(Enum):
    """Modos de edición del PDFTextEditor."""
    PRESERVE = "preserve"       # Preservar propiedades exactas
    FLEXIBLE = "flexible"       # Permitir ajustes automáticos
    NO_REFLOW = "no_reflow"     # Modo caja fija (sin reflow)


class FitStatus(Enum):
    """Estado de ajuste del texto."""
    FITS = "fits"               # El texto cabe perfectamente
    TIGHT = "tight"             # Cabe pero ajustado
    OVERFLOW = "overflow"       # No cabe (desbordamiento)
    UNKNOWN = "unknown"         # No se puede determinar


@dataclass
class EditedSpan:
    """Representa un span que ha sido editado."""
    original_span: Dict[str, Any]
    new_text: str
    original_text: str
    modifications: Dict[str, Any] = field(default_factory=dict)
    fit_status: FitStatus = FitStatus.UNKNOWN
    
    @property
    def has_changes(self) -> bool:
        """True si hay cambios respecto al original."""
        return self.new_text != self.original_text or bool(self.modifications)


@dataclass
class EditorConfig:
    """Configuración del PDFTextEditor."""
    mode: EditMode = EditMode.PRESERVE
    show_metrics: bool = True
    show_guidelines: bool = True
    auto_validate: bool = True
    validate_delay_ms: int = 300
    max_undo_steps: int = 50
    show_property_panel: bool = True
    preserve_whitespace: bool = True


# ================== Widgets Auxiliares ==================


class MetricsStatusBar(QFrame):
    """
    Barra de estado que muestra métricas del texto actual.
    
    Muestra: ancho original, ancho nuevo, estado de ajuste, etc.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.setMinimumHeight(28)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(16)
        
        # Sección de ancho
        self._width_label = QLabel("Ancho: —")
        self._width_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self._width_label)
        
        # Separador
        sep1 = QFrame()
        sep1.setFrameStyle(QFrame.VLine | QFrame.Sunken)
        layout.addWidget(sep1)
        
        # Sección de estado
        self._status_label = QLabel("Estado: —")
        layout.addWidget(self._status_label)
        
        # Separador
        sep2 = QFrame()
        sep2.setFrameStyle(QFrame.VLine | QFrame.Sunken)
        layout.addWidget(sep2)
        
        # Sección de font
        self._font_label = QLabel("Fuente: —")
        layout.addWidget(self._font_label)
        
        layout.addStretch()
        
        # Indicador visual de ajuste
        self._fit_indicator = QLabel("●")
        self._fit_indicator.setStyleSheet("color: gray; font-size: 16px;")
        layout.addWidget(self._fit_indicator)
    
    def update_metrics(
        self,
        original_width: Optional[float],
        new_width: Optional[float],
        fit_status: FitStatus,
        font_info: Optional[str] = None
    ) -> None:
        """Actualizar métricas mostradas."""
        # Ancho
        if original_width is not None and new_width is not None:
            diff = new_width - original_width
            diff_str = f"+{diff:.1f}" if diff >= 0 else f"{diff:.1f}"
            self._width_label.setText(
                f"Ancho: {new_width:.1f} / {original_width:.1f} ({diff_str})"
            )
        else:
            self._width_label.setText("Ancho: —")
        
        # Estado
        status_texts = {
            FitStatus.FITS: ("✓ Cabe", "color: #27ae60;"),
            FitStatus.TIGHT: ("⚠ Ajustado", "color: #f39c12;"),
            FitStatus.OVERFLOW: ("✗ Desborda", "color: #e74c3c;"),
            FitStatus.UNKNOWN: ("? Desconocido", "color: gray;"),
        }
        text, style = status_texts.get(fit_status, ("—", ""))
        self._status_label.setText(f"Estado: {text}")
        self._status_label.setStyleSheet(style)
        
        # Fuente
        if font_info:
            self._font_label.setText(f"Fuente: {font_info}")
        else:
            self._font_label.setText("Fuente: —")
        
        # Indicador
        indicator_colors = {
            FitStatus.FITS: "#27ae60",
            FitStatus.TIGHT: "#f39c12",
            FitStatus.OVERFLOW: "#e74c3c",
            FitStatus.UNKNOWN: "gray",
        }
        self._fit_indicator.setStyleSheet(
            f"color: {indicator_colors.get(fit_status, 'gray')}; font-size: 16px;"
        )


class SpanComparisonWidget(QFrame):
    """
    Widget que muestra comparación original vs editado para un span.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        
        # Original
        orig_group = QGroupBox("Original")
        orig_layout = QVBoxLayout(orig_group)
        self._original_text = QLabel()
        self._original_text.setWordWrap(True)
        self._original_text.setStyleSheet(
            "background: #f8f8f8; padding: 4px; border-radius: 2px;"
        )
        orig_layout.addWidget(self._original_text)
        layout.addWidget(orig_group)
        
        # Editado
        edit_group = QGroupBox("Editado")
        edit_layout = QVBoxLayout(edit_group)
        self._edited_text = QLabel()
        self._edited_text.setWordWrap(True)
        self._edited_text.setStyleSheet(
            "background: #e8f4f8; padding: 4px; border-radius: 2px;"
        )
        edit_layout.addWidget(self._edited_text)
        layout.addWidget(edit_group)
    
    def set_comparison(self, original: str, edited: str) -> None:
        """Establecer textos a comparar."""
        self._original_text.setText(original or "(vacío)")
        self._edited_text.setText(edited or "(vacío)")


class EditorToolBar(QToolBar):
    """
    Barra de herramientas del PDFTextEditor.
    """
    
    # Señales
    modeChanged = pyqtSignal(EditMode)
    metricsToggled = pyqtSignal(bool)
    applyClicked = pyqtSignal()
    cancelClicked = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Editor PDF", parent)
        self.setMovable(False)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configurar UI de la barra."""
        # Acciones de modo
        self._mode_actions = {}
        
        mode_menu = QMenu("Modo", self)
        for mode in EditMode:
            action = mode_menu.addAction(mode.value.capitalize())
            action.setCheckable(True)
            action.setData(mode)
            action.triggered.connect(lambda checked, m=mode: self._on_mode_selected(m))
            self._mode_actions[mode] = action
        
        self._mode_actions[EditMode.PRESERVE].setChecked(True)
        
        mode_btn = QToolButton()
        mode_btn.setText("Modo")
        mode_btn.setMenu(mode_menu)
        mode_btn.setPopupMode(QToolButton.InstantPopup)
        self.addWidget(mode_btn)
        
        self.addSeparator()
        
        # Toggle métricas
        self._metrics_action = QAction("Métricas", self)
        self._metrics_action.setCheckable(True)
        self._metrics_action.setChecked(True)
        self._metrics_action.triggered.connect(
            lambda checked: self.metricsToggled.emit(checked)
        )
        self.addAction(self._metrics_action)
        
        self.addSeparator()
        
        # Botones principales
        self._apply_action = QAction("✓ Aplicar", self)
        self._apply_action.triggered.connect(self.applyClicked.emit)
        self.addAction(self._apply_action)
        
        self._cancel_action = QAction("✗ Cancelar", self)
        self._cancel_action.triggered.connect(self.cancelClicked.emit)
        self.addAction(self._cancel_action)
    
    def _on_mode_selected(self, mode: EditMode) -> None:
        """Manejar selección de modo."""
        for m, action in self._mode_actions.items():
            action.setChecked(m == mode)
        self.modeChanged.emit(mode)


# ================== Editor Principal ==================


class TextEditArea(QTextEdit):
    """
    Área de edición de texto con soporte para propiedades tipográficas.
    """
    
    # Señales
    textModified = pyqtSignal(str)  # Texto actual
    cursorMoved = pyqtSignal(int)   # Posición del cursor
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._original_text = ""
        self._span_data: Optional[Dict[str, Any]] = None
        
        # Configuración
        self.setAcceptRichText(False)  # Solo texto plano inicialmente
        self.setTabChangesFocus(False)
        
        # Conectar señales
        self.textChanged.connect(self._on_text_changed)
        self.cursorPositionChanged.connect(self._on_cursor_moved)
        
        # Estilos
        self.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
            }
            QTextEdit:focus {
                border-color: #0078d4;
            }
        """)
    
    def set_span_data(self, span_data: Dict[str, Any]) -> None:
        """
        Configurar el área de edición para un span específico.
        
        Args:
            span_data: Diccionario con datos del span (text, font_name, etc.)
        """
        self._span_data = span_data
        self._original_text = span_data.get('text', '')
        
        # Configurar fuente
        font_name = span_data.get('font_name', 'Helvetica')
        font_size = span_data.get('font_size', 12)
        is_bold = span_data.get('is_bold', False)
        is_italic = span_data.get('is_italic', False)
        
        font = QFont(font_name, int(font_size))
        font.setBold(is_bold)
        font.setItalic(is_italic)
        self.setFont(font)
        
        # Configurar color
        fill_color = span_data.get('fill_color', '#000000')
        if isinstance(fill_color, str):
            color = QColor(fill_color)
        else:
            color = QColor(0, 0, 0)
        self.setTextColor(color)
        
        # Establecer texto
        self.setPlainText(self._original_text)
    
    def get_current_text(self) -> str:
        """Obtener texto actual."""
        return self.toPlainText()
    
    def get_original_text(self) -> str:
        """Obtener texto original."""
        return self._original_text
    
    def has_changes(self) -> bool:
        """Verificar si hay cambios."""
        return self.get_current_text() != self._original_text
    
    def _on_text_changed(self) -> None:
        """Manejar cambio de texto."""
        self.textModified.emit(self.get_current_text())
    
    def _on_cursor_moved(self) -> None:
        """Manejar movimiento del cursor."""
        self.cursorMoved.emit(self.textCursor().position())


class PDFTextEditorDialog(QDialog):
    """
    Diálogo completo del PDFTextEditor.
    
    Integra todos los componentes de Phase 3C para edición de texto PDF
    con preservación de propiedades tipográficas.
    
    Signals:
        textEdited: Emitido cuando se confirma la edición (EditedSpan)
        cancelled: Emitido cuando se cancela la edición
    """
    
    # Señales
    textEdited = pyqtSignal(object)  # EditedSpan
    cancelled = pyqtSignal()
    
    def __init__(
        self,
        span_data: Dict[str, Any],
        config: Optional[EditorConfig] = None,
        parent: Optional[QWidget] = None
    ):
        """
        Inicializar el diálogo de edición.
        
        Args:
            span_data: Datos del span a editar
            config: Configuración del editor
            parent: Widget padre
        """
        super().__init__(parent)
        
        self._span_data = span_data
        self._config = config or EditorConfig()
        self._fit_status = FitStatus.UNKNOWN
        self._validation_timer: Optional[QTimer] = None
        
        self._setup_ui()
        self._setup_connections()
        self._load_span_data()
    
    def _setup_ui(self) -> None:
        """Configurar la interfaz de usuario."""
        self.setWindowTitle("Editor de Texto PDF")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        
        # Barra de herramientas
        self._toolbar = EditorToolBar()
        main_layout.addWidget(self._toolbar)
        
        # Splitter principal
        splitter = QSplitter(Qt.Horizontal)
        
        # Panel izquierdo: Editor
        edit_panel = QWidget()
        edit_layout = QVBoxLayout(edit_panel)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        
        # Título con info del span
        self._info_label = QLabel()
        self._info_label.setStyleSheet(
            "font-weight: bold; padding: 4px; background: #f0f0f0; border-radius: 4px;"
        )
        edit_layout.addWidget(self._info_label)
        
        # Área de edición
        self._edit_area = TextEditArea()
        edit_layout.addWidget(self._edit_area, 1)
        
        # Barra de métricas
        self._metrics_bar = MetricsStatusBar()
        edit_layout.addWidget(self._metrics_bar)
        
        splitter.addWidget(edit_panel)
        
        # Panel derecho: Propiedades
        if self._config.show_property_panel and HAS_PROPERTY_INSPECTOR:
            self._property_inspector = PropertyInspector()
            splitter.addWidget(self._property_inspector)
            splitter.setSizes([600, 400])
        else:
            self._property_inspector = None
        
        main_layout.addWidget(splitter, 1)
        
        # Comparación original/editado
        self._comparison = SpanComparisonWidget()
        main_layout.addWidget(self._comparison)
        
        # Botones de acción
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self._apply_btn = QPushButton("Aplicar Cambios")
        self._apply_btn.setDefault(True)
        self._apply_btn.setStyleSheet("""
            QPushButton {
                background: #0078d4;
                color: white;
                padding: 8px 24px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #106ebe;
            }
            QPushButton:disabled {
                background: #ccc;
            }
        """)
        btn_layout.addWidget(self._apply_btn)
        
        self._cancel_btn = QPushButton("Cancelar")
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 24px;
                border-radius: 4px;
            }
        """)
        btn_layout.addWidget(self._cancel_btn)
        
        main_layout.addLayout(btn_layout)
        
        # Timer para validación
        if self._config.auto_validate:
            self._validation_timer = QTimer(self)
            self._validation_timer.setSingleShot(True)
            self._validation_timer.timeout.connect(self._validate_fit)
    
    def _setup_connections(self) -> None:
        """Configurar conexiones de señales."""
        # Toolbar
        self._toolbar.modeChanged.connect(self._on_mode_changed)
        self._toolbar.metricsToggled.connect(self._on_metrics_toggled)
        self._toolbar.applyClicked.connect(self._on_apply)
        self._toolbar.cancelClicked.connect(self._on_cancel)
        
        # Editor
        self._edit_area.textModified.connect(self._on_text_modified)
        self._edit_area.cursorMoved.connect(self._on_cursor_moved)
        
        # Botones
        self._apply_btn.clicked.connect(self._on_apply)
        self._cancel_btn.clicked.connect(self._on_cancel)
    
    def _load_span_data(self) -> None:
        """Cargar datos del span en el editor."""
        # Info del span
        text = self._span_data.get('text', '')
        font = self._span_data.get('font_name', 'Unknown')
        size = self._span_data.get('font_size', 12)
        self._info_label.setText(
            f"Editando: \"{text[:50]}...\" ({font}, {size}pt)" if len(text) > 50
            else f"Editando: \"{text}\" ({font}, {size}pt)"
        )
        
        # Cargar en editor
        self._edit_area.set_span_data(self._span_data)
        
        # Actualizar comparación
        self._comparison.set_comparison(text, text)
        
        # Actualizar PropertyInspector
        if self._property_inspector:
            self._property_inspector.update_from_span(self._span_data)
        
        # Validación inicial
        self._validate_fit()
    
    def _on_mode_changed(self, mode: EditMode) -> None:
        """Manejar cambio de modo de edición."""
        self._config.mode = mode
        self._validate_fit()
    
    def _on_metrics_toggled(self, show: bool) -> None:
        """Manejar toggle de métricas."""
        self._config.show_metrics = show
        self._metrics_bar.setVisible(show)
    
    def _on_text_modified(self, text: str) -> None:
        """Manejar modificación de texto."""
        # Actualizar comparación
        original = self._span_data.get('text', '')
        self._comparison.set_comparison(original, text)
        
        # Programar validación
        if self._validation_timer and self._config.auto_validate:
            self._validation_timer.start(self._config.validate_delay_ms)
        
        # Habilitar/deshabilitar botón aplicar
        self._apply_btn.setEnabled(self._edit_area.has_changes())
    
    def _on_cursor_moved(self, position: int) -> None:
        """Manejar movimiento del cursor."""
        # Futuro: actualizar métricas del carácter actual
        pass
    
    def _validate_fit(self) -> None:
        """
        Validar si el texto editado cabe en el espacio original.
        """
        current_text = self._edit_area.get_current_text()
        original_bbox = self._span_data.get('bbox')
        
        if not original_bbox:
            self._fit_status = FitStatus.UNKNOWN
            self._update_fit_display()
            return
        
        # Calcular ancho original
        original_width = original_bbox[2] - original_bbox[0]
        
        # Calcular ancho nuevo (aproximado con QFontMetrics)
        font_name = self._span_data.get('font_name', 'Helvetica')
        font_size = self._span_data.get('font_size', 12)
        is_bold = self._span_data.get('is_bold', False)
        
        font = QFont(font_name, int(font_size))
        font.setBold(is_bold)
        metrics = QFontMetrics(font)
        new_width = metrics.horizontalAdvance(current_text)
        
        # Convertir pixeles a puntos PDF (aproximado)
        # PDF típicamente usa 72 puntos por pulgada
        # QFontMetrics usa pixels del dispositivo
        dpi = 96  # DPI típico de pantalla
        new_width_pt = new_width * 72 / dpi
        
        # Determinar estado
        if new_width_pt <= original_width * 0.98:
            self._fit_status = FitStatus.FITS
        elif new_width_pt <= original_width * 1.05:
            self._fit_status = FitStatus.TIGHT
        else:
            self._fit_status = FitStatus.OVERFLOW
        
        self._update_fit_display(original_width, new_width_pt)
    
    def _update_fit_display(
        self,
        original_width: Optional[float] = None,
        new_width: Optional[float] = None
    ) -> None:
        """Actualizar visualización de estado de ajuste."""
        font_info = None
        if self._span_data:
            font_name = self._span_data.get('font_name', 'Unknown')
            font_size = self._span_data.get('font_size', 12)
            font_info = f"{font_name} {font_size}pt"
        
        self._metrics_bar.update_metrics(
            original_width, new_width, self._fit_status, font_info
        )
        
        # Cambiar borde del editor según estado
        border_colors = {
            FitStatus.FITS: "#27ae60",
            FitStatus.TIGHT: "#f39c12",
            FitStatus.OVERFLOW: "#e74c3c",
            FitStatus.UNKNOWN: "#ccc",
        }
        border_color = border_colors.get(self._fit_status, "#ccc")
        self._edit_area.setStyleSheet(f"""
            QTextEdit {{
                background: white;
                border: 2px solid {border_color};
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
            }}
        """)
    
    def _on_apply(self) -> None:
        """Aplicar los cambios."""
        if not self._edit_area.has_changes():
            self.accept()
            return
        
        # Advertir si hay overflow y modo es PRESERVE
        if (self._fit_status == FitStatus.OVERFLOW and 
            self._config.mode == EditMode.PRESERVE):
            reply = QMessageBox.warning(
                self,
                "Texto desborda",
                "El texto editado no cabe en el espacio original.\n\n"
                "¿Desea aplicar los cambios de todas formas?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # Crear resultado
        edited = EditedSpan(
            original_span=self._span_data,
            new_text=self._edit_area.get_current_text(),
            original_text=self._edit_area.get_original_text(),
            fit_status=self._fit_status
        )
        
        self.textEdited.emit(edited)
        self.accept()
    
    def _on_cancel(self) -> None:
        """Cancelar la edición."""
        if self._edit_area.has_changes():
            reply = QMessageBox.question(
                self,
                "Descartar cambios",
                "¿Desea descartar los cambios realizados?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        self.cancelled.emit()
        self.reject()
    
    def get_edited_span(self) -> Optional[EditedSpan]:
        """
        Obtener el span editado si se aplicaron cambios.
        
        Returns:
            EditedSpan si hay cambios, None si no
        """
        if not self._edit_area.has_changes():
            return None
        
        return EditedSpan(
            original_span=self._span_data,
            new_text=self._edit_area.get_current_text(),
            original_text=self._edit_area.get_original_text(),
            fit_status=self._fit_status
        )


# ================== Clase Principal de Integración ==================


class PDFTextEditor(QWidget):
    """
    Widget editor de texto PDF que integra todos los componentes de Phase 3C.
    
    Este widget puede embeberse en la ventana principal o usarse standalone.
    
    Signals:
        spanEditRequested: Cuando el usuario quiere editar un span (span_data)
        spanEdited: Cuando se completa una edición (EditedSpan)
        selectionChanged: Cuando cambia la selección (list de span_data)
    """
    
    # Señales
    spanEditRequested = pyqtSignal(object)
    spanEdited = pyqtSignal(object)
    selectionChanged = pyqtSignal(list)
    
    def __init__(
        self,
        config: Optional[EditorConfig] = None,
        parent: Optional[QWidget] = None
    ):
        """
        Inicializar el PDFTextEditor.
        
        Args:
            config: Configuración del editor
            parent: Widget padre
        """
        super().__init__(parent)
        
        self._config = config or EditorConfig()
        self._selected_spans: List[Dict[str, Any]] = []
        self._current_doc = None
        self._current_page = 0
        
        # Componentes opcionales
        self._selection_overlay: Optional[TextSelectionOverlay] = None
        self._property_inspector: Optional[PropertyInspector] = None
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configurar la interfaz."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Info label
        self._info_label = QLabel("Seleccione texto para editar")
        self._info_label.setStyleSheet(
            "padding: 8px; background: #e8f4f8; border-radius: 4px;"
        )
        layout.addWidget(self._info_label)
        
        # Property inspector si está disponible
        if HAS_PROPERTY_INSPECTOR:
            self._property_inspector = PropertyInspector()
            layout.addWidget(self._property_inspector, 1)
        
        # Botón de editar
        self._edit_btn = QPushButton("Editar Selección")
        self._edit_btn.setEnabled(False)
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        layout.addWidget(self._edit_btn)
    
    def set_selection_overlay(self, overlay: 'TextSelectionOverlay') -> None:
        """
        Conectar con un TextSelectionOverlay.
        
        Args:
            overlay: Overlay de selección
        """
        self._selection_overlay = overlay
        
        if overlay:
            overlay.selectionChanged.connect(self._on_overlay_selection_changed)
    
    def set_selected_spans(self, spans: List[Dict[str, Any]]) -> None:
        """
        Establecer los spans seleccionados.
        
        Args:
            spans: Lista de diccionarios con datos de spans
        """
        self._selected_spans = spans
        
        # Actualizar UI
        count = len(spans)
        if count == 0:
            self._info_label.setText("Seleccione texto para editar")
            self._edit_btn.setEnabled(False)
        elif count == 1:
            text = spans[0].get('text', '')[:50]
            self._info_label.setText(f"Seleccionado: \"{text}...\"" if len(text) == 50 else f"Seleccionado: \"{text}\"")
            self._edit_btn.setEnabled(True)
        else:
            self._info_label.setText(f"Seleccionados: {count} elementos")
            self._edit_btn.setEnabled(True)
        
        # Actualizar property inspector
        if self._property_inspector and count == 1:
            self._property_inspector.update_from_span(spans[0])
        elif self._property_inspector:
            self._property_inspector.clear()
        
        # Emitir señal
        self.selectionChanged.emit(spans)
    
    def _on_overlay_selection_changed(self) -> None:
        """Manejar cambio de selección en overlay."""
        if self._selection_overlay:
            spans = self._selection_overlay.get_selected_spans_data()
            self.set_selected_spans(spans)
    
    def _on_edit_clicked(self) -> None:
        """Manejar clic en botón editar."""
        if not self._selected_spans:
            return
        
        # Editar primer span (o multi-edición en futuro)
        span_data = self._selected_spans[0]
        self.spanEditRequested.emit(span_data)
        
        # Abrir diálogo
        self.edit_span(span_data)
    
    def edit_span(self, span_data: Dict[str, Any]) -> Optional[EditedSpan]:
        """
        Abrir el diálogo de edición para un span.
        
        Args:
            span_data: Datos del span a editar
            
        Returns:
            EditedSpan si se editó, None si se canceló
        """
        dialog = PDFTextEditorDialog(
            span_data=span_data,
            config=self._config,
            parent=self
        )
        
        result = None
        
        def on_edited(edited: EditedSpan):
            nonlocal result
            result = edited
            self.spanEdited.emit(edited)
        
        dialog.textEdited.connect(on_edited)
        dialog.exec_()
        
        return result
    
    def clear_selection(self) -> None:
        """Limpiar selección actual."""
        self._selected_spans = []
        self.set_selected_spans([])
        
        if self._selection_overlay:
            self._selection_overlay.clear_all()


# ================== Factory Functions ==================


def create_pdf_text_editor(
    with_property_panel: bool = True,
    mode: EditMode = EditMode.PRESERVE
) -> PDFTextEditor:
    """
    Crear un PDFTextEditor con configuración predefinida.
    
    Args:
        with_property_panel: Incluir panel de propiedades
        mode: Modo de edición inicial
        
    Returns:
        PDFTextEditor configurado
    """
    config = EditorConfig(
        mode=mode,
        show_property_panel=with_property_panel
    )
    return PDFTextEditor(config=config)


def show_pdf_text_editor(
    span_data: Dict[str, Any],
    parent: Optional[QWidget] = None,
    config: Optional[EditorConfig] = None
) -> Optional[EditedSpan]:
    """
    Mostrar el diálogo de edición y retornar el resultado.
    
    Args:
        span_data: Datos del span a editar
        parent: Widget padre
        config: Configuración opcional
        
    Returns:
        EditedSpan si se editó, None si se canceló
    """
    dialog = PDFTextEditorDialog(
        span_data=span_data,
        config=config,
        parent=parent
    )
    
    result = None
    
    def on_edited(edited: EditedSpan):
        nonlocal result
        result = edited
    
    dialog.textEdited.connect(on_edited)
    
    if dialog.exec_() == QDialog.Accepted:
        return result
    
    return None

"""
UnifiedTextEditor - Editor de texto por spans para PDF.

Diseño: Muestra el párrafo completo como contexto visual (read-only),
y permite editar individualmente cada span conservando 100% la geometría
y tipografía original del PDF.

Flujo:
1. El usuario clickea texto → se detecta el span exacto
2. Se muestra el párrafo completo con cada span distinguido por colores
3. El span clickeado se pre-selecciona y es editable
4. El usuario puede navegar entre spans con Tab o click
5. Solo los spans modificados se marcan como dirty → PageWriter los reescribe

Uso desde pdf_viewer:
    from ui.unified_text_editor import show_unified_editor
    result = show_unified_editor(parent, spans, "Editar texto", selected_span=span)
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QWidget, QScrollArea, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette

from typing import List, Optional
from core.text_engine.page_document_model import EditableSpan


# Colores para distinguir spans en el contexto visual
_SPAN_COLORS = [
    "#3a86ff", "#8338ec", "#ff006e", "#fb5607", "#ffbe0b",
    "#06d6a0", "#118ab2", "#e63946", "#457b9d", "#2a9d8f",
]

_SELECTED_BG = "#0d3b66"
_HOVER_BG = "#1b4965"


class SpanEditWidget(QFrame):
    """Widget para un span individual: muestra info + campo editable."""
    
    spanModified = pyqtSignal()
    
    def __init__(self, span: EditableSpan, index: int, parent=None):
        super().__init__(parent)
        self.span = span
        self.index = index
        self._color = _SPAN_COLORS[index % len(_SPAN_COLORS)]
        self._is_selected = False
        self._setup_ui()
    
    def _setup_ui(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style(selected=False)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        
        # Header: info del span (fuente, tamaño, estilo)
        info_parts = [f"<b style='color:{self._color};'>■</b>"]
        info_parts.append(f"<span style='color:#bbb;'>{self.span.font_name}</span>")
        info_parts.append(f"<span style='color:#999;'>{self.span.font_size:.1f}pt</span>")
        if self.span.is_bold:
            info_parts.append("<span style='color:#ffa;'>B</span>")
        if self.span.is_italic:
            info_parts.append("<span style='color:#aff;'>I</span>")
        
        header = QLabel(" · ".join(info_parts))
        header.setTextFormat(Qt.RichText)
        header.setStyleSheet("font-size: 10px; color: #888; padding: 0; margin: 0;")
        layout.addWidget(header)
        
        # Campo de edición del texto
        self.edit = QLineEdit(self.span.original_text)
        self.edit.setStyleSheet(f"""
            QLineEdit {{
                background: #1e1e1e;
                border: 1px solid {self._color}40;
                border-radius: 3px;
                padding: 6px 8px;
                color: white;
                font-size: 13px;
                selection-background-color: #0078d4;
            }}
            QLineEdit:focus {{
                border: 2px solid {self._color};
                background: #252525;
            }}
        """)
        
        # Aplicar fuente original para preview visual
        font = QFont()
        font.setFamily(self.span.font_name)
        font.setPointSizeF(min(self.span.font_size, 14))
        font.setBold(self.span.is_bold)
        font.setItalic(self.span.is_italic)
        self.edit.setFont(font)
        
        self.edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.edit)
        
        # Label de advertencia de desbordamiento (oculto por defecto)
        self._overflow_label = QLabel("")
        self._overflow_label.setStyleSheet("color: #ff6b6b; font-size: 10px;")
        self._overflow_label.hide()
        layout.addWidget(self._overflow_label)
    
    def _on_text_changed(self, new_text: str):
        """Llamado cuando el usuario edita el texto."""
        self.span.text = new_text
        
        # Estimar desbordamiento (heurística simple basada en longitud)
        orig_len = len(self.span.original_text)
        new_len = len(new_text)
        if orig_len > 0 and new_len > orig_len * 1.3:
            self._overflow_label.setText(
                f"⚠ Texto ~{int((new_len/orig_len - 1)*100)}% más largo que el original"
            )
            self._overflow_label.show()
        else:
            self._overflow_label.hide()
        
        self.spanModified.emit()
    
    def set_selected(self, selected: bool):
        """Selecciona/deselecciona visualmente este span."""
        self._is_selected = selected
        self._update_style(selected)
        if selected:
            self.edit.setFocus()
    
    def _update_style(self, selected: bool):
        bg = _SELECTED_BG if selected else "#2d2d30"
        border = self._color if selected else "#3d3d3d"
        self.setStyleSheet(f"""
            SpanEditWidget {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
        """)
    
    def mousePressEvent(self, event):
        """Click en el widget selecciona este span."""
        self.set_selected(True)
        super().mousePressEvent(event)


class UnifiedTextEditorDialog(QDialog):
    """Diálogo de edición de texto por spans.

    Muestra el párrafo como contexto con cada span individualmente editable.
    El span clickeado por el usuario se pre-selecciona.
    """

    def __init__(self, spans: List[EditableSpan], title: str = "Editar texto",
                 selected_span: Optional[EditableSpan] = None, parent=None):
        super().__init__(parent)
        self.spans = spans
        self.selected_span = selected_span
        self._span_widgets: List[SpanEditWidget] = []
        self._setup_ui(title)

    def _setup_ui(self, title: str):
        self.setWindowTitle(title)
        self.setMinimumSize(580, 350)
        self.resize(680, 500)

        self.setStyleSheet("""
            QDialog {
                background-color: #2d2d30;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background: #3d3d3d;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px 20px;
                color: white;
                min-width: 90px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #4a4a4a;
                border-color: #0078d4;
            }
            QPushButton#acceptBtn {
                background: #0078d4;
                border: none;
            }
            QPushButton#acceptBtn:hover {
                background: #1a8cff;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # --- Header: contexto visual del párrafo completo ---
        context_label = QLabel(
            "<b style='color:#ddd; font-size:13px;'>Contexto del párrafo</b>"
        )
        context_label.setTextFormat(Qt.RichText)
        main_layout.addWidget(context_label)
        
        # Preview del párrafo con spans coloreados
        preview_html = self._build_context_html()
        self._preview = QLabel(preview_html)
        self._preview.setTextFormat(Qt.RichText)
        self._preview.setWordWrap(True)
        self._preview.setStyleSheet(
            "background: #1a1a1a; border: 1px solid #444; border-radius: 4px; "
            "padding: 10px; font-size: 12px; color: #ccc;"
        )
        self._preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        main_layout.addWidget(self._preview)

        # --- Área de edición de spans ---
        edit_header = QLabel(
            f"<b style='color:#ddd; font-size:13px;'>Editar spans</b>"
            f"<span style='color:#888; font-size:11px;'> — {len(self.spans)} fragmento(s)</span>"
        )
        edit_header.setTextFormat(Qt.RichText)
        main_layout.addWidget(edit_header)

        # ScrollArea para los span editors
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { 
                background: transparent; 
                border: none; 
            }
            QScrollArea > QWidget > QWidget { 
                background: transparent; 
            }
        """)
        
        scroll_content = QWidget()
        self._spans_layout = QVBoxLayout(scroll_content)
        self._spans_layout.setSpacing(6)
        self._spans_layout.setContentsMargins(2, 2, 2, 2)
        
        # Crear un widget por cada span
        selected_widget = None
        for i, span in enumerate(self.spans):
            widget = SpanEditWidget(span, i)
            widget.spanModified.connect(self._on_any_span_modified)
            self._span_widgets.append(widget)
            self._spans_layout.addWidget(widget)
            
            if self.selected_span and span is self.selected_span:
                selected_widget = widget
        
        self._spans_layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)

        # --- Status ---
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #888; font-size: 11px;")
        main_layout.addWidget(self._status_label)

        # --- Botones ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self._accept_btn = QPushButton("Aplicar cambios")
        self._accept_btn.setObjectName("acceptBtn")
        self._accept_btn.clicked.connect(self.accept)
        self._accept_btn.setDefault(True)
        self._accept_btn.setEnabled(False)
        btn_layout.addWidget(self._accept_btn)

        main_layout.addLayout(btn_layout)

        # Seleccionar el span clickeado (o el primero)
        if selected_widget:
            selected_widget.set_selected(True)
        elif self._span_widgets:
            self._span_widgets[0].set_selected(True)

    def _build_context_html(self) -> str:
        """Genera HTML con el contexto del párrafo, cada span con su color."""
        if not self.spans:
            return "<i>Sin texto</i>"
        
        # Agrupar spans por baseline para reconstruir líneas
        from collections import OrderedDict
        lines: dict = OrderedDict()
        for i, span in enumerate(self.spans):
            key = round(span.baseline_y, 1)
            if key not in lines:
                lines[key] = []
            lines[key].append((i, span))
        
        html_lines = []
        for baseline_y in sorted(lines.keys()):
            line_spans = sorted(lines[baseline_y], key=lambda t: t[1].bbox[0])
            line_html = ""
            for idx, span in line_spans:
                color = _SPAN_COLORS[idx % len(_SPAN_COLORS)]
                is_sel = (self.selected_span and span is self.selected_span)
                bg = f"background:{_SELECTED_BG};" if is_sel else ""
                weight = "font-weight:bold;" if span.is_bold else ""
                style_it = "font-style:italic;" if span.is_italic else ""
                text = span.original_text.replace("&", "&amp;").replace("<", "&lt;")
                line_html += (
                    f"<span style='color:{color}; {weight}{style_it}{bg} "
                    f"border-bottom: 2px solid {color}50; padding: 1px 2px;'>"
                    f"{text}</span>"
                )
            html_lines.append(line_html)
        
        return "<br>".join(html_lines)
    
    def _on_any_span_modified(self):
        """Actualiza estado cuando cualquier span cambia."""
        dirty_count = sum(1 for s in self.spans if s.dirty)
        total = len(self.spans)
        
        if dirty_count > 0:
            self._accept_btn.setEnabled(True)
            self._status_label.setText(
                f"✎ {dirty_count} de {total} fragmento(s) modificado(s)"
            )
            self._status_label.setStyleSheet("color: #4fc3f7; font-size: 11px;")
        else:
            self._accept_btn.setEnabled(False)
            self._status_label.setText("")
        
        # Actualizar preview del contexto con cambios en tiempo real
        self._update_live_preview()
    
    def _update_live_preview(self):
        """Actualiza el preview del párrafo con los cambios actuales."""
        from collections import OrderedDict
        lines: dict = OrderedDict()
        for i, span in enumerate(self.spans):
            key = round(span.baseline_y, 1)
            if key not in lines:
                lines[key] = []
            lines[key].append((i, span))
        
        html_lines = []
        for baseline_y in sorted(lines.keys()):
            line_spans = sorted(lines[baseline_y], key=lambda t: t[1].bbox[0])
            line_html = ""
            for idx, span in line_spans:
                color = _SPAN_COLORS[idx % len(_SPAN_COLORS)]
                weight = "font-weight:bold;" if span.is_bold else ""
                style_it = "font-style:italic;" if span.is_italic else ""
                current_text = span.text.replace("&", "&amp;").replace("<", "&lt;")
                is_dirty = span.dirty
                dirty_style = f"background:#1a3a1a;" if is_dirty else ""
                line_html += (
                    f"<span style='color:{color}; {weight}{style_it}{dirty_style} "
                    f"border-bottom: 2px solid {color}50; padding: 1px 2px;'>"
                    f"{current_text}</span>"
                )
            html_lines.append(line_html)
        
        self._preview.setText("<br>".join(html_lines))


def show_unified_editor(
    parent: QWidget,
    spans: List[EditableSpan],
    title: str = "Editar texto",
    selected_span: Optional[EditableSpan] = None
) -> Optional[List[EditableSpan]]:
    """Muestra el editor unificado y retorna los spans editados."""
    if not spans:
        return None

    dialog = UnifiedTextEditorDialog(
        spans, title=title, selected_span=selected_span, parent=parent
    )

    if dialog.exec_() == QDialog.Accepted:
        dirty = [s for s in spans if s.dirty]
        return dirty if dirty else None

    # Si se canceló, revertir los cambios
    for span in spans:
        span.new_text = None
        span.dirty = False

    return None

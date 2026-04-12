"""Panel lateral de chat con IA para consultar documentos PDF.

Provee una interfaz de chat con historial, citas clicables
y búsqueda semántica RAG sobre el documento abierto.
"""

import logging
from typing import Optional

from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QScrollArea,
    QFrame, QSizePolicy, QApplication,
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QTextCursor

from ui.theme_manager import ThemeColor, ThemeStyles

logger = logging.getLogger(__name__)


class ChatWorker(QThread):
    """Worker para ejecutar consultas de IA en segundo plano."""

    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, chat_engine, question: str, parent=None):
        """Inicializa el worker.

        Args:
            chat_engine: Motor de chat.
            question: Pregunta del usuario.
        """
        super().__init__(parent)
        self._engine = chat_engine
        self._question = question

    def run(self):
        """Ejecuta la consulta."""
        try:
            result = self._engine.ask(self._question)
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Error en chat worker: {e}")
            self.error.emit(str(e))


class MessageWidget(QFrame):
    """Widget para mostrar un mensaje de chat."""

    citation_clicked = pyqtSignal(int)

    def __init__(self, role: str, content: str, citations=None, parent=None):
        """Inicializa el widget de mensaje.

        Args:
            role: 'user' o 'assistant'.
            content: Contenido del mensaje.
            citations: Lista de citas (opcional).
        """
        super().__init__(parent)
        self._role = role
        self._citations = citations or []

        self._setup_ui(content)

    def _setup_ui(self, content: str):
        """Configura la interfaz del mensaje."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        is_user = self._role == "user"

        self.setStyleSheet(f"""
            MessageWidget {{
                background-color: {ThemeColor.ACCENT if is_user else ThemeColor.BG_TERTIARY};
                border-radius: 10px;
                margin: {'2px 2px 2px 40px' if is_user else '2px 40px 2px 2px'};
            }}
        """)

        role_label = QLabel("Tú" if is_user else "🤖 Asistente")
        role_label.setStyleSheet(f"""
            font-weight: bold;
            font-size: 11px;
            color: {ThemeColor.TEXT_SECONDARY};
            background: transparent;
        """)
        layout.addWidget(role_label)

        text_label = QLabel(content)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        text_label.setStyleSheet(f"""
            color: {ThemeColor.TEXT_PRIMARY};
            font-size: 13px;
            background: transparent;
        """)
        layout.addWidget(text_label)

        if self._citations:
            self._add_citations(layout)

    def _add_citations(self, layout):
        """Agrega citas clicables al mensaje."""
        citations_frame = QFrame()
        citations_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {ThemeColor.BG_SECONDARY};
                border-radius: 6px;
                padding: 4px;
            }}
        """)
        cl = QVBoxLayout(citations_frame)
        cl.setContentsMargins(4, 4, 4, 4)
        cl.setSpacing(2)

        header = QLabel("📄 Citas:")
        header.setStyleSheet(f"""
            font-size: 11px;
            font-weight: bold;
            color: {ThemeColor.TEXT_SECONDARY};
            background: transparent;
        """)
        cl.addWidget(header)

        for citation in self._citations:
            btn = QPushButton(f"Página {citation.page_num + 1}")
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {ThemeColor.ACCENT};
                    background: transparent;
                    border: none;
                    text-align: left;
                    font-size: 11px;
                    text-decoration: underline;
                    padding: 1px 4px;
                }}
                QPushButton:hover {{
                    color: {ThemeColor.ACCENT_HOVER};
                }}
            """)
            page = citation.page_num
            btn.clicked.connect(lambda checked, p=page: self.citation_clicked.emit(p))
            cl.addWidget(btn)

        layout.addWidget(citations_frame)


class AIChatPanel(QDockWidget):
    """Panel lateral de chat con IA.

    Signals:
        navigateToPage: Emitida al hacer clic en una cita (page_num 0-based).
    """

    navigateToPage = pyqtSignal(int)

    def __init__(self, parent=None):
        """Inicializa el panel de chat."""
        super().__init__("💬 Chat IA", parent)
        self.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.setMinimumWidth(300)

        self._chat_engine = None
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        """Configura la interfaz del panel."""
        container = QWidget()
        container.setStyleSheet(f"""
            background-color: {ThemeColor.BG_PRIMARY};
        """)
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # Header
        header = QLabel("Pregunta sobre tu documento")
        header.setStyleSheet(f"""
            color: {ThemeColor.TEXT_SECONDARY};
            font-size: 12px;
            padding: 4px;
            background: transparent;
        """)
        main_layout.addWidget(header)

        # Chat history scroll area
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {ThemeColor.BORDER_LIGHT};
                border-radius: 6px;
                background-color: {ThemeColor.BG_SECONDARY};
            }}
        """)

        self._chat_container = QWidget()
        self._chat_layout = QVBoxLayout(self._chat_container)
        self._chat_layout.setAlignment(Qt.AlignTop)
        self._chat_layout.setSpacing(6)
        self._chat_layout.setContentsMargins(4, 4, 4, 4)

        self._scroll_area.setWidget(self._chat_container)
        main_layout.addWidget(self._scroll_area, stretch=1)

        # Status label
        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"""
            color: {ThemeColor.TEXT_PLACEHOLDER};
            font-size: 11px;
            background: transparent;
        """)
        self._status_label.hide()
        main_layout.addWidget(self._status_label)

        # Input area
        input_layout = QHBoxLayout()
        input_layout.setSpacing(4)

        self._input_field = QTextEdit()
        self._input_field.setPlaceholderText("Escribe tu pregunta...")
        self._input_field.setMaximumHeight(80)
        self._input_field.setStyleSheet(f"""
            QTextEdit {{
                background-color: {ThemeColor.BG_TERTIARY};
                color: {ThemeColor.TEXT_PRIMARY};
                border: 1px solid {ThemeColor.BORDER_LIGHT};
                border-radius: 6px;
                padding: 6px;
                font-size: 13px;
            }}
            QTextEdit:focus {{
                border-color: {ThemeColor.ACCENT};
            }}
        """)
        input_layout.addWidget(self._input_field, stretch=1)

        self._btn_send = QPushButton("➤")
        self._btn_send.setFixedSize(40, 40)
        self._btn_send.setToolTip("Enviar pregunta")
        self._btn_send.setStyleSheet(f"""
            QPushButton {{
                background-color: {ThemeColor.ACCENT};
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {ThemeColor.ACCENT_HOVER};
            }}
            QPushButton:disabled {{
                background-color: {ThemeColor.BG_TERTIARY};
                color: {ThemeColor.TEXT_PLACEHOLDER};
            }}
        """)
        self._btn_send.clicked.connect(self._on_send)
        self._btn_send.setEnabled(False)
        input_layout.addWidget(self._btn_send)

        main_layout.addLayout(input_layout)

        # Clear button
        self._btn_clear = QPushButton("🗑️ Limpiar chat")
        self._btn_clear.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {ThemeColor.TEXT_SECONDARY};
                border: 1px solid {ThemeColor.BORDER_LIGHT};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {ThemeColor.BG_TERTIARY};
            }}
        """)
        self._btn_clear.clicked.connect(self._on_clear)
        main_layout.addWidget(self._btn_clear)

        self.setWidget(container)

    def set_chat_engine(self, engine) -> None:
        """Establece el motor de chat.

        Args:
            engine: Instancia de ChatEngine.
        """
        self._chat_engine = engine
        self._btn_send.setEnabled(engine is not None)

    def _on_send(self):
        """Envía la pregunta al motor de chat."""
        text = self._input_field.toPlainText().strip()
        if not text or not self._chat_engine:
            return

        self._input_field.clear()
        self._add_message("user", text)

        self._btn_send.setEnabled(False)
        self._status_label.setText("Pensando...")
        self._status_label.show()

        self._worker = ChatWorker(self._chat_engine, text)
        self._worker.finished.connect(self._on_response)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_response(self, message):
        """Procesa la respuesta del motor de chat."""
        self._status_label.hide()
        self._btn_send.setEnabled(True)
        self._add_message(
            "assistant", message.content, message.citations
        )
        self._worker = None

    def _on_error(self, error_text: str):
        """Procesa un error del motor de chat."""
        self._status_label.hide()
        self._btn_send.setEnabled(True)
        self._add_message("assistant", f"❌ Error: {error_text}")
        self._worker = None

    def _add_message(self, role: str, content: str, citations=None):
        """Agrega un mensaje al historial visual.

        Args:
            role: 'user' o 'assistant'.
            content: Contenido del mensaje.
            citations: Lista de citas.
        """
        widget = MessageWidget(role, content, citations)
        widget.citation_clicked.connect(self.navigateToPage.emit)
        self._chat_layout.addWidget(widget)

        QApplication.processEvents()
        scrollbar = self._scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_clear(self):
        """Limpia el historial de chat."""
        while self._chat_layout.count():
            item = self._chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self._chat_engine:
            self._chat_engine.clear_history()

    @property
    def message_count(self) -> int:
        """Número de mensajes en el historial visual."""
        return self._chat_layout.count()

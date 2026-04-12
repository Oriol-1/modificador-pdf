"""Tests para ui.ai_chat_panel."""

import pytest
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from ui.ai_chat_panel import AIChatPanel, MessageWidget, ChatWorker
from core.ai.chat_engine import ChatMessage, MessageRole, Citation


@pytest.fixture(scope="module")
def app():
    """Fixture de QApplication."""
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


class TestMessageWidget:
    """Tests para MessageWidget."""

    def test_user_message(self, app):
        widget = MessageWidget("user", "Hello")
        assert widget._role == "user"

    def test_assistant_message(self, app):
        widget = MessageWidget("assistant", "Response")
        assert widget._role == "assistant"

    def test_with_citations(self, app):
        citations = [Citation(page_num=2, text="Cited text")]
        widget = MessageWidget("assistant", "See citation", citations)
        assert len(widget._citations) == 1

    def test_citation_signal(self, app):
        citations = [Citation(page_num=3, text="Text")]
        widget = MessageWidget("assistant", "Content", citations)
        received = []
        widget.citation_clicked.connect(lambda p: received.append(p))
        # Find the citation button and click it
        from PyQt5.QtWidgets import QPushButton
        buttons = widget.findChildren(QPushButton)
        page_buttons = [b for b in buttons if "Página" in b.text()]
        if page_buttons:
            page_buttons[0].click()
            assert 3 in received


class TestAIChatPanel:
    """Tests para AIChatPanel."""

    def test_creation(self, app):
        panel = AIChatPanel()
        assert panel.windowTitle() == "💬 Chat IA"
        assert panel.message_count == 0

    def test_send_disabled_initially(self, app):
        panel = AIChatPanel()
        assert not panel._btn_send.isEnabled()

    def test_set_chat_engine(self, app):
        panel = AIChatPanel()
        engine = MagicMock()
        panel.set_chat_engine(engine)
        assert panel._chat_engine is engine
        assert panel._btn_send.isEnabled()

    def test_set_chat_engine_none(self, app):
        panel = AIChatPanel()
        panel.set_chat_engine(None)
        assert not panel._btn_send.isEnabled()

    def test_add_message(self, app):
        panel = AIChatPanel()
        panel._add_message("user", "Test message")
        assert panel.message_count == 1

    def test_add_multiple_messages(self, app):
        panel = AIChatPanel()
        panel._add_message("user", "Question 1")
        panel._add_message("assistant", "Answer 1")
        panel._add_message("user", "Question 2")
        assert panel.message_count == 3

    def test_clear_chat(self, app):
        panel = AIChatPanel()
        panel._add_message("user", "Test")
        panel._add_message("assistant", "Reply")
        panel._on_clear()
        assert panel.message_count == 0

    def test_clear_chat_with_engine(self, app):
        panel = AIChatPanel()
        engine = MagicMock()
        panel.set_chat_engine(engine)
        panel._add_message("user", "Test")
        panel._on_clear()
        engine.clear_history.assert_called_once()

    def test_on_response(self, app):
        panel = AIChatPanel()
        engine = MagicMock()
        panel.set_chat_engine(engine)
        msg = ChatMessage(
            role=MessageRole.ASSISTANT,
            content="AI response",
            citations=[Citation(page_num=0, text="ref")],
        )
        panel._on_response(msg)
        assert panel.message_count == 1
        assert panel._btn_send.isEnabled()

    def test_on_error(self, app):
        panel = AIChatPanel()
        engine = MagicMock()
        panel.set_chat_engine(engine)
        panel._on_error("Something went wrong")
        assert panel.message_count == 1
        assert panel._btn_send.isEnabled()

    def test_send_empty_input(self, app):
        panel = AIChatPanel()
        engine = MagicMock()
        panel.set_chat_engine(engine)
        panel._input_field.clear()
        panel._on_send()
        # Nothing should happen
        assert panel.message_count == 0

    def test_navigate_to_page_signal(self, app):
        panel = AIChatPanel()
        received = []
        panel.navigateToPage.connect(lambda p: received.append(p))
        citations = [Citation(page_num=5, text="Text")]
        panel._add_message("assistant", "Content", citations)
        # Find and click citation button
        from PyQt5.QtWidgets import QPushButton
        msgs = [
            panel._chat_layout.itemAt(i).widget()
            for i in range(panel._chat_layout.count())
        ]
        for msg_widget in msgs:
            buttons = msg_widget.findChildren(QPushButton)
            for btn in buttons:
                if "Página" in btn.text():
                    btn.click()
        if received:
            assert 5 in received


class TestChatWorker:
    """Tests para ChatWorker."""

    def test_creation(self, app):
        engine = MagicMock()
        worker = ChatWorker(engine, "Question")
        assert worker._question == "Question"

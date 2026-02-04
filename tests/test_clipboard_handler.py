"""
Tests para ClipboardHandler - PHASE2-202

Cobertura:
- StyledTextData dataclass
- ClipboardHandler class
- Funciones singleton y conveniencia
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from PyQt5.QtWidgets import QApplication

from core.font_manager import FontDescriptor


@pytest.fixture(scope="module")
def app():
    """Fixture para QApplication."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestStyledTextData:
    """Tests para StyledTextData dataclass."""
    
    def test_creation_minimal(self):
        """Test creación mínima."""
        from core.clipboard_handler import StyledTextData
        
        data = StyledTextData(text="Hello World")
        assert data.text == "Hello World"
        assert data.font_descriptor is None
        assert data.position is None
        assert isinstance(data.timestamp, datetime)
    
    def test_creation_full(self):
        """Test creación completa."""
        from core.clipboard_handler import StyledTextData
        
        font = FontDescriptor(
            name="Arial",
            size=12.0,
            color="#000000",
            flags=0,
            was_fallback=False,
            fallback_from=None,
            possible_bold=True
        )
        
        data = StyledTextData(
            text="Test",
            font_descriptor=font,
            position={"page": 0, "x": 100.0, "y": 200.0},
            metadata={"source": "test"}
        )
        
        assert data.text == "Test"
        assert data.font_descriptor.name == "Arial"
        assert data.position["page"] == 0
        assert data.metadata["source"] == "test"
    
    def test_to_dict(self):
        """Test serialización a dict."""
        from core.clipboard_handler import StyledTextData
        
        font = FontDescriptor(
            name="Times",
            size=14.0,
            color="#FF0000",
            flags=0,
            was_fallback=False,
            fallback_from=None,
            possible_bold=False
        )
        
        data = StyledTextData(
            text="Hello",
            font_descriptor=font,
            position={"page": 1, "x": 50.0, "y": 75.0}
        )
        
        d = data.to_dict()
        
        assert d["text"] == "Hello"
        assert d["font_descriptor"]["name"] == "Times"
        assert d["font_descriptor"]["size"] == 14.0
        assert d["position"]["page"] == 1
        assert "timestamp" in d
    
    def test_from_dict(self):
        """Test deserialización desde dict."""
        from core.clipboard_handler import StyledTextData
        
        d = {
            "text": "World",
            "font_descriptor": {
                "name": "Courier",
                "size": 10.0,
                "color": "#0000FF",
                "flags": 0,
                "was_fallback": True,
                "fallback_from": "Monaco",
                "possible_bold": None
            },
            "position": {"page": 2, "x": 10.0, "y": 20.0},
            "timestamp": datetime.now().isoformat(),
            "metadata": {"key": "value"}
        }
        
        data = StyledTextData.from_dict(d)
        
        assert data.text == "World"
        assert data.font_descriptor.name == "Courier"
        assert data.font_descriptor.was_fallback is True
        assert data.position["page"] == 2
        assert data.metadata["key"] == "value"
    
    def test_to_json(self):
        """Test serialización JSON."""
        from core.clipboard_handler import StyledTextData
        
        data = StyledTextData(text="JSON test")
        json_str = data.to_json()
        
        assert '"text": "JSON test"' in json_str
    
    def test_from_json(self):
        """Test deserialización JSON."""
        from core.clipboard_handler import StyledTextData
        
        json_str = '{"text": "From JSON", "timestamp": "2024-01-01T12:00:00", "metadata": {}}'
        data = StyledTextData.from_json(json_str)
        
        assert data.text == "From JSON"
    
    def test_roundtrip(self):
        """Test roundtrip dict -> json -> dict."""
        from core.clipboard_handler import StyledTextData
        
        font = FontDescriptor(
            name="Arial",
            size=16.0,
            color="#00FF00",
            flags=0,
            was_fallback=False,
            fallback_from=None,
            possible_bold=True
        )
        
        original = StyledTextData(
            text="Roundtrip test",
            font_descriptor=font,
            position={"page": 0, "x": 0, "y": 0}
        )
        
        # to_json -> from_json
        json_str = original.to_json()
        restored = StyledTextData.from_json(json_str)
        
        assert restored.text == original.text
        assert restored.font_descriptor.name == original.font_descriptor.name
        assert restored.font_descriptor.size == original.font_descriptor.size


class TestClipboardHandler:
    """Tests para ClipboardHandler."""
    
    @pytest.fixture
    def handler(self, app):
        """Fixture para handler limpio."""
        from core.clipboard_handler import ClipboardHandler, reset_clipboard_handler
        reset_clipboard_handler()
        return ClipboardHandler()
    
    def test_creation(self, handler):
        """Test creación."""
        assert handler is not None
        assert handler.max_history == 10
        assert len(handler.history) == 0
    
    def test_copy_plain(self, handler):
        """Test copiar texto plano."""
        result = handler.copy_plain("Simple text")
        assert result is True
        assert len(handler.history) == 1
    
    def test_copy_styled(self, handler):
        """Test copiar con estilos."""
        font = FontDescriptor(
            name="Arial",
            size=12.0,
            color="#000000",
            flags=0,
            was_fallback=False,
            fallback_from=None,
            possible_bold=False
        )
        
        result = handler.copy_styled(
            text="Styled text",
            font_descriptor=font,
            position={"page": 0, "x": 100, "y": 200}
        )
        
        assert result is True
        assert len(handler.history) == 1
        assert handler.history[0].text == "Styled text"
        assert handler.history[0].font_descriptor.name == "Arial"
    
    def test_paste_plain(self, handler):
        """Test pegar texto plano."""
        handler.copy_plain("Paste test")
        
        result = handler.paste_plain()
        assert result == "Paste test"
    
    def test_paste_styled(self, handler):
        """Test pegar con estilos."""
        font = FontDescriptor(
            name="Times",
            size=14.0,
            color="#FF0000",
            flags=0,
            was_fallback=False,
            fallback_from=None,
            possible_bold=True
        )
        
        handler.copy_styled("Styled paste", font_descriptor=font)
        
        result = handler.paste_styled()
        assert result is not None
        assert result.text == "Styled paste"
        assert result.font_descriptor.name == "Times"
        assert result.font_descriptor.possible_bold is True
    
    def test_has_styled_content(self, handler):
        """Test verificar contenido con estilos."""
        font = FontDescriptor(
            name="Arial",
            size=12.0,
            color="#000000",
            flags=0,
            was_fallback=False,
            fallback_from=None,
            possible_bold=False
        )
        
        handler.copy_styled("Has style", font_descriptor=font)
        
        assert handler.has_styled_content() is True
    
    def test_has_any_content(self, handler):
        """Test verificar cualquier contenido."""
        handler.copy_plain("Any content")
        assert handler.has_any_content() is True
    
    def test_get_preview(self, handler):
        """Test obtener preview."""
        handler.copy_plain("This is a longer text for preview testing")
        
        preview = handler.get_preview(max_length=20)
        assert len(preview) <= 23  # 20 + "..."
        assert preview.endswith("...")
    
    def test_history_limit(self, handler):
        """Test límite de historial."""
        handler.max_history = 3
        
        for i in range(5):
            handler.copy_plain(f"Text {i}")
        
        assert len(handler.history) == 3
        assert handler.history[0].text == "Text 4"  # Más reciente
        assert handler.history[2].text == "Text 2"  # Más antiguo
    
    def test_get_history(self, handler):
        """Test obtener historial."""
        handler.copy_plain("First")
        handler.copy_plain("Second")
        
        history = handler.get_history()
        assert len(history) == 2
        assert history[0].text == "Second"  # Más reciente primero
    
    def test_clear_history(self, handler):
        """Test limpiar historial."""
        handler.copy_plain("Test")
        handler.copy_plain("Test 2")
        
        handler.clear_history()
        assert len(handler.history) == 0
    
    def test_paste_from_history(self, handler):
        """Test pegar desde historial."""
        handler.copy_plain("Old")
        handler.copy_plain("New")
        
        old = handler.paste_from_history(1)
        assert old.text == "Old"
        
        new = handler.paste_from_history(0)
        assert new.text == "New"
        
        invalid = handler.paste_from_history(99)
        assert invalid is None


class TestSingleton:
    """Tests para singleton y funciones de conveniencia."""
    
    def setup_method(self):
        """Reset antes de cada test."""
        from core.clipboard_handler import reset_clipboard_handler
        reset_clipboard_handler()
    
    def test_get_clipboard_handler(self, app):
        """Test obtener singleton."""
        from core.clipboard_handler import get_clipboard_handler
        
        handler1 = get_clipboard_handler()
        handler2 = get_clipboard_handler()
        
        assert handler1 is handler2
    
    def test_reset_clipboard_handler(self, app):
        """Test resetear singleton."""
        from core.clipboard_handler import get_clipboard_handler, reset_clipboard_handler
        
        handler1 = get_clipboard_handler()
        reset_clipboard_handler()
        handler2 = get_clipboard_handler()
        
        assert handler1 is not handler2
    
    def test_copy_text_function(self, app):
        """Test función copy_text."""
        from core.clipboard_handler import copy_text, get_clipboard_handler
        
        result = copy_text("Convenience copy")
        assert result is True
        
        handler = get_clipboard_handler()
        assert len(handler.history) == 1
    
    def test_paste_text_function(self, app):
        """Test función paste_text."""
        from core.clipboard_handler import copy_text, paste_text
        
        copy_text("Convenience paste")
        result = paste_text()
        
        assert result is not None
        assert result.text == "Convenience paste"
    
    def test_has_clipboard_content_function(self, app):
        """Test función has_clipboard_content."""
        from core.clipboard_handler import copy_text, has_clipboard_content
        
        copy_text("Check content")
        assert has_clipboard_content() is True


class TestIntegration:
    """Tests de integración."""
    
    def test_full_workflow(self, app):
        """Test flujo completo."""
        from core.clipboard_handler import (
            get_clipboard_handler, reset_clipboard_handler
        )
        
        reset_clipboard_handler()
        handler = get_clipboard_handler()
        
        # Copiar con estilos
        font = FontDescriptor(
            name="Georgia",
            size=18.0,
            color="#333333",
            flags=0,
            was_fallback=False,
            fallback_from=None,
            possible_bold=True
        )
        
        handler.copy_styled(
            text="Integration test text",
            font_descriptor=font,
            position={"page": 0, "x": 50, "y": 100},
            metadata={"test": True}
        )
        
        # Verificar contenido
        assert handler.has_styled_content() is True
        
        # Pegar
        pasted = handler.paste_styled()
        assert pasted.text == "Integration test text"
        assert pasted.font_descriptor.name == "Georgia"
        assert pasted.font_descriptor.size == 18.0
        assert pasted.font_descriptor.possible_bold is True
        assert pasted.position["page"] == 0
        assert pasted.metadata["test"] is True
        
        # Historial
        assert len(handler.history) == 1
        
        # Preview
        preview = handler.get_preview(15)
        assert "Integration" in preview
    
    def test_copy_without_font(self, app):
        """Test copiar sin fuente preserva texto."""
        from core.clipboard_handler import get_clipboard_handler, reset_clipboard_handler
        
        reset_clipboard_handler()
        handler = get_clipboard_handler()
        
        handler.copy_styled("Plain text only")
        
        pasted = handler.paste_styled()
        assert pasted.text == "Plain text only"
        assert pasted.font_descriptor is None

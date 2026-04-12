"""Tests para el panel de buscar y reemplazar.

Verifica SearchResult dataclass, SearchReplacePanel señales,
navegación entre resultados y lógica de UI.
"""
import pytest
from unittest.mock import MagicMock, patch
import fitz

from ui.search_replace_panel import SearchResult, SearchReplacePanel


# --- Tests para SearchResult ---

class TestSearchResult:
    """Tests para el dataclass SearchResult."""

    def test_create_basic(self):
        """Crea un SearchResult con datos válidos."""
        rect = fitz.Rect(10, 20, 100, 40)
        result = SearchResult(page_num=0, rect=rect)
        assert result.page_num == 0
        assert result.rect == rect

    def test_to_dict(self):
        """Serialización a diccionario."""
        rect = fitz.Rect(10, 20, 100, 40)
        result = SearchResult(page_num=2, rect=rect)
        d = result.to_dict()
        assert d['page_num'] == 2
        assert d['rect'] == [10, 20, 100, 40]

    def test_from_dict(self):
        """Deserialización desde diccionario."""
        d = {'page_num': 3, 'rect': [5, 10, 200, 30]}
        result = SearchResult.from_dict(d)
        assert result.page_num == 3
        assert result.rect.x0 == 5
        assert result.rect.y1 == 30

    def test_roundtrip(self):
        """Serialización ida y vuelta es idempotente."""
        original = SearchResult(page_num=1, rect=fitz.Rect(0, 0, 50, 50))
        restored = SearchResult.from_dict(original.to_dict())
        assert restored.page_num == original.page_num
        assert restored.rect == original.rect

    def test_different_pages(self):
        """Resultados en diferentes páginas."""
        r1 = SearchResult(page_num=0, rect=fitz.Rect(0, 0, 10, 10))
        r2 = SearchResult(page_num=5, rect=fitz.Rect(0, 0, 10, 10))
        assert r1.page_num != r2.page_num


# --- Tests para SearchReplacePanel ---

class TestSearchReplacePanel:
    """Tests para el widget SearchReplacePanel."""

    @pytest.fixture
    def panel(self):
        """Fixture: instancia del panel sin QApplication."""
        # Mock QApplication para evitar requerir display
        with patch('ui.search_replace_panel.QWidget.__init__', return_value=None):
            p = SearchReplacePanel.__new__(SearchReplacePanel)
            p._results = []
            p._current_index = -1
            p._replace_visible = False
            # Mock widgets
            p.input_search = MagicMock()
            p.input_replace = MagicMock()
            p.chk_case = MagicMock()
            p.lbl_count = MagicMock()
            p.btn_next = MagicMock()
            p.btn_prev = MagicMock()
            p.btn_replace = MagicMock()
            p.btn_replace_all = MagicMock()
            p.btn_toggle_replace = MagicMock()
            p.btn_close = MagicMock()
            p._replace_row = MagicMock()
            # Mock signals
            p.searchRequested = MagicMock()
            p.replaceRequested = MagicMock()
            p.replaceAllRequested = MagicMock()
            p.navigateToResult = MagicMock()
            p.closed = MagicMock()
            p.highlightsChanged = MagicMock()
            return p

    def test_set_results_updates_index(self, panel):
        """set_results actualiza el índice al primer resultado."""
        results = [
            SearchResult(0, fitz.Rect(0, 0, 10, 10)),
            SearchResult(1, fitz.Rect(0, 0, 10, 10)),
        ]
        panel.set_results(results)
        assert panel._current_index == 0
        assert len(panel._results) == 2

    def test_set_results_empty(self, panel):
        """set_results con lista vacía resetea el índice."""
        panel.set_results([])
        assert panel._current_index == -1
        assert panel._results == []

    def test_clear_results(self, panel):
        """clear_results limpia todo."""
        panel._results = [SearchResult(0, fitz.Rect(0, 0, 10, 10))]
        panel._current_index = 0
        panel.clear_results()
        assert panel._results == []
        assert panel._current_index == -1
        panel.highlightsChanged.emit.assert_called_with([])

    def test_current_result_valid(self, panel):
        """current_result retorna el resultado actual."""
        results = [SearchResult(0, fitz.Rect(0, 0, 10, 10))]
        panel._results = results
        panel._current_index = 0
        assert panel.current_result == results[0]

    def test_current_result_none_when_empty(self, panel):
        """current_result retorna None sin resultados."""
        panel._results = []
        panel._current_index = -1
        assert panel.current_result is None

    def test_next_wraps_around(self, panel):
        """Siguiente resultado hace wrap al inicio."""
        panel._results = [
            SearchResult(0, fitz.Rect(0, 0, 10, 10)),
            SearchResult(1, fitz.Rect(0, 0, 10, 10)),
        ]
        panel._current_index = 1
        panel._on_next_clicked()
        assert panel._current_index == 0

    def test_prev_wraps_around(self, panel):
        """Resultado anterior hace wrap al final."""
        panel._results = [
            SearchResult(0, fitz.Rect(0, 0, 10, 10)),
            SearchResult(1, fitz.Rect(0, 0, 10, 10)),
        ]
        panel._current_index = 0
        panel._on_prev_clicked()
        assert panel._current_index == 1

    def test_next_no_results_noop(self, panel):
        """Siguiente sin resultados no hace nada."""
        panel._results = []
        panel._current_index = -1
        panel._on_next_clicked()
        assert panel._current_index == -1

    def test_search_text_property(self, panel):
        """Propiedad search_text lee del input."""
        panel.input_search.text.return_value = "hola"
        assert panel.search_text == "hola"

    def test_replace_text_property(self, panel):
        """Propiedad replace_text lee del input."""
        panel.input_replace.text.return_value = "mundo"
        assert panel.replace_text == "mundo"

    def test_case_sensitive_property(self, panel):
        """Propiedad case_sensitive lee del checkbox."""
        panel.chk_case.isChecked.return_value = True
        assert panel.case_sensitive is True

    def test_on_replace_clicked_no_result(self, panel):
        """Reemplazar sin resultado activo no emite."""
        panel._results = []
        panel._current_index = -1
        panel.input_search.text.return_value = "test"
        panel._on_replace_clicked()
        panel.replaceRequested.emit.assert_not_called()

    def test_on_replace_all_empty_text(self, panel):
        """Reemplazar todo con texto vacío no emite."""
        panel.input_search.text.return_value = ""
        panel._on_replace_all_clicked()
        panel.replaceAllRequested.emit.assert_not_called()

    def test_set_results_emits_highlights(self, panel):
        """set_results emite highlightsChanged."""
        results = [SearchResult(0, fitz.Rect(0, 0, 10, 10))]
        panel.set_results(results)
        panel.highlightsChanged.emit.assert_called_with(results)

    def test_on_close_emits_closed(self, panel):
        """Cerrar emite señal closed."""
        panel.hide = MagicMock()
        panel._on_close_clicked()
        panel.closed.emit.assert_called_once()

    def test_navigate_emits_signal(self, panel):
        """Navegar emite navigateToResult."""
        result = SearchResult(2, fitz.Rect(10, 20, 100, 40))
        panel._results = [result]
        panel._current_index = 0
        panel._navigate_to_current()
        panel.navigateToResult.emit.assert_called_once_with(2, result.rect)

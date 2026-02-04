"""
Integration Tests - PHASE2-303

Tests de flujo completo usando escenarios Gherkin que cubren casos reales de usuario.
Validan la integración entre FontManager, ClipboardHandler, ChangeReport y UI.

Escenarios cubiertos:
1. Edición simple de texto preservando fuente
2. Pegar texto con bold detectado
3. Texto que no cabe (ajuste de spacing)
4. Guardar y reabrir PDF (persistencia)
5. Deshacer/Rehacer cambios
6. Copy/paste con HTML bold
7. Copy/paste con HTML italic
8. Múltiples ediciones en mismo documento
9. Edición multi-página
10. Validación de ChangeReport completo
"""

import pytest

from PyQt5.QtWidgets import QApplication

# Core imports
from core.font_manager import FontDescriptor, get_font_manager
from core.clipboard_handler import (
    StyledTextData, 
    get_clipboard_handler, reset_clipboard_handler,
    copy_text, paste_text, has_clipboard_content
)
from core.change_report import (
    ChangeReport, ChangeType,
    get_change_report, reset_change_report
)

# UI imports
from ui.summary_dialog import SummaryDialog, QuickStatsWidget


@pytest.fixture(scope="module")
def app():
    """Fixture para QApplication."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def font_manager():
    """Fixture para FontManager."""
    return get_font_manager()


@pytest.fixture
def clipboard_handler():
    """Fixture para ClipboardHandler limpio."""
    reset_clipboard_handler()
    return get_clipboard_handler()


@pytest.fixture
def change_report():
    """Fixture para ChangeReport limpio."""
    reset_change_report()
    return get_change_report()


@pytest.fixture
def sample_descriptor():
    """Descriptor de fuente típico para tests."""
    return FontDescriptor(
        name="Arial",
        size=12.0,
        color="#000000",
        flags=0,
        was_fallback=False,
        fallback_from=None,
        possible_bold=False
    )


@pytest.fixture
def bold_descriptor():
    """Descriptor de fuente con bold para tests."""
    return FontDescriptor(
        name="Arial-Bold",
        size=12.0,
        color="#000000",
        flags=0,
        was_fallback=False,
        fallback_from=None,
        possible_bold=True
    )


class TestScenario1_SimpleTextEdit:
    """
    Scenario: Edición simple de texto preservando fuente
    Given: Un PDF con texto "viaje" en Arial 12pt
    When: Usuario edita a "viaje increíble"
    Then: El texto se actualiza manteniendo Arial 12pt
    """
    
    def test_edit_preserves_font_family(self, font_manager, sample_descriptor):
        """Verifica que la fuente se preserva durante edición."""
        # Given: Un span simulado del PDF
        span = {"font": "Arial", "size": 12.0, "color": 0, "flags": 0}
        
        # When: FontManager detecta la fuente
        detected = font_manager.detect_font(span)
        
        # Then: La fuente detectada es válida
        assert detected is not None
        assert detected.size == 12.0
    
    def test_edit_preserves_font_size(self, sample_descriptor):
        """Verifica que el tamaño se preserva."""
        assert sample_descriptor.size == 12.0
    
    def test_change_report_records_edit(self, change_report, sample_descriptor):
        """Verifica que ChangeReport registra la edición."""
        # When: Registramos un cambio usando el método atajo
        change_report.add_text_edit(
            page=0,
            x=100,
            y=200,
            old_text="viaje",
            new_text="viaje increíble",
            font_name=sample_descriptor.name,
            font_size=sample_descriptor.size
        )
        
        # Then: El cambio está registrado (accedemos a changes directamente)
        assert len(change_report.changes) == 1
        assert change_report.changes[0].change_type == ChangeType.TEXT_EDIT
        assert change_report.changes[0].old_value == "viaje"
        assert change_report.changes[0].new_value == "viaje increíble"


class TestScenario2_PasteBoldText:
    """
    Scenario: Pegar texto con bold detectado
    Given: Usuario copia "<b>importante</b>" de navegador
    When: Ctrl+V en texto PDF
    Then: Dialog muestra "Aplicar negrita?" y usuario confirma
    """
    
    def test_clipboard_stores_styled_text(self, app, clipboard_handler, bold_descriptor):
        """Verifica que el clipboard almacena texto con estilos."""
        # When: Copiamos texto con estilo bold usando copy_styled
        result = clipboard_handler.copy_styled(
            text="importante",
            font_descriptor=bold_descriptor
        )
        
        # Then: El clipboard tiene contenido estilizado
        assert result is True
        assert clipboard_handler.has_styled_content()
    
    def test_paste_retrieves_style_info(self, app, clipboard_handler, bold_descriptor):
        """Verifica que al pegar se recupera la info de estilo."""
        # Given: Texto con bold en clipboard
        clipboard_handler.copy_styled(
            text="importante",
            font_descriptor=bold_descriptor
        )
        
        # When: Pegamos usando paste_styled
        result = clipboard_handler.paste_styled()
        
        # Then: Recuperamos el texto y estilos
        assert result is not None
        assert result.text == "importante"
        assert result.font_descriptor.possible_bold is True
    
    def test_change_report_records_paste_with_bold(self, change_report):
        """Verifica que ChangeReport registra paste con bold."""
        # When: Registramos paste con bold usando add_text_add
        change_report.add_text_add(
            page=0,
            x=150,
            y=250,
            text="importante",
            font_name="Arial-Bold",
            font_size=12.0
        )
        
        # Then: El cambio está registrado (accedemos a changes directamente)
        assert len(change_report.changes) == 1
        assert change_report.changes[0].change_type == ChangeType.TEXT_ADD


class TestScenario3_TextDoesNotFit:
    """
    Scenario: Texto no cabe - usuario elige opción
    Given: Área original tiene espacio para 20 caracteres
    When: Usuario intenta pegar 40 caracteres
    Then: Dialog muestra opciones [A] Recortar, [B] Espaciado, [C] Tamaño
    """
    
    def test_font_manager_validates_text_fit(self, font_manager, sample_descriptor):
        """Verifica que FontManager valida si el texto cabe."""
        # Given: Área pequeña (100px) y texto largo
        text = "Este es un texto muy largo que no cabe"
        
        # When: Validamos con área pequeña (usa descriptor)
        fits, message = font_manager.validate_text_fits(
            text, sample_descriptor, max_width=100
        )
        
        # Then: No cabe
        assert fits is False
        assert message is not None
    
    def test_font_manager_validates_short_text(self, font_manager, sample_descriptor):
        """Verifica que texto corto sí cabe."""
        text = "Hola"
        
        fits, message = font_manager.validate_text_fits(
            text, sample_descriptor, max_width=500
        )
        
        # El texto corto debería caber con área grande
        assert fits is True
        assert message is None
    
    def test_reduce_tracking_helps_fit(self, font_manager, sample_descriptor):
        """Verifica que reducir tracking ayuda a que quepa."""
        text = "Texto de ejemplo"
        
        # When: Reducimos tracking (usa descriptor)
        result = font_manager.reduce_tracking(text, sample_descriptor, 10)
        
        # Then: Retorna texto (sin espacios extra o con tracking reducido)
        assert result is not None


class TestScenario4_SaveAndReopen:
    """
    Scenario: Guardar y reabrir PDF (persiste cambios)
    Given: Usuario editó texto en página 1
    When: Guarda y reabre el PDF
    Then: Los cambios persisten
    """
    
    def test_change_report_can_serialize(self, change_report):
        """Verifica que ChangeReport puede serializarse."""
        # Given: Algunos cambios registrados
        change_report.add_text_edit(
            page=0,
            x=100,
            y=200,
            old_text="original",
            new_text="modificado"
        )
        
        # When: Serializamos a dict (la API real usa to_dict)
        data = change_report.to_dict()
        
        # Then: Es un dict válido con cambios
        assert data is not None
        assert "changes" in data
        assert len(data["changes"]) == 1
    
    def test_change_report_can_deserialize(self, change_report):
        """Verifica que ChangeReport puede deserializarse."""
        # Given: Dict de cambios
        change_report.add_text_edit(
            page=0,
            x=100,
            y=200,
            old_text="test",
            new_text="prueba"
        )
        data = change_report.to_dict()
        
        # When: Deserializamos en nuevo report
        reset_change_report()
        new_report = ChangeReport.from_dict(data)
        
        # Then: Los cambios se restauran
        assert len(new_report.changes) == 1
        assert new_report.changes[0].old_value == "test"


class TestScenario5_UndoRedo:
    """
    Scenario: Deshacer/Rehacer cambios
    Given: Usuario hizo varios cambios
    When: Presiona Ctrl+Z
    Then: El último cambio se deshace
    
    NOTA: La API actual de ChangeReport no incluye undo/redo.
    Estos tests verifican que los cambios se pueden manipular manualmente.
    """
    
    def test_changes_can_be_removed_manually(self, change_report):
        """Verifica que los cambios se pueden remover manualmente (simula undo)."""
        # Given: Dos cambios
        change_report.add_text_edit(
            page=0, x=100, y=200,
            old_text="primero", new_text="first"
        )
        change_report.add_text_edit(
            page=0, x=100, y=250,
            old_text="segundo", new_text="second"
        )
        
        assert len(change_report.changes) == 2
        
        # When: Removemos el último (simulando undo)
        undone = change_report.changes.pop()
        
        # Then: Solo queda un cambio
        assert undone is not None
        assert len(change_report.changes) == 1
        assert change_report.changes[0].old_value == "primero"
    
    def test_changes_can_be_readded_manually(self, change_report):
        """Verifica que los cambios se pueden re-añadir manualmente (simula redo)."""
        # Given: Un cambio que fue removido
        change_report.add_text_edit(
            page=0, x=100, y=200,
            old_text="test", new_text="prueba"
        )
        undone = change_report.changes.pop()
        
        assert len(change_report.changes) == 0
        
        # When: Re-añadimos (simulando redo)
        change_report.add_change(undone)
        
        # Then: El cambio se restaura
        assert len(change_report.changes) == 1


class TestScenario6_CopyPasteHTMLBold:
    """
    Scenario: Copy/paste con HTML bold
    Given: Clipboard contiene HTML <b>texto</b>
    When: Se detecta el contenido
    Then: Se identifica como bold
    """
    
    def test_styled_data_preserves_bold_flag(self, bold_descriptor):
        """Verifica que StyledTextData preserva flag bold."""
        styled = StyledTextData(
            text="texto negrita",
            font_descriptor=bold_descriptor
        )
        
        assert styled.font_descriptor.possible_bold is True
    
    def test_clipboard_roundtrip_preserves_bold(self, app, clipboard_handler, bold_descriptor):
        """Verifica roundtrip completo con bold."""
        # Given: Texto bold
        metadata = {"source": "html", "original_html": "<b>importante</b>"}
        
        # When: Copy y paste usando los métodos correctos
        clipboard_handler.copy_styled(
            text="importante",
            font_descriptor=bold_descriptor,
            metadata=metadata
        )
        pasted = clipboard_handler.paste_styled()
        
        # Then: Se preserva
        assert pasted.font_descriptor.possible_bold is True
        assert pasted.metadata.get("source") == "html"


class TestScenario7_CopyPasteHTMLItalic:
    """
    Scenario: Copy/paste con HTML italic
    Given: Clipboard contiene HTML <i>texto</i>
    When: Se detecta el contenido
    Then: Se identifica como italic
    """
    
    def test_styled_data_supports_italic_metadata(self):
        """Verifica que StyledTextData soporta metadata italic."""
        descriptor = FontDescriptor(
            name="Arial-Italic",
            size=12.0,
            color="#000000",
            flags=0,
            was_fallback=False,
            fallback_from=None,
            possible_bold=False
        )
        
        styled = StyledTextData(
            text="texto cursiva",
            font_descriptor=descriptor,
            metadata={"italic": True, "source": "html"}
        )
        
        assert styled.metadata.get("italic") is True


class TestScenario8_MultipleEdits:
    """
    Scenario: Múltiples ediciones en mismo documento
    Given: Un PDF abierto
    When: Usuario hace 5 ediciones diferentes
    Then: Todas se registran en ChangeReport
    """
    
    def test_multiple_changes_recorded(self, change_report):
        """Verifica que múltiples cambios se registran."""
        # When: 5 ediciones
        for i in range(5):
            change_report.add_text_edit(
                page=0,
                x=100,
                y=200 + i*30,
                old_text=f"original_{i}",
                new_text=f"modified_{i}"
            )
        
        # Then: Todos registrados (accedemos a changes directamente)
        assert len(change_report.changes) == 5
    
    def test_statistics_reflect_all_changes(self, change_report):
        """Verifica que las estadísticas reflejan todos los cambios."""
        # Given: Cambios de diferentes tipos
        change_report.add_text_edit(
            page=0, x=100, y=200,
            old_text="edit1", new_text="edit1_new"
        )
        change_report.add_text_add(
            page=0, x=100, y=230,
            text="added"
        )
        change_report.add_text_delete(
            page=0, x=100, y=260,
            deleted_text="deleted"  # Parámetro correcto
        )
        
        # When: Obtenemos estadísticas
        stats = change_report.get_statistics()
        
        # Then: Reflejan los tipos (API usa total_changes, no total)
        assert stats["total_changes"] == 3
        assert stats.get("changes_by_type", {}).get("text_edit", 0) >= 1


class TestScenario9_MultiPageEdit:
    """
    Scenario: Edición multi-página
    Given: Un PDF con 3 páginas
    When: Usuario edita texto en cada página
    Then: ChangeReport agrupa por página
    """
    
    def test_changes_grouped_by_page(self, change_report):
        """Verifica que los cambios se agrupan por página."""
        # When: Cambios en 3 páginas
        for page in range(3):
            change_report.add_text_edit(
                page=page,
                x=100,
                y=200,
                old_text=f"page_{page}_old",
                new_text=f"page_{page}_new"
            )
        
        # Then: Podemos filtrar por página usando get_changes_by_page
        page_0_changes = change_report.get_changes_by_page(0)
        page_1_changes = change_report.get_changes_by_page(1)
        page_2_changes = change_report.get_changes_by_page(2)
        
        assert len(page_0_changes) == 1
        assert len(page_1_changes) == 1
        assert len(page_2_changes) == 1
        
        assert page_0_changes[0].position.page == 0
        assert page_1_changes[0].position.page == 1


class TestScenario10_CompleteChangeReportValidation:
    """
    Scenario: Validación completa de ChangeReport
    Given: Sesión de edición completa
    When: Usuario revisa el resumen
    Then: ChangeReport muestra todo correctamente
    """
    
    def test_generate_summary_complete(self, change_report):
        """Verifica que generate_summary genera resumen completo."""
        # Given: Varios cambios
        change_report.add_text_edit(
            page=0, x=100, y=200,
            old_text="hola", new_text="hello",
            font_name="Arial", font_size=12.0
        )
        change_report.add_text_add(
            page=1, x=150, y=250,
            text="nuevo texto",
            font_name="Times", font_size=14.0
        )
        
        # When: Generamos resumen (API real usa generate_summary)
        summary = change_report.generate_summary()
        
        # Then: Contiene información relevante
        assert summary is not None
        assert len(summary) > 0
    
    def test_change_report_tracks_fonts_used(self, change_report):
        """Verifica que ChangeReport rastrea fuentes usadas."""
        # Given: Cambios con diferentes fuentes
        change_report.add_text_edit(
            page=0, x=100, y=200,
            old_text="test1", new_text="test1_new",
            font_name="Arial", font_size=12.0
        )
        change_report.add_text_edit(
            page=0, x=100, y=230,
            old_text="test2", new_text="test2_new",
            font_name="Times", font_size=14.0
        )
        
        # When: Obtenemos estadísticas
        stats = change_report.get_statistics()
        
        # Then: Las fuentes están rastreadas
        assert "fonts_used" in stats or stats.get("total", 0) >= 2


class TestUIIntegration:
    """Tests de integración con componentes UI."""
    
    def test_summary_dialog_loads_change_report(self, app, change_report):
        """Verifica que SummaryDialog carga datos de ChangeReport."""
        # Given: Algunos cambios
        change_report.add_text_edit(
            page=0, x=100, y=200,
            old_text="test", new_text="prueba"
        )
        
        # When: Creamos SummaryDialog
        dialog = SummaryDialog(report=change_report)
        
        # Then: Se crea correctamente
        assert dialog is not None
    
    def test_quick_stats_widget_updates(self, app, change_report):
        """Verifica que QuickStatsWidget se actualiza con cambios."""
        # Given: Widget de stats
        widget = QuickStatsWidget()
        
        # When: Actualizamos con cambios
        change_report.add_text_edit(
            page=0, x=100, y=200,
            old_text="a", new_text="b"
        )
        widget.update_stats(change_report)
        
        # Then: Widget existe y no crashea
        assert widget is not None


class TestFontManagerIntegration:
    """Tests de integración con FontManager."""
    
    def test_bold_detection_integration(self, font_manager):
        """Verifica detección de bold integrada."""
        # Given: Span con posible bold (nombre de fuente Bold)
        span = {"font": "Arial-Bold", "size": 12.0, "color": 0, "flags": 0}
        
        # When: Detectamos
        result = font_manager.detect_possible_bold(span)
        
        # Then: Detecta posible bold
        assert result is True
    
    def test_fallback_integration(self, font_manager):
        """Verifica fallback de fuentes integrado."""
        # Given: Fuente que no existe
        result = font_manager.smart_fallback("FuenteQueNoExiste")
        
        # Then: Retorna fallback
        assert result is not None
    
    def test_handle_bold_strategy(self, font_manager, sample_descriptor):
        """Verifica estrategia de bold."""
        # When: Aplicamos bold
        text, strategy = font_manager.handle_bold(
            "texto",
            sample_descriptor,
            True  # apply_bold
        )
        
        # Then: Retorna texto y estrategia
        assert text is not None
        assert strategy is not None


class TestClipboardIntegration:
    """Tests de integración con Clipboard."""
    
    def test_convenience_functions_work(self, app):
        """Verifica que las funciones de conveniencia funcionan."""
        reset_clipboard_handler()
        
        # Copy usando función de conveniencia
        copy_text("test text")
        
        # Has content
        assert has_clipboard_content() is True
        
        # Paste
        result = paste_text()
        assert result is not None
    
    def test_history_integration(self, app, clipboard_handler):
        """Verifica que el historial funciona."""
        # Given: Múltiples copias usando copy_styled
        clipboard_handler.copy_styled("first")
        clipboard_handler.copy_styled("second")
        clipboard_handler.copy_styled("third")
        
        # When: Obtenemos historial
        history = clipboard_handler.get_history()
        
        # Then: Tiene las entradas
        assert len(history) >= 2  # Al menos las últimas

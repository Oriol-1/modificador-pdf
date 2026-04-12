"""
Tests para SummaryDialog - PHASE2-203

Cobertura:
- StatWidget
- FontUsageTable
- ChangesByPageTable
- SummaryDialog
- QuickStatsWidget
"""

import pytest
from PyQt5.QtWidgets import QApplication

from core.change_report import (
    ChangeReport, reset_change_report
)


@pytest.fixture(scope="module")
def app():
    """Fixture para QApplication."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def sample_report():
    """Fixture con reporte de ejemplo."""
    reset_change_report()
    report = ChangeReport("/test/document.pdf")
    
    # Añadir cambios de prueba
    report.add_text_edit(
        page=0, x=100, y=200,
        old_text="Hello",
        new_text="World",
        font_name="Arial",
        font_size=12.0
    )
    
    report.add_text_add(
        page=0, x=150, y=250,
        text="New text",
        font_name="Times",
        font_size=14.0
    )
    
    report.add_text_delete(
        page=1, x=50, y=100,
        deleted_text="Removed"
    )
    
    report.add_text_edit(
        page=1, x=200, y=300,
        old_text="Old",
        new_text="New",
        font_name="Arial",
        font_size=12.0
    )
    
    return report


class TestStatWidget:
    """Tests para StatWidget."""
    
    def test_creation(self, app):
        """Test creación."""
        from ui.summary_dialog import StatWidget
        
        widget = StatWidget(
            title="Test Stat",
            value="42",
            icon="📊",
            color="#FF0000"
        )
        
        assert widget is not None
        assert widget.value_label.text() == "42"
    
    def test_set_value(self, app):
        """Test actualizar valor."""
        from ui.summary_dialog import StatWidget
        
        widget = StatWidget("Test", "0")
        widget.set_value("100")
        
        assert widget.value_label.text() == "100"


class TestFontUsageTable:
    """Tests para FontUsageTable."""
    
    def test_creation(self, app):
        """Test creación."""
        from ui.summary_dialog import FontUsageTable
        
        table = FontUsageTable()
        assert table.columnCount() == 3
    
    def test_set_data(self, app):
        """Test establecer datos."""
        from ui.summary_dialog import FontUsageTable
        
        table = FontUsageTable()
        table.set_data({
            "Arial": 5,
            "Times": 3,
            "Courier": 2
        })
        
        assert table.rowCount() == 3
        # Arial debe estar primero (más usos)
        assert table.item(0, 0).text() == "Arial"
    
    def test_empty_data(self, app):
        """Test con datos vacíos."""
        from ui.summary_dialog import FontUsageTable
        
        table = FontUsageTable()
        table.set_data({})
        
        assert table.rowCount() == 0


class TestChangesByPageTable:
    """Tests para ChangesByPageTable."""
    
    def test_creation(self, app):
        """Test creación."""
        from ui.summary_dialog import ChangesByPageTable
        
        table = ChangesByPageTable()
        assert table.columnCount() == 4
    
    def test_set_data(self, app):
        """Test establecer datos."""
        from ui.summary_dialog import ChangesByPageTable
        
        table = ChangesByPageTable()
        table.set_data({
            0: {"edits": 2, "adds": 1, "deletes": 0},
            1: {"edits": 1, "adds": 0, "deletes": 1}
        })
        
        assert table.rowCount() == 2
        # Página 1 (índice 0 + 1)
        assert table.item(0, 0).text() == "1"


class TestSummaryDialog:
    """Tests para SummaryDialog."""
    
    def test_creation(self, app, sample_report):
        """Test creación."""
        from ui.summary_dialog import SummaryDialog
        
        dialog = SummaryDialog(report=sample_report)
        
        assert dialog is not None
        assert dialog.report is sample_report
    
    def test_loads_statistics(self, app, sample_report):
        """Test que carga estadísticas."""
        from ui.summary_dialog import SummaryDialog
        
        dialog = SummaryDialog(report=sample_report)
        
        # Total = 4 cambios
        assert dialog.total_stat.value_label.text() == "4"
        
        # 2 ediciones
        assert dialog.edits_stat.value_label.text() == "2"
        
        # 1 añadido
        assert dialog.adds_stat.value_label.text() == "1"
        
        # 1 eliminado
        assert dialog.deletes_stat.value_label.text() == "1"
    
    def test_loads_pages_table(self, app, sample_report):
        """Test que carga tabla de páginas."""
        from ui.summary_dialog import SummaryDialog
        
        dialog = SummaryDialog(report=sample_report)
        
        # 2 páginas con cambios
        assert dialog.pages_table.rowCount() == 2
    
    def test_loads_fonts_table(self, app, sample_report):
        """Test que carga tabla de fuentes."""
        from ui.summary_dialog import SummaryDialog
        
        dialog = SummaryDialog(report=sample_report)
        
        # Arial y Times usadas
        assert dialog.fonts_table.rowCount() >= 1
    
    def test_loads_detail_text(self, app, sample_report):
        """Test que carga texto de detalle."""
        from ui.summary_dialog import SummaryDialog
        
        dialog = SummaryDialog(report=sample_report)
        
        detail = dialog.detail_text.toPlainText()
        assert "REPORTE DE CAMBIOS" in detail
    
    def test_with_document_path(self, app, sample_report):
        """Test con ruta de documento."""
        from ui.summary_dialog import SummaryDialog
        
        dialog = SummaryDialog(
            report=sample_report,
            document_path="/path/to/test.pdf"
        )
        
        assert dialog.document_path == "/path/to/test.pdf"


class TestQuickStatsWidget:
    """Tests para QuickStatsWidget."""
    
    def test_creation(self, app):
        """Test creación."""
        from ui.summary_dialog import QuickStatsWidget
        
        widget = QuickStatsWidget()
        assert widget is not None
        assert widget.isVisible() is False
    
    def test_update_stats_with_changes(self, app, sample_report):
        """Test actualizar con cambios."""
        from ui.summary_dialog import QuickStatsWidget
        
        widget = QuickStatsWidget()
        widget.update_stats(sample_report)
        
        assert widget.isVisible() is True
        assert "4" in widget.changes_label.text()
    
    def test_update_stats_empty(self, app):
        """Test actualizar sin cambios."""
        from ui.summary_dialog import QuickStatsWidget
        
        widget = QuickStatsWidget()
        empty_report = ChangeReport()
        widget.update_stats(empty_report)
        
        assert widget.isVisible() is False
    
    def test_clear(self, app, sample_report):
        """Test limpiar."""
        from ui.summary_dialog import QuickStatsWidget
        
        widget = QuickStatsWidget()
        widget.update_stats(sample_report)
        assert widget.isVisible() is True
        
        widget.clear()
        assert widget.isVisible() is False


class TestIntegration:
    """Tests de integración."""
    
    def test_full_workflow(self, app):
        """Test flujo completo."""
        from ui.summary_dialog import SummaryDialog
        
        reset_change_report()
        report = ChangeReport("/test/full_workflow.pdf")
        
        # Simular múltiples ediciones
        for i in range(5):
            report.add_text_edit(
                page=i % 3,
                x=100 + i * 10,
                y=200,
                old_text=f"Text {i}",
                new_text=f"Modified {i}",
                font_name="Arial" if i % 2 == 0 else "Times",
                font_size=12.0
            )
        
        # Crear diálogo
        dialog = SummaryDialog(report=report)
        
        # Verificar estadísticas
        assert dialog.total_stat.value_label.text() == "5"
        
        # Verificar páginas (3 páginas con cambios)
        assert dialog.pages_table.rowCount() == 3
        
        # Verificar fuentes (Arial y Times)
        assert dialog.fonts_table.rowCount() == 2
    
    def test_calculate_detailed_by_page(self, app, sample_report):
        """Test cálculo detallado por página."""
        from ui.summary_dialog import SummaryDialog
        
        dialog = SummaryDialog(report=sample_report)
        result = dialog._calculate_detailed_by_page()
        
        # Página 0: 1 edit, 1 add, 0 delete
        assert result[0]["edits"] == 1
        assert result[0]["adds"] == 1
        assert result[0]["deletes"] == 0
        
        # Página 1: 1 edit, 0 add, 1 delete
        assert result[1]["edits"] == 1
        assert result[1]["deletes"] == 1
    
    def test_calculate_font_usage(self, app, sample_report):
        """Test cálculo de uso de fuentes."""
        from ui.summary_dialog import SummaryDialog
        
        dialog = SummaryDialog(report=sample_report)
        result = dialog._calculate_font_usage()
        
        # Arial: 2 usos, Times: 1 uso
        assert result.get("Arial", 0) == 2
        assert result.get("Times", 0) == 1

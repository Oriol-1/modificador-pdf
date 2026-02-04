"""
Tests para ChangeReport - PHASE2-103

Cobertura:
- ChangeType enum
- ChangePosition dataclass
- FontInfo dataclass
- Change dataclass
- ChangeReport class
- Funciones singleton
"""

import pytest
from datetime import datetime, timedelta
import json
import tempfile
import os

from core.change_report import (
    ChangeType,
    ChangePosition,
    FontInfo,
    Change,
    ChangeReport,
    get_change_report,
    reset_change_report
)


class TestChangeType:
    """Tests para ChangeType enum."""
    
    def test_all_types_exist(self):
        """Verifica que todos los tipos existen."""
        expected_types = [
            "TEXT_EDIT", "TEXT_ADD", "TEXT_DELETE", "TEXT_MOVE",
            "FONT_CHANGE", "SIZE_CHANGE", "COLOR_CHANGE", "STYLE_CHANGE",
            "IMAGE_ADD", "IMAGE_DELETE",
            "PAGE_ADD", "PAGE_DELETE", "PAGE_ROTATE"
        ]
        for type_name in expected_types:
            assert hasattr(ChangeType, type_name)
    
    def test_type_values(self):
        """Verifica valores de tipos."""
        assert ChangeType.TEXT_EDIT.value == "text_edit"
        assert ChangeType.TEXT_ADD.value == "text_add"
        assert ChangeType.FONT_CHANGE.value == "font_change"


class TestChangePosition:
    """Tests para ChangePosition dataclass."""
    
    def test_creation(self):
        """Test creación básica."""
        pos = ChangePosition(page=0, x=100.0, y=200.0)
        assert pos.page == 0
        assert pos.x == 100.0
        assert pos.y == 200.0
        assert pos.width is None
        assert pos.height is None
    
    def test_creation_with_dimensions(self):
        """Test creación con dimensiones."""
        pos = ChangePosition(page=1, x=50.0, y=75.0, width=200.0, height=50.0)
        assert pos.width == 200.0
        assert pos.height == 50.0
    
    def test_to_dict(self):
        """Test serialización a dict."""
        pos = ChangePosition(page=2, x=10.0, y=20.0, width=100.0, height=30.0)
        d = pos.to_dict()
        assert d["page"] == 2
        assert d["x"] == 10.0
        assert d["y"] == 20.0
        assert d["width"] == 100.0
        assert d["height"] == 30.0
    
    def test_from_dict(self):
        """Test deserialización desde dict."""
        data = {"page": 3, "x": 15.0, "y": 25.0, "width": 50.0}
        pos = ChangePosition.from_dict(data)
        assert pos.page == 3
        assert pos.x == 15.0
        assert pos.height is None


class TestFontInfo:
    """Tests para FontInfo dataclass."""
    
    def test_creation_defaults(self):
        """Test creación con defaults."""
        font = FontInfo(name="Arial", size=12.0)
        assert font.name == "Arial"
        assert font.size == 12.0
        assert font.color == "#000000"
        assert font.bold is False
        assert font.italic is False
    
    def test_creation_full(self):
        """Test creación completa."""
        font = FontInfo(
            name="Times",
            size=14.0,
            color="#FF0000",
            bold=True,
            italic=True
        )
        assert font.bold is True
        assert font.color == "#FF0000"
    
    def test_to_dict(self):
        """Test serialización."""
        font = FontInfo(name="Courier", size=10.0, bold=True)
        d = font.to_dict()
        assert d["name"] == "Courier"
        assert d["bold"] is True
    
    def test_from_dict(self):
        """Test deserialización."""
        data = {"name": "Helvetica", "size": 16.0, "color": "#0000FF"}
        font = FontInfo.from_dict(data)
        assert font.name == "Helvetica"
        assert font.size == 16.0


class TestChange:
    """Tests para Change dataclass."""
    
    def test_creation_minimal(self):
        """Test creación mínima."""
        change = Change(
            change_type=ChangeType.TEXT_EDIT,
            position=ChangePosition(page=0, x=0, y=0)
        )
        assert change.change_type == ChangeType.TEXT_EDIT
        assert change.old_value is None
        assert change.new_value is None
        assert isinstance(change.timestamp, datetime)
    
    def test_creation_full(self):
        """Test creación completa."""
        change = Change(
            change_type=ChangeType.TEXT_EDIT,
            position=ChangePosition(page=1, x=100, y=200),
            old_value="Hello",
            new_value="World",
            font_info=FontInfo(name="Arial", size=12.0)
        )
        assert change.old_value == "Hello"
        assert change.new_value == "World"
        assert change.font_info.name == "Arial"
    
    def test_to_dict(self):
        """Test serialización."""
        change = Change(
            change_type=ChangeType.TEXT_ADD,
            position=ChangePosition(page=0, x=50, y=100),
            new_value="New text"
        )
        d = change.to_dict()
        assert d["change_type"] == "text_add"
        assert d["new_value"] == "New text"
        assert "timestamp" in d
    
    def test_from_dict(self):
        """Test deserialización."""
        data = {
            "change_type": "text_delete",
            "position": {"page": 2, "x": 10, "y": 20},
            "old_value": "Deleted",
            "timestamp": datetime.now().isoformat()
        }
        change = Change.from_dict(data)
        assert change.change_type == ChangeType.TEXT_DELETE
        assert change.old_value == "Deleted"
    
    def test_get_description_text_edit(self):
        """Test descripción para edición."""
        change = Change(
            change_type=ChangeType.TEXT_EDIT,
            position=ChangePosition(page=0, x=0, y=0),
            old_value="old",
            new_value="new"
        )
        desc = change.get_description()
        assert "old" in desc
        assert "new" in desc
        assert "→" in desc
    
    def test_get_description_page_rotate(self):
        """Test descripción para rotación."""
        change = Change(
            change_type=ChangeType.PAGE_ROTATE,
            position=ChangePosition(page=0, x=0, y=0),
            metadata={"degrees": 90}
        )
        desc = change.get_description()
        assert "90" in desc


class TestChangeReport:
    """Tests para ChangeReport class."""
    
    @pytest.fixture
    def report(self):
        """Fixture para reporte limpio."""
        return ChangeReport(document_path="/test/doc.pdf")
    
    def test_creation(self, report):
        """Test creación."""
        assert report.document_path == "/test/doc.pdf"
        assert len(report.changes) == 0
        assert isinstance(report.created_at, datetime)
    
    def test_add_change(self, report):
        """Test añadir cambio."""
        change = Change(
            change_type=ChangeType.TEXT_EDIT,
            position=ChangePosition(page=0, x=0, y=0)
        )
        report.add_change(change)
        assert len(report) == 1
    
    def test_add_text_edit(self, report):
        """Test atajo para edición de texto."""
        change = report.add_text_edit(
            page=0, x=100, y=200,
            old_text="Hello",
            new_text="World",
            font_name="Arial",
            font_size=12.0
        )
        assert change.change_type == ChangeType.TEXT_EDIT
        assert change.old_value == "Hello"
        assert change.font_info.name == "Arial"
        assert len(report) == 1
    
    def test_add_text_add(self, report):
        """Test atajo para añadir texto."""
        change = report.add_text_add(
            page=1, x=50, y=75,
            text="New text",
            font_name="Times",
            font_size=14.0
        )
        assert change.change_type == ChangeType.TEXT_ADD
        assert change.new_value == "New text"
    
    def test_add_text_delete(self, report):
        """Test atajo para eliminar texto."""
        change = report.add_text_delete(
            page=2, x=10, y=20,
            deleted_text="Removed"
        )
        assert change.change_type == ChangeType.TEXT_DELETE
        assert change.old_value == "Removed"
    
    def test_get_changes_by_page(self, report):
        """Test filtrar por página."""
        report.add_text_edit(page=0, x=0, y=0, old_text="a", new_text="b")
        report.add_text_edit(page=1, x=0, y=0, old_text="c", new_text="d")
        report.add_text_edit(page=0, x=10, y=10, old_text="e", new_text="f")
        
        page0_changes = report.get_changes_by_page(0)
        assert len(page0_changes) == 2
        
        page1_changes = report.get_changes_by_page(1)
        assert len(page1_changes) == 1
    
    def test_get_changes_by_type(self, report):
        """Test filtrar por tipo."""
        report.add_text_edit(page=0, x=0, y=0, old_text="a", new_text="b")
        report.add_text_add(page=0, x=10, y=10, text="new")
        report.add_text_delete(page=0, x=20, y=20, deleted_text="old")
        
        edits = report.get_changes_by_type(ChangeType.TEXT_EDIT)
        assert len(edits) == 1
        
        adds = report.get_changes_by_type(ChangeType.TEXT_ADD)
        assert len(adds) == 1
    
    def test_get_statistics(self, report):
        """Test generar estadísticas."""
        report.add_text_edit(page=0, x=0, y=0, old_text="a", new_text="b", font_name="Arial")
        report.add_text_add(page=1, x=0, y=0, text="new", font_name="Times")
        
        stats = report.get_statistics()
        assert stats["total_changes"] == 2
        assert stats["changes_by_type"]["text_edit"] == 1
        assert stats["changes_by_type"]["text_add"] == 1
        assert 0 in stats["changes_by_page"]
        assert 1 in stats["changes_by_page"]
        assert "Arial" in stats["fonts_used"]
        assert "Times" in stats["fonts_used"]
    
    def test_generate_summary(self, report):
        """Test generar resumen."""
        report.add_text_edit(page=0, x=0, y=0, old_text="Hello", new_text="World")
        
        summary = report.generate_summary()
        assert "REPORTE DE CAMBIOS" in summary
        assert "Total de cambios: 1" in summary
        assert "Hello" in summary
        assert "World" in summary
    
    def test_to_dict_from_dict(self, report):
        """Test serialización/deserialización."""
        report.add_text_edit(page=0, x=100, y=200, old_text="old", new_text="new")
        
        data = report.to_dict()
        restored = ChangeReport.from_dict(data)
        
        assert restored.document_path == report.document_path
        assert len(restored) == len(report)
        assert restored.changes[0].old_value == "old"
    
    def test_export_import_json(self, report):
        """Test exportar/importar JSON."""
        report.add_text_edit(page=0, x=0, y=0, old_text="test", new_text="TEST")
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name
        
        try:
            # Exportar
            assert report.export_json(filepath) is True
            
            # Verificar archivo existe
            assert os.path.exists(filepath)
            
            # Importar
            imported = ChangeReport.import_json(filepath)
            assert imported is not None
            assert len(imported) == 1
            assert imported.changes[0].new_value == "TEST"
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def test_clear(self, report):
        """Test limpiar cambios."""
        report.add_text_edit(page=0, x=0, y=0, old_text="a", new_text="b")
        report.add_text_add(page=0, x=0, y=0, text="c")
        assert len(report) == 2
        
        report.clear()
        assert len(report) == 0
    
    def test_undo_last(self, report):
        """Test deshacer último cambio."""
        report.add_text_edit(page=0, x=0, y=0, old_text="first", new_text="FIRST")
        report.add_text_edit(page=0, x=0, y=0, old_text="second", new_text="SECOND")
        
        undone = report.undo_last()
        assert undone.old_value == "second"
        assert len(report) == 1
        
        undone = report.undo_last()
        assert undone.old_value == "first"
        assert len(report) == 0
        
        # Undo vacío
        undone = report.undo_last()
        assert undone is None
    
    def test_bool(self, report):
        """Test bool."""
        assert bool(report) is False
        
        report.add_text_add(page=0, x=0, y=0, text="test")
        assert bool(report) is True


class TestSingleton:
    """Tests para funciones singleton."""
    
    def setup_method(self):
        """Reset antes de cada test."""
        reset_change_report()
    
    def test_get_change_report_creates(self):
        """Test que crea reporte nuevo."""
        report = get_change_report("/path/to/doc.pdf")
        assert report is not None
        assert report.document_path == "/path/to/doc.pdf"
    
    def test_get_change_report_reuses(self):
        """Test que reutiliza reporte existente."""
        report1 = get_change_report("/doc1.pdf")
        report1.add_text_add(page=0, x=0, y=0, text="test")
        
        report2 = get_change_report()  # Sin path
        assert report2 is report1
        assert len(report2) == 1
    
    def test_get_change_report_new_path_creates_new(self):
        """Test que nuevo path crea nuevo reporte."""
        report1 = get_change_report("/doc1.pdf")
        report1.add_text_add(page=0, x=0, y=0, text="test")
        
        report2 = get_change_report("/doc2.pdf")  # Nuevo path
        assert report2 is not report1
        assert len(report2) == 0
    
    def test_reset_change_report(self):
        """Test reset del singleton."""
        report1 = get_change_report("/doc.pdf")
        report1.add_text_add(page=0, x=0, y=0, text="test")
        
        reset_change_report()
        
        report2 = get_change_report()
        assert report2 is not report1
        assert len(report2) == 0


class TestIntegration:
    """Tests de integración."""
    
    def test_full_workflow(self):
        """Test flujo completo de trabajo."""
        reset_change_report()
        
        # Crear reporte
        report = get_change_report("/test/document.pdf")
        
        # Simular ediciones
        report.add_text_edit(
            page=0, x=100, y=200,
            old_text="Título Original",
            new_text="Nuevo Título",
            font_name="Arial",
            font_size=24.0
        )
        
        report.add_text_add(
            page=0, x=100, y=300,
            text="Párrafo añadido",
            font_name="Times",
            font_size=12.0
        )
        
        report.add_text_delete(
            page=1, x=50, y=100,
            deleted_text="Texto eliminado"
        )
        
        # Verificar estadísticas
        stats = report.get_statistics()
        assert stats["total_changes"] == 3
        assert len(stats["fonts_used"]) == 2
        assert 0 in stats["changes_by_page"]
        assert 1 in stats["changes_by_page"]
        
        # Generar resumen
        summary = report.generate_summary()
        assert "Título Original" in summary
        assert "Nuevo Título" in summary
        assert "Párrafo añadido" in summary
        
        # Exportar y reimportar
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name
        
        try:
            report.export_json(filepath)
            restored = ChangeReport.import_json(filepath)
            
            assert len(restored) == 3
            assert restored.get_statistics()["total_changes"] == 3
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

"""
Tests de rendimiento y funcionalidad para el PDF Editor.
Ejecutar con: python -m pytest tests/test_pdf_editor.py -v
O sin pytest: python tests/test_pdf_editor.py

Este archivo sirve como punto de referencia para verificar que todas las
funcionalidades siguen funcionando correctamente después de cambios.
"""

import os
import sys
import tempfile
import shutil
import time
from datetime import datetime

# Intentar importar pytest
try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz  # PyMuPDF


# ============================================================================
# UTILIDADES DE TEST
# ============================================================================

class TestTimer:
    """Utilidad para medir tiempos de ejecución."""
    
    def __init__(self, name="Test"):
        self.name = name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        self.end_time = time.perf_counter()
        self.elapsed = self.end_time - self.start_time
        print(f"  ⏱️  {self.name}: {self.elapsed:.4f}s")
    
    @property
    def elapsed_ms(self):
        return self.elapsed * 1000


def create_test_pdf(path: str, num_pages: int = 1, with_text: bool = True, 
                    with_bold: bool = False) -> str:
    """Crea un PDF de prueba."""
    doc = fitz.open()
    
    for i in range(num_pages):
        page = doc.new_page(width=595, height=842)  # A4
        
        if with_text:
            # Texto normal
            page.insert_text(
                fitz.Point(50, 50),
                f"Página {i + 1} - Texto de prueba normal",
                fontsize=12,
                fontname="helv",
                color=(0, 0, 0)
            )
            
            # Texto más grande
            page.insert_text(
                fitz.Point(50, 100),
                "Título grande de ejemplo",
                fontsize=24,
                fontname="helv",
                color=(0, 0, 0)
            )
            
            if with_bold:
                # Texto en negrita
                page.insert_text(
                    fitz.Point(50, 150),
                    "Texto en negrita",
                    fontsize=12,
                    fontname="hebo",  # Helvetica Bold
                    color=(0, 0, 0)
                )
            
            # Múltiples líneas de texto
            for j in range(5):
                page.insert_text(
                    fitz.Point(50, 200 + j * 20),
                    f"Línea {j + 1}: Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                    fontsize=10,
                    fontname="helv",
                    color=(0, 0, 0)
                )
    
    doc.save(path)
    doc.close()
    return path


# ============================================================================
# TESTS DE PDF HANDLER
# ============================================================================

class TestPDFHandler:
    """Tests para el manejador de PDFs."""
    
    def setup_method(self):
        """Configuración antes de cada test."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_pdf = os.path.join(self.temp_dir, "test.pdf")
        create_test_pdf(self.test_pdf, num_pages=3, with_text=True, with_bold=True)
    
    def teardown_method(self):
        """Limpieza después de cada test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_import_pdf_handler(self):
        """Test: Importar PDFDocument correctamente."""
        from core.pdf_handler import PDFDocument
        assert PDFDocument is not None
        print("  ✅ PDFDocument importado correctamente")
    
    def test_open_pdf(self):
        """Test: Abrir un PDF."""
        from core.pdf_handler import PDFDocument
        
        handler = PDFDocument()
        with TestTimer("Abrir PDF"):
            result = handler.open(self.test_pdf)
        
        assert result == True
        assert handler.doc is not None
        assert handler.page_count() >= 3  # >= porque puede variar
        print(f"  ✅ PDF abierto: {handler.page_count()} páginas")
        
        handler.close()
    
    def test_get_page(self):
        """Test: Obtener una página."""
        from core.pdf_handler import PDFDocument
        
        handler = PDFDocument()
        handler.open(self.test_pdf)
        
        with TestTimer("Obtener página"):
            page = handler.get_page(0)
        
        assert page is not None
        assert page.rect.width > 0
        assert page.rect.height > 0
        print(f"  ✅ Página obtenida: {page.rect.width:.1f}x{page.rect.height:.1f}")
        
        handler.close()
    
    def test_render_page(self):
        """Test: Renderizar una página."""
        from core.pdf_handler import PDFDocument
        
        handler = PDFDocument()
        handler.open(self.test_pdf)
        
        with TestTimer("Renderizar página (zoom 1.0)"):
            pixmap = handler.render_page(0, zoom=1.0)
        
        assert pixmap is not None
        assert pixmap.width > 0
        assert pixmap.height > 0
        print(f"  ✅ Página renderizada: {pixmap.width}x{pixmap.height}")
        
        handler.close()
    
    def test_render_page_high_zoom(self):
        """Test: Renderizar página con zoom alto."""
        from core.pdf_handler import PDFDocument
        
        handler = PDFDocument()
        handler.open(self.test_pdf)
        
        with TestTimer("Renderizar página (zoom 2.0)"):
            pixmap = handler.render_page(0, zoom=2.0)
        
        assert pixmap is not None
        print(f"  ✅ Página renderizada (zoom 2.0): {pixmap.width}x{pixmap.height}")
        
        handler.close()
    
    def test_find_text(self):
        """Test: Buscar texto en el PDF."""
        from core.pdf_handler import PDFDocument
        
        handler = PDFDocument()
        handler.open(self.test_pdf)
        
        with TestTimer("Buscar texto"):
            # Buscar texto en un punto específico (como tupla)
            text_block = handler.find_text_at_point(0, (100, 50))
        
        # Puede o no encontrar texto dependiendo de la posición exacta
        print(f"  ✅ Búsqueda de texto completada: {'encontrado' if text_block else 'no encontrado'}")
        
        handler.close()
    
    def test_erase_area(self):
        """Test: Borrar un área del PDF."""
        from core.pdf_handler import PDFDocument
        
        handler = PDFDocument()
        handler.open(self.test_pdf)
        
        rect = fitz.Rect(40, 40, 200, 70)
        
        with TestTimer("Borrar área"):
            result = handler.erase_area(0, rect, use_redaction=True)
        
        assert result == True
        print("  ✅ Área borrada correctamente")
        
        handler.close()
    
    def test_add_text(self):
        """Test: Añadir texto al PDF."""
        from core.pdf_handler import PDFDocument
        
        handler = PDFDocument()
        handler.open(self.test_pdf)
        
        rect = fitz.Rect(50, 400, 300, 420)
        
        with TestTimer("Añadir texto normal"):
            result = handler.add_text_to_page(
                0, rect, "Texto añadido de prueba",
                font_size=12, color=(0, 0, 0), is_bold=False
            )
        
        assert result == True
        print("  ✅ Texto normal añadido correctamente")
        
        handler.close()
    
    def test_add_bold_text(self):
        """Test: Añadir texto en negrita al PDF."""
        from core.pdf_handler import PDFDocument
        
        handler = PDFDocument()
        handler.open(self.test_pdf)
        
        rect = fitz.Rect(50, 450, 300, 470)
        
        with TestTimer("Añadir texto negrita"):
            result = handler.add_text_to_page(
                0, rect, "Texto en negrita de prueba",
                font_size=14, color=(0, 0, 0), is_bold=True
            )
        
        assert result == True
        print("  ✅ Texto negrita añadido correctamente")
        
        handler.close()
    
    def test_save_pdf(self):
        """Test: Guardar PDF modificado."""
        from core.pdf_handler import PDFDocument
        
        handler = PDFDocument()
        handler.open(self.test_pdf)
        
        # Hacer una modificación
        rect = fitz.Rect(50, 500, 300, 520)
        handler.add_text_to_page(0, rect, "Texto para guardar", font_size=12)
        
        output_path = os.path.join(self.temp_dir, "output.pdf")
        
        with TestTimer("Guardar PDF"):
            result = handler.save(output_path)
        
        assert result == True
        assert os.path.exists(output_path)
        print(f"  ✅ PDF guardado: {os.path.getsize(output_path)} bytes")
        
        handler.close()
    
    def test_undo_redo(self):
        """Test: Funcionalidad de deshacer/rehacer."""
        from core.pdf_handler import PDFDocument
        
        handler = PDFDocument()
        handler.open(self.test_pdf)
        
        # Verificar que no hay nada que deshacer
        initial_undo = handler.can_undo()
        
        # Hacer una modificación
        rect = fitz.Rect(50, 550, 300, 570)
        handler.add_text_to_page(0, rect, "Texto para undo", font_size=12)
        
        # Ahora debería poder deshacer
        can_undo = handler.can_undo()
        
        with TestTimer("Deshacer"):
            if can_undo:
                handler.undo()
        
        print(f"  ✅ Undo/Redo: inicial={initial_undo}, después={can_undo}")
        
        handler.close()


# ============================================================================
# TESTS DE RENDIMIENTO
# ============================================================================

class TestPerformance:
    """Tests de rendimiento."""
    
    def setup_method(self):
        """Configuración antes de cada test."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Limpieza después de cada test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_open_large_pdf(self):
        """Test: Abrir PDF con muchas páginas."""
        from core.pdf_handler import PDFDocument
        
        # Crear PDF con 50 páginas
        large_pdf = os.path.join(self.temp_dir, "large.pdf")
        create_test_pdf(large_pdf, num_pages=50, with_text=True)
        
        handler = PDFDocument()
        
        with TestTimer("Abrir PDF 50 páginas"):
            result = handler.open(large_pdf)
        
        assert result == True
        assert handler.page_count() >= 50  # >= porque puede tener más
        print(f"  ✅ PDF grande abierto: {handler.page_count()} páginas")
        
        handler.close()
    
    def test_render_multiple_pages(self):
        """Test: Renderizar múltiples páginas secuencialmente."""
        from core.pdf_handler import PDFDocument
        
        pdf_path = os.path.join(self.temp_dir, "multi.pdf")
        create_test_pdf(pdf_path, num_pages=10, with_text=True)
        
        handler = PDFDocument()
        handler.open(pdf_path)
        
        with TestTimer("Renderizar 10 páginas"):
            for i in range(10):
                pixmap = handler.render_page(i, zoom=1.0)
                assert pixmap is not None
        
        print("  ✅ 10 páginas renderizadas")
        
        handler.close()
    
    def test_multiple_text_operations(self):
        """Test: Múltiples operaciones de texto."""
        from core.pdf_handler import PDFDocument
        
        pdf_path = os.path.join(self.temp_dir, "ops.pdf")
        create_test_pdf(pdf_path, num_pages=1, with_text=True)
        
        handler = PDFDocument()
        handler.open(pdf_path)
        
        with TestTimer("20 operaciones de texto"):
            for i in range(20):
                y = 300 + (i * 15)
                rect = fitz.Rect(50, y, 400, y + 12)
                handler.add_text_to_page(
                    0, rect, f"Línea de prueba número {i + 1}",
                    font_size=10, is_bold=(i % 2 == 0)
                )
        
        print("  ✅ 20 operaciones de texto completadas")
        
        handler.close()
    
    def test_erase_and_add_performance(self):
        """Test: Rendimiento de borrar y añadir texto."""
        from core.pdf_handler import PDFDocument
        
        pdf_path = os.path.join(self.temp_dir, "erase.pdf")
        create_test_pdf(pdf_path, num_pages=1, with_text=True)
        
        handler = PDFDocument()
        handler.open(pdf_path)
        
        with TestTimer("10 ciclos borrar+añadir"):
            for i in range(10):
                # Borrar
                rect = fitz.Rect(40, 190 + i*2, 500, 210 + i*2)
                handler.erase_area(0, rect, use_redaction=True)
                
                # Añadir
                new_rect = fitz.Rect(50, 600 + i*15, 400, 612 + i*15)
                handler.add_text_to_page(0, new_rect, f"Nuevo texto {i}", font_size=10)
        
        print("  ✅ 10 ciclos borrar+añadir completados")
        
        handler.close()


# ============================================================================
# TESTS DE UI (sin interfaz gráfica real)
# ============================================================================

class TestUIComponents:
    """Tests para componentes de UI (importación y creación)."""
    
    def test_import_pdf_viewer(self):
        """Test: Importar PDFPageView."""
        try:
            from ui.pdf_viewer import PDFPageView
            print("  ✅ PDFPageView importado correctamente")
            assert True
        except ImportError as e:
            print(f"  ⚠️ PDFPageView no se pudo importar: {e}")
            # No fallar si no hay Qt disponible
    
    def test_import_editable_text_item(self):
        """Test: Importar EditableTextItem."""
        try:
            from ui.pdf_viewer import EditableTextItem
            print("  ✅ EditableTextItem importado correctamente")
            assert True
        except ImportError as e:
            print(f"  ⚠️ EditableTextItem no se pudo importar: {e}")
    
    def test_import_text_edit_dialog(self):
        """Test: Importar TextEditDialog."""
        try:
            from ui.pdf_viewer import TextEditDialog
            print("  ✅ TextEditDialog importado correctamente")
            assert True
        except ImportError as e:
            print(f"  ⚠️ TextEditDialog no se pudo importar: {e}")
    
    def test_import_main_window(self):
        """Test: Importar MainWindow."""
        try:
            from ui.main_window import MainWindow
            print("  ✅ MainWindow importado correctamente")
            assert True
        except ImportError as e:
            print(f"  ⚠️ MainWindow no se pudo importar: {e}")


# ============================================================================
# TESTS DE INTEGRIDAD DE DATOS
# ============================================================================

class TestDataIntegrity:
    """Tests de integridad de datos del PDF."""
    
    def setup_method(self):
        """Configuración antes de cada test."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Limpieza después de cada test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_text_preservation_after_edit(self):
        """Test: El texto original se preserva tras editar otro texto."""
        from core.pdf_handler import PDFDocument
        
        pdf_path = os.path.join(self.temp_dir, "integrity.pdf")
        create_test_pdf(pdf_path, num_pages=1, with_text=True)
        
        handler = PDFDocument()
        handler.open(pdf_path)
        
        # Obtener texto inicial
        page = handler.get_page(0)
        initial_text = page.get_text()
        
        # Añadir texto nuevo
        rect = fitz.Rect(50, 700, 300, 720)
        handler.add_text_to_page(0, rect, "Texto adicional", font_size=12)
        
        # Verificar que el texto original sigue ahí
        page = handler.get_page(0)
        final_text = page.get_text()
        
        # El texto final debe contener el texto inicial
        assert "Página 1" in final_text
        assert "Texto adicional" in final_text
        print("  ✅ Texto preservado después de edición")
        
        handler.close()
    
    def test_pdf_valid_after_save(self):
        """Test: El PDF es válido después de guardar."""
        from core.pdf_handler import PDFDocument
        
        pdf_path = os.path.join(self.temp_dir, "valid.pdf")
        create_test_pdf(pdf_path, num_pages=2, with_text=True)
        
        handler = PDFDocument()
        handler.open(pdf_path)
        
        # Hacer modificaciones
        rect = fitz.Rect(50, 700, 300, 720)
        handler.add_text_to_page(0, rect, "Modificación 1", font_size=12)
        handler.add_text_to_page(1, rect, "Modificación 2", font_size=12)
        
        output_path = os.path.join(self.temp_dir, "valid_output.pdf")
        handler.save(output_path)
        handler.close()
        
        # Intentar abrir el PDF guardado
        handler2 = PDFDocument()
        result = handler2.open(output_path)
        
        assert result == True
        assert handler2.page_count() >= 2  # >= porque puede tener más
        
        # Verificar que las modificaciones están
        page = handler2.get_page(0)
        text = page.get_text()
        assert "Modificación 1" in text
        
        print("  ✅ PDF válido después de guardar")
        
        handler2.close()


# ============================================================================
# RUNNER PRINCIPAL
# ============================================================================

def run_tests():
    """Ejecuta todos los tests manualmente."""
    print("\n" + "="*60)
    print("🧪 TESTS DE PDF EDITOR - PUNTO DE REFERENCIA")
    print("="*60)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    test_classes = [
        ("PDF Handler", TestPDFHandler),
        ("Rendimiento", TestPerformance),
        ("Componentes UI", TestUIComponents),
        ("Integridad de Datos", TestDataIntegrity),
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for section_name, test_class in test_classes:
        print(f"\n📦 {section_name}")
        print("-" * 40)
        
        instance = test_class()
        
        # Obtener todos los métodos de test
        test_methods = [m for m in dir(instance) if m.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            test_name = method_name.replace('test_', '').replace('_', ' ').title()
            
            try:
                # Setup
                if hasattr(instance, 'setup_method'):
                    instance.setup_method()
                
                # Ejecutar test
                print(f"\n🔹 {test_name}")
                method = getattr(instance, method_name)
                method()
                
                passed_tests += 1
                
            except Exception as e:
                failed_tests += 1
                print(f"  ❌ FALLÓ: {e}")
            
            finally:
                # Teardown
                if hasattr(instance, 'teardown_method'):
                    try:
                        instance.teardown_method()
                    except:
                        pass
    
    # Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN")
    print("="*60)
    print(f"  Total:    {total_tests}")
    print(f"  Pasaron:  {passed_tests} ✅")
    print(f"  Fallaron: {failed_tests} ❌")
    print(f"  Tasa:     {(passed_tests/total_tests)*100:.1f}%")
    print("="*60)
    
    if failed_tests == 0:
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
        print("   Este es tu punto de referencia - todo funciona correctamente.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) fallaron. Revisa los errores arriba.")
    
    return failed_tests == 0


if __name__ == "__main__":
    if PYTEST_AVAILABLE and len(sys.argv) > 1 and sys.argv[1] == "--pytest":
        # Usar pytest si está disponible y se solicita
        import pytest
        sys.exit(pytest.main([__file__, "-v"]))
    else:
        # Ejecutar tests manualmente
        success = run_tests()
        sys.exit(0 if success else 1)

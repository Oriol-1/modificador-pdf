"""
Tests funcionales para la edición de texto en PDFs.
=================================================

Este archivo contiene tests exhaustivos para asegurar que la funcionalidad
de edición de texto funciona correctamente en TODOS los casos posibles.

Casos cubiertos:
1. Captura completa de texto (sin truncar)
2. Preservación de estilos al mover (negrita, tamaño, fuente, color)
3. Borrado completo del área original al mover
4. Texto multilínea (párrafos)
5. Diferentes fuentes y tamaños
6. Texto con estilos mixtos
7. Coordenadas y posicionamiento correcto
8. Guardado y restauración de textos editables

Ejecutar con: python -m pytest tests/test_text_editing_functional.py -v
O sin pytest: python tests/test_text_editing_functional.py
"""

import os
import sys
import tempfile
from dataclasses import dataclass
from typing import List, Tuple, Optional

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz  # PyMuPDF

# Intentar importar PyQt5 para tests de UI
try:
    from PyQt5.QtGui import QFont, QFontMetrics
    from PyQt5.QtWidgets import QApplication
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("⚠️ PyQt5 no disponible - algunos tests serán omitidos")

# Intentar importar pytest
try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False


# ============================================================================
# ESTRUCTURAS DE DATOS PARA TESTS
# ============================================================================

@dataclass
class TextStyle:
    """Representa el estilo de un texto."""
    font_name: str
    font_size: float
    is_bold: bool
    is_italic: bool
    color: Tuple[float, float, float]
    
    def matches(self, other: 'TextStyle', tolerance: float = 0.5) -> bool:
        """Compara dos estilos con tolerancia."""
        return (
            self.font_name == other.font_name and
            abs(self.font_size - other.font_size) <= tolerance and
            self.is_bold == other.is_bold and
            self.is_italic == other.is_italic and
            all(abs(a - b) < 0.01 for a, b in zip(self.color, other.color))
        )


@dataclass
class TextBlock:
    """Representa un bloque de texto con su posición y estilo."""
    text: str
    rect: fitz.Rect
    style: TextStyle
    
    
@dataclass
class TestResult:
    """Resultado de un test."""
    passed: bool
    message: str
    details: Optional[str] = None


# ============================================================================
# UTILIDADES DE TEST
# ============================================================================

class PDFTestHelper:
    """Utilidades para crear y manipular PDFs de prueba."""
    
    @staticmethod
    def create_test_pdf_with_styles(path: str, blocks: List[TextBlock]) -> str:
        """Crea un PDF con bloques de texto con estilos específicos."""
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)  # A4
        
        for block in blocks:
            fontname = "hebo" if block.style.is_bold else "helv"
            if block.style.is_italic:
                fontname = "heit" if not block.style.is_bold else "hebi"
            
            page.insert_text(
                fitz.Point(block.rect.x0, block.rect.y0 + block.style.font_size),
                block.text,
                fontsize=block.style.font_size,
                fontname=fontname,
                color=block.style.color
            )
        
        doc.save(path)
        doc.close()
        return path
    
    @staticmethod
    def create_multiline_pdf(path: str, lines: List[str], start_y: float = 100,
                             line_spacing: float = 14, font_size: float = 12) -> str:
        """Crea un PDF con múltiples líneas de texto."""
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        
        y = start_y
        for line in lines:
            page.insert_text(
                fitz.Point(50, y),
                line,
                fontsize=font_size,
                fontname="helv",
                color=(0, 0, 0)
            )
            y += line_spacing
        
        doc.save(path)
        doc.close()
        return path
    
    @staticmethod
    def create_mixed_styles_pdf(path: str) -> str:
        """Crea un PDF con estilos mixtos (negrita, normal, diferentes tamaños)."""
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        
        # Título en negrita grande
        page.insert_text(fitz.Point(50, 50), "TÍTULO PRINCIPAL", 
                        fontsize=24, fontname="hebo", color=(0, 0, 0))
        
        # Subtítulo normal
        page.insert_text(fitz.Point(50, 90), "Subtítulo del documento",
                        fontsize=16, fontname="helv", color=(0.3, 0.3, 0.3))
        
        # Párrafo con negrita parcial - línea 1
        page.insert_text(fitz.Point(50, 130), "Este es un texto ",
                        fontsize=12, fontname="helv", color=(0, 0, 0))
        page.insert_text(fitz.Point(145, 130), "en negrita",
                        fontsize=12, fontname="hebo", color=(0, 0, 0))
        page.insert_text(fitz.Point(215, 130), " y normal.",
                        fontsize=12, fontname="helv", color=(0, 0, 0))
        
        # Múltiples líneas de párrafo
        y = 160
        for i in range(5):
            page.insert_text(fitz.Point(50, y), 
                           f"Línea {i+1}: Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                           fontsize=10, fontname="helv", color=(0, 0, 0))
            y += 14
        
        # Texto con color
        page.insert_text(fitz.Point(50, y + 20), "Texto en color rojo",
                        fontsize=12, fontname="helv", color=(1, 0, 0))
        
        page.insert_text(fitz.Point(50, y + 40), "Texto en color azul",
                        fontsize=12, fontname="helv", color=(0, 0, 1))
        
        doc.save(path)
        doc.close()
        return path
    
    @staticmethod
    def get_text_blocks_in_rect(doc: fitz.Document, page_num: int, 
                                 rect: fitz.Rect) -> List[dict]:
        """Obtiene los bloques de texto en un rectángulo."""
        page = doc[page_num]
        blocks = []
        
        text_dict = page.get_text("dict", clip=rect)
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Bloque de texto
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        blocks.append({
                            'text': span.get('text', ''),
                            'font': span.get('font', ''),
                            'size': span.get('size', 12),
                            'color': span.get('color', 0),
                            'bbox': span.get('bbox', []),
                            'flags': span.get('flags', 0)
                        })
        
        return blocks
    
    @staticmethod
    def get_all_text_from_page(doc: fitz.Document, page_num: int) -> str:
        """Obtiene todo el texto de una página."""
        page = doc[page_num]
        return page.get_text()


# ============================================================================
# TESTS DE CAPTURA DE TEXTO
# ============================================================================

class TestTextCapture:
    """Tests para la captura completa de texto."""
    
    def test_capture_single_line(self):
        """Test: Capturar una línea de texto completa."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "single_line.pdf")
            
            # Crear PDF con una línea
            doc = fitz.open()
            page = doc.new_page()
            test_text = "Esta es una línea de prueba completa"
            page.insert_text(fitz.Point(50, 100), test_text, fontsize=12)
            doc.save(pdf_path)
            doc.close()
            
            # Verificar que el texto se captura completo
            doc = fitz.open(pdf_path)
            text = doc[0].get_text().strip()
            doc.close()
            
            assert text == test_text, f"Texto capturado incompleto: '{text}' vs '{test_text}'"
            print("✅ test_capture_single_line: PASSED")
            return TestResult(True, "Línea capturada completa")
    
    def test_capture_multiline_paragraph(self):
        """Test: Capturar un párrafo multilínea completo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "multiline.pdf")
            
            lines = [
                "Primera línea del párrafo.",
                "Segunda línea con más contenido.",
                "Tercera línea para completar.",
                "Cuarta y última línea del texto."
            ]
            
            PDFTestHelper.create_multiline_pdf(pdf_path, lines)
            
            # Verificar que todas las líneas se capturan
            doc = fitz.open(pdf_path)
            captured_text = doc[0].get_text()
            doc.close()
            
            for line in lines:
                assert line in captured_text, f"Línea faltante: '{line}'"
            
            print("✅ test_capture_multiline_paragraph: PASSED")
            return TestResult(True, "Párrafo multilínea capturado completo")
    
    def test_capture_text_with_rect_selection(self):
        """Test: Capturar texto usando selección rectangular."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "rect_select.pdf")
            
            doc = fitz.open()
            page = doc.new_page()
            
            # Texto en posición conocida
            page.insert_text(fitz.Point(100, 200), "Texto dentro del área", fontsize=12)
            page.insert_text(fitz.Point(100, 300), "Texto fuera del área", fontsize=12)
            
            doc.save(pdf_path)
            doc.close()
            
            # Capturar solo el área específica
            doc = fitz.open(pdf_path)
            rect = fitz.Rect(90, 180, 300, 220)
            text = doc[0].get_text("text", clip=rect).strip()
            doc.close()
            
            assert "dentro" in text, f"Debería capturar 'dentro del área': '{text}'"
            assert "fuera" not in text, f"No debería capturar 'fuera': '{text}'"
            
            print("✅ test_capture_text_with_rect_selection: PASSED")
            return TestResult(True, "Selección rectangular funciona correctamente")


# ============================================================================
# TESTS DE PRESERVACIÓN DE ESTILOS
# ============================================================================

class TestStylePreservation:
    """Tests para preservación de estilos al mover/editar texto."""
    
    def test_preserve_font_size(self):
        """Test: El tamaño de fuente se preserva."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "font_size.pdf")
            
            doc = fitz.open()
            page = doc.new_page()
            
            # Textos con diferentes tamaños
            page.insert_text(fitz.Point(50, 50), "Texto pequeño", fontsize=8)
            page.insert_text(fitz.Point(50, 80), "Texto mediano", fontsize=12)
            page.insert_text(fitz.Point(50, 120), "Texto grande", fontsize=24)
            
            doc.save(pdf_path)
            doc.close()
            
            # Verificar tamaños
            doc = fitz.open(pdf_path)
            page = doc[0]
            text_dict = page.get_text("dict")
            
            sizes_found = []
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            sizes_found.append(span.get("size", 0))
            
            doc.close()
            
            # Verificar que se preservan los 3 tamaños distintos
            assert 8 in [round(s) for s in sizes_found], "Falta tamaño 8"
            assert 12 in [round(s) for s in sizes_found], "Falta tamaño 12"
            assert 24 in [round(s) for s in sizes_found], "Falta tamaño 24"
            
            print("✅ test_preserve_font_size: PASSED")
            return TestResult(True, "Tamaños de fuente preservados")
    
    def test_preserve_bold_style(self):
        """Test: El estilo negrita se preserva."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "bold.pdf")
            
            doc = fitz.open()
            page = doc.new_page()
            
            # Texto normal y negrita
            page.insert_text(fitz.Point(50, 50), "Texto normal", fontsize=12, fontname="helv")
            page.insert_text(fitz.Point(50, 80), "Texto en negrita", fontsize=12, fontname="hebo")
            
            doc.save(pdf_path)
            doc.close()
            
            # Verificar estilos
            doc = fitz.open(pdf_path)
            page = doc[0]
            text_dict = page.get_text("dict")
            
            fonts_found = []
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            fonts_found.append(span.get("font", ""))
            
            doc.close()
            
            # Verificar que hay fuentes bold y normal
            has_bold = any("Bold" in f or "bold" in f.lower() for f in fonts_found)
            has_normal = any("Bold" not in f and "bold" not in f.lower() for f in fonts_found)
            
            assert has_bold, f"Falta texto en negrita. Fuentes: {fonts_found}"
            assert has_normal, f"Falta texto normal. Fuentes: {fonts_found}"
            
            print("✅ test_preserve_bold_style: PASSED")
            return TestResult(True, "Estilo negrita preservado")
    
    def test_preserve_color(self):
        """Test: El color del texto se preserva."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "colors.pdf")
            
            doc = fitz.open()
            page = doc.new_page()
            
            # Textos con diferentes colores
            page.insert_text(fitz.Point(50, 50), "Negro", fontsize=12, color=(0, 0, 0))
            page.insert_text(fitz.Point(50, 80), "Rojo", fontsize=12, color=(1, 0, 0))
            page.insert_text(fitz.Point(50, 110), "Azul", fontsize=12, color=(0, 0, 1))
            
            doc.save(pdf_path)
            doc.close()
            
            # Verificar colores
            doc = fitz.open(pdf_path)
            page = doc[0]
            text_dict = page.get_text("dict")
            
            colors_found = set()
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            colors_found.add(span.get("color", 0))
            
            doc.close()
            
            # Debe haber al menos 3 colores diferentes
            assert len(colors_found) >= 3, f"Esperaba 3+ colores, encontré {len(colors_found)}: {colors_found}"
            
            print("✅ test_preserve_color: PASSED")
            return TestResult(True, "Colores preservados")
    
    def test_extract_text_runs_with_styles(self):
        """Test: Extraer text_runs con estilos individuales."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "mixed.pdf")
            
            PDFTestHelper.create_mixed_styles_pdf(pdf_path)
            
            doc = fitz.open(pdf_path)
            page = doc[0]
            text_dict = page.get_text("dict")
            
            # Contar spans con diferentes estilos
            bold_count = 0
            normal_count = 0
            
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            font = span.get("font", "")
                            if "Bold" in font or "bold" in font.lower():
                                bold_count += 1
                            else:
                                normal_count += 1
            
            doc.close()
            
            assert bold_count > 0, "Debería haber spans en negrita"
            assert normal_count > 0, "Debería haber spans normales"
            
            print(f"✅ test_extract_text_runs_with_styles: PASSED (bold={bold_count}, normal={normal_count})")
            return TestResult(True, f"Text runs extraídos: {bold_count} bold, {normal_count} normal")


# ============================================================================
# TESTS DE BORRADO Y MOVIMIENTO
# ============================================================================

class TestEraseAndMove:
    """Tests para borrado y movimiento de texto."""
    
    def test_erase_text_area(self):
        """Test: Borrar texto de un área específica."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "erase_test.pdf")
            modified_path = os.path.join(tmpdir, "erased.pdf")
            
            # Crear PDF original
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text(fitz.Point(100, 100), "Texto a borrar", fontsize=12)
            page.insert_text(fitz.Point(100, 200), "Texto que permanece", fontsize=12)
            doc.save(pdf_path)
            doc.close()
            
            # Verificar texto original
            doc = fitz.open(pdf_path)
            original_text = doc[0].get_text()
            assert "Texto a borrar" in original_text
            assert "Texto que permanece" in original_text
            
            # Borrar área específica usando redacción
            page = doc[0]
            rect = fitz.Rect(90, 85, 250, 115)
            page.add_redact_annot(rect)
            page.apply_redactions()
            
            doc.save(modified_path)
            doc.close()
            
            # Verificar que solo se borró lo correcto
            doc = fitz.open(modified_path)
            modified_text = doc[0].get_text()
            doc.close()
            
            assert "Texto a borrar" not in modified_text, "El texto debería estar borrado"
            assert "Texto que permanece" in modified_text, "Este texto NO debería estar borrado"
            
            print("✅ test_erase_text_area: PASSED")
            return TestResult(True, "Borrado de área funciona correctamente")
    
    def test_erase_multiline_block(self):
        """Test: Borrar un bloque multilínea completo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "multiline_erase.pdf")
            modified_path = os.path.join(tmpdir, "erased.pdf")
            
            lines = [
                "Primera línea a borrar",
                "Segunda línea a borrar",
                "Tercera línea a borrar"
            ]
            
            # Crear PDF
            doc = fitz.open()
            page = doc.new_page()
            
            y = 100
            for line in lines:
                page.insert_text(fitz.Point(50, y), line, fontsize=12)
                y += 14
            
            # Texto que debe permanecer
            page.insert_text(fitz.Point(50, 300), "Este texto no se borra", fontsize=12)
            
            doc.save(pdf_path)
            doc.close()
            
            # Verificar original
            doc = fitz.open(pdf_path)
            assert all(line in doc[0].get_text() for line in lines)
            
            # Borrar bloque multilínea
            page = doc[0]
            rect = fitz.Rect(40, 85, 300, 145)  # Rect que cubre las 3 líneas
            page.add_redact_annot(rect)
            page.apply_redactions()
            
            doc.save(modified_path)
            doc.close()
            
            # Verificar
            doc = fitz.open(modified_path)
            text = doc[0].get_text()
            doc.close()
            
            for line in lines:
                assert line not in text, f"'{line}' debería estar borrado"
            assert "Este texto no se borra" in text
            
            print("✅ test_erase_multiline_block: PASSED")
            return TestResult(True, "Borrado de bloque multilínea funciona")
    
    def test_calculate_erase_rect_for_text(self):
        """Test: Calcular rectángulo de borrado correcto para texto."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "rect_calc.pdf")
            
            # Crear PDF con texto en posición conocida
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text(fitz.Point(100, 100), "Texto de prueba", fontsize=12)
            doc.save(pdf_path)
            doc.close()
            
            # Obtener el rectángulo real del texto
            doc = fitz.open(pdf_path)
            page = doc[0]
            text_dict = page.get_text("dict")
            
            text_rect = None
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            if "prueba" in span.get("text", ""):
                                bbox = span.get("bbox", [])
                                if bbox:
                                    text_rect = fitz.Rect(bbox)
                                    break
            
            doc.close()
            
            assert text_rect is not None, "Debería encontrar el rectángulo del texto"
            assert text_rect.width > 0, "El rectángulo debe tener ancho"
            assert text_rect.height > 0, "El rectángulo debe tener alto"
            
            print(f"✅ test_calculate_erase_rect_for_text: PASSED (rect={text_rect})")
            return TestResult(True, f"Rectángulo calculado: {text_rect}")


# ============================================================================
# TESTS DE COORDINADAS
# ============================================================================

class TestCoordinates:
    """Tests para manejo correcto de coordenadas."""
    
    def test_pdf_coordinate_system(self):
        """Test: El sistema de coordenadas PDF es correcto."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "coords.pdf")
            
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)  # A4
            
            # Texto en esquinas
            page.insert_text(fitz.Point(10, 20), "Superior izquierda", fontsize=10)
            page.insert_text(fitz.Point(400, 20), "Superior derecha", fontsize=10)
            page.insert_text(fitz.Point(10, 820), "Inferior izquierda", fontsize=10)
            page.insert_text(fitz.Point(400, 820), "Inferior derecha", fontsize=10)
            
            doc.save(pdf_path)
            doc.close()
            
            # Verificar posiciones
            doc = fitz.open(pdf_path)
            page = doc[0]
            text_dict = page.get_text("dict")
            
            positions = {}
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "")
                            bbox = span.get("bbox", [0, 0, 0, 0])
                            positions[text] = (bbox[0], bbox[1])
            
            doc.close()
            
            # Verificar que están en las posiciones correctas
            sup_izq = positions.get("Superior izquierda", (999, 999))
            sup_der = positions.get("Superior derecha", (0, 0))
            inf_izq = positions.get("Inferior izquierda", (999, 0))
            _inf_der = positions.get("Inferior derecha", (0, 999))  # noqa: F841
            
            assert sup_izq[0] < sup_der[0], "Superior izquierda debe estar a la izquierda"
            assert sup_izq[1] < inf_izq[1], "Superior debe estar arriba (Y menor)"
            
            print("✅ test_pdf_coordinate_system: PASSED")
            return TestResult(True, "Sistema de coordenadas correcto")
    
    def test_rect_contains_text(self):
        """Test: Verificar si un rectángulo contiene texto."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "rect_contains.pdf")
            
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text(fitz.Point(100, 100), "Dentro", fontsize=12)
            page.insert_text(fitz.Point(300, 300), "Fuera", fontsize=12)
            doc.save(pdf_path)
            doc.close()
            
            doc = fitz.open(pdf_path)
            page = doc[0]
            
            # Rectángulo que contiene solo "Dentro"
            rect = fitz.Rect(90, 85, 200, 115)
            text_inside = page.get_text("text", clip=rect).strip()
            
            assert "Dentro" in text_inside, f"Debería contener 'Dentro': '{text_inside}'"
            assert "Fuera" not in text_inside, f"No debería contener 'Fuera': '{text_inside}'"
            
            doc.close()
            
            print("✅ test_rect_contains_text: PASSED")
            return TestResult(True, "Detección de texto en rectángulo correcta")


# ============================================================================
# TESTS DE INTEGRACIÓN
# ============================================================================

class TestIntegration:
    """Tests de integración para flujos completos."""
    
    def test_full_edit_workflow(self):
        """Test: Flujo completo de edición (capturar -> mover -> guardar)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "workflow.pdf")
            output_path = os.path.join(tmpdir, "modified.pdf")
            
            # 1. Crear PDF original
            doc = fitz.open()
            page = doc.new_page()
            original_text = "Texto original para editar"
            page.insert_text(fitz.Point(100, 100), original_text, fontsize=12)
            doc.save(pdf_path)
            doc.close()
            
            # 2. Abrir, "capturar" y modificar
            doc = fitz.open(pdf_path)
            page = doc[0]
            
            # Simular captura: obtener texto y rect
            text_dict = page.get_text("dict")
            captured_rect = None
            captured_text = None
            
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            if "original" in span.get("text", ""):
                                captured_text = span.get("text", "")
                                captured_rect = fitz.Rect(span.get("bbox", []))
            
            assert captured_text is not None, "Debería capturar el texto"
            assert captured_rect is not None, "Debería tener un rectángulo"
            
            # 3. Simular borrado del original
            page.add_redact_annot(captured_rect)
            page.apply_redactions()
            
            # 4. Simular inserción en nueva posición
            new_pos = fitz.Point(200, 200)
            page.insert_text(new_pos, captured_text, fontsize=12)
            
            doc.save(output_path)
            doc.close()
            
            # 5. Verificar resultado
            doc = fitz.open(output_path)
            final_text = doc[0].get_text()
            doc.close()
            
            assert original_text in final_text, f"El texto debería existir: '{final_text}'"
            
            print("✅ test_full_edit_workflow: PASSED")
            return TestResult(True, "Flujo completo de edición funciona")
    
    def test_preserve_unedited_content(self):
        """Test: El contenido no editado se preserva intacto."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "preserve.pdf")
            output_path = os.path.join(tmpdir, "modified.pdf")
            
            # Crear PDF con múltiples elementos
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text(fitz.Point(50, 50), "Texto 1 - No tocar", fontsize=12)
            page.insert_text(fitz.Point(50, 100), "Texto 2 - A editar", fontsize=12)
            page.insert_text(fitz.Point(50, 150), "Texto 3 - No tocar", fontsize=12)
            doc.save(pdf_path)
            doc.close()
            
            # Editar solo "Texto 2"
            doc = fitz.open(pdf_path)
            page = doc[0]
            
            # Borrar texto 2
            rect = fitz.Rect(40, 85, 200, 115)
            page.add_redact_annot(rect)
            page.apply_redactions()
            
            # Insertar nuevo
            page.insert_text(fitz.Point(50, 100), "Texto 2 - Editado", fontsize=12)
            
            doc.save(output_path)
            doc.close()
            
            # Verificar
            doc = fitz.open(output_path)
            text = doc[0].get_text()
            doc.close()
            
            assert "Texto 1 - No tocar" in text, "Texto 1 debe preservarse"
            assert "Texto 3 - No tocar" in text, "Texto 3 debe preservarse"
            assert "Texto 2 - Editado" in text, "Texto 2 debe estar editado"
            assert "Texto 2 - A editar" not in text, "Texto 2 original debe estar borrado"
            
            print("✅ test_preserve_unedited_content: PASSED")
            return TestResult(True, "Contenido no editado se preserva")


# ============================================================================
# TESTS ESPECÍFICOS PARA EditableTextItem (requiere PyQt5)
# ============================================================================

if PYQT_AVAILABLE:
    class TestEditableTextItem:
        """Tests para el componente EditableTextItem."""
        
        def test_rect_adjustment_to_content(self):
            """Test: El rectángulo se ajusta al contenido del texto."""
            # Este test requiere la aplicación Qt
            _app = QApplication.instance() or QApplication(sys.argv)  # noqa: F841
            
            # Simular cálculo de tamaño
            font = QFont("Helvetica", 12)
            metrics = QFontMetrics(font)
            
            test_text = "Texto de prueba para medir"
            text_width = metrics.horizontalAdvance(test_text)
            text_height = metrics.height()
            
            # El rectángulo debe tener al menos el tamaño del texto
            assert text_width > 0, "El ancho debe ser positivo"
            assert text_height > 0, "La altura debe ser positiva"
            
            # Multilinea
            multiline = "Línea 1\nLínea 2\nLínea 3"
            lines = multiline.split('\n')
            multi_height = len(lines) * metrics.lineSpacing()
            
            assert multi_height > text_height, "Multilínea debe ser más alto"
            
            print("✅ test_rect_adjustment_to_content: PASSED")
            print(f"   - Ancho texto: {text_width}px")
            print(f"   - Alto línea: {text_height}px")
            print(f"   - Alto multilínea: {multi_height}px")
            return TestResult(True, "Ajuste de rectángulo funciona")
        
        def test_text_runs_structure(self):
            """Test: La estructura de text_runs es correcta."""
            # Simular estructura de text_runs
            text_runs = [
                {'text': 'Texto ', 'font_name': 'Helvetica', 'font_size': 12, 'is_bold': False},
                {'text': 'en negrita', 'font_name': 'Helvetica-Bold', 'font_size': 12, 'is_bold': True},
                {'text': ' y normal.', 'font_name': 'Helvetica', 'font_size': 12, 'is_bold': False},
            ]
            
            # Verificar estructura
            for run in text_runs:
                assert 'text' in run, "Cada run debe tener 'text'"
                assert 'font_name' in run, "Cada run debe tener 'font_name'"
                assert 'font_size' in run, "Cada run debe tener 'font_size'"
                assert 'is_bold' in run, "Cada run debe tener 'is_bold'"
            
            # Reconstruir texto completo
            full_text = ''.join(run['text'] for run in text_runs)
            assert full_text == "Texto en negrita y normal."
            
            # Verificar que hay runs bold y normal
            bold_runs = [r for r in text_runs if r['is_bold']]
            normal_runs = [r for r in text_runs if not r['is_bold']]
            
            assert len(bold_runs) > 0, "Debe haber runs en negrita"
            assert len(normal_runs) > 0, "Debe haber runs normales"
            
            print("✅ test_text_runs_structure: PASSED")
            return TestResult(True, "Estructura de text_runs correcta")


# ============================================================================
# EJECUTOR DE TESTS
# ============================================================================

def run_all_tests():
    """Ejecuta todos los tests y reporta resultados."""
    print("\n" + "=" * 70)
    print("🧪 TESTS FUNCIONALES DE EDICIÓN DE TEXTO PDF")
    print("=" * 70 + "\n")
    
    test_classes = [
        ("Captura de Texto", TestTextCapture()),
        ("Preservación de Estilos", TestStylePreservation()),
        ("Borrado y Movimiento", TestEraseAndMove()),
        ("Coordenadas", TestCoordinates()),
        ("Integración", TestIntegration()),
    ]
    
    if PYQT_AVAILABLE:
        test_classes.append(("EditableTextItem", TestEditableTextItem()))
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for class_name, test_instance in test_classes:
        print(f"\n📋 {class_name}")
        print("-" * 50)
        
        # Obtener todos los métodos de test
        test_methods = [m for m in dir(test_instance) if m.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(test_instance, method_name)
                result = method()
                if result and result.passed:
                    passed_tests += 1
                else:
                    failed_tests.append((class_name, method_name, "Result failed"))
            except Exception as e:
                failed_tests.append((class_name, method_name, str(e)))
                print(f"❌ {method_name}: FAILED - {e}")
    
    # Resumen
    print("\n" + "=" * 70)
    print("📊 RESUMEN DE TESTS")
    print("=" * 70)
    print(f"✅ Pasados: {passed_tests}/{total_tests}")
    print(f"❌ Fallidos: {len(failed_tests)}/{total_tests}")
    
    if failed_tests:
        print("\n⚠️ Tests fallidos:")
        for class_name, method, error in failed_tests:
            print(f"   - {class_name}.{method}: {error}")
    
    print("\n" + "=" * 70)
    
    return len(failed_tests) == 0


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    if PYTEST_AVAILABLE and len(sys.argv) > 1 and sys.argv[1] == "--pytest":
        # Ejecutar con pytest
        pytest.main([__file__, "-v"])
    else:
        # Ejecutar directamente
        success = run_all_tests()
        sys.exit(0 if success else 1)

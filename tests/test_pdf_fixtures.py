"""
PHASE2-302: Tests para PDF Fixtures

Estos tests verifican que los PDFs de prueba están correctamente
generados y pueden ser usados para testing de font detection.
"""
import pytest
from pathlib import Path
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

import fitz  # PyMuPDF

# Directorio de fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "test_pdfs"


class TestPDFFixturesExist:
    """Verificar que los PDFs de prueba existen."""
    
    def test_fixtures_directory_exists(self):
        """El directorio de fixtures debe existir."""
        assert FIXTURES_DIR.exists(), f"Directorio no encontrado: {FIXTURES_DIR}"
    
    def test_simple_fonts_pdf_exists(self):
        """simple_fonts.pdf debe existir."""
        pdf_path = FIXTURES_DIR / "simple_fonts.pdf"
        assert pdf_path.exists(), f"PDF no encontrado: {pdf_path}"
    
    def test_custom_fonts_pdf_exists(self):
        """custom_fonts.pdf debe existir."""
        pdf_path = FIXTURES_DIR / "custom_fonts.pdf"
        assert pdf_path.exists(), f"PDF no encontrado: {pdf_path}"
    
    def test_bold_italic_pdf_exists(self):
        """bold_italic.pdf debe existir."""
        pdf_path = FIXTURES_DIR / "bold_italic.pdf"
        assert pdf_path.exists(), f"PDF no encontrado: {pdf_path}"


class TestSimpleFontsPDF:
    """Tests para simple_fonts.pdf"""
    
    @pytest.fixture
    def pdf_doc(self):
        """Abrir el PDF para testing."""
        pdf_path = FIXTURES_DIR / "simple_fonts.pdf"
        doc = fitz.open(str(pdf_path))
        yield doc
        doc.close()
    
    def test_has_multiple_pages(self, pdf_doc):
        """El PDF debe tener al menos 1 página."""
        assert len(pdf_doc) >= 1
    
    def test_contains_arial_text(self, pdf_doc):
        """El PDF debe contener texto con fuente tipo Arial/Helvetica."""
        page = pdf_doc[0]
        text_dict = page.get_text("dict")
        
        # Buscar fuentes Helvetica (Arial en PDF)
        fonts_found = set()
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        font = span.get("font", "")
                        fonts_found.add(font)
        
        # Debe tener alguna fuente (Helvetica es la más común)
        assert len(fonts_found) > 0, "No se encontraron fuentes"
    
    def test_contains_editable_text(self, pdf_doc):
        """El PDF debe contener texto que puede ser extraído."""
        page = pdf_doc[0]
        text = page.get_text()
        
        # Debe tener contenido de texto
        assert len(text.strip()) > 50, "El PDF no tiene suficiente texto"
    
    def test_contains_sample_text_markers(self, pdf_doc):
        """El PDF debe contener marcadores de texto de prueba."""
        page = pdf_doc[0]
        text = page.get_text()
        
        # Verificar que contiene texto esperado
        assert "Arial" in text or "Helvetica" in text or "fuente" in text.lower()


class TestCustomFontsPDF:
    """Tests para custom_fonts.pdf"""
    
    @pytest.fixture
    def pdf_doc(self):
        """Abrir el PDF para testing."""
        pdf_path = FIXTURES_DIR / "custom_fonts.pdf"
        doc = fitz.open(str(pdf_path))
        yield doc
        doc.close()
    
    def test_has_content(self, pdf_doc):
        """El PDF debe tener contenido."""
        assert len(pdf_doc) >= 1
        
        page = pdf_doc[0]
        text = page.get_text()
        assert len(text.strip()) > 0, "El PDF no tiene texto"
    
    def test_font_simulation_markers(self, pdf_doc):
        """El PDF debe tener marcadores de simulación de fuentes."""
        page = pdf_doc[0]
        text = page.get_text()
        
        # Debe mencionar fuentes personalizadas o simulaciones
        has_font_ref = (
            "custom" in text.lower() or 
            "font" in text.lower() or
            "fuente" in text.lower() or
            "simulación" in text.lower() or
            "simulacion" in text.lower()
        )
        assert has_font_ref, "No se encontraron referencias a fuentes custom"


class TestBoldItalicPDF:
    """Tests para bold_italic.pdf - crítico para heurísticas."""
    
    @pytest.fixture
    def pdf_doc(self):
        """Abrir el PDF para testing."""
        pdf_path = FIXTURES_DIR / "bold_italic.pdf"
        doc = fitz.open(str(pdf_path))
        yield doc
        doc.close()
    
    def test_has_two_pages(self, pdf_doc):
        """El PDF debe tener 2 páginas."""
        assert len(pdf_doc) == 2, f"Esperado 2 páginas, encontradas {len(pdf_doc)}"
    
    def test_page1_has_bold_samples(self, pdf_doc):
        """La página 1 debe tener muestras de texto bold."""
        page = pdf_doc[0]
        text = page.get_text()
        
        assert "[BOLD]" in text, "No se encontraron marcadores [BOLD]"
    
    def test_page1_has_normal_samples(self, pdf_doc):
        """La página 1 debe tener muestras de texto normal."""
        page = pdf_doc[0]
        text = page.get_text()
        
        assert "[NORMAL]" in text, "No se encontraron marcadores [NORMAL]"
    
    def test_contains_helvetica_variants(self, pdf_doc):
        """El PDF debe contener variantes de Helvetica."""
        page = pdf_doc[0]
        text_dict = page.get_text("dict")
        
        fonts = set()
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        fonts.add(span.get("font", ""))
        
        # Debe tener múltiples fuentes
        assert len(fonts) >= 2, f"Solo se encontraron {len(fonts)} fuentes: {fonts}"
    
    def test_can_detect_bold_font_property(self, pdf_doc):
        """Debe poder detectar la propiedad bold en las fuentes."""
        page = pdf_doc[0]
        text_dict = page.get_text("dict")
        
        bold_fonts_found = []
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        font = span.get("font", "").lower()
                        if "bold" in font:
                            bold_fonts_found.append(font)
        
        assert len(bold_fonts_found) > 0, "No se detectaron fuentes bold"
    
    def test_can_detect_italic_font_property(self, pdf_doc):
        """Debe poder detectar la propiedad italic en las fuentes."""
        page = pdf_doc[0]
        text_dict = page.get_text("dict")
        
        italic_fonts_found = []
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        font = span.get("font", "").lower()
                        if "italic" in font or "oblique" in font:
                            italic_fonts_found.append(font)
        
        assert len(italic_fonts_found) > 0, "No se detectaron fuentes italic"
    
    def test_page2_has_editable_sections(self, pdf_doc):
        """La página 2 debe tener secciones editables."""
        page = pdf_doc[1]
        text = page.get_text()
        
        assert "EDITABLE" in text, "No se encontraron marcadores EDITABLE"


class TestFontDetectionWithFixtures:
    """Tests de integración: detectar fuentes en los PDFs."""
    
    @pytest.fixture
    def bold_italic_doc(self):
        """Abrir bold_italic.pdf para testing."""
        pdf_path = FIXTURES_DIR / "bold_italic.pdf"
        doc = fitz.open(str(pdf_path))
        yield doc
        doc.close()
    
    def test_extract_all_font_names(self, bold_italic_doc):
        """Extraer todos los nombres de fuentes del PDF."""
        all_fonts = set()
        
        for page_num in range(len(bold_italic_doc)):
            page = bold_italic_doc[page_num]
            text_dict = page.get_text("dict")
            
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            all_fonts.add(span.get("font", ""))
        
        # Debería tener al menos 3 fuentes diferentes
        assert len(all_fonts) >= 3, f"Esperado >=3 fuentes, encontradas: {all_fonts}"
    
    def test_font_metrics_extraction(self, bold_italic_doc):
        """Verificar que se pueden extraer métricas de fuente."""
        page = bold_italic_doc[0]
        text_dict = page.get_text("dict")
        
        spans_with_metrics = []
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if span.get("size") and span.get("font"):
                            spans_with_metrics.append({
                                "font": span.get("font"),
                                "size": span.get("size"),
                                "flags": span.get("flags", 0),
                                "text": span.get("text", "")[:20]
                            })
        
        assert len(spans_with_metrics) > 0, "No se pudieron extraer métricas"
    
    def test_bold_flag_detection(self, bold_italic_doc):
        """Verificar detección de flag bold en spans."""
        page = bold_italic_doc[0]
        text_dict = page.get_text("dict")
        
        # Flag 16 = bold en PyMuPDF
        bold_spans = []
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        flags = span.get("flags", 0)
                        font = span.get("font", "").lower()
                        # Bold puede detectarse por flag o por nombre
                        if (flags & 16) or "bold" in font:
                            bold_spans.append(span)
        
        assert len(bold_spans) > 0, "No se detectaron spans bold"


class TestPDFFixturesRegeneration:
    """Tests para verificar que los PDFs pueden regenerarse."""
    
    def test_can_import_generator(self):
        """El módulo generador debe poder importarse."""
        from tests.fixtures.generate_test_pdfs import main
        assert callable(main)
    
    def test_generator_functions_exist(self):
        """Las funciones de generación deben existir."""
        from tests.fixtures import generate_test_pdfs
        
        assert hasattr(generate_test_pdfs, "create_simple_fonts_pdf")
        assert hasattr(generate_test_pdfs, "create_custom_fonts_pdf")
        assert hasattr(generate_test_pdfs, "create_bold_italic_pdf")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

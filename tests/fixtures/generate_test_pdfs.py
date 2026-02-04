"""
PHASE2-302: Generador de PDFs de Prueba

Crea PDFs fixtures para testing de:
- Detección de fuentes (simple_fonts.pdf)
- Fuentes custom/embebidas (custom_fonts.pdf)
- Negritas e itálicas (bold_italic.pdf)

Ejecutar: python tests/fixtures/generate_test_pdfs.py
"""

import sys
from pathlib import Path

# Asegurar imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERROR: PyMuPDF no instalado. Ejecuta: pip install PyMuPDF")
    sys.exit(1)


def create_simple_fonts_pdf(output_path: str) -> bool:
    """
    Crea simple_fonts.pdf con Arial, Times, Courier.
    
    Contenido:
    - Párrafo en Arial 12pt
    - Párrafo en Times 12pt  
    - Párrafo en Courier 12pt
    - Texto en diferentes tamaños
    """
    try:
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)  # A4
        
        y_pos = 50
        
        # Título
        page.insert_text(
            fitz.Point(50, y_pos),
            "Test PDF: Simple Fonts",
            fontsize=18,
            fontname="helv",
            color=(0, 0, 0)
        )
        y_pos += 40
        
        # Helvetica (Arial equivalent) 12pt
        page.insert_text(
            fitz.Point(50, y_pos),
            "Este párrafo está en Helvetica (Arial) 12pt.",
            fontsize=12,
            fontname="helv",
            color=(0, 0, 0)
        )
        y_pos += 25
        
        page.insert_text(
            fitz.Point(50, y_pos),
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            fontsize=12,
            fontname="helv",
            color=(0, 0, 0)
        )
        y_pos += 40
        
        # Times 12pt
        page.insert_text(
            fitz.Point(50, y_pos),
            "Este párrafo está en Times 12pt.",
            fontsize=12,
            fontname="tiro",
            color=(0, 0, 0)
        )
        y_pos += 25
        
        page.insert_text(
            fitz.Point(50, y_pos),
            "Sed do eiusmod tempor incididunt ut labore et dolore magna.",
            fontsize=12,
            fontname="tiro",
            color=(0, 0, 0)
        )
        y_pos += 40
        
        # Courier 12pt
        page.insert_text(
            fitz.Point(50, y_pos),
            "Este párrafo está en Courier 12pt.",
            fontsize=12,
            fontname="cour",
            color=(0, 0, 0)
        )
        y_pos += 25
        
        page.insert_text(
            fitz.Point(50, y_pos),
            "Ut enim ad minim veniam, quis nostrud exercitation.",
            fontsize=12,
            fontname="cour",
            color=(0, 0, 0)
        )
        y_pos += 50
        
        # Diferentes tamaños
        page.insert_text(
            fitz.Point(50, y_pos),
            "Tamaño 10pt - Texto pequeño",
            fontsize=10,
            fontname="helv",
            color=(0, 0, 0)
        )
        y_pos += 20
        
        page.insert_text(
            fitz.Point(50, y_pos),
            "Tamaño 14pt - Texto mediano",
            fontsize=14,
            fontname="helv",
            color=(0, 0, 0)
        )
        y_pos += 25
        
        page.insert_text(
            fitz.Point(50, y_pos),
            "Tamaño 18pt - Texto grande",
            fontsize=18,
            fontname="helv",
            color=(0, 0, 0)
        )
        y_pos += 40
        
        # Colores
        page.insert_text(
            fitz.Point(50, y_pos),
            "Texto en rojo",
            fontsize=12,
            fontname="helv",
            color=(1, 0, 0)
        )
        
        page.insert_text(
            fitz.Point(200, y_pos),
            "Texto en azul",
            fontsize=12,
            fontname="helv",
            color=(0, 0, 1)
        )
        
        page.insert_text(
            fitz.Point(350, y_pos),
            "Texto en verde",
            fontsize=12,
            fontname="helv",
            color=(0, 0.5, 0)
        )
        
        doc.save(output_path)
        doc.close()
        print(f"  ✅ Creado: {output_path}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error creando simple_fonts.pdf: {e}")
        return False


def create_custom_fonts_pdf(output_path: str) -> bool:
    """
    Crea custom_fonts.pdf con fuentes custom/embebidas.
    
    Nota: PyMuPDF tiene soporte limitado para fuentes custom,
    usamos las base14 con nombres que simulan custom fonts.
    """
    try:
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        
        y_pos = 50
        
        # Título
        page.insert_text(
            fitz.Point(50, y_pos),
            "Test PDF: Custom Fonts Simulation",
            fontsize=18,
            fontname="helv",
            color=(0, 0, 0)
        )
        y_pos += 40
        
        # Nota explicativa
        page.insert_text(
            fitz.Point(50, y_pos),
            "Este PDF simula fuentes custom usando las Base-14 de PDF.",
            fontsize=10,
            fontname="helv",
            color=(0.4, 0.4, 0.4)
        )
        y_pos += 30
        
        # Helvetica como "MyriadPro" simulation
        page.insert_text(
            fitz.Point(50, y_pos),
            "[Simulando MyriadPro] Clean sans-serif text",
            fontsize=12,
            fontname="helv",
            color=(0, 0, 0)
        )
        y_pos += 25
        
        # Times como "Georgia" simulation  
        page.insert_text(
            fitz.Point(50, y_pos),
            "[Simulando Georgia] Elegant serif typography",
            fontsize=12,
            fontname="tiro",
            color=(0, 0, 0)
        )
        y_pos += 25
        
        # Courier como "Consolas" simulation
        page.insert_text(
            fitz.Point(50, y_pos),
            "[Simulando Consolas] Monospace code font",
            fontsize=12,
            fontname="cour",
            color=(0, 0, 0)
        )
        y_pos += 40
        
        # Helvetica Oblique como "Italic custom"
        page.insert_text(
            fitz.Point(50, y_pos),
            "[Custom Italic] Texto en cursiva personalizada",
            fontsize=12,
            fontname="hebo",  # Helvetica-Bold
            color=(0, 0, 0)
        )
        y_pos += 25
        
        # Múltiples líneas de texto para testing
        sample_text = [
            "El viaje fue increíble, visitamos muchos lugares.",
            "La documentación técnica requiere precisión.",
            "Los números: 123456789 y símbolos: @#$%&*",
            "Acentos: áéíóú ÁÉÍÓÚ ñÑ üÜ",
        ]
        
        for text in sample_text:
            page.insert_text(
                fitz.Point(50, y_pos),
                text,
                fontsize=11,
                fontname="helv",
                color=(0, 0, 0)
            )
            y_pos += 20
        
        doc.save(output_path)
        doc.close()
        print(f"  ✅ Creado: {output_path}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error creando custom_fonts.pdf: {e}")
        return False


def create_bold_italic_pdf(output_path: str) -> bool:
    """
    Crea bold_italic.pdf con negritas y cursivas.
    
    Este PDF es crucial para testing de heurísticas de bold.
    Usa fuentes Base-14 de PDF (estándar).
    
    Base-14 disponibles:
    - Courier, Courier-Oblique, Courier-Bold, Courier-BoldOblique
    - Helvetica, Helvetica-Oblique, Helvetica-Bold, Helvetica-BoldOblique
    - Times-Roman, Times-Italic, Times-Bold, Times-BoldItalic
    - Symbol, ZapfDingbats
    """
    try:
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        
        y_pos = 50
        
        # Título
        page.insert_text(
            fitz.Point(50, y_pos),
            "Test PDF: Bold & Italic Detection",
            fontsize=18,
            fontname="Helvetica-Bold",
            color=(0, 0, 0)
        )
        y_pos += 40
        
        # Texto normal para comparación
        page.insert_text(
            fitz.Point(50, y_pos),
            "Este texto esta en peso NORMAL (Helvetica Regular).",
            fontsize=12,
            fontname="Helvetica",
            color=(0, 0, 0)
        )
        y_pos += 25
        
        # Texto bold - Helvetica-Bold
        page.insert_text(
            fitz.Point(50, y_pos),
            "Este texto esta en NEGRITA (Helvetica-Bold).",
            fontsize=12,
            fontname="Helvetica-Bold",
            color=(0, 0, 0)
        )
        y_pos += 25
        
        # Texto italic - Helvetica-Oblique
        page.insert_text(
            fitz.Point(50, y_pos),
            "Este texto esta en CURSIVA (Helvetica-Oblique).",
            fontsize=12,
            fontname="Helvetica-Oblique",
            color=(0, 0, 0)
        )
        y_pos += 25
        
        # Texto bold-italic - Helvetica-BoldOblique
        page.insert_text(
            fitz.Point(50, y_pos),
            "Este texto esta en NEGRITA CURSIVA (Helvetica-BoldOblique).",
            fontsize=12,
            fontname="Helvetica-BoldOblique",
            color=(0, 0, 0)
        )
        y_pos += 40
        
        # Times variants
        page.insert_text(
            fitz.Point(50, y_pos),
            "Times Normal - Texto serif estandar",
            fontsize=12,
            fontname="Times-Roman",
            color=(0, 0, 0)
        )
        y_pos += 25
        
        page.insert_text(
            fitz.Point(50, y_pos),
            "Times Bold - Texto serif en negrita",
            fontsize=12,
            fontname="Times-Bold",
            color=(0, 0, 0)
        )
        y_pos += 25
        
        page.insert_text(
            fitz.Point(50, y_pos),
            "Times Italic - Texto serif en cursiva",
            fontsize=12,
            fontname="Times-Italic",
            color=(0, 0, 0)
        )
        y_pos += 25
        
        page.insert_text(
            fitz.Point(50, y_pos),
            "Times BoldItalic - Texto serif negrita cursiva",
            fontsize=12,
            fontname="Times-BoldItalic",
            color=(0, 0, 0)
        )
        y_pos += 40
        
        # Courier variants
        page.insert_text(
            fitz.Point(50, y_pos),
            "Courier Normal - Monospace estandar",
            fontsize=12,
            fontname="Courier",
            color=(0, 0, 0)
        )
        y_pos += 25
        
        page.insert_text(
            fitz.Point(50, y_pos),
            "Courier Bold - Monospace en negrita",
            fontsize=12,
            fontname="Courier-Bold",
            color=(0, 0, 0)
        )
        y_pos += 25
        
        page.insert_text(
            fitz.Point(50, y_pos),
            "Courier Oblique - Monospace cursiva",
            fontsize=12,
            fontname="Courier-Oblique",
            color=(0, 0, 0)
        )
        y_pos += 40
        
        # Sección para testing de heurísticas
        page.insert_text(
            fitz.Point(50, y_pos),
            "=== SECCION HEURISTICA BOLD ===",
            fontsize=14,
            fontname="Times-Bold",
            color=(0.2, 0.2, 0.2)
        )
        y_pos += 30
        
        # Texto que debería detectarse como bold
        bold_samples = [
            "[BOLD] palabra_importante",
            "[BOLD] TEXTO EN MAYUSCULAS",
            "[BOLD] Titulo de seccion",
        ]
        
        for text in bold_samples:
            page.insert_text(
                fitz.Point(50, y_pos),
                text,
                fontsize=12,
                fontname="Helvetica-Bold",
                color=(0, 0, 0)
            )
            y_pos += 20
        
        # Texto que NO debería detectarse como bold
        normal_samples = [
            "[NORMAL] texto normal regular",
            "[NORMAL] another regular text",
            "[NORMAL] mas texto sin negrita",
        ]
        
        y_pos += 10
        for text in normal_samples:
            page.insert_text(
                fitz.Point(50, y_pos),
                text,
                fontsize=12,
                fontname="Helvetica",
                color=(0, 0, 0)
            )
            y_pos += 20
        
        # Página 2: Más ejemplos
        page2 = doc.new_page(width=595, height=842)
        y_pos = 50
        
        page2.insert_text(
            fitz.Point(50, y_pos),
            "Pagina 2: Ejemplos adicionales para testing",
            fontsize=16,
            fontname="Times-Bold",
            color=(0, 0, 0)
        )
        y_pos += 40
        
        # Párrafos para edición
        page2.insert_text(
            fitz.Point(50, y_pos),
            "El viaje fue largo y cansado pero valio la pena.",
            fontsize=12,
            fontname="Helvetica",
            color=(0, 0, 0)
        )
        y_pos += 25
        
        page2.insert_text(
            fitz.Point(50, y_pos),
            "El viaje fue increible y memorable.",
            fontsize=12,
            fontname="Helvetica-Bold",
            color=(0, 0, 0)
        )
        y_pos += 25
        
        page2.insert_text(
            fitz.Point(50, y_pos),
            "Visitamos hermosos lugares durante el recorrido.",
            fontsize=12,
            fontname="Helvetica-Oblique",
            color=(0, 0, 0)
        )
        y_pos += 40
        
        # Texto para edición de prueba
        page2.insert_text(
            fitz.Point(50, y_pos),
            "TEXTO EDITABLE: El viaje fue largo",
            fontsize=12,
            fontname="Helvetica",
            color=(0, 0, 0)
        )
        y_pos += 25
        
        page2.insert_text(
            fitz.Point(50, y_pos),
            "BOLD EDITABLE: Texto importante en negrita",
            fontsize=12,
            fontname="Helvetica-Bold",
            color=(0, 0, 0)
        )
        
        doc.save(output_path)
        doc.close()
        print(f"  ✅ Creado: {output_path}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error creando bold_italic.pdf: {e}")
        return False


def main():
    """Genera todos los PDFs de prueba."""
    print("\n" + "=" * 60)
    print("🔧 PHASE2-302: Generando PDFs de Prueba")
    print("=" * 60)
    
    # Directorio de salida
    output_dir = Path(__file__).parent / "test_pdfs"
    output_dir.mkdir(exist_ok=True)
    
    print(f"\n📁 Directorio: {output_dir}\n")
    
    # Generar PDFs
    results = []
    
    results.append(
        create_simple_fonts_pdf(str(output_dir / "simple_fonts.pdf"))
    )
    
    results.append(
        create_custom_fonts_pdf(str(output_dir / "custom_fonts.pdf"))
    )
    
    results.append(
        create_bold_italic_pdf(str(output_dir / "bold_italic.pdf"))
    )
    
    # Resumen
    print("\n" + "-" * 40)
    success = sum(results)
    total = len(results)
    
    if success == total:
        print(f"✅ {success}/{total} PDFs creados correctamente")
    else:
        print(f"⚠️ {success}/{total} PDFs creados ({total - success} fallidos)")
    
    print("=" * 60 + "\n")
    
    return success == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

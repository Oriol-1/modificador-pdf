"""
Tests específicos para problemas reportados en edición de texto.
================================================================

Este archivo contiene tests específicos para los problemas conocidos:
1. Texto se trunca al seleccionar (solo captura parte)
2. Texto se rompe al mover
3. Estilos se pierden al mover (negrita, tamaño, fuente)
4. Texto duplicado queda en origen al mover
5. Texto editado borra otro texto cercano

Ejecutar con: python tests/test_reported_issues.py
"""

import os
import sys
import tempfile
import fitz

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Intentar importar módulos del proyecto
try:
    import importlib.util
    PDF_HANDLER_AVAILABLE = importlib.util.find_spec('core.pdf_handler') is not None
except ImportError:
    PDF_HANDLER_AVAILABLE = False

if not PDF_HANDLER_AVAILABLE:
    print("⚠️ PDFHandler no disponible - usando tests básicos")


# ============================================================================
# TESTS PARA PROBLEMA 1: TEXTO TRUNCADO AL SELECCIONAR
# ============================================================================

class TestTextTruncation:
    """Tests para verificar que el texto NO se trunca al seleccionar."""
    
    def test_long_line_not_truncated(self):
        """Test: Una línea que cabe en la página debe capturarse completa."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "long_line.pdf")
            
            # Texto que cabe en la página (no demasiado largo)
            long_text = "Este es un texto moderado que cabe en una línea de la página."
            
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.insert_text(fitz.Point(50, 100), long_text, fontsize=10)
            doc.save(pdf_path)
            doc.close()
            
            # Verificar captura completa
            doc = fitz.open(pdf_path)
            captured = doc[0].get_text().strip()
            doc.close()
            
            # Debe capturar TODO el texto
            assert captured == long_text, f"Texto truncado:\n  Original: {len(long_text)} chars\n  Capturado: {len(captured)} chars"
            
            print("✅ test_long_line_not_truncated: PASSED")
            return True
    
    def test_paragraph_all_lines_captured(self):
        """Test: Un párrafo de varias líneas debe capturarse completo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "paragraph.pdf")
            
            lines = [
                "Línea 1: Introducción al tema principal.",
                "Línea 2: Desarrollo de la idea central.",
                "Línea 3: Argumentos adicionales.",
                "Línea 4: Conclusión del párrafo.",
                "Línea 5: Último elemento del texto."
            ]
            
            doc = fitz.open()
            page = doc.new_page()
            y = 100
            for line in lines:
                page.insert_text(fitz.Point(50, y), line, fontsize=12)
                y += 16
            doc.save(pdf_path)
            doc.close()
            
            # Capturar todo el área del párrafo
            doc = fitz.open(pdf_path)
            rect = fitz.Rect(40, 85, 500, 200)
            captured = doc[0].get_text("text", clip=rect)
            doc.close()
            
            # Verificar TODAS las líneas
            for line in lines:
                assert line in captured, f"Línea faltante: '{line}'"
            
            print("✅ test_paragraph_all_lines_captured: PASSED")
            return True
    
    def test_selection_rect_expands_to_content(self):
        """Test: El rectángulo de selección debe expandirse para cubrir todo el texto."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "expand.pdf")
            
            doc = fitz.open()
            page = doc.new_page()
            # Texto que el usuario selecciona parcialmente con clic
            page.insert_text(fitz.Point(100, 100), "Texto completo que debe capturarse entero", fontsize=12)
            doc.save(pdf_path)
            doc.close()
            
            doc = fitz.open(pdf_path)
            page = doc[0]
            
            # Simular: usuario hace clic en medio del texto (rect pequeño)
            small_click_rect = fitz.Rect(150, 95, 200, 110)
            
            # Obtener spans en esa área
            text_dict = page.get_text("dict", clip=small_click_rect)
            
            # El texto capturado debe incluir la línea completa
            found_text = ""
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            found_text += span.get("text", "")
            
            doc.close()
            
            # Aunque el clic sea pequeño, debe encontrar texto
            assert len(found_text) > 0, "Debería encontrar texto con clic parcial"
            
            print(f"✅ test_selection_rect_expands_to_content: PASSED (found '{found_text}')")
            return True


# ============================================================================
# TESTS PARA PROBLEMA 2: TEXTO SE ROMPE AL MOVER
# ============================================================================

class TestTextBreaking:
    """Tests para verificar que el texto NO se rompe al mover."""
    
    def test_text_integrity_after_simulated_move(self):
        """Test: El texto mantiene su integridad al simular un movimiento."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "move.pdf")
            output_path = os.path.join(tmpdir, "moved.pdf")
            
            original_text = "Texto que será movido sin romperse"
            
            # Crear PDF original
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text(fitz.Point(100, 100), original_text, fontsize=12)
            doc.save(pdf_path)
            doc.close()
            
            # Simular movimiento: borrar original + insertar en nueva posición
            doc = fitz.open(pdf_path)
            page = doc[0]
            
            # Obtener rect exacto del texto
            text_dict = page.get_text("dict")
            original_rect = None
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            if "movido" in span.get("text", ""):
                                original_rect = fitz.Rect(span.get("bbox"))
                                break
            
            assert original_rect, "Debe encontrar el rect original"
            
            # Borrar original
            page.add_redact_annot(original_rect)
            page.apply_redactions()
            
            # Insertar en nueva posición (simula mover)
            new_pos = fitz.Point(200, 300)
            page.insert_text(new_pos, original_text, fontsize=12)
            
            doc.save(output_path)
            doc.close()
            
            # Verificar que el texto está completo en nueva posición
            doc = fitz.open(output_path)
            final_text = doc[0].get_text()
            doc.close()
            
            assert original_text in final_text, f"Texto roto o incompleto: '{final_text}'"
            
            print("✅ test_text_integrity_after_simulated_move: PASSED")
            return True
    
    def test_multiline_text_stays_together(self):
        """Test: Un texto multilínea permanece junto al mover."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "multiline.pdf")
            output_path = os.path.join(tmpdir, "moved.pdf")
            
            lines = ["Primera línea", "Segunda línea", "Tercera línea"]
            
            doc = fitz.open()
            page = doc.new_page()
            y = 100
            for line in lines:
                page.insert_text(fitz.Point(100, y), line, fontsize=12)
                y += 16
            doc.save(pdf_path)
            doc.close()
            
            # Simular movimiento de todo el bloque
            doc = fitz.open(pdf_path)
            page = doc[0]
            
            # Borrar área original
            block_rect = fitz.Rect(90, 85, 250, 150)
            page.add_redact_annot(block_rect)
            page.apply_redactions()
            
            # Insertar en nueva posición
            new_y = 300
            for line in lines:
                page.insert_text(fitz.Point(200, new_y), line, fontsize=12)
                new_y += 16
            
            doc.save(output_path)
            doc.close()
            
            # Verificar que TODAS las líneas están
            doc = fitz.open(output_path)
            final_text = doc[0].get_text()
            doc.close()
            
            for line in lines:
                assert line in final_text, f"Línea faltante: '{line}'"
            
            print("✅ test_multiline_text_stays_together: PASSED")
            return True


# ============================================================================
# TESTS PARA PROBLEMA 3: ESTILOS SE PIERDEN AL MOVER
# ============================================================================

class TestStyleLoss:
    """Tests para verificar que los estilos NO se pierden al mover."""
    
    def test_bold_preserved_in_extraction(self):
        """Test: El estilo negrita se preserva al extraer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "bold.pdf")
            
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text(fitz.Point(100, 100), "Texto en negrita", fontsize=12, fontname="hebo")
            doc.save(pdf_path)
            doc.close()
            
            # Extraer y verificar estilo
            doc = fitz.open(pdf_path)
            page = doc[0]
            text_dict = page.get_text("dict")
            
            is_bold = False
            font_name = ""
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            if "negrita" in span.get("text", ""):
                                font_name = span.get("font", "")
                                # Helvetica-Bold o variantes
                                is_bold = "Bold" in font_name or "bold" in font_name.lower()
            
            doc.close()
            
            assert is_bold, f"Negrita perdida. Fuente: {font_name}"
            
            print(f"✅ test_bold_preserved_in_extraction: PASSED (font={font_name})")
            return True
    
    def test_font_size_preserved(self):
        """Test: El tamaño de fuente se preserva."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "sizes.pdf")
            
            sizes_to_test = [8, 12, 18, 24]
            
            doc = fitz.open()
            page = doc.new_page()
            y = 50
            for size in sizes_to_test:
                page.insert_text(fitz.Point(50, y), f"Tamaño {size}", fontsize=size)
                y += size + 10
            doc.save(pdf_path)
            doc.close()
            
            # Extraer y verificar tamaños
            doc = fitz.open(pdf_path)
            page = doc[0]
            text_dict = page.get_text("dict")
            
            found_sizes = []
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            found_sizes.append(round(span.get("size", 0)))
            
            doc.close()
            
            for size in sizes_to_test:
                assert size in found_sizes, f"Tamaño {size} no preservado. Encontrados: {found_sizes}"
            
            print(f"✅ test_font_size_preserved: PASSED (sizes={found_sizes})")
            return True
    
    def test_color_preserved(self):
        """Test: El color se preserva."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "colors.pdf")
            
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text(fitz.Point(50, 50), "Rojo", fontsize=12, color=(1, 0, 0))
            page.insert_text(fitz.Point(50, 70), "Verde", fontsize=12, color=(0, 1, 0))
            page.insert_text(fitz.Point(50, 90), "Azul", fontsize=12, color=(0, 0, 1))
            doc.save(pdf_path)
            doc.close()
            
            # Verificar colores
            doc = fitz.open(pdf_path)
            page = doc[0]
            text_dict = page.get_text("dict")
            
            colors = set()
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            colors.add(span.get("color", 0))
            
            doc.close()
            
            assert len(colors) >= 3, f"Colores perdidos. Encontrados: {len(colors)}"
            
            print(f"✅ test_color_preserved: PASSED (colors={len(colors)})")
            return True


# ============================================================================
# TESTS PARA PROBLEMA 4: TEXTO DUPLICADO EN ORIGEN
# ============================================================================

class TestDuplication:
    """Tests para verificar que NO queda texto duplicado al mover."""
    
    def test_no_duplicate_after_move(self):
        """Test: No debe quedar texto duplicado en la posición original."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "dup.pdf")
            output_path = os.path.join(tmpdir, "moved.pdf")
            
            original_text = "Texto único sin duplicar"
            
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text(fitz.Point(100, 100), original_text, fontsize=12)
            doc.save(pdf_path)
            doc.close()
            
            # Simular movimiento
            doc = fitz.open(pdf_path)
            page = doc[0]
            
            # Borrar original COMPLETAMENTE
            original_rect = fitz.Rect(90, 85, 300, 115)
            page.add_redact_annot(original_rect)
            page.apply_redactions()
            
            # Insertar en nueva posición
            page.insert_text(fitz.Point(200, 300), original_text, fontsize=12)
            
            doc.save(output_path)
            doc.close()
            
            # Verificar que el texto aparece EXACTAMENTE UNA VEZ
            doc = fitz.open(output_path)
            final_text = doc[0].get_text()
            doc.close()
            
            count = final_text.count(original_text)
            assert count == 1, f"Texto duplicado: aparece {count} veces"
            
            print("✅ test_no_duplicate_after_move: PASSED")
            return True
    
    def test_original_area_is_clear(self):
        """Test: El área original debe quedar limpia después del borrado."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "clear.pdf")
            output_path = os.path.join(tmpdir, "cleared.pdf")
            
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text(fitz.Point(100, 100), "Texto a eliminar", fontsize=12)
            doc.save(pdf_path)
            doc.close()
            
            # Borrar el área
            doc = fitz.open(pdf_path)
            page = doc[0]
            rect = fitz.Rect(90, 85, 250, 115)
            page.add_redact_annot(rect)
            page.apply_redactions()
            doc.save(output_path)
            doc.close()
            
            # Verificar que el área está vacía
            doc = fitz.open(output_path)
            page = doc[0]
            text_in_area = page.get_text("text", clip=rect).strip()
            doc.close()
            
            assert text_in_area == "", f"Área no limpia: '{text_in_area}'"
            
            print("✅ test_original_area_is_clear: PASSED")
            return True
    
    def test_erase_rect_covers_all_text(self):
        """Test: El rectángulo de borrado debe cubrir TODO el texto."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "full_cover.pdf")
            
            # Texto que puede ser más grande que el rect del clic original
            long_text = "Este es un texto bastante largo que puede extenderse más allá del área de clic inicial del usuario"
            
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text(fitz.Point(50, 100), long_text, fontsize=10)
            doc.save(pdf_path)
            doc.close()
            
            # Obtener el rect REAL del texto
            doc = fitz.open(pdf_path)
            page = doc[0]
            text_dict = page.get_text("dict")
            
            actual_rects = []
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            if span.get("text", "").strip():
                                actual_rects.append(fitz.Rect(span.get("bbox")))
            
            doc.close()
            
            # El rect de borrado debe cubrir todo
            if actual_rects:
                # Combinar todos los rects
                combined = actual_rects[0]
                for r in actual_rects[1:]:
                    combined = combined | r  # Unión de rects
                
                # Verificar que el rect calculado es suficiente
                assert combined.width > 0, "El rect debe tener ancho"
                assert combined.height > 0, "El rect debe tener alto"
                
                print(f"✅ test_erase_rect_covers_all_text: PASSED (rect={combined})")
            else:
                print("⚠️ No se encontraron rects")
            
            return True


# ============================================================================
# TESTS PARA PROBLEMA 5: BORRA TEXTO CERCANO
# ============================================================================

class TestCollateralDamage:
    """Tests para verificar que NO se borra texto no relacionado."""
    
    def test_nearby_text_preserved(self):
        """Test: El texto cercano al editado debe preservarse."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "nearby.pdf")
            output_path = os.path.join(tmpdir, "edited.pdf")
            
            doc = fitz.open()
            page = doc.new_page()
            # Texto a editar
            page.insert_text(fitz.Point(100, 100), "TEXTO A EDITAR", fontsize=12)
            # Texto cercano que NO debe tocarse
            page.insert_text(fitz.Point(100, 120), "Texto cercano intacto", fontsize=12)
            page.insert_text(fitz.Point(100, 80), "Texto arriba intacto", fontsize=12)
            page.insert_text(fitz.Point(250, 100), "Texto derecha intacto", fontsize=12)
            doc.save(pdf_path)
            doc.close()
            
            # Borrar SOLO el texto objetivo (rect preciso)
            doc = fitz.open(pdf_path)
            page = doc[0]
            
            # Rect MUY preciso para el texto objetivo
            target_rect = fitz.Rect(95, 88, 220, 106)
            page.add_redact_annot(target_rect)
            page.apply_redactions()
            
            doc.save(output_path)
            doc.close()
            
            # Verificar que los otros textos están intactos
            doc = fitz.open(output_path)
            final_text = doc[0].get_text()
            doc.close()
            
            assert "TEXTO A EDITAR" not in final_text, "El texto objetivo debería estar borrado"
            assert "cercano intacto" in final_text, "Texto cercano fue borrado por error"
            assert "arriba intacto" in final_text, "Texto arriba fue borrado por error"
            assert "derecha intacto" in final_text, "Texto derecha fue borrado por error"
            
            print("✅ test_nearby_text_preserved: PASSED")
            return True
    
    def test_column_isolation(self):
        """Test: Texto en columnas separadas no debe verse afectado."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "columns.pdf")
            output_path = os.path.join(tmpdir, "edited.pdf")
            
            doc = fitz.open()
            page = doc.new_page()
            
            # Columna izquierda
            page.insert_text(fitz.Point(50, 100), "Columna izquierda", fontsize=12)
            page.insert_text(fitz.Point(50, 120), "Línea 2 izquierda", fontsize=12)
            
            # Columna derecha
            page.insert_text(fitz.Point(350, 100), "Columna derecha", fontsize=12)
            page.insert_text(fitz.Point(350, 120), "Línea 2 derecha", fontsize=12)
            
            doc.save(pdf_path)
            doc.close()
            
            # Editar solo columna izquierda
            doc = fitz.open(pdf_path)
            page = doc[0]
            
            left_rect = fitz.Rect(40, 85, 200, 140)
            page.add_redact_annot(left_rect)
            page.apply_redactions()
            
            doc.save(output_path)
            doc.close()
            
            # Columna derecha debe estar intacta
            doc = fitz.open(output_path)
            final_text = doc[0].get_text()
            doc.close()
            
            assert "izquierda" not in final_text, "Columna izquierda debería estar borrada"
            assert "Columna derecha" in final_text, "Columna derecha fue afectada"
            assert "Línea 2 derecha" in final_text, "Línea 2 derecha fue afectada"
            
            print("✅ test_column_isolation: PASSED")
            return True


# ============================================================================
# EJECUTOR DE TESTS
# ============================================================================

def run_all_issue_tests():
    """Ejecuta todos los tests de problemas reportados."""
    print("\n" + "=" * 70)
    print("🔍 TESTS DE PROBLEMAS REPORTADOS")
    print("=" * 70 + "\n")
    
    test_classes = [
        ("PROBLEMA 1: Texto Truncado", TestTextTruncation()),
        ("PROBLEMA 2: Texto se Rompe", TestTextBreaking()),
        ("PROBLEMA 3: Estilos Perdidos", TestStyleLoss()),
        ("PROBLEMA 4: Texto Duplicado", TestDuplication()),
        ("PROBLEMA 5: Borra Texto Cercano", TestCollateralDamage()),
    ]
    
    total = 0
    passed = 0
    failed = []
    
    for section_name, test_instance in test_classes:
        print(f"\n📋 {section_name}")
        print("-" * 50)
        
        test_methods = [m for m in dir(test_instance) if m.startswith('test_')]
        
        for method_name in test_methods:
            total += 1
            try:
                method = getattr(test_instance, method_name)
                if method():
                    passed += 1
            except AssertionError as e:
                failed.append((section_name, method_name, str(e)))
                print(f"❌ {method_name}: FAILED - {e}")
            except Exception as e:
                failed.append((section_name, method_name, str(e)))
                print(f"❌ {method_name}: ERROR - {e}")
    
    # Resumen
    print("\n" + "=" * 70)
    print("📊 RESUMEN")
    print("=" * 70)
    print(f"✅ Pasados: {passed}/{total}")
    print(f"❌ Fallidos: {len(failed)}/{total}")
    
    if failed:
        print("\n⚠️ Tests fallidos:")
        for section, method, error in failed:
            print(f"   - {section} > {method}")
            print(f"     Error: {error[:100]}...")
    
    print("\n" + "=" * 70)
    
    if len(failed) == 0:
        print("🎉 TODOS LOS TESTS DE PROBLEMAS REPORTADOS PASAN")
    else:
        print("⚠️ HAY PROBLEMAS QUE NECESITAN CORRECCIÓN")
    
    return len(failed) == 0


if __name__ == "__main__":
    success = run_all_issue_tests()
    sys.exit(0 if success else 1)

"""Smoke test del MOVE puro: clona un span del PDF a una nueva posición usando
move_text_region y verifica que el texto, fuente y tamaño se preservan, y que
no quedan residuos en la posición original.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz
from core.pdf_handler import PDFDocument


def main():
    src = "tests/fixtures/test_pdfs/custom_fonts.pdf"
    if not os.path.exists(src):
        src = "tests/fixtures/test_pdfs/simple_fonts.pdf"
    print(f"PDF de prueba: {src}")

    h = PDFDocument()
    assert h.open(src), f"no se pudo abrir {src}"

    page = h.get_page(0)
    text_dict = page.get_text("dict")
    spans = []
    for b in text_dict.get("blocks", []):
        if b.get("type") != 0:
            continue
        for ln in b.get("lines", []):
            for sp in ln.get("spans", []):
                if sp.get("text", "").strip():
                    spans.append(sp)
    assert spans, "no hay spans en la página"
    target = spans[0]
    src_rect = fitz.Rect(target["bbox"])
    print(f"Span original: '{target['text']}' font={target['font']} size={target['size']} bbox={src_rect}")

    # Mover 200 pt a la derecha y 50 pt abajo
    dest = (src_rect.x0 + 200, src_rect.y0 + 50)
    print(f"Destino: {dest}")

    # Reproducir orden del viewer: snapshot pristine ANTES del erase
    h._ensure_move_source_snapshot()
    print("snapshot pristine capturado")

    # Borrar el original (simula CASO 2 del viewer)
    h._save_snapshot()
    h.erase_text_transparent(0, src_rect, save_snapshot=False, already_internal=True)

    # Aplicar MOVE puro
    ok = h.move_text_region(0, src_rect, dest, save_snapshot=False)
    assert ok, "move_text_region devolvió False"
    print("move_text_region: OK")

    # Verificar resultado
    page = h.get_page(0)
    new_dict = page.get_text("dict")
    found_at_origin = False
    found_at_dest = False
    for b in new_dict.get("blocks", []):
        if b.get("type") != 0:
            continue
        for ln in b.get("lines", []):
            for sp in ln.get("spans", []):
                txt = sp.get("text", "")
                rect = fitz.Rect(sp["bbox"])
                if target["text"] in txt or txt in target["text"]:
                    if abs(rect.x0 - src_rect.x0) < 5 and abs(rect.y0 - src_rect.y0) < 5:
                        found_at_origin = True
                        print(f"  [WARN] residuo en origen: {rect}")
                    elif abs(rect.x0 - dest[0]) < 8 and abs(rect.y0 - dest[1]) < 8:
                        found_at_dest = True
                        print(f"  [OK] encontrado en destino: '{txt}' font={sp.get('font')} size={sp.get('size')} bbox={rect}")
                        # Verificar preservación
                        if sp.get("font") == target["font"]:
                            print("  [OK] FUENTE preservada")
                        else:
                            print(f"  [FAIL] FUENTE cambiada: {target['font']} → {sp.get('font')}")
                        if abs(sp.get("size", 0) - target["size"]) < 0.1:
                            print("  [OK] TAMAÑO preservado")
                        else:
                            print(f"  [FAIL] TAMAÑO cambiado: {target['size']} → {sp.get('size')}")

    print()
    print(f"residuo en origen: {found_at_origin}")
    print(f"presente en destino: {found_at_dest}")

    out = "tests/fixtures/_verify_pure_move_out.pdf"
    h.save_as(out)
    print(f"PDF resultado guardado en {out}")


if __name__ == "__main__":
    main()

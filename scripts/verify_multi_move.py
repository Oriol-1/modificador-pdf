"""Reproduce el escenario reportado: mover varios textos, guardar y reabrir.
Detecta campos fantasma, duplicados o invisibles en el PDF resultante."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QRectF
from core.pdf_handler import PDFDocument


def main():
    app = QApplication.instance() or QApplication([])
    src = "tests/fixtures/test_pdfs/custom_fonts.pdf"
    out = "tests/fixtures/_multi_move_out.pdf"
    if os.path.exists(out):
        os.remove(out)

    h = PDFDocument()
    assert h.open(src), "no se pudo abrir"
    from ui.pdf_viewer import PDFPageView
    v = PDFPageView()
    v.zoom_level = 1.0
    v.current_page = 0
    v.tool_mode = "edit"
    v.pdf_doc = h
    v.render_page()

    # Coger varios spans para mover
    page = h.get_page(0)
    text_dict = page.get_text("dict")
    spans = []
    for b in text_dict.get("blocks", []):
        if b.get("type") != 0: continue
        for ln in b.get("lines", []):
            for sp in ln.get("spans", []):
                if sp.get("text", "").strip():
                    spans.append(sp)
    if len(spans) < 3:
        print("no hay 3 spans"); return

    # Mover los 3 primeros spans (cada uno 100pt a la derecha)
    targets = spans[:3]
    for i, target in enumerate(targets):
        src_rect = fitz.Rect(target["bbox"])
        click_pt = (src_rect.x0 + 5, src_rect.y0 + 5)
        block = h.find_text_at_point(0, click_pt)
        if not block:
            print(f"#{i}: no se encontro span"); continue
        item = v._materialize_pdf_text_as_overlay(block)
        if not item:
            print(f"#{i}: no se materializo"); continue
        page_data = v.editable_texts_data[v._current_page_key()]
        # Mover 150pt a la derecha
        dest = fitz.Rect(src_rect.x0 + 150, src_rect.y0,
                         src_rect.x0 + 150 + src_rect.width, src_rect.y1)
        page_data[-1]['pdf_rect'] = dest
        page_data[-1]['is_overlay'] = True
        page_data[-1]['pending_write'] = True
        page_data[-1]['needs_erase'] = False
        # CASO 2: borrar original
        h._save_snapshot()
        h.erase_text_transparent(0, src_rect, save_snapshot=False, already_internal=True)
        print(f"#{i}: '{target['text'][:40]}' movido a {dest}")

    # Commit
    print("\n--- COMMIT ---")
    res = v.commit_overlay_texts()
    print(f"commit: {res}")

    # Save
    print("\n--- SAVE ---")
    h.save_as(out)
    print(f"size: {os.path.getsize(out)} bytes")

    # Reabrir y auditar
    print("\n--- AUDIT REOPENED ---")
    doc = fitz.open(out)
    page = doc[0]
    blocks = []
    for b in page.get_text("dict").get("blocks", []):
        if b.get("type") != 0: continue
        for ln in b.get("lines", []):
            for sp in ln.get("spans", []):
                blocks.append((sp.get("bbox"), sp.get("text", "")))
    print(f"\nTotal spans: {len(blocks)}")
    seen_texts = {}
    for bbox, txt in blocks:
        seen_texts.setdefault(txt, []).append(bbox)
    for txt, bboxes in seen_texts.items():
        if len(bboxes) > 1:
            print(f"  DUP '{txt[:40]}': aparece {len(bboxes)} veces:")
            for bb in bboxes:
                print(f"    bbox={bb}")
        elif not txt.strip():
            print(f"  EMPTY span at {bboxes[0]}")

    # Render visual
    pix = page.get_pixmap(dpi=72)
    pix.save("tests/fixtures/_multi_move_out.png")
    print(f"\nrender saved")


if __name__ == "__main__":
    main()

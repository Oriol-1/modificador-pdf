"""Reproduce el flujo: open -> materializar -> mover -> commit -> save -> reopen.
Verifica que el PDF guardado contiene los cambios.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QPointF, QRectF
from core.pdf_handler import PDFDocument


def main():
    app = QApplication.instance() or QApplication([])
    src = "tests/fixtures/test_pdfs/custom_fonts.pdf"
    out = "tests/fixtures/_verify_save_out.pdf"
    if os.path.exists(out):
        os.remove(out)

    print("=== TEST: open ===")
    h = PDFDocument()
    assert h.open(src), "no se pudo abrir"

    # Importar el viewer (necesita app de Qt)
    from ui.pdf_viewer import PDFPageView
    v = PDFPageView()
    v.zoom_level = 1.0
    v.current_page = 0
    v.tool_mode = "edit"
    v.pdf_doc = h

    # Renderizar la pagina
    v.render_page()

    # Buscar un span del PDF para mover
    page = h.get_page(0)
    text_dict = page.get_text("dict")
    target_span = None
    for b in text_dict.get("blocks", []):
        if b.get("type") != 0:
            continue
        for ln in b.get("lines", []):
            for sp in ln.get("spans", []):
                if sp.get("text", "").strip():
                    target_span = sp
                    break
            if target_span:
                break
        if target_span:
            break
    assert target_span, "no hay spans"
    src_rect = fitz.Rect(target_span["bbox"])
    print(f"target span: '{target_span['text']}' at {src_rect}")

    # Materializar via la API real del viewer
    print("\n=== TEST: materialize ===")
    block = h.find_text_at_point(0, (src_rect.x0 + 5, src_rect.y0 + 5))
    assert block is not None, "find_text_at_point devolvió None"
    print(f"block: '{block.text}' rect={block.rect} internal_rect={getattr(block, 'internal_rect', None)}")

    item = v._materialize_pdf_text_as_overlay(block)
    assert item is not None, "_materialize_pdf_text_as_overlay devolvió None"
    print(f"item: text='{item.text}' is_overlay={item.is_overlay} needs_erase={item.needs_erase}")

    # Verificar que move_only=True está en data
    page_data = v.editable_texts_data[v._current_page_key()]
    print(f"data: move_only={page_data[-1].get('move_only')}, source_rect={page_data[-1].get('source_rect_internal')}")
    assert page_data[-1].get('move_only') is True, "move_only no se marcó"

    # Simular el movimiento: actualizar pdf_rect del data al destino
    new_rect = QRectF(src_rect.x0 + 200, src_rect.y0 + 50, src_rect.width, src_rect.height)
    page_data[-1]['pdf_rect'] = fitz.Rect(new_rect.x(), new_rect.y(),
                                           new_rect.x() + new_rect.width(),
                                           new_rect.y() + new_rect.height())
    page_data[-1]['is_overlay'] = True
    page_data[-1]['pending_write'] = True
    page_data[-1]['needs_erase'] = False
    print(f"\n=== TEST: data tras simulación de move ===")
    print(f"  pdf_rect={page_data[-1]['pdf_rect']}")
    print(f"  text='{page_data[-1]['text']}'")
    print(f"  original_text='{page_data[-1].get('original_text')}'")

    # Borrar el original (esto haría CASO 2)
    h._save_snapshot()
    h.erase_text_transparent(0, src_rect, save_snapshot=False, already_internal=True)
    print("erase original: OK")

    # Commit
    print("\n=== TEST: commit_overlay_texts ===")
    result = v.commit_overlay_texts()
    print(f"commit result: {result}")

    # Save
    print("\n=== TEST: save ===")
    saved = h.save_as(out)
    print(f"save result: {saved}")
    print(f"file exists: {os.path.exists(out)}")
    if os.path.exists(out):
        print(f"file size: {os.path.getsize(out)} bytes")

    # Reabrir y verificar
    print("\n=== TEST: reopen ===")
    h2 = PDFDocument()
    assert h2.open(out), "no se pudo reabrir"
    page2 = h2.get_page(0)
    pix = page2.get_pixmap(dpi=72)
    pix.save("tests/fixtures/_verify_save_out.png")
    print("rendered to tests/fixtures/_verify_save_out.png")

    # Buscar texto en destino
    text2 = page2.get_text("text")
    print(f"\nTexto presente tras reabrir:")
    for line in text2.split("\n")[:5]:
        if line.strip():
            print(f"  | {line}")


if __name__ == "__main__":
    main()

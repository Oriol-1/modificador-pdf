"""Tests de integración: persistencia del MOVE de overlays editables.

Valida que el flujo completo (crear overlay → mover → commit → guardar →
reabrir) conserva exactamente la nueva posición y el contenido del texto.

NO usa interacción de ratón: orquestra directamente las estructuras
internas (`editable_texts_data` + `commit_overlay_texts`) que el flujo de
arrastre alimenta.
"""

import os
import tempfile
from typing import Tuple

import fitz
import pytest
from PyQt5.QtCore import QRectF
from PyQt5.QtWidgets import QApplication

from core.pdf_handler import PDFDocument
from ui.pdf_viewer import PDFPageView


@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture
def blank_pdf_path():
    """Crea un PDF temporal en blanco (1 página tamaño Letter)."""
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    doc = fitz.open()
    doc.new_page(width=612, height=792)
    doc.save(path)
    doc.close()
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


def _open_pdf(path: str) -> PDFDocument:
    pdf = PDFDocument()
    assert pdf.open(path), f"No se pudo abrir {path}"
    return pdf


def _seed_overlay(viewer: PDFPageView, text: str, rect: fitz.Rect,
                  font_size: float = 14.0,
                  color: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                  original_rect: fitz.Rect = None) -> dict:
    """Inserta un overlay pendiente de escribir en `editable_texts_data`."""
    data = {
        "text": text,
        "font_size": font_size,
        "font_name": "helv",
        "is_bold": False,
        "color": color,
        "pdf_rect": fitz.Rect(rect),
        "view_rect": QRectF(rect.x0, rect.y0, rect.width, rect.height),
        "original_pdf_rect": fitz.Rect(original_rect) if original_rect else None,
        "internal_pdf_rect": None,
        "needs_erase": False,
        "is_overlay": True,
        "pending_write": True,
        "text_runs": None,
        "has_mixed_styles": False,
        "line_spacing": 0.0,
    }
    page_data = viewer.editable_texts_data.setdefault(viewer._current_page_key(), [])
    page_data.append(data)
    return data


def _text_in_rect(pdf_path: str, page_num: int, rect: fitz.Rect, expected: str) -> bool:
    """¿Aparece `expected` dentro (o cerca) de `rect` en la página?"""
    doc = fitz.open(pdf_path)
    try:
        page = doc[page_num]
        # clip un poco mayor para tolerar redondeos
        clip = fitz.Rect(rect.x0 - 5, rect.y0 - 5, rect.x1 + 50, rect.y1 + 20)
        text = page.get_text("text", clip=clip)
    finally:
        doc.close()
    return expected in text


class TestMovePersistence:
    """Persistencia tras commit + save + reopen."""

    def test_overlay_se_escribe_en_su_pdf_rect(self, blank_pdf_path):
        pdf_doc = _open_pdf(blank_pdf_path)
        viewer = PDFPageView()
        viewer.pdf_doc = pdf_doc
        viewer.current_page = 0

        rect_a = fitz.Rect(100, 100, 300, 130)
        _seed_overlay(viewer, "TEXTO_ORIGINAL", rect_a)

        assert viewer.commit_overlay_texts() is True

        # Guardar a un path nuevo y reabrir.
        out_path = blank_pdf_path + ".out.pdf"
        try:
            assert pdf_doc.save_as(out_path) is True
            assert _text_in_rect(out_path, 0, rect_a, "TEXTO_ORIGINAL")
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

    def test_mover_overlay_persiste_en_nueva_posicion(self, blank_pdf_path):
        """Crear overlay → commit → guardar → reabrir → mover → commit → guardar → reabrir.

        Tras el segundo guardado, el texto debe aparecer en la nueva posición y
        NO en la original.
        """
        # --- 1) Crear y commitear el overlay en posición A.
        pdf_doc = _open_pdf(blank_pdf_path)
        viewer = PDFPageView()
        viewer.pdf_doc = pdf_doc
        viewer.current_page = 0

        rect_a = fitz.Rect(80, 100, 280, 128)
        data = _seed_overlay(viewer, "MOVEME", rect_a)
        assert viewer.commit_overlay_texts() is True

        path_a = blank_pdf_path + ".a.pdf"
        path_b = blank_pdf_path + ".b.pdf"
        try:
            assert pdf_doc.save_as(path_a) is True
            assert _text_in_rect(path_a, 0, rect_a, "MOVEME"), \
                "El overlay debe haberse escrito en la posición original"

            # --- 2) Reabrir y simular MOVE: nueva pdf_rect, pending_write=True,
            # original_pdf_rect = posición previa (= internal tras commit).
            pdf_doc2 = _open_pdf(path_a)
            viewer2 = PDFPageView()
            viewer2.pdf_doc = pdf_doc2
            viewer2.current_page = 0

            rect_b = fitz.Rect(80, 400, 280, 428)  # mismo tamaño, otra Y
            data2 = _seed_overlay(
                viewer2, "MOVEME", rect_b,
                original_rect=rect_a,  # cubrir la posición previa
            )
            # Marcar como overlay nuevo pendiente que debe borrar el rastro previo.
            assert viewer2.commit_overlay_texts() is True
            assert pdf_doc2.save_as(path_b) is True

            # --- 3) Verificar resultado final.
            assert _text_in_rect(path_b, 0, rect_b, "MOVEME"), \
                "El texto movido debe estar en la nueva posición"
            # La posición original debe estar limpia (commit_overlay_texts borra
            # original_pdf_rect antes de escribir).
            assert not _text_in_rect(path_b, 0, rect_a, "MOVEME"), \
                "El texto NO debe seguir apareciendo en la posición original"
        finally:
            for p in (path_a, path_b):
                if os.path.exists(p):
                    os.remove(p)

    def test_dimensiones_se_preservan_tras_move(self, blank_pdf_path):
        """El ancho/alto del pdf_rect tras commit no debe cambiar respecto al solicitado."""
        pdf_doc = _open_pdf(blank_pdf_path)
        viewer = PDFPageView()
        viewer.pdf_doc = pdf_doc
        viewer.current_page = 0

        rect_a = fitz.Rect(50, 50, 250, 78)
        data = _seed_overlay(viewer, "DIMS", rect_a)
        assert viewer.commit_overlay_texts() is True

        # internal_pdf_rect debe coincidir con pdf_rect (sin recálculos).
        assert data["internal_pdf_rect"] is not None
        assert abs(data["internal_pdf_rect"].width - rect_a.width) < 0.01
        assert abs(data["internal_pdf_rect"].height - rect_a.height) < 0.01

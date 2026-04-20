"""Servicio de impresión: renderiza el PDF en memoria a un QPrinter."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QImage


def print_document(pdf_doc, printer):
    """Imprime el documento `pdf_doc` (PDFDocument) en `printer` (QPrinter).

    Respeta el rango de páginas y número de copias elegidos en QPrintDialog.
    Renderiza cada página vía PyMuPDF a un QImage y lo escala al área imprimible.
    """
    if not pdf_doc or not pdf_doc.is_open():
        raise RuntimeError("No hay documento abierto para imprimir")

    fitz_doc = pdf_doc.doc
    total = fitz_doc.page_count

    from_page = printer.fromPage()
    to_page = printer.toPage()
    if from_page == 0 and to_page == 0:
        from_page, to_page = 1, total
    from_page = max(1, from_page)
    to_page = min(total, to_page)

    painter = QPainter()
    if not painter.begin(printer):
        raise RuntimeError("No se pudo iniciar el QPainter sobre la impresora")

    try:
        dpi = printer.resolution()
        zoom = dpi / 72.0
        import fitz
        matrix = fitz.Matrix(zoom, zoom)

        copies = max(1, printer.copyCount())
        for copy in range(copies):
            for page_idx in range(from_page - 1, to_page):
                if copy > 0 or page_idx > from_page - 1:
                    printer.newPage()

                page = fitz_doc.load_page(page_idx)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                fmt = QImage.Format_RGB888
                image = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt).copy()

                target = painter.viewport()
                scaled = image.scaled(
                    target.width(), target.height(),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation,
                )
                x = target.x() + (target.width() - scaled.width()) // 2
                y = target.y() + (target.height() - scaled.height()) // 2
                painter.drawImage(x, y, scaled)
    finally:
        painter.end()

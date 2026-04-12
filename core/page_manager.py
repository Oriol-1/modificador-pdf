"""Gestor de operaciones de página para documentos PDF.

Provee funciones para unir, dividir, extraer, eliminar
y reordenar páginas usando PyMuPDF.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple
import logging
import os

import fitz

logger = logging.getLogger(__name__)


class PageOperation(Enum):
    """Tipo de operación de página."""
    MERGE = "merge"
    SPLIT = "split"
    EXTRACT = "extract"
    DELETE = "delete"
    REORDER = "reorder"
    ROTATE = "rotate"


@dataclass
class PageRange:
    """Rango de páginas (1-based, inclusive).

    Attributes:
        start: Página inicial (1-based).
        end: Página final (1-based, inclusive).
    """
    start: int
    end: int

    def to_indices(self) -> List[int]:
        """Convierte a lista de índices 0-based."""
        return list(range(self.start - 1, self.end))

    @staticmethod
    def from_string(s: str, max_pages: int) -> 'PageRange':
        """Parsea un rango desde string (e.g., '1-5', '3').

        Args:
            s: String del rango.
            max_pages: Número máximo de páginas.

        Returns:
            PageRange validado.

        Raises:
            ValueError: Si el rango es inválido.
        """
        s = s.strip()
        if '-' in s:
            parts = s.split('-', 1)
            start = int(parts[0].strip())
            end = int(parts[1].strip())
        else:
            start = end = int(s)

        if start < 1 or end < 1:
            raise ValueError(f"Las páginas deben ser >= 1: {s}")
        if start > max_pages or end > max_pages:
            raise ValueError(
                f"Página fuera de rango (máximo {max_pages}): {s}"
            )
        if start > end:
            raise ValueError(f"Rango invertido: {s}")

        return PageRange(start=start, end=end)


@dataclass
class OperationResult:
    """Resultado de una operación de página.

    Attributes:
        success: Si la operación fue exitosa.
        output_path: Ruta del archivo resultante.
        message: Mensaje descriptivo.
        pages_affected: Número de páginas afectadas.
    """
    success: bool
    output_path: str = ""
    message: str = ""
    pages_affected: int = 0


def merge_pdfs(
    input_paths: List[str],
    output_path: str,
) -> OperationResult:
    """Une múltiples PDFs en uno solo.

    Args:
        input_paths: Lista de rutas de PDFs a unir.
        output_path: Ruta del PDF resultante.

    Returns:
        OperationResult con el resultado.
    """
    if not input_paths:
        return OperationResult(
            success=False, message="No se proporcionaron archivos"
        )

    try:
        merged = fitz.open()
        total_pages = 0

        for path in input_paths:
            if not os.path.isfile(path):
                return OperationResult(
                    success=False,
                    message=f"Archivo no encontrado: {path}",
                )
            doc = fitz.open(path)
            merged.insert_pdf(doc)
            total_pages += doc.page_count
            doc.close()

        merged.save(output_path)
        merged.close()

        logger.info(
            f"PDFs unidos: {len(input_paths)} archivos, "
            f"{total_pages} páginas → {output_path}"
        )

        return OperationResult(
            success=True,
            output_path=output_path,
            message=f"Unión exitosa: {total_pages} páginas",
            pages_affected=total_pages,
        )
    except Exception as e:
        logger.error(f"Error al unir PDFs: {e}")
        return OperationResult(
            success=False, message=f"Error al unir: {e}"
        )


def split_pdf(
    input_path: str,
    output_dir: str,
    ranges: Optional[List[PageRange]] = None,
) -> OperationResult:
    """Divide un PDF en múltiples archivos.

    Si no se especifican rangos, divide en páginas individuales.

    Args:
        input_path: Ruta del PDF de entrada.
        output_dir: Directorio de salida.
        ranges: Rangos de páginas (opcional).

    Returns:
        OperationResult con el resultado.
    """
    try:
        doc = fitz.open(input_path)
        os.makedirs(output_dir, exist_ok=True)

        base_name = os.path.splitext(os.path.basename(input_path))[0]

        if ranges is None:
            ranges = [PageRange(i + 1, i + 1) for i in range(doc.page_count)]

        files_created = 0
        for i, page_range in enumerate(ranges):
            output_path = os.path.join(
                output_dir,
                f"{base_name}_p{page_range.start}-{page_range.end}.pdf",
            )
            new_doc = fitz.open()
            new_doc.insert_pdf(
                doc,
                from_page=page_range.start - 1,
                to_page=page_range.end - 1,
            )
            new_doc.save(output_path)
            new_doc.close()
            files_created += 1

        doc.close()

        logger.info(
            f"PDF dividido: {files_created} archivos en {output_dir}"
        )

        return OperationResult(
            success=True,
            output_path=output_dir,
            message=f"División exitosa: {files_created} archivos creados",
            pages_affected=sum(
                r.end - r.start + 1 for r in ranges
            ),
        )
    except Exception as e:
        logger.error(f"Error al dividir PDF: {e}")
        return OperationResult(
            success=False, message=f"Error al dividir: {e}"
        )


def extract_pages(
    input_path: str,
    output_path: str,
    page_indices: List[int],
) -> OperationResult:
    """Extrae páginas específicas a un nuevo PDF.

    Args:
        input_path: Ruta del PDF de entrada.
        output_path: Ruta del PDF de salida.
        page_indices: Índices de páginas a extraer (0-based).

    Returns:
        OperationResult con el resultado.
    """
    if not page_indices:
        return OperationResult(
            success=False, message="No se especificaron páginas"
        )

    try:
        doc = fitz.open(input_path)

        valid_indices = [
            i for i in page_indices
            if 0 <= i < doc.page_count
        ]

        if not valid_indices:
            doc.close()
            return OperationResult(
                success=False, message="Ninguna página válida"
            )

        new_doc = fitz.open()
        for idx in valid_indices:
            new_doc.insert_pdf(doc, from_page=idx, to_page=idx)
        new_doc.save(output_path)
        new_doc.close()
        doc.close()

        logger.info(
            f"Páginas extraídas: {len(valid_indices)} → {output_path}"
        )

        return OperationResult(
            success=True,
            output_path=output_path,
            message=f"Extraídas {len(valid_indices)} páginas",
            pages_affected=len(valid_indices),
        )
    except Exception as e:
        logger.error(f"Error al extraer páginas: {e}")
        return OperationResult(
            success=False, message=f"Error al extraer: {e}"
        )


def delete_pages(
    input_path: str,
    output_path: str,
    page_indices: List[int],
) -> OperationResult:
    """Elimina páginas de un PDF.

    Args:
        input_path: Ruta del PDF de entrada.
        output_path: Ruta del PDF de salida.
        page_indices: Índices de páginas a eliminar (0-based).

    Returns:
        OperationResult con el resultado.
    """
    if not page_indices:
        return OperationResult(
            success=False, message="No se especificaron páginas"
        )

    try:
        doc = fitz.open(input_path)

        valid_indices = sorted(set(
            i for i in page_indices
            if 0 <= i < doc.page_count
        ))

        if len(valid_indices) >= doc.page_count:
            doc.close()
            return OperationResult(
                success=False,
                message="No se pueden eliminar todas las páginas",
            )

        doc.delete_pages(valid_indices)
        doc.save(output_path)
        doc.close()

        logger.info(
            f"Páginas eliminadas: {len(valid_indices)} → {output_path}"
        )

        return OperationResult(
            success=True,
            output_path=output_path,
            message=f"Eliminadas {len(valid_indices)} páginas",
            pages_affected=len(valid_indices),
        )
    except Exception as e:
        logger.error(f"Error al eliminar páginas: {e}")
        return OperationResult(
            success=False, message=f"Error al eliminar: {e}"
        )


def reorder_pages(
    input_path: str,
    output_path: str,
    new_order: List[int],
) -> OperationResult:
    """Reordena las páginas de un PDF.

    Args:
        input_path: Ruta del PDF de entrada.
        output_path: Ruta del PDF de salida.
        new_order: Nueva orden de páginas (0-based).
            new_order[nueva_pos] = vieja_pos.

    Returns:
        OperationResult con el resultado.
    """
    try:
        doc = fitz.open(input_path)

        if sorted(new_order) != list(range(doc.page_count)):
            doc.close()
            return OperationResult(
                success=False,
                message="Orden inválido: debe ser una permutación",
            )

        doc.select(new_order)
        doc.save(output_path)
        doc.close()

        logger.info(f"Páginas reordenadas → {output_path}")

        return OperationResult(
            success=True,
            output_path=output_path,
            message=f"Reordenadas {len(new_order)} páginas",
            pages_affected=len(new_order),
        )
    except Exception as e:
        logger.error(f"Error al reordenar páginas: {e}")
        return OperationResult(
            success=False, message=f"Error al reordenar: {e}"
        )


def rotate_pages(
    input_path: str,
    output_path: str,
    page_indices: List[int],
    angle: int,
) -> OperationResult:
    """Rota páginas específicas.

    Args:
        input_path: Ruta del PDF de entrada.
        output_path: Ruta del PDF de salida.
        page_indices: Índices de páginas a rotar (0-based).
        angle: Ángulo de rotación (90, 180, 270).

    Returns:
        OperationResult con el resultado.
    """
    if angle not in (90, 180, 270):
        return OperationResult(
            success=False,
            message=f"Ángulo inválido: {angle} (debe ser 90, 180 o 270)",
        )

    try:
        doc = fitz.open(input_path)

        valid_indices = [
            i for i in page_indices
            if 0 <= i < doc.page_count
        ]

        for idx in valid_indices:
            page = doc[idx]
            page.set_rotation((page.rotation + angle) % 360)

        doc.save(output_path)
        doc.close()

        logger.info(
            f"Rotadas {len(valid_indices)} páginas {angle}° → {output_path}"
        )

        return OperationResult(
            success=True,
            output_path=output_path,
            message=f"Rotadas {len(valid_indices)} páginas {angle}°",
            pages_affected=len(valid_indices),
        )
    except Exception as e:
        logger.error(f"Error al rotar páginas: {e}")
        return OperationResult(
            success=False, message=f"Error al rotar: {e}"
        )


def get_page_info(doc) -> List[dict]:
    """Obtiene información de cada página del documento.

    Args:
        doc: Documento fitz abierto.

    Returns:
        Lista de diccionarios con info de cada página.
    """
    pages = []
    for i, page in enumerate(doc):
        rect = page.rect
        pages.append({
            "index": i,
            "number": i + 1,
            "width": rect.width,
            "height": rect.height,
            "rotation": page.rotation,
            "text_length": len(page.get_text("text")),
        })
    return pages

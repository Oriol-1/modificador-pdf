"""Indexador de documentos PDF para búsqueda RAG.

Extrae texto de documentos PDF y lo divide en chunks con
metadata para búsqueda semántica.
"""

from dataclasses import dataclass, field
from typing import List
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Fragmento de texto extraído de un PDF.

    Attributes:
        chunk_id: Identificador único del chunk.
        text: Contenido textual del chunk.
        page_num: Número de página (0-based).
        start_char: Posición inicial en el texto de la página.
        end_char: Posición final en el texto de la página.
    """
    chunk_id: int
    text: str
    page_num: int
    start_char: int = 0
    end_char: int = 0

    def to_dict(self) -> dict:
        """Serializa a diccionario."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "page_num": self.page_num,
            "start_char": self.start_char,
            "end_char": self.end_char,
        }

    @staticmethod
    def from_dict(data: dict) -> 'TextChunk':
        """Deserializa desde diccionario."""
        return TextChunk(**data)


@dataclass
class DocumentIndex:
    """Índice de un documento PDF con sus chunks.

    Attributes:
        file_path: Ruta del archivo PDF indexado.
        total_pages: Número total de páginas.
        chunks: Lista de chunks de texto.
        page_texts: Texto completo por página.
    """
    file_path: str
    total_pages: int
    chunks: List[TextChunk] = field(default_factory=list)
    page_texts: List[str] = field(default_factory=list)


def extract_page_texts(doc) -> List[str]:
    """Extrae el texto de cada página de un documento fitz.

    Args:
        doc: Documento fitz abierto.

    Returns:
        Lista de textos, uno por página.
    """
    texts = []
    for page in doc:
        text = page.get_text("text")
        texts.append(text.strip())
    return texts


def split_into_chunks(
    text: str,
    page_num: int,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    start_id: int = 0,
) -> List[TextChunk]:
    """Divide texto en chunks con solapamiento.

    Args:
        text: Texto a dividir.
        page_num: Número de página.
        chunk_size: Tamaño máximo de cada chunk en caracteres.
        chunk_overlap: Solapamiento entre chunks consecutivos.
        start_id: ID inicial para los chunks.

    Returns:
        Lista de TextChunk.
    """
    if not text.strip():
        return []

    chunks = []
    paragraphs = re.split(r'\n\s*\n', text)

    current_text = ""
    current_start = 0
    chunk_id = start_id
    pos = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            pos += 2
            continue

        if len(current_text) + len(para) + 1 > chunk_size and current_text:
            chunks.append(TextChunk(
                chunk_id=chunk_id,
                text=current_text.strip(),
                page_num=page_num,
                start_char=current_start,
                end_char=current_start + len(current_text),
            ))
            chunk_id += 1
            if chunk_overlap > 0 and len(current_text) > chunk_overlap:
                overlap_text = current_text[-chunk_overlap:]
                current_text = overlap_text + " " + para
                current_start = pos - chunk_overlap
            else:
                current_text = para
                current_start = pos
        else:
            if current_text:
                current_text += "\n" + para
            else:
                current_text = para
                current_start = pos

        pos += len(para) + 2

    if current_text.strip():
        chunks.append(TextChunk(
            chunk_id=chunk_id,
            text=current_text.strip(),
            page_num=page_num,
            start_char=current_start,
            end_char=current_start + len(current_text),
        ))

    return chunks


def create_document_index(
    doc,
    file_path: str = "",
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> DocumentIndex:
    """Crea un índice completo del documento PDF.

    Args:
        doc: Documento fitz abierto.
        file_path: Ruta del archivo.
        chunk_size: Tamaño de chunk.
        chunk_overlap: Solapamiento de chunks.

    Returns:
        DocumentIndex con todos los chunks.
    """
    page_texts = extract_page_texts(doc)
    all_chunks = []
    chunk_id = 0

    for page_num, text in enumerate(page_texts):
        page_chunks = split_into_chunks(
            text, page_num, chunk_size, chunk_overlap, chunk_id
        )
        all_chunks.extend(page_chunks)
        if page_chunks:
            chunk_id = page_chunks[-1].chunk_id + 1

    logger.info(
        f"Documento indexado: {len(page_texts)} páginas, "
        f"{len(all_chunks)} chunks"
    )

    return DocumentIndex(
        file_path=file_path,
        total_pages=len(page_texts),
        chunks=all_chunks,
        page_texts=page_texts,
    )

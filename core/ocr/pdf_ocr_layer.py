"""Capa de texto invisible sobre PDFs escaneados.

Permite convertir PDFs escaneados en PDFs con texto buscable
insertando una capa de texto invisible (render_mode=3) sobre
las imágenes originales.
"""
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import fitz  # PyMuPDF

from core.ocr.ocr_engine import OCRResult, OCRWord, OCRLine

logger = logging.getLogger(__name__)


@dataclass
class OCRPageResult:
    """Resultado OCR de una página individual.
    
    Attributes:
        page_num: Número de página (0-based).
        ocr_result: Resultado OCR de la página.
        was_scanned: True si la página se detectó como escaneada.
        text_inserted: True si se insertó capa de texto.
    """
    page_num: int
    ocr_result: Optional[OCRResult] = None
    was_scanned: bool = False
    text_inserted: bool = False


@dataclass
class OCRDocumentResult:
    """Resultado OCR del documento completo.
    
    Attributes:
        pages: Resultados por página.
        total_pages: Páginas totales del documento.
        scanned_pages: Cantidad de páginas escaneadas.
        processed_pages: Cantidad de páginas procesadas con OCR.
        total_words: Palabras totales reconocidas.
        avg_confidence: Confianza promedio global.
    """
    pages: List[OCRPageResult] = field(default_factory=list)
    total_pages: int = 0
    scanned_pages: int = 0
    processed_pages: int = 0
    total_words: int = 0
    avg_confidence: float = 0.0


def is_scanned_page(page: fitz.Page, text_threshold: int = 10) -> bool:
    """Detecta si una página es escaneada (imagen sin texto).
    
    Args:
        page: Página de PyMuPDF.
        text_threshold: Caracteres mínimos para considerar la página
            como no escaneada.
            
    Returns:
        True si la página parece escaneada.
    """
    text = page.get_text("text").strip()
    images = page.get_images(full=True)
    
    has_minimal_text = len(text) < text_threshold
    has_images = len(images) > 0
    
    return has_minimal_text and has_images


def detect_scanned_pages(doc: fitz.Document) -> List[int]:
    """Detecta las páginas escaneadas de un documento.
    
    Args:
        doc: Documento PyMuPDF abierto.
        
    Returns:
        Lista de índices de páginas escaneadas (0-based).
    """
    scanned = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        if is_scanned_page(page):
            scanned.append(page_num)
    return scanned


def page_image_to_numpy(page: fitz.Page, dpi: int = 300):
    """Convierte una página PDF a imagen numpy array.
    
    Args:
        page: Página de PyMuPDF.
        dpi: Resolución de la imagen resultante.
        
    Returns:
        numpy array con la imagen en formato BGR.
    """
    import numpy as np
    
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n
    )
    
    # PyMuPDF genera RGB, convertir a BGR para OpenCV
    if pix.n == 3:
        import cv2
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    
    return img


def insert_invisible_text(
    page: fitz.Page,
    ocr_result: OCRResult,
    image_dpi: int = 300,
) -> int:
    """Inserta texto invisible sobre una página escaneada.
    
    Los textos se posicionan en las coordenadas de los bounding boxes
    de OCR, escalados al sistema de coordenadas PDF.
    
    Args:
        page: Página de PyMuPDF.
        ocr_result: Resultado de OCR con palabras y posiciones.
        image_dpi: DPI de la imagen OCR para escalar coordenadas.
        
    Returns:
        Cantidad de palabras insertadas.
    """
    if not ocr_result.words:
        return 0
    
    # Factor de escala de pixels (image DPI) a puntos PDF (72 DPI)
    scale = 72.0 / image_dpi
    
    words_inserted = 0
    
    for word in ocr_result.words:
        if not word.text.strip():
            continue
        if word.confidence < 10:
            continue
        
        # Convertir coordenadas de imagen a coordenadas PDF
        x = word.x * scale
        y = word.y * scale
        w = word.width * scale
        h = word.height * scale
        
        # Calcular tamaño de fuente proporcional al alto del bounding box
        fontsize = max(h * 0.85, 4.0)
        
        try:
            page.insert_text(
                point=fitz.Point(x, y + h),  # Baseline es parte inferior
                text=word.text,
                fontsize=fontsize,
                fontname="helv",
                render_mode=3,  # Invisible
                overlay=True,
            )
            words_inserted += 1
        except Exception as e:
            logger.debug(f"Error insertando palabra '{word.text}': {e}")
    
    logger.info(
        f"Insertadas {words_inserted}/{len(ocr_result.words)} palabras "
        f"invisibles en página"
    )
    return words_inserted


def process_document_ocr(
    doc: fitz.Document,
    ocr_engine,
    language: str = "spa",
    preprocess_fn=None,
    dpi: int = 300,
    page_indices: Optional[List[int]] = None,
    progress_callback=None,
) -> OCRDocumentResult:
    """Procesa un documento completo con OCR.
    
    Args:
        doc: Documento PyMuPDF abierto.
        ocr_engine: Instancia de OCREngine.
        language: Código de idioma para OCR.
        preprocess_fn: Función de preprocesado de imagen (opcional).
            Debe aceptar numpy array y retornar numpy array o
            PreprocessResult.
        dpi: DPI para renderizar páginas.
        page_indices: Índices de páginas a procesar (None = auto-detectar).
        progress_callback: Callback(page_num, total, status_text).
        
    Returns:
        OCRDocumentResult con todos los resultados.
    """
    total_pages = len(doc)
    
    # Determinar qué páginas procesar
    if page_indices is None:
        page_indices = detect_scanned_pages(doc)
    
    result = OCRDocumentResult(
        total_pages=total_pages,
        scanned_pages=len(page_indices),
    )
    
    for i, page_num in enumerate(page_indices):
        if progress_callback:
            progress_callback(
                i, len(page_indices),
                f"Procesando página {page_num + 1}/{total_pages}..."
            )
        
        page = doc[page_num]
        page_result = OCRPageResult(page_num=page_num, was_scanned=True)
        
        try:
            # Renderizar página a imagen
            img = page_image_to_numpy(page, dpi=dpi)
            
            # Preprocesar si hay función
            if preprocess_fn is not None:
                processed = preprocess_fn(img)
                # Si retorna un PreprocessResult, extraer imagen
                if hasattr(processed, 'image'):
                    img = processed.image
                else:
                    img = processed
            
            # Ejecutar OCR
            ocr_result = ocr_engine.recognize(img, language=language)
            page_result.ocr_result = ocr_result
            
            # Insertar texto invisible
            n_words = insert_invisible_text(page, ocr_result, image_dpi=dpi)
            page_result.text_inserted = n_words > 0
            
            result.total_words += len(ocr_result.words)
            result.processed_pages += 1
            
        except Exception as e:
            logger.error(f"Error OCR en página {page_num}: {e}")
        
        result.pages.append(page_result)
    
    # Confianza promedio global
    all_confs = []
    for pr in result.pages:
        if pr.ocr_result:
            all_confs.append(pr.ocr_result.avg_confidence)
    result.avg_confidence = (
        sum(all_confs) / len(all_confs) if all_confs else 0.0
    )
    
    if progress_callback:
        progress_callback(
            len(page_indices), len(page_indices),
            f"OCR completado: {result.total_words} palabras en "
            f"{result.processed_pages} páginas"
        )
    
    logger.info(
        f"OCR documento completado: {result.processed_pages} páginas, "
        f"{result.total_words} palabras, confianza={result.avg_confidence:.1f}%"
    )
    
    return result

"""Motor de compresión inteligente de PDFs.

Aplica técnicas progresivas de compresión para reducir el tamaño
de archivos PDF, desde lossless hasta lossy con control de calidad.
"""
import logging
import tempfile
import os
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional, Tuple

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class CompressionLevel(IntEnum):
    """Nivel de compresión predefinido."""
    LOSSLESS = 0       # Solo limpieza, sin pérdida
    LOW = 1            # Ligera reducción de calidad de imagen
    MEDIUM = 2         # Reducción moderada
    HIGH = 3           # Reducción agresiva
    MAXIMUM = 4        # Máxima compresión posible


class CompressionTechnique(IntEnum):
    """Técnicas de compresión disponibles, ordenadas de menor a mayor pérdida."""
    GARBAGE_CLEANUP = 0
    METADATA_REMOVAL = 1
    FONT_SUBSETTING = 2
    DEFLATE_RECOMPRESS = 3
    IMAGE_DPI_REDUCTION = 4
    IMAGE_JPEG_CONVERSION = 5


@dataclass
class CompressionConfig:
    """Configuración de compresión.
    
    Attributes:
        target_size_kb: Tamaño objetivo en KB (0 = sin objetivo, usar level).
        level: Nivel de compresión predefinido.
        garbage_level: Nivel de limpieza de objetos (0-4).
        remove_metadata: Eliminar metadatos no esenciales.
        subset_fonts: Hacer subset de fuentes embebidas.
        image_max_dpi: DPI máximo para imágenes (0 = no reducir).
        image_quality: Calidad JPEG para imágenes (1-100).
        convert_png_to_jpeg: Convertir PNG sin transparencia a JPEG.
    """
    target_size_kb: int = 0
    level: CompressionLevel = CompressionLevel.MEDIUM
    garbage_level: int = 4
    remove_metadata: bool = True
    subset_fonts: bool = True
    image_max_dpi: int = 150
    image_quality: int = 75
    convert_png_to_jpeg: bool = True

    @staticmethod
    def from_level(level: CompressionLevel) -> 'CompressionConfig':
        """Crea configuración a partir de un nivel predefinido."""
        presets = {
            CompressionLevel.LOSSLESS: CompressionConfig(
                level=CompressionLevel.LOSSLESS,
                garbage_level=4, remove_metadata=True, subset_fonts=True,
                image_max_dpi=0, image_quality=100, convert_png_to_jpeg=False,
            ),
            CompressionLevel.LOW: CompressionConfig(
                level=CompressionLevel.LOW,
                garbage_level=4, remove_metadata=True, subset_fonts=True,
                image_max_dpi=200, image_quality=85, convert_png_to_jpeg=False,
            ),
            CompressionLevel.MEDIUM: CompressionConfig(
                level=CompressionLevel.MEDIUM,
                garbage_level=4, remove_metadata=True, subset_fonts=True,
                image_max_dpi=150, image_quality=75, convert_png_to_jpeg=True,
            ),
            CompressionLevel.HIGH: CompressionConfig(
                level=CompressionLevel.HIGH,
                garbage_level=4, remove_metadata=True, subset_fonts=True,
                image_max_dpi=100, image_quality=60, convert_png_to_jpeg=True,
            ),
            CompressionLevel.MAXIMUM: CompressionConfig(
                level=CompressionLevel.MAXIMUM,
                garbage_level=4, remove_metadata=True, subset_fonts=True,
                image_max_dpi=72, image_quality=40, convert_png_to_jpeg=True,
            ),
        }
        return presets.get(level, presets[CompressionLevel.MEDIUM])

    @staticmethod
    def for_email() -> 'CompressionConfig':
        """Preset para envío por email (objetivo ~5 MB)."""
        config = CompressionConfig.from_level(CompressionLevel.MEDIUM)
        config.target_size_kb = 5120
        return config

    @staticmethod
    def for_web() -> 'CompressionConfig':
        """Preset para uso web (objetivo ~1 MB)."""
        config = CompressionConfig.from_level(CompressionLevel.HIGH)
        config.target_size_kb = 1024
        return config

    @staticmethod
    def for_minimum() -> 'CompressionConfig':
        """Preset para tamaño mínimo (objetivo ~400 KB)."""
        config = CompressionConfig.from_level(CompressionLevel.MAXIMUM)
        config.target_size_kb = 400
        return config


@dataclass
class CompressionResult:
    """Resultado de la compresión.
    
    Attributes:
        original_size: Tamaño original en bytes.
        compressed_size: Tamaño comprimido en bytes.
        techniques_applied: Técnicas aplicadas.
        output_path: Ruta del archivo comprimido (si se guardó).
        success: True si la compresión fue exitosa.
        error: Mensaje de error si no fue exitosa.
    """
    original_size: int = 0
    compressed_size: int = 0
    techniques_applied: List[CompressionTechnique] = field(default_factory=list)
    output_path: str = ""
    success: bool = True
    error: str = ""

    @property
    def reduction_percent(self) -> float:
        """Porcentaje de reducción de tamaño."""
        if self.original_size <= 0:
            return 0.0
        return (1.0 - self.compressed_size / self.original_size) * 100.0

    @property
    def original_size_str(self) -> str:
        """Tamaño original formateado."""
        return _format_size(self.original_size)

    @property
    def compressed_size_str(self) -> str:
        """Tamaño comprimido formateado."""
        return _format_size(self.compressed_size)


def _format_size(size_bytes: int) -> str:
    """Formatea un tamaño en bytes a string legible."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def _get_file_size(path: str) -> int:
    """Retorna el tamaño de un archivo en bytes."""
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def apply_garbage_cleanup(doc: fitz.Document, level: int = 4) -> bool:
    """Limpia objetos huérfanos del PDF.
    
    Args:
        doc: Documento PyMuPDF abierto.
        level: Nivel de limpieza (0-4, mayor = más agresivo).
        
    Returns:
        True si se aplicó correctamente.
    """
    try:
        # El garbage collection se aplica al guardar, aquí solo marcamos
        logger.debug(f"Garbage cleanup programado: level={level}")
        return True
    except Exception as e:
        logger.error(f"Error en garbage cleanup: {e}")
        return False


def apply_metadata_removal(doc: fitz.Document) -> bool:
    """Elimina metadatos no esenciales del PDF.
    
    Args:
        doc: Documento PyMuPDF abierto.
        
    Returns:
        True si se aplicó correctamente.
    """
    try:
        doc.set_metadata({})
        # Eliminar XML metadata
        doc.del_xml_metadata()
        logger.debug("Metadatos eliminados")
        return True
    except Exception as e:
        logger.error(f"Error eliminando metadatos: {e}")
        return False


def apply_font_subsetting(doc: fitz.Document) -> bool:
    """Hace subset de fuentes embebidas para reducir tamaño.
    
    Args:
        doc: Documento PyMuPDF abierto.
        
    Returns:
        True si se aplicó correctamente.
    """
    try:
        doc.subset_fonts()
        logger.debug("Font subsetting aplicado")
        return True
    except Exception as e:
        logger.error(f"Error en font subsetting: {e}")
        return False


def apply_image_compression(
    doc: fitz.Document,
    max_dpi: int = 150,
    quality: int = 75,
    convert_png: bool = True,
    progress_callback=None,
) -> int:
    """Comprime las imágenes del documento.
    
    Args:
        doc: Documento PyMuPDF abierto.
        max_dpi: DPI máximo permitido para imágenes.
        quality: Calidad JPEG (1-100).
        convert_png: Convertir PNG sin transparencia a JPEG.
        progress_callback: Callback(page_num, total_pages).
        
    Returns:
        Cantidad de imágenes procesadas.
    """
    images_processed = 0
    total_pages = len(doc)
    
    for page_num in range(total_pages):
        if progress_callback:
            progress_callback(page_num, total_pages)
        
        page = doc[page_num]
        image_list = page.get_images(full=True)
        
        for img_index, img_info in enumerate(image_list):
            xref = img_info[0]
            
            try:
                base_image = doc.extract_image(xref)
                if not base_image:
                    continue
                
                img_bytes = base_image["image"]
                img_ext = base_image.get("ext", "")
                width = base_image.get("width", 0)
                height = base_image.get("height", 0)
                
                if width <= 0 or height <= 0:
                    continue
                
                # Calcular DPI actual (aproximado basado en la página)
                page_rect = page.rect
                # Buscar dpi estimado por el ratio imagen/página
                img_dpi_x = width / (page_rect.width / 72.0) if page_rect.width > 0 else 72
                img_dpi_y = height / (page_rect.height / 72.0) if page_rect.height > 0 else 72
                current_dpi = max(img_dpi_x, img_dpi_y)
                
                # Reducir DPI si excede el máximo
                if max_dpi > 0 and current_dpi > max_dpi * 1.1:
                    scale = max_dpi / current_dpi
                    new_width = max(1, int(width * scale))
                    new_height = max(1, int(height * scale))
                else:
                    new_width = width
                    new_height = height
                
                # Crear pixmap desde los datos originales
                pix = fitz.Pixmap(doc, xref)
                
                # Si tiene alpha y queremos convertir a JPEG, quitar alpha
                if pix.alpha and (convert_png or img_ext.lower() != "png"):
                    pix = fitz.Pixmap(fitz.csRGB, pix)  # Quitar alpha
                
                # Redimensionar si es necesario
                if new_width != width or new_height != height:
                    pix = fitz.Pixmap(pix, new_width, new_height, None, None)
                
                # Reemplazar imagen en el documento
                # Guardar como JPEG con la calidad especificada
                img_data = pix.tobytes(output="jpeg", jpg_quality=quality)
                
                doc._updateStream(xref, img_data)
                
                images_processed += 1
                
            except Exception as e:
                logger.debug(f"No se pudo comprimir imagen xref={xref}: {e}")
                continue
    
    logger.info(f"Imágenes comprimidas: {images_processed}")
    return images_processed


def compress_pdf(
    input_path: str,
    output_path: str,
    config: Optional[CompressionConfig] = None,
    progress_callback=None,
) -> CompressionResult:
    """Comprime un archivo PDF.
    
    Args:
        input_path: Ruta del PDF de entrada.
        output_path: Ruta del PDF comprimido de salida.
        config: Configuración de compresión.
        progress_callback: Callback(step, total_steps, description).
        
    Returns:
        CompressionResult con el resultado.
    """
    if config is None:
        config = CompressionConfig.from_level(CompressionLevel.MEDIUM)
    
    result = CompressionResult(output_path=output_path)
    result.original_size = _get_file_size(input_path)
    
    if result.original_size == 0:
        result.success = False
        result.error = "No se pudo leer el archivo de entrada"
        return result
    
    total_steps = 5
    step = 0
    
    try:
        doc = fitz.open(input_path)
        
        # 1. Garbage cleanup
        if progress_callback:
            progress_callback(step, total_steps, "Limpiando objetos huérfanos...")
        if apply_garbage_cleanup(doc, config.garbage_level):
            result.techniques_applied.append(CompressionTechnique.GARBAGE_CLEANUP)
        step += 1
        
        # 2. Metadata removal
        if config.remove_metadata:
            if progress_callback:
                progress_callback(step, total_steps, "Eliminando metadatos...")
            if apply_metadata_removal(doc):
                result.techniques_applied.append(CompressionTechnique.METADATA_REMOVAL)
        step += 1
        
        # 3. Font subsetting
        if config.subset_fonts:
            if progress_callback:
                progress_callback(step, total_steps, "Optimizando fuentes...")
            if apply_font_subsetting(doc):
                result.techniques_applied.append(CompressionTechnique.FONT_SUBSETTING)
        step += 1
        
        # 4. Image compression
        if config.image_max_dpi > 0 or config.convert_png_to_jpeg:
            if progress_callback:
                progress_callback(step, total_steps, "Comprimiendo imágenes...")
            
            n_images = apply_image_compression(
                doc,
                max_dpi=config.image_max_dpi,
                quality=config.image_quality,
                convert_png=config.convert_png_to_jpeg,
            )
            if n_images > 0:
                result.techniques_applied.append(CompressionTechnique.IMAGE_DPI_REDUCTION)
                if config.convert_png_to_jpeg:
                    result.techniques_applied.append(CompressionTechnique.IMAGE_JPEG_CONVERSION)
        step += 1
        
        # 5. Guardar con optimizaciones
        if progress_callback:
            progress_callback(step, total_steps, "Guardando PDF comprimido...")
        
        doc.save(
            output_path,
            garbage=config.garbage_level,
            deflate=True,
            deflate_images=True,
            deflate_fonts=True,
            clean=True,
        )
        doc.close()
        step += 1
        
        result.techniques_applied.append(CompressionTechnique.DEFLATE_RECOMPRESS)
        result.compressed_size = _get_file_size(output_path)
        result.success = True
        
        if progress_callback:
            progress_callback(step, total_steps, "Compresión completada")
        
        logger.info(
            f"PDF comprimido: {result.original_size_str} → {result.compressed_size_str} "
            f"({result.reduction_percent:.1f}% reducción)"
        )
        
    except Exception as e:
        result.success = False
        result.error = str(e)
        logger.error(f"Error comprimiendo PDF: {e}")
    
    return result


def compress_document(
    doc: fitz.Document,
    config: Optional[CompressionConfig] = None,
    progress_callback=None,
) -> Tuple[bytes, CompressionResult]:
    """Comprime un documento ya abierto y retorna los bytes.
    
    Args:
        doc: Documento PyMuPDF abierto.
        config: Configuración de compresión.
        progress_callback: Callback(step, total_steps, description).
        
    Returns:
        Tupla (bytes_comprimidos, CompressionResult).
    """
    if config is None:
        config = CompressionConfig.from_level(CompressionLevel.MEDIUM)
    
    result = CompressionResult()
    
    # Obtener tamaño original guardando a buffer temporal
    original_bytes = doc.tobytes()
    result.original_size = len(original_bytes)
    
    total_steps = 4
    step = 0
    
    try:
        # 1. Garbage (se aplica en save)
        if progress_callback:
            progress_callback(step, total_steps, "Limpiando objetos...")
        result.techniques_applied.append(CompressionTechnique.GARBAGE_CLEANUP)
        step += 1
        
        # 2. Metadata
        if config.remove_metadata:
            if progress_callback:
                progress_callback(step, total_steps, "Eliminando metadatos...")
            apply_metadata_removal(doc)
            result.techniques_applied.append(CompressionTechnique.METADATA_REMOVAL)
        step += 1
        
        # 3. Fonts
        if config.subset_fonts:
            if progress_callback:
                progress_callback(step, total_steps, "Optimizando fuentes...")
            apply_font_subsetting(doc)
            result.techniques_applied.append(CompressionTechnique.FONT_SUBSETTING)
        step += 1
        
        # 4. Images
        if config.image_max_dpi > 0 or config.convert_png_to_jpeg:
            if progress_callback:
                progress_callback(step, total_steps, "Comprimiendo imágenes...")
            apply_image_compression(
                doc,
                max_dpi=config.image_max_dpi,
                quality=config.image_quality,
                convert_png=config.convert_png_to_jpeg,
            )
            result.techniques_applied.append(CompressionTechnique.IMAGE_DPI_REDUCTION)
        step += 1
        
        # Guardar a bytes con compresión
        compressed_bytes = doc.tobytes(
            garbage=config.garbage_level,
            deflate=True,
            deflate_images=True,
            deflate_fonts=True,
            clean=True,
        )
        
        result.compressed_size = len(compressed_bytes)
        result.techniques_applied.append(CompressionTechnique.DEFLATE_RECOMPRESS)
        result.success = True
        
        logger.info(
            f"Documento comprimido: {result.original_size_str} → "
            f"{result.compressed_size_str} ({result.reduction_percent:.1f}%)"
        )
        
        return compressed_bytes, result
        
    except Exception as e:
        result.success = False
        result.error = str(e)
        logger.error(f"Error comprimiendo documento: {e}")
        return original_bytes, result

"""Módulo OCR para PDF Editor Pro.

Provee reconocimiento óptico de caracteres (OCR) para PDFs escaneados,
incluyendo preprocesado de imagen, integración con Tesseract, y creación
de capas de texto invisible sobre el PDF.
"""
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


def is_ocr_available() -> bool:
    """Verifica si las dependencias OCR están disponibles."""
    return HAS_OPENCV and HAS_TESSERACT

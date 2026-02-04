"""Módulo core del editor de PDF."""
from .models import TextBlock, EditOperation
from .pdf_handler import PDFDocument

__all__ = ['PDFDocument', 'TextBlock', 'EditOperation']

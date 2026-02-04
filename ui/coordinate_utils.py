"""
Utilidades para conversión de coordenadas entre vista y PDF.
"""

import fitz
from PyQt5.QtCore import QRectF, QPointF


class CoordinateConverter:
    """
    Convierte coordenadas entre el sistema de vista (QGraphicsView) y el PDF.
    
    El sistema de coordenadas de vista está escalado por el zoom_level.
    El sistema de coordenadas PDF usa puntos (1/72 de pulgada).
    """
    
    def __init__(self, zoom_level: float = 1.0, page_rotation: int = 0):
        self.zoom_level = zoom_level
        self.page_rotation = page_rotation
    
    def update(self, zoom_level: float = None, page_rotation: int = None):
        """Actualiza los parámetros de conversión."""
        if zoom_level is not None:
            self.zoom_level = zoom_level
        if page_rotation is not None:
            self.page_rotation = page_rotation
    
    def view_to_pdf_rect(self, view_rect: QRectF, debug: bool = False) -> fitz.Rect:
        """
        Convierte un rectángulo de coordenadas de vista (pixmap) a coordenadas de PDF.
        
        IMPORTANTE: PyMuPDF maneja las coordenadas de página internamente considerando
        la rotación. Las coordenadas de page.rect ya están en el sistema "visual".
        Por lo tanto, solo necesitamos escalar por el zoom.
        
        Args:
            view_rect: Rectángulo en coordenadas de vista
            debug: Si True, imprime información de debug
            
        Returns:
            Rectángulo en coordenadas de PDF
        """
        # El pixmap es el PDF renderizado con zoom, así que dividimos por zoom
        x0 = view_rect.x() / self.zoom_level
        y0 = view_rect.y() / self.zoom_level
        x1 = view_rect.right() / self.zoom_level
        y1 = view_rect.bottom() / self.zoom_level
        
        if debug:
            print("=== Conversión de coordenadas ===")
            print(f"View rect: ({view_rect.x():.1f}, {view_rect.y():.1f}) -> ({view_rect.right():.1f}, {view_rect.bottom():.1f})")
            print(f"Zoom: {self.zoom_level}")
            print(f"Rotación página: {self.page_rotation}°")
            print(f"PDF rect (escalado): ({x0:.1f}, {y0:.1f}) -> ({x1:.1f}, {y1:.1f})")
        
        # Crear el rectángulo - PyMuPDF maneja la rotación internamente
        pdf_rect = fitz.Rect(x0, y0, x1, y1)
        
        if debug:
            print(f"PDF rect final: {pdf_rect}")
        
        return pdf_rect
    
    def pdf_to_view_rect(self, pdf_rect: fitz.Rect) -> QRectF:
        """
        Convierte un rectángulo de coordenadas de PDF a coordenadas de vista.
        Operación inversa a view_to_pdf_rect.
        
        Args:
            pdf_rect: Rectángulo en coordenadas de PDF
            
        Returns:
            Rectángulo en coordenadas de vista
        """
        # Simplemente aplicar el zoom
        x0 = pdf_rect.x0 * self.zoom_level
        y0 = pdf_rect.y0 * self.zoom_level
        x1 = pdf_rect.x1 * self.zoom_level
        y1 = pdf_rect.y1 * self.zoom_level
        
        return QRectF(x0, y0, x1 - x0, y1 - y0)
    
    def view_to_pdf_point(self, view_point: QPointF) -> tuple:
        """
        Convierte un punto de coordenadas de vista a coordenadas de PDF.
        
        Args:
            view_point: Punto en coordenadas de vista
            
        Returns:
            Tupla (x, y) en coordenadas de PDF
        """
        pdf_x = view_point.x() / self.zoom_level
        pdf_y = view_point.y() / self.zoom_level
        return (pdf_x, pdf_y)
    
    def pdf_to_view_point(self, pdf_x: float, pdf_y: float) -> QPointF:
        """
        Convierte un punto de coordenadas de PDF a coordenadas de vista.
        
        Args:
            pdf_x: Coordenada X en PDF
            pdf_y: Coordenada Y en PDF
            
        Returns:
            QPointF en coordenadas de vista
        """
        view_x = pdf_x * self.zoom_level
        view_y = pdf_y * self.zoom_level
        return QPointF(view_x, view_y)

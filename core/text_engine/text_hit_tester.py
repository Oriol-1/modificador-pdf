"""
TextHitTester - Hit-testing preciso de texto PDF.

Este módulo proporciona funcionalidad para:
- Detectar qué texto hay bajo una coordenada en la página
- Encontrar spans y líneas en posiciones específicas
- Cachear datos de texto para rendimiento
- Convertir entre coordenadas de vista y PDF

El hit-testing es fundamental para:
- Mostrar tooltips de propiedades
- Seleccionar texto específico
- Editar spans individuales
- Integración con PropertyInspector
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any
from enum import Enum
import fitz  # PyMuPDF

try:
    from .text_span import TextSpanMetrics, create_span_from_pymupdf
    from .text_line import TextLine, LineGrouper, group_spans_into_lines, find_line_at_point
except ImportError:
    from text_span import TextSpanMetrics, create_span_from_pymupdf
    from text_line import TextLine, LineGrouper, group_spans_into_lines, find_line_at_point


class HitType(Enum):
    """Tipo de resultado de hit-testing."""
    NONE = "none"               # No se encontró texto
    SPAN = "span"               # Se encontró un span específico
    LINE = "line"               # Se encontró una línea (pero no span preciso)
    INTER_SPAN_GAP = "gap"      # En espacio entre spans de una línea
    CHARACTER = "character"     # Carácter específico encontrado


@dataclass
class HitTestResult:
    """
    Resultado de una operación de hit-testing.
    
    Contiene información completa sobre qué se encontró en el punto.
    """
    hit_type: HitType = HitType.NONE
    
    # Span encontrado (si aplica)
    span: Optional[TextSpanMetrics] = None
    
    # Línea encontrada (si aplica)
    line: Optional[TextLine] = None
    
    # Índice del carácter dentro del span (si aplica)
    char_index: Optional[int] = None
    
    # Coordenadas originales de la consulta
    point: Tuple[float, float] = (0.0, 0.0)
    
    # Bounding box del elemento encontrado
    bbox: Optional[Tuple[float, float, float, float]] = None
    
    # Distancia al elemento más cercano
    distance: float = float('inf')
    
    # Metadatos adicionales
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def found(self) -> bool:
        """True si se encontró algo."""
        return self.hit_type != HitType.NONE
    
    @property
    def text(self) -> str:
        """Texto del elemento encontrado."""
        if self.span:
            return self.span.text
        elif self.line:
            return self.line.text
        return ""
    
    @property
    def char_text(self) -> str:
        """Texto del carácter específico (si aplica)."""
        if self.span and self.char_index is not None:
            if 0 <= self.char_index < len(self.span.text):
                return self.span.text[self.char_index]
        return ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para serialización."""
        return {
            'hit_type': self.hit_type.value,
            'span_id': self.span.span_id if self.span else None,
            'span_text': self.span.text if self.span else None,
            'line_id': self.line.line_id if self.line else None,
            'line_text': self.line.text if self.line else None,
            'char_index': self.char_index,
            'char_text': self.char_text,
            'point': self.point,
            'bbox': self.bbox,
            'distance': self.distance if self.distance != float('inf') else None,
            'metadata': self.metadata,
        }


@dataclass
class PageTextCache:
    """
    Caché de datos de texto extraídos de una página.
    
    Almacena spans y líneas para evitar re-extracción costosa.
    """
    page_num: int
    spans: List[TextSpanMetrics] = field(default_factory=list)
    lines: List[TextLine] = field(default_factory=list)
    is_valid: bool = False
    
    # Índice espacial simple para búsqueda rápida
    _y_sorted_lines: List[TextLine] = field(default_factory=list)
    
    def build_spatial_index(self) -> None:
        """Construir índice espacial para búsqueda rápida."""
        # Ordenar líneas por Y para búsqueda binaria
        self._y_sorted_lines = sorted(
            self.lines, 
            key=lambda line: line.baseline_y
        )
    
    def get_lines_near_y(
        self, 
        y: float, 
        tolerance: float = 20.0
    ) -> List[TextLine]:
        """Obtener líneas cercanas a una coordenada Y."""
        if not self._y_sorted_lines:
            self.build_spatial_index()
        
        result = []
        for line in self._y_sorted_lines:
            bbox = line.bbox
            if abs(line.baseline_y - y) <= tolerance or \
               (bbox[1] - tolerance <= y <= bbox[3] + tolerance):
                result.append(line)
        
        return result
    
    def clear(self) -> None:
        """Limpiar la caché."""
        self.spans.clear()
        self.lines.clear()
        self._y_sorted_lines.clear()
        self.is_valid = False


class TextHitTester:
    """
    Hit-tester de texto PDF con caché y búsqueda optimizada.
    
    Uso básico:
        hit_tester = TextHitTester()
        hit_tester.set_document(pdf_doc)
        
        # Buscar texto en un punto
        result = hit_tester.hit_test(page_num=0, x=100, y=200)
        if result.found:
            print(f"Encontrado: {result.span.text}")
    """
    
    def __init__(self, font_manager=None):
        """
        Inicializar el hit-tester.
        
        Args:
            font_manager: Instancia de FontManager para detección de fuentes
        """
        self._document: Optional[fitz.Document] = None
        self._font_manager = font_manager
        self._page_caches: Dict[int, PageTextCache] = {}
        
        # Configuración
        self._default_tolerance = 5.0  # Tolerancia de hit-testing en puntos
        self._extract_char_widths = True  # Extraer anchos de caracteres
        
        # Line grouper configuration
        self._line_grouper = LineGrouper()
    
    # === Configuración del documento ===
    
    def set_document(self, document: Optional[fitz.Document]) -> None:
        """
        Establecer el documento PDF a usar.
        
        Args:
            document: Documento fitz.Document o None para limpiar
        """
        if self._document != document:
            self.clear_cache()
        self._document = document
    
    def set_font_manager(self, font_manager) -> None:
        """Establecer el FontManager para detección de fuentes."""
        self._font_manager = font_manager
    
    # === Gestión de caché ===
    
    def clear_cache(self) -> None:
        """Limpiar toda la caché."""
        for cache in self._page_caches.values():
            cache.clear()
        self._page_caches.clear()
    
    def invalidate_page(self, page_num: int) -> None:
        """
        Invalidar la caché de una página específica.
        
        Llamar cuando el contenido de la página cambia.
        """
        if page_num in self._page_caches:
            self._page_caches[page_num].clear()
            self._page_caches[page_num].is_valid = False
    
    def ensure_page_cached(self, page_num: int) -> PageTextCache:
        """
        Asegurar que una página esté en caché.
        
        Args:
            page_num: Número de página
            
        Returns:
            PageTextCache con los datos de la página
        """
        if page_num not in self._page_caches:
            self._page_caches[page_num] = PageTextCache(page_num=page_num)
        
        cache = self._page_caches[page_num]
        
        if not cache.is_valid:
            self._extract_page_text(page_num, cache)
        
        return cache
    
    def _extract_page_text(self, page_num: int, cache: PageTextCache) -> None:
        """
        Extraer texto de una página y llenar la caché.
        
        Args:
            page_num: Número de página
            cache: Caché a llenar
        """
        if not self._document or not self._document.is_open:
            return
        
        if page_num < 0 or page_num >= self._document.page_count:
            return
        
        try:
            page = self._document[page_num]
            
            # Extraer texto en formato dict para obtener detalles
            flags = fitz.TEXT_PRESERVE_WHITESPACE | fitz.TEXT_PRESERVE_LIGATURES
            
            if self._extract_char_widths:
                # Incluir información de caracteres
                text_dict = page.get_text("dict", flags=flags)
            else:
                text_dict = page.get_text("dict", flags=flags)
            
            # Convertir bloques a spans
            cache.spans = []
            
            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:  # Solo bloques de texto
                    continue
                
                for line_data in block.get("lines", []):
                    for span_dict in line_data.get("spans", []):
                        if span_dict.get("text", "").strip():  # Ignorar spans vacíos
                            span = create_span_from_pymupdf(
                                span_dict, 
                                page_num, 
                                self._font_manager
                            )
                            cache.spans.append(span)
            
            # Agrupar spans en líneas
            if cache.spans:
                cache.lines = group_spans_into_lines(cache.spans)
            else:
                cache.lines = []
            
            # Construir índice espacial
            cache.build_spatial_index()
            
            cache.is_valid = True
            
        except Exception as e:
            # Log error pero no fallar
            cache.is_valid = False
            cache.metadata = {'error': str(e)}
    
    # === Hit-testing ===
    
    def hit_test(
        self,
        page_num: int,
        x: float,
        y: float,
        tolerance: Optional[float] = None
    ) -> HitTestResult:
        """
        Realizar hit-testing en una coordenada.
        
        Args:
            page_num: Número de página
            x: Coordenada X en espacio PDF
            y: Coordenada Y en espacio PDF
            tolerance: Tolerancia de búsqueda (default: 5pt)
            
        Returns:
            HitTestResult con el resultado de la búsqueda
        """
        result = HitTestResult(point=(x, y))
        
        if tolerance is None:
            tolerance = self._default_tolerance
        
        cache = self.ensure_page_cached(page_num)
        
        if not cache.is_valid or not cache.lines:
            return result
        
        # Buscar línea cercana
        lines_near = cache.get_lines_near_y(y, tolerance * 2)
        
        if not lines_near:
            # Buscar en todas las líneas como fallback
            line = find_line_at_point(cache.lines, x, y, tolerance)
            if line:
                lines_near = [line]
        
        if not lines_near:
            return result
        
        # Encontrar la mejor línea (menor distancia)
        best_line = None
        best_distance = float('inf')
        
        for line in lines_near:
            bbox = line.bbox
            
            # Distancia al bbox de la línea
            dx = max(bbox[0] - x, 0, x - bbox[2])
            dy = max(bbox[1] - y, 0, y - bbox[3])
            dist = (dx * dx + dy * dy) ** 0.5
            
            if dist < best_distance:
                best_distance = dist
                best_line = line
        
        if best_line is None or best_distance > tolerance * 2:
            return result
        
        result.line = best_line
        result.bbox = best_line.bbox
        result.distance = best_distance
        result.hit_type = HitType.LINE
        
        # Buscar span específico dentro de la línea
        span = best_line.find_span_at_x(x)
        
        if span:
            result.span = span
            result.bbox = span.bbox
            result.hit_type = HitType.SPAN
            
            # Verificar si está realmente dentro del bbox del span
            if span.bbox[1] - tolerance <= y <= span.bbox[3] + tolerance:
                # Buscar carácter específico
                char_result = best_line.find_char_at_x(x)
                if char_result:
                    result.char_index = char_result[1]
                    result.hit_type = HitType.CHARACTER
        else:
            # Puede estar en un gap entre spans
            if best_line.spans:
                # Verificar si está entre spans
                for i, s in enumerate(best_line.spans):
                    if s.bbox[2] < x:
                        next_idx = i + 1
                        if next_idx < len(best_line.spans):
                            next_span = best_line.spans[next_idx]
                            if x < next_span.bbox[0]:
                                result.hit_type = HitType.INTER_SPAN_GAP
                                result.metadata['prev_span_id'] = s.span_id
                                result.metadata['next_span_id'] = next_span.span_id
                                break
        
        return result
    
    def hit_test_spans_in_rect(
        self,
        page_num: int,
        rect: Tuple[float, float, float, float]
    ) -> List[TextSpanMetrics]:
        """
        Encontrar todos los spans que intersectan con un rectángulo.
        
        Args:
            page_num: Número de página
            rect: Rectángulo (x0, y0, x1, y1)
            
        Returns:
            Lista de TextSpanMetrics que intersectan
        """
        cache = self.ensure_page_cached(page_num)
        
        if not cache.is_valid:
            return []
        
        x0, y0, x1, y1 = rect
        result = []
        
        for span in cache.spans:
            bbox = span.bbox
            # Verificar intersección
            if not (bbox[2] < x0 or bbox[0] > x1 or bbox[3] < y0 or bbox[1] > y1):
                result.append(span)
        
        return result
    
    def hit_test_lines_in_rect(
        self,
        page_num: int,
        rect: Tuple[float, float, float, float]
    ) -> List[TextLine]:
        """
        Encontrar todas las líneas que intersectan con un rectángulo.
        
        Args:
            page_num: Número de página
            rect: Rectángulo (x0, y0, x1, y1)
            
        Returns:
            Lista de TextLine que intersectan
        """
        cache = self.ensure_page_cached(page_num)
        
        if not cache.is_valid:
            return []
        
        x0, y0, x1, y1 = rect
        result = []
        
        for line in cache.lines:
            bbox = line.bbox
            # Verificar intersección
            if not (bbox[2] < x0 or bbox[0] > x1 or bbox[3] < y0 or bbox[1] > y1):
                result.append(line)
        
        return result
    
    def get_span_by_id(
        self,
        page_num: int,
        span_id: str
    ) -> Optional[TextSpanMetrics]:
        """
        Obtener un span por su ID.
        
        Args:
            page_num: Número de página
            span_id: ID del span
            
        Returns:
            TextSpanMetrics o None si no se encuentra
        """
        cache = self.ensure_page_cached(page_num)
        
        if not cache.is_valid:
            return None
        
        for span in cache.spans:
            if span.span_id == span_id:
                return span
        
        return None
    
    def get_line_by_id(
        self, 
        page_num: int, 
        line_id: str
    ) -> Optional[TextLine]:
        """
        Obtener una línea por su ID.
        
        Args:
            page_num: Número de página
            line_id: ID de la línea
            
        Returns:
            TextLine o None si no se encuentra
        """
        cache = self.ensure_page_cached(page_num)
        
        if not cache.is_valid:
            return None
        
        for line in cache.lines:
            if line.line_id == line_id:
                return line
        
        return None
    
    # === Consultas de datos ===
    
    def get_all_spans(self, page_num: int) -> List[TextSpanMetrics]:
        """Obtener todos los spans de una página."""
        cache = self.ensure_page_cached(page_num)
        return cache.spans if cache.is_valid else []
    
    def get_all_lines(self, page_num: int) -> List[TextLine]:
        """Obtener todas las líneas de una página."""
        cache = self.ensure_page_cached(page_num)
        return cache.lines if cache.is_valid else []
    
    def get_page_text(self, page_num: int) -> str:
        """Obtener todo el texto de una página."""
        lines = self.get_all_lines(page_num)
        return "\n".join(line.text for line in lines)
    
    # === Utilidades ===
    
    def find_nearest_span(
        self,
        page_num: int,
        x: float,
        y: float,
        max_distance: float = 50.0
    ) -> Optional[TextSpanMetrics]:
        """
        Encontrar el span más cercano a un punto.
        
        Args:
            page_num: Número de página
            x, y: Coordenadas
            max_distance: Distancia máxima de búsqueda
            
        Returns:
            TextSpanMetrics más cercano o None
        """
        cache = self.ensure_page_cached(page_num)
        
        if not cache.is_valid:
            return None
        
        best_span = None
        best_dist = max_distance
        
        for span in cache.spans:
            bbox = span.bbox
            
            # Centro del span
            cx = (bbox[0] + bbox[2]) / 2
            cy = (bbox[1] + bbox[3]) / 2
            
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            
            if dist < best_dist:
                best_dist = dist
                best_span = span
        
        return best_span


# === Funciones de conveniencia ===

def create_hit_tester(document=None, font_manager=None) -> TextHitTester:
    """
    Crear un TextHitTester configurado.
    
    Args:
        document: Documento fitz.Document opcional
        font_manager: FontManager opcional
        
    Returns:
        TextHitTester configurado
    """
    tester = TextHitTester(font_manager=font_manager)
    if document:
        tester.set_document(document)
    return tester


def hit_test_point(
    document: fitz.Document,
    page_num: int,
    x: float,
    y: float,
    font_manager=None,
    tolerance: float = 5.0
) -> HitTestResult:
    """
    Conveniencia: hit-test en un punto sin crear instancia persistente.
    
    Args:
        document: Documento PDF
        page_num: Número de página
        x, y: Coordenadas
        font_manager: FontManager opcional
        tolerance: Tolerancia de búsqueda
        
    Returns:
        HitTestResult
    """
    tester = TextHitTester(font_manager=font_manager)
    tester.set_document(document)
    return tester.hit_test(page_num, x, y, tolerance)


def get_span_at_point(
    document: fitz.Document,
    page_num: int,
    x: float,
    y: float,
    font_manager=None
) -> Optional[TextSpanMetrics]:
    """
    Conveniencia: obtener span en un punto.
    
    Args:
        document: Documento PDF
        page_num: Número de página
        x, y: Coordenadas
        font_manager: FontManager opcional
        
    Returns:
        TextSpanMetrics o None
    """
    result = hit_test_point(document, page_num, x, y, font_manager)
    return result.span


def get_line_at_point(
    document: fitz.Document,
    page_num: int,
    x: float,
    y: float,
    font_manager=None
) -> Optional[TextLine]:
    """
    Conveniencia: obtener línea en un punto.
    
    Args:
        document: Documento PDF
        page_num: Número de página
        x, y: Coordenadas
        font_manager: FontManager opcional
        
    Returns:
        TextLine o None
    """
    result = hit_test_point(document, page_num, x, y, font_manager)
    return result.line

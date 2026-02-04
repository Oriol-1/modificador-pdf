"""
ClipboardHandler - Manejo de portapapeles con estilos para PDF Editor Pro

PHASE2-202: Copy/Paste with Styles
Permite copiar y pegar texto preservando información de fuente y estilo.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import logging

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QMimeData

from core.font_manager import FontDescriptor

logger = logging.getLogger(__name__)


# MIME type personalizado para datos con estilo
STYLED_TEXT_MIME = "application/x-pdf-editor-styled-text"


@dataclass
class StyledTextData:
    """
    Datos de texto con información de estilo.
    
    Attributes:
        text: El texto copiado
        font_descriptor: Información de fuente (opcional)
        position: Posición original (page, x, y)
        timestamp: Momento de la copia
        metadata: Datos adicionales
    """
    text: str
    font_descriptor: Optional[FontDescriptor] = None
    position: Optional[Dict[str, float]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario serializable."""
        result = {
            "text": self.text,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
        
        if self.font_descriptor:
            result["font_descriptor"] = {
                "name": self.font_descriptor.name,
                "size": self.font_descriptor.size,
                "color": self.font_descriptor.color,
                "flags": self.font_descriptor.flags,
                "was_fallback": self.font_descriptor.was_fallback,
                "fallback_from": self.font_descriptor.fallback_from,
                "possible_bold": self.font_descriptor.possible_bold
            }
        
        if self.position:
            result["position"] = self.position
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StyledTextData":
        """Crea desde diccionario."""
        font_descriptor = None
        if "font_descriptor" in data and data["font_descriptor"]:
            fd = data["font_descriptor"]
            font_descriptor = FontDescriptor(
                name=fd.get("name", "Arial"),
                size=fd.get("size", 12.0),
                color=fd.get("color", "#000000"),
                flags=fd.get("flags", 0),
                was_fallback=fd.get("was_fallback", False),
                fallback_from=fd.get("fallback_from"),
                possible_bold=fd.get("possible_bold")
            )
        
        return cls(
            text=data.get("text", ""),
            font_descriptor=font_descriptor,
            position=data.get("position"),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            metadata=data.get("metadata", {})
        )
    
    def to_json(self) -> str:
        """Serializa a JSON."""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> "StyledTextData":
        """Deserializa desde JSON."""
        data = json.loads(json_str)
        return cls.from_dict(data)


class ClipboardHandler:
    """
    Gestor de portapapeles con soporte para texto con estilos.
    
    Permite:
    - Copiar texto con información de fuente
    - Pegar preservando estilos
    - Fallback a texto plano si no hay estilos
    - Historial de copias recientes
    """
    
    def __init__(self, max_history: int = 10):
        """
        Inicializa el handler.
        
        Args:
            max_history: Número máximo de elementos en historial
        """
        self.max_history = max_history
        self.history: List[StyledTextData] = []
        self._clipboard = QApplication.clipboard()
        logger.info("ClipboardHandler inicializado")
    
    def copy_styled(
        self,
        text: str,
        font_descriptor: Optional[FontDescriptor] = None,
        position: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Copia texto con información de estilo al portapapeles.
        
        Args:
            text: Texto a copiar
            font_descriptor: Información de fuente (opcional)
            position: Posición original {page, x, y} (opcional)
            metadata: Datos adicionales (opcional)
            
        Returns:
            True si éxito, False si error
        """
        try:
            # Crear datos estructurados
            styled_data = StyledTextData(
                text=text,
                font_descriptor=font_descriptor,
                position=position,
                metadata=metadata or {}
            )
            
            # Crear MIME data con ambos formatos
            mime_data = QMimeData()
            
            # Texto plano (compatibilidad)
            mime_data.setText(text)
            
            # Datos con estilo (formato personalizado)
            mime_data.setData(STYLED_TEXT_MIME, styled_data.to_json().encode('utf-8'))
            
            # Establecer en clipboard
            self._clipboard.setMimeData(mime_data)
            
            # Añadir al historial
            self._add_to_history(styled_data)
            
            logger.debug(f"Copiado: '{text[:50]}...' con fuente={font_descriptor.name if font_descriptor else 'N/A'}")
            return True
            
        except Exception as e:
            logger.error(f"Error al copiar: {e}")
            return False
    
    def copy_plain(self, text: str) -> bool:
        """
        Copia texto sin estilos (método simple).
        
        Args:
            text: Texto a copiar
            
        Returns:
            True si éxito
        """
        return self.copy_styled(text)
    
    def paste_styled(self) -> Optional[StyledTextData]:
        """
        Pega texto con estilos si están disponibles.
        
        Returns:
            StyledTextData o None si no hay datos
        """
        try:
            mime_data = self._clipboard.mimeData()
            
            # Intentar obtener datos con estilo
            if mime_data.hasFormat(STYLED_TEXT_MIME):
                json_bytes = mime_data.data(STYLED_TEXT_MIME)
                json_str = json_bytes.data().decode('utf-8')
                styled_data = StyledTextData.from_json(json_str)
                logger.debug(f"Pegado con estilos: '{styled_data.text[:50]}...'")
                return styled_data
            
            # Fallback a texto plano
            if mime_data.hasText():
                text = mime_data.text()
                logger.debug(f"Pegado texto plano: '{text[:50]}...'")
                return StyledTextData(text=text)
            
            return None
            
        except Exception as e:
            logger.error(f"Error al pegar: {e}")
            return None
    
    def paste_plain(self) -> Optional[str]:
        """
        Pega solo el texto (sin estilos).
        
        Returns:
            Texto o None si no hay datos
        """
        styled = self.paste_styled()
        return styled.text if styled else None
    
    def has_styled_content(self) -> bool:
        """
        Verifica si el portapapeles tiene contenido con estilos.
        
        Returns:
            True si hay datos con estilo
        """
        mime_data = self._clipboard.mimeData()
        return mime_data.hasFormat(STYLED_TEXT_MIME)
    
    def has_any_content(self) -> bool:
        """
        Verifica si el portapapeles tiene cualquier contenido de texto.
        
        Returns:
            True si hay texto
        """
        mime_data = self._clipboard.mimeData()
        return mime_data.hasText() or mime_data.hasFormat(STYLED_TEXT_MIME)
    
    def get_preview(self, max_length: int = 50) -> Optional[str]:
        """
        Obtiene un preview del contenido del portapapeles.
        
        Args:
            max_length: Longitud máxima del preview
            
        Returns:
            Preview del texto o None
        """
        styled = self.paste_styled()
        if styled:
            text = styled.text
            if len(text) > max_length:
                return text[:max_length] + "..."
            return text
        return None
    
    def _add_to_history(self, data: StyledTextData) -> None:
        """Añade al historial de copias."""
        self.history.insert(0, data)
        
        # Limitar tamaño
        while len(self.history) > self.max_history:
            self.history.pop()
    
    def get_history(self) -> List[StyledTextData]:
        """
        Obtiene el historial de copias.
        
        Returns:
            Lista de StyledTextData (más reciente primero)
        """
        return self.history.copy()
    
    def clear_history(self) -> None:
        """Limpia el historial."""
        self.history.clear()
        logger.debug("Historial de clipboard limpiado")
    
    def paste_from_history(self, index: int) -> Optional[StyledTextData]:
        """
        Recupera un elemento del historial.
        
        Args:
            index: Índice en el historial (0 = más reciente)
            
        Returns:
            StyledTextData o None si índice inválido
        """
        if 0 <= index < len(self.history):
            return self.history[index]
        return None
    
    def clear(self) -> None:
        """Limpia el portapapeles."""
        self._clipboard.clear()
        logger.debug("Clipboard limpiado")


# Singleton global
_clipboard_handler: Optional[ClipboardHandler] = None


def get_clipboard_handler() -> ClipboardHandler:
    """
    Obtiene la instancia global del ClipboardHandler.
    
    Returns:
        Instancia de ClipboardHandler
    """
    global _clipboard_handler
    if _clipboard_handler is None:
        _clipboard_handler = ClipboardHandler()
    return _clipboard_handler


def reset_clipboard_handler() -> None:
    """Resetea el handler global."""
    global _clipboard_handler
    _clipboard_handler = None


# Funciones de conveniencia
def copy_text(
    text: str,
    font_descriptor: Optional[FontDescriptor] = None,
    **kwargs
) -> bool:
    """
    Función de conveniencia para copiar texto.
    
    Args:
        text: Texto a copiar
        font_descriptor: Información de fuente (opcional)
        **kwargs: Argumentos adicionales (position, metadata)
        
    Returns:
        True si éxito
    """
    return get_clipboard_handler().copy_styled(text, font_descriptor, **kwargs)


def paste_text() -> Optional[StyledTextData]:
    """
    Función de conveniencia para pegar texto.
    
    Returns:
        StyledTextData o None
    """
    return get_clipboard_handler().paste_styled()


def has_clipboard_content() -> bool:
    """
    Verifica si hay contenido en el portapapeles.
    
    Returns:
        True si hay contenido
    """
    return get_clipboard_handler().has_any_content()

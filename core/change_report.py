"""
ChangeReport - Sistema de tracking de cambios para PDF Editor Pro

Responsable de:
1. Registrar cada cambio realizado en un PDF
2. Almacenar información detallada (fuente, posición, contenido)
3. Generar reportes de cambios para resumen
4. Permitir exportar historial de modificaciones

PHASE2-103: Implementación completa
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Tipos de cambios soportados."""
    TEXT_EDIT = "text_edit"           # Edición de texto existente
    TEXT_ADD = "text_add"             # Añadir texto nuevo
    TEXT_DELETE = "text_delete"       # Eliminar texto
    TEXT_MOVE = "text_move"           # Mover texto
    FONT_CHANGE = "font_change"       # Cambio de fuente
    SIZE_CHANGE = "size_change"       # Cambio de tamaño
    COLOR_CHANGE = "color_change"     # Cambio de color
    STYLE_CHANGE = "style_change"     # Cambio de estilo (bold, italic)
    IMAGE_ADD = "image_add"           # Añadir imagen
    IMAGE_DELETE = "image_delete"     # Eliminar imagen
    PAGE_ADD = "page_add"             # Añadir página
    PAGE_DELETE = "page_delete"       # Eliminar página
    PAGE_ROTATE = "page_rotate"       # Rotar página


@dataclass
class ChangePosition:
    """Posición de un cambio en el documento."""
    page: int
    x: float
    y: float
    width: Optional[float] = None
    height: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            "page": self.page,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChangePosition":
        """Crea desde diccionario."""
        return cls(
            page=data.get("page", 0),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            width=data.get("width"),
            height=data.get("height")
        )


@dataclass
class FontInfo:
    """Información de fuente para un cambio."""
    name: str
    size: float
    color: str = "#000000"
    bold: bool = False
    italic: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            "name": self.name,
            "size": self.size,
            "color": self.color,
            "bold": self.bold,
            "italic": self.italic
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FontInfo":
        """Crea desde diccionario."""
        return cls(
            name=data.get("name", "Arial"),
            size=data.get("size", 12.0),
            color=data.get("color", "#000000"),
            bold=data.get("bold", False),
            italic=data.get("italic", False)
        )


@dataclass
class Change:
    """
    Representa un cambio individual en el documento.
    
    Attributes:
        change_type: Tipo de cambio (ChangeType enum)
        position: Posición del cambio en el documento
        timestamp: Momento del cambio
        old_value: Valor anterior (si aplica)
        new_value: Valor nuevo (si aplica)
        font_info: Información de fuente (si aplica)
        metadata: Datos adicionales específicos del cambio
    """
    change_type: ChangeType
    position: ChangePosition
    timestamp: datetime = field(default_factory=datetime.now)
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    font_info: Optional[FontInfo] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario serializable."""
        return {
            "change_type": self.change_type.value,
            "position": self.position.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "old_value": self.old_value,
            "new_value": self.new_value,
            "font_info": self.font_info.to_dict() if self.font_info else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Change":
        """Crea desde diccionario."""
        return cls(
            change_type=ChangeType(data.get("change_type", "text_edit")),
            position=ChangePosition.from_dict(data.get("position", {})),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            old_value=data.get("old_value"),
            new_value=data.get("new_value"),
            font_info=FontInfo.from_dict(data["font_info"]) if data.get("font_info") else None,
            metadata=data.get("metadata", {})
        )
    
    def get_description(self) -> str:
        """Genera descripción legible del cambio."""
        descriptions = {
            ChangeType.TEXT_EDIT: f"Texto editado: '{self.old_value}' → '{self.new_value}'",
            ChangeType.TEXT_ADD: f"Texto añadido: '{self.new_value}'",
            ChangeType.TEXT_DELETE: f"Texto eliminado: '{self.old_value}'",
            ChangeType.TEXT_MOVE: f"Texto movido a página {self.position.page}",
            ChangeType.FONT_CHANGE: f"Fuente cambiada: {self.old_value} → {self.new_value}",
            ChangeType.SIZE_CHANGE: f"Tamaño cambiado: {self.old_value} → {self.new_value}",
            ChangeType.COLOR_CHANGE: f"Color cambiado: {self.old_value} → {self.new_value}",
            ChangeType.STYLE_CHANGE: f"Estilo cambiado: {self.old_value} → {self.new_value}",
            ChangeType.IMAGE_ADD: "Imagen añadida",
            ChangeType.IMAGE_DELETE: "Imagen eliminada",
            ChangeType.PAGE_ADD: f"Página añadida: {self.position.page}",
            ChangeType.PAGE_DELETE: f"Página eliminada: {self.position.page}",
            ChangeType.PAGE_ROTATE: f"Página rotada: {self.metadata.get('degrees', 0)}°"
        }
        return descriptions.get(self.change_type, "Cambio desconocido")


class ChangeReport:
    """
    Gestor de reportes de cambios para un documento PDF.
    
    Permite:
    - Registrar cambios individuales
    - Generar estadísticas
    - Exportar/importar historial
    - Filtrar por tipo/página/fecha
    """
    
    def __init__(self, document_path: Optional[str] = None):
        """
        Inicializa el reporte de cambios.
        
        Args:
            document_path: Ruta del documento (opcional)
        """
        self.document_path = document_path
        self.changes: List[Change] = []
        self.created_at = datetime.now()
        self.modified_at = datetime.now()
        logger.info(f"ChangeReport inicializado para: {document_path or 'nuevo documento'}")
    
    def add_change(self, change: Change) -> None:
        """
        Añade un cambio al reporte.
        
        Args:
            change: Objeto Change a registrar
        """
        self.changes.append(change)
        self.modified_at = datetime.now()
        logger.debug(f"Cambio registrado: {change.get_description()}")
    
    def add_text_edit(
        self,
        page: int,
        x: float,
        y: float,
        old_text: str,
        new_text: str,
        font_name: Optional[str] = None,
        font_size: Optional[float] = None,
        font_color: Optional[str] = None
    ) -> Change:
        """
        Atajo para registrar edición de texto.
        
        Args:
            page: Número de página
            x, y: Coordenadas
            old_text: Texto original
            new_text: Texto nuevo
            font_name: Nombre de fuente (opcional)
            font_size: Tamaño de fuente (opcional)
            font_color: Color de fuente (opcional)
            
        Returns:
            Change creado
        """
        font_info = None
        if font_name or font_size or font_color:
            font_info = FontInfo(
                name=font_name or "Arial",
                size=font_size or 12.0,
                color=font_color or "#000000"
            )
        
        change = Change(
            change_type=ChangeType.TEXT_EDIT,
            position=ChangePosition(page=page, x=x, y=y),
            old_value=old_text,
            new_value=new_text,
            font_info=font_info
        )
        self.add_change(change)
        return change
    
    def add_text_add(
        self,
        page: int,
        x: float,
        y: float,
        text: str,
        font_name: str = "Arial",
        font_size: float = 12.0,
        font_color: str = "#000000"
    ) -> Change:
        """
        Atajo para registrar texto añadido.
        
        Args:
            page: Número de página
            x, y: Coordenadas
            text: Texto añadido
            font_name: Nombre de fuente
            font_size: Tamaño de fuente
            font_color: Color de fuente
            
        Returns:
            Change creado
        """
        change = Change(
            change_type=ChangeType.TEXT_ADD,
            position=ChangePosition(page=page, x=x, y=y),
            new_value=text,
            font_info=FontInfo(
                name=font_name,
                size=font_size,
                color=font_color
            )
        )
        self.add_change(change)
        return change
    
    def add_text_delete(
        self,
        page: int,
        x: float,
        y: float,
        deleted_text: str
    ) -> Change:
        """
        Atajo para registrar texto eliminado.
        
        Args:
            page: Número de página
            x, y: Coordenadas
            deleted_text: Texto eliminado
            
        Returns:
            Change creado
        """
        change = Change(
            change_type=ChangeType.TEXT_DELETE,
            position=ChangePosition(page=page, x=x, y=y),
            old_value=deleted_text
        )
        self.add_change(change)
        return change
    
    def get_changes_by_page(self, page: int) -> List[Change]:
        """
        Obtiene cambios de una página específica.
        
        Args:
            page: Número de página
            
        Returns:
            Lista de cambios en esa página
        """
        return [c for c in self.changes if c.position.page == page]
    
    def get_changes_by_type(self, change_type: ChangeType) -> List[Change]:
        """
        Obtiene cambios de un tipo específico.
        
        Args:
            change_type: Tipo de cambio a filtrar
            
        Returns:
            Lista de cambios de ese tipo
        """
        return [c for c in self.changes if c.change_type == change_type]
    
    def get_changes_in_range(
        self,
        start: datetime,
        end: datetime
    ) -> List[Change]:
        """
        Obtiene cambios en un rango de tiempo.
        
        Args:
            start: Inicio del rango
            end: Fin del rango
            
        Returns:
            Lista de cambios en ese rango
        """
        return [c for c in self.changes if start <= c.timestamp <= end]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Genera estadísticas del reporte.
        
        Returns:
            Diccionario con estadísticas
        """
        stats = {
            "total_changes": len(self.changes),
            "changes_by_type": {},
            "changes_by_page": {},
            "fonts_used": set(),
            "first_change": None,
            "last_change": None
        }
        
        for change in self.changes:
            # Por tipo
            type_name = change.change_type.value
            stats["changes_by_type"][type_name] = stats["changes_by_type"].get(type_name, 0) + 1
            
            # Por página
            page = change.position.page
            stats["changes_by_page"][page] = stats["changes_by_page"].get(page, 0) + 1
            
            # Fuentes
            if change.font_info:
                stats["fonts_used"].add(change.font_info.name)
        
        # Convertir set a lista para serialización
        stats["fonts_used"] = list(stats["fonts_used"])
        
        # Timestamps
        if self.changes:
            sorted_changes = sorted(self.changes, key=lambda c: c.timestamp)
            stats["first_change"] = sorted_changes[0].timestamp.isoformat()
            stats["last_change"] = sorted_changes[-1].timestamp.isoformat()
        
        return stats
    
    def generate_summary(self) -> str:
        """
        Genera resumen legible del reporte.
        
        Returns:
            Texto con resumen de cambios
        """
        stats = self.get_statistics()
        
        lines = [
            "=" * 50,
            "REPORTE DE CAMBIOS",
            "=" * 50,
            f"Documento: {self.document_path or 'Sin nombre'}",
            f"Creado: {self.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"Modificado: {self.modified_at.strftime('%Y-%m-%d %H:%M')}",
            "",
            f"Total de cambios: {stats['total_changes']}",
            "",
            "CAMBIOS POR TIPO:",
            "-" * 30
        ]
        
        for change_type, count in stats["changes_by_type"].items():
            lines.append(f"  {change_type}: {count}")
        
        lines.extend([
            "",
            "CAMBIOS POR PÁGINA:",
            "-" * 30
        ])
        
        for page, count in sorted(stats["changes_by_page"].items()):
            lines.append(f"  Página {page + 1}: {count} cambios")
        
        if stats["fonts_used"]:
            lines.extend([
                "",
                "FUENTES UTILIZADAS:",
                "-" * 30
            ])
            for font in sorted(stats["fonts_used"]):
                lines.append(f"  • {font}")
        
        lines.extend([
            "",
            "DETALLE DE CAMBIOS:",
            "-" * 30
        ])
        
        for i, change in enumerate(self.changes, 1):
            lines.append(f"{i}. [{change.timestamp.strftime('%H:%M:%S')}] {change.get_description()}")
        
        lines.append("=" * 50)
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario serializable."""
        return {
            "document_path": self.document_path,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "changes": [c.to_dict() for c in self.changes]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChangeReport":
        """Crea desde diccionario."""
        report = cls(document_path=data.get("document_path"))
        report.created_at = datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
        report.modified_at = datetime.fromisoformat(data.get("modified_at", datetime.now().isoformat()))
        report.changes = [Change.from_dict(c) for c in data.get("changes", [])]
        return report
    
    def export_json(self, filepath: str) -> bool:
        """
        Exporta reporte a JSON.
        
        Args:
            filepath: Ruta del archivo JSON
            
        Returns:
            True si éxito, False si error
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"Reporte exportado a: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error exportando reporte: {e}")
            return False
    
    @classmethod
    def import_json(cls, filepath: str) -> Optional["ChangeReport"]:
        """
        Importa reporte desde JSON.
        
        Args:
            filepath: Ruta del archivo JSON
            
        Returns:
            ChangeReport o None si error
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            report = cls.from_dict(data)
            logger.info(f"Reporte importado desde: {filepath}")
            return report
        except Exception as e:
            logger.error(f"Error importando reporte: {e}")
            return None
    
    def clear(self) -> None:
        """Limpia todos los cambios."""
        self.changes.clear()
        self.modified_at = datetime.now()
        logger.info("Reporte de cambios limpiado")
    
    def undo_last(self) -> Optional[Change]:
        """
        Elimina y retorna el último cambio.
        
        Returns:
            Último cambio eliminado o None
        """
        if self.changes:
            change = self.changes.pop()
            self.modified_at = datetime.now()
            logger.debug(f"Cambio deshecho: {change.get_description()}")
            return change
        return None
    
    def __len__(self) -> int:
        """Retorna número de cambios."""
        return len(self.changes)
    
    def __bool__(self) -> bool:
        """True si hay cambios."""
        return bool(self.changes)


# Singleton para acceso global
_global_report: Optional[ChangeReport] = None


def get_change_report(document_path: Optional[str] = None) -> ChangeReport:
    """
    Obtiene o crea el reporte de cambios global.
    
    Args:
        document_path: Ruta del documento (para nuevo reporte)
        
    Returns:
        Instancia de ChangeReport
    """
    global _global_report
    if _global_report is None or document_path:
        _global_report = ChangeReport(document_path)
    return _global_report


def reset_change_report() -> None:
    """Resetea el reporte global."""
    global _global_report
    _global_report = None

"""
Sistema de identidad de página basado en UUID.

Mantiene una correspondencia bidireccional entre UUIDs inmutables
y los índices posicionales de página del PDF. Esto permite que las
operaciones de reordenamiento e inserción no corrompan los datos
asociados a cada página (textos editados, highlights, etc.).
"""

import uuid
from typing import Dict, List, Optional


class PageIdentityMap:
    """
    Mapa de identidad de páginas: UUID inmutable ↔ índice posicional.
    
    Invariante: len(self._order) == doc.page_count en todo momento.
    """
    
    def __init__(self):
        self._order: List[str] = []  # [uuid_pag0, uuid_pag1, ...]
    
    # --- Inicialización ---
    
    def initialize(self, page_count: int):
        """Crea UUIDs para un documento recién abierto."""
        self._order = [str(uuid.uuid4()) for _ in range(page_count)]
    
    # --- Consultas ---
    
    def uuid_for_index(self, page_index: int) -> Optional[str]:
        """Devuelve el UUID de la página en la posición dada."""
        if 0 <= page_index < len(self._order):
            return self._order[page_index]
        return None
    
    def index_for_uuid(self, page_uuid: str) -> Optional[int]:
        """Devuelve el índice actual de la página con ese UUID."""
        try:
            return self._order.index(page_uuid)
        except ValueError:
            return None
    
    @property
    def page_count(self) -> int:
        return len(self._order)
    
    @property
    def order(self) -> List[str]:
        """Lista ordenada de UUIDs (posición = índice de página)."""
        return list(self._order)
    
    # --- Mutaciones ---
    
    def insert_pages(self, at_index: int, count: int) -> List[str]:
        """
        Inserta 'count' páginas nuevas en la posición 'at_index'.
        Retorna la lista de nuevos UUIDs creados.
        """
        new_uuids = [str(uuid.uuid4()) for _ in range(count)]
        for i, uid in enumerate(new_uuids):
            self._order.insert(at_index + i, uid)
        return new_uuids
    
    def remove_page(self, page_index: int) -> Optional[str]:
        """Elimina una página. Retorna el UUID eliminado o None si el índice es inválido."""
        if len(self._order) <= 1:
            return None  # No eliminar la última página
        if 0 <= page_index < len(self._order):
            return self._order.pop(page_index)
        return None
    
    def reorder(self, new_order: List[int]) -> bool:
        """
        Reordena páginas. new_order[nueva_pos] = vieja_pos.
        Ejemplo: [2, 0, 1] → la página que era 2 pasa a ser 0, etc.
        Retorna True si el reorden es válido.
        """
        if not self._is_valid_permutation(new_order):
            return False
        self._order = [self._order[i] for i in new_order]
        return True
    
    def move_page(self, from_index: int, to_index: int) -> bool:
        """
        Mueve una página de from_index a to_index.
        Retorna True si la operación es válida.
        """
        if not (0 <= from_index < len(self._order)):
            return False
        if not (0 <= to_index < len(self._order)):
            return False
        if from_index == to_index:
            return False
        uid = self._order.pop(from_index)
        self._order.insert(to_index, uid)
        return True
    
    # --- Serialización (para snapshots de undo/redo) ---
    
    def to_list(self) -> List[str]:
        """Serializa para snapshot."""
        return list(self._order)
    
    def from_list(self, order: List[str]):
        """Restaura desde snapshot."""
        self._order = list(order) if order else []
    
    # --- Validación ---
    
    def _is_valid_permutation(self, order: List[int]) -> bool:
        """Verifica que order sea una permutación válida de range(page_count)."""
        return sorted(order) == list(range(len(self._order)))

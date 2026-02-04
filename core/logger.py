"""
Sistema de logging configurable para el editor PDF.
Permite activar/desactivar logs de debug sin modificar el código.
"""

import os

# Niveles de debug (se pueden combinar)
DEBUG_NONE = 0
DEBUG_RENDER = 1      # Logs de renderizado de páginas
DEBUG_COORDS = 2      # Logs de conversión de coordenadas
DEBUG_EDIT = 4        # Logs de edición de texto
DEBUG_UNDO = 8        # Logs de undo/redo
DEBUG_SELECTION = 16  # Logs de selección
DEBUG_OVERLAY = 32    # Logs de overlays
DEBUG_ALL = 255       # Todos los logs

# Nivel de debug actual (cambiar para activar/desactivar)
# En producción: DEBUG_NONE
# Para debugging: DEBUG_ALL o combinación específica
_debug_level = DEBUG_NONE

# Permitir configurar via variable de entorno
_env_debug = os.environ.get('PDF_EDITOR_DEBUG', '')
if _env_debug:
    try:
        _debug_level = int(_env_debug)
    except ValueError:
        if _env_debug.upper() == 'ALL':
            _debug_level = DEBUG_ALL


def set_debug_level(level: int):
    """Configura el nivel de debug."""
    global _debug_level
    _debug_level = level


def get_debug_level() -> int:
    """Obtiene el nivel de debug actual."""
    return _debug_level


def debug_print(category: int, message: str):
    """Imprime mensaje de debug si la categoría está activa."""
    if _debug_level & category:
        print(message)


def debug_render(message: str):
    """Log de renderizado."""
    debug_print(DEBUG_RENDER, message)


def debug_coords(message: str):
    """Log de coordenadas."""
    debug_print(DEBUG_COORDS, message)


def debug_edit(message: str):
    """Log de edición."""
    debug_print(DEBUG_EDIT, message)


def debug_undo(message: str):
    """Log de undo/redo."""
    debug_print(DEBUG_UNDO, message)


def debug_selection(message: str):
    """Log de selección."""
    debug_print(DEBUG_SELECTION, message)


def debug_overlay(message: str):
    """Log de overlays."""
    debug_print(DEBUG_OVERLAY, message)

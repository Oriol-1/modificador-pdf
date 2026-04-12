"""Configuración compartida de pytest para todo el proyecto.

Se asegura de que el directorio raíz del proyecto esté en sys.path
para que los imports absolutos (from core.X, from ui.X) funcionen
desde cualquier subcarpeta de tests.
"""
import sys
import os

# Asegurar que la raíz del proyecto está en sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

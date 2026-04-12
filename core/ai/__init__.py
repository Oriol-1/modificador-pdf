"""Paquete de inteligencia artificial para asistente de PDF.

Provee funcionalidad de chat con RAG, traducción y
análisis de documentos PDF.
"""

import logging

logger = logging.getLogger(__name__)

# Dependencias opcionales

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    openai = None
    HAS_OPENAI = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False


def is_ai_available() -> bool:
    """Verifica si las dependencias mínimas de IA están disponibles."""
    return HAS_NUMPY

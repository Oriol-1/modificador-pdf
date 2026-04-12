"""Configuración del asistente de IA.

Gestiona proveedores LLM, embeddings y parámetros
de búsqueda RAG.
"""

from dataclasses import dataclass
from enum import Enum
import json
import os
import logging

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Proveedor de modelo de lenguaje."""
    OPENAI = "openai"
    OLLAMA = "ollama"
    NONE = "none"


class EmbeddingProvider(Enum):
    """Proveedor de embeddings."""
    TFIDF = "tfidf"
    OPENAI = "openai"
    SENTENCE_TRANSFORMERS = "sentence_transformers"


@dataclass
class AIConfig:
    """Configuración del asistente de IA.

    Attributes:
        llm_provider: Proveedor de LLM a usar.
        embedding_provider: Proveedor de embeddings.
        openai_api_key: Clave API de OpenAI.
        openai_model: Modelo de OpenAI a usar.
        ollama_url: URL del servidor Ollama.
        ollama_model: Modelo de Ollama a usar.
        chunk_size: Tamaño de chunk en caracteres.
        chunk_overlap: Solapamiento entre chunks.
        top_k: Número de chunks relevantes a recuperar.
        temperature: Temperatura para generación de texto.
    """
    llm_provider: LLMProvider = LLMProvider.NONE
    embedding_provider: EmbeddingProvider = EmbeddingProvider.TFIDF
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5
    temperature: float = 0.3

    def to_dict(self) -> dict:
        """Serializa la configuración a diccionario."""
        return {
            "llm_provider": self.llm_provider.value,
            "embedding_provider": self.embedding_provider.value,
            "openai_api_key": self.openai_api_key,
            "openai_model": self.openai_model,
            "ollama_url": self.ollama_url,
            "ollama_model": self.ollama_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "top_k": self.top_k,
            "temperature": self.temperature,
        }

    @staticmethod
    def from_dict(data: dict) -> 'AIConfig':
        """Deserializa configuración desde diccionario."""
        return AIConfig(
            llm_provider=LLMProvider(data.get("llm_provider", "none")),
            embedding_provider=EmbeddingProvider(data.get("embedding_provider", "tfidf")),
            openai_api_key=data.get("openai_api_key", ""),
            openai_model=data.get("openai_model", "gpt-4o-mini"),
            ollama_url=data.get("ollama_url", "http://localhost:11434"),
            ollama_model=data.get("ollama_model", "llama3.2"),
            chunk_size=data.get("chunk_size", 500),
            chunk_overlap=data.get("chunk_overlap", 50),
            top_k=data.get("top_k", 5),
            temperature=data.get("temperature", 0.3),
        )

    def save(self, path: str) -> None:
        """Guarda la configuración en un archivo JSON."""
        data = self.to_dict()
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Configuración IA guardada en {path}")

    @staticmethod
    def load(path: str) -> 'AIConfig':
        """Carga la configuración desde un archivo JSON."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Configuración IA cargada desde {path}")
            return AIConfig.from_dict(data)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"No se pudo cargar configuración IA: {e}")
            return AIConfig()

    @property
    def has_llm(self) -> bool:
        """Indica si hay un proveedor LLM configurado."""
        if self.llm_provider == LLMProvider.OPENAI:
            return bool(self.openai_api_key)
        if self.llm_provider == LLMProvider.OLLAMA:
            return True
        return False

"""Almacén de embeddings vectoriales para búsqueda semántica.

Soporta TF-IDF (built-in), OpenAI embeddings, y
sentence-transformers como proveedores.
"""

from dataclasses import dataclass
from typing import List, Tuple
import logging
import re
from collections import Counter

from core.ai import HAS_NUMPY
from core.ai.document_indexer import TextChunk

logger = logging.getLogger(__name__)

if HAS_NUMPY:
    import numpy as np


@dataclass
class SearchResult:
    """Resultado de búsqueda semántica.

    Attributes:
        chunk: Chunk de texto encontrado.
        score: Puntuación de similitud (0-1).
        rank: Posición en el ranking.
    """
    chunk: TextChunk
    score: float
    rank: int = 0


class TFIDFEmbedder:
    """Embedder basado en TF-IDF. Sin dependencias externas.

    Usa numpy para cálculos vectoriales eficientes.
    """

    def __init__(self):
        """Inicializa el embedder TF-IDF."""
        self._vocabulary: dict = {}
        self._idf = None
        self._doc_vectors = None
        self._fitted = False

    def _tokenize(self, text: str) -> List[str]:
        """Tokeniza texto en palabras normalizadas."""
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return [t for t in tokens if len(t) > 1]

    def fit(self, texts: List[str]) -> None:
        """Ajusta el modelo TF-IDF a los textos dados.

        Args:
            texts: Lista de textos para construir vocabulario.
        """
        if not HAS_NUMPY:
            raise RuntimeError("numpy es requerido para TFIDFEmbedder")

        all_tokens = set()
        doc_tokens = []
        for text in texts:
            tokens = self._tokenize(text)
            doc_tokens.append(tokens)
            all_tokens.update(tokens)

        self._vocabulary = {
            token: idx for idx, token in enumerate(sorted(all_tokens))
        }
        vocab_size = len(self._vocabulary)

        if vocab_size == 0:
            self._fitted = True
            return

        n_docs = len(texts)

        df = np.zeros(vocab_size)
        for tokens in doc_tokens:
            seen = set(tokens)
            for token in seen:
                if token in self._vocabulary:
                    df[self._vocabulary[token]] += 1

        self._idf = np.log((n_docs + 1) / (df + 1)) + 1

        self._doc_vectors = np.zeros((n_docs, vocab_size))
        for i, tokens in enumerate(doc_tokens):
            tf = Counter(tokens)
            for token, count in tf.items():
                if token in self._vocabulary:
                    idx = self._vocabulary[token]
                    self._doc_vectors[i, idx] = count * self._idf[idx]

            norm = np.linalg.norm(self._doc_vectors[i])
            if norm > 0:
                self._doc_vectors[i] /= norm

        self._fitted = True
        logger.debug(f"TF-IDF ajustado: {vocab_size} términos, {n_docs} docs")

    def embed_query(self, text: str):
        """Genera embedding TF-IDF para una consulta.

        Args:
            text: Texto de consulta.

        Returns:
            Vector numpy normalizado.
        """
        if not self._fitted or not self._vocabulary:
            return np.zeros(1)

        vocab_size = len(self._vocabulary)
        vector = np.zeros(vocab_size)
        tokens = self._tokenize(text)
        tf = Counter(tokens)

        for token, count in tf.items():
            if token in self._vocabulary:
                idx = self._vocabulary[token]
                vector[idx] = count * self._idf[idx]

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm

        return vector

    def search(self, query: str, top_k: int = 5) -> List[Tuple[int, float]]:
        """Busca los documentos más similares a la consulta.

        Args:
            query: Texto de consulta.
            top_k: Número de resultados.

        Returns:
            Lista de (índice_documento, score).
        """
        if not self._fitted or self._doc_vectors is None:
            return []
        if len(self._doc_vectors) == 0:
            return []

        query_vector = self.embed_query(query)
        if len(query_vector) != self._doc_vectors.shape[1]:
            return []

        scores = self._doc_vectors @ query_vector
        top_indices = np.argsort(scores)[::-1][:top_k]

        return [
            (int(idx), float(scores[idx]))
            for idx in top_indices
            if scores[idx] > 0
        ]


class EmbeddingStore:
    """Almacén de embeddings con búsqueda semántica.

    Soporta múltiples proveedores de embeddings.
    """

    def __init__(self):
        """Inicializa el almacén."""
        self._chunks: List[TextChunk] = []
        self._embedder = TFIDFEmbedder()
        self._indexed = False

    def index_chunks(self, chunks: List[TextChunk]) -> None:
        """Indexa una lista de chunks para búsqueda.

        Args:
            chunks: Lista de TextChunk a indexar.
        """
        self._chunks = list(chunks)
        texts = [chunk.text for chunk in chunks]
        self._embedder.fit(texts)
        self._indexed = True
        logger.info(f"Indexados {len(chunks)} chunks para búsqueda")

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """Busca chunks relevantes para la consulta.

        Args:
            query: Texto de consulta.
            top_k: Número máximo de resultados.

        Returns:
            Lista de SearchResult ordenados por relevancia.
        """
        if not self._indexed or not self._chunks:
            return []

        raw_results = self._embedder.search(query, top_k)

        results = []
        for rank, (idx, score) in enumerate(raw_results):
            if idx < len(self._chunks):
                results.append(SearchResult(
                    chunk=self._chunks[idx],
                    score=score,
                    rank=rank,
                ))

        return results

    @property
    def is_indexed(self) -> bool:
        """Indica si hay chunks indexados."""
        return self._indexed

    @property
    def chunk_count(self) -> int:
        """Número de chunks indexados."""
        return len(self._chunks)

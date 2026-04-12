"""Motor de chat con RAG para consultas sobre documentos PDF.

Soporta múltiples proveedores LLM: OpenAI, Ollama.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import json
import logging
import re
import urllib.request
import urllib.error

from core.ai import HAS_OPENAI
from core.ai.ai_config import AIConfig, LLMProvider
from core.ai.document_indexer import DocumentIndex
from core.ai.embedding_store import EmbeddingStore, SearchResult

logger = logging.getLogger(__name__)

if HAS_OPENAI:
    import openai


class MessageRole(Enum):
    """Rol del mensaje en la conversación."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Citation:
    """Cita a una sección del documento.

    Attributes:
        page_num: Número de página (0-based).
        text: Texto citado.
        chunk_id: ID del chunk fuente.
    """
    page_num: int
    text: str
    chunk_id: int = 0


@dataclass
class ChatMessage:
    """Mensaje en la conversación de chat.

    Attributes:
        role: Rol del mensaje.
        content: Contenido textual.
        citations: Citas al documento (solo para assistant).
    """
    role: MessageRole
    content: str
    citations: List[Citation] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serializa a diccionario."""
        return {
            "role": self.role.value,
            "content": self.content,
        }


def build_rag_prompt(
    query: str,
    context_chunks: List[SearchResult],
    system_prompt: str = "",
) -> List[dict]:
    """Construye el prompt RAG con contexto del documento.

    Args:
        query: Pregunta del usuario.
        context_chunks: Chunks relevantes encontrados.
        system_prompt: Prompt de sistema personalizado.

    Returns:
        Lista de mensajes para el LLM.
    """
    if not system_prompt:
        system_prompt = (
            "Eres un asistente experto en análisis de documentos PDF. "
            "Responde las preguntas del usuario basándote ÚNICAMENTE en el "
            "contexto proporcionado del documento. Si la información no está "
            "en el contexto, indícalo claramente. Cita las páginas relevantes "
            "usando el formato [Página X]."
        )

    context_parts = []
    for result in context_chunks:
        chunk = result.chunk
        context_parts.append(
            f"[Página {chunk.page_num + 1}] {chunk.text}"
        )

    context_text = (
        "\n\n---\n\n".join(context_parts)
        if context_parts
        else "(Sin contexto disponible)"
    )

    user_message = (
        f"Contexto del documento:\n{context_text}\n\n"
        f"Pregunta: {query}"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]


def call_openai(
    messages: List[dict],
    config: AIConfig,
) -> str:
    """Llama a la API de OpenAI.

    Args:
        messages: Mensajes de la conversación.
        config: Configuración de IA.

    Returns:
        Respuesta del modelo.

    Raises:
        RuntimeError: Si openai no está disponible o falla la API.
    """
    if not HAS_OPENAI:
        raise RuntimeError("El paquete 'openai' no está instalado")

    if not config.openai_api_key:
        raise RuntimeError("API key de OpenAI no configurada")

    client = openai.OpenAI(api_key=config.openai_api_key)
    response = client.chat.completions.create(
        model=config.openai_model,
        messages=messages,
        temperature=config.temperature,
    )
    return response.choices[0].message.content


def call_ollama(
    messages: List[dict],
    config: AIConfig,
) -> str:
    """Llama a un servidor Ollama local.

    Args:
        messages: Mensajes de la conversación.
        config: Configuración de IA.

    Returns:
        Respuesta del modelo.

    Raises:
        RuntimeError: Si Ollama no está disponible.
    """
    url = f"{config.ollama_url}/api/chat"
    payload = json.dumps({
        "model": config.ollama_model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": config.temperature,
        },
    }).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get("message", {}).get("content", "")
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"No se pudo conectar a Ollama en {config.ollama_url}. "
            f"Asegúrese de que Ollama está ejecutándose: {e}"
        )


def extract_citations(
    response: str,
    context_chunks: List[SearchResult],
) -> List[Citation]:
    """Extrae citas de la respuesta basándose en el contexto.

    Args:
        response: Respuesta del LLM.
        context_chunks: Chunks de contexto usados.

    Returns:
        Lista de citas encontradas.
    """
    citations = []
    seen_pages = set()

    pattern = r'\[Página\s+(\d+)\]'
    matches = re.finditer(pattern, response)

    for match in matches:
        page_num = int(match.group(1)) - 1
        if page_num in seen_pages:
            continue
        seen_pages.add(page_num)

        for result in context_chunks:
            if result.chunk.page_num == page_num:
                citations.append(Citation(
                    page_num=page_num,
                    text=result.chunk.text[:100],
                    chunk_id=result.chunk.chunk_id,
                ))
                break

    return citations


class ChatEngine:
    """Motor de chat con RAG para documentos PDF.

    Attributes:
        config: Configuración de IA.
        embedding_store: Almacén de embeddings.
        history: Historial de conversación.
    """

    def __init__(self, config: AIConfig):
        """Inicializa el motor de chat.

        Args:
            config: Configuración de IA.
        """
        self.config = config
        self.embedding_store = EmbeddingStore()
        self.history: List[ChatMessage] = []
        self._document_index: Optional[DocumentIndex] = None

    def index_document(self, doc_index: DocumentIndex) -> None:
        """Indexa un documento para búsqueda RAG.

        Args:
            doc_index: Índice del documento.
        """
        self._document_index = doc_index
        self.embedding_store.index_chunks(doc_index.chunks)
        self.history.clear()
        logger.info(
            f"Documento indexado para chat: {doc_index.total_pages} páginas"
        )

    def ask(self, question: str) -> ChatMessage:
        """Hace una pregunta sobre el documento.

        Args:
            question: Pregunta del usuario.

        Returns:
            ChatMessage con la respuesta y citas.

        Raises:
            RuntimeError: Si no hay documento indexado o LLM no configurado.
        """
        if not self.embedding_store.is_indexed:
            raise RuntimeError(
                "No hay documento indexado. Abra un PDF primero."
            )

        user_msg = ChatMessage(role=MessageRole.USER, content=question)
        self.history.append(user_msg)

        context = self.embedding_store.search(question, self.config.top_k)
        messages = build_rag_prompt(question, context)

        try:
            if self.config.llm_provider == LLMProvider.OPENAI:
                response_text = call_openai(messages, self.config)
            elif self.config.llm_provider == LLMProvider.OLLAMA:
                response_text = call_ollama(messages, self.config)
            else:
                response_text = self._format_context_only(context)
        except Exception as e:
            logger.error(f"Error al consultar LLM: {e}")
            response_text = f"Error al consultar el modelo de IA: {e}"

        citations = extract_citations(response_text, context)

        assistant_msg = ChatMessage(
            role=MessageRole.ASSISTANT,
            content=response_text,
            citations=citations,
        )
        self.history.append(assistant_msg)

        return assistant_msg

    def _format_context_only(self, context: List[SearchResult]) -> str:
        """Formatea contexto cuando no hay LLM disponible.

        Args:
            context: Resultados de búsqueda.

        Returns:
            Texto con los fragmentos relevantes.
        """
        if not context:
            return "No se encontraron fragmentos relevantes en el documento."

        parts = ["Fragmentos relevantes encontrados:\n"]
        for i, result in enumerate(context, 1):
            chunk = result.chunk
            parts.append(
                f"{i}. [Página {chunk.page_num + 1}] "
                f"(relevancia: {result.score:.0%})\n{chunk.text}\n"
            )

        parts.append(
            "\n(Configure un proveedor de IA en Ajustes para "
            "obtener respuestas generadas con IA)"
        )
        return "\n".join(parts)

    def clear_history(self) -> None:
        """Limpia el historial de conversación."""
        self.history.clear()

    @property
    def has_document(self) -> bool:
        """Indica si hay un documento indexado."""
        return self.embedding_store.is_indexed

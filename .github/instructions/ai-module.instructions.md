---
description: "Use when working on the AI module: RAG indexing, LLM chat with PDF, translation, embedding store, or AI UI components."
applyTo: "core/ai/**/*.py"
---
# AI Module Guidelines

## Architecture
```
core/ai/
├── __init__.py
├── document_indexer.py    # Extract and chunk text by page with metadata
├── embedding_store.py     # Vectorize chunks with embeddings (local or cloud)
├── chat_engine.py         # RAG pipeline: query → retrieve → prompt → LLM → cited answer
└── translator.py          # LLM-based translation preserving layout
```

## RAG Pipeline
1. **Index**: Extract text per page → split into chunks with metadata `(page_num, position, text)`
2. **Embed**: Vectorize chunks using sentence-transformers (local) or OpenAI embeddings (cloud)
3. **Store**: Save in ChromaDB (local vector store)
4. **Query**: Semantic search → top-k relevant chunks
5. **Generate**: Build prompt with context + user question → send to LLM
6. **Cite**: Map each response fragment to source `(page_num, original_text)`

## Multi-Provider Support
```python
class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"        # Local, no cloud dependency

class ChatEngine:
    def __init__(self, provider: LLMProvider, api_key: Optional[str] = None):
        """Inicializa el motor de chat con el proveedor elegido."""
```

## Key Rules
- **Privacy first**: Documents are indexed LOCALLY by default. Cloud APIs only when user opts in
- **Citations required**: Every AI response MUST include `(page_num, source_text)` for each claim
- **API keys**: Never hardcode. Store in QSettings or environment variables
- **Graceful degradation**: If no API key configured, show clear message — don't crash
- **Token limits**: Chunk text to fit context window (4K tokens per chunk max)

## Dependencies
```python
# Required
from openai import OpenAI           # openai package
import chromadb                      # chromadb for local vector store

# Optional local
from sentence_transformers import SentenceTransformer  # For local embeddings
```

from __future__ import annotations

from openai import OpenAI

from ..config import EMBEDDING_MODEL, NEBIUS_API_KEY, NEBIUS_BASE_URL

_client = OpenAI(api_key=NEBIUS_API_KEY, base_url=NEBIUS_BASE_URL, timeout=30.0)

MAX_EMBEDDING_INPUT_CHARS = 8000


def embed_text(text: str) -> list[float]:
    """Calls Nebius Token Factory's embedding endpoint (Qwen3-Embedding-8B, 4096 dims).

    Raises on failure — callers decide whether to degrade gracefully. Evidence writes and
    the investigation endpoint both treat a failed embedding as "store/search without
    semantic search this time" rather than failing the whole request.
    """
    response = _client.embeddings.create(model=EMBEDDING_MODEL, input=text[:MAX_EMBEDDING_INPUT_CHARS])
    return response.data[0].embedding

"""
Embedding service using OpenRouter's text-embedding-3-small model.

OpenRouter implements the OpenAI API spec — uses the openai Python client
pointed at the OpenRouter base URL.

Embedding dimension: 1536 (text-embedding-3-small). LOCKED.
"""
import logging

from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client = AsyncOpenAI(
    api_key=settings.openrouter_api_key,
    base_url="https://openrouter.ai/api/v1",
)

_BATCH_SIZE = 100


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate 1536-dim embeddings for a list of text strings.

    Raises:
        ValueError: If any text is empty or returned dimension != 1536.
        openai.APIError: On API failure (propagated — caller handles retry).
    """
    if not texts:
        return []

    for i, t in enumerate(texts):
        if not t.strip():
            raise ValueError(f"Empty text at index {i} — cannot embed empty string")

    all_embeddings: list[list[float]] = []

    for batch_start in range(0, len(texts), _BATCH_SIZE):
        batch = texts[batch_start : batch_start + _BATCH_SIZE]
        logger.info(
            "Requesting embeddings for batch %d-%d of %d texts",
            batch_start,
            batch_start + len(batch),
            len(texts),
        )
        response = await _client.embeddings.create(
            model=settings.embedding_model,
            input=batch,
        )
        for item in response.data:
            embedding = item.embedding
            if len(embedding) != settings.embedding_dimension:
                raise ValueError(
                    f"API returned {len(embedding)}-dim embedding; "
                    f"expected {settings.embedding_dimension}. "
                    "Check EMBEDDING_MODEL matches text-embedding-3-small."
                )
            all_embeddings.append(embedding)

    return all_embeddings

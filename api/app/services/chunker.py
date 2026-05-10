"""
Token-aware text chunking for RAG ingestion.

Strategy (per 01-CONTEXT.md decisions — locked):
  - Chunk size:   512 tokens
  - Overlap:      50 tokens (~10%)
  - Min filter:   drop chunks with < 50 tokens
  - Structured:   preserve markdown tables/lists as whole unit if ≤ 512 tokens
"""
import logging
import re

import tiktoken

logger = logging.getLogger(__name__)

_ENCODING = tiktoken.get_encoding("cl100k_base")
_CHUNK_SIZE = 512
_OVERLAP = 50
_MIN_TOKENS = 50


def _count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


def _is_structured_block(text: str) -> bool:
    stripped = text.strip()
    if re.search(r"^\|.+\|", stripped, re.MULTILINE):
        return True
    if re.search(r"^[-*]\s+\S", stripped, re.MULTILINE):
        return True
    if re.search(r"^\d+\.\s+\S", stripped, re.MULTILINE):
        return True
    return False


def _split_paragraphs(text: str) -> list[str]:
    raw_blocks = re.split(r"\n\n+", text)
    return [b.strip() for b in raw_blocks if b.strip()]


def chunk_text(text: str) -> list[tuple[str, int]]:
    """
    Split text into overlapping chunks of 512 tokens with 50-token overlap.
    Drops chunks with < 50 tokens.

    Returns:
        List of (chunk_text, token_count) tuples.
    """
    paragraphs = _split_paragraphs(text)
    chunks: list[tuple[str, int]] = []

    current_tokens: list[int] = []
    current_text_parts: list[str] = []

    def flush_chunk() -> None:
        if not current_tokens:
            return
        chunk_str = " ".join(current_text_parts).strip()
        token_count = len(current_tokens)
        if token_count < _MIN_TOKENS:
            logger.debug("Dropping chunk with %d tokens (below %d min)", token_count, _MIN_TOKENS)
            return
        chunks.append((chunk_str, token_count))

    for para in paragraphs:
        para_tokens = _ENCODING.encode(para)
        para_count = len(para_tokens)

        if _is_structured_block(para) and para_count <= _CHUNK_SIZE:
            if current_tokens:
                flush_chunk()
                current_tokens = []
                current_text_parts = []
            chunks.append((para, para_count))
            continue

        if len(current_tokens) + para_count > _CHUNK_SIZE:
            flush_chunk()
            if len(current_tokens) > _OVERLAP:
                overlap_tokens = current_tokens[-_OVERLAP:]
                current_tokens = overlap_tokens
                current_text_parts = [_ENCODING.decode(overlap_tokens)]
            else:
                current_tokens = []
                current_text_parts = []

        current_tokens.extend(para_tokens)
        current_text_parts.append(para)

    flush_chunk()
    return chunks

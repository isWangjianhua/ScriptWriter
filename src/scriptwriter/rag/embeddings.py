from __future__ import annotations

import hashlib
import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

_FALLBACK_DIM = 1536


@lru_cache(maxsize=1)
def _build_openai_embedder():
    provider = os.getenv("SCRIPTWRITER_EMBEDDING_PROVIDER", "auto").strip().lower()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if provider not in {"auto", "openai"}:
        return None
    if not api_key:
        return None

    try:
        from langchain_openai import OpenAIEmbeddings

        model = os.getenv("SCRIPTWRITER_EMBEDDING_MODEL", "text-embedding-3-small").strip()
        return OpenAIEmbeddings(model=model)
    except Exception as exc:  # pragma: no cover - environment-dependent
        logger.warning("OpenAI embeddings unavailable, fallback to hash embeddings: %s", exc)
        return None


def _hash_embedding(text: str, dim: int = _FALLBACK_DIM) -> list[float]:
    if dim <= 0:
        raise ValueError("dim must be > 0")

    out: list[float] = []
    counter = 0
    while len(out) < dim:
        digest = hashlib.sha256(f"{counter}:{text}".encode()).digest()
        for idx in range(0, len(digest), 4):
            if len(out) >= dim:
                break
            chunk = digest[idx : idx + 4]
            value = int.from_bytes(chunk, byteorder="big", signed=False)
            # Map to [-1, 1]
            out.append((value / 0xFFFFFFFF) * 2.0 - 1.0)
        counter += 1

    return out


def get_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    embedder = _build_openai_embedder()
    if embedder is not None:
        try:
            vectors = embedder.embed_documents(texts)
            if vectors and all(isinstance(v, list) for v in vectors):
                return [[float(x) for x in vector] for vector in vectors]
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            logger.warning("OpenAI embed_documents failed, fallback to hash embeddings: %s", exc)

    return [_hash_embedding(text) for text in texts]


def get_query_embedding(text: str) -> list[float]:
    query = text.strip()
    if not query:
        return _hash_embedding("")

    embedder = _build_openai_embedder()
    if embedder is not None:
        try:
            vector = embedder.embed_query(query)
            if isinstance(vector, list):
                return [float(x) for x in vector]
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            logger.warning("OpenAI embed_query failed, fallback to hash embeddings: %s", exc)

    return _hash_embedding(query)


def get_mock_embedding(text: str) -> list[float]:
    """Backwards-compatible alias for old call sites."""
    return get_query_embedding(text)

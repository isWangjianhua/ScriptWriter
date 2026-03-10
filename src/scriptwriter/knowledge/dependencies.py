from __future__ import annotations

import os

import httpx
from sqlalchemy import create_engine, text

from scriptwriter.knowledge.milvus_store import _get_milvus_client


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _check_postgres() -> None:
    dsn = _require_env("SCRIPTWRITER_KNOWLEDGE_PG_DSN")
    normalized = dsn
    if normalized.startswith("postgresql+asyncpg://"):
        normalized = normalized.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    elif normalized.startswith("postgres://"):
        normalized = normalized.replace("postgres://", "postgresql+psycopg://", 1)
    elif normalized.startswith("postgresql://"):
        normalized = normalized.replace("postgresql://", "postgresql+psycopg://", 1)

    engine = create_engine(normalized, future=True, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    finally:
        engine.dispose()


def _check_opensearch() -> None:
    url = _require_env("SCRIPTWRITER_OPENSEARCH_URL").rstrip("/")
    with httpx.Client(timeout=5.0) as client:
        response = client.get(f"{url}/_cluster/health")
        response.raise_for_status()


def _check_milvus() -> None:
    client = _get_milvus_client()
    if client is None:
        raise RuntimeError("Milvus is unavailable")


def _check_llm_env() -> None:
    _require_env("OPENAI_API_KEY")


def check_knowledge_dependencies() -> None:
    if os.getenv("SCRIPTWRITER_SKIP_DEPENDENCY_CHECK", "").strip() == "1":
        return
    _check_postgres()
    _check_opensearch()
    _check_milvus()
    _check_llm_env()

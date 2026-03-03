from __future__ import annotations

import logging
import os

from scriptwriter.state_store.base import StateStore
from scriptwriter.state_store.in_memory import InMemoryStateStore

logger = logging.getLogger(__name__)

_store_singleton: StateStore | None = None


def get_state_store() -> StateStore:
    global _store_singleton
    if _store_singleton is not None:
        return _store_singleton

    dsn = os.getenv("SCRIPTWRITER_DATABASE_URL", "").strip()
    if dsn:
        try:
            from scriptwriter.state_store.postgres import PostgresStateStore

            _store_singleton = PostgresStateStore(dsn)
            logger.info("Using PostgreSQL state store")
            return _store_singleton
        except Exception as exc:
            logger.exception("Failed to initialize PostgreSQL state store, fallback to in-memory: %s", exc)

    _store_singleton = InMemoryStateStore()
    logger.info("Using in-memory state store")
    return _store_singleton


def reset_state_store_for_tests() -> None:
    global _store_singleton
    _store_singleton = None

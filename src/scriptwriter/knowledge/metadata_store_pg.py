from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    and_,
    bindparam,
    create_engine,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine

from scriptwriter.knowledge.metadata_repository import CandidateDocument, ChunkHit, KnowledgeMetadataRepository, StoredDocument

_TOKEN_RE = re.compile(r"[\w\-]+")

_METADATA = MetaData()

_DOCUMENTS = Table(
    "knowledge_documents",
    _METADATA,
    Column("doc_id", String, primary_key=True),
    Column("user_id", String, nullable=False),
    Column("project_id", String, nullable=False),
    Column("doc_type", String, nullable=False),
    Column("title", String, nullable=False, default=""),
    Column("path_l1", String, nullable=False, default=""),
    Column("path_l2", String, nullable=False, default=""),
    Column("source_path", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

Index("idx_kd_user_project", _DOCUMENTS.c.user_id, _DOCUMENTS.c.project_id)
Index("idx_kd_path", _DOCUMENTS.c.path_l1, _DOCUMENTS.c.path_l2)

_CHUNKS = Table(
    "knowledge_chunks",
    _METADATA,
    Column("chunk_id", String, primary_key=True),
    Column("doc_id", String, ForeignKey("knowledge_documents.doc_id", ondelete="CASCADE"), nullable=False),
    Column("user_id", String, nullable=False),
    Column("project_id", String, nullable=False),
    Column("chunk_order", Integer, nullable=False),
    Column("segment_type", String, nullable=False),
    Column("text", Text, nullable=False),
    Column("source_type", String),
    Column("version_id", String),
    Column("episode_id", String),
    Column("scene_id", String),
    Column("is_active", Boolean, nullable=False, default=True),
    Column("title", String, nullable=False, default=""),
    Column("doc_type", String, nullable=False, default=""),
    Column("path_l1", String, nullable=False, default=""),
    Column("path_l2", String, nullable=False, default=""),
)

Index("idx_kc_doc_order", _CHUNKS.c.doc_id, _CHUNKS.c.chunk_order)
Index("idx_kc_user_project", _CHUNKS.c.user_id, _CHUNKS.c.project_id)


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]


def _normalize_sqlalchemy_dsn(dsn: str) -> str:
    normalized = dsn.strip()
    if normalized.startswith("postgresql+asyncpg://"):
        return normalized.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if normalized.startswith("postgres://"):
        return normalized.replace("postgres://", "postgresql+psycopg://", 1)
    if normalized.startswith("postgresql://"):
        return normalized.replace("postgresql://", "postgresql+psycopg://", 1)
    return normalized


class PostgresKnowledgeMetadataStore(KnowledgeMetadataRepository):
    def __init__(self, *, dsn: str, source_root: Path) -> None:
        self._source_root = source_root
        self._source_root.mkdir(parents=True, exist_ok=True)
        self._engine: Engine = create_engine(_normalize_sqlalchemy_dsn(dsn), future=True, pool_pre_ping=True)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        _METADATA.create_all(self._engine, checkfirst=True)

    def persist_source(self, doc_id: str, content: str) -> str:
        safe_doc_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", doc_id)
        path = self._source_root / f"{safe_doc_id}.txt"
        path.write_text(content, encoding="utf-8")
        return str(path)

    def upsert_document(
        self,
        *,
        doc_id: str,
        user_id: str,
        project_id: str,
        doc_type: str,
        title: str,
        path_l1: str,
        path_l2: str,
        source_path: str,
    ) -> None:
        now = datetime.now(UTC)
        values = {
            "user_id": user_id,
            "project_id": project_id,
            "doc_type": doc_type,
            "title": title,
            "path_l1": path_l1,
            "path_l2": path_l2,
            "source_path": source_path,
            "updated_at": now,
        }
        with self._engine.begin() as conn:
            result = conn.execute(update(_DOCUMENTS).where(_DOCUMENTS.c.doc_id == doc_id).values(**values))
            if not result.rowcount:
                conn.execute(
                    insert(_DOCUMENTS).values(
                        doc_id=doc_id,
                        created_at=now,
                        **values,
                    )
                )

    def replace_chunks(
        self,
        *,
        doc_id: str,
        user_id: str,
        project_id: str,
        chunks: list[dict[str, object]],
    ) -> None:
        rows: list[dict[str, object]] = []
        for idx, chunk in enumerate(chunks):
            rows.append(
                {
                    "chunk_id": str(chunk.get("chunk_id") or f"{doc_id}:{idx}"),
                    "doc_id": doc_id,
                    "user_id": user_id,
                    "project_id": project_id,
                    "chunk_order": int(chunk.get("chunk_order", idx)),
                    "segment_type": str(chunk.get("segment_type", "paragraph")),
                    "text": str(chunk.get("text", "")),
                    "source_type": _pick_str(chunk.get("source_type")),
                    "version_id": _pick_str(chunk.get("version_id")),
                    "episode_id": _pick_str(chunk.get("episode_id")),
                    "scene_id": _pick_str(chunk.get("scene_id")),
                    "is_active": bool(chunk.get("is_active", True)),
                    "title": str(chunk.get("title", "")),
                    "doc_type": str(chunk.get("doc_type", "")),
                    "path_l1": str(chunk.get("path_l1", "")),
                    "path_l2": str(chunk.get("path_l2", "")),
                }
            )

        with self._engine.begin() as conn:
            conn.execute(delete(_CHUNKS).where(_CHUNKS.c.doc_id == doc_id))
            if rows:
                conn.execute(insert(_CHUNKS), rows)

    def list_candidate_docs(
        self,
        *,
        user_id: str,
        project_id: str,
        query: str,
        doc_type: str | None = None,
        path_l1: str | None = None,
        path_l2: str | None = None,
        limit: int = 20,
    ) -> list[CandidateDocument]:
        conditions = [_DOCUMENTS.c.user_id == user_id, _DOCUMENTS.c.project_id == project_id]
        if doc_type:
            conditions.append(_DOCUMENTS.c.doc_type == doc_type)
        if path_l1:
            conditions.append(_DOCUMENTS.c.path_l1 == path_l1)
        if path_l2:
            conditions.append(_DOCUMENTS.c.path_l2 == path_l2)

        stmt = (
            select(
                _DOCUMENTS.c.doc_id,
                _DOCUMENTS.c.doc_type,
                _DOCUMENTS.c.title,
                _DOCUMENTS.c.path_l1,
                _DOCUMENTS.c.path_l2,
                _DOCUMENTS.c.source_path,
            )
            .where(and_(*conditions))
        )
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()

        tokens = _tokenize(query)
        candidates: list[CandidateDocument] = []
        for row in rows:
            data = row._mapping
            doc_type_v = str(data["doc_type"] or "")
            title_v = str(data["title"] or "")
            path_l1_v = str(data["path_l1"] or "")
            path_l2_v = str(data["path_l2"] or "")
            score = self._score(tokens, title_v, path_l1_v, path_l2_v, doc_type_v)
            candidates.append(
                CandidateDocument(
                    doc_id=str(data["doc_id"]),
                    doc_type=doc_type_v,
                    title=title_v,
                    path_l1=path_l1_v,
                    path_l2=path_l2_v,
                    source_path=str(data["source_path"] or ""),
                    score=score,
                )
            )
        candidates.sort(key=lambda item: item.score, reverse=True)
        return candidates[: max(limit, 0)]

    def list_documents(
        self,
        *,
        user_id: str,
        project_id: str,
        doc_id: str | None = None,
        doc_type: str | None = None,
        path_l1: str | None = None,
        path_l2: str | None = None,
        limit: int = 1000,
    ) -> list[StoredDocument]:
        conditions = [_DOCUMENTS.c.user_id == user_id, _DOCUMENTS.c.project_id == project_id]
        if doc_id:
            conditions.append(_DOCUMENTS.c.doc_id == doc_id)
        if doc_type:
            conditions.append(_DOCUMENTS.c.doc_type == doc_type)
        if path_l1:
            conditions.append(_DOCUMENTS.c.path_l1 == path_l1)
        if path_l2:
            conditions.append(_DOCUMENTS.c.path_l2 == path_l2)

        stmt = (
            select(
                _DOCUMENTS.c.doc_id,
                _DOCUMENTS.c.user_id,
                _DOCUMENTS.c.project_id,
                _DOCUMENTS.c.doc_type,
                _DOCUMENTS.c.title,
                _DOCUMENTS.c.path_l1,
                _DOCUMENTS.c.path_l2,
                _DOCUMENTS.c.source_path,
            )
            .where(and_(*conditions))
            .order_by(_DOCUMENTS.c.created_at.asc())
            .limit(max(limit, 0))
        )
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [
            StoredDocument(
                doc_id=str(row._mapping["doc_id"]),
                user_id=str(row._mapping["user_id"]),
                project_id=str(row._mapping["project_id"]),
                doc_type=str(row._mapping["doc_type"]),
                title=str(row._mapping["title"] or ""),
                path_l1=str(row._mapping["path_l1"] or ""),
                path_l2=str(row._mapping["path_l2"] or ""),
                source_path=str(row._mapping["source_path"] or ""),
            )
            for row in rows
        ]

    def search_chunk_rows(
        self,
        *,
        doc_ids: list[str],
        query: str,
        limit: int = 5,
    ) -> list[ChunkHit]:
        if not doc_ids:
            return []

        stmt = (
            select(
                _CHUNKS.c.chunk_id,
                _CHUNKS.c.doc_id,
                _CHUNKS.c.segment_type,
                _CHUNKS.c.text,
                _CHUNKS.c.chunk_order,
            )
            .where(_CHUNKS.c.doc_id.in_(bindparam("doc_ids", expanding=True)))
            .order_by(_CHUNKS.c.chunk_order.asc())
        )
        with self._engine.connect() as conn:
            rows = conn.execute(stmt, {"doc_ids": doc_ids}).all()

        tokens = _tokenize(query)
        ranked: list[ChunkHit] = []
        for row in rows:
            data = row._mapping
            text = str(data["text"] or "")
            lowered = text.lower()
            score = sum(1 for token in tokens if token in lowered)
            if not tokens:
                score = 1
            if score > 0:
                ranked.append(
                    ChunkHit(
                        chunk_id=str(data["chunk_id"]),
                        doc_id=str(data["doc_id"]),
                        chunk_order=int(data["chunk_order"]),
                        segment_type=str(data["segment_type"] or ""),
                        text=text,
                        score=score,
                    )
                )
        ranked.sort(key=lambda item: (-item.score, item.chunk_order))
        return ranked[: max(limit, 0)]

    def load_source_text(self, doc_id: str) -> str | None:
        stmt = select(_DOCUMENTS.c.source_path).where(_DOCUMENTS.c.doc_id == doc_id)
        with self._engine.connect() as conn:
            row = conn.execute(stmt).first()
        if row is None:
            return None
        path = Path(str(row._mapping["source_path"]))
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def delete_chunks_by_doc(self, doc_id: str) -> int:
        with self._engine.begin() as conn:
            result = conn.execute(delete(_CHUNKS).where(_CHUNKS.c.doc_id == doc_id))
            return int(result.rowcount or 0)

    @staticmethod
    def _score(tokens: list[str], title: str, path_l1: str, path_l2: str, doc_type: str) -> int:
        if not tokens:
            return 1
        haystack = " ".join([title.lower(), path_l1.lower(), path_l2.lower(), doc_type.lower()])
        return sum(1 for token in tokens if token in haystack)


def _pick_str(value: object) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        if text:
            return text
    return None

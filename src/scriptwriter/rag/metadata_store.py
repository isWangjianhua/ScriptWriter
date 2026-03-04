from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CandidateDocument:
    doc_id: str
    doc_type: str
    title: str
    path_l1: str
    path_l2: str
    source_path: str
    score: int


_TOKEN_RE = re.compile(r"[\w\-]+")


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]


class KnowledgeMetadataStore:
    def __init__(self, *, db_path: Path, source_root: Path) -> None:
        self._db_path = db_path
        self._source_root = source_root
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._source_root.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        ddl = """
        CREATE TABLE IF NOT EXISTS rag_documents (
            doc_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            path_l1 TEXT NOT NULL DEFAULT '',
            path_l2 TEXT NOT NULL DEFAULT '',
            source_path TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_rag_documents_user_project
            ON rag_documents(user_id, project_id);

        CREATE INDEX IF NOT EXISTS idx_rag_documents_path
            ON rag_documents(path_l1, path_l2);

        CREATE TABLE IF NOT EXISTS rag_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT NOT NULL,
            chunk_order INTEGER NOT NULL,
            segment_type TEXT NOT NULL,
            text TEXT NOT NULL,
            FOREIGN KEY(doc_id) REFERENCES rag_documents(doc_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_rag_chunks_doc
            ON rag_chunks(doc_id, chunk_order);
        """

        with self._connect() as conn:
            conn.executescript(ddl)

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
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO rag_documents(
                    doc_id, user_id, project_id, doc_type, title, path_l1, path_l2, source_path
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    user_id=excluded.user_id,
                    project_id=excluded.project_id,
                    doc_type=excluded.doc_type,
                    title=excluded.title,
                    path_l1=excluded.path_l1,
                    path_l2=excluded.path_l2,
                    source_path=excluded.source_path
                """,
                (doc_id, user_id, project_id, doc_type, title, path_l1, path_l2, source_path),
            )

    def replace_chunks(self, doc_id: str, chunks: list[dict[str, object]]) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM rag_chunks WHERE doc_id = ?", (doc_id,))
            conn.executemany(
                """
                INSERT INTO rag_chunks(doc_id, chunk_order, segment_type, text)
                VALUES(?, ?, ?, ?)
                """,
                [
                    (
                        doc_id,
                        int(chunk.get("chunk_order", idx)),
                        str(chunk.get("segment_type", "paragraph")),
                        str(chunk.get("text", "")),
                    )
                    for idx, chunk in enumerate(chunks)
                ],
            )

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
        conditions = ["user_id = ?", "project_id = ?"]
        params: list[object] = [user_id, project_id]

        if doc_type:
            conditions.append("doc_type = ?")
            params.append(doc_type)
        if path_l1:
            conditions.append("path_l1 = ?")
            params.append(path_l1)
        if path_l2:
            conditions.append("path_l2 = ?")
            params.append(path_l2)

        sql = (
            "SELECT doc_id, doc_type, title, path_l1, path_l2, source_path "
            "FROM rag_documents WHERE " + " AND ".join(conditions)
        )

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        tokens = _tokenize(query)
        candidates: list[CandidateDocument] = []
        for row in rows:
            title_v = str(row["title"] or "")
            path_l1_v = str(row["path_l1"] or "")
            path_l2_v = str(row["path_l2"] or "")
            doc_type_v = str(row["doc_type"] or "")
            score = self._score(tokens, title_v, path_l1_v, path_l2_v, doc_type_v)
            candidates.append(
                CandidateDocument(
                    doc_id=str(row["doc_id"]),
                    doc_type=doc_type_v,
                    title=title_v,
                    path_l1=path_l1_v,
                    path_l2=path_l2_v,
                    source_path=str(row["source_path"]),
                    score=score,
                )
            )

        candidates.sort(key=lambda item: item.score, reverse=True)
        return candidates[: max(limit, 0)]

    def search_chunks(self, *, doc_ids: list[str], query: str, limit: int = 5) -> list[str]:
        if not doc_ids:
            return []

        placeholders = ",".join(["?"] * len(doc_ids))
        sql = (
            "SELECT doc_id, text, chunk_order FROM rag_chunks "
            f"WHERE doc_id IN ({placeholders}) ORDER BY chunk_order ASC"
        )

        with self._connect() as conn:
            rows = conn.execute(sql, doc_ids).fetchall()

        tokens = _tokenize(query)
        ranked: list[tuple[int, int, str]] = []
        for row in rows:
            text = str(row["text"])
            lowered = text.lower()
            score = sum(1 for token in tokens if token in lowered)
            if not tokens:
                score = 1
            if score > 0:
                ranked.append((score, int(row["chunk_order"]), text))

        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in ranked[: max(limit, 0)]]

    def load_source_text(self, doc_id: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT source_path FROM rag_documents WHERE doc_id = ?",
                (doc_id,),
            ).fetchone()

        if row is None:
            return None

        source_path = Path(str(row["source_path"]))
        if not source_path.exists():
            return None

        return source_path.read_text(encoding="utf-8")

    @staticmethod
    def _score(tokens: list[str], title: str, path_l1: str, path_l2: str, doc_type: str) -> int:
        if not tokens:
            return 0

        title_l = title.lower()
        path_l1_l = path_l1.lower()
        path_l2_l = path_l2.lower()
        doc_type_l = doc_type.lower()

        score = 0
        for token in tokens:
            if token in path_l1_l:
                score += 3
            if token in path_l2_l:
                score += 2
            if token in title_l:
                score += 2
            if token in doc_type_l:
                score += 1
        return score

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class CandidateDocument:
    doc_id: str
    doc_type: str
    title: str
    path_l1: str
    path_l2: str
    source_path: str
    score: int


@dataclass(frozen=True)
class StoredDocument:
    doc_id: str
    user_id: str
    project_id: str
    doc_type: str
    title: str
    path_l1: str
    path_l2: str
    source_path: str


@dataclass(frozen=True)
class ChunkHit:
    chunk_id: str
    doc_id: str
    chunk_order: int
    segment_type: str
    text: str
    score: int


@runtime_checkable
class KnowledgeMetadataRepository(Protocol):
    def persist_source(self, doc_id: str, content: str) -> str:
        ...

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
        ...

    def replace_chunks(
        self,
        *,
        doc_id: str,
        user_id: str,
        project_id: str,
        chunks: list[dict[str, object]],
    ) -> None:
        ...

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
        ...

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
        ...

    def search_chunk_rows(
        self,
        *,
        doc_ids: list[str],
        query: str,
        limit: int = 5,
    ) -> list[ChunkHit]:
        ...

    def load_source_text(self, doc_id: str) -> str | None:
        ...

    def delete_chunks_by_doc(self, doc_id: str) -> int:
        ...


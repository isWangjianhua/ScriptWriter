from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from scriptwriter.agents.memory.milvus_store import add_texts_to_milvus, search_milvus_bible
from scriptwriter.rag.embeddings import get_mock_embedding
from scriptwriter.rag.metadata_store import KnowledgeMetadataStore
from scriptwriter.rag.segmenter import chunk_segments, segment_content


@dataclass(frozen=True)
class IngestResult:
    doc_id: str
    chunk_count: int
    source_path: str


_METADATA_STORE: KnowledgeMetadataStore | None = None


def _resolve_data_dir(data_dir: str | Path | None = None) -> Path:
    if data_dir is None:
        env_dir = os.getenv("SCRIPTWRITER_RAG_DATA_DIR", "").strip()
        if env_dir:
            return Path(env_dir)
        return Path("data") / "rag"
    return Path(data_dir)


def _get_metadata_store() -> KnowledgeMetadataStore:
    global _METADATA_STORE
    if _METADATA_STORE is None:
        base_dir = _resolve_data_dir()
        _METADATA_STORE = KnowledgeMetadataStore(
            db_path=base_dir / "metadata.db",
            source_root=base_dir / "sources",
        )
    return _METADATA_STORE


def reset_knowledge_services_for_tests(data_dir: str | Path | None = None) -> None:
    global _METADATA_STORE
    if data_dir is None:
        _METADATA_STORE = None
        return

    base_dir = _resolve_data_dir(data_dir)
    _METADATA_STORE = KnowledgeMetadataStore(
        db_path=base_dir / "metadata.db",
        source_root=base_dir / "sources",
    )


def ingest_knowledge_document(
    *,
    user_id: str,
    project_id: str,
    content: str,
    doc_type: str,
    title: str | None = None,
    path_l1: str | None = None,
    path_l2: str | None = None,
    doc_id: str | None = None,
    chunk_max_chars: int = 800,
    chunk_overlap: int = 120,
) -> IngestResult:
    body = content.strip()
    if not body:
        raise ValueError("content must not be empty")

    normalized_doc_type = doc_type.strip().lower()
    if normalized_doc_type not in {"script", "novel", "text"}:
        raise ValueError("doc_type must be one of: script, novel, text")

    resolved_doc_id = doc_id or uuid4().hex
    resolved_title = (title or resolved_doc_id).strip()
    resolved_path_l1 = (path_l1 or "").strip()
    resolved_path_l2 = (path_l2 or "").strip()

    segments = segment_content(body, normalized_doc_type)
    chunks = chunk_segments(segments, max_chars=chunk_max_chars, overlap=chunk_overlap)
    if not chunks:
        raise ValueError("failed to create chunks from content")

    store = _get_metadata_store()
    source_path = store.persist_source(resolved_doc_id, body)
    store.upsert_document(
        doc_id=resolved_doc_id,
        user_id=user_id,
        project_id=project_id,
        doc_type=normalized_doc_type,
        title=resolved_title,
        path_l1=resolved_path_l1,
        path_l2=resolved_path_l2,
        source_path=source_path,
    )

    chunk_rows: list[dict[str, object]] = []
    texts: list[str] = []
    vectors: list[list[float]] = []
    metadatas: list[dict[str, object]] = []

    for idx, chunk in enumerate(chunks):
        chunk_rows.append(
            {
                "chunk_order": idx,
                "segment_type": chunk.segment_type,
                "text": chunk.text,
            }
        )
        texts.append(chunk.text)
        vectors.append(get_mock_embedding(chunk.text))
        metadatas.append(
            {
                "doc_id": resolved_doc_id,
                "doc_type": normalized_doc_type,
                "path_l1": resolved_path_l1,
                "path_l2": resolved_path_l2,
                "segment_type": chunk.segment_type,
                "segment_index": chunk.segment_index,
                "chunk_index": chunk.chunk_index,
                "chunk_order": idx,
                "title": resolved_title,
            }
        )

    store.replace_chunks(resolved_doc_id, chunk_rows)
    add_texts_to_milvus(
        user_id=user_id,
        project_id=project_id,
        texts=texts,
        vectors=vectors,
        metadatas=metadatas,
    )

    return IngestResult(doc_id=resolved_doc_id, chunk_count=len(chunks), source_path=source_path)


def search_knowledge(
    *,
    user_id: str,
    project_id: str,
    query: str,
    limit: int = 3,
    doc_type: str | None = None,
    path_l1: str | None = None,
    path_l2: str | None = None,
) -> list[str]:
    query_text = query.strip()
    if not query_text:
        return []

    top_k = max(limit, 1)
    store = _get_metadata_store()
    candidates = store.list_candidate_docs(
        user_id=user_id,
        project_id=project_id,
        query=query_text,
        doc_type=doc_type,
        path_l1=path_l1,
        path_l2=path_l2,
        limit=top_k * 4,
    )
    candidate_doc_ids = [candidate.doc_id for candidate in candidates]

    query_vector = get_mock_embedding(query_text)
    filters: dict[str, object] = {}
    if doc_type:
        filters["doc_type"] = doc_type
    if path_l1:
        filters["path_l1"] = path_l1
    if path_l2:
        filters["path_l2"] = path_l2
    if candidate_doc_ids:
        filters["doc_ids"] = candidate_doc_ids

    vector_results = search_milvus_bible(
        user_id=user_id,
        project_id=project_id,
        query_vector=query_vector,
        limit=top_k,
        filters=filters,
    )
    if vector_results:
        return vector_results[:top_k]

    if not candidate_doc_ids:
        return []

    fallback_results = store.search_chunks(doc_ids=candidate_doc_ids, query=query_text, limit=top_k)
    return fallback_results[:top_k]

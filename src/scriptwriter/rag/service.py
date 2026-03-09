from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from scriptwriter.agents.memory.milvus_store import (
    add_texts_to_milvus,
    delete_milvus_documents,
    search_milvus_bible_records,
)
from scriptwriter.rag.embeddings import get_embeddings, get_query_embedding
from scriptwriter.rag.metadata_store import CandidateDocument, KnowledgeMetadataStore
from scriptwriter.rag.segmenter import chunk_segments, segment_content


@dataclass(frozen=True)
class IngestResult:
    doc_id: str
    chunk_count: int
    source_path: str


@dataclass(frozen=True)
class KnowledgeHit:
    text: str
    doc_id: str | None
    doc_type: str | None
    title: str | None
    path_l1: str | None
    path_l2: str | None
    segment_type: str | None
    chunk_order: int | None
    score: float | None
    source_backend: str
    source_type: str | None = None
    version_id: str | None = None
    episode_id: str | None = None
    scene_id: str | None = None
    is_active: bool | None = None


@dataclass(frozen=True)
class RebuildResult:
    docs_processed: int
    chunks_indexed: int
    deleted_vectors: int


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


def _build_chunk_payloads(
    *,
    doc_id: str,
    doc_type: str,
    title: str,
    path_l1: str,
    path_l2: str,
    chunks,
    source_type: str | None = None,
    version_id: str | None = None,
    episode_id: str | None = None,
    scene_id: str | None = None,
    is_active: bool = True,
) -> tuple[list[dict[str, object]], list[str], list[dict[str, object]]]:
    chunk_rows: list[dict[str, object]] = []
    texts: list[str] = []
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
        metadatas.append(
            {
                "doc_id": doc_id,
                "doc_type": doc_type,
                "path_l1": path_l1,
                "path_l2": path_l2,
                "segment_type": chunk.segment_type,
                "segment_index": chunk.segment_index,
                "chunk_index": chunk.chunk_index,
                "chunk_order": idx,
                "title": title,
                "source_type": source_type,
                "version_id": version_id,
                "episode_id": episode_id,
                "scene_id": scene_id,
                "is_active": is_active,
            }
        )

    return chunk_rows, texts, metadatas


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
    source_type: str | None = None,
    version_id: str | None = None,
    episode_id: str | None = None,
    scene_id: str | None = None,
    is_active: bool = True,
) -> IngestResult:
    body = content.strip()
    if not body:
        raise ValueError("content must not be empty")

    normalized_doc_type = doc_type.strip().lower()
    if normalized_doc_type not in {"script", "novel", "text", "markdown"}:
        raise ValueError("doc_type must be one of: script, novel, text, markdown")

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

    chunk_rows, texts, metadatas = _build_chunk_payloads(
        doc_id=resolved_doc_id,
        doc_type=normalized_doc_type,
        title=resolved_title,
        path_l1=resolved_path_l1,
        path_l2=resolved_path_l2,
        chunks=chunks,
        source_type=source_type,
        version_id=version_id,
        episode_id=episode_id,
        scene_id=scene_id,
        is_active=is_active,
    )

    vectors = get_embeddings(texts)
    store.replace_chunks(resolved_doc_id, chunk_rows)
    add_texts_to_milvus(
        user_id=user_id,
        project_id=project_id,
        texts=texts,
        vectors=vectors,
        metadatas=metadatas,
    )

    return IngestResult(doc_id=resolved_doc_id, chunk_count=len(chunks), source_path=source_path)


def _candidate_map(candidates: list[CandidateDocument]) -> dict[str, CandidateDocument]:
    return {candidate.doc_id: candidate for candidate in candidates}


def search_knowledge_hits(
    *,
    user_id: str,
    project_id: str,
    query: str,
    limit: int = 3,
    doc_type: str | None = None,
    path_l1: str | None = None,
    path_l2: str | None = None,
    source_type: str | None = None,
    version_id: str | None = None,
    episode_id: str | None = None,
    scene_id: str | None = None,
    is_active: bool | None = None,
) -> list[KnowledgeHit]:
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
    candidate_by_id = _candidate_map(candidates)

    query_vector = get_query_embedding(query_text)
    filters: dict[str, object] = {}
    if doc_type:
        filters["doc_type"] = doc_type
    if path_l1:
        filters["path_l1"] = path_l1
    if path_l2:
        filters["path_l2"] = path_l2
    if source_type:
        filters["source_type"] = source_type
    if version_id:
        filters["version_id"] = version_id
    if episode_id:
        filters["episode_id"] = episode_id
    if scene_id:
        filters["scene_id"] = scene_id
    if is_active is not None:
        filters["is_active"] = is_active
    if candidate_doc_ids:
        filters["doc_ids"] = candidate_doc_ids

    vector_results = search_milvus_bible_records(
        user_id=user_id,
        project_id=project_id,
        query_vector=query_vector,
        limit=top_k,
        filters=filters,
    )
    if vector_results:
        hits: list[KnowledgeHit] = []
        for row in vector_results:
            text = row.get("text")
            if not isinstance(text, str):
                continue
            row_doc_id = row.get("doc_id")
            doc_id_value = row_doc_id if isinstance(row_doc_id, str) and row_doc_id else None
            candidate = candidate_by_id.get(doc_id_value or "")

            raw_chunk_order = row.get("chunk_order")
            chunk_order_value = int(raw_chunk_order) if isinstance(raw_chunk_order, (int, float)) else None
            raw_score = row.get("score")
            score_value = float(raw_score) if isinstance(raw_score, (int, float)) else None
            raw_is_active = row.get("is_active")
            is_active_value = raw_is_active if isinstance(raw_is_active, bool) else None

            hits.append(
                KnowledgeHit(
                    text=text,
                    doc_id=doc_id_value,
                    doc_type=_pick_str(row.get("doc_type"), candidate.doc_type if candidate else None),
                    title=_pick_str(row.get("title"), candidate.title if candidate else None),
                    path_l1=_pick_str(row.get("path_l1"), candidate.path_l1 if candidate else None),
                    path_l2=_pick_str(row.get("path_l2"), candidate.path_l2 if candidate else None),
                    segment_type=_pick_str(row.get("segment_type"), None),
                    chunk_order=chunk_order_value,
                    score=score_value,
                    source_backend="milvus",
                    source_type=_pick_str(row.get("source_type"), source_type),
                    version_id=_pick_str(row.get("version_id"), version_id),
                    episode_id=_pick_str(row.get("episode_id"), episode_id),
                    scene_id=_pick_str(row.get("scene_id"), scene_id),
                    is_active=is_active_value if is_active_value is not None else is_active,
                )
            )
        return hits[:top_k]

    if not candidate_doc_ids:
        return []

    chunk_hits = store.search_chunk_rows(doc_ids=candidate_doc_ids, query=query_text, limit=top_k)
    fallback_hits: list[KnowledgeHit] = []
    for chunk_hit in chunk_hits:
        candidate = candidate_by_id.get(chunk_hit.doc_id)
        fallback_hits.append(
            KnowledgeHit(
                text=chunk_hit.text,
                doc_id=chunk_hit.doc_id,
                doc_type=candidate.doc_type if candidate else None,
                title=candidate.title if candidate else None,
                path_l1=candidate.path_l1 if candidate else None,
                path_l2=candidate.path_l2 if candidate else None,
                segment_type=chunk_hit.segment_type,
                chunk_order=chunk_hit.chunk_order,
                score=float(chunk_hit.score),
                source_backend="sqlite",
                source_type=source_type,
                version_id=version_id,
                episode_id=episode_id,
                scene_id=scene_id,
                is_active=is_active,
            )
        )
    return fallback_hits[:top_k]


def search_knowledge(
    *,
    user_id: str,
    project_id: str,
    query: str,
    limit: int = 3,
    doc_type: str | None = None,
    path_l1: str | None = None,
    path_l2: str | None = None,
    source_type: str | None = None,
    version_id: str | None = None,
    episode_id: str | None = None,
    scene_id: str | None = None,
    is_active: bool | None = None,
) -> list[str]:
    hits = search_knowledge_hits(
        user_id=user_id,
        project_id=project_id,
        query=query,
        limit=limit,
        doc_type=doc_type,
        path_l1=path_l1,
        path_l2=path_l2,
        source_type=source_type,
        version_id=version_id,
        episode_id=episode_id,
        scene_id=scene_id,
        is_active=is_active,
    )
    return [hit.text for hit in hits]


def rebuild_knowledge_index(
    *,
    user_id: str,
    project_id: str,
    doc_id: str | None = None,
    chunk_max_chars: int = 800,
    chunk_overlap: int = 120,
) -> RebuildResult:
    store = _get_metadata_store()
    docs = store.list_documents(user_id=user_id, project_id=project_id, doc_id=doc_id)
    if not docs:
        return RebuildResult(docs_processed=0, chunks_indexed=0, deleted_vectors=0)

    doc_ids = [doc.doc_id for doc in docs]
    deleted = delete_milvus_documents(user_id=user_id, project_id=project_id, doc_ids=doc_ids)

    chunks_indexed = 0
    for doc in docs:
        body = store.load_source_text(doc.doc_id)
        if not body:
            continue

        segments = segment_content(body, doc.doc_type)
        chunks = chunk_segments(segments, max_chars=chunk_max_chars, overlap=chunk_overlap)
        if not chunks:
            continue

        chunk_rows, texts, metadatas = _build_chunk_payloads(
            doc_id=doc.doc_id,
            doc_type=doc.doc_type,
            title=doc.title,
            path_l1=doc.path_l1,
            path_l2=doc.path_l2,
            chunks=chunks,
        )

        vectors = get_embeddings(texts)
        store.replace_chunks(doc.doc_id, chunk_rows)
        add_texts_to_milvus(
            user_id=user_id,
            project_id=project_id,
            texts=texts,
            vectors=vectors,
            metadatas=metadatas,
        )
        chunks_indexed += len(chunks)

    return RebuildResult(
        docs_processed=len(docs),
        chunks_indexed=chunks_indexed,
        deleted_vectors=deleted,
    )


def _pick_str(primary: object, fallback: str | None) -> str | None:
    if isinstance(primary, str) and primary:
        return primary
    return fallback

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from scriptwriter.knowledge.embeddings import get_embeddings
from scriptwriter.knowledge.keyword_store import OpenSearchKeywordStore
from scriptwriter.knowledge.metadata_repository import CandidateDocument
from scriptwriter.knowledge.metadata_store_pg import PostgresKnowledgeMetadataStore
from scriptwriter.knowledge.milvus_store import add_texts_to_milvus, delete_milvus_documents, search_milvus_bible_records
from scriptwriter.knowledge.models import ProjectKnowledgeHit
from scriptwriter.knowledge.retrieval_pipeline import KnowledgeRetrievalPipeline
from scriptwriter.knowledge.segmenter import chunk_segments, segment_content


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


_PG_STORE: PostgresKnowledgeMetadataStore | None = None
_KEYWORD_STORE: OpenSearchKeywordStore | None = None
_RETRIEVAL_PIPELINE: KnowledgeRetrievalPipeline | None = None


def _resolve_data_dir(data_dir: str | Path | None = None) -> Path:
    if data_dir is None:
        env_dir = os.getenv("SCRIPTWRITER_RAG_DATA_DIR", "").strip()
        if env_dir:
            return Path(env_dir)
        return Path("data") / "rag"
    return Path(data_dir)


def _get_pg_store() -> PostgresKnowledgeMetadataStore:
    global _PG_STORE
    if _PG_STORE is None:
        dsn = os.getenv("SCRIPTWRITER_KNOWLEDGE_PG_DSN", "").strip()
        if not dsn:
            raise RuntimeError("Missing required environment variable: SCRIPTWRITER_KNOWLEDGE_PG_DSN")
        base_dir = _resolve_data_dir()
        _PG_STORE = PostgresKnowledgeMetadataStore(dsn=dsn, source_root=base_dir / "sources")
    return _PG_STORE


def _get_keyword_store() -> OpenSearchKeywordStore:
    global _KEYWORD_STORE
    if _KEYWORD_STORE is None:
        url = os.getenv("SCRIPTWRITER_OPENSEARCH_URL", "").strip()
        if not url:
            raise RuntimeError("Missing required environment variable: SCRIPTWRITER_OPENSEARCH_URL")
        index = os.getenv("SCRIPTWRITER_OPENSEARCH_INDEX", "knowledge_chunks_v1").strip() or "knowledge_chunks_v1"
        _KEYWORD_STORE = OpenSearchKeywordStore(url=url, index=index)
        _KEYWORD_STORE.ensure_index()
    return _KEYWORD_STORE


def _get_retrieval_pipeline() -> KnowledgeRetrievalPipeline:
    global _RETRIEVAL_PIPELINE
    if _RETRIEVAL_PIPELINE is None:
        rewrite_model = os.getenv("SCRIPTWRITER_QUERY_REWRITE_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
        rerank_model = os.getenv("SCRIPTWRITER_RERANK_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
        _RETRIEVAL_PIPELINE = KnowledgeRetrievalPipeline(
            keyword_store=_get_keyword_store(),
            vector_search_fn=search_milvus_bible_records,
            rewrite_model=rewrite_model,
            rerank_model=rerank_model,
        )
    return _RETRIEVAL_PIPELINE


def reset_knowledge_services_for_tests(data_dir: str | Path | None = None) -> None:
    global _PG_STORE, _KEYWORD_STORE, _RETRIEVAL_PIPELINE
    _PG_STORE = None
    _KEYWORD_STORE = None
    _RETRIEVAL_PIPELINE = None
    if data_dir is not None:
        os.environ["SCRIPTWRITER_RAG_DATA_DIR"] = str(data_dir)


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
) -> tuple[list[dict[str, object]], list[str], list[dict[str, object]], list[dict[str, object]]]:
    chunk_rows: list[dict[str, object]] = []
    texts: list[str] = []
    milvus_metadatas: list[dict[str, object]] = []
    keyword_docs: list[dict[str, object]] = []

    for idx, chunk in enumerate(chunks):
        chunk_id = f"{doc_id}:{idx}"
        row = {
            "chunk_id": chunk_id,
            "chunk_order": idx,
            "segment_type": chunk.segment_type,
            "text": chunk.text,
            "source_type": source_type,
            "version_id": version_id,
            "episode_id": episode_id,
            "scene_id": scene_id,
            "is_active": is_active,
            "title": title,
            "doc_type": doc_type,
            "path_l1": path_l1,
            "path_l2": path_l2,
        }
        chunk_rows.append(row)
        texts.append(chunk.text)
        milvus_metadatas.append(
            {
                "chunk_id": chunk_id,
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
        keyword_docs.append(
            {
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "doc_type": doc_type,
                "path_l1": path_l1,
                "path_l2": path_l2,
                "segment_type": chunk.segment_type,
                "chunk_order": idx,
                "title": title,
                "text": chunk.text,
                "source_type": source_type,
                "version_id": version_id,
                "episode_id": episode_id,
                "scene_id": scene_id,
                "is_active": is_active,
            }
        )

    return chunk_rows, texts, milvus_metadatas, keyword_docs


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

    pg_store = _get_pg_store()
    keyword_store = _get_keyword_store()

    source_path = pg_store.persist_source(resolved_doc_id, body)
    pg_store.upsert_document(
        doc_id=resolved_doc_id,
        user_id=user_id,
        project_id=project_id,
        doc_type=normalized_doc_type,
        title=resolved_title,
        path_l1=resolved_path_l1,
        path_l2=resolved_path_l2,
        source_path=source_path,
    )

    chunk_rows, texts, milvus_metadatas, keyword_docs = _build_chunk_payloads(
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
    pg_store.replace_chunks(doc_id=resolved_doc_id, user_id=user_id, project_id=project_id, chunks=chunk_rows)

    try:
        keyword_payload = [{**item, "user_id": user_id, "project_id": project_id} for item in keyword_docs]
        keyword_store.upsert_chunks(keyword_payload)
    except Exception:
        pg_store.delete_chunks_by_doc(resolved_doc_id)
        raise

    vectors = get_embeddings(texts)
    ok = add_texts_to_milvus(
        user_id=user_id,
        project_id=project_id,
        texts=texts,
        vectors=vectors,
        metadatas=milvus_metadatas,
    )
    if not ok:
        chunk_ids = [str(item["chunk_id"]) for item in keyword_docs]
        keyword_store.delete_chunks(chunk_ids)
        pg_store.delete_chunks_by_doc(resolved_doc_id)
        raise RuntimeError("Milvus indexing failed")

    return IngestResult(doc_id=resolved_doc_id, chunk_count=len(chunks), source_path=source_path)


def ingest_project_knowledge_document(**kwargs):
    return ingest_knowledge_document(**kwargs)


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

    configured_top_k = int(os.getenv("SCRIPTWRITER_RETRIEVAL_TOPK_FINAL", "5"))
    top_k = min(max(limit, 1), max(configured_top_k, 1))
    top_n_keyword = int(os.getenv("SCRIPTWRITER_RETRIEVAL_TOPN_KEYWORD", "12"))
    top_n_vector = int(os.getenv("SCRIPTWRITER_RETRIEVAL_TOPN_VECTOR", "12"))
    top_n_keyword = max(top_n_keyword, top_k)
    top_n_vector = max(top_n_vector, top_k)

    pg_store = _get_pg_store()
    candidates = pg_store.list_candidate_docs(
        user_id=user_id,
        project_id=project_id,
        query=query_text,
        doc_type=doc_type,
        path_l1=path_l1,
        path_l2=path_l2,
        limit=max(top_n_keyword, top_n_vector) * 4,
    )
    candidate_doc_ids = [candidate.doc_id for candidate in candidates]
    candidate_by_id = _candidate_map(candidates)
    if not candidate_doc_ids:
        return []

    filters: dict[str, object] = {"doc_ids": candidate_doc_ids}
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

    ranked = _get_retrieval_pipeline().run(
        query=query_text,
        user_id=user_id,
        project_id=project_id,
        top_n_keyword=top_n_keyword,
        top_n_vector=top_n_vector,
        top_k=top_k,
        filters=filters,
    )
    hits: list[KnowledgeHit] = []
    for candidate in ranked:
        payload = candidate.payload
        row_doc_id = payload.get("doc_id")
        doc_id_value = row_doc_id if isinstance(row_doc_id, str) and row_doc_id else None
        doc_candidate = candidate_by_id.get(doc_id_value or "")
        raw_chunk_order = payload.get("chunk_order")
        chunk_order_value = int(raw_chunk_order) if isinstance(raw_chunk_order, (int, float)) else None
        raw_is_active = payload.get("is_active")
        is_active_value = raw_is_active if isinstance(raw_is_active, bool) else None
        hits.append(
            KnowledgeHit(
                text=candidate.text,
                doc_id=doc_id_value,
                doc_type=_pick_str(payload.get("doc_type"), doc_candidate.doc_type if doc_candidate else None),
                title=_pick_str(payload.get("title"), doc_candidate.title if doc_candidate else None),
                path_l1=_pick_str(payload.get("path_l1"), doc_candidate.path_l1 if doc_candidate else None),
                path_l2=_pick_str(payload.get("path_l2"), doc_candidate.path_l2 if doc_candidate else None),
                segment_type=_pick_str(payload.get("segment_type"), None),
                chunk_order=chunk_order_value,
                score=float(candidate.score),
                source_backend=candidate.source_backend,
                source_type=_pick_str(payload.get("source_type"), source_type),
                version_id=_pick_str(payload.get("version_id"), version_id),
                episode_id=_pick_str(payload.get("episode_id"), episode_id),
                scene_id=_pick_str(payload.get("scene_id"), scene_id),
                is_active=is_active_value if is_active_value is not None else is_active,
            )
        )
    return hits[:top_k]


def search_project_knowledge_hits(**kwargs) -> list[ProjectKnowledgeHit]:
    hits = search_knowledge_hits(**kwargs)
    return [
        ProjectKnowledgeHit(
            text=hit.text,
            doc_id=hit.doc_id,
            doc_type=hit.doc_type,
            title=hit.title,
            path_l1=hit.path_l1,
            path_l2=hit.path_l2,
            segment_type=hit.segment_type,
            chunk_order=hit.chunk_order,
            score=hit.score,
            source_backend=hit.source_backend,
            source_type=hit.source_type,
            version_id=hit.version_id,
            episode_id=hit.episode_id,
            scene_id=hit.scene_id,
            is_active=hit.is_active,
        )
        for hit in hits
    ]


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
    pg_store = _get_pg_store()
    keyword_store = _get_keyword_store()
    docs = pg_store.list_documents(user_id=user_id, project_id=project_id, doc_id=doc_id)
    if not docs:
        return RebuildResult(docs_processed=0, chunks_indexed=0, deleted_vectors=0)

    doc_ids = [doc.doc_id for doc in docs]
    deleted = delete_milvus_documents(user_id=user_id, project_id=project_id, doc_ids=doc_ids)

    chunks_indexed = 0
    for doc in docs:
        body = pg_store.load_source_text(doc.doc_id)
        if not body:
            continue
        segments = segment_content(body, doc.doc_type)
        chunks = chunk_segments(segments, max_chars=chunk_max_chars, overlap=chunk_overlap)
        if not chunks:
            continue
        chunk_rows, texts, milvus_metadatas, keyword_docs = _build_chunk_payloads(
            doc_id=doc.doc_id,
            doc_type=doc.doc_type,
            title=doc.title,
            path_l1=doc.path_l1,
            path_l2=doc.path_l2,
            chunks=chunks,
        )
        pg_store.replace_chunks(doc_id=doc.doc_id, user_id=user_id, project_id=project_id, chunks=chunk_rows)
        keyword_payload = [{**item, "user_id": user_id, "project_id": project_id} for item in keyword_docs]
        keyword_store.upsert_chunks(keyword_payload)
        vectors = get_embeddings(texts)
        ok = add_texts_to_milvus(user_id=user_id, project_id=project_id, texts=texts, vectors=vectors, metadatas=milvus_metadatas)
        if not ok:
            raise RuntimeError("Milvus indexing failed during rebuild")
        chunks_indexed += len(chunks)

    return RebuildResult(docs_processed=len(docs), chunks_indexed=chunks_indexed, deleted_vectors=deleted)


def _pick_str(primary: object, fallback: str | None) -> str | None:
    if isinstance(primary, str) and primary:
        return primary
    return fallback

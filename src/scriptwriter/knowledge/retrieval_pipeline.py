from __future__ import annotations

import json
from dataclasses import dataclass

from scriptwriter.knowledge.embeddings import get_query_embedding
from scriptwriter.knowledge.keyword_store import KeywordHit, OpenSearchKeywordStore


@dataclass(frozen=True)
class RetrievalCandidate:
    chunk_id: str
    text: str
    score: float
    source_backend: str
    payload: dict[str, object]


def fuse_rrf(keyword_hits: list[KeywordHit], vector_hits: list[dict[str, object]], limit: int, k: int = 60) -> list[RetrievalCandidate]:
    by_chunk: dict[str, dict[str, object]] = {}
    score_map: dict[str, float] = {}

    for rank, hit in enumerate(keyword_hits, start=1):
        score_map[hit.chunk_id] = score_map.get(hit.chunk_id, 0.0) + 1.0 / (k + rank)
        by_chunk.setdefault(
            hit.chunk_id,
            {
                "chunk_id": hit.chunk_id,
                "text": str(hit.payload.get("text", "")),
                "source_backend": "keyword",
                "payload": dict(hit.payload),
            },
        )

    for rank, row in enumerate(vector_hits, start=1):
        chunk_id = row.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id:
            doc_id = str(row.get("doc_id", ""))
            chunk_order = row.get("chunk_order")
            chunk_id = f"{doc_id}:{chunk_order}"
        score_map[chunk_id] = score_map.get(chunk_id, 0.0) + 1.0 / (k + rank)
        payload = dict(row)
        by_chunk.setdefault(
            chunk_id,
            {
                "chunk_id": chunk_id,
                "text": str(payload.get("text", "")),
                "source_backend": "milvus",
                "payload": payload,
            },
        )
        by_chunk[chunk_id]["payload"].update(payload)

    ranked = sorted(score_map.items(), key=lambda item: item[1], reverse=True)
    out: list[RetrievalCandidate] = []
    for chunk_id, score in ranked[: max(limit, 1)]:
        raw = by_chunk[chunk_id]
        out.append(
            RetrievalCandidate(
                chunk_id=chunk_id,
                text=str(raw["text"]),
                score=float(score),
                source_backend=str(raw["source_backend"]),
                payload=dict(raw["payload"]),
            )
        )
    return out


class KnowledgeRetrievalPipeline:
    def __init__(
        self,
        *,
        keyword_store: OpenSearchKeywordStore,
        vector_search_fn,
        rewrite_model: str,
        rerank_model: str,
    ) -> None:
        self._keyword_store = keyword_store
        self._vector_search_fn = vector_search_fn
        self._rewrite_model = rewrite_model
        self._rerank_model = rerank_model

    def rewrite_query(self, query: str) -> str:
        try:
            from langchain_openai import ChatOpenAI
        except Exception as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(f"LLM client unavailable for query rewrite: {exc}") from exc

        llm = ChatOpenAI(model=self._rewrite_model, temperature=0)
        prompt = (
            "You are a retrieval rewriter.\n"
            "Rewrite the query for semantic and keyword retrieval, keep intent unchanged.\n"
            "Return only one rewritten query line.\n"
            f"Query: {query}"
        )
        result = llm.invoke(prompt)
        text = str(getattr(result, "content", "")).strip()
        if not text:
            raise RuntimeError("Query rewrite returned empty content")
        return text

    def hybrid_retrieve(
        self,
        *,
        query: str,
        user_id: str,
        project_id: str,
        top_n_keyword: int,
        top_n_vector: int,
        filters: dict[str, object],
    ) -> list[RetrievalCandidate]:
        keyword_hits = self._keyword_store.search(
            query=query,
            user_id=user_id,
            project_id=project_id,
            limit=top_n_keyword,
            doc_type=_as_optional_str(filters.get("doc_type")),
            path_l1=_as_optional_str(filters.get("path_l1")),
            path_l2=_as_optional_str(filters.get("path_l2")),
            source_type=_as_optional_str(filters.get("source_type")),
            version_id=_as_optional_str(filters.get("version_id")),
            episode_id=_as_optional_str(filters.get("episode_id")),
            scene_id=_as_optional_str(filters.get("scene_id")),
            is_active=_as_optional_bool(filters.get("is_active")),
        )
        query_vector = get_query_embedding(query)
        vector_hits = self._vector_search_fn(
            user_id=user_id,
            project_id=project_id,
            query_vector=query_vector,
            limit=top_n_vector,
            filters=filters,
        )
        return fuse_rrf(keyword_hits, vector_hits, limit=max(top_n_keyword, top_n_vector))

    def rerank(self, *, query: str, candidates: list[RetrievalCandidate], top_k: int) -> list[RetrievalCandidate]:
        if not candidates:
            return []
        try:
            from langchain_openai import ChatOpenAI
        except Exception as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(f"LLM client unavailable for rerank: {exc}") from exc

        llm = ChatOpenAI(model=self._rerank_model, temperature=0)
        payload = [
            {
                "chunk_id": candidate.chunk_id,
                "text": candidate.text[:1800],
            }
            for candidate in candidates
        ]
        prompt = (
            "You are a passage reranker.\n"
            "Given query and candidates, return JSON array of objects: "
            '[{"chunk_id":"...", "score":0.0}].\n'
            "Score range 0~1, higher is more relevant.\n"
            "Do not include any text outside JSON.\n"
            f"Query: {query}\nCandidates: {json.dumps(payload, ensure_ascii=True)}"
        )
        result = llm.invoke(prompt)
        text = str(getattr(result, "content", "")).strip()
        data = _parse_rerank_json(text)
        score_by_id = {item["chunk_id"]: item["score"] for item in data}

        ranked = sorted(
            candidates,
            key=lambda item: score_by_id.get(item.chunk_id, 0.0),
            reverse=True,
        )
        return ranked[: max(top_k, 1)]

    def run(
        self,
        *,
        query: str,
        user_id: str,
        project_id: str,
        top_n_keyword: int,
        top_n_vector: int,
        top_k: int,
        filters: dict[str, object],
    ) -> list[RetrievalCandidate]:
        rewritten = self.rewrite_query(query)
        fused = self.hybrid_retrieve(
            query=rewritten,
            user_id=user_id,
            project_id=project_id,
            top_n_keyword=top_n_keyword,
            top_n_vector=top_n_vector,
            filters=filters,
        )
        return self.rerank(query=query, candidates=fused, top_k=top_k)


def _parse_rerank_json(raw: str) -> list[dict[str, object]]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json", "", 1).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Failed to parse rerank response JSON") from exc
    if not isinstance(parsed, list):
        raise RuntimeError("Rerank response must be a JSON array")
    out: list[dict[str, object]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        chunk_id = item.get("chunk_id")
        score = item.get("score")
        if not isinstance(chunk_id, str):
            continue
        if not isinstance(score, (int, float)):
            continue
        out.append({"chunk_id": chunk_id, "score": float(score)})
    if not out:
        raise RuntimeError("Rerank response contains no valid scored candidates")
    return out


def _as_optional_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _as_optional_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


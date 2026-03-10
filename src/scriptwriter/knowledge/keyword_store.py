from __future__ import annotations

import json
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class KeywordHit:
    chunk_id: str
    score: float
    payload: dict[str, object]


class OpenSearchKeywordStore:
    def __init__(self, *, url: str, index: str, timeout_sec: float = 8.0) -> None:
        self._url = url.rstrip("/")
        self._index = index
        self._timeout_sec = timeout_sec

    def ping(self) -> None:
        with httpx.Client(timeout=self._timeout_sec) as client:
            response = client.get(f"{self._url}/_cluster/health")
            response.raise_for_status()

    def ensure_index(self) -> None:
        with httpx.Client(timeout=self._timeout_sec) as client:
            exists = client.head(f"{self._url}/{self._index}")
            if exists.status_code == 200:
                return
            if exists.status_code not in (404,):
                exists.raise_for_status()

            mapping = {
                "mappings": {
                    "properties": {
                        "chunk_id": {"type": "keyword"},
                        "doc_id": {"type": "keyword"},
                        "user_id": {"type": "keyword"},
                        "project_id": {"type": "keyword"},
                        "doc_type": {"type": "keyword"},
                        "path_l1": {"type": "keyword"},
                        "path_l2": {"type": "keyword"},
                        "source_type": {"type": "keyword"},
                        "version_id": {"type": "keyword"},
                        "episode_id": {"type": "keyword"},
                        "scene_id": {"type": "keyword"},
                        "is_active": {"type": "boolean"},
                        "title": {"type": "text"},
                        "text": {"type": "text"},
                        "segment_type": {"type": "keyword"},
                        "chunk_order": {"type": "integer"},
                    }
                }
            }
            created = client.put(f"{self._url}/{self._index}", json=mapping)
            created.raise_for_status()

    def upsert_chunks(self, chunks: list[dict[str, object]]) -> None:
        if not chunks:
            return
        lines: list[str] = []
        for chunk in chunks:
            chunk_id = str(chunk["chunk_id"])
            lines.append(json.dumps({"index": {"_index": self._index, "_id": chunk_id}}))
            lines.append(json.dumps(chunk))
        payload = "\n".join(lines) + "\n"
        headers = {"Content-Type": "application/x-ndjson"}
        with httpx.Client(timeout=self._timeout_sec) as client:
            response = client.post(f"{self._url}/_bulk", content=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
        if body.get("errors") is True:
            raise RuntimeError("OpenSearch bulk upsert failed")

    def delete_chunks(self, chunk_ids: list[str]) -> int:
        if not chunk_ids:
            return 0
        query = {"query": {"terms": {"chunk_id": chunk_ids}}}
        with httpx.Client(timeout=self._timeout_sec) as client:
            response = client.post(f"{self._url}/{self._index}/_delete_by_query", json=query)
            response.raise_for_status()
            body = response.json()
        deleted = body.get("deleted")
        if isinstance(deleted, int):
            return deleted
        return len(chunk_ids)

    def search(
        self,
        *,
        query: str,
        user_id: str,
        project_id: str,
        limit: int,
        doc_type: str | None = None,
        path_l1: str | None = None,
        path_l2: str | None = None,
        source_type: str | None = None,
        version_id: str | None = None,
        episode_id: str | None = None,
        scene_id: str | None = None,
        is_active: bool | None = None,
    ) -> list[KeywordHit]:
        filters: list[dict[str, object]] = [
            {"term": {"user_id": user_id}},
            {"term": {"project_id": project_id}},
        ]
        if doc_type:
            filters.append({"term": {"doc_type": doc_type}})
        if path_l1:
            filters.append({"term": {"path_l1": path_l1}})
        if path_l2:
            filters.append({"term": {"path_l2": path_l2}})
        if source_type:
            filters.append({"term": {"source_type": source_type}})
        if version_id:
            filters.append({"term": {"version_id": version_id}})
        if episode_id:
            filters.append({"term": {"episode_id": episode_id}})
        if scene_id:
            filters.append({"term": {"scene_id": scene_id}})
        if is_active is not None:
            filters.append({"term": {"is_active": is_active}})

        payload = {
            "size": max(limit, 1),
            "query": {
                "bool": {
                    "filter": filters,
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["text^3", "title^2", "path_l1", "path_l2", "doc_type"],
                            }
                        }
                    ],
                }
            },
        }
        with httpx.Client(timeout=self._timeout_sec) as client:
            response = client.post(f"{self._url}/{self._index}/_search", json=payload)
            response.raise_for_status()
            body = response.json()
        hits_payload = body.get("hits", {}).get("hits", [])
        hits: list[KeywordHit] = []
        for row in hits_payload:
            source = row.get("_source", {}) if isinstance(row, dict) else {}
            if not isinstance(source, dict):
                continue
            chunk_id = source.get("chunk_id")
            if not isinstance(chunk_id, str) or not chunk_id:
                continue
            raw_score = row.get("_score")
            score = float(raw_score) if isinstance(raw_score, (int, float)) else 0.0
            hits.append(KeywordHit(chunk_id=chunk_id, score=score, payload=source))
        return hits


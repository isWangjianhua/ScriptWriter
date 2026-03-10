from __future__ import annotations

import scriptwriter.knowledge.keyword_store as keyword_store_module
from scriptwriter.knowledge.keyword_store import OpenSearchKeywordStore


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, object] | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self) -> dict[str, object]:
        return dict(self._payload)


class _FakeClient:
    def __init__(self, calls: list[tuple[str, str, object | None]]):
        self.calls = calls

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def head(self, url: str):
        self.calls.append(("HEAD", url, None))
        return _FakeResponse(404)

    def put(self, url: str, json: dict[str, object]):
        self.calls.append(("PUT", url, json))
        return _FakeResponse(200, {"acknowledged": True})

    def post(self, url: str, json=None, content=None, headers=None):
        payload = json if json is not None else {"content": content, "headers": headers}
        self.calls.append(("POST", url, payload))
        if url.endswith("/_search"):
            return _FakeResponse(
                200,
                {
                    "hits": {
                        "hits": [
                            {
                                "_score": 1.23,
                                "_source": {"chunk_id": "c1", "text": "hero enters station"},
                            }
                        ]
                    }
                },
            )
        if url.endswith("/_bulk"):
            return _FakeResponse(200, {"errors": False})
        if url.endswith("/_delete_by_query"):
            return _FakeResponse(200, {"deleted": 1})
        return _FakeResponse(200, {})

    def get(self, url: str):
        self.calls.append(("GET", url, None))
        return _FakeResponse(200, {"status": "green"})


def test_keyword_store_ensure_index_and_search(monkeypatch):
    calls: list[tuple[str, str, object | None]] = []
    monkeypatch.setattr(keyword_store_module.httpx, "Client", lambda timeout: _FakeClient(calls))

    store = OpenSearchKeywordStore(url="http://localhost:9200", index="knowledge_chunks_v1")
    store.ensure_index()
    store.upsert_chunks([{"chunk_id": "c1", "text": "hero enters station", "user_id": "u1", "project_id": "p1"}])
    hits = store.search(query="hero", user_id="u1", project_id="p1", limit=3)

    assert any(method == "PUT" and "/knowledge_chunks_v1" in url for method, url, _ in calls)
    assert hits[0].chunk_id == "c1"

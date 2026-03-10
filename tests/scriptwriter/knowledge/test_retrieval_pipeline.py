from __future__ import annotations

from scriptwriter.knowledge.keyword_store import KeywordHit
from scriptwriter.knowledge.retrieval_pipeline import KnowledgeRetrievalPipeline, RetrievalCandidate, fuse_rrf


class _DummyKeywordStore:
    def search(self, **kwargs):
        _ = kwargs
        return [KeywordHit(chunk_id="c1", score=2.0, payload={"chunk_id": "c1", "text": "hero text"})]


def test_fuse_rrf_dedups_by_chunk_id():
    keyword_hits = [
        KeywordHit(chunk_id="c1", score=2.0, payload={"chunk_id": "c1", "text": "A"}),
        KeywordHit(chunk_id="c2", score=1.9, payload={"chunk_id": "c2", "text": "B"}),
    ]
    vector_hits = [
        {"chunk_id": "c2", "text": "B2"},
        {"chunk_id": "c3", "text": "C"},
    ]
    fused = fuse_rrf(keyword_hits, vector_hits, limit=3)
    ids = [item.chunk_id for item in fused]
    assert ids[0] == "c2"
    assert "c1" in ids and "c3" in ids


def test_pipeline_run_order(monkeypatch):
    pipeline = KnowledgeRetrievalPipeline(
        keyword_store=_DummyKeywordStore(),
        vector_search_fn=lambda **kwargs: [{"chunk_id": "c1", "text": "hero text"}],
        rewrite_model="gpt-4o-mini",
        rerank_model="gpt-4o-mini",
    )
    calls: list[str] = []

    monkeypatch.setattr(pipeline, "rewrite_query", lambda query: calls.append("rewrite") or f"rw:{query}")
    monkeypatch.setattr(
        pipeline,
        "hybrid_retrieve",
        lambda **kwargs: calls.append("hybrid") or [RetrievalCandidate("c1", "hero text", 0.8, "milvus", {"chunk_id": "c1"})],
    )
    monkeypatch.setattr(pipeline, "rerank", lambda **kwargs: calls.append("rerank") or kwargs["candidates"])

    out = pipeline.run(
        query="hero",
        user_id="u1",
        project_id="p1",
        top_n_keyword=3,
        top_n_vector=3,
        top_k=2,
        filters={},
    )

    assert calls == ["rewrite", "hybrid", "rerank"]
    assert out and out[0].chunk_id == "c1"

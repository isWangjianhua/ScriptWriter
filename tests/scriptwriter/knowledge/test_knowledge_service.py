from types import SimpleNamespace

from scriptwriter.knowledge.models import ProjectKnowledgeHit
from scriptwriter.knowledge.service import ingest_project_knowledge_document, search_knowledge_hits, search_project_knowledge_hits


def test_ingest_project_knowledge_passes_extended_metadata_to_rag(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_ingest(**kwargs):
        captured.update(kwargs)
        return "ok"

    monkeypatch.setattr("scriptwriter.knowledge.service.ingest_knowledge_document", _fake_ingest)

    result = ingest_project_knowledge_document(
        user_id="user_1",
        project_id="project_1",
        content="A hero enters the station.",
        doc_type="text",
        title="Episode Notes",
        source_type="outline",
        version_id="outline_v2",
        episode_id="ep1",
        scene_id="scene_3",
        is_active=True,
    )

    assert result == "ok"
    assert captured["source_type"] == "outline"
    assert captured["version_id"] == "outline_v2"
    assert captured["episode_id"] == "ep1"
    assert captured["scene_id"] == "scene_3"
    assert captured["is_active"] is True


def test_search_project_knowledge_hits_maps_rag_hits_to_project_hits(monkeypatch):
    class FakeHit:
        def __init__(self):
            self.text = "Hero opens the vault."
            self.doc_id = "doc_1"
            self.doc_type = "script"
            self.title = "Pilot"
            self.path_l1 = "season1"
            self.path_l2 = "ep1"
            self.segment_type = "scene"
            self.chunk_order = 2
            self.score = 0.91
            self.source_backend = "milvus"
            self.source_type = "draft"
            self.version_id = "draft_v1"
            self.episode_id = "ep1"
            self.scene_id = "scene_2"
            self.is_active = True

    monkeypatch.setattr(
        "scriptwriter.knowledge.service.search_knowledge_hits",
        lambda **kwargs: [FakeHit()],
    )

    hits = search_project_knowledge_hits(
        user_id="user_1",
        project_id="project_1",
        query="vault",
        version_id="draft_v1",
    )

    assert hits == [
        ProjectKnowledgeHit(
            text="Hero opens the vault.",
            doc_id="doc_1",
            doc_type="script",
            title="Pilot",
            path_l1="season1",
            path_l2="ep1",
            segment_type="scene",
            chunk_order=2,
            score=0.91,
            source_backend="milvus",
            source_type="draft",
            version_id="draft_v1",
            episode_id="ep1",
            scene_id="scene_2",
            is_active=True,
        )
    ]


def test_ingest_knowledge_raises_when_milvus_indexing_failed(monkeypatch):
    import scriptwriter.knowledge.service as service_module

    class _FakePgStore:
        def __init__(self):
            self.deleted_docs: list[str] = []

        def persist_source(self, doc_id: str, content: str) -> str:
            _ = content
            return f"/tmp/{doc_id}.txt"

        def upsert_document(self, **kwargs):
            _ = kwargs
            return None

        def replace_chunks(self, **kwargs):
            _ = kwargs
            return None

        def delete_chunks_by_doc(self, doc_id: str) -> int:
            self.deleted_docs.append(doc_id)
            return 1

    class _FakeKeywordStore:
        def __init__(self):
            self.deleted: list[str] = []

        def upsert_chunks(self, chunks):
            _ = chunks
            return None

        def delete_chunks(self, chunk_ids: list[str]) -> int:
            self.deleted.extend(chunk_ids)
            return len(chunk_ids)

    fake_pg = _FakePgStore()
    fake_keyword = _FakeKeywordStore()

    monkeypatch.setattr(service_module, "_get_pg_store", lambda: fake_pg)
    monkeypatch.setattr(service_module, "_get_keyword_store", lambda: fake_keyword)
    monkeypatch.setattr(
        service_module,
        "segment_content",
        lambda body, doc_type: [SimpleNamespace(text=body, segment_type="paragraph", segment_index=0)],
    )
    monkeypatch.setattr(
        service_module,
        "chunk_segments",
        lambda segments, max_chars, overlap: [
            SimpleNamespace(text=segments[0].text, segment_type="paragraph", segment_index=0, chunk_index=0)
        ],
    )
    monkeypatch.setattr(service_module, "get_embeddings", lambda texts: [[0.1] * 4 for _ in texts])
    monkeypatch.setattr(service_module, "add_texts_to_milvus", lambda **kwargs: False)

    try:
        service_module.ingest_knowledge_document(
            user_id="user_1",
            project_id="project_1",
            content="hello",
            doc_type="text",
        )
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "Milvus indexing failed" in str(exc)
        assert fake_keyword.deleted
        assert fake_pg.deleted_docs


def test_search_knowledge_hits_maps_pipeline_output(monkeypatch):
    import scriptwriter.knowledge.service as service_module

    monkeypatch.setattr(
        service_module,
        "_get_pg_store",
        lambda: SimpleNamespace(
            list_candidate_docs=lambda **kwargs: [
                SimpleNamespace(doc_id="doc_1", doc_type="script", title="Pilot", path_l1="s1", path_l2="ep1", source_path="/tmp/x")
            ]
        ),
    )
    monkeypatch.setattr(
        service_module,
        "_get_retrieval_pipeline",
        lambda: SimpleNamespace(
            run=lambda **kwargs: [
                SimpleNamespace(
                    chunk_id="doc_1:0",
                    text="Hero opens vault",
                    score=0.77,
                    source_backend="milvus",
                    payload={
                        "doc_id": "doc_1",
                        "doc_type": "script",
                        "title": "Pilot",
                        "path_l1": "s1",
                        "path_l2": "ep1",
                        "segment_type": "scene",
                        "chunk_order": 0,
                        "source_type": "draft",
                        "version_id": "draft_v1",
                        "episode_id": "ep1",
                        "scene_id": "scene_2",
                        "is_active": True,
                    },
                )
            ]
        ),
    )

    hits = search_knowledge_hits(user_id="user_1", project_id="project_1", query="vault", limit=1)
    assert len(hits) == 1
    assert hits[0].text == "Hero opens vault"
    assert hits[0].source_backend == "milvus"

from scriptwriter.knowledge.models import ProjectKnowledgeHit
from scriptwriter.knowledge.service import ingest_project_knowledge_document, search_project_knowledge_hits


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

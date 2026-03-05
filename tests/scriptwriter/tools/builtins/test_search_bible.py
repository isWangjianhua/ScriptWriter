import scriptwriter.tools.builtins.search_bible as search_bible_module
from scriptwriter.rag.service import KnowledgeHit
from scriptwriter.tools.builtins.search_bible import search_story_bible


def test_search_story_bible_formats_source_annotations(monkeypatch):
    def _fake_hits(**kwargs):
        _ = kwargs
        return [
            KnowledgeHit(
                text="Hero opens the vault.",
                doc_id="doc1",
                doc_type="script",
                title="Pilot",
                path_l1="season1",
                path_l2="ep1",
                segment_type="scene",
                chunk_order=2,
                score=0.8,
                source_backend="milvus",
            )
        ]

    monkeypatch.setattr(search_bible_module, "search_knowledge_hits", _fake_hits)

    output = search_story_bible.invoke(
        {"project_id": "project_1", "query": "vault"},
        config={"configurable": {"user_id": "user_1"}},
    )

    assert "Hero opens the vault." in output
    assert "[source: season1/ep1#chunk-2]" in output


def test_search_story_bible_no_hit_message(monkeypatch):
    monkeypatch.setattr(search_bible_module, "search_knowledge_hits", lambda **kwargs: [])

    output = search_story_bible.invoke(
        {"project_id": "project_1", "query": "nothing"},
        config={"configurable": {"user_id": "user_1"}},
    )

    assert output == "No relevant information found."

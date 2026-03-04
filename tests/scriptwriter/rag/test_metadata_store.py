from pathlib import Path

from scriptwriter.rag.metadata_store import KnowledgeMetadataStore


def test_metadata_store_persists_source_and_routes_candidates(tmp_path: Path):
    store = KnowledgeMetadataStore(
        db_path=tmp_path / "rag.db",
        source_root=tmp_path / "sources",
    )

    source_path_1 = store.persist_source("doc_script_a", "INT. LAB - DAY\nAlice enters.")
    store.upsert_document(
        doc_id="doc_script_a",
        user_id="u1",
        project_id="p1",
        doc_type="script",
        title="Episode 1",
        path_l1="season1",
        path_l2="ep1",
        source_path=source_path_1,
    )

    source_path_2 = store.persist_source("doc_novel_b", "CHAPTER 1\nBob travels.")
    store.upsert_document(
        doc_id="doc_novel_b",
        user_id="u1",
        project_id="p1",
        doc_type="novel",
        title="Side Story",
        path_l1="season2",
        path_l2="ep3",
        source_path=source_path_2,
    )

    store.replace_chunks(
        "doc_script_a",
        [{"chunk_order": 0, "segment_type": "scene", "text": "Alice enters the lab quickly."}],
    )
    store.replace_chunks(
        "doc_novel_b",
        [{"chunk_order": 0, "segment_type": "chapter", "text": "Bob travels across the sea."}],
    )

    candidates = store.list_candidate_docs(
        user_id="u1",
        project_id="p1",
        query="season1 lab",
        limit=5,
    )

    assert candidates
    assert candidates[0].doc_id == "doc_script_a"
    assert store.load_source_text("doc_script_a") == "INT. LAB - DAY\nAlice enters."


def test_metadata_store_chunk_keyword_search(tmp_path: Path):
    store = KnowledgeMetadataStore(db_path=tmp_path / "rag.db", source_root=tmp_path / "sources")
    path = store.persist_source("doc_text", "A plain text document.")
    store.upsert_document(
        doc_id="doc_text",
        user_id="u2",
        project_id="p2",
        doc_type="text",
        title="notes",
        path_l1="notes",
        path_l2="chapter",
        source_path=path,
    )
    store.replace_chunks(
        "doc_text",
        [
            {
                "chunk_order": 0,
                "segment_type": "paragraph",
                "text": "The red dragon lands in silence.",
            },
            {
                "chunk_order": 1,
                "segment_type": "paragraph",
                "text": "Clouds drift above the valley.",
            },
        ],
    )

    hits = store.search_chunks(doc_ids=["doc_text"], query="dragon", limit=3)
    assert hits
    assert "dragon" in hits[0].lower()

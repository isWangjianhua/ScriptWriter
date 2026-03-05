from pathlib import Path

import scriptwriter.rag.service as rag_service
from scriptwriter.rag import (
    ingest_knowledge_document,
    rebuild_knowledge_index,
    reset_knowledge_services_for_tests,
    search_knowledge,
    search_knowledge_hits,
)


def test_ingest_document_splits_and_writes_metadata(tmp_path: Path, monkeypatch):
    reset_knowledge_services_for_tests(data_dir=tmp_path)

    captured: dict[str, object] = {}

    def _fake_add_texts(user_id, project_id, texts, vectors, metadatas=None):
        captured["user_id"] = user_id
        captured["project_id"] = project_id
        captured["texts"] = list(texts)
        captured["metadatas"] = list(metadatas or [])
        return True

    monkeypatch.setattr(rag_service, "add_texts_to_milvus", _fake_add_texts)

    result = ingest_knowledge_document(
        user_id="u1",
        project_id="p1",
        content="INT. HALLWAY - NIGHT\nHe runs.\n\nEXT. ROOF - NIGHT\nShe waits.",
        doc_type="script",
        title="Pilot",
        path_l1="season1",
        path_l2="ep1",
    )

    assert result.chunk_count >= 2
    assert result.doc_id
    assert captured["user_id"] == "u1"
    assert captured["project_id"] == "p1"
    assert captured["metadatas"]


def test_search_knowledge_routes_by_metadata_before_vector(tmp_path: Path, monkeypatch):
    reset_knowledge_services_for_tests(data_dir=tmp_path)

    doc_a = ingest_knowledge_document(
        user_id="u1",
        project_id="p1",
        content="Hero walks into the control room.",
        doc_type="text",
        title="Mainline",
        path_l1="arc_a",
        path_l2="ch1",
    )
    ingest_knowledge_document(
        user_id="u1",
        project_id="p1",
        content="Villain studies the map.",
        doc_type="text",
        title="B Plot",
        path_l1="arc_b",
        path_l2="ch2",
    )

    captured_filters: dict[str, object] = {}

    def _fake_search(user_id, project_id, query_vector, limit=3, filters=None):
        captured_filters["value"] = dict(filters or {})
        return []

    monkeypatch.setattr(rag_service, "search_milvus_bible_records", _fake_search)

    results = search_knowledge(
        user_id="u1",
        project_id="p1",
        query="hero control room",
        path_l1="arc_a",
        limit=3,
    )

    assert results
    assert doc_a.doc_id in (captured_filters.get("value") or {}).get("doc_ids", [])
    assert "hero" in results[0].lower()


def test_search_knowledge_hits_include_source_metadata(tmp_path: Path, monkeypatch):
    reset_knowledge_services_for_tests(data_dir=tmp_path)

    doc = ingest_knowledge_document(
        user_id="u1",
        project_id="p1",
        content="Hero opens the old door in silence.",
        doc_type="text",
        title="Main Arc",
        path_l1="arc_a",
        path_l2="ch1",
    )

    def _fake_search(*args, **kwargs):
        return []

    monkeypatch.setattr(rag_service, "search_milvus_bible_records", _fake_search)

    hits = search_knowledge_hits(
        user_id="u1",
        project_id="p1",
        query="old door",
        path_l1="arc_a",
        limit=2,
    )

    assert hits
    assert hits[0].doc_id == doc.doc_id
    assert hits[0].title == "Main Arc"
    assert hits[0].path_l1 == "arc_a"
    assert hits[0].source_backend == "sqlite"


def test_rebuild_knowledge_index_reinserts_vectors(tmp_path: Path, monkeypatch):
    reset_knowledge_services_for_tests(data_dir=tmp_path)

    doc = ingest_knowledge_document(
        user_id="u1",
        project_id="p1",
        content="INT. ROOM - DAY\nHero sits.",
        doc_type="script",
        title="Pilot",
        path_l1="s1",
        path_l2="e1",
    )

    deleted: dict[str, object] = {}
    inserted: dict[str, object] = {}

    def _fake_delete(*, user_id, project_id, doc_ids):
        deleted["user_id"] = user_id
        deleted["project_id"] = project_id
        deleted["doc_ids"] = list(doc_ids)
        return len(doc_ids)

    def _fake_add(*, user_id, project_id, texts, vectors, metadatas=None):
        inserted["user_id"] = user_id
        inserted["project_id"] = project_id
        inserted["texts"] = list(texts)
        inserted["metadatas"] = list(metadatas or [])
        return True

    monkeypatch.setattr(rag_service, "delete_milvus_documents", _fake_delete)
    monkeypatch.setattr(rag_service, "add_texts_to_milvus", _fake_add)

    result = rebuild_knowledge_index(user_id="u1", project_id="p1", doc_id=doc.doc_id)

    assert result.docs_processed == 1
    assert result.chunks_indexed >= 1
    assert result.deleted_vectors == 1
    assert deleted["doc_ids"] == [doc.doc_id]
    assert inserted["texts"]

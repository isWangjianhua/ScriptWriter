from __future__ import annotations

from pathlib import Path

from scriptwriter.knowledge.metadata_store_pg import PostgresKnowledgeMetadataStore


def test_pg_store_upserts_documents_and_chunks(tmp_path: Path):
    db_path = tmp_path / "knowledge.db"
    store = PostgresKnowledgeMetadataStore(
        dsn=f"sqlite+pysqlite:///{db_path}",
        source_root=tmp_path / "sources",
    )
    source_path = store.persist_source("doc1", "hello world")
    assert source_path.endswith("doc1.txt")

    store.upsert_document(
        doc_id="doc1",
        user_id="u1",
        project_id="p1",
        doc_type="text",
        title="title",
        path_l1="p1",
        path_l2="p2",
        source_path=source_path,
    )
    store.replace_chunks(
        doc_id="doc1",
        user_id="u1",
        project_id="p1",
        chunks=[{"chunk_id": "doc1:0", "chunk_order": 0, "segment_type": "paragraph", "text": "hello"}],
    )
    docs = store.list_candidate_docs(user_id="u1", project_id="p1", query="title")
    assert docs and docs[0].doc_id == "doc1"

    chunk_hits = store.search_chunk_rows(doc_ids=["doc1"], query="hello", limit=3)
    assert chunk_hits and chunk_hits[0].chunk_id == "doc1:0"


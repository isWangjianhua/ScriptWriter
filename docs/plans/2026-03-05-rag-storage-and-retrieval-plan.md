# RAG Storage And Retrieval Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a production-lean RAG ingestion and retrieval path that leverages structured script/novel segmentation while still supporting plain text and persisting metadata artifacts to disk.

**Architecture:** Add a `rag` service that orchestrates segmentation, chunking, embedding, metadata persistence, and vector retrieval. Use SQLite for deterministic local metadata + source artifact persistence, and Milvus for vector similarity with strict metadata filters to reduce unrelated recalls.

**Tech Stack:** Python 3.11+, FastAPI, sqlite3, pymilvus (optional runtime), pytest/httpx.

---

### Task 1: RAG metadata persistence foundation

**Files:**
- Create: `src/scriptwriter/rag/metadata_store.py`
- Test: `tests/scriptwriter/rag/test_metadata_store.py`

**Step 1: Write the failing test**
- Add tests for ingesting a document, listing candidates with metadata filters, and loading persisted source.

**Step 2: Run test to verify it fails**
- Run: `uv run pytest tests/scriptwriter/rag/test_metadata_store.py -q`
- Expected: FAIL due to missing module/behavior.

**Step 3: Write minimal implementation**
- Implement SQLite schema and methods: `save_source`, `upsert_document`, `insert_chunks`, `list_candidates`.

**Step 4: Run test to verify it passes**
- Run: `uv run pytest tests/scriptwriter/rag/test_metadata_store.py -q`
- Expected: PASS.

**Step 5: Commit**
- `git add tests/scriptwriter/rag/test_metadata_store.py src/scriptwriter/rag/metadata_store.py`
- `git commit -m "feat(rag): add metadata persistence store"`

### Task 2: Service-level ingest and retrieval routing

**Files:**
- Create: `src/scriptwriter/rag/service.py`
- Modify: `src/scriptwriter/rag/__init__.py`
- Modify: `src/scriptwriter/agents/memory/milvus_store.py`
- Modify: `src/scriptwriter/tools/builtins/search_bible.py`
- Test: `tests/scriptwriter/rag/test_service.py`

**Step 1: Write the failing test**
- Add service tests for doc ingestion and filtered retrieval by path/doc-type.

**Step 2: Run test to verify it fails**
- Run: `uv run pytest tests/scriptwriter/rag/test_service.py -q`
- Expected: FAIL due to missing service and filter flow.

**Step 3: Write minimal implementation**
- Implement service functions: `ingest_knowledge_document`, `search_knowledge`, `reset_knowledge_services_for_tests`.
- Extend Milvus insert/search metadata filter support (`doc_id`, `doc_type`, `segment_type`, `path_l1`, `path_l2`).
- Update tool to call service instead of direct Milvus function.

**Step 4: Run test to verify it passes**
- Run: `uv run pytest tests/scriptwriter/rag/test_service.py -q`
- Expected: PASS.

**Step 5: Commit**
- `git add ...`
- `git commit -m "feat(rag): add ingest/search service with metadata routing"`

### Task 3: API ingestion endpoint

**Files:**
- Modify: `src/scriptwriter/gateway/routers/chat.py`
- Test: `tests/scriptwriter/gateway/routers/test_chat.py`

**Step 1: Write the failing test**
- Add test for `POST /api/knowledge/ingest` success + validation.

**Step 2: Run test to verify it fails**
- Run: `uv run pytest tests/scriptwriter/gateway/routers/test_chat.py -q`
- Expected: FAIL due to missing endpoint.

**Step 3: Write minimal implementation**
- Add request schema and endpoint that calls rag service ingest.

**Step 4: Run test to verify it passes**
- Run: `uv run pytest tests/scriptwriter/gateway/routers/test_chat.py -q`
- Expected: PASS.

**Step 5: Commit**
- `git add ...`
- `git commit -m "feat(api): add knowledge ingest endpoint"`

### Task 4: End-to-end verification

**Files:**
- Test: existing and newly added tests

**Step 1: Run focused test suite**
- Run: `uv run pytest tests/scriptwriter/rag tests/scriptwriter/gateway/routers/test_chat.py -q`

**Step 2: Run full test suite**
- Run: `uv run pytest -q`

**Step 3: Record evidence**
- Capture pass/fail counts and any residual risk.

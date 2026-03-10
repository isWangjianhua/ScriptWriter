# Knowledge Hybrid Retrieval Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace SQLite-only knowledge metadata and simple retrieval with a strong-dependency PostgreSQL + OpenSearch + Milvus pipeline that executes rewrite, hybrid retrieve, and rerank for query search.

**Architecture:** Keep public knowledge service APIs stable while introducing backend adapters: PostgreSQL metadata repository, OpenSearch keyword index, and retrieval pipeline components for LLM query rewrite, score-fused hybrid retrieval, and LLM reranking. Fail fast at startup and runtime when PostgreSQL, OpenSearch, or Milvus is unavailable.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, psycopg3, OpenSearch/Elasticsearch client, pymilvus, LangChain OpenAI, pytest.

---

### Task 1: Add failing tests for strong dependency bootstrap checks

**Files:**
- Modify: `tests/scriptwriter/test_bootstrap.py`
- Modify: `src/scriptwriter/api/app.py`
- Test: `tests/scriptwriter/test_bootstrap.py`

**Step 1: Write the failing test**

```python
def test_app_startup_fails_when_knowledge_dependencies_unavailable(monkeypatch):
    monkeypatch.setattr("scriptwriter.knowledge.dependencies.check_knowledge_dependencies", lambda: (_ for _ in ()).throw(RuntimeError("pg down")))
    with pytest.raises(RuntimeError, match="pg down"):
        importlib.reload(importlib.import_module("scriptwriter.api.app"))
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scriptwriter/test_bootstrap.py::test_app_startup_fails_when_knowledge_dependencies_unavailable -q`
Expected: FAIL because startup currently does not enforce dependency health checks.

**Step 3: Write minimal implementation**

```python
def _initialize_dependencies() -> None:
    check_knowledge_dependencies()

_initialize_dependencies()
app = FastAPI(title="ScriptWriter Project API")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/scriptwriter/test_bootstrap.py::test_app_startup_fails_when_knowledge_dependencies_unavailable -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/scriptwriter/test_bootstrap.py src/scriptwriter/api/app.py src/scriptwriter/knowledge/dependencies.py
git commit -m "feat(knowledge): enforce strong dependency checks at app startup"
```

### Task 2: Introduce PostgreSQL metadata repository contract and failing tests

**Files:**
- Create: `src/scriptwriter/knowledge/metadata_repository.py`
- Create: `src/scriptwriter/knowledge/metadata_store_pg.py`
- Create: `tests/scriptwriter/knowledge/test_metadata_store_pg.py`
- Modify: `src/scriptwriter/knowledge/service.py`

**Step 1: Write the failing test**

```python
def test_pg_store_upserts_documents_and_chunks(monkeypatch):
    store = PostgresKnowledgeMetadataStore(dsn="postgresql://x")
    store.upsert_document(...)
    store.replace_chunks(...)
    docs = store.list_candidate_docs(user_id="u1", project_id="p1", query="hero")
    assert docs
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scriptwriter/knowledge/test_metadata_store_pg.py -q`
Expected: FAIL because PG metadata store does not exist.

**Step 3: Write minimal implementation**

```python
class PostgresKnowledgeMetadataStore(KnowledgeMetadataRepository):
    def upsert_document(...): ...
    def replace_chunks(...): ...
    def list_candidate_docs(...): ...
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/scriptwriter/knowledge/test_metadata_store_pg.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/scriptwriter/knowledge/metadata_repository.py src/scriptwriter/knowledge/metadata_store_pg.py tests/scriptwriter/knowledge/test_metadata_store_pg.py src/scriptwriter/knowledge/service.py
git commit -m "feat(knowledge): add PostgreSQL metadata repository"
```

### Task 3: Add OpenSearch keyword index adapter with failing tests

**Files:**
- Create: `src/scriptwriter/knowledge/keyword_store.py`
- Create: `tests/scriptwriter/knowledge/test_keyword_store.py`

**Step 1: Write the failing test**

```python
def test_keyword_store_indexes_and_searches_chunks(monkeypatch):
    store = OpenSearchKeywordStore(url="http://localhost:9200", index="knowledge_chunks_v1")
    store.upsert_chunks([{"chunk_id": "c1", "text": "hero enters station", "user_id": "u1", "project_id": "p1"}])
    hits = store.search(query="hero station", user_id="u1", project_id="p1", limit=3)
    assert hits[0]["chunk_id"] == "c1"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scriptwriter/knowledge/test_keyword_store.py -q`
Expected: FAIL because keyword store does not exist.

**Step 3: Write minimal implementation**

```python
class OpenSearchKeywordStore:
    def ensure_index(self) -> None: ...
    def upsert_chunks(self, chunks: list[dict[str, object]]) -> None: ...
    def search(self, *, query: str, user_id: str, project_id: str, limit: int, **filters) -> list[dict[str, object]]: ...
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/scriptwriter/knowledge/test_keyword_store.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/scriptwriter/knowledge/keyword_store.py tests/scriptwriter/knowledge/test_keyword_store.py
git commit -m "feat(knowledge): add OpenSearch keyword index adapter"
```

### Task 4: Add query rewrite and rerank components with failing tests

**Files:**
- Create: `src/scriptwriter/knowledge/retrieval_pipeline.py`
- Create: `tests/scriptwriter/knowledge/test_retrieval_pipeline.py`

**Step 1: Write the failing test**

```python
def test_pipeline_rewrites_query_then_reranks(monkeypatch):
    pipeline = KnowledgeRetrievalPipeline(...)
    monkeypatch.setattr(pipeline, "_rewrite_query", lambda q: "expanded query")
    monkeypatch.setattr(pipeline, "_rerank", lambda q, cands, k: cands[:k])
    out = pipeline.run(query="hero", user_id="u1", project_id="p1", top_k=2)
    assert out
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scriptwriter/knowledge/test_retrieval_pipeline.py -q`
Expected: FAIL because retrieval pipeline does not exist.

**Step 3: Write minimal implementation**

```python
class KnowledgeRetrievalPipeline:
    def run(self, *, query: str, user_id: str, project_id: str, top_k: int, **filters) -> list[dict[str, object]]:
        rewritten = self._rewrite_query(query)
        fused = self._hybrid_retrieve(rewritten, user_id=user_id, project_id=project_id, **filters)
        return self._rerank(query, fused, top_k)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/scriptwriter/knowledge/test_retrieval_pipeline.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/scriptwriter/knowledge/retrieval_pipeline.py tests/scriptwriter/knowledge/test_retrieval_pipeline.py
git commit -m "feat(knowledge): add rewrite and rerank pipeline components"
```

### Task 5: Implement hybrid fusion logic (keyword + vector) with failing tests

**Files:**
- Modify: `src/scriptwriter/knowledge/retrieval_pipeline.py`
- Modify: `tests/scriptwriter/knowledge/test_retrieval_pipeline.py`

**Step 1: Write the failing test**

```python
def test_hybrid_retrieve_uses_rrf_and_dedup_by_chunk_id():
    keyword_hits = [{"chunk_id": "c1", "score": 8.0}, {"chunk_id": "c2", "score": 7.5}]
    vector_hits = [{"chunk_id": "c2", "score": 0.9}, {"chunk_id": "c3", "score": 0.88}]
    fused = fuse_rrf(keyword_hits, vector_hits, limit=3)
    assert [x["chunk_id"] for x in fused] == ["c2", "c1", "c3"]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scriptwriter/knowledge/test_retrieval_pipeline.py::test_hybrid_retrieve_uses_rrf_and_dedup_by_chunk_id -q`
Expected: FAIL because fusion logic does not exist.

**Step 3: Write minimal implementation**

```python
def fuse_rrf(keyword_hits: list[dict[str, object]], vector_hits: list[dict[str, object]], limit: int) -> list[dict[str, object]]:
    # rank-based reciprocal fusion by chunk_id
    ...
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/scriptwriter/knowledge/test_retrieval_pipeline.py::test_hybrid_retrieve_uses_rrf_and_dedup_by_chunk_id -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/scriptwriter/knowledge/retrieval_pipeline.py tests/scriptwriter/knowledge/test_retrieval_pipeline.py
git commit -m "feat(knowledge): add hybrid RRF fusion"
```

### Task 6: Rewire ingest path to PG + OpenSearch + Milvus with failure compensation

**Files:**
- Modify: `src/scriptwriter/knowledge/service.py`
- Modify: `tests/scriptwriter/knowledge/test_knowledge_service.py`

**Step 1: Write the failing test**

```python
def test_ingest_writes_pg_opensearch_milvus_and_raises_on_any_backend_failure(monkeypatch):
    monkeypatch.setattr(service_module, "add_texts_to_milvus", lambda **kwargs: False)
    with pytest.raises(RuntimeError, match="Milvus indexing failed"):
        ingest_knowledge_document(...)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scriptwriter/knowledge/test_knowledge_service.py::test_ingest_writes_pg_opensearch_milvus_and_raises_on_any_backend_failure -q`
Expected: FAIL because ingest currently tolerates backend failures.

**Step 3: Write minimal implementation**

```python
ok = add_texts_to_milvus(...)
if not ok:
    keyword_store.delete_chunks(chunk_ids)
    pg_store.delete_chunks(doc_id)
    raise RuntimeError("Milvus indexing failed")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/scriptwriter/knowledge/test_knowledge_service.py::test_ingest_writes_pg_opensearch_milvus_and_raises_on_any_backend_failure -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/scriptwriter/knowledge/service.py tests/scriptwriter/knowledge/test_knowledge_service.py
git commit -m "feat(knowledge): enforce strong ingest consistency across stores"
```

### Task 7: Rewire search path to rewrite -> hybrid retrieve -> rerank

**Files:**
- Modify: `src/scriptwriter/knowledge/service.py`
- Modify: `tests/scriptwriter/knowledge/test_knowledge_service.py`
- Modify: `tests/scriptwriter/tools/builtins/test_search_bible.py`

**Step 1: Write the failing test**

```python
def test_search_knowledge_hits_uses_pipeline_order(monkeypatch):
    calls = []
    monkeypatch.setattr(service_module, "rewrite_query", lambda q, **k: calls.append("rewrite") or q)
    monkeypatch.setattr(service_module, "hybrid_retrieve", lambda **k: calls.append("hybrid") or [{"chunk_id": "c1", "text": "x"}])
    monkeypatch.setattr(service_module, "rerank_hits", lambda **k: calls.append("rerank") or [{"chunk_id": "c1", "text": "x"}])
    search_knowledge_hits(user_id="u1", project_id="p1", query="hero")
    assert calls == ["rewrite", "hybrid", "rerank"]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scriptwriter/knowledge/test_knowledge_service.py::test_search_knowledge_hits_uses_pipeline_order -q`
Expected: FAIL because search path currently bypasses rewrite/rerank.

**Step 3: Write minimal implementation**

```python
rewritten_query = retrieval_pipeline.rewrite(query, user_id=user_id, project_id=project_id)
fused = retrieval_pipeline.hybrid_retrieve(query=rewritten_query, user_id=user_id, project_id=project_id, ...)
ranked = retrieval_pipeline.rerank(original_query=query, candidates=fused, top_k=top_k)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/scriptwriter/knowledge/test_knowledge_service.py::test_search_knowledge_hits_uses_pipeline_order -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/scriptwriter/knowledge/service.py tests/scriptwriter/knowledge/test_knowledge_service.py tests/scriptwriter/tools/builtins/test_search_bible.py
git commit -m "feat(knowledge): add rewrite-hybrid-rerank search flow"
```

### Task 8: Add explicit dependency check module for PostgreSQL, OpenSearch, Milvus

**Files:**
- Create: `src/scriptwriter/knowledge/dependencies.py`
- Create: `tests/scriptwriter/knowledge/test_dependencies.py`
- Modify: `src/scriptwriter/api/app.py`

**Step 1: Write the failing test**

```python
def test_check_knowledge_dependencies_raises_when_opensearch_unavailable(monkeypatch):
    monkeypatch.setattr("scriptwriter.knowledge.dependencies._check_opensearch", lambda: (_ for _ in ()).throw(RuntimeError("os down")))
    with pytest.raises(RuntimeError, match="os down"):
        check_knowledge_dependencies()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scriptwriter/knowledge/test_dependencies.py -q`
Expected: FAIL because dependency checker does not exist.

**Step 3: Write minimal implementation**

```python
def check_knowledge_dependencies() -> None:
    _check_postgres()
    _check_opensearch()
    _check_milvus()
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/scriptwriter/knowledge/test_dependencies.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/scriptwriter/knowledge/dependencies.py tests/scriptwriter/knowledge/test_dependencies.py src/scriptwriter/api/app.py
git commit -m "feat(knowledge): add explicit strong dependency health checks"
```

### Task 9: Add and validate `.env.example`

**Files:**
- Create: `.env.example`
- Modify: `README.md`
- Modify: `README_ZH.md`
- Modify: `docs/en/operations.md`
- Modify: `docs/zh/operations.md`

**Step 1: Write the failing test**

```python
def test_env_example_contains_required_knowledge_settings():
    text = Path(".env.example").read_text(encoding="utf-8")
    required = [
        "SCRIPTWRITER_KNOWLEDGE_PG_DSN=",
        "SCRIPTWRITER_OPENSEARCH_URL=",
        "SCRIPTWRITER_OPENSEARCH_INDEX=",
        "SCRIPTWRITER_QUERY_REWRITE_MODEL=",
        "SCRIPTWRITER_RERANK_MODEL=",
    ]
    for key in required:
        assert key in text
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/scriptwriter/test_bootstrap.py::test_env_example_contains_required_knowledge_settings -q`
Expected: FAIL because `.env.example` or required keys do not exist.

**Step 3: Write minimal implementation**

```dotenv
SCRIPTWRITER_KNOWLEDGE_PG_DSN=postgresql://postgres:password@127.0.0.1:5432/scriptwriter
SCRIPTWRITER_OPENSEARCH_URL=http://127.0.0.1:9200
SCRIPTWRITER_OPENSEARCH_INDEX=knowledge_chunks_v1
SCRIPTWRITER_QUERY_REWRITE_MODEL=gpt-4o-mini
SCRIPTWRITER_RERANK_MODEL=gpt-4o-mini
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/scriptwriter/test_bootstrap.py::test_env_example_contains_required_knowledge_settings -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add .env.example README.md README_ZH.md docs/en/operations.md docs/zh/operations.md tests/scriptwriter/test_bootstrap.py
git commit -m "docs(config): add env example for hybrid knowledge stack"
```

### Task 10: Full verification before merge

**Files:**
- Modify: none (verification only)

**Step 1: Run focused knowledge tests**

Run: `uv run pytest tests/scriptwriter/knowledge -q`
Expected: PASS with no failures.

**Step 2: Run API and tool regression tests**

Run: `uv run pytest tests/scriptwriter/api/test_projects.py tests/scriptwriter/tools/builtins/test_search_bible.py -q`
Expected: PASS.

**Step 3: Run lint**

Run: `uv run --extra dev ruff check src tests`
Expected: PASS with zero errors.

**Step 4: Run full test suite**

Run: `uv run pytest -q`
Expected: PASS.

**Step 5: Commit verification update**

```bash
git add docs/en/api-reference.md docs/zh/api-reference.md docs/en/architecture.md docs/zh/architecture.md
git commit -m "docs(knowledge): document hybrid retrieval behavior and strong dependencies"
```


# Operations and Configuration

## Runtime Commands

Install:

```bash
uv sync
```

Run API:

```bash
PYTHONPATH=src uv run uvicorn scriptwriter.gateway.app:app --reload
```

Run tests and lint:

```bash
uv run pytest -q
uv run --extra dev ruff check src tests
```

Rebuild knowledge index:

```bash
uv run python scripts/rebuild_knowledge_index.py \
  --user-id user_1 \
  --project-id project_alpha
```

## Environment Variables

### Core

- `OPENAI_API_KEY`
- `SCRIPTWRITER_DATABASE_URL`
- `SCRIPTWRITER_THREADS_DIR` (default `data/threads`)
- `SCRIPTWRITER_RAG_DATA_DIR` (default `data/rag`)
- `SCRIPTWRITER_MAX_UPLOAD_BYTES` (default `20971520`)

### Models

- `SCRIPTWRITER_WRITER_MODEL` (default `gpt-4o`)
- `SCRIPTWRITER_CRITIC_MODEL` (default `gpt-4o-mini`)

### Embeddings / Retrieval

- `SCRIPTWRITER_EMBEDDING_PROVIDER` (`auto`, `openai`, `mock`)
- `SCRIPTWRITER_EMBEDDING_MODEL`
- `SCRIPTWRITER_MILVUS_DB_PATH` (default `./data/milvus_demo.db`)

### MCP

- `SCRIPTWRITER_MCP_SERVERS_JSON`
- `SCRIPTWRITER_ENABLE_BRAVE_MCP`
- `BRAVE_API_KEY`

## State Store Selection

Selection happens in `state_store/factory.py`:

- if `SCRIPTWRITER_DATABASE_URL` is set and Postgres init succeeds -> PostgreSQL store
- otherwise -> in-memory store

Operational recommendation:

- Use PostgreSQL for any persistent/staging/production environment.
- In-memory store is suitable for local tests and demos only.

## Data Directories

- Thread runtime files: `data/threads/{thread_id}/...`
- RAG metadata/sources: `data/rag/...`
- Milvus local db: `data/milvus_demo.db` (default path)

`data/threads/` is runtime state and should not be committed.

## Observability Gaps (Current)

The current codebase does not yet provide:

- unified request ID tracing
- structured metrics export
- centralized auth context propagation

These are recommended next steps before production hardening.

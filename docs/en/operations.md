# Operations and Configuration

## Runtime Commands

Install:

```bash
uv sync
```

Run API:

```bash
PYTHONPATH=src uv run uvicorn scriptwriter.api.app:app --reload
```

Run tests and lint:

```bash
uv run pytest -q
uv run --extra dev ruff check src tests
```

## Environment Variables

### Knowledge Storage

- `SCRIPTWRITER_RAG_DATA_DIR`  
  Base directory for SQLite metadata and persisted source text. Default: `data/rag`
- `SCRIPTWRITER_MILVUS_DB_PATH`  
  Local Milvus database path. Default: `./data/milvus_demo.db`

### Embeddings

- `OPENAI_API_KEY`
- `SCRIPTWRITER_EMBEDDING_PROVIDER`  
  Supported values: `auto`, `openai`, `mock`
- `SCRIPTWRITER_EMBEDDING_MODEL`  
  Default OpenAI embedding model: `text-embedding-3-small`

### MCP

- `SCRIPTWRITER_MCP_SERVERS_JSON`  
  JSON object of MCP server configs
- `SCRIPTWRITER_ENABLE_BRAVE_MCP`  
  Legacy shortcut for enabling Brave MCP via stdio
- `BRAVE_API_KEY`

## Persistence Model

### Project Workflow State

- projects
- artifact versions
- confirmation records

These live only in process memory through `InMemoryProjectStore`. Restarting the API clears them.

### Knowledge Data

- document metadata: SQLite database under `data/rag/metadata.db` by default
- source text: `data/rag/sources/`
- vector data: Milvus local db file

Knowledge data survives process restarts.

## Operational Notes

- There is no documented production persistence backend for project workflow state in the current implementation.
- If Milvus is unavailable, ingest still persists metadata and source text, but vector search is reduced or disabled.
- If OpenAI embeddings are unavailable, the system falls back to hash-based embeddings.

## Data Directories

- Knowledge metadata and source text: `data/rag/...`
- Milvus local database: `data/milvus_demo.db` by default

## Observability Gaps

The current codebase does not yet provide:

- request-level tracing
- structured metrics export
- authentication-derived runtime context
- durable project workflow storage

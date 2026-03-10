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
- `SCRIPTWRITER_KNOWLEDGE_PG_DSN`  
  PostgreSQL DSN for knowledge metadata storage (required)
- `SCRIPTWRITER_OPENSEARCH_URL`  
  OpenSearch/Elasticsearch-compatible endpoint URL (required)
- `SCRIPTWRITER_OPENSEARCH_INDEX`  
  Keyword index name, default `knowledge_chunks_v1`

### Embeddings

- `OPENAI_API_KEY`
- `SCRIPTWRITER_EMBEDDING_PROVIDER`  
  Supported values: `auto`, `openai`, `mock`
- `SCRIPTWRITER_EMBEDDING_MODEL`  
  Default OpenAI embedding model: `text-embedding-3-small`
- `SCRIPTWRITER_QUERY_REWRITE_MODEL`  
  LLM model used for query rewrite
- `SCRIPTWRITER_RERANK_MODEL`  
  LLM model used for reranking
- `SCRIPTWRITER_RETRIEVAL_TOPN_VECTOR`
- `SCRIPTWRITER_RETRIEVAL_TOPN_KEYWORD`
- `SCRIPTWRITER_RETRIEVAL_TOPK_FINAL`

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
- Knowledge retrieval startup now enforces strong dependencies: PostgreSQL, OpenSearch, and Milvus must all be available.
- Query path is `rewrite -> hybrid retrieve -> rerank` with LLM rewrite/rerank models.

## Data Directories

- Knowledge metadata and source text: `data/rag/...`
- Milvus local database: `data/milvus_demo.db` by default

## Observability Gaps

The current codebase does not yet provide:

- request-level tracing
- structured metrics export
- authentication-derived runtime context
- durable project workflow storage

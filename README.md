# ScriptWriter

Multi-agent screenplay orchestration backend, built with FastAPI.

## Overview

ScriptWriter separates two core concerns:

- `RAG` (retrieval): fetch external knowledge such as story bible content.
- `Memory` (state flow): persist run/session progression, events, and snapshots for recovery.

The current lead-agent flow is:

1. `planner`
2. `writer`
3. `critic`
4. revision loop or completion

## Key Features

- Multi-agent orchestration (`planner -> writer -> critic`)
- Recoverable state flow (`session/run/events/snapshot`)
- NDJSON streaming chat API (`/api/chat`)
- Run recovery API (`/api/runs/{run_id}`)
- State store fallback strategy:
  - PostgreSQL when `SCRIPTWRITER_DATABASE_URL` is configured
  - In-memory store otherwise

## Tech Stack

- Python 3.11 - 3.13
- FastAPI / Uvicorn
- LangChain / LangGraph
- Milvus (RAG vector retrieval)
- PostgreSQL (`psycopg`) for durable state store

## Quick Start

### 1. Install

```bash
uv sync
```

### 2. Run API

```bash
PYTHONPATH=src uvicorn scriptwriter.gateway.app:app --reload
```

### 3. Run Tests

```bash
uv run pytest -q
```

## Configuration

### Core Environment Variables

- `OPENAI_API_KEY`: enable LLM-backed planner/writer behavior.
- `SCRIPTWRITER_DATABASE_URL`: PostgreSQL DSN for persistent state store.
- `SCRIPTWRITER_MCP_SERVERS_JSON`: JSON object for MCP servers.
- `SCRIPTWRITER_ENABLE_BRAVE_MCP`: set to `1` to enable legacy Brave MCP config.
- `BRAVE_API_KEY`: used when Brave MCP is enabled.
- `SCRIPTWRITER_RAG_DATA_DIR`: local RAG metadata/source directory (default `data/rag`).
- `SCRIPTWRITER_MILVUS_DB_PATH`: Milvus local db path (default `./data/milvus_demo.db`).
- `SCRIPTWRITER_EMBEDDING_PROVIDER`: `auto`/`openai`/`mock`.
- `SCRIPTWRITER_EMBEDDING_MODEL`: OpenAI embedding model when provider is openai.
- `BRAVE_API_KEY`: when set, internet search uses Brave Search API first.

### MCP JSON Example

```bash
export SCRIPTWRITER_MCP_SERVERS_JSON='{
  "example-server": {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-example"],
    "enabled": true
  }
}'
```

## API

### `POST /api/chat`

Input JSON:

```json
{
  "message": "Write a suspense opening scene",
  "user_id": "user_1",
  "project_id": "project_alpha"
}
```

Response is NDJSON (`application/x-ndjson`), including events like:

- `run_started`
- `canvas_update`
- `chat_chunk`
- `critic_note`
- `error`

### `GET /api/runs/{run_id}`

Returns recovery payload with:

- run metadata
- latest recovered state
- full event list
- replay metadata (`replay_from_seq`, `replayed_events`)

### `POST /api/knowledge/ingest`

Ingest a knowledge document into RAG:

```json
{
  "user_id": "user_1",
  "project_id": "project_alpha",
  "doc_type": "script",
  "title": "Pilot",
  "path_l1": "season1",
  "path_l2": "ep1",
  "content": "INT. ROOM - DAY\nHe sits."
}
```

Returns `doc_id`, `chunk_count`, `source_path`.

## Hot Topic Writing

When user input contains hot/latest intent (e.g. `最新`, `热点`, `today`, `latest`, `news`), writer automatically fetches internet context via internal tools before drafting.

## Operations

### Rebuild Knowledge Index

Use this when chunking strategy or embedding config changes:

```bash
uv run python scripts/rebuild_knowledge_index.py \
  --user-id user_1 \
  --project-id project_alpha
```

## Project Layout

```text
src/scriptwriter/
  agents/
    lead_agent/       # planner/writer/critic/orchestrator
    memory/           # Milvus retrieval wrapper
    thread_state.py   # in-memory state schema
  gateway/
    app.py            # FastAPI app
    routers/chat.py   # chat + run recovery APIs
  state_store/        # store abstraction + in-memory + postgres
  tools/builtins/     # tool layer (e.g. search_story_bible)
  config/             # runtime extension config (MCP)
```

## Development Notes

- Keep `RAG` and `Memory` boundaries strict.
- Persist events/snapshots as JSON-serializable payloads.
- Avoid import-time side effects for external systems.
- Prefer tests before behavior changes.

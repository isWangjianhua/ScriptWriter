# ScriptWriter

Thread-scoped multi-agent screenplay backend built on FastAPI.

中文说明请看 [README_ZH.md](README_ZH.md).

## What This Project Does

- Runs a `planner -> writer -> critic` orchestration pipeline.
- Persists run lifecycle (`session`, `run`, `events`, `snapshot`) for recovery.
- Supports thread-isolated upload and artifact access with path traversal protection.
- Provides RAG-backed story knowledge ingest/retrieval and optional MCP tools.

## Documentation

- [Docs Home](docs/README.md)
- [English Docs](docs/en/README.md)
- [Architecture Overview](docs/en/architecture.md)
- [API Reference](docs/en/api-reference.md)
- [Operations and Configuration](docs/en/operations.md)
- [Development Guide](docs/en/development.md)
- [Security Model](docs/en/security-model.md)
- [Design/Planning History](docs/plans/)

## Quick Start

### 1. Install

```bash
uv sync
```

### 2. Run API

```bash
PYTHONPATH=src uv run uvicorn scriptwriter.gateway.app:app --reload
```

### 3. Run Quality Checks

```bash
uv run --extra dev ruff check src tests
uv run pytest -q
```

## Main Endpoints

- `POST /api/threads/{thread_id}/chat`
- `GET /api/threads/{thread_id}/runs/{run_id}?user_id=...&project_id=...`
- `POST /api/threads/{thread_id}/knowledge/ingest`
- `POST /api/threads/{thread_id}/knowledge/upload`
- `GET /api/threads/{thread_id}/knowledge/upload/list`
- `DELETE /api/threads/{thread_id}/knowledge/upload/{filename}`
- `GET /api/threads/{thread_id}/artifacts/{path}`

See [API Reference](docs/en/api-reference.md) for request/response details.

## Runtime Notes

- `user_id` and `project_id` are required (no default fallback).
- `thread_id` is validated (`[A-Za-z0-9_-]+`) and used as isolation boundary.
- `data/threads/` is runtime data and is ignored by git.

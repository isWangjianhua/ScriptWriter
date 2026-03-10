# ScriptWriter

Project-centric screenplay backend built on FastAPI.

中文说明请看 [README_ZH.md](README_ZH.md).

## What This Project Does

- Manages a screenplay workflow of `bible -> outline -> draft`.
- Tracks artifact versions and confirmations per project.
- Stores project state in an in-memory repository for local iteration.
- Ingests project-scoped knowledge into SQLite metadata plus Milvus-backed vectors.
- Supports optional MCP tool loading and built-in web / bible tools.

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
PYTHONPATH=src uv run uvicorn scriptwriter.api.app:app --reload
```

### 3. Run Quality Checks

```bash
uv run --extra dev ruff check src tests
uv run pytest -q
```

## Main Endpoints

- `POST /api/projects`
- `GET /api/projects/{project_id}`
- `POST /api/projects/{project_id}/chat`
- `POST /api/projects/{project_id}/confirm`
- `POST /api/projects/{project_id}/knowledge/upload`
- `GET /api/projects/{project_id}/versions`

See [API Reference](docs/en/api-reference.md) for request/response details.

## Runtime Notes

- API responses are JSON only; there is no chat streaming or run recovery API in the current implementation.
- Project records, versions, and confirmations live in process memory and reset when the service restarts.
- Knowledge documents persist under `data/rag/` by default, with vectors stored in the Milvus local database path.
- `POST /api/projects/{project_id}/chat` can create a missing project if `title` is provided in the request body.

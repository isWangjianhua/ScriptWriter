# ScriptWriter Agent Guide

## Purpose

ScriptWriter is a thread-scoped multi-agent backend for screenplay generation.

Core separation:

- `RAG`: document ingest and retrieval for knowledge context.
- `Memory/State`: run/session/events/snapshot lifecycle.

## Runtime Architecture

- API gateway: `src/scriptwriter/gateway/`
- Lead orchestration: `src/scriptwriter/agents/lead_agent/`
- Middlewares: `src/scriptwriter/agents/middlewares/`
- State store: `src/scriptwriter/state_store/`
- Knowledge layer: `src/scriptwriter/rag/`

Flow order:

1. planner
2. writer
3. critic
4. revision loop or completion

## Public API Surface

- `POST /api/threads/{thread_id}/chat`
- `GET /api/threads/{thread_id}/runs/{run_id}`
- `POST /api/threads/{thread_id}/knowledge/ingest`
- `POST /api/threads/{thread_id}/knowledge/upload`
- `GET /api/threads/{thread_id}/knowledge/upload/list`
- `DELETE /api/threads/{thread_id}/knowledge/upload/{filename}`
- `GET /api/threads/{thread_id}/artifacts/{path}`

`user_id` and `project_id` are required in scoped flows.

## State Store

Backend selection:

- `SCRIPTWRITER_DATABASE_URL` present and valid -> PostgreSQL
- otherwise -> in-memory fallback

PostgreSQL logical tables:

- `agent_sessions`
- `agent_runs`
- `agent_events`
- `agent_snapshots`

## Development Commands

- install: `uv sync`
- lint: `uv run --extra dev ruff check src tests`
- test: `uv run pytest -q`
- run api: `PYTHONPATH=src uv run uvicorn scriptwriter.gateway.app:app --reload`
- smoke run: `uv run python scripts/smoke_graph.py`

## Conventions

- Keep thread and tenant boundaries strict.
- Keep RAG and state concerns separate.
- Keep event payloads JSON-serializable.
- Avoid import-time side effects around external systems.
- Update docs when changing API, env vars, or behavior.

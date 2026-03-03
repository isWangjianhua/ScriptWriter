# ScriptWriter Agent Guide

## Purpose
`ScriptWriter` is a multi-agent backend for screenplay generation. The system separates:
- `RAG`: retrieval of external knowledge (story bible, references).
- `Memory`: orchestration run/session state and recovery data.

## Runtime Architecture
- API gateway: `src/scriptwriter/gateway/`
- Lead-agent orchestration: `src/scriptwriter/agents/lead_agent/`
- Tooling and retrieval: `src/scriptwriter/tools/`
- State persistence layer: `src/scriptwriter/state_store/`

Current execution path is orchestrator-first:
1. `planner`
2. `writer`
3. `critic`
4. revision loop / completion

The flow emits persistent events and snapshots, then returns NDJSON from `/api/chat`.

## State Store
State store is selected by environment:
- `SCRIPTWRITER_DATABASE_URL` set: use PostgreSQL state store.
- Otherwise: use in-memory fallback store.

PostgreSQL schema includes:
- `agent_sessions`
- `agent_runs`
- `agent_events`
- `agent_snapshots`

## Development Commands
- Install deps: `pip install -r requirements.txt`
- Run tests: `pytest -q`
- Run API: `PYTHONPATH=src uvicorn scriptwriter.gateway.app:app --reload`
- Smoke graph script: `PYTHONPATH=src python scripts/smoke_graph.py`

## Conventions
- Keep `RAG` and `Memory` boundaries strict:
  - RAG stores retrievable knowledge chunks.
  - Memory stores run/session/event/snapshot state.
- Add tests before behavior changes.
- Keep event payloads JSON-serializable.
- Avoid import-time side effects for external systems.

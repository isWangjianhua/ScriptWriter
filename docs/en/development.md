# Development Guide

## Working Principles

- Keep thread-scoped boundaries intact (`thread_id`, `user_id`, `project_id`).
- Keep RAG and run-state responsibilities separated.
- Prefer adding tests for behavior changes before refactor rollout.
- Keep event payloads and snapshots JSON-serializable.

## Local Workflow

1. Install dependencies:

```bash
uv sync
```

2. Run tests:

```bash
uv run pytest -q
```

3. Run lint:

```bash
uv run --extra dev ruff check src tests
```

4. Run API for manual checks:

```bash
PYTHONPATH=src uv run uvicorn scriptwriter.gateway.app:app --reload
```

## Test Layout

- `tests/scriptwriter/gateway/routers/`: API contract and security behavior
- `tests/scriptwriter/agents/`: orchestrator and state behavior
- `tests/scriptwriter/state_store/`: store protocol behavior
- `tests/scriptwriter/rag/`: chunking/metadata/retrieval
- `tests/scriptwriter/tools/builtins/`: tool-level contracts

## Common Change Patterns

### Add API Endpoint

1. Add router in `src/scriptwriter/gateway/routers/`
2. Register router in `gateway/app.py`
3. Add tests under `tests/scriptwriter/gateway/routers/`
4. Update `docs/en/api-reference.md` and `docs/zh/api-reference.md`

### Change Agent State

1. Update `agents/thread_state.py`
2. Update orchestrator merge/recovery logic
3. Update serialization if needed
4. Update state-related tests

### Change State Store

1. Update `state_store/base.py` protocol first
2. Implement both `in_memory.py` and `postgres.py`
3. Add/adjust tests for protocol parity

## Documentation Rule

If behavior, endpoint, or env var changes, update:

- `README.md` (entry-level)
- at least one detailed doc in `docs/` (source-of-truth)

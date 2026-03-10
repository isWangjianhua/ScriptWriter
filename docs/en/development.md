# Development Guide

## Working Principles

- Keep project workflow logic and knowledge ingest logic separate.
- Preserve the `bible -> outline -> draft` transition model unless intentionally changing product behavior.
- Prefer tests before refactors or behavior changes.
- Keep API contracts aligned with `src/scriptwriter/api/routers/projects.py`.

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
PYTHONPATH=src uv run uvicorn scriptwriter.api.app:app --reload
```

## Test Layout

- `tests/scriptwriter/api/`: API contract behavior
- `tests/scriptwriter/projects/`: project service and repository behavior
- `tests/scriptwriter/workflow/`: workflow state transitions
- `tests/scriptwriter/knowledge/`: ingest and retrieval behavior
- `tests/scriptwriter/tools/builtins/`: tool-level behavior
- `tests/scriptwriter/memory/`: memory snapshot behavior

## Common Change Patterns

### Add or Change an API Endpoint

1. Update `src/scriptwriter/api/routers/projects.py`, or add a new router under `src/scriptwriter/api/routers/`.
2. Register new routers in `src/scriptwriter/api/app.py` if needed.
3. Add or update tests under `tests/scriptwriter/api/`.
4. Update both `docs/en/api-reference.md` and `docs/zh/api-reference.md`.

### Change Workflow Logic

1. Update state transitions in `src/scriptwriter/projects/workflow.py`.
2. Update orchestration rules in `src/scriptwriter/projects/service.py` and `src/scriptwriter/agent/service.py`.
3. Add or adjust tests under `tests/scriptwriter/projects/` and `tests/scriptwriter/workflow/`.
4. Update README and architecture docs if the user-visible flow changes.

### Change Knowledge Behavior

1. Update `src/scriptwriter/knowledge/service.py`.
2. Update supporting modules such as `metadata_store_pg.py`, `keyword_store.py`, `milvus_store.py`, or `embeddings.py`.
3. Add or adjust tests under `tests/scriptwriter/knowledge/`.
4. Update operations and security docs if env vars, storage paths, or scope semantics change.

## Documentation Rule

If behavior, endpoints, or env vars change, update:

- `README.md`
- `README_ZH.md`
- at least one detailed doc under `docs/en/`
- the matching doc under `docs/zh/`

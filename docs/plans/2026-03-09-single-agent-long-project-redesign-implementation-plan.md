# Single-Agent Long-Project Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current fixed multi-node screenplay flow with a project-centric single-agent architecture that supports long-lived story memory, Milvus-backed retrieval, and the simplified `planning -> awaiting_confirmation -> drafting/completed` workflow.

**Architecture:** Build a parallel set of project-oriented modules for API, workflow, memory, knowledge, and storage. Keep the first pass intentionally simple: one agent runtime, one project chat endpoint, PostgreSQL for source-of-truth state, and Milvus for retrieval over story materials and historical versions.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, LangGraph, PostgreSQL, Milvus, pytest/httpx.

---

### Task 1: Define the new shared project and workflow models

**Files:**
- Create: `src/scriptwriter/shared/models.py`
- Create: `src/scriptwriter/workflow/models.py`
- Test: `tests/scriptwriter/workflow/test_models.py`

**Step 1: Write the failing test**
- Add tests for the simplified workflow enums and core project payload models.
- Cover `planning`, `awaiting_confirmation`, `drafting`, `completed`, and `rewriting`.
- Cover `current_artifact_type` values `bible`, `outline`, and `draft`.

**Step 2: Run test to verify it fails**
- Run: `uv run pytest tests/scriptwriter/workflow/test_models.py -q`
- Expected: FAIL because the new modules do not exist yet.

**Step 3: Write minimal implementation**
- Add shared Pydantic models for project summaries, version summaries, and confirmation payloads.
- Add workflow models for stage tracking and transition requests.

**Step 4: Run test to verify it passes**
- Run: `uv run pytest tests/scriptwriter/workflow/test_models.py -q`
- Expected: PASS.

**Step 5: Commit**
- `git add src/scriptwriter/shared/models.py src/scriptwriter/workflow/models.py tests/scriptwriter/workflow/test_models.py`
- `git commit -m "feat(workflow): add project and workflow models"`

### Task 2: Build the simplified workflow engine

**Files:**
- Create: `src/scriptwriter/workflow/service.py`
- Test: `tests/scriptwriter/workflow/test_service.py`

**Step 1: Write the failing test**
- Add transition tests for:
- new project entering `planning`
- bible approval moving back to `planning` for outline generation
- outline approval moving to `drafting`
- rewrite requests entering `rewriting`
- rewrite completion returning to `drafting` or `completed`

**Step 2: Run test to verify it fails**
- Run: `uv run pytest tests/scriptwriter/workflow/test_service.py -q`
- Expected: FAIL due to missing workflow service.

**Step 3: Write minimal implementation**
- Implement a workflow service that accepts the current state plus a user intent and returns the next stage and artifact target.

**Step 4: Run test to verify it passes**
- Run: `uv run pytest tests/scriptwriter/workflow/test_service.py -q`
- Expected: PASS.

**Step 5: Commit**
- `git add src/scriptwriter/workflow/service.py tests/scriptwriter/workflow/test_service.py`
- `git commit -m "feat(workflow): add simplified project state machine"`

### Task 3: Add project version and confirmation persistence contracts

**Files:**
- Create: `src/scriptwriter/projects/models.py`
- Create: `src/scriptwriter/projects/repository.py`
- Test: `tests/scriptwriter/projects/test_repository_contract.py`

**Step 1: Write the failing test**
- Add repository-contract tests for storing projects, versions, active pointers, and confirmation records.

**Step 2: Run test to verify it fails**
- Run: `uv run pytest tests/scriptwriter/projects/test_repository_contract.py -q`
- Expected: FAIL because the repository layer does not exist.

**Step 3: Write minimal implementation**
- Define Pydantic models for `Project`, `BibleVersion`, `OutlineVersion`, `DraftVersion`, and `ConfirmationRecord`.
- Add a repository protocol describing the required operations.

**Step 4: Run test to verify it passes**
- Run: `uv run pytest tests/scriptwriter/projects/test_repository_contract.py -q`
- Expected: PASS.

**Step 5: Commit**
- `git add src/scriptwriter/projects/models.py src/scriptwriter/projects/repository.py tests/scriptwriter/projects/test_repository_contract.py`
- `git commit -m "feat(projects): define project version repository contracts"`

### Task 4: Implement project storage in PostgreSQL with an in-memory fallback for tests

**Files:**
- Create: `src/scriptwriter/storage/project_store.py`
- Create: `src/scriptwriter/storage/in_memory_project_store.py`
- Test: `tests/scriptwriter/storage/test_project_store.py`

**Step 1: Write the failing test**
- Add tests for creating a project, saving version content, switching active versions, and recording confirmations.

**Step 2: Run test to verify it fails**
- Run: `uv run pytest tests/scriptwriter/storage/test_project_store.py -q`
- Expected: FAIL because the new stores do not exist yet.

**Step 3: Write minimal implementation**
- Implement an in-memory project store first for deterministic tests.
- Add the PostgreSQL-backed store interface or initial implementation behind the same API.

**Step 4: Run test to verify it passes**
- Run: `uv run pytest tests/scriptwriter/storage/test_project_store.py -q`
- Expected: PASS.

**Step 5: Commit**
- `git add src/scriptwriter/storage/project_store.py src/scriptwriter/storage/in_memory_project_store.py tests/scriptwriter/storage/test_project_store.py`
- `git commit -m "feat(storage): add project version stores"`

### Task 5: Build structured memory services and consistency checks

**Files:**
- Create: `src/scriptwriter/memory/models.py`
- Create: `src/scriptwriter/memory/service.py`
- Test: `tests/scriptwriter/memory/test_service.py`

**Step 1: Write the failing test**
- Add tests for extracting facts, storing canon entries, and detecting conflicts against existing memory.

**Step 2: Run test to verify it fails**
- Run: `uv run pytest tests/scriptwriter/memory/test_service.py -q`
- Expected: FAIL because the memory service does not exist.

**Step 3: Write minimal implementation**
- Add structured models for characters, world rules, story facts, and timeline events.
- Implement read, write, and consistency-check functions over the project store.

**Step 4: Run test to verify it passes**
- Run: `uv run pytest tests/scriptwriter/memory/test_service.py -q`
- Expected: PASS.

**Step 5: Commit**
- `git add src/scriptwriter/memory/models.py src/scriptwriter/memory/service.py tests/scriptwriter/memory/test_service.py`
- `git commit -m "feat(memory): add structured canon services"`

### Task 6: Refactor knowledge retrieval around project-scoped Milvus search

**Files:**
- Create: `src/scriptwriter/knowledge/models.py`
- Create: `src/scriptwriter/knowledge/service.py`
- Modify: `src/scriptwriter/agents/memory/milvus_store.py`
- Test: `tests/scriptwriter/knowledge/test_service.py`

**Step 1: Write the failing test**
- Add tests for ingesting project documents, chunk metadata, and filtered retrieval by `project_id`, `doc_type`, and `version_id`.

**Step 2: Run test to verify it fails**
- Run: `uv run pytest tests/scriptwriter/knowledge/test_service.py -q`
- Expected: FAIL because the new knowledge service layer does not exist.

**Step 3: Write minimal implementation**
- Wrap the current Milvus adapter with a project-scoped knowledge service.
- Standardize metadata fields for story materials and historical versions.

**Step 4: Run test to verify it passes**
- Run: `uv run pytest tests/scriptwriter/knowledge/test_service.py -q`
- Expected: PASS.

**Step 5: Commit**
- `git add src/scriptwriter/knowledge/models.py src/scriptwriter/knowledge/service.py src/scriptwriter/agents/memory/milvus_store.py tests/scriptwriter/knowledge/test_service.py`
- `git commit -m "feat(knowledge): add project-scoped retrieval service"`

### Task 7: Create the single-agent runtime and intent router

**Files:**
- Create: `src/scriptwriter/agent/models.py`
- Create: `src/scriptwriter/agent/service.py`
- Create: `src/scriptwriter/agent/prompts.py`
- Test: `tests/scriptwriter/agent/test_service.py`

**Step 1: Write the failing test**
- Add tests for intent classification and action routing:
- generate bible
- generate outline
- confirm artifact
- continue draft
- rewrite scene

**Step 2: Run test to verify it fails**
- Run: `uv run pytest tests/scriptwriter/agent/test_service.py -q`
- Expected: FAIL because the new agent runtime does not exist.

**Step 3: Write minimal implementation**
- Implement a service that accepts project state plus user input and returns an agent action request.
- Add prompt builders for bible, outline, draft, and rewrite generation.

**Step 4: Run test to verify it passes**
- Run: `uv run pytest tests/scriptwriter/agent/test_service.py -q`
- Expected: PASS.

**Step 5: Commit**
- `git add src/scriptwriter/agent/models.py src/scriptwriter/agent/service.py src/scriptwriter/agent/prompts.py tests/scriptwriter/agent/test_service.py`
- `git commit -m "feat(agent): add single-agent runtime and intent routing"`

### Task 8: Wire project orchestration across workflow, memory, and knowledge

**Files:**
- Create: `src/scriptwriter/projects/service.py`
- Test: `tests/scriptwriter/projects/test_service.py`

**Step 1: Write the failing test**
- Add service tests for:
- creating a project from chat
- generating a bible and moving to `awaiting_confirmation`
- confirming a bible and generating an outline
- confirming an outline and entering `drafting`
- rewrite flows generating a new draft version

**Step 2: Run test to verify it fails**
- Run: `uv run pytest tests/scriptwriter/projects/test_service.py -q`
- Expected: FAIL because the orchestration service does not exist.

**Step 3: Write minimal implementation**
- Implement a project service that coordinates the workflow engine, project store, memory service, knowledge service, and single-agent runtime.

**Step 4: Run test to verify it passes**
- Run: `uv run pytest tests/scriptwriter/projects/test_service.py -q`
- Expected: PASS.

**Step 5: Commit**
- `git add src/scriptwriter/projects/service.py tests/scriptwriter/projects/test_service.py`
- `git commit -m "feat(projects): add single-agent project orchestration"`

### Task 9: Add project-centric FastAPI endpoints

**Files:**
- Create: `src/scriptwriter/api/app.py`
- Create: `src/scriptwriter/api/routers/projects.py`
- Test: `tests/scriptwriter/api/test_projects.py`

**Step 1: Write the failing test**
- Add API tests for:
- `POST /api/projects`
- `GET /api/projects/{project_id}`
- `POST /api/projects/{project_id}/chat`
- `POST /api/projects/{project_id}/confirm`
- `GET /api/projects/{project_id}/versions`

**Step 2: Run test to verify it fails**
- Run: `uv run pytest tests/scriptwriter/api/test_projects.py -q`
- Expected: FAIL because the new API does not exist.

**Step 3: Write minimal implementation**
- Add project-centric routes and route them to the new project service.
- Keep streaming output compatible with the current frontend expectation where practical.

**Step 4: Run test to verify it passes**
- Run: `uv run pytest tests/scriptwriter/api/test_projects.py -q`
- Expected: PASS.

**Step 5: Commit**
- `git add src/scriptwriter/api/app.py src/scriptwriter/api/routers/projects.py tests/scriptwriter/api/test_projects.py`
- `git commit -m "feat(api): add project-centric single-agent endpoints"`

### Task 10: Add knowledge upload support for project materials

**Files:**
- Modify: `src/scriptwriter/api/routers/projects.py`
- Test: `tests/scriptwriter/api/test_projects.py`

**Step 1: Write the failing test**
- Add tests for uploading a reference document and making it retrievable for the project.

**Step 2: Run test to verify it fails**
- Run: `uv run pytest tests/scriptwriter/api/test_projects.py -q`
- Expected: FAIL due to missing upload route or ingest path.

**Step 3: Write minimal implementation**
- Add `POST /api/projects/{project_id}/knowledge/upload` and route it to the knowledge service.

**Step 4: Run test to verify it passes**
- Run: `uv run pytest tests/scriptwriter/api/test_projects.py -q`
- Expected: PASS.

**Step 5: Commit**
- `git add src/scriptwriter/api/routers/projects.py tests/scriptwriter/api/test_projects.py`
- `git commit -m "feat(api): add project knowledge upload route"`

### Task 11: Add backward-compatibility strategy or explicit deprecation guard

**Files:**
- Modify: `src/scriptwriter/main.py`
- Modify: `README.md`
- Modify: `README_ZH.md`
- Test: `tests/scriptwriter/test_bootstrap.py`

**Step 1: Write the failing test**
- Add a bootstrap test that verifies the app starts with the new API entrypoint or returns a clear deprecation path.

**Step 2: Run test to verify it fails**
- Run: `uv run pytest tests/scriptwriter/test_bootstrap.py -q`
- Expected: FAIL because the startup contract has changed.

**Step 3: Write minimal implementation**
- Point the app bootstrap to the new API module or provide a clear compatibility shim.
- Update both READMEs to document the new project-centric flow.

**Step 4: Run test to verify it passes**
- Run: `uv run pytest tests/scriptwriter/test_bootstrap.py -q`
- Expected: PASS.

**Step 5: Commit**
- `git add src/scriptwriter/main.py README.md README_ZH.md tests/scriptwriter/test_bootstrap.py`
- `git commit -m "chore: switch bootstrap to project-centric architecture"`

### Task 12: Full verification and cleanup

**Files:**
- Test: existing and newly added tests

**Step 1: Run focused suites**
- Run: `uv run pytest tests/scriptwriter/workflow tests/scriptwriter/projects tests/scriptwriter/memory tests/scriptwriter/knowledge tests/scriptwriter/agent tests/scriptwriter/api -q`
- Expected: PASS for the new architecture slices.

**Step 2: Run full suite**
- Run: `uv run pytest -q`
- Expected: PASS or a short list of explicit compatibility failures to resolve.

**Step 3: Run lint**
- Run: `uv run --extra dev ruff check src tests`
- Expected: PASS.

**Step 4: Record evidence**
- Capture which legacy modules remain and whether the old lead-agent flow can be deleted immediately or should be removed in a follow-up.

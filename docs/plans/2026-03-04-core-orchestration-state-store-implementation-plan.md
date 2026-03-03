# Core Orchestration State Store Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build recoverable multi-agent orchestration with persistent run/session state, event log, and snapshot support.

**Architecture:** Introduce a state-store abstraction with in-memory and PostgreSQL implementations. The lead-agent orchestrator records immutable events and periodic snapshots, and gateway endpoints expose run metadata plus recovery payloads. Runtime keeps RAG and memory responsibilities separated: RAG for external knowledge retrieval, memory for workflow state progression/recovery.

**Tech Stack:** FastAPI, Pydantic, Python typing/dataclasses, PostgreSQL (psycopg), pytest/httpx.

---

### Task 1: Add State Store Abstractions

**Files:**
- Create: `src/scriptwriter/state_store/base.py`
- Create: `src/scriptwriter/state_store/serialization.py`
- Create: `src/scriptwriter/state_store/__init__.py`
- Test: `tests/scriptwriter/state_store/test_in_memory_store.py`

**Step 1: Write failing tests for run/session/event/snapshot contracts**
**Step 2: Run tests to verify failure**
**Step 3: Implement minimal protocol and serializers**
**Step 4: Run tests to verify pass**

### Task 2: Add In-Memory and PostgreSQL Stores

**Files:**
- Create: `src/scriptwriter/state_store/in_memory.py`
- Create: `src/scriptwriter/state_store/postgres.py`
- Create: `src/scriptwriter/state_store/factory.py`
- Modify: `requirements.txt`
- Test: `tests/scriptwriter/state_store/test_in_memory_store.py`

**Step 1: Add failing tests for event sequencing and snapshot loading**
**Step 2: Run tests to verify failure**
**Step 3: Implement in-memory store and PostgreSQL backend skeleton**
**Step 4: Run tests to verify pass**

### Task 3: Persist Orchestration Runtime Events

**Files:**
- Modify: `src/scriptwriter/agents/lead_agent/orchestrator.py`
- Test: `tests/scriptwriter/agents/test_orchestrator.py`

**Step 1: Add failing tests asserting run metadata and persisted event log**
**Step 2: Run tests to verify failure**
**Step 3: Implement persisted flow execution and recovery replay**
**Step 4: Run tests to verify pass**

### Task 4: Add Recovery APIs

**Files:**
- Modify: `src/scriptwriter/gateway/routers/chat.py`
- Modify: `tests/scriptwriter/gateway/routers/test_chat.py`

**Step 1: Add failing tests for `/api/runs/{run_id}` recovery endpoint**
**Step 2: Run tests to verify failure**
**Step 3: Implement response models and endpoint wiring to state store**
**Step 4: Run tests to verify pass**

### Task 5: End-to-End Verification

**Files:**
- Modify: `tests/scriptwriter/test_bootstrap.py` (if needed)

**Step 1: Run targeted tests for new modules**
**Step 2: Run full `pytest` suite**
**Step 3: Ensure no regressions**

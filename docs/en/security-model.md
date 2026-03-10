# Security Model

## Scope

Current security posture is limited and focused on:

- basic request validation through Pydantic models
- project existence checks on workflow and knowledge routes
- project-scoped knowledge filtering by `user_id` and `project_id`
- optional isolation of persisted knowledge files under `data/rag/`

This is not a full authentication or authorization system.

## API Boundary

The current API surface is project-scoped:

- `POST /api/projects`
- `GET /api/projects/{project_id}`
- `POST /api/projects/{project_id}/chat`
- `POST /api/projects/{project_id}/confirm`
- `POST /api/projects/{project_id}/knowledge/upload`
- `GET /api/projects/{project_id}/versions`

There is no thread boundary in the current implementation.

## Validation Boundary

Request bodies use Pydantic validation for:

- non-empty `project_id`, `title`, and `message`
- non-empty `user_id`, `content`, and `doc_type` for knowledge upload

Knowledge ingest further enforces a `doc_type` allowlist:

- `script`
- `novel`
- `text`
- `markdown`

## Knowledge Isolation

Knowledge records are scoped by:

- `user_id`
- `project_id`

These fields are written into SQLite metadata and Milvus filters during ingest and search.

## Data Safety Characteristics

- project workflow state is in-memory only, which reduces long-lived state exposure but is not durable
- persisted knowledge source files are written under the configured RAG data directory
- vector search falls back gracefully when Milvus is unavailable
- embeddings fall back to deterministic hash vectors when OpenAI embeddings are unavailable

## Known Gaps

- `user_id` and `project_id` are client-supplied; there is no identity binding
- no authn/authz layer
- no rate limiting or quota enforcement
- no audit logging pipeline
- no durable project workflow store

## Recommended Next Hardening Steps

1. Add authenticated identity and derive `user_id` from trusted context.
2. Add rate limiting for chat and knowledge ingest endpoints.
3. Add audit logging for project mutations and knowledge writes.
4. Introduce a durable project store with access-control boundaries.

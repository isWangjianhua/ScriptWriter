# Single-Agent Long-Project Redesign

## Goal
Rebuild ScriptWriter into a single-agent, long-project screenplay system that keeps project memory over time, uses Milvus for text retrieval, and enforces a simpler user flow:

`bible -> outline -> user confirmation -> script`

The system must also support explicit shortcuts such as "rewrite scene 3" or "do not regenerate the bible".

## Product Constraints
- Keep the product promise unchanged: user inputs ideas, hot topics, novels, or other story material and receives screenplay output.
- Favor a simple first version over a fully generalized architecture.
- Support long-lived projects that accumulate facts, versions, and revisions across multiple sessions.
- Default to gated confirmation for new projects or major direction changes.
- Allow explicit user override for local rewrites or targeted edits.

## Core Architecture

### Single Runtime Model
The new backend uses one creative agent instead of fixed `planner -> writer -> critic` nodes.

That agent is responsible for:
- interpreting the user's intent
- deciding the next project step
- collecting memory and knowledge context
- generating bible, outline, or screenplay text
- saving new versions and updating project state

This keeps the product mentally simple: one project, one agent, one conversational entry point.

### Simplified Workflow State
The first version keeps only four durable states plus one temporary rewrite mode:

- `planning`
- `awaiting_confirmation`
- `drafting`
- `completed`
- `rewriting`

Two fields provide the missing detail without expanding the state machine:
- `current_artifact_type`: `bible`, `outline`, or `draft`
- `current_artifact_version_id`

This gives enough control for the core UX:
- New project: `planning -> awaiting_confirmation -> drafting -> completed`
- Bible or outline revisions: return to `planning`
- Local scene rewrite: enter `rewriting`, then return to `drafting` or `completed`

### Project Truth Model
The system separates stable truth from retrievable text.

#### Structured Memory
Stored in PostgreSQL and treated as the final project truth source.

It contains:
- character profiles
- world rules
- locations
- timeline events
- confirmed story facts
- unresolved foreshadowing
- tone and style constraints

Structured memory decides whether a new generation is consistent with the project.

#### Knowledge Retrieval
Stored in Milvus and used for recall, not truth.

It contains chunked text from:
- uploaded novels and reference docs
- existing scripts
- prior bible and outline versions
- historical draft versions
- research notes

Each chunk should include metadata such as:
- `project_id`
- `doc_id`
- `doc_type`
- `version_id`
- `episode_id`
- `scene_id`
- `is_active`

Milvus answers "what text is relevant?" while structured memory answers "what is canon?"

## Module Layout
Use a simple, product-shaped layout instead of abstract DDD layering:

```text
src/scriptwriter/
  api/          # FastAPI routes and streaming responses
  agent/        # single-agent runtime, prompts, tools, intent routing
  workflow/     # simplified project state machine
  memory/       # structured facts and consistency checks
  knowledge/    # chunking, embeddings, Milvus retrieval
  projects/     # project metadata, versions, confirmation records
  storage/      # Postgres, Milvus, artifact storage adapters
  providers/    # LLM and embedding providers
  shared/       # config, logging, common models, errors
```

This structure is intentionally direct:
- `projects` manages project versions and active pointers
- `memory` manages canon facts
- `knowledge` manages retrieval
- `workflow` decides stage transitions
- `agent` ties the experience together

## Persistence Strategy

### PostgreSQL
PostgreSQL is the system of record for:
- project state
- active version pointers
- bible, outline, and draft versions
- confirmation history
- structured memory
- event logs

For the first implementation, long text content can stay in PostgreSQL `TEXT` columns for simplicity.

### Milvus
Milvus is dedicated to semantic retrieval.

Use it for:
- source novels
- uploaded references
- historical drafts
- prior bible and outline text
- script chunks

Milvus should not be responsible for workflow state or final canon.

### Artifact Files
Markdown or other export files are derived artifacts, not the source of truth.

Use them for:
- exports
- downloads
- audit snapshots when useful

## API Shape
Move the public API to project-centric endpoints.

### Core endpoints
- `POST /api/projects`
- `GET /api/projects/{project_id}`
- `POST /api/projects/{project_id}/chat`
- `POST /api/projects/{project_id}/confirm`
- `POST /api/projects/{project_id}/knowledge/upload`
- `GET /api/projects/{project_id}/versions`

### Main interaction contract
`POST /api/projects/{project_id}/chat` is the primary creative entry point.

The agent decides whether the user is:
- starting a new project
- adding or changing story facts
- confirming the current bible or outline
- asking to draft screenplay pages
- requesting a rewrite
- asking to continue an episode

Streaming responses should continue to use NDJSON or SSE-style incremental events.

## User Flow

### New project
1. User provides an idea, novel, or hot topic.
2. Agent creates or updates project context.
3. Agent generates a bible and saves `BibleVersion`.
4. State becomes `awaiting_confirmation` with `current_artifact_type = bible`.
5. After approval, the agent generates an outline and saves `OutlineVersion`.
6. State returns to `awaiting_confirmation` with `current_artifact_type = outline`.
7. After approval, the agent enters `drafting` and generates script pages.

### Local rewrite
1. User requests a specific rewrite.
2. Agent enters `rewriting`.
3. Agent loads active draft context, structured memory, and Milvus recalls.
4. Agent writes a new `DraftVersion`.
5. State returns to `drafting` or `completed`.

### Major direction change
1. User changes protagonist, tone, world rule, or central conflict.
2. Agent detects project-wide impact.
3. Existing outline or draft is marked stale.
4. Workflow returns to `planning`.

## Agent Tooling
The single agent should use a narrow tool surface:

- `load_project_state`
- `load_active_versions`
- `save_bible_version`
- `save_outline_version`
- `save_draft_version`
- `record_confirmation`
- `search_memory`
- `update_memory`
- `search_knowledge`
- `check_consistency`

This keeps the runtime understandable and reduces accidental coupling between modules.

## Testing Strategy

### Unit tests
- workflow state transitions
- confirmation rules
- consistency checks
- version activation logic

### Integration tests
- new project flow through bible and outline confirmation
- direct rewrite flow
- project state recovery
- knowledge upload and retrieval

### End-to-end tests
- idea to bible
- bible to outline
- outline to draft
- rewrite after a confirmed outline

## Migration Direction
Do not retrofit the current `planner/writer/critic` stack in place.

Instead:
1. Create the new modules in parallel.
2. Build the new project API and workflow first.
3. Keep old code untouched until the new flow works end-to-end.
4. Remove or archive the old lead-agent pipeline after verification.

## Out of Scope for First Pass
- multi-agent orchestration
- complex background jobs
- microservice splitting
- advanced critic/reflection loops
- object storage migration
- fine-grained workflow states beyond the simplified state machine

## Summary
This redesign turns ScriptWriter from a one-shot orchestration service into a long-lived creative system with:
- one conversational agent
- one simple workflow state machine
- one structured canon layer
- one Milvus retrieval layer
- one project-centric API surface

That is enough to support the intended product without overbuilding the first rewrite.

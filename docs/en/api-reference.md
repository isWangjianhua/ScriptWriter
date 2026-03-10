# API Reference

Base media type: `application/json`

All endpoints below are current and project-scoped.

## Project Model

Typical project payload:

```json
{
  "project_id": "project_alpha",
  "title": "Pilot",
  "stage": "awaiting_confirmation",
  "current_artifact_type": "bible",
  "current_artifact_version_id": "bible_v1",
  "active_bible_version_id": "bible_v1",
  "active_outline_version_id": null,
  "active_draft_version_id": null
}
```

`stage` values:

- `planning`
- `awaiting_confirmation`
- `drafting`
- `completed`
- `rewriting`

`current_artifact_type` values:

- `bible`
- `outline`
- `draft`

## Projects

### `POST /api/projects`

Request body:

```json
{
  "project_id": "project_alpha",
  "title": "Pilot"
}
```

Behavior:

- creates the project if it does not exist
- returns the existing project unchanged if `project_id` already exists

Response: full project payload.

### `GET /api/projects/{project_id}`

Returns the current project payload.

Errors:

- `404` if the project does not exist

## Chat Workflow

### `POST /api/projects/{project_id}/chat`

Request body:

```json
{
  "message": "Write a crime thriller series",
  "title": "Pilot"
}
```

Behavior:

- if the project does not exist, `title` is required and the API creates the project first
- the service classifies the message into one of: generate bible, confirm artifact, generate outline, continue draft, rewrite draft
- responses are synchronous JSON; there is no streaming response format

Common transitions:

- first chat on a new project -> generates `bible_v1`
- approval while waiting for bible confirmation -> generates `outline_v1`
- approval while waiting for outline confirmation -> generates `draft_v1`
- continue drafting -> creates the next draft version
- rewrite request -> creates a new draft version from rewrite prompt

Errors:

- `400` if the project is missing and `title` is omitted
- `404` if the project is missing for a path that requires an existing project

Response: full project payload.

## Confirmation

### `POST /api/projects/{project_id}/confirm`

Request body:

```json
{
  "comment": "continue"
}
```

Behavior:

- confirms the current pending artifact
- advances the workflow to the next artifact when applicable

Errors:

- `404` if the project does not exist
- `400` if no artifact is awaiting confirmation

Response: full project payload.

## Knowledge Upload

### `POST /api/projects/{project_id}/knowledge/upload`

Request body:

```json
{
  "user_id": "user_1",
  "content": "Reference notes for the project",
  "doc_type": "text",
  "title": "Story Guide",
  "path_l1": "season1",
  "path_l2": "episode1",
  "source_type": "reference",
  "version_id": "outline_v1",
  "episode_id": "ep1",
  "scene_id": "scene_2",
  "is_active": true
}
```

`doc_type` allowed values:

- `script`
- `novel`
- `text`
- `markdown`

Response:

```json
{
  "doc_id": "xxx",
  "chunk_count": 3,
  "source_path": "data/rag/sources/xxx.txt"
}
```

Behavior:

- requires the project to exist
- segments and chunks `content`
- stores metadata in SQLite under `data/rag/` by default
- stores vectors in Milvus if available

Errors:

- `404` if the project does not exist
- `400` if content is empty or `doc_type` is invalid

## Versions

### `GET /api/projects/{project_id}/versions`

Response:

```json
{
  "bible": [
    {
      "version_id": "bible_v1",
      "project_id": "project_alpha",
      "version_number": 1,
      "content": "...",
      "artifact_type": "bible",
      "status": "active"
    }
  ],
  "outline": [],
  "draft": []
}
```

Errors:

- `404` if the project does not exist

## Non-Goals of the Current API

- no thread-scoped endpoints
- no run recovery endpoints
- no file upload / artifact serving routes
- no chat streaming transport

# API Reference

Base media types:

- JSON: `application/json`
- Chat stream: `application/x-ndjson`

All endpoints below are current and thread-scoped.

## Chat

### `POST /api/threads/{thread_id}/chat`

Request body:

```json
{
  "message": "Write a suspense opening scene",
  "user_id": "user_1",
  "project_id": "project_alpha",
  "resume_run_id": "optional_previous_run_id"
}
```

Behavior:

- validates `thread_id`
- validates `user_id` + `project_id`
- optional scoped resume from `resume_run_id`
- executes orchestrator and streams NDJSON events

NDJSON event types:

- `run_started`
- `canvas_update`
- `chat_chunk`
- `critic_note`
- `error`

## Run Recovery

### `GET /api/threads/{thread_id}/runs/{run_id}?user_id=...&project_id=...`

Returns:

- run metadata (`run_id`, `session_id`, `thread_id`, `status`)
- recovered `state`
- complete `events`
- replay metadata (`replay_from_seq`, `replayed_events`)

Security semantics:

- `404` if run does not exist
- `403` if run exists but tenant/thread scope mismatches

## Knowledge Ingest

### `POST /api/threads/{thread_id}/knowledge/ingest`

Request body:

```json
{
  "user_id": "user_1",
  "project_id": "project_alpha",
  "doc_type": "script",
  "title": "Pilot",
  "path_l1": "season1",
  "path_l2": "ep1",
  "content": "INT. ROOM - DAY\nHe sits.",
  "doc_id": "optional_doc_id"
}
```

Response:

```json
{
  "doc_id": "xxx",
  "chunk_count": 12,
  "source_path": "..."
}
```

`doc_type` allowed values: `script`, `novel`, `text`, `markdown`.

## Knowledge Upload

### `POST /api/threads/{thread_id}/knowledge/upload`

Multipart form fields:

- required: `file`, `user_id`, `project_id`
- optional: `title`, `path_l1`, `path_l2`, `doc_type`

Response:

```json
{
  "doc_id": "xxx",
  "chunk_count": 3,
  "filename": "my_novel.txt",
  "title": "my_novel",
  "doc_type": "markdown",
  "virtual_path": "/mnt/user-data/uploads/my_novel.txt",
  "artifact_url": "/api/threads/thread_alpha/artifacts/mnt/user-data/uploads/my_novel.txt"
}
```

Limits and errors:

- size cap from `SCRIPTWRITER_MAX_UPLOAD_BYTES`
- `413` if exceeded
- traversal and unsafe paths blocked

### `GET /api/threads/{thread_id}/knowledge/upload/list`

Response:

```json
{
  "files": [
    {
      "filename": "my_novel.txt",
      "size": 1234,
      "virtual_path": "/mnt/user-data/uploads/my_novel.txt",
      "artifact_url": "/api/threads/thread_alpha/artifacts/mnt/user-data/uploads/my_novel.txt",
      "modified": 1741161000.0
    }
  ],
  "count": 1
}
```

### `DELETE /api/threads/{thread_id}/knowledge/upload/{filename}`

Deletes one uploaded file from the thread upload directory.

## Artifacts

### `GET /api/threads/{thread_id}/artifacts/{path}`

Reads files through virtual path mapping.

- `path` must start with `mnt/user-data/...`
- supports inline text/html rendering
- supports `?download=true` for attachment response

Typical path examples:

- `mnt/user-data/uploads/my_novel.txt`
- `mnt/user-data/outputs/final_draft.md`

## Breaking Changes from Legacy API

- removed `POST /api/chat`
- removed `GET /api/runs/{run_id}`
- removed non-thread-scoped knowledge endpoints
- removed `default_user/default_project` fallback behavior

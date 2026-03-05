# Security Model

## Scope

Current security posture is focused on:

- thread isolation
- tenant ownership checks
- path traversal protection
- upload size/type controls

This is not a full authentication/authorization system yet.

## Isolation Boundaries

### Thread Boundary

- Each request is thread-scoped: `/api/threads/{thread_id}/...`
- `thread_id` must match `^[A-Za-z0-9_-]+$`
- Thread directories are resolved under `SCRIPTWRITER_THREADS_DIR`

### Tenant Boundary

Run recovery is scoped by:

- `thread_id`
- `user_id`
- `project_id`

`get_run_scoped(...)` enforces the tuple and prevents raw `run_id` access.

## Path Safety

- Upload delete/list/read routes reject traversal attempts.
- Virtual path resolver only accepts paths under `/mnt/user-data/{uploads|outputs|workspace}`.
- Resolved filesystem paths must stay under allowed base directories.

## Upload Hardening

- File upload reads in chunks.
- Max size is enforced by `SCRIPTWRITER_MAX_UPLOAD_BYTES`.
- Unsupported extensions are rejected.
- Unsafe filenames are normalized.

## Prompt/Tool Safety

- Middleware marks external web context as untrusted data.
- Tool-call integrity middleware patches dangling tool call message chains.

## Known Gaps

- `user_id` and `project_id` are still client-supplied (no JWT/session binding yet).
- No rate limiting or quota enforcement at gateway level.
- No centralized audit log pipeline.

## Recommended Next Hardening Steps

1. Add auth layer and derive user/project scope from verified identity.
2. Add request-level rate limiting.
3. Add structured audit logging for sensitive operations.
4. Add metrics and alerts for repeated forbidden/traversal attempts.

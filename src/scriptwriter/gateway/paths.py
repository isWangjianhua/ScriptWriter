from __future__ import annotations

import os
import re
from pathlib import Path

_SAFE_THREAD_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
VIRTUAL_PATH_PREFIX = "/mnt/user-data"
_ALLOWED_VIRTUAL_ROOTS = {"uploads", "outputs", "workspace"}


def safe_thread_id(thread_id: str) -> str:
    candidate = thread_id.strip()
    if not candidate:
        raise ValueError("thread_id must not be empty")
    if not _SAFE_THREAD_ID_RE.fullmatch(candidate):
        raise ValueError(
            "thread_id is invalid; only letters, numbers, underscores, and hyphens are allowed"
        )
    return candidate


def _threads_root() -> Path:
    root = os.getenv("SCRIPTWRITER_THREADS_DIR", "").strip()
    if root:
        return Path(root)
    return Path("data") / "threads"


def thread_dir(thread_id: str) -> Path:
    return _threads_root() / safe_thread_id(thread_id)


def workspace_dir(thread_id: str) -> Path:
    base = thread_dir(thread_id) / "workspace"
    base.mkdir(parents=True, exist_ok=True)
    return base


def uploads_dir(thread_id: str) -> Path:
    base = thread_dir(thread_id) / "uploads"
    base.mkdir(parents=True, exist_ok=True)
    return base


def outputs_dir(thread_id: str) -> Path:
    base = thread_dir(thread_id) / "outputs"
    base.mkdir(parents=True, exist_ok=True)
    return base


def resolve_upload_path(thread_id: str, filename: str) -> Path:
    base = uploads_dir(thread_id).resolve()
    candidate = (base / filename).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ValueError("Access denied: path traversal detected") from exc
    return candidate


def resolve_thread_virtual_path(thread_id: str, virtual_path: str) -> Path:
    """Resolve a virtual sandbox path into a thread-scoped host filesystem path."""
    safe_id = safe_thread_id(thread_id)
    stripped = virtual_path.lstrip("/")
    prefix = VIRTUAL_PATH_PREFIX.lstrip("/")

    if stripped != prefix and not stripped.startswith(prefix + "/"):
        raise ValueError(f"Path must start with {VIRTUAL_PATH_PREFIX}")

    relative = stripped[len(prefix) :].lstrip("/")
    root_segment, _, tail = relative.partition("/")
    if root_segment not in _ALLOWED_VIRTUAL_ROOTS:
        raise ValueError(f"Unsupported virtual root '{root_segment}'")

    if root_segment == "uploads":
        base = uploads_dir(safe_id).resolve()
    elif root_segment == "outputs":
        base = outputs_dir(safe_id).resolve()
    else:
        base = workspace_dir(safe_id).resolve()

    candidate = (base / tail).resolve() if tail else base
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ValueError("Access denied: path traversal detected") from exc

    return candidate

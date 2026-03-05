"""Upload router for ingesting files into the thread-scoped RAG knowledge base."""

from __future__ import annotations

import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from scriptwriter.gateway.paths import VIRTUAL_PATH_PREFIX, resolve_upload_path, safe_thread_id, uploads_dir
from scriptwriter.rag.service import IngestResult, ingest_knowledge_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/threads/{thread_id}/knowledge", tags=["knowledge"])

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".txt",
        ".md",
        ".pdf",
        ".doc",
        ".docx",
        ".epub",
        ".ppt",
        ".pptx",
        ".xls",
        ".xlsx",
    }
)

_DEFAULT_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


class UploadIngestResponse(BaseModel):
    doc_id: str
    chunk_count: int
    filename: str
    title: str
    doc_type: str
    virtual_path: str
    artifact_url: str


def _validated_thread_id(thread_id: str) -> str:
    try:
        return safe_thread_id(thread_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _safe_filename(raw: str) -> str:
    name = Path(raw).name
    name = re.sub(r"[^\w.\-]", "_", name)
    return name or "upload"


def _infer_doc_type(filename: str) -> str:
    _ = filename
    return "markdown"


def _max_upload_bytes() -> int:
    raw = os.getenv("SCRIPTWRITER_MAX_UPLOAD_BYTES", "").strip()
    if not raw:
        return _DEFAULT_MAX_UPLOAD_BYTES
    try:
        limit = int(raw)
    except ValueError:
        return _DEFAULT_MAX_UPLOAD_BYTES
    if limit <= 0:
        return _DEFAULT_MAX_UPLOAD_BYTES
    return limit


async def _read_limited(file: UploadFile, *, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        piece = await file.read(1024 * 1024)
        if not piece:
            break
        total += len(piece)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Uploaded file exceeds max allowed size ({max_bytes} bytes).",
            )
        chunks.append(piece)
    return b"".join(chunks)


async def _extract_text(file_bytes: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    try:
        from markitdown import MarkItDown  # type: ignore[import-untyped]
    except ImportError as exc:
        raise HTTPException(
            status_code=501,
            detail="markitdown is not installed. Run: pip install markitdown[all]",
        ) from exc

    suffix = ext if ext else ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)

    try:
        md = MarkItDown()
        result = md.convert(str(tmp_path))
        text = result.text_content or ""
    except Exception as exc:
        logger.exception("markitdown conversion failed for %s", filename)
        raise HTTPException(
            status_code=422,
            detail=f"Failed to convert '{filename}': {exc}",
        ) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    return text


@router.post("/upload", response_model=UploadIngestResponse, status_code=201)
async def upload_and_ingest(
    thread_id: str,
    file: Annotated[UploadFile, File(...)],
    user_id: Annotated[str, Form(...)],
    project_id: Annotated[str, Form(...)],
    title: str | None = Form(default=None),
    path_l1: str | None = Form(default=None),
    path_l2: str | None = Form(default=None),
    doc_type: str | None = Form(default=None),
) -> UploadIngestResponse:
    safe_id = _validated_thread_id(thread_id)
    user_id = user_id.strip()
    project_id = project_id.strip()
    if not user_id or not project_id:
        raise HTTPException(status_code=422, detail="user_id and project_id are required")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    safe_name = _safe_filename(file.filename)
    ext = Path(safe_name).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type '{ext}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            ),
        )

    raw_bytes = await _read_limited(file, max_bytes=_max_upload_bytes())
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    upload_path = resolve_upload_path(safe_id, safe_name)
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(raw_bytes)

    text_content = await _extract_text(raw_bytes, safe_name)
    if not text_content.strip():
        raise HTTPException(
            status_code=422,
            detail="Could not extract any text from the uploaded file.",
        )

    resolved_title = title or Path(safe_name).stem
    resolved_doc_type = doc_type or _infer_doc_type(safe_name)

    try:
        result: IngestResult = ingest_knowledge_document(
            user_id=user_id,
            project_id=project_id,
            content=text_content,
            doc_type=resolved_doc_type,
            title=resolved_title,
            path_l1=path_l1,
            path_l2=path_l2,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info(
        "Thread=%s ingested file=%s doc_id=%s chunks=%d",
        safe_id,
        safe_name,
        result.doc_id,
        result.chunk_count,
    )

    return UploadIngestResponse(
        doc_id=result.doc_id,
        chunk_count=result.chunk_count,
        filename=safe_name,
        title=resolved_title,
        doc_type=resolved_doc_type,
        virtual_path=f"{VIRTUAL_PATH_PREFIX}/uploads/{safe_name}",
        artifact_url=f"/api/threads/{safe_id}/artifacts/mnt/user-data/uploads/{safe_name}",
    )


@router.get("/upload/list")
async def list_uploads(thread_id: str) -> dict[str, object]:
    safe_id = _validated_thread_id(thread_id)
    base = uploads_dir(safe_id)
    files = []
    for file_path in sorted(base.iterdir()):
        if file_path.is_file():
            stat = file_path.stat()
            files.append(
                {
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "virtual_path": f"{VIRTUAL_PATH_PREFIX}/uploads/{file_path.name}",
                    "artifact_url": f"/api/threads/{safe_id}/artifacts/mnt/user-data/uploads/{file_path.name}",
                    "modified": stat.st_mtime,
                }
            )
    return {"files": files, "count": len(files)}


@router.delete("/upload/{filename:path}")
async def delete_upload(thread_id: str, filename: str) -> dict[str, object]:
    safe_id = _validated_thread_id(thread_id)
    if filename != Path(filename).name:
        raise HTTPException(status_code=403, detail="Access denied: path traversal detected")

    try:
        target = resolve_upload_path(safe_id, filename)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    if not target.exists():
        raise HTTPException(status_code=404, detail="file not found")
    if not target.is_file():
        raise HTTPException(status_code=400, detail="path is not a file")

    target.unlink()
    return {"success": True, "message": f"Deleted {filename}"}

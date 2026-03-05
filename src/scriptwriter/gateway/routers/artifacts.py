from __future__ import annotations

import mimetypes
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response

from scriptwriter.gateway.paths import resolve_thread_virtual_path, safe_thread_id

router = APIRouter(prefix="/api/threads/{thread_id}/artifacts", tags=["artifacts"])


def _validated_thread_id(thread_id: str) -> str:
    try:
        return safe_thread_id(thread_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{path:path}")
async def get_artifact(thread_id: str, path: str, download: bool = Query(default=False)) -> Response:
    safe_id = _validated_thread_id(thread_id)
    try:
        file_path = resolve_thread_virtual_path(safe_id, path)
    except ValueError as exc:
        message = str(exc)
        if "traversal" in message.lower():
            raise HTTPException(status_code=403, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="artifact not found")
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="path is not a file")

    mime_type, _ = mimetypes.guess_type(str(file_path))
    encoded_name = quote(file_path.name)

    if download:
        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type=mime_type,
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
        )

    if mime_type == "text/html":
        return HTMLResponse(content=file_path.read_text(encoding="utf-8"))
    if mime_type and mime_type.startswith("text/"):
        return PlainTextResponse(content=file_path.read_text(encoding="utf-8"), media_type=mime_type)
    return Response(
        content=file_path.read_bytes(),
        media_type=mime_type or "application/octet-stream",
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{encoded_name}"},
    )

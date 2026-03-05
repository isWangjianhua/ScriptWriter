from __future__ import annotations

import httpx
import pytest

from scriptwriter.gateway.app import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_get_artifact_text_file(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIPTWRITER_THREADS_DIR", str(tmp_path))
    thread_uploads = tmp_path / "thread_alpha" / "uploads"
    thread_uploads.mkdir(parents=True, exist_ok=True)
    (thread_uploads / "my_novel.txt").write_text("Once upon a time", encoding="utf-8")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/threads/thread_alpha/artifacts/mnt/user-data/uploads/my_novel.txt"
        )

    assert response.status_code == 200
    assert response.text == "Once upon a time"
    assert response.headers["content-type"].startswith("text/plain")


@pytest.mark.anyio
async def test_get_artifact_rejects_non_virtual_prefix(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIPTWRITER_THREADS_DIR", str(tmp_path))

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/threads/thread_alpha/artifacts/uploads/my_novel.txt")

    assert response.status_code == 400


@pytest.mark.anyio
async def test_get_artifact_rejects_traversal(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIPTWRITER_THREADS_DIR", str(tmp_path))

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/threads/thread_alpha/artifacts/mnt/user-data/uploads/%2E%2E/%2E%2E/etc/passwd"
        )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_get_artifact_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIPTWRITER_THREADS_DIR", str(tmp_path))

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/threads/thread_alpha/artifacts/mnt/user-data/uploads/missing.txt")

    assert response.status_code == 404

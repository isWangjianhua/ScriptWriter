"""Tests for the file upload / RAG ingest endpoint."""

from __future__ import annotations

import io

import httpx
import pytest

from scriptwriter.gateway.app import app
from scriptwriter.gateway.routers.uploads import SUPPORTED_EXTENSIONS
from scriptwriter.rag import reset_knowledge_services_for_tests


@pytest.fixture
def anyio_backend():
    return "asyncio"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_upload(filename: str, content: str | bytes, content_type: str = "text/plain"):
    """Build a multipart file tuple for httpx."""
    data = content.encode() if isinstance(content, str) else content
    return ("file", (filename, io.BytesIO(data), content_type))


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_upload_txt_file(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIPTWRITER_RAG_DATA_DIR", str(tmp_path))
    reset_knowledge_services_for_tests(data_dir=tmp_path)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/threads/thread_alpha/knowledge/upload",
            files=[_make_upload("three_body.txt", "Chapter 1\nThe Red Shore\n\nIn 1967..." * 30)],
            data={
                "user_id": "user_1",
                "project_id": "proj_1",
                "title": "The Three-Body Problem",
                "path_l1": "sci-fi",
            },
        )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["doc_id"]
    assert payload["chunk_count"] >= 1
    assert payload["filename"] == "three_body.txt"
    assert payload["title"] == "The Three-Body Problem"
    assert payload["doc_type"] == "markdown"
    assert payload["virtual_path"] == "/mnt/user-data/uploads/three_body.txt"
    assert payload["artifact_url"] == "/api/threads/thread_alpha/artifacts/mnt/user-data/uploads/three_body.txt"


@pytest.mark.anyio
async def test_upload_md_file(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIPTWRITER_RAG_DATA_DIR", str(tmp_path))
    reset_knowledge_services_for_tests(data_dir=tmp_path)

    content = "# Character Bible\n\n## Protagonist\n\nA brooding detective in 2077...\n" * 20

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/threads/thread_alpha/knowledge/upload",
            files=[_make_upload("character_bible.md", content, "text/markdown")],
            data={
                "user_id": "user_1",
                "project_id": "proj_1",
            },
        )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["doc_id"]
    assert payload["filename"] == "character_bible.md"
    assert payload["doc_type"] == "markdown"  # always markdown now


@pytest.mark.anyio
async def test_upload_markdown_heading_segmentation(tmp_path, monkeypatch):
    """Verify that Markdown headings produce multiple sections when chunked."""
    monkeypatch.setenv("SCRIPTWRITER_RAG_DATA_DIR", str(tmp_path))
    reset_knowledge_services_for_tests(data_dir=tmp_path)

    # A document with 3 top-level headings → at least 3 chunks
    content = (
        "# Chapter 1: The Red Shore\n\n" + "Red text " * 60 + "\n\n"
        "# Chapter 2: Three Bodies\n\n" + "Star motion " * 60 + "\n\n"
        "# Chapter 3: Sunset for Humanity\n\n" + "Dark forest " * 60 + "\n"
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/threads/thread_alpha/knowledge/upload",
            files=[_make_upload("chapters.md", content, "text/markdown")],
            data={"user_id": "u1", "project_id": "p1"},
        )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["doc_type"] == "markdown"
    assert payload["chunk_count"] >= 3, (
        f"Expected >=3 chunks for 3 headings, got {payload['chunk_count']}"
    )


@pytest.mark.anyio
async def test_upload_uses_filename_as_default_title(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIPTWRITER_RAG_DATA_DIR", str(tmp_path))
    reset_knowledge_services_for_tests(data_dir=tmp_path)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/threads/thread_alpha/knowledge/upload",
            files=[_make_upload("my_novel.txt", "Once upon a time " * 50)],
            data={"user_id": "u1", "project_id": "p1"},
        )

    assert response.status_code == 201, response.text
    assert response.json()["title"] == "my_novel"  # stem of filename


# ---------------------------------------------------------------------------
# Error / edge-case tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_upload_unsupported_extension_returns_415(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIPTWRITER_RAG_DATA_DIR", str(tmp_path))
    reset_knowledge_services_for_tests(data_dir=tmp_path)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/threads/thread_alpha/knowledge/upload",
            files=[_make_upload("image.png", b"\x89PNG\r\n\x1a\n", "image/png")],
            data={"user_id": "u1", "project_id": "p1"},
        )

    assert response.status_code == 415


@pytest.mark.anyio
async def test_upload_empty_file_returns_400(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIPTWRITER_RAG_DATA_DIR", str(tmp_path))
    reset_knowledge_services_for_tests(data_dir=tmp_path)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/threads/thread_alpha/knowledge/upload",
            files=[_make_upload("empty.txt", "")],
            data={"user_id": "u1", "project_id": "p1"},
        )

    assert response.status_code == 400


@pytest.mark.anyio
async def test_upload_requires_user_and_project(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIPTWRITER_RAG_DATA_DIR", str(tmp_path))
    reset_knowledge_services_for_tests(data_dir=tmp_path)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        missing_user = await client.post(
            "/api/threads/thread_alpha/knowledge/upload",
            files=[_make_upload("notes.txt", "hello")],
            data={"project_id": "p1"},
        )
        missing_project = await client.post(
            "/api/threads/thread_alpha/knowledge/upload",
            files=[_make_upload("notes.txt", "hello")],
            data={"user_id": "u1"},
        )

    assert missing_user.status_code == 422
    assert missing_project.status_code == 422


@pytest.mark.anyio
async def test_upload_rejects_oversized_file(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIPTWRITER_RAG_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SCRIPTWRITER_MAX_UPLOAD_BYTES", "16")
    reset_knowledge_services_for_tests(data_dir=tmp_path)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/threads/thread_alpha/knowledge/upload",
            files=[_make_upload("too_big.txt", "x" * 64)],
            data={"user_id": "u1", "project_id": "p1"},
        )

    assert response.status_code == 413


@pytest.mark.anyio
async def test_upload_list_and_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIPTWRITER_RAG_DATA_DIR", str(tmp_path))
    reset_knowledge_services_for_tests(data_dir=tmp_path)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        up = await client.post(
            "/api/threads/thread_alpha/knowledge/upload",
            files=[_make_upload("keep.txt", "hello")],
            data={"user_id": "u1", "project_id": "p1"},
        )
        assert up.status_code == 201, up.text

        listed = await client.get("/api/threads/thread_alpha/knowledge/upload/list")
        assert listed.status_code == 200
        data = listed.json()
        assert data["count"] >= 1
        matched = [item for item in data["files"] if item["filename"] == "keep.txt"]
        assert matched
        assert matched[0]["virtual_path"] == "/mnt/user-data/uploads/keep.txt"
        assert matched[0]["artifact_url"] == "/api/threads/thread_alpha/artifacts/mnt/user-data/uploads/keep.txt"

        deleted = await client.delete("/api/threads/thread_alpha/knowledge/upload/keep.txt")
        assert deleted.status_code == 200

        listed_after = await client.get("/api/threads/thread_alpha/knowledge/upload/list")
        assert listed_after.status_code == 200
        assert all(item["filename"] != "keep.txt" for item in listed_after.json()["files"])


@pytest.mark.anyio
async def test_upload_delete_rejects_traversal(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIPTWRITER_RAG_DATA_DIR", str(tmp_path))
    reset_knowledge_services_for_tests(data_dir=tmp_path)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(
            "/api/threads/thread_alpha/knowledge/upload/%2E%2E/%2E%2E/etc/passwd"
        )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_supported_extensions_set():
    """Quick sanity check that the extension set is non-empty and well-formed."""
    assert ".txt" in SUPPORTED_EXTENSIONS
    assert ".pdf" in SUPPORTED_EXTENSIONS
    assert ".docx" in SUPPORTED_EXTENSIONS
    for ext in SUPPORTED_EXTENSIONS:
        assert ext.startswith("."), f"Extension must start with '.': {ext!r}"

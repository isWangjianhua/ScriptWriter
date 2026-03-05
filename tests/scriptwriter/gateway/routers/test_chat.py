import httpx
import pytest

from scriptwriter.gateway.app import app
from scriptwriter.rag import reset_knowledge_services_for_tests


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_thread_chat_and_scoped_run_recovery():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/api/threads/thread_alpha/chat",
            json={"message": "Write a scene", "user_id": "user_1", "project_id": "test_1"},
        ) as response:
            assert response.status_code == 200
            lines = [line async for line in response.aiter_lines() if line]

    run_started = [line for line in lines if '"type": "run_started"' in line]
    assert run_started
    run_id = run_started[0].split('"run_id": "')[1].split('"')[0]

    assert any("canvas_update" in line for line in lines)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        recovery = await client.get(
            f"/api/threads/thread_alpha/runs/{run_id}",
            params={"user_id": "user_1", "project_id": "test_1"},
        )
    assert recovery.status_code == 200
    payload = recovery.json()
    assert payload["run_id"] == run_id
    assert payload["state"]["current_draft"]


@pytest.mark.anyio
async def test_thread_chat_rejects_empty_message():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/threads/thread_alpha/chat",
            json={"message": "", "user_id": "user_1", "project_id": "test_1"},
        )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_thread_chat_requires_user_and_project():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        missing_user = await client.post(
            "/api/threads/thread_alpha/chat",
            json={"message": "Write a scene", "project_id": "test_1"},
        )
        missing_project = await client.post(
            "/api/threads/thread_alpha/chat",
            json={"message": "Write a scene", "user_id": "user_1"},
        )
    assert missing_user.status_code == 422
    assert missing_project.status_code == 422


@pytest.mark.anyio
async def test_thread_scoped_run_recovery_forbidden_cross_tenant():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/api/threads/thread_alpha/chat",
            json={"message": "Write a scene", "user_id": "user_1", "project_id": "project_1"},
        ) as response:
            assert response.status_code == 200
            lines = [line async for line in response.aiter_lines() if line]

        run_started = [line for line in lines if '"type": "run_started"' in line]
        assert run_started
        run_id = run_started[0].split('"run_id": "')[1].split('"')[0]

        forbidden = await client.get(
            f"/api/threads/thread_alpha/runs/{run_id}",
            params={"user_id": "user_2", "project_id": "project_1"},
        )
    assert forbidden.status_code == 403


@pytest.mark.anyio
async def test_thread_chat_resume_forbidden_cross_tenant():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/api/threads/thread_alpha/chat",
            json={"message": "Write a scene", "user_id": "user_1", "project_id": "project_1"},
        ) as response:
            assert response.status_code == 200
            lines = [line async for line in response.aiter_lines() if line]

        run_started = [line for line in lines if '"type": "run_started"' in line]
        assert run_started
        run_id = run_started[0].split('"run_id": "')[1].split('"')[0]

        forbidden = await client.post(
            "/api/threads/thread_alpha/chat",
            json={
                "message": "Continue",
                "user_id": "user_2",
                "project_id": "project_1",
                "resume_run_id": run_id,
            },
        )

    assert forbidden.status_code == 403


@pytest.mark.anyio
async def test_thread_chat_rejects_invalid_thread_id():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/threads/thread..alpha/chat",
            json={"message": "Write a scene", "user_id": "user_1", "project_id": "test_1"},
        )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_thread_scoped_knowledge_ingest_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIPTWRITER_RAG_DATA_DIR", str(tmp_path))
    reset_knowledge_services_for_tests(data_dir=tmp_path)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/threads/thread_alpha/knowledge/ingest",
            json={
                "user_id": "user_1",
                "project_id": "project_1",
                "doc_type": "script",
                "title": "Pilot",
                "path_l1": "season1",
                "path_l2": "ep1",
                "content": "INT. ROOM - DAY\nHe sits.\n\nEXT. ROAD - NIGHT\nShe runs.",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["doc_id"]
    assert payload["chunk_count"] >= 2


@pytest.mark.anyio
async def test_thread_scoped_knowledge_ingest_requires_user_and_project(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIPTWRITER_RAG_DATA_DIR", str(tmp_path))
    reset_knowledge_services_for_tests(data_dir=tmp_path)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        missing_user = await client.post(
            "/api/threads/thread_alpha/knowledge/ingest",
            json={
                "project_id": "project_1",
                "doc_type": "script",
                "content": "INT. ROOM - DAY",
            },
        )
        missing_project = await client.post(
            "/api/threads/thread_alpha/knowledge/ingest",
            json={
                "user_id": "user_1",
                "doc_type": "script",
                "content": "INT. ROOM - DAY",
            },
        )
    assert missing_user.status_code == 422
    assert missing_project.status_code == 422

import httpx
import pytest

from scriptwriter.gateway.app import app
from scriptwriter.rag import reset_knowledge_services_for_tests


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_chat_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/api/chat",
            json={"message": "Write a scene", "user_id": "user_1", "project_id": "test_1"},
        ) as response:
            assert response.status_code == 200
            lines = [line async for line in response.aiter_lines() if line]

    run_started = [line for line in lines if '"type": "run_started"' in line]
    assert run_started
    run_id = run_started[0].split('"run_id": "')[1].split('"')[0]

    assert any("canvas_update" in line for line in lines)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        recovery = await client.get(f"/api/runs/{run_id}")
    assert recovery.status_code == 200
    payload = recovery.json()
    assert payload["run_id"] == run_id
    assert payload["state"]["current_draft"]


@pytest.mark.anyio
async def test_chat_endpoint_rejects_empty_message():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/chat",
            json={"message": "", "user_id": "user_1", "project_id": "test_1"},
        )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_knowledge_ingest_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRIPTWRITER_RAG_DATA_DIR", str(tmp_path))
    reset_knowledge_services_for_tests(data_dir=tmp_path)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/knowledge/ingest",
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

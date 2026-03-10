import httpx
import pytest

from scriptwriter.api.app import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_project_endpoints_create_read_chat_confirm_and_list_versions():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/api/projects",
            json={"project_id": "project_123", "title": "Pilot"},
        )
        assert created.status_code == 200

        fetched = await client.get("/api/projects/project_123")
        assert fetched.status_code == 200
        assert fetched.json()["project_id"] == "project_123"

        chatted = await client.post(
            "/api/projects/project_456/chat",
            json={"message": "Write a crime thriller series", "title": "Pilot"},
        )
        assert chatted.status_code == 200
        assert chatted.json()["current_artifact_type"] == "bible"

        outline = await client.post(
            "/api/projects/project_456/chat",
            json={"message": "approve and continue"},
        )
        assert outline.status_code == 200
        assert outline.json()["current_artifact_type"] == "outline"

        draft = await client.post(
            "/api/projects/project_456/chat",
            json={"message": "approve and start writing"},
        )
        assert draft.status_code == 200
        assert draft.json()["current_artifact_type"] == "draft"

        continued = await client.post(
            "/api/projects/project_456/chat",
            json={"message": "continue writing"},
        )
        assert continued.status_code == 200
        assert continued.json()["current_artifact_version_id"] == "draft_v2"

        confirmed = await client.post(
            "/api/projects/project_123/confirm",
            json={"comment": "continue"},
        )
        assert confirmed.status_code == 400

        create_for_knowledge = await client.post(
            "/api/projects/project_789/chat",
            json={"message": "Write a sci-fi project", "title": "Sci-Fi"},
        )
        assert create_for_knowledge.status_code == 200

        knowledge = await client.post(
            "/api/projects/project_789/knowledge/upload",
            json={
                "user_id": "user_1",
                "content": "Reference notes for the project",
                "doc_type": "text",
                "title": "Story Guide",
                "source_type": "reference",
            },
        )
        assert knowledge.status_code == 200
        assert knowledge.json()["chunk_count"] >= 1

        versions = await client.get("/api/projects/project_456/versions")
        assert versions.status_code == 200
        payload = versions.json()
        assert payload["bible"]
        assert payload["outline"]
        assert payload["draft"]

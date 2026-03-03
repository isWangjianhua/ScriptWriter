from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_endpoint():
    with client.stream("POST", "/api/chat", json={"message": "Write a scene", "tenant_id": "tenant_1", "project_id": "test_1"}) as response:
        assert response.status_code == 200
        lines = list(response.iter_lines())
        
    assert any("canvas_update" in line for line in lines if line)

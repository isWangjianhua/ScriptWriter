from app.core.state import ScreenplayState

def test_screenplay_state_dict():
    state: ScreenplayState = {
        "messages": [],
        "tenant_id": "test_tenant",
        "project_id": "test_project",
        "current_draft": "",
        "critic_notes": [],
        "revision_count": 0,
        "artifacts": {}
    }
    assert state["project_id"] == "test_project"
    assert state["tenant_id"] == "test_tenant"
    assert state["revision_count"] == 0

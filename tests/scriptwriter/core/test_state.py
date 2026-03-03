from scriptwriter.core.state import ScreenplayState

def test_screenplay_state_dict():
    state: ScreenplayState = {
        "messages": [],
        "user_id": "test_user",
        "project_id": "test_project",
        "current_draft": "",
        "plan": [],
        "critic_notes": [],
        "revision_count": 0,
        "artifacts": {}
    }
    assert state["project_id"] == "test_project"
    assert state["user_id"] == "test_user"
    assert state["revision_count"] == 0

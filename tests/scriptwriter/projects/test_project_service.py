from scriptwriter.projects.memory import MemoryService
from scriptwriter.projects.service import ProjectService
from scriptwriter.projects.store import InMemoryProjectStore


def test_create_project_from_chat_generates_bible_and_waits_for_confirmation():
    service = ProjectService(store=InMemoryProjectStore(), memory_service=MemoryService())

    project = service.create_project_from_chat(
        project_id="project_123",
        title="Pilot",
        user_input="Write a crime thriller project",
    )

    assert project.stage == "awaiting_confirmation"
    assert project.current_artifact_type == "bible"
    assert project.current_artifact_version_id == "bible_v1"
    assert project.active_bible_version_id == "bible_v1"


def test_confirming_bible_generates_outline_and_waits_again():
    service = ProjectService(store=InMemoryProjectStore(), memory_service=MemoryService())
    service.create_project_from_chat(project_id="project_123", title="Pilot", user_input="Write a crime thriller project")

    project = service.confirm_current_artifact("project_123", comment="continue")

    assert project.stage == "awaiting_confirmation"
    assert project.current_artifact_type == "outline"
    assert project.current_artifact_version_id == "outline_v1"
    assert project.active_outline_version_id == "outline_v1"


def test_confirming_outline_enters_drafting_with_first_draft_version():
    service = ProjectService(store=InMemoryProjectStore(), memory_service=MemoryService())
    service.create_project_from_chat(project_id="project_123", title="Pilot", user_input="Write a crime thriller project")
    service.confirm_current_artifact("project_123", comment="continue")

    project = service.confirm_current_artifact("project_123", comment="start writing")

    assert project.stage == "drafting"
    assert project.current_artifact_type == "draft"
    assert project.current_artifact_version_id == "draft_v1"
    assert project.active_draft_version_id == "draft_v1"


def test_rewrite_scene_generates_new_draft_version():
    service = ProjectService(store=InMemoryProjectStore(), memory_service=MemoryService())
    service.create_project_from_chat(project_id="project_123", title="Pilot", user_input="Write a crime thriller project")
    service.confirm_current_artifact("project_123", comment="continue")
    service.confirm_current_artifact("project_123", comment="start writing")

    project = service.rewrite_scene("project_123", "rewrite scene three with more conflict")

    assert project.current_artifact_type == "draft"
    assert project.current_artifact_version_id == "draft_v2"
    assert project.active_draft_version_id == "draft_v2"


def test_handle_chat_routes_confirmation_and_continue_actions():
    service = ProjectService(store=InMemoryProjectStore(), memory_service=MemoryService())
    service.handle_chat(project_id="project_123", title="Pilot", user_input="Write a crime thriller project")

    outline_project = service.handle_chat(project_id="project_123", user_input="approve and continue")
    assert outline_project.current_artifact_type == "outline"
    assert outline_project.current_artifact_version_id == "outline_v1"

    draft_project = service.handle_chat(project_id="project_123", user_input="approve and start writing")
    assert draft_project.current_artifact_type == "draft"
    assert draft_project.current_artifact_version_id == "draft_v1"

    continued_project = service.handle_chat(project_id="project_123", user_input="continue writing")
    assert continued_project.stage == "drafting"
    assert continued_project.current_artifact_version_id == "draft_v2"


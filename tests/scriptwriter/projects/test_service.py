from scriptwriter.memory.service import MemoryService
from scriptwriter.projects.service import ProjectService
from scriptwriter.storage.in_memory_project_store import InMemoryProjectStore


def test_create_project_from_chat_generates_bible_and_waits_for_confirmation():
    service = ProjectService(store=InMemoryProjectStore(), memory_service=MemoryService())

    project = service.create_project_from_chat(
        project_id="project_123",
        title="Pilot",
        user_input="写一个犯罪悬疑剧项目",
    )

    assert project.stage == "awaiting_confirmation"
    assert project.current_artifact_type == "bible"
    assert project.current_artifact_version_id == "bible_v1"
    assert project.active_bible_version_id == "bible_v1"


def test_confirming_bible_generates_outline_and_waits_again():
    service = ProjectService(store=InMemoryProjectStore(), memory_service=MemoryService())
    service.create_project_from_chat(project_id="project_123", title="Pilot", user_input="写一个犯罪悬疑剧项目")

    project = service.confirm_current_artifact("project_123", comment="继续")

    assert project.stage == "awaiting_confirmation"
    assert project.current_artifact_type == "outline"
    assert project.current_artifact_version_id == "outline_v1"
    assert project.active_outline_version_id == "outline_v1"


def test_confirming_outline_enters_drafting_with_first_draft_version():
    service = ProjectService(store=InMemoryProjectStore(), memory_service=MemoryService())
    service.create_project_from_chat(project_id="project_123", title="Pilot", user_input="写一个犯罪悬疑剧项目")
    service.confirm_current_artifact("project_123", comment="继续")

    project = service.confirm_current_artifact("project_123", comment="开始写")

    assert project.stage == "drafting"
    assert project.current_artifact_type == "draft"
    assert project.current_artifact_version_id == "draft_v1"
    assert project.active_draft_version_id == "draft_v1"


def test_rewrite_scene_generates_new_draft_version():
    service = ProjectService(store=InMemoryProjectStore(), memory_service=MemoryService())
    service.create_project_from_chat(project_id="project_123", title="Pilot", user_input="写一个犯罪悬疑剧项目")
    service.confirm_current_artifact("project_123", comment="继续")
    service.confirm_current_artifact("project_123", comment="开始写")

    project = service.rewrite_scene("project_123", "重写第三场戏，让冲突更强")

    assert project.current_artifact_type == "draft"
    assert project.current_artifact_version_id == "draft_v2"
    assert project.active_draft_version_id == "draft_v2"


def test_handle_chat_routes_confirmation_and_continue_actions():
    service = ProjectService(store=InMemoryProjectStore(), memory_service=MemoryService())
    service.handle_chat(project_id="project_123", title="Pilot", user_input="写一个犯罪悬疑剧项目")

    outline_project = service.handle_chat(project_id="project_123", user_input="确认，继续")
    assert outline_project.current_artifact_type == "outline"
    assert outline_project.current_artifact_version_id == "outline_v1"

    draft_project = service.handle_chat(project_id="project_123", user_input="确认，开始写")
    assert draft_project.current_artifact_type == "draft"
    assert draft_project.current_artifact_version_id == "draft_v1"

    continued_project = service.handle_chat(project_id="project_123", user_input="继续往下写")
    assert continued_project.stage == "drafting"
    assert continued_project.current_artifact_version_id == "draft_v2"

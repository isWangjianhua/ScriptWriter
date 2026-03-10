from scriptwriter.projects.models import BibleVersion, ConfirmationRecord, DraftVersion, OutlineVersion, Project
from scriptwriter.projects.store import InMemoryProjectStore


def test_create_project_and_load_it_back():
    store = InMemoryProjectStore()
    project = Project(project_id="project_123", title="Pilot", stage="planning")

    store.create_project(project)

    loaded = store.get_project("project_123")
    assert loaded == project


def test_save_versions_and_list_them_by_artifact_type():
    store = InMemoryProjectStore()
    store.create_project(Project(project_id="project_123", title="Pilot", stage="planning"))

    bible = BibleVersion(version_id="b1", project_id="project_123", version_number=1, content="bible")
    outline = OutlineVersion(version_id="o1", project_id="project_123", version_number=1, content="outline")
    draft = DraftVersion(version_id="d1", project_id="project_123", version_number=1, content="draft")

    store.save_bible_version(bible)
    store.save_outline_version(outline)
    store.save_draft_version(draft)

    assert store.list_versions("project_123", "bible") == [bible]
    assert store.list_versions("project_123", "outline") == [outline]
    assert store.list_versions("project_123", "draft") == [draft]


def test_set_active_version_updates_project_pointer():
    store = InMemoryProjectStore()
    project = Project(project_id="project_123", title="Pilot", stage="planning")
    store.create_project(project)
    store.save_outline_version(OutlineVersion(version_id="o2", project_id="project_123", version_number=2, content="outline"))

    updated = store.set_active_version("project_123", "outline", "o2")

    assert updated.active_outline_version_id == "o2"
    assert store.get_project("project_123").active_outline_version_id == "o2"


def test_record_confirmation_returns_the_saved_record():
    store = InMemoryProjectStore()
    store.create_project(Project(project_id="project_123", title="Pilot", stage="planning"))
    record = ConfirmationRecord(
        record_id="c1",
        project_id="project_123",
        artifact_type="bible",
        artifact_version_id="b1",
        approved=True,
    )

    saved = store.record_confirmation(record)

    assert saved == record


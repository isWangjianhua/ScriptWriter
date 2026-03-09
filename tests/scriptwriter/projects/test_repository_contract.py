from scriptwriter.projects.models import BibleVersion, ConfirmationRecord, DraftVersion, OutlineVersion, Project
from scriptwriter.projects.repository import ProjectRepository


class FakeProjectRepository:
    def create_project(self, project: Project) -> Project:
        return project

    def save_project(self, project: Project) -> Project:
        return project

    def get_project(self, project_id: str) -> Project | None:
        return None

    def save_bible_version(self, version: BibleVersion) -> BibleVersion:
        return version

    def save_outline_version(self, version: OutlineVersion) -> OutlineVersion:
        return version

    def save_draft_version(self, version: DraftVersion) -> DraftVersion:
        return version

    def list_versions(self, project_id: str, artifact_type: str) -> list[BibleVersion | OutlineVersion | DraftVersion]:
        return []

    def set_active_version(self, project_id: str, artifact_type: str, version_id: str) -> Project:
        return Project(project_id=project_id, title="Pilot", stage="planning")

    def record_confirmation(self, record: ConfirmationRecord) -> ConfirmationRecord:
        return record


def test_project_repository_protocol_accepts_expected_shape():
    assert isinstance(FakeProjectRepository(), ProjectRepository)


def test_project_model_defaults_active_version_pointers_to_none():
    project = Project(project_id="project_123", title="Pilot", stage="planning")

    assert project.current_artifact_type is None
    assert project.current_artifact_version_id is None
    assert project.active_bible_version_id is None
    assert project.active_outline_version_id is None
    assert project.active_draft_version_id is None


def test_version_models_keep_artifact_types_stable():
    bible = BibleVersion(version_id="b1", project_id="project_123", version_number=1, content="bible")
    outline = OutlineVersion(version_id="o1", project_id="project_123", version_number=2, content="outline")
    draft = DraftVersion(version_id="d1", project_id="project_123", version_number=3, content="draft")

    assert bible.artifact_type == "bible"
    assert outline.artifact_type == "outline"
    assert draft.artifact_type == "draft"


def test_confirmation_record_captures_review_outcome():
    record = ConfirmationRecord(
        record_id="confirm_1",
        project_id="project_123",
        artifact_type="outline",
        artifact_version_id="o1",
        approved=False,
        comment="Need more tension.",
    )

    assert record.approved is False
    assert record.comment == "Need more tension."

from scriptwriter.shared.models import ArtifactVersionSummary, ConfirmationPayload, ProjectSummary
from scriptwriter.workflow.models import ArtifactType, WorkflowStage, WorkflowState


def test_workflow_stage_values_are_stable():
    assert WorkflowStage.PLANNING.value == "planning"
    assert WorkflowStage.AWAITING_CONFIRMATION.value == "awaiting_confirmation"
    assert WorkflowStage.DRAFTING.value == "drafting"
    assert WorkflowStage.COMPLETED.value == "completed"
    assert WorkflowStage.REWRITING.value == "rewriting"


def test_artifact_type_values_are_stable():
    assert ArtifactType.BIBLE.value == "bible"
    assert ArtifactType.OUTLINE.value == "outline"
    assert ArtifactType.DRAFT.value == "draft"


def test_workflow_state_tracks_current_artifact_context():
    state = WorkflowState(
        stage=WorkflowStage.AWAITING_CONFIRMATION,
        current_artifact_type=ArtifactType.OUTLINE,
        current_artifact_version_id="outline_v2",
    )

    assert state.stage is WorkflowStage.AWAITING_CONFIRMATION
    assert state.current_artifact_type is ArtifactType.OUTLINE
    assert state.current_artifact_version_id == "outline_v2"


def test_project_summary_exposes_stage_and_current_artifact():
    project = ProjectSummary(
        project_id="project_123",
        title="Pilot",
        stage="planning",
        current_artifact_type="bible",
        current_artifact_version_id="bible_v1",
    )

    assert project.project_id == "project_123"
    assert project.stage == "planning"
    assert project.current_artifact_type == "bible"
    assert project.current_artifact_version_id == "bible_v1"


def test_artifact_version_summary_defaults_to_active_status():
    version = ArtifactVersionSummary(
        version_id="outline_v1",
        project_id="project_123",
        artifact_type="outline",
        version_number=1,
    )

    assert version.status == "active"


def test_confirmation_payload_tracks_user_decision():
    payload = ConfirmationPayload(
        project_id="project_123",
        artifact_type="bible",
        artifact_version_id="bible_v1",
        approved=True,
        comment="Looks good.",
    )

    assert payload.approved is True
    assert payload.comment == "Looks good."

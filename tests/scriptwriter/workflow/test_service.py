from scriptwriter.workflow.models import ArtifactType, WorkflowStage, WorkflowState
from scriptwriter.workflow.service import WorkflowAction, advance_workflow


def test_start_project_enters_planning_with_bible_target():
    state = advance_workflow(None, WorkflowAction.START_PROJECT)

    assert state.stage is WorkflowStage.PLANNING
    assert state.current_artifact_type is ArtifactType.BIBLE
    assert state.current_artifact_version_id is None


def test_approving_bible_moves_back_to_planning_for_outline():
    state = WorkflowState(
        stage=WorkflowStage.AWAITING_CONFIRMATION,
        current_artifact_type=ArtifactType.BIBLE,
        current_artifact_version_id="bible_v1",
    )

    next_state = advance_workflow(state, WorkflowAction.APPROVE_ARTIFACT)

    assert next_state.stage is WorkflowStage.PLANNING
    assert next_state.current_artifact_type is ArtifactType.OUTLINE
    assert next_state.current_artifact_version_id is None


def test_approving_outline_enters_drafting():
    state = WorkflowState(
        stage=WorkflowStage.AWAITING_CONFIRMATION,
        current_artifact_type=ArtifactType.OUTLINE,
        current_artifact_version_id="outline_v2",
    )

    next_state = advance_workflow(state, WorkflowAction.APPROVE_ARTIFACT)

    assert next_state.stage is WorkflowStage.DRAFTING
    assert next_state.current_artifact_type is ArtifactType.DRAFT


def test_rewrite_request_enters_rewriting_mode():
    state = WorkflowState(
        stage=WorkflowStage.COMPLETED,
        current_artifact_type=ArtifactType.DRAFT,
        current_artifact_version_id="draft_v3",
    )

    next_state = advance_workflow(state, WorkflowAction.REQUEST_REWRITE)

    assert next_state.stage is WorkflowStage.REWRITING
    assert next_state.current_artifact_type is ArtifactType.DRAFT
    assert next_state.current_artifact_version_id == "draft_v3"


def test_rewrite_completion_returns_to_requested_stage():
    state = WorkflowState(
        stage=WorkflowStage.REWRITING,
        current_artifact_type=ArtifactType.DRAFT,
        current_artifact_version_id="draft_v4",
    )

    next_state = advance_workflow(
        state,
        WorkflowAction.COMPLETE_REWRITE,
        rewrite_returns_to=WorkflowStage.COMPLETED,
    )

    assert next_state.stage is WorkflowStage.COMPLETED
    assert next_state.current_artifact_type is ArtifactType.DRAFT
    assert next_state.current_artifact_version_id == "draft_v4"

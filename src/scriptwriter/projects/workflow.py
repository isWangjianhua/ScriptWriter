from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class WorkflowStage(str, Enum):
    PLANNING = "planning"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    DRAFTING = "drafting"
    COMPLETED = "completed"
    REWRITING = "rewriting"


class ArtifactType(str, Enum):
    BIBLE = "bible"
    OUTLINE = "outline"
    DRAFT = "draft"


class WorkflowState(BaseModel):
    stage: WorkflowStage
    current_artifact_type: ArtifactType | None = None
    current_artifact_version_id: str | None = None


class WorkflowAction(str, Enum):
    START_PROJECT = "start_project"
    APPROVE_ARTIFACT = "approve_artifact"
    REQUEST_REWRITE = "request_rewrite"
    COMPLETE_REWRITE = "complete_rewrite"
    RETURN_TO_PLANNING = "return_to_planning"
    COMPLETE_DRAFT = "complete_draft"


def advance_workflow(
    state: WorkflowState | None,
    action: WorkflowAction,
    *,
    rewrite_returns_to: WorkflowStage = WorkflowStage.DRAFTING,
) -> WorkflowState:
    if action is WorkflowAction.START_PROJECT:
        return WorkflowState(stage=WorkflowStage.PLANNING, current_artifact_type=ArtifactType.BIBLE)

    if action is WorkflowAction.APPROVE_ARTIFACT:
        if state is None or state.stage is not WorkflowStage.AWAITING_CONFIRMATION or state.current_artifact_type is None:
            raise ValueError("approve_artifact requires a pending artifact confirmation state")

        if state.current_artifact_type is ArtifactType.BIBLE:
            return WorkflowState(stage=WorkflowStage.PLANNING, current_artifact_type=ArtifactType.OUTLINE)

        if state.current_artifact_type is ArtifactType.OUTLINE:
            return WorkflowState(stage=WorkflowStage.DRAFTING, current_artifact_type=ArtifactType.DRAFT)

        return WorkflowState(
            stage=WorkflowStage.COMPLETED,
            current_artifact_type=ArtifactType.DRAFT,
            current_artifact_version_id=state.current_artifact_version_id,
        )

    if action is WorkflowAction.REQUEST_REWRITE:
        if state is None:
            raise ValueError("request_rewrite requires an existing workflow state")

        return WorkflowState(
            stage=WorkflowStage.REWRITING,
            current_artifact_type=ArtifactType.DRAFT,
            current_artifact_version_id=state.current_artifact_version_id,
        )

    if action is WorkflowAction.COMPLETE_REWRITE:
        if state is None or state.stage is not WorkflowStage.REWRITING:
            raise ValueError("complete_rewrite requires a rewriting state")

        return WorkflowState(
            stage=rewrite_returns_to,
            current_artifact_type=ArtifactType.DRAFT,
            current_artifact_version_id=state.current_artifact_version_id,
        )

    if action is WorkflowAction.RETURN_TO_PLANNING:
        return WorkflowState(stage=WorkflowStage.PLANNING, current_artifact_type=ArtifactType.BIBLE)

    if action is WorkflowAction.COMPLETE_DRAFT:
        if state is None:
            raise ValueError("complete_draft requires an existing workflow state")

        return WorkflowState(
            stage=WorkflowStage.COMPLETED,
            current_artifact_type=ArtifactType.DRAFT,
            current_artifact_version_id=state.current_artifact_version_id,
        )

    raise ValueError(f"Unsupported workflow action: {action}")

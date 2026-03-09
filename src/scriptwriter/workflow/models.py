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

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ArtifactKind = Literal["bible", "outline", "draft"]


class ProjectSummary(BaseModel):
    project_id: str
    title: str
    stage: str
    current_artifact_type: ArtifactKind | None = None
    current_artifact_version_id: str | None = None


class ArtifactVersionSummary(BaseModel):
    version_id: str
    project_id: str
    artifact_type: ArtifactKind
    version_number: int = Field(ge=1)
    status: str = "active"
    title: str | None = None


class ConfirmationPayload(BaseModel):
    project_id: str
    artifact_type: ArtifactKind
    artifact_version_id: str
    approved: bool
    comment: str | None = None

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

ArtifactVersionType = Literal["bible", "outline", "draft"]


class Project(BaseModel):
    project_id: str
    title: str
    stage: str
    current_artifact_type: ArtifactVersionType | None = None
    current_artifact_version_id: str | None = None
    active_bible_version_id: str | None = None
    active_outline_version_id: str | None = None
    active_draft_version_id: str | None = None


class BibleVersion(BaseModel):
    version_id: str
    project_id: str
    version_number: int
    content: str
    artifact_type: Literal["bible"] = "bible"
    status: str = "active"


class OutlineVersion(BaseModel):
    version_id: str
    project_id: str
    version_number: int
    content: str
    artifact_type: Literal["outline"] = "outline"
    status: str = "active"


class DraftVersion(BaseModel):
    version_id: str
    project_id: str
    version_number: int
    content: str
    artifact_type: Literal["draft"] = "draft"
    status: str = "active"


class ConfirmationRecord(BaseModel):
    record_id: str
    project_id: str
    artifact_type: ArtifactVersionType
    artifact_version_id: str
    approved: bool
    comment: str | None = None

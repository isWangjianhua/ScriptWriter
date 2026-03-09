from __future__ import annotations

from typing import Protocol, runtime_checkable

from scriptwriter.projects.models import BibleVersion, ConfirmationRecord, DraftVersion, OutlineVersion, Project


@runtime_checkable
class ProjectRepository(Protocol):
    def create_project(self, project: Project) -> Project:
        ...

    def save_project(self, project: Project) -> Project:
        ...

    def get_project(self, project_id: str) -> Project | None:
        ...

    def save_bible_version(self, version: BibleVersion) -> BibleVersion:
        ...

    def save_outline_version(self, version: OutlineVersion) -> OutlineVersion:
        ...

    def save_draft_version(self, version: DraftVersion) -> DraftVersion:
        ...

    def list_versions(self, project_id: str, artifact_type: str) -> list[BibleVersion | OutlineVersion | DraftVersion]:
        ...

    def set_active_version(self, project_id: str, artifact_type: str, version_id: str) -> Project:
        ...

    def record_confirmation(self, record: ConfirmationRecord) -> ConfirmationRecord:
        ...

from __future__ import annotations

from scriptwriter.projects.models import BibleVersion, ConfirmationRecord, DraftVersion, OutlineVersion, Project
from scriptwriter.storage.project_store import ProjectStore


class InMemoryProjectStore(ProjectStore):
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._versions: dict[tuple[str, str], list[BibleVersion | OutlineVersion | DraftVersion]] = {}
        self._confirmations: dict[str, list[ConfirmationRecord]] = {}

    def create_project(self, project: Project) -> Project:
        self._projects[project.project_id] = project.model_copy(deep=True)
        return self._projects[project.project_id].model_copy(deep=True)

    def save_project(self, project: Project) -> Project:
        self._projects[project.project_id] = project.model_copy(deep=True)
        return self._projects[project.project_id].model_copy(deep=True)

    def get_project(self, project_id: str) -> Project | None:
        project = self._projects.get(project_id)
        if project is None:
            return None
        return project.model_copy(deep=True)

    def save_bible_version(self, version: BibleVersion) -> BibleVersion:
        self._append_version(version.project_id, "bible", version)
        return version

    def save_outline_version(self, version: OutlineVersion) -> OutlineVersion:
        self._append_version(version.project_id, "outline", version)
        return version

    def save_draft_version(self, version: DraftVersion) -> DraftVersion:
        self._append_version(version.project_id, "draft", version)
        return version

    def list_versions(self, project_id: str, artifact_type: str) -> list[BibleVersion | OutlineVersion | DraftVersion]:
        versions = self._versions.get((project_id, artifact_type), [])
        return [version.model_copy(deep=True) for version in versions]

    def set_active_version(self, project_id: str, artifact_type: str, version_id: str) -> Project:
        project = self._require_project(project_id)

        if artifact_type == "bible":
            updated = project.model_copy(update={"active_bible_version_id": version_id})
        elif artifact_type == "outline":
            updated = project.model_copy(update={"active_outline_version_id": version_id})
        elif artifact_type == "draft":
            updated = project.model_copy(update={"active_draft_version_id": version_id})
        else:
            raise ValueError(f"Unsupported artifact type: {artifact_type}")

        self._projects[project_id] = updated
        return updated.model_copy(deep=True)

    def record_confirmation(self, record: ConfirmationRecord) -> ConfirmationRecord:
        self._require_project(record.project_id)
        self._confirmations.setdefault(record.project_id, []).append(record.model_copy(deep=True))
        return record

    def _append_version(
        self,
        project_id: str,
        artifact_type: str,
        version: BibleVersion | OutlineVersion | DraftVersion,
    ) -> None:
        self._require_project(project_id)
        self._versions.setdefault((project_id, artifact_type), []).append(version.model_copy(deep=True))

    def _require_project(self, project_id: str) -> Project:
        project = self._projects.get(project_id)
        if project is None:
            raise KeyError(project_id)
        return project

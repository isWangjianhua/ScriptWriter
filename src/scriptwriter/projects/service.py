from __future__ import annotations

from dataclasses import dataclass

from scriptwriter.agent.models import AgentAction, AgentRequest
from scriptwriter.agent.prompts import build_bible_prompt, build_draft_prompt, build_outline_prompt, build_rewrite_prompt
from scriptwriter.agent.service import plan_agent_action
from scriptwriter.projects.memory import MemoryService
from scriptwriter.projects.models import BibleVersion, ConfirmationRecord, DraftVersion, OutlineVersion, Project
from scriptwriter.projects.repository import ProjectRepository
from scriptwriter.projects.workflow import ArtifactType, WorkflowAction, WorkflowStage, WorkflowState, advance_workflow


@dataclass
class ProjectService:
    store: ProjectRepository
    memory_service: MemoryService

    def create_project(self, *, project_id: str, title: str) -> Project:
        existing = self.store.get_project(project_id)
        if existing is not None:
            return existing
        return self.store.create_project(Project(project_id=project_id, title=title, stage=WorkflowStage.PLANNING.value))

    def get_project(self, project_id: str) -> Project | None:
        return self.store.get_project(project_id)

    def list_versions(self, project_id: str) -> dict[str, list[dict[str, object]]]:
        if self.store.get_project(project_id) is None:
            raise KeyError(project_id)
        return {
            "bible": [version.model_dump() for version in self.store.list_versions(project_id, ArtifactType.BIBLE.value)],
            "outline": [version.model_dump() for version in self.store.list_versions(project_id, ArtifactType.OUTLINE.value)],
            "draft": [version.model_dump() for version in self.store.list_versions(project_id, ArtifactType.DRAFT.value)],
        }

    def handle_chat(self, *, project_id: str, user_input: str, title: str | None = None) -> Project:
        project = self.store.get_project(project_id)
        if project is None:
            if title is None:
                raise ValueError("title is required when creating a project from chat")
            return self.create_project_from_chat(project_id=project_id, title=title, user_input=user_input)

        request = AgentRequest(user_input=user_input, workflow_state=self._project_to_workflow_state(project))
        plan = plan_agent_action(request)

        if plan.action is AgentAction.CONFIRM_ARTIFACT:
            return self.confirm_current_artifact(project_id, comment=user_input)
        if plan.action is AgentAction.REWRITE_SCENE:
            return self.rewrite_scene(project_id, user_input)
        if plan.action is AgentAction.CONTINUE_DRAFT:
            return self._generate_draft(project, user_input, stage=WorkflowStage.DRAFTING)
        if plan.action is AgentAction.GENERATE_OUTLINE:
            return self._generate_outline(project, user_input)
        return self._generate_bible(project, user_input)

    def create_project_from_chat(self, *, project_id: str, title: str, user_input: str) -> Project:
        initial_state = advance_workflow(None, WorkflowAction.START_PROJECT)
        project = Project(
            project_id=project_id,
            title=title,
            stage=initial_state.stage.value,
            current_artifact_type=initial_state.current_artifact_type.value if initial_state.current_artifact_type else None,
            current_artifact_version_id=initial_state.current_artifact_version_id,
        )
        self.store.create_project(project)
        return self._generate_bible(project, user_input)

    def confirm_current_artifact(self, project_id: str, *, comment: str | None = None) -> Project:
        project = self._require_project(project_id)
        if project.current_artifact_type is None or project.current_artifact_version_id is None:
            raise ValueError("No current artifact is awaiting confirmation")

        self.store.record_confirmation(
            ConfirmationRecord(
                record_id=f"confirm_{project.current_artifact_version_id}",
                project_id=project_id,
                artifact_type=project.current_artifact_type,
                artifact_version_id=project.current_artifact_version_id,
                approved=True,
                comment=comment,
            )
        )

        state = WorkflowState(
            stage=WorkflowStage.AWAITING_CONFIRMATION,
            current_artifact_type=ArtifactType(project.current_artifact_type),
            current_artifact_version_id=project.current_artifact_version_id,
        )
        next_state = advance_workflow(state, WorkflowAction.APPROVE_ARTIFACT)

        if next_state.current_artifact_type is ArtifactType.OUTLINE:
            return self._generate_outline(project, comment or "continue")
        if next_state.current_artifact_type is ArtifactType.DRAFT:
            return self._generate_draft(project, comment or "start writing", stage=next_state.stage)

        updated = project.model_copy(
            update={
                "stage": next_state.stage.value,
                "current_artifact_type": next_state.current_artifact_type.value if next_state.current_artifact_type else None,
                "current_artifact_version_id": next_state.current_artifact_version_id,
            }
        )
        return self.store.save_project(updated)

    def rewrite_scene(self, project_id: str, instruction: str) -> Project:
        project = self._require_project(project_id)
        state = self._project_to_workflow_state(project)
        rewrite_state = advance_workflow(state, WorkflowAction.REQUEST_REWRITE)
        rewrite_project = project.model_copy(update={"stage": rewrite_state.stage.value})
        self.store.save_project(rewrite_project)
        return self._generate_draft(rewrite_project, instruction, stage=WorkflowStage.COMPLETED, rewrite=True)

    def _generate_bible(self, project: Project, user_input: str) -> Project:
        version_id = self._next_version_id(project.project_id, ArtifactType.BIBLE)
        bible = BibleVersion(
            version_id=version_id,
            project_id=project.project_id,
            version_number=self._next_version_number(project.project_id, ArtifactType.BIBLE),
            content=build_bible_prompt(user_input),
        )
        self.store.save_bible_version(bible)
        project = self.store.set_active_version(project.project_id, ArtifactType.BIBLE.value, version_id)
        project = project.model_copy(
            update={
                "stage": WorkflowStage.AWAITING_CONFIRMATION.value,
                "current_artifact_type": ArtifactType.BIBLE.value,
                "current_artifact_version_id": version_id,
            }
        )
        return self.store.save_project(project)

    def _generate_outline(self, project: Project, user_input: str) -> Project:
        version_id = self._next_version_id(project.project_id, ArtifactType.OUTLINE)
        outline = OutlineVersion(
            version_id=version_id,
            project_id=project.project_id,
            version_number=self._next_version_number(project.project_id, ArtifactType.OUTLINE),
            content=build_outline_prompt(user_input),
        )
        self.store.save_outline_version(outline)
        project = self.store.set_active_version(project.project_id, ArtifactType.OUTLINE.value, version_id)
        project = project.model_copy(
            update={
                "stage": WorkflowStage.AWAITING_CONFIRMATION.value,
                "current_artifact_type": ArtifactType.OUTLINE.value,
                "current_artifact_version_id": version_id,
            }
        )
        return self.store.save_project(project)

    def _generate_draft(self, project: Project, user_input: str, *, stage: WorkflowStage, rewrite: bool = False) -> Project:
        version_id = self._next_version_id(project.project_id, ArtifactType.DRAFT)
        draft = DraftVersion(
            version_id=version_id,
            project_id=project.project_id,
            version_number=self._next_version_number(project.project_id, ArtifactType.DRAFT),
            content=build_rewrite_prompt(user_input) if rewrite else build_draft_prompt(user_input),
        )
        self.store.save_draft_version(draft)
        project = self.store.set_active_version(project.project_id, ArtifactType.DRAFT.value, version_id)
        project = project.model_copy(
            update={
                "stage": stage.value,
                "current_artifact_type": ArtifactType.DRAFT.value,
                "current_artifact_version_id": version_id,
            }
        )
        return self.store.save_project(project)

    def _project_to_workflow_state(self, project: Project) -> WorkflowState:
        return WorkflowState(
            stage=WorkflowStage(project.stage),
            current_artifact_type=ArtifactType(project.current_artifact_type) if project.current_artifact_type else None,
            current_artifact_version_id=project.current_artifact_version_id,
        )

    def _next_version_number(self, project_id: str, artifact_type: ArtifactType) -> int:
        return len(self.store.list_versions(project_id, artifact_type.value)) + 1

    def _next_version_id(self, project_id: str, artifact_type: ArtifactType) -> str:
        version_number = self._next_version_number(project_id, artifact_type)
        return f"{artifact_type.value}_v{version_number}"

    def _require_project(self, project_id: str) -> Project:
        project = self.store.get_project(project_id)
        if project is None:
            raise KeyError(project_id)
        return project


from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from scriptwriter.projects.workflow import WorkflowState


class AgentAction(str, Enum):
    GENERATE_BIBLE = "generate_bible"
    GENERATE_OUTLINE = "generate_outline"
    CONFIRM_ARTIFACT = "confirm_artifact"
    CONTINUE_DRAFT = "continue_draft"
    REWRITE_SCENE = "rewrite_scene"


class AgentRequest(BaseModel):
    user_input: str
    workflow_state: WorkflowState | None = None


class AgentPlan(BaseModel):
    action: AgentAction
    reason: str


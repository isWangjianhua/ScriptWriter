from __future__ import annotations

from scriptwriter.agent.models import AgentAction, AgentPlan, AgentRequest
from scriptwriter.projects.workflow import ArtifactType, WorkflowStage

_CONFIRM_TOKENS = (
    "confirm",
    "approved",
    "approve",
    "ok",
    "yes",
    "looks good",
    "continue",
    "确认",
    "通过",
    "可以",
    "继续",
)
_REWRITE_TOKENS = (
    "rewrite",
    "revise",
    "redo",
    "重写",
    "改写",
    "重来",
)
_CONTINUE_TOKENS = (
    "continue",
    "more",
    "next",
    "keep writing",
    "继续",
    "往下写",
    "接着写",
)


def plan_agent_action(request: AgentRequest) -> AgentPlan:
    user_input = request.user_input.strip()
    lowered = user_input.lower()
    workflow_state = request.workflow_state

    if workflow_state is None:
        return AgentPlan(action=AgentAction.GENERATE_BIBLE, reason="No workflow state exists yet.")

    if any(token in user_input or token in lowered for token in _REWRITE_TOKENS):
        return AgentPlan(action=AgentAction.REWRITE_SCENE, reason="User explicitly requested a rewrite.")

    if workflow_state.stage is WorkflowStage.AWAITING_CONFIRMATION and any(
        token in user_input or token in lowered for token in _CONFIRM_TOKENS
    ):
        return AgentPlan(action=AgentAction.CONFIRM_ARTIFACT, reason="User approved the pending artifact.")

    if workflow_state.stage is WorkflowStage.PLANNING and workflow_state.current_artifact_type is ArtifactType.OUTLINE:
        return AgentPlan(action=AgentAction.GENERATE_OUTLINE, reason="Planning is currently targeting the outline.")

    if workflow_state.stage is WorkflowStage.DRAFTING or any(
        token in user_input or token in lowered for token in _CONTINUE_TOKENS
    ):
        return AgentPlan(action=AgentAction.CONTINUE_DRAFT, reason="User wants to keep drafting.")

    return AgentPlan(action=AgentAction.GENERATE_BIBLE, reason="Defaulting to bible generation.")

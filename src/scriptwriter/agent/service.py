from __future__ import annotations

from scriptwriter.agent.models import AgentAction, AgentPlan, AgentRequest
from scriptwriter.workflow.models import ArtifactType, WorkflowStage

_CONFIRM_TOKENS = ("确认", "ok", "好的", "continue", "approve")
_REWRITE_TOKENS = ("重写", "rewrite", "改写")
_CONTINUE_TOKENS = ("继续", "continue", "往下写", "more")


def plan_agent_action(request: AgentRequest) -> AgentPlan:
    user_input = request.user_input.strip()
    lowered = user_input.lower()
    workflow_state = request.workflow_state

    if workflow_state is None:
        return AgentPlan(action=AgentAction.GENERATE_BIBLE, reason="No workflow state exists yet.")

    if any(token in lowered for token in _REWRITE_TOKENS):
        return AgentPlan(action=AgentAction.REWRITE_SCENE, reason="User explicitly requested a rewrite.")

    if workflow_state.stage is WorkflowStage.AWAITING_CONFIRMATION and any(token in lowered for token in _CONFIRM_TOKENS):
        return AgentPlan(action=AgentAction.CONFIRM_ARTIFACT, reason="User approved the pending artifact.")

    if workflow_state.stage is WorkflowStage.PLANNING and workflow_state.current_artifact_type is ArtifactType.OUTLINE:
        return AgentPlan(action=AgentAction.GENERATE_OUTLINE, reason="Planning is currently targeting the outline.")

    if workflow_state.stage is WorkflowStage.DRAFTING or any(token in lowered for token in _CONTINUE_TOKENS):
        return AgentPlan(action=AgentAction.CONTINUE_DRAFT, reason="User wants to keep drafting.")

    return AgentPlan(action=AgentAction.GENERATE_BIBLE, reason="Defaulting to bible generation.")

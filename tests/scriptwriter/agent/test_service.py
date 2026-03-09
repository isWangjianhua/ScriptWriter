from scriptwriter.agent.models import AgentAction, AgentRequest
from scriptwriter.agent.service import plan_agent_action
from scriptwriter.workflow.models import ArtifactType, WorkflowStage, WorkflowState


def test_plans_bible_generation_for_new_project():
    request = AgentRequest(user_input="写一个悬疑剧项目", workflow_state=None)

    action = plan_agent_action(request)

    assert action.action is AgentAction.GENERATE_BIBLE


def test_plans_outline_generation_when_bible_has_been_approved():
    request = AgentRequest(
        user_input="确认这个 bible",
        workflow_state=WorkflowState(stage=WorkflowStage.PLANNING, current_artifact_type=ArtifactType.OUTLINE),
    )

    action = plan_agent_action(request)

    assert action.action is AgentAction.GENERATE_OUTLINE


def test_plans_artifact_confirmation_in_review_stage():
    request = AgentRequest(
        user_input="确认，继续",
        workflow_state=WorkflowState(stage=WorkflowStage.AWAITING_CONFIRMATION, current_artifact_type=ArtifactType.BIBLE),
    )

    action = plan_agent_action(request)

    assert action.action is AgentAction.CONFIRM_ARTIFACT


def test_plans_scene_rewrite_for_explicit_rewrite_request():
    request = AgentRequest(
        user_input="直接重写第三场戏，让冲突更强",
        workflow_state=WorkflowState(stage=WorkflowStage.COMPLETED, current_artifact_type=ArtifactType.DRAFT),
    )

    action = plan_agent_action(request)

    assert action.action is AgentAction.REWRITE_SCENE


def test_plans_continue_draft_when_user_requests_more_pages():
    request = AgentRequest(
        user_input="继续往下写",
        workflow_state=WorkflowState(stage=WorkflowStage.DRAFTING, current_artifact_type=ArtifactType.DRAFT),
    )

    action = plan_agent_action(request)

    assert action.action is AgentAction.CONTINUE_DRAFT

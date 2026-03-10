from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

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


class AgentPlanGraphState(TypedDict):
    request: AgentRequest
    route: str
    reason: str
    plan: AgentPlan


def _contains_token(user_input: str, lowered: str, tokens: tuple[str, ...]) -> bool:
    return any(token in user_input or token in lowered for token in tokens)


def _classify_route(request: AgentRequest) -> tuple[str, str]:
    user_input = request.user_input.strip()
    lowered = user_input.lower()
    workflow_state = request.workflow_state

    if workflow_state is None:
        return "generate_bible", "No workflow state exists yet."

    if _contains_token(user_input, lowered, _REWRITE_TOKENS):
        return "rewrite_scene", "User explicitly requested a rewrite."

    if workflow_state.stage is WorkflowStage.AWAITING_CONFIRMATION and _contains_token(user_input, lowered, _CONFIRM_TOKENS):
        return "confirm_artifact", "User approved the pending artifact."

    if workflow_state.stage is WorkflowStage.PLANNING and workflow_state.current_artifact_type is ArtifactType.OUTLINE:
        return "generate_outline", "Planning is currently targeting the outline."

    if workflow_state.stage is WorkflowStage.DRAFTING or _contains_token(user_input, lowered, _CONTINUE_TOKENS):
        return "continue_draft", "User wants to keep drafting."

    return "generate_bible", "Defaulting to bible generation."


def _node_classify(state: AgentPlanGraphState) -> dict[str, str]:
    route, reason = _classify_route(state["request"])
    return {"route": route, "reason": reason}


def _node_generate_bible(state: AgentPlanGraphState) -> dict[str, AgentPlan]:
    return {"plan": AgentPlan(action=AgentAction.GENERATE_BIBLE, reason=state["reason"])}


def _node_generate_outline(state: AgentPlanGraphState) -> dict[str, AgentPlan]:
    return {"plan": AgentPlan(action=AgentAction.GENERATE_OUTLINE, reason=state["reason"])}


def _node_confirm_artifact(state: AgentPlanGraphState) -> dict[str, AgentPlan]:
    return {"plan": AgentPlan(action=AgentAction.CONFIRM_ARTIFACT, reason=state["reason"])}


def _node_continue_draft(state: AgentPlanGraphState) -> dict[str, AgentPlan]:
    return {"plan": AgentPlan(action=AgentAction.CONTINUE_DRAFT, reason=state["reason"])}


def _node_rewrite_scene(state: AgentPlanGraphState) -> dict[str, AgentPlan]:
    return {"plan": AgentPlan(action=AgentAction.REWRITE_SCENE, reason=state["reason"])}


def _build_agent_plan_graph():
    graph = StateGraph(AgentPlanGraphState)
    graph.add_node("classify", _node_classify)
    graph.add_node("generate_bible", _node_generate_bible)
    graph.add_node("generate_outline", _node_generate_outline)
    graph.add_node("confirm_artifact", _node_confirm_artifact)
    graph.add_node("continue_draft", _node_continue_draft)
    graph.add_node("rewrite_scene", _node_rewrite_scene)

    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",
        lambda state: state["route"],
        {
            "generate_bible": "generate_bible",
            "generate_outline": "generate_outline",
            "confirm_artifact": "confirm_artifact",
            "continue_draft": "continue_draft",
            "rewrite_scene": "rewrite_scene",
        },
    )
    graph.add_edge("generate_bible", END)
    graph.add_edge("generate_outline", END)
    graph.add_edge("confirm_artifact", END)
    graph.add_edge("continue_draft", END)
    graph.add_edge("rewrite_scene", END)
    return graph.compile()


_AGENT_PLAN_GRAPH = _build_agent_plan_graph()


def plan_agent_action(request: AgentRequest) -> AgentPlan:
    result = _AGENT_PLAN_GRAPH.invoke({"request": request})
    plan = result.get("plan")
    if isinstance(plan, AgentPlan):
        return plan
    raise RuntimeError("Agent planning graph returned invalid result")

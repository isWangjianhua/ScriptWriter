from langchain_core.messages import HumanMessage

from scriptwriter.agents.lead_agent.orchestrator import run_lead_agent_flow
from scriptwriter.state_store.in_memory import InMemoryStateStore


def test_run_lead_agent_flow_converges():
    state = {
        "messages": [HumanMessage(content="Write a scene")],
        "user_id": "user_1",
        "project_id": "project_1",
        "thread_id": "thread_1",
        "thread_data": {},
        "revision_count": 0,
        "critic_notes": [],
        "plan": [],
        "current_draft": "",
        "artifacts": {},
    }

    store = InMemoryStateStore()
    result = run_lead_agent_flow(state, store=store)
    assert result.state["revision_count"] == 2
    assert result.state["current_draft"]
    assert result.state["plan"]
    assert result.run_id
    assert len(result.events) >= 4

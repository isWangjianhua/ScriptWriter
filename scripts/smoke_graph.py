from __future__ import annotations

import asyncio

from langchain_core.messages import HumanMessage

from scriptwriter.agents.lead_agent.orchestrator import run_lead_agent_flow


async def main() -> None:
    inputs = {
        "messages": [HumanMessage(content="Write a fight scene")],
        "user_id": "user_mnze",
        "project_id": "project_alpha",
        "thread_id": "thread_demo",
        "thread_data": {},
        "revision_count": 0,
        "critic_notes": [],
        "plan": [],
        "current_draft": "",
        "global_context": "",
        "episodic_memory": [],
        "artifacts": {},
    }

    out = await asyncio.to_thread(run_lead_agent_flow, inputs)
    if out.state.get("plan"):
        print("--- Planner Architecture Plan ---")
        print(out.state["plan"])
    if out.state.get("artifacts"):
        print("--- Artifacts ---")
        print(out.state["artifacts"])
    print("Orchestrator execution complete without exceptions.")


if __name__ == "__main__":
    asyncio.run(main())

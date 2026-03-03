import asyncio
from scriptwriter.agents.lead_agent.graph import compiled_graph
from langchain_core.messages import HumanMessage


async def main():
    config = {"configurable": {"thread_id": "test_thread_123", "user_id": "user_mnze"}}
    inputs = {
        "messages": [HumanMessage(content="Write a fight scene")],
        "user_id": "user_mnze",
        "project_id": "project_alpha",
        "revision_count": 0,
        "critic_notes": [],
        "plan": [],
        "current_draft": "",
    }

    # Use invoke to avoid Python 3.13 + langgraph async runtime issues.
    out = await asyncio.to_thread(compiled_graph.invoke, inputs, config)
    if "plan" in out:
        print("--- Planner Architecture Plan ---")
        print(out["plan"])
    if "artifacts" in out:
        print("--- Dynamic Skills Loaded ---")
        print(out["artifacts"].get("loaded_skills_debug"))
    print("Graph execution complete without exceptions.")


if __name__ == "__main__":
    asyncio.run(main())

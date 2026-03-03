import asyncio
from scriptwriter.workflow.graph import compiled_graph
from langchain_core.messages import HumanMessage

async def main():
    config = {"configurable": {"thread_id": "test_thread_123", "user_id": "user_mnze"}}
    inputs = {
        "messages": [HumanMessage(content="Write a fight scene")],
        "user_id": "user_mnze",
        "project_id": "project_alpha",
        "revision_count": 0,
        "critic_notes": [],
        "current_draft": ""
    }
    
    # Just running a smoke test to ensure there are no key errors down the line
    async for event in compiled_graph.astream_events(inputs, config, version="v2"):
        if event["event"] == "on_chain_end" and event["name"] == "writer_node":
            out = event["data"].get("output", {})
            if "artifacts" in out:
                print("--- Dynamic Skills Loaded ---")
                print(out["artifacts"].get("loaded_skills_debug"))
                print("--- Skill Payload Preview ---")
                print(out["artifacts"].get("skill_content_debug")[:100] + "...")
    print("Graph execution complete without exceptions.")

asyncio.run(main())

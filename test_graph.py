import asyncio
from app.workflow.graph import compiled_graph
from langchain_core.messages import HumanMessage

async def main():
    config = {"configurable": {"thread_id": "test_1"}}
    inputs = {"messages": [HumanMessage(content="Write a scene")], "project_id": "test_1", "revision_count": 0, "critic_notes": [], "current_draft": ""}
    
    async for event in compiled_graph.astream_events(inputs, config, version="v2"):
        print(event["event"], event["name"])

asyncio.run(main())

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import json
from app.workflow.graph import compiled_graph
from langchain_core.messages import HumanMessage

router = APIRouter()

@router.post("/api/chat")
async def chat_stream(request: Request):
    data = await request.json()
    user_input = data.get("message")
    tenant_id = data.get("tenant_id", "default_tenant")
    project_id = data.get("project_id", "default_project")
    
    async def event_generator():
        config = {
            "configurable": {
                # thread_id isolates conversational checkpoints for LangGraph memory
                "thread_id": f"{tenant_id}_{project_id}",
                # pass tenant_id into config to implicitly forward to backend Tools
                "tenant_id": tenant_id
            }
        }
        inputs = {
            "messages": [HumanMessage(content=user_input)], 
            "tenant_id": tenant_id,
            "project_id": project_id, 
            "revision_count": 0, 
            "critic_notes": [], 
            "current_draft": ""
        }
        
        async for event in compiled_graph.astream_events(inputs, config, version="v2"):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                if "chunk" in event["data"]:
                    chunk = event["data"]["chunk"].content
                    if chunk:
                        yield json.dumps({"type": "chat_chunk", "content": chunk}) + "\n"
            elif kind == "on_tool_start":
                yield json.dumps({"type": "tool_start", "name": event["name"]}) + "\n"
            elif kind == "on_chain_end" and event["name"] == "writer_node":
                out = event["data"].get("output", {})
                if "artifacts" in out:
                    yield json.dumps({"type": "canvas_update", "data": out["artifacts"]}) + "\n"
            elif kind == "on_chain_end" and event["name"] == "planner_node":
                out = event["data"].get("output", {})
                if "artifacts" in out:
                    yield json.dumps({"type": "canvas_update", "data": out["artifacts"]}) + "\n"
            elif kind == "on_chain_end" and event["name"] == "critic_node":
                out = event["data"].get("output", {})
                if "critic_notes" in out:
                    yield json.dumps({"type": "critic_note", "notes": out["critic_notes"]}) + "\n"
                    
    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

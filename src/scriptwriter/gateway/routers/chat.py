import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
from pydantic import BaseModel, StringConstraints
from scriptwriter.agents.lead_agent.orchestrator import recover_run_state, run_lead_agent_flow
from langchain_core.messages import HumanMessage
from scriptwriter.state_store.factory import get_state_store

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    user_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = "default_user"
    project_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = "default_project"
    thread_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None


@router.post("/api/chat")
async def chat_stream(payload: ChatRequest):
    async def event_generator():
        inputs = {
            "messages": [HumanMessage(content=payload.message)],
            "user_id": payload.user_id,
            "project_id": payload.project_id,
            "revision_count": 0,
            "critic_notes": [],
            "plan": [],
            "current_draft": "",
            "artifacts": {},
        }

        try:
            result = run_lead_agent_flow(inputs, store=get_state_store())
            yield json.dumps({"type": "run_started", "run_id": result.run_id, "session_id": result.session_id}) + "\n"

            plan = result.state.get("plan", [])
            if plan:
                yield json.dumps({"type": "canvas_update", "data": {"planner_breakdown": {"scenes": plan}}}) + "\n"

            artifacts = result.state.get("artifacts", {})
            if artifacts:
                yield json.dumps({"type": "canvas_update", "data": artifacts}) + "\n"

            draft = result.state.get("current_draft", "")
            if draft:
                yield json.dumps({"type": "chat_chunk", "content": draft}) + "\n"

            notes = result.state.get("critic_notes", [])
            if notes:
                yield json.dumps({"type": "critic_note", "notes": notes}) + "\n"
        except Exception:
            logger.exception("chat stream failed")
            yield json.dumps(
                {
                    "type": "error",
                    "error": {
                        "code": "GRAPH_STREAM_ERROR",
                        "message": "Failed to generate response.",
                    },
                }
            ) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


@router.get("/api/runs/{run_id}")
async def get_run_recovery(run_id: str):
    try:
        recovery = recover_run_state(run_id, store=get_state_store())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc

    return {
        "run_id": recovery.run.run_id,
        "session_id": recovery.run.session_id,
        "status": recovery.run.status,
        "state": recovery.state,
        "events": [
            {
                "seq_no": event.seq_no,
                "event_type": event.event_type,
                "agent_name": event.agent_name,
                "payload": event.payload,
            }
            for event in recovery.events
        ],
        "replay_from_seq": recovery.replay_from_seq,
        "replayed_events": [
            {
                "seq_no": event.seq_no,
                "event_type": event.event_type,
                "agent_name": event.agent_name,
                "payload": event.payload,
            }
            for event in recovery.replayed_events
        ],
    }

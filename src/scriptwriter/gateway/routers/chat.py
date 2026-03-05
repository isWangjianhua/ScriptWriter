from __future__ import annotations

import asyncio
import json
import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, StringConstraints

from scriptwriter.agents.lead_agent.orchestrator import recover_run_state, run_lead_agent_flow
from scriptwriter.gateway.paths import safe_thread_id
from scriptwriter.rag.service import ingest_knowledge_document
from scriptwriter.state_store.base import StateStore
from scriptwriter.state_store.factory import get_state_store

router = APIRouter(prefix="/api/threads/{thread_id}")
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    user_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    project_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    resume_run_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None


class KnowledgeIngestRequest(BaseModel):
    user_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    project_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    doc_type: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    path_l1: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    path_l2: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    content: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    doc_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None


def _validated_thread_id(thread_id: str) -> str:
    try:
        return safe_thread_id(thread_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _recover_scoped_or_raise(
    *,
    store: StateStore,
    run_id: str,
    thread_id: str,
    user_id: str,
    project_id: str,
):
    run_any = store.get_run(run_id)
    if run_any is None:
        raise HTTPException(status_code=404, detail="run not found")

    try:
        return recover_run_state(
            run_id,
            thread_id=thread_id,
            user_id=user_id,
            project_id=project_id,
            store=store,
        )
    except KeyError as exc:
        raise HTTPException(status_code=403, detail="forbidden") from exc


@router.post("/chat")
async def chat_stream(thread_id: str, payload: ChatRequest):
    safe_id = _validated_thread_id(thread_id)
    store = get_state_store()
    restored_state: dict[str, object] = {}

    if payload.resume_run_id:
        recovery = _recover_scoped_or_raise(
            store=store,
            run_id=payload.resume_run_id,
            thread_id=safe_id,
            user_id=payload.user_id,
            project_id=payload.project_id,
        )
        restored_state = recovery.state

    async def event_generator():
        inputs = {
            "messages": [HumanMessage(content=payload.message)],
            "user_id": payload.user_id,
            "project_id": payload.project_id,
            "thread_id": safe_id,
            "thread_data": {},
            "global_context": "",
            "episodic_memory": [],
            "revision_count": 0,
            "critic_notes": [],
            "plan": [],
            "current_draft": "",
            "artifacts": {},
        }

        if restored_state:
            inputs["global_context"] = restored_state.get("global_context", "")
            inputs["episodic_memory"] = restored_state.get("episodic_memory", [])
            inputs["plan"] = restored_state.get("plan", [])
            inputs["current_draft"] = restored_state.get("current_draft", "")
            inputs["artifacts"] = restored_state.get("artifacts", {})
            logger.info("Restored state from run_id %s", payload.resume_run_id)

        try:
            result = await asyncio.to_thread(run_lead_agent_flow, inputs, store)
            yield json.dumps(
                {
                    "type": "run_started",
                    "run_id": result.run_id,
                    "session_id": result.session_id,
                    "thread_id": safe_id,
                }
            ) + "\n"

            plan = result.state.get("plan", [])
            if plan:
                yield json.dumps(
                    {"type": "canvas_update", "data": {"planner_breakdown": {"scenes": plan}}}
                ) + "\n"

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


@router.post("/knowledge/ingest")
async def ingest_knowledge(thread_id: str, payload: KnowledgeIngestRequest):
    _validated_thread_id(thread_id)
    try:
        result = ingest_knowledge_document(
            user_id=payload.user_id,
            project_id=payload.project_id,
            content=payload.content,
            doc_type=payload.doc_type,
            title=payload.title,
            path_l1=payload.path_l1,
            path_l2=payload.path_l2,
            doc_id=payload.doc_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "doc_id": result.doc_id,
        "chunk_count": result.chunk_count,
        "source_path": result.source_path,
    }


@router.get("/runs/{run_id}")
async def get_run_recovery(
    thread_id: str,
    run_id: str,
    user_id: Annotated[str, Query(min_length=1)],
    project_id: Annotated[str, Query(min_length=1)],
):
    safe_id = _validated_thread_id(thread_id)
    recovery = _recover_scoped_or_raise(
        store=get_state_store(),
        run_id=run_id,
        thread_id=safe_id,
        user_id=user_id,
        project_id=project_id,
    )

    return {
        "run_id": recovery.run.run_id,
        "session_id": recovery.run.session_id,
        "thread_id": recovery.run.thread_id,
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

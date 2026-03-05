from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scriptwriter.agents.lead_agent.critic import critic_node
from scriptwriter.agents.lead_agent.planner import planner_node
from scriptwriter.agents.lead_agent.writer import writer_node
from scriptwriter.agents.thread_state import ScreenplayState
from scriptwriter.state_store.base import StateStore, StoredEvent, StoredRun
from scriptwriter.state_store.factory import get_state_store
from scriptwriter.state_store.serialization import deserialize_state, serialize_state


@dataclass(frozen=True)
class FlowResult:
    session_id: str
    run_id: str
    state: ScreenplayState
    events: list[StoredEvent]


@dataclass(frozen=True)
class RecoveryResult:
    run: StoredRun
    state: dict[str, Any]
    events: list[StoredEvent]
    replayed_events: list[StoredEvent]
    replay_from_seq: int


def _should_revise(state: ScreenplayState) -> bool:
    revision_count = state.get("revision_count", 0)
    notes = state.get("critic_notes", [])
    return revision_count > 0 and bool(notes) and revision_count < 2


def _apply_delta(state: dict[str, Any], delta: dict[str, Any]) -> None:
    for key, value in delta.items():
        state[key] = value


def _append_event_and_snapshot(
    *,
    store: StateStore,
    run_id: str,
    state: dict[str, Any],
    events: list[StoredEvent],
    event_type: str,
    agent_name: str,
    payload: dict[str, Any],
) -> StoredEvent:
    event = store.append_event(run_id, event_type, agent_name, payload)
    events.append(event)
    store.save_snapshot(run_id, event.seq_no, serialize_state(state))
    return event


def run_lead_agent_flow(initial_state: ScreenplayState, store: StateStore | None = None) -> FlowResult:
    store = store or get_state_store()
    state: ScreenplayState = dict(initial_state)

    messages = state.get("messages", [])
    input_message = messages[-1].content if messages else ""
    session_id = store.create_or_get_session(state["user_id"], state["project_id"])
    thread_id = str(state.get("thread_id", "")).strip()
    if not thread_id:
        raise ValueError("thread_id is required in state")
    run_id = store.create_run(session_id, thread_id, input_message)
    events: list[StoredEvent] = []

    _append_event_and_snapshot(
        store=store,
        run_id=run_id,
        state=state,
        events=events,
        event_type="run_started",
        agent_name="supervisor",
        payload={
            "thread_id": thread_id,
            "message": input_message,
            "user_id": state["user_id"],
            "project_id": state["project_id"],
        },
    )

    try:
        planner_delta = planner_node(state)
        _apply_delta(state, planner_delta)
        _append_event_and_snapshot(
            store=store,
            run_id=run_id,
            state=state,
            events=events,
            event_type="planner_completed",
            agent_name="planner",
            payload={"delta": serialize_state(planner_delta)},
        )

        while True:
            writer_delta = writer_node(state)
            _apply_delta(state, writer_delta)
            _append_event_and_snapshot(
                store=store,
                run_id=run_id,
                state=state,
                events=events,
                event_type="writer_draft_produced",
                agent_name="writer",
                payload={"delta": serialize_state(writer_delta)},
            )

            critic_delta = critic_node(state)
            _apply_delta(state, critic_delta)
            critic_event = _append_event_and_snapshot(
                store=store,
                run_id=run_id,
                state=state,
                events=events,
                event_type="critic_feedback_added",
                agent_name="critic",
                payload={"delta": serialize_state(critic_delta)},
            )
            if not _should_revise(state):
                store.mark_run_completed(run_id, current_step="completed")
                _append_event_and_snapshot(
                    store=store,
                    run_id=run_id,
                    state=state,
                    events=events,
                    event_type="run_completed",
                    agent_name="supervisor",
                    payload={"last_critic_seq": critic_event.seq_no},
                )
                break

            _append_event_and_snapshot(
                store=store,
                run_id=run_id,
                state=state,
                events=events,
                event_type="revision_requested",
                agent_name="supervisor",
                payload={"revision_count": state.get("revision_count", 0)},
            )
    except Exception as exc:
        store.mark_run_failed(run_id, error_code="ORCHESTRATION_ERROR", error_message=str(exc), current_step="failed")
        _append_event_and_snapshot(
            store=store,
            run_id=run_id,
            state=state,
            events=events,
            event_type="run_failed",
            agent_name="supervisor",
            payload={"error": str(exc)},
        )
        raise

    return FlowResult(session_id=session_id, run_id=run_id, state=state, events=events)


def recover_run_state(
    run_id: str,
    *,
    thread_id: str,
    user_id: str,
    project_id: str,
    store: StateStore | None = None,
) -> RecoveryResult:
    store = store or get_state_store()
    run = store.get_run_scoped(
        run_id=run_id,
        thread_id=thread_id,
        user_id=user_id,
        project_id=project_id,
    )
    if run is None:
        raise KeyError(run_id)

    all_events = store.get_events(run_id, after_seq_no=0)
    snapshot = store.get_latest_snapshot(run_id)
    if snapshot:
        state = deserialize_state(snapshot.state)
        replay_from_seq = snapshot.last_seq_no
    else:
        state = {}
        replay_from_seq = 0

    replayed_events = store.get_events(run_id, after_seq_no=replay_from_seq)
    for event in replayed_events:
        delta = event.payload.get("delta")
        if isinstance(delta, dict):
            _apply_delta(state, delta)

    return RecoveryResult(
        run=run,
        state=state,
        events=all_events,
        replayed_events=replayed_events,
        replay_from_seq=replay_from_seq,
    )

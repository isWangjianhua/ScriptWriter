from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from uuid import uuid4

from scriptwriter.state_store.base import StateStore, StoredEvent, StoredRun, StoredSnapshot


class InMemoryStateStore(StateStore):
    def __init__(self) -> None:
        self._session_by_scope: dict[tuple[str, str], str] = {}
        self._runs: dict[str, StoredRun] = {}
        self._events: dict[str, list[StoredEvent]] = {}
        self._snapshots: dict[str, StoredSnapshot] = {}

    def create_or_get_session(self, user_id: str, project_id: str) -> str:
        key = (user_id, project_id)
        if key not in self._session_by_scope:
            self._session_by_scope[key] = str(uuid4())
        return self._session_by_scope[key]

    def create_run(self, session_id: str, input_message: str) -> str:
        run_id = str(uuid4())
        self._runs[run_id] = StoredRun(
            run_id=run_id,
            session_id=session_id,
            input_message=input_message,
            status="RUNNING",
        )
        self._events[run_id] = []
        return run_id

    def append_event(
        self,
        run_id: str,
        event_type: str,
        agent_name: str,
        payload: dict,
    ) -> StoredEvent:
        events = self._events.setdefault(run_id, [])
        event = StoredEvent(
            run_id=run_id,
            seq_no=len(events) + 1,
            event_type=event_type,
            agent_name=agent_name,
            payload=deepcopy(payload),
        )
        events.append(event)
        return event

    def save_snapshot(self, run_id: str, last_seq_no: int, state: dict) -> None:
        self._snapshots[run_id] = StoredSnapshot(
            run_id=run_id,
            last_seq_no=last_seq_no,
            state=deepcopy(state),
        )

    def get_latest_snapshot(self, run_id: str) -> StoredSnapshot | None:
        snapshot = self._snapshots.get(run_id)
        return deepcopy(snapshot) if snapshot else None

    def get_events(self, run_id: str, after_seq_no: int = 0) -> list[StoredEvent]:
        events = self._events.get(run_id, [])
        return [deepcopy(event) for event in events if event.seq_no > after_seq_no]

    def get_run(self, run_id: str) -> StoredRun | None:
        run = self._runs.get(run_id)
        return deepcopy(run) if run else None

    def mark_run_completed(self, run_id: str, current_step: str | None = None) -> None:
        run = self._runs.get(run_id)
        if not run:
            return
        self._runs[run_id] = replace(run, status="COMPLETED", current_step=current_step)

    def mark_run_failed(
        self,
        run_id: str,
        error_code: str,
        error_message: str,
        current_step: str | None = None,
    ) -> None:
        run = self._runs.get(run_id)
        if not run:
            return
        self._runs[run_id] = replace(
            run,
            status="FAILED",
            current_step=current_step,
            error_code=error_code,
            error_message=error_message,
        )

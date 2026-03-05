from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class StoredEvent:
    run_id: str
    seq_no: int
    event_type: str
    agent_name: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class StoredSnapshot:
    run_id: str
    last_seq_no: int
    state: dict[str, Any]


@dataclass(frozen=True)
class StoredRun:
    run_id: str
    session_id: str
    thread_id: str
    input_message: str
    status: str
    current_step: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class StateStore(Protocol):
    def create_or_get_session(self, user_id: str, project_id: str) -> str: ...

    def create_run(self, session_id: str, thread_id: str, input_message: str) -> str: ...

    def append_event(
        self,
        run_id: str,
        event_type: str,
        agent_name: str,
        payload: dict[str, Any],
    ) -> StoredEvent: ...

    def save_snapshot(self, run_id: str, last_seq_no: int, state: dict[str, Any]) -> None: ...

    def get_latest_snapshot(self, run_id: str) -> StoredSnapshot | None: ...

    def get_events(self, run_id: str, after_seq_no: int = 0) -> list[StoredEvent]: ...

    def get_run(self, run_id: str) -> StoredRun | None: ...

    def get_run_scoped(
        self,
        run_id: str,
        thread_id: str,
        user_id: str,
        project_id: str,
    ) -> StoredRun | None: ...

    def mark_run_completed(self, run_id: str, current_step: str | None = None) -> None: ...

    def mark_run_failed(
        self,
        run_id: str,
        error_code: str,
        error_message: str,
        current_step: str | None = None,
    ) -> None: ...

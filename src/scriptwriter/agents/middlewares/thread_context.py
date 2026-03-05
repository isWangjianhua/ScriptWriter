from __future__ import annotations

from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langgraph.runtime import Runtime

from scriptwriter.agents.thread_state import ScreenplayState
from scriptwriter.gateway.paths import thread_dir


class ThreadContextMiddleware(AgentMiddleware[ScreenplayState]):
    """Ensure per-thread directory context is available in agent state."""

    def before_agent(self, state: ScreenplayState, runtime: Runtime) -> dict[str, Any] | None:
        thread_id = str(state.get("thread_id") or runtime.context.get("thread_id") or "").strip()
        if not thread_id:
            return None

        root = thread_dir(thread_id)
        thread_data = {
            "workspace_path": str((root / "workspace").resolve()),
            "uploads_path": str((root / "uploads").resolve()),
            "outputs_path": str((root / "outputs").resolve()),
        }
        return {"thread_data": thread_data}

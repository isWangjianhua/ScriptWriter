from __future__ import annotations

from typing import Any

from langgraph.runtime import Runtime

from scriptwriter.agents.middlewares.prompt_guard import PromptGuardMiddleware
from scriptwriter.agents.thread_state import ScreenplayState


class ScriptWriterMiddleware(PromptGuardMiddleware):
    """Compatibility wrapper around prompt/context guard + tool call tracing."""

    def __init__(self, inject_plan: bool = False, inject_draft: bool = False):
        super().__init__(inject_plan=inject_plan, inject_draft=inject_draft)

    def after_model(self, state: ScreenplayState, runtime: Runtime) -> dict[str, Any] | None:
        _ = runtime
        messages = state.get("messages", [])
        if not messages:
            return None

        last_msg = messages[-1]
        tool_calls = getattr(last_msg, "tool_calls", None)
        if tool_calls:
            artifacts = dict(state.get("artifacts", {}))
            recorded = list(artifacts.get("writer_tool_calls", []))
            for tool_call in tool_calls:
                recorded.append({"tool": tool_call["name"], "args": tool_call["args"]})
            artifacts["writer_tool_calls"] = recorded
            return {"artifacts": artifacts}

        return None

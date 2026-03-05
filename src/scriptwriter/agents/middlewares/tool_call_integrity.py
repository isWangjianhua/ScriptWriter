from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelCallResult, ModelRequest, ModelResponse
from langchain_core.messages import ToolMessage

from scriptwriter.agents.thread_state import ScreenplayState


class ToolCallIntegrityMiddleware(AgentMiddleware[ScreenplayState]):
    """Patch dangling tool calls to keep message history valid."""

    @staticmethod
    def _patch_messages(messages: list[Any]) -> list[Any] | None:
        existing_tool_ids = {
            msg.tool_call_id for msg in messages if isinstance(msg, ToolMessage) and msg.tool_call_id
        }

        needs_patch = False
        for msg in messages:
            if getattr(msg, "type", None) != "ai":
                continue
            for call in getattr(msg, "tool_calls", None) or []:
                call_id = call.get("id")
                if call_id and call_id not in existing_tool_ids:
                    needs_patch = True
                    break
            if needs_patch:
                break

        if not needs_patch:
            return None

        patched: list[Any] = []
        patched_ids: set[str] = set()
        for msg in messages:
            patched.append(msg)
            if getattr(msg, "type", None) != "ai":
                continue
            for call in getattr(msg, "tool_calls", None) or []:
                call_id = call.get("id")
                if call_id and call_id not in existing_tool_ids and call_id not in patched_ids:
                    patched.append(
                        ToolMessage(
                            content="[Tool call interrupted and no result was produced.]",
                            tool_call_id=call_id,
                            name=call.get("name", "unknown"),
                            status="error",
                        )
                    )
                    patched_ids.add(call_id)
        return patched

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelCallResult:
        patched = self._patch_messages(list(request.messages))
        if patched is not None:
            request = request.override(messages=patched)
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        patched = self._patch_messages(list(request.messages))
        if patched is not None:
            request = request.override(messages=patched)
        return await handler(request)

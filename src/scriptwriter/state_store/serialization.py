from __future__ import annotations

from typing import Any, Mapping

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


def _sanitize(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _sanitize(v) for k, v in value.items()}
    if hasattr(value, "content") and hasattr(value, "type"):
        return {"type": str(getattr(value, "type", "unknown")), "content": str(getattr(value, "content", ""))}
    return str(value)


def serialize_state(state: Mapping[str, Any]) -> dict[str, Any]:
    return _sanitize(dict(state))


def deserialize_state(state: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(state)
    raw_messages = data.get("messages", [])
    messages = []
    if isinstance(raw_messages, list):
        for item in raw_messages:
            if isinstance(item, dict):
                kind = str(item.get("type", "human"))
                content = str(item.get("content", ""))
                if kind == "ai":
                    messages.append(AIMessage(content=content))
                elif kind == "system":
                    messages.append(SystemMessage(content=content))
                else:
                    messages.append(HumanMessage(content=content))
    data["messages"] = messages
    return data

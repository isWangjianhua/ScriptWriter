from typing import Any

from langchain.agents import AgentState


class ScreenplayState(AgentState):
    user_id: str
    project_id: str
    thread_id: str
    thread_data: dict[str, str]

    # Core memory / global context (characters, world-building, etc.)
    global_context: str

    # Text state
    current_draft: str
    plan: list[dict[str, Any]]  # e.g. [{"id": 1, "desc": "intro", "status": "pending"}]

    # Episodic memory (for long-term historical context)
    episodic_memory: list[str]

    # Critic state
    critic_notes: list[str]
    revision_count: int

    # Payload for frontend UI
    artifacts: dict[str, Any]

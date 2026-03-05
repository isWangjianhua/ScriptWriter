from __future__ import annotations

from scriptwriter.agents.lead_agent.orchestrator import run_lead_agent_flow
from scriptwriter.agents.thread_state import ScreenplayState
from scriptwriter.state_store.base import StateStore


def invoke_flow(state: ScreenplayState, store: StateStore | None = None) -> ScreenplayState:
    """Compatibility shim that delegates to orchestrator-only execution."""
    return run_lead_agent_flow(state, store=store).state

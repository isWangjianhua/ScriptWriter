from __future__ import annotations

import logging
import os
from typing import Any, Literal

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from scriptwriter.agents.lead_agent.middleware import ScriptWriterMiddleware
from scriptwriter.agents.middlewares.thread_context import ThreadContextMiddleware
from scriptwriter.agents.middlewares.tool_call_integrity import ToolCallIntegrityMiddleware
from scriptwriter.agents.thread_state import ScreenplayState

logger = logging.getLogger(__name__)

_MAX_REVISIONS = 2


class CriticVerdict(BaseModel):
    verdict: Literal["approve", "revise"] = Field(
        ...,
        description=(
            "approve: the draft is solid and ready. "
            "revise: the draft needs another pass."
        ),
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Concrete actionable revision notes. Empty when verdict is approve.",
    )
    episode_summary: str = Field(
        default="",
        description=(
            "When verdict is approve, write a 2-3 sentence factual summary suitable for episodic memory."
        ),
    )


def _mock_verdict(revision_count: int) -> CriticVerdict:
    if revision_count < 2:
        return CriticVerdict(
            verdict="revise",
            notes=["Mock revision request to test the loop."],
        )
    return CriticVerdict(
        verdict="approve",
        episode_summary="[mock] The scene was reviewed and approved without modifications.",
    )


def critic_node(state: ScreenplayState, llm: Any = None) -> dict[str, Any]:
    revision_count = int(state.get("revision_count", 0))
    existing_notes = list(state.get("critic_notes", []))
    episodic_memory = list(state.get("episodic_memory", []))

    if revision_count >= _MAX_REVISIONS:
        logger.info("Revision cap reached (%d). Force-approving.", revision_count)
        summary = f"[auto-approved after {revision_count} revisions]"
        return {"episodic_memory": episodic_memory + [summary]}

    if not os.environ.get("OPENAI_API_KEY") and llm is None:
        verdict = _mock_verdict(revision_count)
    else:
        verdict = _call_agent_critic(state, llm)

    if verdict.verdict == "revise":
        logger.info(
            "Critic requested revision (%d/%d): %s",
            revision_count + 1,
            _MAX_REVISIONS,
            verdict.notes,
        )
        return {
            "critic_notes": existing_notes + verdict.notes,
            "revision_count": revision_count + 1,
        }

    if verdict.episode_summary:
        entry = f"[Draft {revision_count}] {verdict.episode_summary}"
        episodic_memory = episodic_memory + [entry]
        logger.info("Critic approved. Archived episodic memory entry.")

    return {
        "episodic_memory": episodic_memory,
        "artifacts": {
            **state.get("artifacts", {}),
            "critic_verdict": verdict.verdict,
            "critic_episode_summary": verdict.episode_summary,
        },
    }


def _call_agent_critic(state: ScreenplayState, llm: Any = None) -> CriticVerdict:
    if llm is None:
        model_name = os.getenv("SCRIPTWRITER_CRITIC_MODEL", "gpt-4o-mini")
        llm = ChatOpenAI(model=model_name, temperature=0.1)

    prior_notes = state.get("critic_notes", [])
    prior_notes_block = ""
    if prior_notes:
        prior_notes_block = "\n\n[PRIOR REVISION NOTES]\n" + "\n".join(
            f"- {note}" for note in prior_notes
        )

    from scriptwriter.agents.lead_agent.prompts import get_critic_prompt

    agent = create_agent(
        model=llm,
        middleware=[
            ThreadContextMiddleware(),
            ToolCallIntegrityMiddleware(),
            ScriptWriterMiddleware(inject_plan=True),
        ],
        system_prompt=get_critic_prompt() + prior_notes_block,
        response_format=CriticVerdict,
        state_schema=ScreenplayState,
    )

    try:
        user_msg = f"[DRAFT TO REVIEW]\n\n{state.get('current_draft', '')}"
        short_state = {**state, "messages": [HumanMessage(content=user_msg)]}
        result = agent.invoke(short_state)
        verdict: CriticVerdict | None = result.get("structured_response")
        if verdict is None:
            raise ValueError("Critic agent failed to produce verdict")
        return verdict
    except Exception:
        logger.exception("Critic agent failed; falling back to auto-approve.")
        return CriticVerdict(
            verdict="approve",
            episode_summary="[fallback] Critic agent failed; draft auto-approved.",
        )

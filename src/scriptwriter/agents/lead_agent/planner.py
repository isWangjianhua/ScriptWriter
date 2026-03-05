from __future__ import annotations

import logging
import os
from typing import Any

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from scriptwriter.agents.lead_agent.middleware import ScriptWriterMiddleware
from scriptwriter.agents.middlewares.thread_context import ThreadContextMiddleware
from scriptwriter.agents.middlewares.tool_call_integrity import ToolCallIntegrityMiddleware
from scriptwriter.agents.thread_state import ScreenplayState

logger = logging.getLogger(__name__)


class SceneTask(BaseModel):
    beat_number: int = Field(..., description="Chronological sequence number of the scene.")
    setting: str = Field(
        ...,
        description="INT./EXT. location and time of day, e.g. 'INT. COFFEE SHOP - DAY'.",
    )
    characters_involved: list[str] = Field(
        ...,
        description="Names of characters present in this scene.",
    )
    plot_beat: str = Field(
        ...,
        description="A 1-2 sentence description of what needs to happen in this scene.",
    )


class ScriptPlan(BaseModel):
    scenes: list[SceneTask] = Field(
        ...,
        description="The structured array of upcoming scenes to write.",
    )


def planner_node(state: ScreenplayState, llm: Any = None) -> dict[str, Any]:
    """The macro architect. Splits user intent into scene tasks."""
    messages = state.get("messages", [])
    user_input = messages[-1].content if messages else "A generic short scene."

    if not os.environ.get("OPENAI_API_KEY") and llm is None:
        logger.info("No OPENAI_API_KEY found; returning fallback plan.")
        fallback_plan = ScriptPlan(
            scenes=[
                SceneTask(
                    beat_number=1,
                    setting="INT. OFFICE - DAY",
                    characters_involved=["PROTAGONIST"],
                    plot_beat="Establishes the normal world of the protagonist.",
                )
            ]
        )
        ready_plan = fallback_plan.model_dump()
        return {
            "plan": ready_plan["scenes"],
            "artifacts": {"planner_breakdown": ready_plan},
        }

    if llm is None:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

    from scriptwriter.agents.lead_agent.prompts import get_planner_prompt

    agent = create_agent(
        model=llm,
        middleware=[
            ThreadContextMiddleware(),
            ToolCallIntegrityMiddleware(),
            ScriptWriterMiddleware(inject_draft=True),
        ],
        system_prompt=get_planner_prompt(),
        response_format=ScriptPlan,
        state_schema=ScreenplayState,
    )

    try:
        logger.info("Designing architecture for prompt: %s", str(user_input)[:50])
        result = agent.invoke(state)
        plan_obj: ScriptPlan | None = result.get("structured_response")
        if plan_obj is None:
            raise ValueError("Agent failed to produce structured plan")

        ready_plan = plan_obj.model_dump()
        return {
            **result,
            "plan": ready_plan.get("scenes", []),
            "artifacts": {
                **state.get("artifacts", {}),
                **result.get("artifacts", {}),
                "planner_breakdown": ready_plan,
            },
        }
    except Exception as exc:
        logger.exception("LLM decomposition failed")
        return {
            "plan": [],
            "artifacts": {
                **state.get("artifacts", {}),
                "planner_error": str(exc),
            },
        }

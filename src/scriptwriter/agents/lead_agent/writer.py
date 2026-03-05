from __future__ import annotations

import logging
import os
from typing import Any

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from scriptwriter.agents.lead_agent.middleware import ScriptWriterMiddleware
from scriptwriter.agents.middlewares.thread_context import ThreadContextMiddleware
from scriptwriter.agents.middlewares.tool_call_integrity import ToolCallIntegrityMiddleware
from scriptwriter.agents.thread_state import ScreenplayState
from scriptwriter.mcp.tools import get_cached_mcp_tools
from scriptwriter.tools.builtins.read_skill import read_skill
from scriptwriter.tools.builtins.search_bible import search_story_bible
from scriptwriter.tools.builtins.store_bible import save_story_bible
from scriptwriter.tools.builtins.web_search import search_web, search_web_hits

logger = logging.getLogger(__name__)

_HOT_TOPIC_PATTERNS = (
    "最新",
    "热点",
    "热搜",
    "今日",
    "今天",
    "实时",
    "最近",
    "breaking",
    "latest",
    "today",
    "news",
    "trend",
)


def _needs_web_search(user_input: str) -> bool:
    lowered = user_input.lower()
    return any(token in lowered for token in _HOT_TOPIC_PATTERNS)


def _render_web_context(raw_user_input: str) -> str:
    hits = search_web_hits(raw_user_input, max_results=5)
    if not hits:
        return ""
    return "\n".join(f"- {hit.title}: {hit.snippet} ({hit.url})" for hit in hits)


def writer_node(state: ScreenplayState, llm: Any = None) -> dict[str, Any]:
    messages = state.get("messages", [])
    user_input = messages[-1].content.lower() if messages else ""

    web_context = ""
    if _needs_web_search(user_input):
        raw_user_input = messages[-1].content if messages else ""
        web_context = _render_web_context(raw_user_input)

    from scriptwriter.agents.lead_agent.prompts import get_writer_prompt

    base_prompt = get_writer_prompt(web_context=web_context)
    mcp_tools = get_cached_mcp_tools()
    all_tools = [search_story_bible, save_story_bible, search_web, read_skill] + mcp_tools

    if not os.environ.get("OPENAI_API_KEY") and llm is None:
        logger.info("No OPENAI_API_KEY found; using mock writer.")
        new_draft = state.get("current_draft", "") + "\nINT. OFFICE - DAY\nJohn writes a script."
        return {
            "current_draft": new_draft,
            "artifacts": {
                **state.get("artifacts", {}),
                "scene_1": new_draft,
                "writer_mock": True,
                "mcp_tools_mounted_count": len(mcp_tools),
                "web_search_used": bool(web_context),
            },
        }

    if llm is None:
        model_name = os.getenv("SCRIPTWRITER_WRITER_MODEL", "gpt-4o")
        llm = ChatOpenAI(model=model_name, temperature=0.7)

    agent = create_agent(
        model=llm,
        tools=all_tools,
        middleware=[
            ThreadContextMiddleware(),
            ToolCallIntegrityMiddleware(),
            ScriptWriterMiddleware(inject_plan=True, inject_draft=True),
        ],
        system_prompt=base_prompt,
        state_schema=ScreenplayState,
    )

    config = {
        "configurable": {
            "user_id": state.get("user_id", ""),
            "project_id": state.get("project_id", ""),
            "thread_id": state.get("thread_id", ""),
        }
    }
    result = agent.invoke(state, config=config)

    final_messages = result.get("messages", [])
    new_draft = state.get("current_draft", "")
    if final_messages and hasattr(final_messages[-1], "content"):
        content = final_messages[-1].content
        if isinstance(content, str) and content.strip():
            new_draft = content.strip()

    merged_artifacts = {
        **state.get("artifacts", {}),
        **result.get("artifacts", {}),
        "scene_1": new_draft,
        "mcp_tools_mounted_count": len(mcp_tools),
        "web_search_used": bool(web_context),
        "web_context_debug": web_context,
    }

    return {
        **result,
        "current_draft": new_draft,
        "artifacts": merged_artifacts,
    }

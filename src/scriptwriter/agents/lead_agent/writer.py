from __future__ import annotations

import asyncio
import logging
import os
import re
from functools import lru_cache
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from scriptwriter.agents.thread_state import ScreenplayState
from scriptwriter.mcp.tools import get_mcp_tools
from scriptwriter.tools.builtins.search_bible import search_story_bible
from scriptwriter.tools.builtins.web_search import search_web, search_web_hits

logger = logging.getLogger(__name__)

_MAX_TOOL_ROUNDS = 3



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


def _extract_text_content(raw_content: Any) -> str:
    if isinstance(raw_content, str):
        return raw_content

    if isinstance(raw_content, list):
        blocks: list[str] = []
        for item in raw_content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    blocks.append(text)
            elif isinstance(item, str):
                blocks.append(item)
        return "\n".join(blocks).strip()

    return str(raw_content)


def _invoke_tool(
    *,
    tool_map: dict[str, Any],
    tool_name: str,
    tool_args: Any,
    user_id: str,
    project_id: str,
) -> str:
    tool = tool_map.get(tool_name)
    if tool is None:
        return f"Tool not found: {tool_name}"

    payload = tool_args if isinstance(tool_args, dict) else {}
    try:
        result = tool.invoke(payload, config={"configurable": {"user_id": user_id, "project_id": project_id}})
        return str(result)
    except TypeError:
        try:
            result = tool.invoke(payload)
            return str(result)
        except Exception as exc:
            return f"Tool '{tool_name}' failed: {str(exc)}"
    except Exception as exc:
        return f"Tool '{tool_name}' failed: {str(exc)}"


from langchain.agents import create_agent
from scriptwriter.agents.lead_agent.middleware import ScriptWriterMiddleware

def writer_node(state: ScreenplayState, llm: Any = None):
    """Generate screenplay content using the Agent factory."""
    messages = state.get("messages", [])
    user_input = messages[-1].content.lower() if messages else ""

    # 1. Add research context if needed
    web_context = ""
    if _needs_web_search(user_input):
        raw_user_input = messages[-1].content if messages else ""
        web_context = _render_web_context(raw_user_input)

    # 2. Finalize system prompt
    from scriptwriter.agents.lead_agent.prompts import get_writer_prompt
    base_prompt = get_writer_prompt(web_context=web_context)

    # 4. Resolve Tools
    try:
        asyncio.get_running_loop()
        mcp_tools: list[Any] = []
    except RuntimeError:
        mcp_tools = asyncio.run(get_mcp_tools())

    from scriptwriter.tools.builtins.store_bible import save_story_bible
    from scriptwriter.tools.builtins.read_skill import read_skill
    all_tools = [search_story_bible, save_story_bible, search_web, read_skill] + mcp_tools
    # 5. Build and execute Agent
    if not os.environ.get("OPENAI_API_KEY") and llm is None:
        logger.info("No OPENAI_API_KEY found, using mock writer.")
        new_draft = state.get("current_draft", "") + "\nINT. OFFICE - DAY\nJohn writes a script."
        return {
            "current_draft": new_draft,
            "artifacts": {
                **state.get("artifacts", {}),
                "scene_1": new_draft,
                "writer_mock": True
            },
        }

    if llm is None:
        model_name = os.getenv("SCRIPTWRITER_WRITER_MODEL", "gpt-4o")
        llm = ChatOpenAI(model=model_name, temperature=0.7)

    agent = create_agent(
        model=llm,
        tools=all_tools,
        middleware=[ScriptWriterMiddleware(inject_plan=True, inject_draft=True)],
        system_prompt=base_prompt,
        state_schema=ScreenplayState,
    )

    # The agent run inherits the state and returns the delta
    config = {"configurable": {
        "user_id": state.get("user_id", "default_user"),
        "project_id": state.get("project_id", "default_project")
    }}
    
    # We invoke the agent. It returns a dict with 'messages' and 'artifacts' etc.
    result = agent.invoke(state, config=config)
    
    # Extract the new draft from the last AIMessage content
    final_messages = result.get("messages", [])
    new_draft = state.get("current_draft", "")
    if final_messages and hasattr(final_messages[-1], "content"):
        content = final_messages[-1].content
        if isinstance(content, str) and content.strip():
            new_draft = content.strip()

    # Merge artifacts
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



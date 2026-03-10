from __future__ import annotations

from scriptwriter.agent.models import AgentAction


def build_bible_prompt(user_input: str) -> str:
    return f"Generate a story bible from this request:\n\n{user_input.strip()}"


def build_outline_prompt(user_input: str) -> str:
    return f"Generate an episode outline from this request:\n\n{user_input.strip()}"


def build_draft_prompt(user_input: str) -> str:
    return f"Continue or draft screenplay pages for this request:\n\n{user_input.strip()}"


def build_rewrite_prompt(user_input: str) -> str:
    return f"Rewrite the requested screenplay section using this instruction:\n\n{user_input.strip()}"


def build_prompt_for_action(action: AgentAction, user_input: str) -> str:
    if action is AgentAction.GENERATE_BIBLE:
        return build_bible_prompt(user_input)
    if action is AgentAction.GENERATE_OUTLINE:
        return build_outline_prompt(user_input)
    if action is AgentAction.REWRITE_SCENE:
        return build_rewrite_prompt(user_input)
    return build_draft_prompt(user_input)


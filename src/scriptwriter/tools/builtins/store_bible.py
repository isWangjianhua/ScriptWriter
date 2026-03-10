from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import tool

from scriptwriter.knowledge.service import ingest_knowledge_document


def _scope_from_config(config: RunnableConfig) -> tuple[str, str] | None:
    configurable = (config or {}).get("configurable", {})
    user_id = str(configurable.get("user_id", "")).strip()
    project_id = str(configurable.get("project_id", "")).strip()
    if not user_id or not project_id:
        return None
    return user_id, project_id


@tool
def save_story_bible(
    content: str,
    title: str,
    path_l1: str | None = None,
    path_l2: str | None = None,
    config: RunnableConfig = None,
) -> str:
    """Save newly established lore, rules, or character sheets to the story bible."""
    scope = _scope_from_config(config)
    if scope is None:
        return "Missing runtime scope: user_id and project_id are required."
    user_id, project_id = scope

    try:
        result = ingest_knowledge_document(
            user_id=user_id,
            project_id=project_id,
            content=content,
            doc_type="markdown",
            title=title,
            path_l1=path_l1,
            path_l2=path_l2,
        )
        return f"Successfully saved to story bible. Doc ID: {result.doc_id}"
    except Exception as exc:
        return f"Failed to save to story bible: {str(exc)}"


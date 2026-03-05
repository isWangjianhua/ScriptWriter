from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import tool

from scriptwriter.rag.service import KnowledgeHit, search_knowledge_hits


def _format_source(hit: KnowledgeHit) -> str:
    path_bits = [bit for bit in [hit.path_l1, hit.path_l2] if bit]
    path = "/".join(path_bits)
    label = path or hit.title or hit.doc_id or "unknown"
    if hit.chunk_order is not None:
        return f"{label}#chunk-{hit.chunk_order}"
    return label


def _scope_from_config(config: RunnableConfig) -> tuple[str, str] | None:
    configurable = (config or {}).get("configurable", {})
    user_id = str(configurable.get("user_id", "")).strip()
    project_id = str(configurable.get("project_id", "")).strip()
    if not user_id or not project_id:
        return None
    return user_id, project_id


@tool
def search_story_bible(
    query: str,
    path_l1: str | None = None,
    path_l2: str | None = None,
    config: RunnableConfig = None
) -> str:
    """Search story bible for character/rule/background context with citation hints.
    Use path_l1 and path_l2 to filter by document categories (e.g. path_l1="characters").
    """
    # Extract user_id/project_id from trusted runtime config to avoid prompt spoofing.
    scope = _scope_from_config(config)
    if scope is None:
        return "Missing runtime scope: user_id and project_id are required."
    user_id, project_id = scope

    try:
        hits = search_knowledge_hits(
            user_id=user_id,
            project_id=project_id,
            query=query,
            path_l1=path_l1,
            path_l2=path_l2,
            limit=3,
        )

        if not hits:
            return "No relevant information found."

        lines: list[str] = []
        for idx, hit in enumerate(hits, start=1):
            lines.append(f"{idx}. {hit.text}\n[source: {_format_source(hit)}]")

        return "\n\n".join(lines)
    except Exception as exc:
        return f"Knowledge base error or not initialized: {str(exc)}"

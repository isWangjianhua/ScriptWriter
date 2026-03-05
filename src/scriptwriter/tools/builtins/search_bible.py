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


@tool
def search_story_bible(
    query: str,
    path_l1: str | None = None,
    path_l2: str | None = None,
    config: RunnableConfig | None = None
) -> str:
    """Search story bible for character/rule/background context with citation hints.
    Use path_l1 and path_l2 to filter by document categories (e.g. path_l1="characters").
    """

    # We defensively extract user_id and project_id from the RunnableConfig context
    # so the LLM cannot spoof them via prompting.
    user_id = (config or {}).get("configurable", {}).get("user_id", "default_user")
    project_id = (config or {}).get("configurable", {}).get("project_id", "default_project")

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

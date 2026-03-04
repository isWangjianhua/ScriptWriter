from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import tool

from scriptwriter.rag.service import search_knowledge


@tool
def search_story_bible(project_id: str, query: str, config: RunnableConfig | None = None) -> str:
    """Search story bible for character/rule/background context."""

    # We defensively extract user_id from the RunnableConfig context
    # so the LLM cannot spoof the user_id via prompting!
    user_id = (config or {}).get("configurable", {}).get("user_id", "default_user")
    
    try:
        results = search_knowledge(
            user_id=user_id,
            project_id=project_id,
            query=query,
            limit=3,
        )
        
        if not results:
            return "No relevant information found."
        
        return "\n".join(results)
    except Exception as e:
        return f"Knowledge base error or not initialized: {str(e)}"

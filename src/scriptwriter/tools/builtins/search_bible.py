from langchain_core.tools import tool
from langchain_core.runnables.config import RunnableConfig
from scriptwriter.agents.memory.milvus_store import search_milvus_bible

# Example embedding function placeholder. In production, use SentenceTransformers or OpenAI embeddings
def get_mock_embedding(text: str) -> list[float]:
    """Generates a mock vector of 1536 dims just for MVP."""
    return [0.1] * 1536

@tool
def search_story_bible(project_id: str, query: str, config: RunnableConfig | None = None) -> str:
    """Useful to search for rules, character names, or backgrounds from the user's uploaded story bible."""
    
    # We defensively extract user_id from the RunnableConfig context 
    # so the LLM cannot spoof the user_id via prompting!
    user_id = (config or {}).get("configurable", {}).get("user_id", "default_user")
    
    try:
        # Convert query text into a vector
        query_vector = get_mock_embedding(query)
        
        # Pass vector to Milvus search along with user constraint
        results = search_milvus_bible(user_id, project_id, query_vector)
        
        if not results:
            return "No relevant information found."
        
        return "\n".join(results)
    except Exception as e:
        return f"Knowledge base error or not initialized: {str(e)}"

from langchain_core.tools import tool
from langchain_core.runnables.config import RunnableConfig
from app.memory.milvus_store import search_milvus_bible

# Example embedding function placeholder. In production, use SentenceTransformers or OpenAI embeddings
def get_mock_embedding(text: str) -> list[float]:
    """Generates a mock vector of 1536 dims just for MVP."""
    return [0.1] * 1536

@tool
def search_story_bible(project_id: str, query: str, config: RunnableConfig) -> str:
    """Useful to search for rules, character names, or backgrounds from the user's uploaded story bible."""
    
    # We defensively extract tenant_id from the RunnableConfig context 
    # so the LLM cannot spoof the tenant_id via prompting!
    tenant_id = config.get("configurable", {}).get("tenant_id", "default_tenant")
    
    try:
        # Convert query text into a vector
        query_vector = get_mock_embedding(query)
        
        # Pass vector to Milvus search along with tenant constraint
        results = search_milvus_bible(tenant_id, project_id, query_vector)
        
        if not results:
            return "No relevant information found."
        
        return "\n".join(results)
    except Exception as e:
        return f"Knowledge base error or not initialized: {str(e)}"

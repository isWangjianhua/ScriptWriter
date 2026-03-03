from typing import TypedDict, List, Dict, Any, Annotated
import operator
from langchain_core.messages import BaseMessage

class ScreenplayState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    tenant_id: str
    project_id: str
    
    # Text state
    current_draft: str
    
    # Critic state
    critic_notes: List[str]
    revision_count: int
    
    # Payload for Frontend UI
    artifacts: Dict[str, Any]

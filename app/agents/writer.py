from langchain_core.messages import AIMessage
from app.core.state import ScreenplayState

def writer_node(state: ScreenplayState):
    """Generates the screenplay content based on the plan and context."""
    # Dummy implementation for MVP to test the state graph
    
    current_draft = state.get("current_draft", "")
    new_draft = current_draft + " INT. ABANDONED FACTORY - DAY\nJohn looks around. "
    
    return {
        "current_draft": new_draft,
        "artifacts": {"scene_1": new_draft}
    }

from app.core.state import ScreenplayState

def planner_node(state: ScreenplayState):
    """The macro architect. Takes user input and splits it into tasks."""
    # For MVP, just prep a simple plan and push it
    notes = state.get("critic_notes", [])
    
    # We could simulate creating a plan queue here
    return {
        "artifacts": {"plan": "1. Set characters\n2. Write scene 1"}
    }

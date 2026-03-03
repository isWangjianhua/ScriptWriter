from scriptwriter.agents.thread_state import ScreenplayState

def critic_node(state: ScreenplayState):
    """Evaluates the draft and suggests revisions if necessary."""
    # Dummy implementation for MVP
    rev_count = state.get("revision_count", 0)
    current_draft = state.get("current_draft", "")
    
    notes = state.get("critic_notes", [])
    
    if rev_count < 2 and "John looks around." in current_draft:
        # Simulate rejection
        return {
            "critic_notes": notes + ["John shouldn't just look around, he needs to take action."],
            "revision_count": rev_count + 1,
            "current_draft": current_draft,
            "plan": state.get("plan", []),
        }
        
    return {
        "revision_count": rev_count,
        "critic_notes": notes,
        "current_draft": current_draft,
        "plan": state.get("plan", []),
    }

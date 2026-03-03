from langgraph.graph import StateGraph, END
from scriptwriter.core.state import ScreenplayState
from scriptwriter.agents.planner import planner_node
from scriptwriter.agents.writer import writer_node
from scriptwriter.agents.critic import critic_node

def should_revise(state: ScreenplayState):
    """Routing logic after critic."""
    if state.get("revision_count", 0) > 0 and state.get("critic_notes") and state.get("revision_count", 0) < 2:
        return "writer_node"
    return END

# Build Graph
builder = StateGraph(ScreenplayState)

# Add Nodes
builder.add_node("planner_node", planner_node)
builder.add_node("writer_node", writer_node)
builder.add_node("critic_node", critic_node)

# Add Edges
builder.set_entry_point("planner_node")
builder.add_edge("planner_node", "writer_node")
builder.add_edge("writer_node", "critic_node")
builder.add_conditional_edges("critic_node", should_revise)

compiled_graph = builder.compile()

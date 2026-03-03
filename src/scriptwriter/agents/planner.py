from scriptwriter.core.state import ScreenplayState

import os
import json
from pydantic import BaseModel, Field
from typing import List, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from scriptwriter.core.state import ScreenplayState

class SceneTask(BaseModel):
    beat_number: int = Field(..., description="Chronological sequence number of the scene.")
    setting: str = Field(..., description="INT./EXT. location and time of day, e.g., 'INT. COFFEE SHOP - DAY'.")
    characters_involved: List[str] = Field(..., description="Names of characters present in this scene.")
    plot_beat: str = Field(..., description="A 1-2 sentence description of what needs to happen in this scene.")

class ScriptPlan(BaseModel):
    scenes: List[SceneTask] = Field(..., description="The structured array of upcoming scenes to write.")

def planner_node(state: ScreenplayState):
    """The macro architect. Takes user input and splits it into discrete scene tasks."""
    messages = state.get("messages", [])
    user_input = messages[-1].content if messages else "A generic short scene."
    
    # We defensively check for API key. If none is found, we fall back to a mock to prevent 
    # crashing local tests and MVP pipelines where billing isn't set up yet.
    if not os.environ.get("OPENAI_API_KEY"):
        print("[Planner] No OPENAI_API_KEY found, returning fallback architectural plan.")
        fallback_plan = ScriptPlan(scenes=[
            SceneTask(
                beat_number=1, 
                setting="INT. OFFICE - DAY", 
                characters_involved=["PROTAGONIST"], 
                plot_beat="Establishes the normal world of the protagonist."
            )
        ])
        
        # We store the dictionary version of the plan into the State
        ready_plan = fallback_plan.model_dump()
        return {
            "plan": ready_plan["scenes"],
            "artifacts": {"planner_breakdown": ready_plan}
        }
    
    # True Production Mode (Supervisor Pattern)
    print(f"[Planner] Designing architecture for prompt: {user_input[:50]}...")
    
    sys_prompt = SystemMessage(content=(
        "You are the Lead Director / Showrunner. "
        "Your job is to take the user's premise and break it down into a sequence of distinct, "
        "manageable scene beats. Do not write the actual script, only provide the architectural blueprint."
    ))
    
    # Initialize LLM with strict JSON schema adherence
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2)
    structured_llm = llm.with_structured_output(ScriptPlan)
    
    try:
        plan: ScriptPlan = structured_llm.invoke([sys_prompt] + messages)
        ready_plan = plan.model_dump()
        return {
            "plan": ready_plan.get("scenes", []),
            "artifacts": {"planner_breakdown": ready_plan}
        }
    except Exception as e:
        print(f"[Planner] LLM decomposition failed: {e}")
        return {
            "plan": [],
            "artifacts": {"planner_error": str(e)}
        }

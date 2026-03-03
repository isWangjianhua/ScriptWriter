import os
from langchain_core.messages import AIMessage, SystemMessage
from app.core.state import ScreenplayState

def load_skill_context(skill_name: str) -> str:
    """Reads the Markdown skill file from disk to inject as context."""
    # Navigate from app/agents/writer.py -> app/agents -> app -> project_root -> skills
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    file_path = os.path.join(project_root, "skills", f"{skill_name}.md")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""

def writer_node(state: ScreenplayState):
    """Generates the screenplay content based on the plan and context."""
    messages = state.get("messages", [])
    user_input = messages[-1].content.lower() if messages else ""
    
    # Progressive Skill Loading (DeerFlow Architecture Concept)
    # Instead of a bloated 3000-word super prompt, we ONLY mount the skills needed.
    active_skills = ["hollywood_format"] # Always load base formatting
    
    if "fight" in user_input or "action" in user_input or "shoot" in user_input:
        active_skills.append("action_rules")
    if "talk" in user_input or "dialogue" in user_input or "say" in user_input:
        active_skills.append("dialogue_rules")
        
    skill_texts = [f"--- SKILL: {s} ---\n" + load_skill_context(s) for s in active_skills]
    compiled_skills = "\n\n".join(skill_texts)
    
    # In a real LLM call, this would be prepended as a SystemMessage
    # sys_msg = SystemMessage(content=f"You are an expert screenwriter.\n\n{compiled_skills}")
    
    current_draft = state.get("current_draft", "")
    new_draft = current_draft + " INT. ABANDONED FACTORY - DAY\nJohn looks around. "
    
    # We dump the loaded skills into artifacts just to visualize that the isolation worked!
    return {
        "current_draft": new_draft,
        "artifacts": {
            "scene_1": new_draft,
            "loaded_skills_debug": active_skills,
            "skill_content_debug": compiled_skills
        }
    }

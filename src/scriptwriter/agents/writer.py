import os
import re
from langchain_core.messages import AIMessage, SystemMessage
from scriptwriter.core.state import ScreenplayState

def load_skill_context(skill_name: str) -> str:
    """Reads the Markdown skill file from the DeerFlow-style directory structure and strips the yaml frontmatter."""
    # Navigate: src/scriptwriter/agents/writer.py -> src/scriptwriter/agents -> src/scriptwriter -> src -> project_root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    # We check in both public and custom categories like DeerFlow does
    for category in ["public", "custom"]:
        file_path = os.path.join(project_root, "skills", category, skill_name, "SKILL.md")
        if not os.path.exists(file_path):
            continue
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Parse YAML front matter using regex like DeerFlow parser.py
            front_matter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
            if front_matter_match:
                # Strip the frontmatter to only return the actual skill markdown payload to the LLM
                return content[front_matter_match.end():].strip()
            
            # If no frontmatter is found, just return the whole file
            return content.strip()
            
        except Exception as e:
            print(f"Error reading skill {skill_name}: {e}")
            
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

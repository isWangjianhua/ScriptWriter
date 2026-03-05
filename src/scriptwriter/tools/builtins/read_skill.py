import logging
import os

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

def _get_enabled_skills() -> list[dict[str, str]]:
    """Returns a list of dictionaries with 'name' and 'description' for available skills."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    skill_list = []
    
    for category in ["public", "custom"]:
        cat_dir = os.path.join(project_root, "skills", category)
        if not os.path.exists(cat_dir):
            continue
            
        for skill_name in os.listdir(cat_dir):
            skill_dir = os.path.join(cat_dir, skill_name)
            if os.path.isdir(skill_dir) and os.path.exists(os.path.join(skill_dir, "SKILL.md")):
                # Provide a generic description or try to read frontmatter (simplified here)
                skill_list.append({
                    "name": skill_name,
                    "description": f"Best practices and rules for {skill_name}"
                })
                
    return skill_list

@tool
def read_skill(skill_name: str) -> str:
    """Read the workflow rules and guidelines for a specific writing skill (e.g. hollywood_format).
    Call this tool PROACTIVELY to learn how to write a specific scene or use a formatting rule.
    """
    if "/" in skill_name or "\\" in skill_name or ".." in skill_name:
        return "Invalid skill name."

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    
    for category in ["public", "custom"]:
        file_path = os.path.join(project_root, "skills", category, skill_name, "SKILL.md")
        if os.path.exists(file_path):
            try:
                with open(file_path, encoding="utf-8") as fp:
                    return fp.read()
            except Exception as e:
                return f"Error reading skill {skill_name}: {e}"
                
    return f"Skill '{skill_name}' not found."

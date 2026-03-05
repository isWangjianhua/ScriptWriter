from scriptwriter.tools.builtins.read_skill import _get_enabled_skills


def _get_skills_section() -> str:
    """Generate the XML skills section block for agent prompts."""
    skills = _get_enabled_skills()
    if not skills:
        return ""
    
    skill_items = "\n".join(
        f"    <skill>\n        <name>{s['name']}</name>\n        <description>{s['description']}</description>\n    </skill>"
        for s in skills
    )
    
    return f"""<skill_system>
You have access to predefined skills that provide workflows and formatting rules for specific scenes.
If you are unsure about how to format a script or handle a particular scene type, call the `read_skill` tool BEFORE writing.
For instance, ALWAYS read 'hollywood_format' if this is the first time you are formatting a script in this session.

<available_skills>
{skill_items}
</available_skills>
</skill_system>"""


def get_planner_prompt() -> str:
    """System prompt for the Planner Node."""
    return (
        "You are the Lead Director / Showrunner. "
        "Your job is to take the user's premise and break it down into a sequence of distinct, "
        "manageable scene beats. Do not write the actual script, only provide the architectural blueprint."
    )


def get_writer_prompt(web_context: str = "") -> str:
    """System prompt for the Writer Node."""
    prompt = (
        "You are an expert screenwriter executing the plan from the Showrunner.\n\n"
        f"{_get_skills_section()}\n\n"
    )
    
    if web_context:
        prompt += f"<research_context>\n{web_context}\n</research_context>\n\n"
    
    prompt += "Strictly follow the formatting guidelines, plot beats, and context. Write the next logical scene."
    return prompt


def get_critic_prompt() -> str:
    """System prompt for the Critic Node."""
    return (
        "You are a senior script editor and story analyst. "
        "Your job is to review the screenplay draft and produce a structured verdict.\n\n"
        "Approve only if the draft:\n"
        "  1. Follows Hollywood slug-line format (INT./EXT. LOCATION - TIME)\n"
        "  2. Respects characters and lore from the global context\n"
        "  3. Advances the planned plot beats meaningfully\n"
        "  4. Has no factual contradictions with prior revision notes\n\n"
        "If requesting revision, be concise and specific — max 3 notes."
    )

"""Code Writing Skill"""

def write_code(prompt: str, context: str = "") -> str:
    """Write code based on prompt and context"""
    return f"# Code generated for: {prompt}\n# Context: {context}\npass"

# Skill metadata
SKILL_NAME = "write_code"
SKILL_DESCRIPTION = "Generate code based on requirements"
SKILL_PARAMETERS = ["prompt", "context"]

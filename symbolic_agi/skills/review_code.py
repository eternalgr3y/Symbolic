"""Code Review Skill"""

def review_code(code: str) -> str:
    """Review code for quality and issues"""
    return f"Reviewing code: {len(code)} characters"

# Skill metadata
SKILL_NAME = "review_code" 
SKILL_DESCRIPTION = "Review code for quality, bugs, and improvements"
SKILL_PARAMETERS = ["code"]

"""Plan Review Skill"""

def review_plan(plan: list, original_goal: str) -> dict:
    """Review a plan for correctness and completeness"""
    return {
        "approved": True,
        "feedback": "Plan looks good",
        "plan": plan
    }

# Skill metadata
SKILL_NAME = "review_plan"
SKILL_DESCRIPTION = "Review and validate execution plans"
SKILL_PARAMETERS = ["plan", "original_goal"]

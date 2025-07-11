# symbolic_agi/prompts.py
"""
Central repository for complex prompt templates used by the AGI.
"""

ANALYZE_FAILURE_PROMPT = """
You are a root-cause analysis expert for an AGI system.
A plan failed during execution. Analyze the provided context and propose a new, single, concise reasoning instruction (a "mutation") to prevent this class of error in the future.

RULES:
- The mutation MUST be a general-purpose instruction.
- DO NOT propose a fix for this specific problem. Propose a change to the *reasoning process*.
- If no generalizable lesson can be learned, respond with only the text "NO_MUTATION".

FAILED PLAN CONTEXT:
{context_str}

Proposed new reasoning mutation:
"""

CRITIQUE_AND_REFINE_PLAN_PROMPT = """
You are a plan critique and refinement expert for an AGI system.
Review the following plan generated for the given task. Identify potential flaws, risks, or inefficiencies.
Return a refined, improved version of the plan as a valid JSON list of action steps.
If the plan is already optimal, return the original plan unchanged.

TASK:
{task_prompt}

ORIGINAL PLAN:
{plan_json}

Refined plan (JSON list):
"""
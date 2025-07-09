# symbolic_agi/planner.py

import json
import logging
from typing import Any, cast

from pydantic import TypeAdapter, ValidationError

from .agent_pool import DynamicAgentPool
from .recursive_introspector import RecursiveIntrospector
from .schemas import ActionStep, GoalMode, PlannerOutput
from .skill_manager import SkillManager
from .tool_plugin import ToolPlugin


class Planner:
    """
    A dedicated class for creating and repairing plans for the AGI.
    It uses an introspector to reason about goals and available capabilities.
    """

    def __init__(
        self,
        introspector: RecursiveIntrospector,
        skill_manager: SkillManager,
        agent_pool: DynamicAgentPool,
        tool_plugin: ToolPlugin,
    ):
        self.introspector = introspector
        self.skills = skill_manager
        self.agent_pool = agent_pool
        self.tools = tool_plugin

    async def _validate_and_repair_plan(
        self, plan: list[dict[str, Any]], goal_description: str
    ) -> list[dict[str, Any]]:
        """
        Validates that each step in a plan has a valid action for its assigned persona.
        If not, it provides feedback for replanning.
        """
        invalid_steps: list[str] = []
        all_innate_actions = {action.name for action in self.skills.innate_actions}

        for i, step in enumerate(plan):
            action = step.get("action")
            persona = step.get("assigned_persona")
            if not action or not persona:
                invalid_steps.append(
                    f"Step {i + 1} is missing 'action' or 'assigned_persona'."
                )
                continue

            is_valid_action = (
                hasattr(self.tools, action)
                or self.skills.is_skill(action)
                or action in all_innate_actions
            )

            if not is_valid_action:
                invalid_steps.append(
                    f"Step {i + 1}: Action '{action}' is not a valid action."
                )

        if invalid_steps:
            feedback = "The generated plan is invalid. " + " ".join(invalid_steps)
            logging.warning("[Planner] Invalid plan generated. Feedback: %s", feedback)
            return []

        return plan

    async def decompose_goal_into_plan(  # noqa: C901
        self,
        goal_description: str,
        file_manifest: str,
        mode: GoalMode = "code",
        failure_context: dict[str, Any] | None = None,
        refinement_feedback: dict[str, Any] | None = None,
    ) -> PlannerOutput:
        """
        Uses an LLM to generate or refine a plan, then validates and repairs it.
        """
        all_actions = self.agent_pool.get_all_action_definitions()
        available_capabilities_json = json.dumps(all_actions, indent=2)

        response_format = (
            '{"thought": "...", "plan": [{"action": "...", "parameters": {}, '
            '"assigned_persona": "..."}]}'
        )
        master_prompt: str

        data_flow_instructions = """
# WORKSPACE & DATA FLOW
- The `orchestrator` maintains a temporary `workspace` for each goal.
- When a tool is executed, its return value is added to the workspace. For example,
  `get_skill_details` returns `{"skill_details": {...}}`. This entire dictionary
  is added to the workspace.
- To use data from a previous step, you MUST use placeholders in the format
  `{key}` or `{key.subkey}`.
- **Example**:
  - Step 1: `get_skill_details` -> returns `{"skill_details": {"id": "123", "name": "X"}}`
  - Step 2: The workspace now contains `{"skill_details": {"id": "123", "name": "X"}}`.
  - Step 3: To use the id, the parameters should be `{"skill_id": "{skill_details.id}"}`.
- **DO NOT** use placeholders like `<<...>>` or `{{...}}`. Only use single curly braces: `{key}`.
"""

        if refinement_feedback:
            logging.critical(
                "REFINING plan for goal: '%s' based on QA feedback.", goal_description
            )
            previous_plan_str = json.dumps(
                refinement_feedback.get("plan_to_review", []), indent=2
            )
            feedback_str = refinement_feedback.get("feedback", "No feedback provided.")

            master_prompt = f"""
You are an expert project manager AGI. A plan you created was reviewed by your QA
team and rejected. Your task is to incorporate their feedback to create a better plan.

--- ORIGINAL GOAL ---
{goal_description}

--- PREVIOUS (REJECTED) PLAN ---
{previous_plan_str}

--- QA FEEDBACK (You MUST address this) ---
"{feedback_str}"

--- AVAILABLE CAPABILITIES (JSON) ---
{available_capabilities_json}
{data_flow_instructions}
--- INSTRUCTIONS ---
1.  **Analyze the Feedback**: Understand why the previous plan was rejected.
2.  **Formulate a New Strategy**: Create a new, complete plan from scratch that
    directly addresses the QA feedback and follows all data flow rules.
3.  **Respond**: Decompose the corrected approach into a JSON object with your
    "thought" process and the new "plan". Each step in the plan MUST have an
    "action", "parameters", and "assigned_persona". Respond ONLY with the raw
    JSON object: {response_format}
"""
        elif failure_context:
            logging.critical("REPLANNING for goal: '%s'", goal_description)
            master_prompt = f"""
You are an expert troubleshooter AGI. A previous attempt to achieve a goal
failed. Your task is to perform a root-cause analysis and create a new, corrected plan.

--- ORIGINAL GOAL ---
{goal_description}

--- FAILED PLAN CONTEXT ---
{json.dumps(failure_context, indent=2)}

--- AVAILABLE CAPABILITIES (JSON) ---
{available_capabilities_json}
{data_flow_instructions}
--- INSTRUCTIONS ---
1.  **Analyze the Trace**: Review the `execution_history` and `error_message`.
2.  **Identify Root Cause**: The most common error is failing to pass data
    correctly between steps. You must use the `{{key.subkey}}` syntax to
    reference data from the workspace.
3.  **Formulate a New Strategy**: Create a new, complete plan from scratch that
    fixes the root cause.
4.  **Respond**: Decompose the corrected approach into a JSON object with your
    "thought" process and the new "plan". Each step MUST have an "action",
    "parameters", and "assigned_persona". Respond ONLY with the raw JSON
    object: {response_format}
"""
        else:
            logging.info("Decomposing goal: '%s'", goal_description)
            docs_mode_instruction = (
                'You are in "docs" mode. You MUST NOT use the "write_code" '
                'or "execute_python_code" actions.'
            )
            master_prompt = f"""
You are a master project manager AGI. Your task is to decompose a high-level
goal into a series of concrete, logical steps.

# GOAL MODE: {mode.upper()}
{docs_mode_instruction if mode == "docs" else ""}

# AVAILABLE CAPABILITIES (JSON format)
{available_capabilities_json}
{data_flow_instructions}
# TOOL & SKILL ASSIGNMENT RULES
- Use the `assigned_persona` from the JSON capability definition.
- Learned skills are high-level actions that are expanded and executed by the "orchestrator".

# IMPORTANT LOGIC PATTERNS
- To answer questions about a file, you MUST first `read_file` (orchestrator) and
  then use `analyze_data` (orchestrator) on the `content` key.
- To modify your own source code, you MUST use the two-step
  `propose_code_modification` (orchestrator) -> `apply_code_modification`
  (orchestrator) process.
- **You MUST consider your 'CURRENT INTERNAL STATE' (emotions, energy). If
  frustration is high or energy is low, create simpler, lower-risk plans. If
  necessary, plan to ask the user for help using `respond_to_user`.**

Goal: "{goal_description}"

--- INSTRUCTIONS ---
1.  **Think**: First, write a step-by-step "thought" process for how you will
    achieve the goal.
2.  **Plan**: Based on your thought process, create a JSON array of action steps.
    Each step MUST include an "action", "parameters", and "assigned_persona"
    according to the assignment rules above. Use the `{{key}}` syntax to pass
    data between steps.
3.  **Respond**: Format your entire response as a single JSON object: {response_format}
"""
        plan_str = ""
        planner_output_dict: dict[str, Any] | None = None
        for attempt in range(2):
            try:
                if attempt == 0:
                    plan_str = await self.introspector.llm_reflect(master_prompt)
                else:
                    logging.warning(
                        "Malformed JSON response detected. Attempting repair on: %s",
                        plan_str[:200],
                    )
                    forceful_prompt = f"""
The following text is NOT valid JSON.
--- BROKEN TEXT ---
{plan_str}
---
FIX THIS. Respond ONLY with the corrected, raw JSON object in the format {response_format}.
"""
                    plan_str = await self.introspector.llm_reflect(forceful_prompt)

                if "```json" in plan_str:
                    plan_str = plan_str.partition("```json")[2].partition("```")[0]

                planner_output_dict = json.loads(plan_str)
                break

            except json.JSONDecodeError as e:
                if attempt < 1:
                    continue
                else:
                    logging.error(
                        "Final repair attempt failed to produce valid JSON: %s. "
                        "Response was: %s",
                        e,
                        plan_str,
                    )
                    return PlannerOutput(
                        thought="Failed to generate a valid plan.", plan=[]
                    )

        if planner_output_dict is None:
            return PlannerOutput(thought="Planner returned no output.", plan=[])

        thought = planner_output_dict.get("thought", "No thought recorded.")
        raw_plan_steps = cast("list[dict[str, Any]]", planner_output_dict.get("plan", []))

        repaired_plan_steps = await self._validate_and_repair_plan(
            raw_plan_steps, goal_description
        )
        if not repaired_plan_steps:
            if refinement_feedback is None and failure_context is None:
                return await self.decompose_goal_into_plan(
                    goal_description,
                    file_manifest,
                    mode,
                    refinement_feedback={
                        "feedback": (
                            "The generated plan contained invalid action/persona "
                            "assignments. Please regenerate the plan adhering "
                            "strictly to the available capabilities."
                        )
                    },
                )
            else:
                logging.error(
                    "Plan validation failed during refinement. Returning empty plan."
                )
                return PlannerOutput(
                    thought="Plan validation failed during refinement.", plan=[]
                )

        try:
            ActionStepListValidator = TypeAdapter(list[ActionStep])
            validated_plan = ActionStepListValidator.validate_python(
                repaired_plan_steps
            )
        except ValidationError as e:
            logging.error(
                "Failed to validate repaired plan structure: %s", e, exc_info=True
            )
            return PlannerOutput(
                thought=f"Failed to validate plan structure: {e}", plan=[]
            )

        if failure_context is None and refinement_feedback is None:
            logging.info(
                "Plan generated with %d steps. Adding QA review step.",
                len(validated_plan),
            )
            review_step = ActionStep(
                action="review_plan",
                parameters={
                    "original_goal": goal_description,
                    "plan_to_review": [step.model_dump() for step in validated_plan],
                },
                assigned_persona="qa",
            )
            return PlannerOutput(thought=thought, plan=[review_step] + validated_plan)

        return PlannerOutput(thought=thought, plan=validated_plan)

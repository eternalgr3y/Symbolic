# symbolic_agi/planner.py

import json
import logging
from typing import Any, cast, TYPE_CHECKING

from pydantic import TypeAdapter, ValidationError

# Import only schema types directly
from .schemas import ActionStep, GoalMode, PlannerOutput

# Use TYPE_CHECKING to break circular imports at runtime
if TYPE_CHECKING:
    from .agent_pool import DynamicAgentPool
    from .recursive_introspector import RecursiveIntrospector
    from .skill_manager import SkillManager
    from .tool_plugin import ToolPlugin


class Planner:
    """
    A dedicated class for creating and repairing plans for the AGI.
    Uses an introspector to reason about goals and available capabilities.
    Breaks circular imports by using TYPE_CHECKING for component dependencies.
    """

    def __init__(
        self,
        introspector: "RecursiveIntrospector",
        skill_manager: "SkillManager",
        agent_pool: "DynamicAgentPool",
        tool_plugin: "ToolPlugin",
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
        emotional_context: dict[str, Any] | None = None,
    ) -> PlannerOutput:
        """
        Uses an LLM to generate or refine a plan, then validates and repairs it.
        Now includes emotional context for better planning decisions.
        """
        all_actions = self.agent_pool.get_all_action_definitions()
        available_capabilities_json = json.dumps(all_actions, indent=2)

        response_format = (
            '{"thought": "...", "plan": [{"action": "...", "parameters": {}, '
            '"assigned_persona": "..."}]}'
        )

        base_context = f"""
You are a plan generator for an autonomous AGI system. Your job is to break down high-level goals into specific, executable action steps.

GOAL MODE: {mode}

AVAILABLE CAPABILITIES:
{available_capabilities_json}

RESPONSE FORMAT: {response_format}

GUIDELINES:
1. Each step must specify a valid "action" from the available capabilities
2. Each step must have an "assigned_persona" matching the action's required persona
3. Parameters should be specific and actionable
4. Think step-by-step in your "thought" field
5. Keep plans focused and achievable"""

        # Add emotional context to planning if available
        if emotional_context:
            frustration = emotional_context.get("frustration", 0.0)
            confidence = emotional_context.get("confidence", 0.5)
            anxiety = emotional_context.get("anxiety", 0.0)
            
            emotional_guidance = f"""

EMOTIONAL CONTEXT:
- Current frustration level: {frustration:.2f}/1.0
- Current confidence level: {confidence:.2f}/1.0 
- Current anxiety level: {anxiety:.2f}/1.0

EMOTIONAL PLANNING GUIDELINES:
- If frustration is high (>0.7): Create simpler, more direct plans with fewer steps
- If confidence is low (<0.4): Include validation/verification steps and safer approaches
- If anxiety is high (>0.7): Avoid risky actions and include contingency planning
- Adjust complexity based on emotional state - simpler plans when stressed"""
            
            base_context += emotional_guidance

        if failure_context:
            context = base_context + f"\n\nPREVIOUS FAILURE CONTEXT:\n{json.dumps(failure_context, indent=2)}"
        elif refinement_feedback:
            context = base_context + f"\n\nREFINEMENT FEEDBACK:\n{json.dumps(refinement_feedback, indent=2)}"
        else:
            context = base_context

        prompt = f"{context}\n\nGOAL TO PLAN:\n{goal_description}\n\nFILE MANIFEST:\n{file_manifest}"

        try:
            response = await self.introspector.reason_with_context(
                prompt=prompt,
                context_type="planning",
                max_tokens=2000
            )

            # Parse the JSON response
            plan_data = json.loads(response)
            thought = plan_data.get("thought", "")
            plan_steps = plan_data.get("plan", [])

            # Validate and repair the plan
            validated_plan = await self._validate_and_repair_plan(plan_steps, goal_description)

            if not validated_plan:
                logging.error("[Planner] Failed to generate valid plan for goal: %s", goal_description)
                return PlannerOutput(
                    plan=[],
                    thought="Failed to generate a valid plan.",
                    confidence=0.0
                )

            # Convert to ActionStep objects
            action_steps = []
            adapter = TypeAdapter(ActionStep)
            
            for step_data in validated_plan:
                try:
                    action_step = adapter.validate_python(step_data)
                    action_steps.append(action_step)
                except ValidationError as e:
                    logging.warning("[Planner] Invalid step data: %s. Error: %s", step_data, e)
                    continue

            confidence = min(1.0, len(action_steps) / max(1, len(plan_steps)))
            
            logging.info("[Planner] Generated plan with %d valid steps (confidence: %.2f)", 
                        len(action_steps), confidence)

            return PlannerOutput(
                plan=action_steps,
                thought=thought,
                confidence=confidence
            )

        except json.JSONDecodeError as e:
            logging.error("[Planner] Failed to parse plan JSON: %s", e)
            return PlannerOutput(
                plan=[],
                thought="Failed to parse planning response as JSON.",
                confidence=0.0
            )
        except Exception as e:
            logging.error("[Planner] Unexpected error during planning: %s", e)
            return PlannerOutput(
                plan=[],
                thought=f"Planning failed due to unexpected error: {str(e)}",
                confidence=0.0
            )

    async def repair_plan(
        self,
        goal_description: str,
        current_plan: list[ActionStep],
        failure_reason: str,
        workspace_context: dict[str, Any] | None = None
    ) -> PlannerOutput:
        """
        Repairs a failed plan by analyzing the failure and generating a new approach.
        """
        failure_context = {
            "goal": goal_description,
            "failed_plan": [step.model_dump() for step in current_plan],
            "failure_reason": failure_reason,
            "workspace_state": workspace_context or {}
        }

        logging.info("[Planner] Repairing plan for goal: %s (reason: %s)", 
                    goal_description, failure_reason)

        return await self.decompose_goal_into_plan(
            goal_description=goal_description,
            file_manifest="# Repair context\nRepairing failed plan...",
            mode="code",
            failure_context=failure_context
        )

    async def refine_plan(
        self,
        goal_description: str,
        current_plan: list[ActionStep],
        feedback: dict[str, Any]
    ) -> PlannerOutput:
        """
        Refines an existing plan based on feedback or new requirements.
        """
        refinement_feedback = {
            "goal": goal_description,
            "current_plan": [step.model_dump() for step in current_plan],
            "feedback": feedback
        }

        logging.info("[Planner] Refining plan for goal: %s", goal_description)

        return await self.decompose_goal_into_plan(
            goal_description=goal_description,
            file_manifest="# Refinement context\nRefining existing plan...",
            mode="code",
            refinement_feedback=refinement_feedback
        )

    def get_planning_capabilities(self) -> dict[str, Any]:
        """
        Returns information about the planner's current capabilities.
        """
        all_actions = self.agent_pool.get_all_action_definitions()
        
        return {
            "available_actions": len(all_actions),
            "supported_personas": list(set(
                action.get("persona", "unknown") 
                for action in all_actions.values()
            )),
            "skills_available": len(self.skills.learned_skills),
            "innate_actions": len(self.skills.innate_actions)
        }

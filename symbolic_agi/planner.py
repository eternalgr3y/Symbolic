# symbolic_agi/planner.py
import json
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .api_client import client, monitored_chat_completion
from .schemas import ActionStep, PlannerOutput

if TYPE_CHECKING:
    from .agent_pool import DynamicAgentPool
    from .recursive_introspector import RecursiveIntrospector
    from .skill_manager import SkillManager
    from .tool_plugin import ToolPlugin

class Planner:
    """Creates executable plans from high-level goals."""
    
    def __init__(
        self,
        tools: "ToolPlugin",
        agent_pool: "DynamicAgentPool",
        skills: "SkillManager",
        introspector: "RecursiveIntrospector"
    ):
        self.tools = tools
        self.agent_pool = agent_pool
        self.skills = skills
        self.introspector = introspector

    async def create_plan(self, goal_description: str) -> Optional[PlannerOutput]:
        """Create a plan to achieve the given goal."""
        try:
            # Get available actions
            all_actions = self.skills.get_all_actions()
            
            # Format actions for prompt
            actions_desc = []
            for name, action in all_actions.items():
                params = [f"{p.name}: {p.type}" for p in action.parameters]
                actions_desc.append(f"- {name}({', '.join(params)}): {action.description}")
            
            actions_text = "\n".join(actions_desc)
            
            prompt = f"""You are a planning module for an AGI system. Create a detailed plan to achieve the following goal:

Goal: {goal_description}

Available Actions:
{actions_text}

Create a step-by-step plan using the available actions. Return a JSON object with:
- "thought": Your reasoning about how to achieve the goal
- "plan": An array of action steps, each with:
  - "action": The action name
  - "parameters": Object with parameter values
  - "expected_outcome": What this step should achieve
  - "reasoning": Why this step is necessary

Be specific and use only the available actions."""

            response = await monitored_chat_completion(
                client,
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a planning AI that creates executable plans."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=2000
            )
            
            # Parse response
            plan_data = json.loads(response.choices[0].message.content)
            
            # Convert to ActionStep objects
            steps = []
            for step_data in plan_data.get("plan", []):
                steps.append(ActionStep(
                    action=step_data["action"],
                    parameters=step_data.get("parameters", {}),
                    expected_outcome=step_data.get("expected_outcome"),
                    reasoning=step_data.get("reasoning")
                ))
            
            return PlannerOutput(
                thought=plan_data.get("thought", ""),
                plan=steps
            )
            
        except Exception as e:
            logging.error(f"[Planner] Error creating plan: {e}")
            return None

    async def refine_plan(
        self,
        original_plan: List[ActionStep],
        feedback: str
    ) -> Optional[List[ActionStep]]:
        """Refine a plan based on feedback."""
        try:
            plan_text = json.dumps([{
                "action": step.action,
                "parameters": step.parameters,
                "expected_outcome": step.expected_outcome,
                "reasoning": step.reasoning
            } for step in original_plan], indent=2)
            
            prompt = f"""Refine the following plan based on the feedback:

Original Plan:
{plan_text}

Feedback:
{feedback}

Provide an improved plan that addresses the feedback. Return a JSON array of action steps."""

            response = await monitored_chat_completion(
                client,
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a planning AI that refines plans based on feedback."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=2000
            )
            
            # Parse response
            refined_data = json.loads(response.choices[0].message.content)
            
            steps = []
            for step_data in refined_data.get("plan", []):
                steps.append(ActionStep(
                    action=step_data["action"],
                    parameters=step_data.get("parameters", {}),
                    expected_outcome=step_data.get("expected_outcome"),
                    reasoning=step_data.get("reasoning")
                ))
            
            return steps
            
        except Exception as e:
            logging.error(f"[Planner] Error refining plan: {e}")
            return None
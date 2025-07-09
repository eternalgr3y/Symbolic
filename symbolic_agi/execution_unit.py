# symbolic_agi/execution_unit.py

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from . import metrics
from .schemas import ActionStep, ExecutionStepRecord

if TYPE_CHECKING:
    from .agi_controller import SymbolicAGI


class ExecutionUnit:
    """
    Handles the active execution of goals, including planning, delegation,
    failure handling, and reflection.
    """

    agi: "SymbolicAGI"

    def __init__(self, agi: "SymbolicAGI"):
        self.agi = agi
        self._skill_expansion_history: Dict[str, List[str]] = {}

    def _resolve_workspace_references(
        self, parameters: Dict[str, Any], workspace: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recursively resolves placeholder strings like '{key.subkey}' from the workspace.
        """

        def _resolve_value(value_to_resolve: Any) -> Any:
            if (
                isinstance(value_to_resolve, str)
                and value_to_resolve.startswith("{")
                and value_to_resolve.endswith("}")
            ):
                placeholder = value_to_resolve.strip("{}")
                try:
                    current_val: Any = workspace
                    for k in placeholder.split("."):
                        current_val = current_val[k]
                    logging.debug(
                        "Resolved workspace reference '{{{}}}' to value.", placeholder
                    )
                    return current_val
                except (KeyError, TypeError) as e:
                    logging.warning(
                        "Could not resolve '{{{}}}' in workspace: %s. Leaving as is.",
                        placeholder,
                        e,
                    )
            return value_to_resolve

        resolved_params: Dict[str, Any] = {}
        for key, value in parameters.items():
            if isinstance(value, dict):
                resolved_params[key] = self._resolve_workspace_references(
                    cast(Dict[str, Any], value), workspace
                )
            elif isinstance(value, list):
                resolved_list: List[Any] = []
                for item in value:
                    if isinstance(item, dict):
                        resolved_list.append(
                            self._resolve_workspace_references(
                                cast(Dict[str, Any], item), workspace
                            )
                        )
                    else:
                        resolved_list.append(_resolve_value(item))
                resolved_params[key] = resolved_list
            else:
                resolved_params[key] = _resolve_value(value)
        return resolved_params

    async def handle_autonomous_cycle(self) -> Dict[str, Any]:  # noqa: C901
        """The main execution loop for the orchestrator to process the active goal."""
        with metrics.AGI_CYCLE_DURATION.time():
            if self.agi.perception_buffer:
                interrupted = await self._reflect_on_perceptions()
                if interrupted:
                    return {
                        "description": (
                            "*Perception caused an interruption. "
                            "Re-evaluating priorities.*"
                        )
                    }

            active_goal = self.agi.ltm.get_active_goal()

            if not active_goal:
                logging.info(
                    "[Drive Loop] No active goal. Consulting meta-cognition "
                    "to generate one."
                )
                await self.agi.meta_cognition.generate_goal_from_drives()
                active_goal = self.agi.ltm.get_active_goal()
                if not active_goal:
                    return {
                        "description": (
                            "*Orchestrator is idle. No active goals and no "
                            "strong drives to generate one.*"
                        )
                    }
                return {
                    "description": (
                        f"*New autonomous goal generated: '{active_goal.description}'. "
                        "Beginning execution.*"
                    )
                }

            if not active_goal.sub_tasks:
                plan = await self._classify_and_generate_initial_plan(active_goal)
                if not plan:
                    self.agi.ltm.invalidate_plan(
                        active_goal.id, "Failed to create a plan for the goal."
                    )
                    return {"description": "*Failed to create a plan for the goal.*"}

                ethical_ok = await self.agi.evaluator.evaluate_plan(
                    {"plan": [s.model_dump() for s in plan]}
                )
                if not ethical_ok:
                    self.agi.ltm.invalidate_plan(
                        active_goal.id, "Ethical gate rejected the initial plan."
                    )
                    return {
                        "description": (
                            "*Ethical gate rejected the initial plan. "
                            "Triggering replan.*"
                        )
                    }

                self.agi.ltm.update_plan(active_goal.id, plan)
                return {
                    "description": (
                        f"*New plan created for goal '{active_goal.description}'. "
                        "Starting execution.*"
                    )
                }

            if active_goal.id not in self.agi.workspaces:
                self.agi.workspaces[active_goal.id] = {
                    "goal_description": active_goal.description
                }
                self.agi.execution_history[active_goal.id] = []
            workspace = self.agi.workspaces[active_goal.id]

            next_step = active_goal.sub_tasks[0]

            if self.agi.skills.is_skill(next_step.action):
                skill = self.agi.skills.get_skill_by_name(next_step.action)
                if skill:
                    action_names = [step.action for step in skill.action_sequence]
                    logging.critical(
                        "[DEBUG] Expanding skill '%s' with actions: %s",
                        skill.name,
                        action_names,
                    )

                    goal_expansions = self._skill_expansion_history.get(
                        active_goal.id, []
                    )

                    if len(goal_expansions) >= 3 and all(
                        s == skill.name for s in goal_expansions[-3:]
                    ):
                        error_msg = (
                            f"Infinite recursion detected: skill '{skill.name}' "
                            "expanded repeatedly"
                        )
                        await self._handle_plan_failure(
                            active_goal, next_step, error_msg
                        )
                        return {
                            "description": (
                                f"Step failed: {error_msg} Triggering replan."
                            )
                        }

                    logging.info("[Skill] Expanding skill: '%s'", skill.name)

                    if active_goal.id not in self._skill_expansion_history:
                        self._skill_expansion_history[active_goal.id] = []
                    self._skill_expansion_history[active_goal.id].append(skill.name)

                    if len(self._skill_expansion_history[active_goal.id]) > 5:
                        self._skill_expansion_history[active_goal.id] = (
                            self._skill_expansion_history[active_goal.id][-5:]
                        )

                    current_plan = active_goal.sub_tasks
                    current_plan.pop(0)
                    expanded_plan = skill.action_sequence + current_plan
                    self.agi.ltm.update_plan(active_goal.id, expanded_plan)
                    return {
                        "description": (
                            f"*Skill '{skill.name}' expanded. Continuing execution.*"
                        )
                    }

            resolved_parameters = self._resolve_workspace_references(
                next_step.parameters, workspace
            )
            next_step.parameters = resolved_parameters

            logging.info(
                "[Step] Executing: %s for persona '%s'",
                next_step.action,
                next_step.assigned_persona,
            )

            result: Optional[Dict[str, Any]] = None
            if next_step.assigned_persona == "orchestrator":
                result = await self.agi.execute_single_action(next_step)
                if result.get("status") != "success":
                    await self._handle_plan_failure(
                        active_goal,
                        next_step,
                        result.get("description", "Orchestrator task failed."),
                    )
                    return {
                        "description": (
                            f"Step failed: {result.get('description')}. "
                            "Triggering replan."
                        )
                    }
            else:
                agent_names: List[str] = self.agi.agent_pool.get_agents_by_persona(
                    next_step.assigned_persona
                )
                if not agent_names:
                    await self._handle_plan_failure(
                        active_goal,
                        next_step,
                        f"No agent found with persona '{next_step.assigned_persona}'.",
                    )
                    return {
                        "description": (
                            f"Step failed: No agent found for persona "
                            f"'{next_step.assigned_persona}'. Triggering replan."
                        )
                    }

                agent_name = self._select_most_trusted_agent(agent_names)
                logging.info(
                    "[Delegate] Selected agent '%s' based on trust score.", agent_name
                )

                agent_state = self.agi.agent_pool.get_agent_state(agent_name)
                next_step.parameters["agent_state"] = agent_state
                next_step.parameters["workspace"] = workspace

                reply = await self.agi.delegate_task_and_wait(agent_name, next_step)

                if not reply or reply.payload.get("status") == "failure":
                    error = (
                        reply.payload.get("error", "unknown error")
                        if reply
                        else "timeout"
                    )
                    await self._handle_plan_failure(
                        active_goal,
                        next_step,
                        f"Step '{next_step.action}' failed: {error}",
                        agent_name,
                    )
                    return {"description": f"Step failed: {error}. Triggering replan."}

                if browser_action_data := reply.payload.get("browser_action"):
                    action_type = browser_action_data.get("action")
                    if action_type in ["click", "fill"]:
                        logging.info(
                            "Browser agent decided to '%s'. Executing now.",
                            action_type,
                        )
                        browser_step = ActionStep(
                            action=f"browser_{action_type}",
                            parameters=browser_action_data,
                            assigned_persona="orchestrator",
                        )
                        browser_result = await self.agi.execute_single_action(
                            browser_step
                        )
                        if browser_result.get("status") != "success":
                            error_msg = (
                                f"Browser action '{action_type}' failed: "
                                f"{browser_result.get('description')}"
                            )
                            await self._handle_plan_failure(
                                active_goal, next_step, error_msg, agent_name
                            )
                            return {
                                "description": (
                                    f"Step failed: {error_msg}. Triggering replan."
                                )
                            }
                    elif action_type == "done":
                        logging.info("Browser agent has completed its objective.")

                if next_step.action == "review_plan":
                    if not reply.payload.get("approved"):
                        feedback = reply.payload.get(
                            "feedback",
                            "Plan rejected by QA without specific feedback.",
                        )
                        self._decay_trust(agent_name)
                        await self._trigger_plan_refinement(active_goal, feedback)
                        return {
                            "description": (
                                f"Plan rejected by QA: {feedback}. Triggering refinement."
                            )
                        }
                    logging.info("Plan approved by QA. Proceeding with execution.")
                    self._reward_trust(agent_name)
                    self.agi.ltm.complete_sub_task(active_goal.id)
                    return {
                        "description": "*Plan approved by QA. Continuing execution.*"
                    }

                if reply:
                    self._reward_trust(agent_name)
                    if state_updates := reply.payload.pop("state_updates", None):
                        self.agi.agent_pool.update_agent_state(
                            agent_name, state_updates
                        )

                    self.agi.workspaces[active_goal.id].update(reply.payload)
                    logging.info(
                        "[Result] Workspace updated with keys: %s",
                        list(self.agi.workspaces[active_goal.id].keys()),
                    )

            history_record = ExecutionStepRecord(
                step=next_step,
                workspace_after=self.agi.workspaces[active_goal.id].copy(),
            )
            self.agi.execution_history[active_goal.id].append(history_record)

            if result and result.get("response_text"):
                self.agi.ltm.complete_sub_task(active_goal.id)
                self.agi.ltm.update_goal_status(active_goal.id, "completed")
                return result

            self.agi.ltm.complete_sub_task(active_goal.id)

            current_goal_state = self.agi.ltm.get_goal_by_id(active_goal.id)
            if not current_goal_state or not current_goal_state.sub_tasks:
                if current_goal_state:
                    await self._reflect_on_completed_goal(current_goal_state)

                if active_goal.id in self.agi.workspaces:
                    del self.agi.workspaces[active_goal.id]
                if active_goal.id in self.agi.execution_history:
                    del self.agi.execution_history[active_goal.id]
                if active_goal.id in self._skill_expansion_history:
                    del self._skill_expansion_history[active_goal.id]
                return {
                    "description": (
                        f"*Goal '{active_goal.description}' completed. "
                        "Post-goal reflection initiated.*"
                    )
                }

            return {
                "description": (
                    f"*(Goal: {active_goal.description}) Step "
                    f"'{next_step.action}' OK.*"
                )
            }

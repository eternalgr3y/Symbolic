# symbolic_agi/execution_unit.py

import json
import logging
import random
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from . import config, metrics
from .schemas import ActionStep, ExecutionStepRecord, GoalModel, MemoryEntryModel

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

    async def handle_autonomous_cycle(self) -> Dict[str, Any]:
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

    def _select_most_trusted_agent(self, agent_names: List[str]) -> str:
        """
        Selects an agent from a list using trust-weighted random selection.
        Agents with trust below 0.05 are ineligible.
        """
        if not agent_names:
            raise ValueError("Cannot select an agent from an empty list.")

        candidates: List[str] = []
        weights: List[float] = []
        for name in agent_names:
            state = self.agi.agent_pool.get_agent_state(name)
            trust_score = state.get("trust_score", 0.0)
            if trust_score >= 0.05:
                candidates.append(name)
                weights.append(trust_score)

        if not candidates:
            logging.warning(
                "All agents for persona have trust < 0.05. Selecting from original list."
            )
            return max(
                agent_names,
                key=lambda name: self.agi.agent_pool.get_agent_state(name).get(
                    "trust_score", 0.0
                ),
            )

        return random.choices(candidates, weights=weights, k=1)[0]

    def _decay_trust(self, agent_name: str) -> None:
        """Decreases the trust score of a specific agent upon failure and updates metrics."""
        agent_data = self.agi.agent_pool.subagents.get(agent_name)
        if not agent_data:
            return

        state = agent_data.get("state", {})
        current_score = state.get("trust_score", config.INITIAL_TRUST_SCORE)
        new_score = max(0.0, current_score - config.TRUST_DECAY_RATE)
        self.agi.agent_pool.update_agent_state(agent_name, {"trust_score": new_score})

        persona = agent_data.get("persona", "unknown")
        metrics.AGENT_TRUST.labels(agent_name=agent_name, persona=persona).set(
            new_score
        )
        logging.warning(
            "Trust decayed for agent '%s'. New score: %.2f", agent_name, new_score
        )

    def _reward_trust(self, agent_name: str) -> None:
        """Increases the trust score of a specific agent upon success and updates metrics."""
        agent_data = self.agi.agent_pool.subagents.get(agent_name)
        if not agent_data:
            return

        state = agent_data.get("state", {})
        current_score = state.get("trust_score", config.INITIAL_TRUST_SCORE)
        new_score = min(
            config.MAX_TRUST_SCORE, current_score + config.TRUST_REWARD_RATE
        )
        self.agi.agent_pool.update_agent_state(agent_name, {"trust_score": new_score})

        persona = agent_data.get("persona", "unknown")
        metrics.AGENT_TRUST.labels(agent_name=agent_name, persona=persona).set(
            new_score
        )
        logging.info(
            "Trust rewarded for agent '%s'. New score: %.2f", agent_name, new_score
        )

    async def _classify_and_generate_initial_plan(
        self, goal: GoalModel
    ) -> List[ActionStep]:
        logging.info("[Planner] Decomposing goal into initial plan...")
        source_files_result = await self.agi.tools.read_own_source_code(file_name="")
        workspace_files_result = await self.agi.tools.list_files()

        file_manifest = "Available Source Code Files (`symbolic_agi/`):\n"
        source_list = cast(List[str], source_files_result.get("files", []))
        if source_files_result.get("status") == "success":
            file_manifest += "\n".join([f"- {f}" for f in source_list])
        else:
            file_manifest += "- Could not list source files."

        file_manifest += "\n\nAvailable Workspace Files (`data/workspace/`):\n"
        workspace_list = cast(List[str], workspace_files_result.get("files", []))
        if workspace_files_result.get("status") == "success":
            file_manifest += "\n".join([f"- {f}" for f in workspace_list])
        else:
            file_manifest += "- Could not list workspace files."

        planner_output = await self.agi.planner.decompose_goal_into_plan(
            goal.description, file_manifest, mode=goal.mode
        )
        logging.info("[Planner] Thought: %s", planner_output.thought)
        return planner_output.plan

    async def _trigger_plan_refinement(self, goal: GoalModel, feedback: str) -> None:
        logging.critical(
            "[Planner] PLAN REFINEMENT triggered for goal '%s'. Reason: %s",
            goal.id,
            feedback,
        )

        new_refinement_count: int = self.agi.ltm.increment_refinement_count(goal.id)
        if new_refinement_count >= goal.max_refinements:
            final_error = (
                f"Goal failed after {new_refinement_count} refinement attempts. "
                f"Last feedback: {feedback}"
            )
            self.agi.ltm.invalidate_plan(goal.id, final_error)
            return

        plan_to_review = (
            goal.sub_tasks[1:]
            if goal.sub_tasks and goal.sub_tasks[0].action == "review_plan"
            else goal.sub_tasks
        )

        refinement_context: Dict[str, Any] = {
            "plan_to_review": [step.model_dump() for step in plan_to_review],
            "feedback": feedback,
        }

        source_files_result = await self.agi.tools.read_own_source_code(file_name="")
        workspace_files_result = await self.agi.tools.list_files()
        file_manifest = "Source Files: " + ", ".join(
            cast(List[str], source_files_result.get("files", []))
        )
        file_manifest += "\nWorkspace Files: " + ", ".join(
            cast(List[str], workspace_files_result.get("files", []))
        )

        planner_output = await self.agi.planner.decompose_goal_into_plan(
            goal_description=goal.description,
            file_manifest=file_manifest,
            mode=goal.mode,
            refinement_feedback=refinement_context,
        )

        logging.info("[Planner] Refined Thought: %s", planner_output.thought)
        new_plan = planner_output.plan

        if new_plan:
            ethical_ok = await self.agi.evaluator.evaluate_plan(
                {"plan": [s.model_dump() for s in new_plan]}
            )
            if not ethical_ok:
                logging.critical(
                    "REFINED PLAN REJECTED by Ethical Gate for goal '%s'.", goal.id
                )
                self.agi.ltm.invalidate_plan(
                    goal.id, "Ethical gate rejected the refined plan."
                )
                return

            logging.critical(
                "PLAN REFINEMENT SUCCESSFUL. New plan created for goal '%s'.", goal.id
            )
            self.agi.ltm.update_plan(goal.id, new_plan)
        else:
            logging.error(
                "PLAN REFINEMENT FAILED. Could not generate a new plan for goal '%s'.",
                goal.id,
            )
            self.agi.ltm.invalidate_plan(
                goal.id, "Refinement process failed to generate a valid new plan."
            )

    async def _reflect_on_perceptions(self) -> bool:
        events_to_process = list(self.agi.perception_buffer)
        self.agi.perception_buffer.clear()

        logging.info(
            "[Perception] Reflecting on %d new perception(s).", len(events_to_process)
        )

        for event in events_to_process:
            await self.agi.memory.add_memory(
                MemoryEntryModel(
                    type="perception",
                    content=event.model_dump(mode="json"),
                    importance=0.6,
                )
            )

        active_goal = self.agi.ltm.get_active_goal()
        current_goal_desc = (
            active_goal.description if active_goal else "I am currently idle."
        )

        prompt = (
            "You are a conscious AGI. You have just perceived the following events "
            "in your environment while working on a task.\n\n"
            "--- PERCEIVED EVENTS ---\n"
            f"{json.dumps([e.model_dump(mode='json') for e in events_to_process], indent=2)}\n\n"
            f"--- CURRENT GOAL ---\n{current_goal_desc}\n\n"
            "--- INSTRUCTIONS ---\n"
            "Analyze the events. Are they important or surprising enough to justify "
            "interrupting your current task?\n"
            "- If an event is highly relevant, urgent, or unexpected (like a new "
            "file appearing that seems related to your goal), you should interrupt.\n"
            "- If the events are routine or irrelevant, you should not interrupt.\n\n"
            "Respond with ONLY a single, valid JSON object with the following keys:\n"
            '- "interrupt": boolean (true if you should stop your current task to '
            "address this)\n"
            '- "reason": string (a brief explanation for your decision)\n'
            '- "new_goal_description": string (if interrupting, a new high-level '
            "goal to address the perception, otherwise an empty string)\n"
        )
        response_str = ""
        try:
            response_str = await self.agi.introspector.llm_reflect(prompt)
            reflection = json.loads(response_str)

            if reflection.get("interrupt") and reflection.get("new_goal_description"):
                new_desc = reflection["new_goal_description"]
                logging.critical(
                    "PERCEPTION TRIGGERED NEW GOAL: %s. Reason: %s",
                    new_desc,
                    reflection.get("reason"),
                )
                new_goal = GoalModel(description=new_desc, sub_tasks=[])
                self.agi.ltm.add_goal(new_goal)
                return True

        except (json.JSONDecodeError, KeyError) as e:
            logging.error(
                "Failed to parse perception reflection response: %s. Response was: %s",
                e,
                response_str,
            )

        return False

    async def _reflect_on_completed_goal(self, goal: GoalModel) -> None:
        """Handles post-goal reflection for skill learning and emotional state update."""
        self.agi.emotional_state.joy = min(1.0, self.agi.emotional_state.joy + 0.2)
        self.agi.emotional_state.frustration *= 0.5
        self.agi.emotional_state.clamp()
        logging.info(
            "Goal '%s' completed. Emotional state updated: %s",
            goal.description,
            self.agi.emotional_state.model_dump(),
        )

        if not goal.original_plan:
            logging.warning(
                "Cannot learn from goal '%s': No original plan was recorded.", goal.id
            )
            self.agi.ltm.update_goal_status(goal.id, "completed")
            return

        logging.info(
            "Reflecting on completed goal '%s' to check for skill acquisition.",
            goal.description,
        )

        plan_json = json.dumps(
            [step.model_dump(mode="json") for step in goal.original_plan]
        )

        prompt = (
            "You are a meta-cognitive AGI reflecting on a successfully completed task.\n"
            "Your goal is to decide if the plan used to achieve the task is general "
            "and useful enough to be saved as a new, reusable skill.\n\n"
            f'--- TASK DESCRIPTION ---\n"{goal.description}"\n\n'
            f"--- SUCCESSFUL PLAN ---\n{plan_json}\n\n"
            "--- ANALYSIS INSTRUCTIONS ---\n"
            "1.  **Generality**: Is this task something that might be requested again "
            'in a different context? (e.g., "summarize a file" is general, '
            '"summarize the file \'report_xyz.txt\' from yesterday" is not).\n'
            "2.  **Efficiency**: Was the plan reasonably direct? (Assume this plan was "
            "successful).\n"
            "3.  **Name & Description**: If it's worth learning, propose a short, "
            "function-like `skill_name` (e.g., `summarize_and_save_webpage`) and a "
            "concise one-sentence `skill_description`.\n\n"
            "--- RESPONSE FORMAT ---\n"
            "Respond with ONLY a single, valid JSON object with the following keys:\n"
            '- "should_learn": boolean (true if the plan should be saved as a skill)\n'
            '- "skill_name": string (the proposed name, or an empty string if not '
            "learning)\n"
            '- "skill_description": string (the proposed description, or an empty '
            "string if not learning)\n"
        )

        response_str = ""
        try:
            response_str = await self.agi.introspector.llm_reflect(prompt)
            if "```json" in response_str:
                response_str = response_str.partition("```json")[2].partition("```")[0]
            response_str = response_str.strip()

            reflection = json.loads(response_str)

            if reflection.get("should_learn"):
                name = reflection.get("skill_name")
                desc = reflection.get("skill_description")
                if name and desc and goal.original_plan:
                    await self.agi.skills.add_new_skill(
                        name=name, description=desc, plan=goal.original_plan
                    )
                    await self.agi.meta_cognition.record_meta_event(
                        "skill_transfer",
                        {"name": name, "description": desc, "source_goal": goal.id},
                    )
                    logging.critical(
                        "LEARNED NEW SKILL: '%s' from goal '%s'",
                        name,
                        goal.description,
                    )
                else:
                    logging.warning(
                        "LLM recommended learning a skill but did not provide a valid "
                        "name or description."
                    )

        except (json.JSONDecodeError, KeyError) as e:
            logging.error(
                "Failed to parse reflection response for skill learning: %s. "
                "Response was: %s",
                e,
                response_str,
            )
        except Exception as e:
            logging.error(
                "An unexpected error occurred during skill reflection: %s",
                e,
                exc_info=True,
            )
        finally:
            self.agi.ltm.update_goal_status(goal.id, "completed")

    async def _handle_plan_failure(
        self,
        goal: GoalModel,
        failed_step: ActionStep,
        error_message: str,
        agent_name: Optional[str] = None,
    ) -> None:
        """
        Handles a failed plan step by updating emotions, analyzing the failure,
        decaying trust, and then replanning.
        """
        logging.error(
            "Plan failed for goal '%s' at step '%s': %s",
            goal.description,
            failed_step.action,
            error_message,
        )

        self.agi.emotional_state.frustration = min(
            1.0, self.agi.emotional_state.frustration + 0.3
        )
        self.agi.emotional_state.sadness = min(
            1.0, self.agi.emotional_state.sadness + 0.1
        )
        self.agi.emotional_state.clamp()
        logging.warning(
            "Plan failure. Emotional state updated: %s",
            self.agi.emotional_state.model_dump(),
        )

        if agent_name:
            self._decay_trust(agent_name)

        failure_context: Dict[str, Any] = {
            "execution_history": [
                record.model_dump(mode="json")
                for record in self.agi.execution_history.get(goal.id, [])
            ],
            "failed_step": failed_step.model_dump(mode="json"),
            "error_message": error_message,
        }
        await self.agi.introspector.analyze_failure_and_propose_mutation(
            failure_context
        )

        new_failure_count = self.agi.ltm.increment_failure_count(goal.id)

        if new_failure_count >= goal.max_failures:
            final_error = (
                f"Goal failed after {new_failure_count} attempts. "
                f"Last error: {error_message}"
            )
            self.agi.ltm.invalidate_plan(goal.id, final_error)
            if goal.id in self.agi.workspaces:
                del self.agi.workspaces[goal.id]
            if goal.id in self.agi.execution_history:
                del self.agi.execution_history[goal.id]
            if goal.id in self._skill_expansion_history:
                del self._skill_expansion_history[goal.id]
            return

        await self._trigger_replanning(goal, failed_step, error_message)

    async def _trigger_replanning(
        self, goal: GoalModel, failed_step: ActionStep, error_message: str
    ) -> None:
        logging.info("Triggering replanning for goal: %s", goal.id)

        failure_context: Dict[str, Any] = {
            "execution_history": [
                record.model_dump(mode="json")
                for record in self.agi.execution_history.get(goal.id, [])
            ],
            "failed_step": failed_step.model_dump(mode="json"),
            "error_message": error_message,
        }

        source_files_result = await self.agi.tools.read_own_source_code(file_name="")
        workspace_files_result = await self.agi.tools.list_files()
        file_manifest = "Source Files: " + ", ".join(
            cast(List[str], source_files_result.get("files", []))
        )
        file_manifest += "\nWorkspace Files: " + ", ".join(
            cast(List[str], workspace_files_result.get("files", []))
        )

        planner_output = await self.agi.planner.decompose_goal_into_plan(
            goal_description=goal.description,
            file_manifest=file_manifest,
            mode=goal.mode,
            failure_context=failure_context,
        )

        logging.info("[Planner] Replanner Thought: %s", planner_output.thought)
        new_plan = planner_output.plan

        if new_plan:
            ethical_ok = await self.agi.evaluator.evaluate_plan(
                {"plan": [s.model_dump() for s in new_plan]}
            )
            if not ethical_ok:
                logging.critical(
                    "REPLAN REJECTED by Ethical Gate for goal '%s'.", goal.id
                )
                self.agi.ltm.invalidate_plan(
                    goal.id, "Ethical gate rejected the replanned plan."
                )
                return

            logging.critical(
                "REPLAN SUCCESSFUL. New plan created for goal '%s'.", goal.id
            )
            self.agi.ltm.update_plan(goal.id, new_plan)
        else:
            logging.error(
                "REPLAN FAILED. Could not generate a new plan for goal '%s'.", goal.id
            )
            self.agi.ltm.invalidate_plan(
                goal.id, "Replanning process failed to generate a valid new plan."
            )

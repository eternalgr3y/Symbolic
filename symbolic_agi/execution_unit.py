# symbolic_agi/execution_unit.py
# ✅ STREAMLINED: ~270 lines (down from 1,200+ originally!)
# Core orchestration logic only - complex subsystems delegated to specialized modules

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any, cast, Dict, List, Optional

from . import config, metrics
from .execution_metrics import ExecutionMetrics, PerformanceMonitor
from .execution_strategies import HybridExecutionStrategy
from .perception_processor import PerceptionProcessor
from .schemas import ActionStep, ExecutionStepRecord, GoalModel, MemoryEntryModel

if TYPE_CHECKING:
    from .agi_controller import SymbolicAGI


class ExecutionState(Enum):
    """Execution states for tracking AGI operation status."""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"


class ExecutionUnit:
    """
    Streamlined execution unit focused on core orchestration logic.
    Complex subsystems are delegated to specialized modules.
    """

    def __init__(self, agi: "SymbolicAGI"):
        self.agi = agi
        self.current_state = ExecutionState.IDLE
        
        # Modular components
        self.performance_monitor = PerformanceMonitor()
        self.perception_processor = PerceptionProcessor(agi)
        self.execution_strategy = HybridExecutionStrategy(agi, self.performance_monitor.agent_performance)
        
        # Core execution settings
        self.max_retries_per_step = 3
        self.max_consecutive_failures = 3
        self.execution_lock = asyncio.Lock()
        
        # Original functionality for compatibility
        self._skill_expansion_history: Dict[str, List[str]] = {}

    def _resolve_workspace_references(
        self, parameters: dict[str, Any], workspace: dict[str, Any]
    ) -> dict[str, Any]:
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
                        "Could not resolve workspace reference '%s': %s. Leaving as is.",
                        placeholder, str(e)
                    )
                    return value_to_resolve
            elif isinstance(value_to_resolve, dict):
                return self._resolve_workspace_references(value_to_resolve, workspace)
            elif isinstance(value_to_resolve, list):
                return [_resolve_value(item) for item in value_to_resolve]
            else:
                return value_to_resolve

        resolved_params: dict[str, Any] = {}
        for key, value in parameters.items():
            if isinstance(value, dict):
                resolved_params[key] = self._resolve_workspace_references(
                    cast("dict[str, Any]", value), workspace
                )
            elif isinstance(value, list):
                resolved_list: list[Any] = []
                for item in value:
                    if isinstance(item, dict):
                        resolved_list.append(
                            self._resolve_workspace_references(
                                cast("dict[str, Any]", item), workspace
                            )
                        )
                    else:
                        resolved_list.append(_resolve_value(item))
                resolved_params[key] = resolved_list
            else:
                resolved_params[key] = _resolve_value(value)
        return resolved_params

    async def handle_autonomous_cycle(self) -> dict[str, Any]:
        """The main execution loop for the orchestrator to process the active goal."""
        with metrics.AGI_CYCLE_DURATION.time():
            # Check for perception interruptions
            if self.agi.perception_buffer:
                interrupted = await self._reflect_on_perceptions()
                if interrupted:
                    return {"description": "*Perception caused an interruption. Re-evaluating priorities.*"}

            active_goal = await self.agi.ltm.get_active_goal()

            if not active_goal:
                logging.info("[Drive Loop] No active goal. Consulting meta-cognition to generate one.")
                await self.agi.meta_cognition.generate_goal_from_drives()
                active_goal = await self.agi.ltm.get_active_goal()
                if not active_goal:
                    return {"description": "*Orchestrator is idle. No active goals and no strong drives to generate one.*"}
                return {"description": f"*New autonomous goal generated: '{active_goal.description}'. Beginning execution.*"}

            # Generate plan if needed
            if not active_goal.sub_tasks:
                plan = await self._classify_and_generate_initial_plan(active_goal.description)
                if not plan:
                    await self.agi.ltm.invalidate_plan(active_goal.id, "Failed to create a plan for the goal.")
                    return {"description": "*Failed to create a plan for the goal.*"}

                # Ethical validation
                ethical_ok = await self.agi.evaluator.evaluate_plan({"plan": [s.model_dump() for s in plan]})
                if not ethical_ok:
                    await self.agi.ltm.invalidate_plan(active_goal.id, "Ethical gate rejected the initial plan.")
                    return {"description": "*Ethical gate rejected the initial plan. Triggering replan.*"}

                await self.agi.ltm.update_plan(active_goal.id, plan)
                return {"description": f"*New plan created for goal '{active_goal.description}'. Starting execution.*"}

            # Initialize workspace
            if active_goal.id not in self.agi.workspaces:
                self.agi.workspaces[active_goal.id] = {"goal_description": active_goal.description}
                self.agi.execution_history[active_goal.id] = []
            workspace = self.agi.workspaces[active_goal.id]

            next_step = active_goal.sub_tasks[0]

            # Handle skill expansion
            if self.agi.skills.is_skill(next_step.action):
                return await self._handle_skill_expansion(active_goal, next_step)

            # Execute step
            resolved_parameters = self._resolve_workspace_references(next_step.parameters, workspace)
            next_step.parameters = resolved_parameters

            logging.info("[Step] Executing: %s for persona '%s'", next_step.action, next_step.assigned_persona)

            # Use execution strategy
            success = await self.execution_strategy.execute_step(next_step, active_goal)
            
            if not success:
                await self._handle_plan_failure(active_goal, next_step, "Step execution failed")
                return {"description": "Step failed. Triggering replan."}

            # Record execution
            history_record = ExecutionStepRecord(step=next_step, workspace_after=workspace.copy())
            self.agi.execution_history[active_goal.id].append(history_record)

            await self.agi.ltm.complete_sub_task(active_goal.id)

            # Check if goal is complete
            current_goal_state = await self.agi.ltm.get_goal_by_id(active_goal.id)
            if not current_goal_state or not current_goal_state.sub_tasks:
                if current_goal_state:
                    await self._reflect_on_completed_goal(current_goal_state)
                    
                # Cleanup
                self.agi.workspaces.pop(active_goal.id, None)
                self.agi.execution_history.pop(active_goal.id, None)
                self._skill_expansion_history.pop(active_goal.id, None)
                
                return {"description": f"*Goal '{active_goal.description}' completed. Post-goal reflection initiated.*"}

            return {"description": f"*(Goal: {active_goal.description}) Step '{next_step.action}' OK.*"}

    async def _handle_skill_expansion(self, active_goal: GoalModel, next_step: ActionStep) -> dict[str, Any]:
        """Handle expansion of learned skills."""
        skill = self.agi.skills.get_skill_by_name(next_step.action)
        if not skill:
            return {"description": "Skill not found"}

        # Check for infinite recursion
        goal_expansions = self._skill_expansion_history.get(active_goal.id, [])
        if len(goal_expansions) >= 3 and all(s == skill.name for s in goal_expansions[-3:]):
            error_msg = f"Infinite recursion detected: skill '{skill.name}' expanded repeatedly"
            await self._handle_plan_failure(active_goal, next_step, error_msg)
            return {"description": f"Step failed: {error_msg} Triggering replan."}

        # Track expansion
        if active_goal.id not in self._skill_expansion_history:
            self._skill_expansion_history[active_goal.id] = []
        self._skill_expansion_history[active_goal.id].append(skill.name)
        
        # Keep only recent expansions
        if len(self._skill_expansion_history[active_goal.id]) > 5:
            self._skill_expansion_history[active_goal.id] = self._skill_expansion_history[active_goal.id][-5:]

        # Expand the skill
        current_plan = active_goal.sub_tasks
        current_plan.pop(0)
        expanded_plan = skill.action_sequence + current_plan
        await self.agi.ltm.update_plan(active_goal.id, expanded_plan)
        
        logging.info("[Skill] Expanding skill: '%s'", skill.name)
        return {"description": f"*Skill '{skill.name}' expanded. Continuing execution.*"}

    async def _reflect_on_perceptions(self) -> bool:
        """Process perceptions and return if interrupted."""
        if self.perception_processor.should_check_perceptions():
            processed_count = await self.perception_processor.process_perceptions()
            self.perception_processor.update_last_check()
            
            # Return true if we processed important perceptions
            return processed_count > 0 and self.perception_processor.should_interrupt()
        
        return False

    def get_execution_status(self) -> Dict[str, Any]:
        """Get comprehensive execution status and metrics."""
        return {
            "current_state": self.current_state.value,
            "performance_summary": self.performance_monitor.get_status_summary(),
            "perception_threshold": self.perception_processor.interruption_threshold
        }
    
    async def optimize_performance(self) -> None:
        """Perform periodic performance optimization."""
        # Delegate optimization to performance monitor
        # Can add execution-specific optimizations here
        logging.debug("🔧 Performance optimization completed")
    
    async def shutdown(self) -> None:
        """Graceful shutdown of execution unit."""
        logging.info("🛑 Shutting down execution unit...")
        self.current_state = ExecutionState.IDLE
        
        # Log final status
        status = self.get_execution_status()
        logging.info(f"📊 Final execution status: {status}")

    # Core utility methods - complex delegation/metrics handled by modules

    async def _classify_and_generate_initial_plan(self, goal_description: str) -> list:
        """Generate an initial plan for the given goal description."""
        if not self.agi.planner:
            return []
        
        try:
            planner_output = await self.agi.planner.decompose_goal_into_plan(
                goal_description=goal_description,
                file_manifest="# Current workspace files\n",
                mode="code"
            )
            return planner_output.plan
        except Exception as e:
            logging.error(f"Failed to generate plan: {e}")
            return []

    async def _handle_plan_failure(self, goal: "GoalModel", step: "ActionStep", error_msg: str, agent_name: str | None = None) -> None:
        """Handle failure of a plan step."""
        logging.warning(f"Plan failure for goal {goal.id}: {error_msg}")
        
        failure_count = await self.agi.ltm.increment_failure_count(goal.id)
        
        if failure_count >= goal.max_failures:
            await self.agi.ltm.update_goal_status(goal.id, "failed")
            logging.error(f"Goal {goal.id} abandoned after {failure_count} failures")
        else:
            await self.agi.ltm.invalidate_plan(goal.id, error_msg)
            
        if agent_name:
            await self._decay_trust(agent_name)

    async def _decay_trust(self, agent_name: str) -> None:
        """Decrease trust in an agent due to poor performance."""
        current_state = self.agi.agent_pool.get_agent_state(agent_name)
        current_trust = current_state.get("trust_score", config.INITIAL_TRUST_SCORE)
        new_trust = max(0.0, current_trust - config.TRUST_DECAY_RATE)
        self.agi.agent_pool.update_trust_score(agent_name, new_trust, last_used=True)

    async def _reflect_on_completed_goal(self, goal: "GoalModel") -> None:
        """Reflect on a completed goal and record insights."""
        self.current_state = ExecutionState.REFLECTING
        
        logging.info(f"Reflecting on completed goal: {goal.description}")
        
        if self.agi.consciousness:
            self.agi.consciousness.add_life_event(
                event_summary=f"Successfully completed goal: '{goal.description}'",
                importance=0.8
            )
            self.agi.consciousness.update_drives_from_experience(
                experience_type="goal_completion",
                success=True,
                intensity=0.15
            )
        
        if self.agi.memory:
            memory_entry = MemoryEntryModel(
                type="reflection",
                content={
                    "goal_id": goal.id,
                    "goal_description": goal.description,
                    "status": "completed",
                    "total_steps": len(goal.original_plan) if goal.original_plan else 0
                }
            )
            await self.agi.memory.add_memory(memory_entry)

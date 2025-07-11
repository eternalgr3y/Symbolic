# symbolic_agi/execution_engine.py
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from . import config
from .schemas import ActionStep, ExecutionContext, ExecutionResult, ExecutionStepRecord, GoalModel
from .skill_manager import INNATE_ACTIONS

if TYPE_CHECKING:
    from .agi_controller import SymbolicAGI
    from .goal_management import GoalManager
    from .planner import Planner
    from .recursive_introspector import RecursiveIntrospector

class ExecutionEngine:
    """Executes plans and manages task execution."""
    
    def __init__(
        self,
        agi: "SymbolicAGI",
        goal_manager: "GoalManager",
        planner: "Planner",
        introspector: "RecursiveIntrospector"
    ):
        self.agi = agi
        self.goal_manager = goal_manager
        self.planner = planner
        self.introspector = introspector
        self.current_context: Optional[ExecutionContext] = None
        self._running = False

    async def run(self) -> None:
        """Main execution loop."""
        self._running = True
        logging.info("[ExecutionEngine] Starting execution loop")
        
        while self._running and not self.agi.shutdown_event.is_set():
            try:
                # Get next active goal
                active_goals = self.goal_manager.get_active_goals()
                
                if active_goals:
                    goal = active_goals[0]
                    await self.execute_goal(goal)
                else:
                    # No active goals, wait
                    await asyncio.sleep(5)
                    
            except asyncio.CancelledError:
                logging.info("[ExecutionEngine] Execution loop cancelled")
                raise  # Re-raise the CancelledError
            except Exception as e:
                logging.error(f"[ExecutionEngine] Error in execution loop: {e}")
                await asyncio.sleep(10)
                
        logging.info("[ExecutionEngine] Execution loop stopped")

    async def execute_goal(self, goal: GoalModel) -> ExecutionResult:
        """Execute a single goal."""
        logging.info(f"[ExecutionEngine] Executing goal: {goal.description}")
        
        try:
            # Create execution context
            self.current_context = ExecutionContext(goal=goal, plan=[])
            
            # Generate plan
            planner_output = await self.planner.create_plan(goal.description)
            if not planner_output:
                return ExecutionResult(
                    success=False,
                    error="Failed to create plan",
                    metrics=self.current_context.metrics
                )
                
            self.current_context.plan = planner_output.plan
            self.current_context.metrics.total_steps = len(planner_output.plan)
            
            # Execute each step
            for i, step in enumerate(self.current_context.plan):
                self.current_context.current_step = i
                
                result = await self.execute_step(step)
                
                if not result.success:
                    # Handle failure
                    self.goal_manager.fail_goal(goal.id, result.error or "Step execution failed")
                    return ExecutionResult(
                        success=False,
                        error=result.error,
                        metrics=self.current_context.metrics
                    )
                    
            # Goal completed successfully
            self.goal_manager.complete_goal(goal.id)
            
            # Calculate final metrics
            self.current_context.metrics.success_rate = (
                self.current_context.metrics.completed_steps / 
                self.current_context.metrics.total_steps
            ) if self.current_context.metrics.total_steps > 0 else 0.0
            
            return ExecutionResult(
                success=True,
                result=self.current_context.workspace,
                metrics=self.current_context.metrics
            )
            
        except Exception as e:
            logging.error(f"[ExecutionEngine] Goal execution error: {e}")
            self.goal_manager.fail_goal(goal.id, str(e))
            return ExecutionResult(
                success=False,
                error=str(e),
                metrics=self.current_context.metrics if self.current_context else None
            )
        finally:
            self.current_context = None

    async def execute_step(self, step: ActionStep) -> ExecutionResult:
        """Execute a single action step."""
        logging.info(f"[ExecutionEngine] Executing step: {step.action}")
        
        record = ExecutionStepRecord(
            step_index=self.current_context.current_step,
            action=step.action,
            parameters=step.parameters,
            started_at=datetime.now(timezone.utc)
        )
        
        start_time = time.time()
        
        try:
            # Check if action exists
            if step.action not in INNATE_ACTIONS:
                # Try to delegate to agent pool
                result = await self.agi.agent_pool.delegate_task({
                    "action": step.action,
                    "parameters": step.parameters,
                    "context": self.current_context.workspace
                })
                
                if result is None:
                    raise ValueError(f"Unknown action: {step.action}")
                    
            else:
                # Execute innate action
                action_func = INNATE_ACTIONS[step.action]
                result = await action_func(self.agi, **step.parameters)
            
            # Update record
            record.completed_at = datetime.now(timezone.utc)
            record.result = result
            
            # Update workspace
            if isinstance(result, dict) and result.get('success'):
                self.current_context.workspace[f"step_{self.current_context.current_step}"] = result
                
            # Update metrics
            self.current_context.metrics.completed_steps += 1
            step_duration = time.time() - start_time
            self.current_context.metrics.total_duration += step_duration
            self.current_context.metrics.average_step_duration = (
                self.current_context.metrics.total_duration / 
                self.current_context.metrics.completed_steps
            )
            
            self.current_context.execution_history.append(record)
            
            return ExecutionResult(
                success=True,
                result=result,
                metrics=self.current_context.metrics
            )
            
        except Exception as e:
            logging.error(f"[ExecutionEngine] Step execution error: {e}")
            
            record.completed_at = datetime.now(timezone.utc)
            record.error = str(e)
            record.retries += 1
            
            self.current_context.metrics.failed_steps += 1
            self.current_context.execution_history.append(record)
            
            return ExecutionResult(
                success=False,
                error=str(e),
                metrics=self.current_context.metrics
            )

    def stop(self) -> None:
        """Stop the execution engine."""
        self._running = False
# symbolic_agi/execution_engine.py

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .agi_controller import SymbolicAGI
    from .goal_management import GoalManager, EnhancedGoal, GoalStatus

class ExecutionEngine:
    """
    Advanced execution engine with monitoring, retries, and concurrent processing.
    This class now contains the main cognitive loop of the AGI.
    """

    def __init__(self, agi: "SymbolicAGI", goal_manager: "GoalManager"):
        self.agi = agi
        self.goal_manager = goal_manager
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        logging.info("ExecutionEngine initialized.")

    async def start(self): 
        """Starts the main execution loop in a background task."""
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self.execution_loop())
            logging.info("ExecutionEngine main loop started.")
        await asyncio.sleep(0)

    async def stop(self):
        """Stops the main execution loop."""
        if self.is_running and self.task:
            self.is_running = False
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logging.error(f"Critical error in execution loop: {e}", exc_info=True)
                await asyncio.sleep(5) # Cooldown after critical error
                logging.info("ExecutionEngine main loop successfully cancelled.")

    async def execution_loop(self):
        """The main cognitive loop of the AGI."""
        while self.is_running:
            try:
                next_goal = self.goal_manager.get_next_goal()

                if next_goal:
                    self.goal_manager.start_goal(next_goal)
                    task = asyncio.create_task(self._process_goal_async(next_goal))
                    self.active_tasks.append(task)  # Save the task
                    logging.info(f"Processing goal [{next_goal.id}]: {next_goal.description}") 

                await asyncio.sleep(1)  # Main loop heartbeat

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logging.error(f"Critical error in execution loop: {e}", exc_info=True)
                await asyncio.sleep(5) # Cooldown after critical error

    async def _process_goal_async(self, goal: "EnhancedGoal"):
        """Processes a single goal asynchronously with monitoring and retries."""
        start_time = time.time()

        try:
            logging.info(f"🎯 Processing goal [{goal.id}]: {goal.description}")

            # The AGI controller's method now focuses purely on plan execution
            result = await asyncio.wait_for(
                self.agi.process_goal_with_plan(goal.description),
                timeout=goal.timeout_seconds
            )

            execution_time = time.time() - start_time
            result['execution_time'] = execution_time

            if result.get('status') in ['success', 'partial_failure']:
                await self.goal_manager.complete_goal(goal.id, result)
            else:
                raise RuntimeError(result.get('description', 'Unknown execution error'))

        except asyncio.CancelledError:
            # Handle cancellation cleanup if needed
            logging.info(f"🚫 Goal [{goal.id}] was cancelled during processing.")
            # Re-raise to properly propagate the cancellation
            raise
            
        except asyncio.TimeoutError:
            error_msg = f"Goal timed out after {goal.timeout_seconds} seconds"
            logging.error(f"⏰ Goal [{goal.id}] timed out.")
            await self._handle_failure(goal, error_msg)

        except Exception as e:
            error_msg = f"Execution failed: {str(e)}"
            logging.error(f"❌ Goal [{goal.id}] failed: {error_msg}", exc_info=True)
            await self._handle_failure(goal, error_msg)

    async def _handle_failure(self, goal: "EnhancedGoal", error: str):
        """Handles goal failure, including retry logic."""
        from .goal_management import GoalStatus # Local import to avoid circular dependency

        if goal.retry_count < goal.max_retries:
            goal.retry_count += 1
            goal.status = GoalStatus.QUEUED
            goal.error = error # Store last error
            self.goal_manager.goal_queue.put(goal)
            logging.info(f"🔄 Retrying goal [{goal.id}] (attempt {goal.retry_count + 1}/{goal.max_retries}) due to: {error}")
        else:
            await self.goal_manager.fail_goal(goal.id, f"Exceeded max retries. Last error: {error}")
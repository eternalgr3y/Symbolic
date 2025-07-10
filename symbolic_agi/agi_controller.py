# symbolic_agi/agi_controller.py

import asyncio
import atexit
import logging
import os
from collections import deque
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, cast
from datetime import datetime, timezone

from playwright.async_api import Browser, Page, async_playwright
from watchfiles import awatch

from . import config
from . import reasoning_skills
from .agent_pool import DynamicAgentPool
from .api_client import client
from .ethical_governance import SymbolicEvaluator
from .goal_management import GoalManager
from .execution_engine import ExecutionEngine
from .knowledge_base import KnowledgeBase
from .long_term_memory import LongTermMemory
from .message_bus import RedisMessageBus
from .meta_cognition import MetaCognitionUnit
from .micro_world import MicroWorld
from .planner import Planner
from .recursive_introspector import RecursiveIntrospector
from .schemas import (
    ActionStep, AGIConfig, EmotionalState, GoalModel, MessageModel, PerceptionEvent
)
from .skill_manager import SkillManager
from .symbolic_identity import SymbolicIdentity
from .symbolic_memory import SymbolicMemory
from .tool_plugin import ToolPlugin

if TYPE_CHECKING:
    from .consciousness import Consciousness

class SymbolicAGI:
    """
    The core class for the Symbolic AGI. Acts as a dependency container and
    top-level manager for its functional units.
    """

    cfg: AGIConfig
    name: str
    message_bus: RedisMessageBus
    memory: SymbolicMemory
    knowledge_base: KnowledgeBase
    identity: SymbolicIdentity
    ltm: LongTermMemory
    skills: SkillManager
    agent_pool: DynamicAgentPool
    evaluator: SymbolicEvaluator
    introspector: RecursiveIntrospector
    planner: Planner
    consciousness: Optional["Consciousness"]
    meta_cognition: MetaCognitionUnit
    goal_manager: GoalManager
    execution_engine: ExecutionEngine
    world: MicroWorld
    tools: ToolPlugin
    emotional_state: EmotionalState
    _perception_task: Optional[asyncio.Task[None]]
    perception_buffer: deque[PerceptionEvent]
    agent_tasks: List[asyncio.Task[None]]
    browser: Optional[Browser] = None
    page: Optional[Page] = None

    def __init__(
        self, cfg: Optional[AGIConfig] = None, world: Optional[MicroWorld] = None
    ) -> None:
        self.cfg = cfg or AGIConfig()
        self.name = self.cfg.name
        self.message_bus = RedisMessageBus()

        # Core components are initialized in the create() factory method
        self.memory = None # type: ignore
        self.knowledge_base = None # type: ignore
        self.identity = None # type: ignore
        self.ltm = None # type: ignore
        self.skills = None # type: ignore
        self.agent_pool = None # type: ignore
        self.planner = None # type: ignore
        self.introspector = None # type: ignore
        self.evaluator = None # type: ignore
        self.consciousness = None
        self.meta_cognition = None # type: ignore
        self.goal_manager = None # type: ignore
        self.execution_engine = None # type: ignore

        # Ready-to-use components
        self.world = world or MicroWorld()
        self.tools = ToolPlugin(self)
        self.emotional_state = EmotionalState()

        # Runtime state
        self._perception_task = None
        self.perception_buffer = deque(maxlen=100)
        self.agent_tasks = []

        atexit.register(self._sync_shutdown)

    @classmethod
    async def create(cls, cfg: Optional[AGIConfig] = None, world: Optional[MicroWorld] = None, db_path: str = config.DB_PATH) -> "SymbolicAGI":
        """Asynchronously initialize the AGI and its components in the correct order."""
        instance = cls(cfg, world)

        await instance.message_bus._initialize()

        instance.memory = await SymbolicMemory.create(client, db_path=db_path)
        instance.knowledge_base = await KnowledgeBase.create(db_path=db_path, memory_system=instance.memory)
        instance.identity = await SymbolicIdentity.create(instance.memory, db_path=db_path)
        instance.ltm = await LongTermMemory.create(db_path=db_path)
        instance.skills = await SkillManager.create(db_path=db_path, message_bus=instance.message_bus)
        instance.agent_pool = DynamicAgentPool(instance.message_bus, instance.skills)
        instance.evaluator = SymbolicEvaluator(instance.identity)
        instance.introspector = RecursiveIntrospector(instance.identity, client, debate_timeout=instance.cfg.debate_timeout_seconds)

        if instance.consciousness is None:
            from .consciousness import Consciousness as ConsciousnessClass
            instance.consciousness = await ConsciousnessClass.create(db_path=db_path)

        instance.planner = Planner(
            introspector=instance.introspector,
            skill_manager=instance.skills,
            agent_pool=instance.agent_pool,
            tool_plugin=instance.tools,
        )

        instance.meta_cognition = MetaCognitionUnit(instance)

        instance.goal_manager = GoalManager(max_concurrent_goals=3)
        instance.execution_engine = ExecutionEngine(instance, instance.goal_manager)

        await instance._create_essential_agents()

        instance.message_bus.subscribe(instance.name)
        return instance

    async def _create_essential_agents(self) -> None:
        """Create essential agents that the AGI needs to function properly."""
        essential_agents = [
            {"name": "QA_Agent_Alpha", "persona": "qa"},
            {"name": "Research_Agent_Beta", "persona": "researcher"},  
            {"name": "Code_Agent_Gamma", "persona": "developer"},
            {"name": "Analysis_Agent_Delta", "persona": "analyst"},
        ]

        for agent_data in essential_agents:
            await asyncio.sleep(0)
            self.agent_pool.add_agent(
                name=agent_data["name"],
                persona=agent_data["persona"], 
                memory=self.memory
            )
            logging.info(f"Auto-created essential agent: {agent_data['name']} ({agent_data['persona']})")

    async def start_background_tasks(self) -> None:
        """Start all background tasks including the new ExecutionEngine."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        logging.info("Playwright browser instance started.")

        if self.meta_cognition:
            await self.meta_cognition.run_background_tasks()

        if self.execution_engine:
            self._execution_engine_task = asyncio.create_task(self.execution_engine.execution_loop())
            logging.info("Execution engine loop started.")

        if self._perception_task is None:
            logging.info("Controller: Starting background perception task...")
            self._perception_task = asyncio.create_task(self._workspace_monitor_task())
        else:
            logging.warning("Controller: Background perception task already started.")

    def _sync_shutdown(self) -> None:
        """Synchronous shutdown for atexit."""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(self.shutdown())
            else:
                asyncio.run(self.shutdown())
        except RuntimeError:
            asyncio.run(self.shutdown())

    async def shutdown(self) -> None:
        """Shutdown all components including the new ExecutionEngine."""
        logging.info("Controller: Initiating shutdown...")

        if self.goal_manager:
            self.goal_manager.shutdown_event.set()

        if self.execution_engine:
            # The execution engine loop will stop due to the shutdown_event
            pass

        if self.meta_cognition:
            await self.meta_cognition.shutdown()

        if self._perception_task and not self._perception_task.done():
            self._perception_task.cancel()
            await asyncio.gather(self._perception_task, return_exceptions=True)

        for task in self.agent_tasks:
            task.cancel()
        await asyncio.gather(*self.agent_tasks, return_exceptions=True)
        logging.info("All specialist agent tasks have been cancelled.")

        if self.browser:
            await self.browser.close()
        if self.memory:
            await self.memory.shutdown()
        if self.message_bus:
            await self.message_bus.shutdown()

        logging.info("Controller: Shutdown complete.")

    async def process_goal_with_plan(self, goal_description: str) -> Dict[str, Any]:
        """
        Process a goal by decomposing it into a plan and executing it.
        This method is called by the ExecutionEngine and is focused purely on execution.
        """
        try:
            logging.info(f"Executing plan for goal: {goal_description}")

            planner_output = await self.planner.decompose_goal_into_plan(goal_description, "")

            if not planner_output.plan:
                return {"status": "failure", "description": "Failed to create a valid plan for the goal"}

            plan = planner_output.plan
            logging.info(f"📋 Created plan with {len(plan)} steps for goal '{goal_description}'")

            results = []
            for i, step in enumerate(plan, 1):
                logging.info(f"🔧 Executing step {i}/{len(plan)}: {step.action}")

                result = await self.execute_single_action(step)
                results.append(result)

                if result.get("status") != "success":
                    logging.error(f"❌ Step {i} failed: {result.get('description', 'Unknown error')}")
                    return {
                        "status": "failure",
                        "description": f"Plan execution failed at step {i}: {result.get('description')}",
                        "failed_step": step.model_dump(),
                        "results": results
                    }
                else:
                    logging.info(f"✅ Step {i} completed successfully.")

            successful_steps = [r for r in results if r.get("status") == "success"]
            final_result = {
                "status": "success",
                "description": f"Successfully executed plan for goal: {goal_description}",
                "steps_executed": len(results),
                "steps_successful": len(successful_steps),
                "results": results[-5:]
            }

            logging.info(f"🏁 Plan execution complete for goal: {goal_description}")
            return final_result

        except Exception as e:
            logging.error(f"❌ Goal processing failed critically: {e}", exc_info=True)
            return {"status": "failure", "description": f"Critical error during goal processing: {e}"}

    async def execute_single_action(self, step: ActionStep) -> Dict[str, Any]:
        """Execute a single action step, delegating to the ToolPlugin."""
        try:
            logging.info(f"Executing action: {step.action} with parameters: {step.parameters}")

            if hasattr(self.tools, step.action):
                action_func = getattr(self.tools, step.action)
                result = await action_func(**step.parameters)
            else:
                result = {"status": "failure", "description": f"Unknown action: {step.action}"}

            if result.get("status") == "success":
                logging.info(f"✅ Action '{step.action}' completed successfully")
            else:
                logging.warning(f"⚠️ Action '{step.action}' failed: {result.get('description', 'Unknown error')}")

            return result

        except Exception as e:
            error_result = {
                "status": "failure",
                "description": f"Action execution error: {str(e)}",
                "action": step.action,
                "error_type": type(e).__name__
            }
            logging.error(f"❌ Action '{step.action}' failed with exception: {e}", exc_info=True)
            return error_result

    async def _workspace_monitor_task(self) -> None:
        """Monitors the workspace directory for changes."""
        logging.info("Async workspace watchdog started.")
        workspace_path = os.path.abspath(self.tools.workspace_dir)
        try:
            async for changes in awatch(workspace_path):
                for change_type, path in changes:
                    file_path = os.path.relpath(path, workspace_path)
                    logging.info("PERCEPTION: Detected file change '%s' in workspace: %s", change_type.name, file_path)
                    event = PerceptionEvent(
                        type="file_modified",
                        source="workspace",
                        content={"change": change_type.name, "path": file_path},
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                    self.perception_buffer.append(event)
        except asyncio.CancelledError:
            logging.info("Async workspace watchdog has been cancelled.")
            raise
        except Exception as e:
            logging.error("Error in workspace watchdog task: %s", e, exc_info=True)
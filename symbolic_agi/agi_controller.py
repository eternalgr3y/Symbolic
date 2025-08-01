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
from .agent_pool import DynamicAgentPool
from .api_client import client
from .ethical_governance import SymbolicEvaluator  # Class not found
from .execution_unit import ExecutionUnit
from .long_term_memory import LongTermMemory
from .message_bus import RedisMessageBus
from .meta_cognition import MetaCognitionUnit
from .micro_world import MicroWorld
from .planner import Planner
from .recursive_introspector import RecursiveIntrospector
from .schemas import (
    ActionStep,
    AGIConfig,
    EmotionalState,
    GoalModel,
    MessageModel,
    PerceptionEvent,
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

    planner: Planner
    cfg: AGIConfig
    name: str
    memory: SymbolicMemory
    identity: SymbolicIdentity
    world: MicroWorld
    skills: SkillManager
    ltm: LongTermMemory
    tools: ToolPlugin
    introspector: RecursiveIntrospector
    evaluator: SymbolicEvaluator  # Class not found
    consciousness: Optional["Consciousness"]
    meta_cognition: MetaCognitionUnit
    execution_unit: ExecutionUnit
    message_bus: RedisMessageBus
    agent_pool: DynamicAgentPool
    emotional_state: EmotionalState
    _perception_task: Optional[asyncio.Task[None]]
    perception_buffer: deque[PerceptionEvent]
    workspaces: Dict[str, Dict[str, Any]]
    execution_history: Dict[str, List[Any]]
    orchestrator_actions: Dict[str, Callable[..., Any]]
    agent_tasks: List[asyncio.Task[None]]

    browser: Optional[Browser] = None
    page: Optional[Page] = None

    def __init__(
        self, cfg: Optional[AGIConfig] = None, world: Optional[MicroWorld] = None
    ) -> None:
        self.cfg = cfg or AGIConfig()
        self.name = self.cfg.name
        self.message_bus = RedisMessageBus()
        
        # Core components (initialized in create() factory method)
        self.memory = None # type: ignore
        self.identity = None # type: ignore
        self.ltm = None # type: ignore
        self.skills = None # type: ignore
        self.agent_pool = None # type: ignore
        self.planner = None # type: ignore
        self.introspector = None # type: ignore
        self.consciousness = None
        
        # Ready-to-use components
        self.world = world or MicroWorld()
        self.tools = ToolPlugin(self)
        self.execution_unit = ExecutionUnit(self)
        self.emotional_state = EmotionalState()
        
        # Runtime state
        self._perception_task = None
        self.perception_buffer = deque(maxlen=100)
        self.workspaces = {}
        self.execution_history = {}
        self.agent_tasks = []

        # Built-in orchestrator actions
        self.orchestrator_actions = {
            "create_long_term_goal_with_sub_tasks": self._action_create_goal,
            "respond_to_user": self._action_respond_to_user,
            "review_plan": self._action_review_plan,  # Add fallback for QA
        }
 
        atexit.register(self._sync_shutdown)
    
    @classmethod
    async def create(cls, cfg: Optional[AGIConfig] = None, world: Optional[MicroWorld] = None, db_path: str = config.DB_PATH) -> "SymbolicAGI":
        """Asynchronously initialize the AGI and its components."""
        instance = cls(cfg, world)
        instance.memory = await SymbolicMemory.create(client, db_path=db_path)
        instance.identity = await SymbolicIdentity.create(instance.memory, db_path=db_path)
        instance.ltm = await LongTermMemory.create(db_path=db_path)
        instance.skills = await SkillManager.create(db_path=db_path, message_bus=instance.message_bus)
        instance.agent_pool = DynamicAgentPool(instance.message_bus, instance.skills)
        instance.evaluator = SymbolicEvaluator(instance.identity)  # Class not found
        instance.introspector = RecursiveIntrospector(instance.identity, client, debate_timeout=instance.cfg.debate_timeout_seconds)
        instance.introspector.get_emotional_state = lambda: instance.emotional_state.model_dump()
        instance.planner = Planner(
            introspector=instance.introspector,
            skill_manager=instance.skills,
            agent_pool=instance.agent_pool,
            tool_plugin=instance.tools,
        )
        if instance.consciousness is None:
            from .consciousness import Consciousness as ConsciousnessClass
            instance.consciousness = await ConsciousnessClass.create(db_path=db_path)
        
        instance.meta_cognition = MetaCognitionUnit(instance)
        
        # Create essential agents automatically
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
            self.agent_pool.add_agent(
                name=agent_data["name"],
                persona=agent_data["persona"], 
                memory=self.memory
            )
            logging.info(f"Auto-created essential agent: {agent_data['name']} ({agent_data['persona']})")

    async def start_background_tasks(self) -> None:
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        logging.info("Playwright browser instance started.")

        if self.meta_cognition:
            await self.meta_cognition.run_background_tasks()

        if self._perception_task is None:
            logging.info("Controller: Starting background perception task...")
            self._perception_task = asyncio.create_task(self._workspace_monitor_task())
        else:
            logging.warning("Controller: Background perception task already started.")

    def _sync_shutdown(self) -> None:
        """Synchronous shutdown for atexit."""
        asyncio.run(self.shutdown())

    async def shutdown(self) -> None:
        logging.info("Controller: Initiating shutdown...")
        if self.meta_cognition:
            await self.meta_cognition.shutdown()

        if self._perception_task and not self._perception_task.done():
            self._perception_task.cancel()
            try:
                await self._perception_task
            except asyncio.CancelledError:
                logging.info("Background perception task successfully cancelled.")

        for task in self.agent_tasks:
            task.cancel()
        await asyncio.gather(*self.agent_tasks, return_exceptions=True)
        logging.info("All specialist agent tasks have been cancelled.")

        if self.browser:
            try:
                await self.browser.close()
                logging.info("Playwright browser instance closed.")
            except Exception as e:
                logging.debug("Browser already closed or error during close: %s", e)

        if self.memory:
            await self.memory.shutdown()

        if self.message_bus:
            await self.message_bus.shutdown()

        logging.info("Controller: Shutdown complete.")

    async def delegate_task_and_wait(
        self, receiver_id: str, step: ActionStep
    ) -> Optional[MessageModel]:
        orchestrator_queue = self.message_bus.agent_queues.get(self.name)
        if not orchestrator_queue:
            logging.error(
                "Orchestrator is not subscribed to the message bus. Cannot delegate."
            )
            return None

        task_message = MessageModel(
            sender_id=self.name,
            receiver_id=receiver_id,
            message_type=step.action,
            payload=step.parameters,
        )
        await self.message_bus.publish(task_message)
        logging.info(
            "[Delegate] Delegated task '%s' to '%s'. Waiting for reply...",
            step.action,
            receiver_id,
        )

        try:
            timeout = self.cfg.meta_task_timeout
            reply: Any = await asyncio.wait_for(orchestrator_queue.get(), timeout=timeout)
            if reply is None:
                logging.warning(
                    "Received shutdown signal while waiting for reply from '%s'.",
                    receiver_id,
                )
                return None

            typed_reply = cast(MessageModel, reply)
            logging.info(
                "[Delegate] Received reply of type '%s' from '%s'.",
                typed_reply.message_type,
                typed_reply.sender_id,
            )
            orchestrator_queue.task_done()
            return typed_reply
        except asyncio.TimeoutError:
            logging.error(
                "Timeout: No reply received from '%s' for task '%s'.",
                receiver_id,
                step.action,
            )
            return None

    async def execute_plan(self, plan: List[ActionStep]) -> None:
        logging.info("Executing an internal plan with %d steps.", len(plan))
        for step in plan:
            result = await self.execute_single_action(step)
            if result.get("status") != "success":
                logging.error(
                    "Internal plan execution failed at step '%s': %s",
                    step.action,
                    result.get("description"),
                )
                break

    async def execute_single_action(self, step: ActionStep) -> Dict[str, Any]:
        """Execute a single action step with fallback strategies."""
        self.identity.consume_energy()
        try:
            # Try orchestrator actions first
            if step.action in self.orchestrator_actions:
                action_func = self.orchestrator_actions[step.action]
                return cast(Dict[str, Any], await action_func(**step.parameters))

            # Try tool methods
            tool_method = getattr(self.tools, step.action, None)
            if tool_method and asyncio.iscoroutinefunction(tool_method):
                # Add workspace context for tools
                active_goal = await self.ltm.get_active_goal()
                if active_goal:
                    workspace = self.workspaces.setdefault(active_goal.id, {})
                    step.parameters["workspace"] = workspace
                result = await tool_method(**step.parameters)
                return cast(Dict[str, Any], result)

            # Try world actions
            world_action = getattr(self.world, f"_action_{step.action}", None)
            if callable(world_action):
                if asyncio.iscoroutinefunction(world_action):
                    world_result = await world_action(**step.parameters)
                else:
                    world_result = world_action(**step.parameters)
                return cast(Dict[str, Any], world_result)

            return {
                "status": "failure",
                "description": f"Unknown action: {step.action}",
            }
        except Exception as e:
            logging.error("Error executing action '%s': %s", step.action, e, exc_info=True)
            return {
                "status": "failure",
                "description": f"Execution error: {e}",
            }

    async def _action_create_goal(self, description: str, sub_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Creates a new long-term goal with predefined plan."""
        plan = [ActionStep.model_validate(s) for s in sub_tasks]
        goal = GoalModel(description=description, sub_tasks=plan, original_plan=plan)
        await self.ltm.add_goal(goal)
        logging.info("Successfully created new long-term goal '%s' with %d steps.", goal.id, len(plan))
        return {
            "status": "success",
            "description": "Goal created.",
            "goal_id": goal.id,
        }

    async def _action_respond_to_user(self, text: str) -> Dict[str, Any]:
        return {"status": "success", "response_text": text}

    async def _action_review_plan(self, **kwargs: Any) -> Dict[str, Any]:
        """Fallback plan review when QA agents are not available."""
        logging.info("Performing orchestrator-level plan review")
        
        # Simple approval logic - in a real system this would be more sophisticated
        workspace = kwargs.get("workspace", {})
        goal_description = workspace.get("goal_description", "unknown goal")
        
        # Basic safety checks
        if any(word in goal_description.lower() for word in ["delete", "remove", "destroy", "harm"]):
            return {
                "status": "success",
                "approved": False,
                "feedback": "Plan rejected due to potentially destructive actions"
            }
        
        # Approve most plans by default
        return {
            "status": "success", 
            "approved": True,
            "feedback": "Plan approved by orchestrator review"
        }

    def wrap_content(self, value: Any, default_key: str = "text") -> Dict[str, Any]:
        if isinstance(value, dict):
            return cast(Dict[str, Any], value)
        return {default_key: value}

    async def _workspace_monitor_task(self) -> None:
        """
        Uses watchfiles to efficiently monitor the workspace directory for changes.
        This is an event-driven approach, superior to polling.
        """
        logging.info("Async workspace watchdog started.")
        workspace_path = os.path.abspath(self.tools.workspace_dir)
        try:
            async for changes in awatch(workspace_path):
                for change_type, path in changes:
                    file_path = os.path.relpath(path, workspace_path)
                    logging.info(
                        "PERCEPTION: Detected file change '%s' in workspace: %s",
                        change_type.name,
                        file_path,
                    )
                    event = PerceptionEvent(
                        type="file_modified",
                        source="workspace",
                        content={"change": change_type.name, "path": file_path},
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                    self.perception_buffer.append(event)
        except asyncio.CancelledError:
            logging.info("Async workspace watchdog has been cancelled.")
        except Exception as e:
            logging.error("Error in workspace watchdog task: %s", e, exc_info=True)

    async def startup_validation(self) -> None:
        """Validates and repairs any malformed goals during startup."""
        logging.info("Running startup validation…")
        for goal in list(self.ltm.goals.values()):
            if not goal.sub_tasks and goal.status == "active":
                logging.warning(
                    "Found active goal '%s' with no plan. Decomposing now.", goal.description
                )
                planner_output = await self.planner.decompose_goal_into_plan(
                    goal.description, ""
                )
                if planner_output.plan:
                    await self.ltm.update_plan(goal.id, planner_output.plan)
                else:
                    await self.ltm.invalidate_plan(
                        goal.id, "Failed to create a valid plan on startup."
                    )
# symbolic_agi/agi_controller.py

import asyncio
import logging
from collections import deque
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, cast

from playwright.async_api import Browser, Page, async_playwright

from .agent_pool import DynamicAgentPool
from .api_client import client
from .ethical_governance import SymbolicEvaluator
from .execution_unit import ExecutionUnit
from .long_term_memory import LongTermMemory
from .message_bus import MessageBus
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
    evaluator: SymbolicEvaluator
    consciousness: Optional["Consciousness"]
    meta_cognition: MetaCognitionUnit
    execution_unit: ExecutionUnit
    message_bus: MessageBus
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
        self, cfg: AGIConfig = AGIConfig(), world: Optional[MicroWorld] = None
    ) -> None:
        self.cfg = cfg
        self.name = cfg.name
        self.message_bus = MessageBus()
        self.memory = SymbolicMemory(client)
        self.identity = SymbolicIdentity(self.memory)
        self.world = world or MicroWorld()
        self.skills = SkillManager(message_bus=self.message_bus)

        self.ltm = LongTermMemory()
        self.tools = ToolPlugin(self)
        self.introspector = RecursiveIntrospector(
            self.identity, client, debate_timeout=self.cfg.debate_timeout_seconds
        )
        self.evaluator = SymbolicEvaluator(self.identity)
        self.agent_pool = DynamicAgentPool(self.message_bus, self.skills)

        self.planner = Planner(
            introspector=self.introspector,
            skill_manager=self.skills,
            agent_pool=self.agent_pool,
            tool_plugin=self.tools,
        )

        try:
            from .consciousness import Consciousness as ConsciousnessClass

            self.consciousness = ConsciousnessClass()
        except ImportError:
            self.consciousness = None

        self.meta_cognition = MetaCognitionUnit(self)
        self.execution_unit = ExecutionUnit(self)

        self.message_bus.subscribe(self.name)
        self.emotional_state = EmotionalState()
        self.introspector.get_emotional_state = (
            lambda: self.emotional_state.model_dump()
        )
        self._perception_task = None
        self.perception_buffer = deque(maxlen=100)
        self.workspaces = {}
        self.execution_history = {}
        self.agent_tasks = []

        self.orchestrator_actions = {
            "create_long_term_goal_with_sub_tasks": self._action_create_goal,
            "respond_to_user": self._action_respond_to_user,
            "provision_agent": self.tools.provision_agent,
            "browser_new_page": self.tools.browser_new_page,
            "browser_click": self.tools.browser_click,
            "browser_fill": self.tools.browser_fill,
            "browser_get_content": self.tools.browser_get_content,
        }

    async def start_background_tasks(self) -> None:
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)
        logging.info("Playwright browser instance started.")

        await self.meta_cognition.run_background_tasks()

        if self._perception_task is None:
            logging.info("Controller: Starting background perception task...")
            self._perception_task = asyncio.create_task(self._workspace_monitor_task())
        else:
            logging.warning("Controller: Background perception task already started.")

    async def shutdown(self) -> None:
        logging.info("Controller: Initiating shutdown...")
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
                logging.error("Error closing browser, may already be closed: %s", e)

        if self.identity:
            self.identity.save_profile()

        if self.memory:
            await self.memory.shutdown()
            await self.memory.save()
            self.memory.rebuild_index()

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
        self.identity.consume_energy()
        try:
            if step.action in self.orchestrator_actions:
                action_func = self.orchestrator_actions[step.action]
                return cast(Dict[str, Any], await action_func(**step.parameters))

            tool_method = getattr(self.tools, step.action, None)

            if tool_method and asyncio.iscoroutinefunction(tool_method):
                active_goal = self.ltm.get_active_goal()
                if active_goal:
                    workspace = self.workspaces.setdefault(active_goal.id, {})
                    step.parameters["workspace"] = workspace
                result = await tool_method(**step.parameters)
                return cast(Dict[str, Any], result)

            world_action = getattr(self.world, f"_action_{step.action}", None)
            if callable(world_action):
                world_result: Any
                if asyncio.iscoroutinefunction(world_action):
                    world_result = await world_action(**step.parameters)
                else:
                    world_result = world_action(**step.parameters)
                return cast(Dict[str, Any], world_result)

            return {
                "status": "failure",
                "description": f"Unknown or non-awaitable action: {step.action}",
            }
        except Exception as e:
            logging.error(
                "Critical error executing action '%s': %s",
                step.action,
                e,
                exc_info=True,
            )
            return {
                "status": "failure",
                "description": f"An unexpected error occurred: {e}",
            }

    async def _action_create_goal(
        self, description: str, sub_tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Creates a new long-term goal, either with a predefined plan or by generating one."""
        plan = [ActionStep.model_validate(s) for s in sub_tasks]
        goal = GoalModel(description=description, sub_tasks=plan, original_plan=plan)
        self.ltm.add_goal(goal)
        logging.info(
            "Successfully created new long-term goal '%s' with %d steps.",
            goal.id,
            len(plan),
        )
        result: Dict[str, Any] = {
            "status": "success",
            "description": "Goal created.",
            "goal_id": goal.id,
        }
        return result

    async def _action_respond_to_user(self, text: str) -> Dict[str, Any]:
        return {"status": "success", "response_text": text}

    def wrap_content(self, value: Any, default_key: str = "text") -> Dict[str, Any]:
        if isinstance(value, dict):
            return cast(Dict[str, Any], value)
        return {default_key: value}

    async def _workspace_monitor_task(self) -> None:
        logging.info("Workspace monitor task started.")
        known_files: Set[str] = set()

        try:
            initial_files = await self.tools.list_files()
            if initial_files.get("status") == "success":
                files_list = cast(List[str], initial_files.get("files", []))
                known_files.update(files_list)
        except Exception as e:
            logging.error("Error during initial workspace scan: %s", e)

        while True:
            await asyncio.sleep(5)
            try:
                current_files_result = await self.tools.list_files()
                if current_files_result.get("status") != "success":
                    continue

                current_files_list = cast(
                    List[str], current_files_result.get("files", [])
                )
                current_files: Set[str] = set(current_files_list)
                new_files: Set[str] = current_files - known_files

                for file in new_files:
                    event = PerceptionEvent(
                        source="workspace",
                        type="file_created",
                        content={"file_path": file},
                    )
                    self.perception_buffer.append(event)
                    logging.info(
                        "PERCEPTION: New file detected in workspace: %s", file
                    )

                known_files = current_files
            except Exception as e:
                logging.error("Error in workspace monitor task: %s", e, exc_info=True)

    async def startup_validation(self) -> None:
        """Validates and repairs any malformed goals during startup."""
        logging.info("Running startup validation…")
        needs_saving = False
        for goal in list(self.ltm.goals.values()):
            if not goal.sub_tasks and goal.status == "active":
                logging.warning(
                    "Found active goal '%s' with no plan. Decomposing now.", goal.id
                )
                planner_output = await self.planner.decompose_goal_into_plan(
                    goal.description, ""
                )
                if planner_output.plan:
                    self.ltm.update_plan(goal.id, planner_output.plan)
                    needs_saving = True
                else:
                    self.ltm.invalidate_plan(
                        goal.id, "Failed to create a valid plan on startup."
                    )

        if needs_saving:
            self.ltm.save()

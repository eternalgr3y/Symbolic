import asyncio
import atexit
import logging
import os
from collections import deque
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, cast

from playwright.async_api import Browser, Page, async_playwright
from watchfiles import awatch

if TYPE_CHECKING:
    from .consciousness import Consciousness

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
    ActionStep,
    AGIConfig,
    EmotionalState,
    GoalModel,
    MessageModel,
    PerceptionEvent
)
from .skill_manager import SkillManager
from .symbolic_identity import SymbolicIdentity
from .symbolic_memory import SymbolicMemory
from .tool_plugin import ToolPlugin

if TYPE_CHECKING:
    from .consciousness import Consciousness

class SymbolicAGI:
    """The core class for the Symbolic AGI. Acts as a dependency container."""
    
    def __init__(self, cfg: AGIConfig):
        self.cfg = cfg
        self.shutdown_event = asyncio.Event()
        self._background_tasks: list[asyncio.Task] = []
        self._execution_engine_task: Optional[asyncio.Task] = None
        self._perception_task: Optional[asyncio.Task] = None
        
    @classmethod
    async def create(cls) -> "SymbolicAGI":
        """Asynchronously initialize the AGI and its components in the correct order."""
        cfg = config.get_config()
        instance = cls(cfg)

        instance.message_bus = RedisMessageBus()
        await instance.message_bus._initialize()
        instance.memory = await SymbolicMemory.create(client)
        instance.identity = await SymbolicIdentity.create(instance.memory)
        instance.knowledge_base = await KnowledgeBase.create(memory_system=instance.memory)
        instance.ltm = await LongTermMemory.create()
        instance.skills = await SkillManager.create(message_bus=instance.message_bus)
        instance.agent_pool = DynamicAgentPool(instance.message_bus, instance.skills)
        instance.consciousness = await consciousness.Consciousness.create()
        instance.evaluator = SymbolicEvaluator(instance.identity)
        instance.tools = ToolPlugin(instance)

        instance.introspector = RecursiveIntrospector(
            identity=instance.identity,
            client=client,
            debate_timeout=instance.cfg.debate_timeout_seconds
        )
        
        instance.world = MicroWorld(workspace_dir=instance.cfg.workspace_dir)
        instance.planner = Planner(
            tools=instance.tools,
            agent_pool=instance.agent_pool,
            skills=instance.skills,
            introspector=instance.introspector
        )
        
        instance.goal_manager = GoalManager(instance.ltm)
        instance.execution_engine = ExecutionEngine(
            agi=instance,
            goal_manager=instance.goal_manager,
            planner=instance.planner,
            introspector=instance.introspector
        )
        
        instance.meta_cognition = MetaCognitionUnit(instance)
        instance.emotional_state = EmotionalState()
        instance.perception_buffer = deque(maxlen=100)
        instance.agent_tasks: List[asyncio.Task] = []
        instance.browser: Optional[Browser] = None
        instance.page: Optional[Page] = None

        # Register sync shutdown handler
        instance._sync_shutdown = lambda: asyncio.run(instance.shutdown())
        atexit.register(instance._sync_shutdown)
        
        # Create essential agents
        instance._create_essential_agents()
        
        return instance

    def _create_essential_agents(self) -> None:
        """Create essential agents that the AGI needs to function properly."""
        essential_personas = ["qa", "research", "coding"]
        for persona in essential_personas:
            agent_name = f"{persona.title()}_Agent_{persona[:2].upper()}"
            if agent_name not in self.agent_pool.agents:
                self.agent_pool.create_agent(agent_name, persona)
                logging.info(f"Auto-created essential agent: {agent_name} ({persona})")

    async def start_background_tasks(self) -> None:
        """Starts and manages all background tasks."""
        # Start execution engine
        self._execution_engine_task = asyncio.create_task(
            self.execution_engine.run()
        )
        self._background_tasks.append(self._execution_engine_task)
        
        # Start perception processing
        self._perception_task = asyncio.create_task(
            self._process_perception_events()
        )
        self._background_tasks.append(self._perception_task)
        
        # Start meta-cognition
        await self.meta_cognition.run_background_tasks()

    async def _process_perception_events(self) -> None:
        """Process perception events from the buffer."""
        while not self.shutdown_event.is_set():
            try:
                if self.perception_buffer:
                    event = self.perception_buffer.popleft()
                    # Process the event with timeout
                    try:
                        await asyncio.wait_for(
                            self._handle_perception_event(event),
                            timeout=5.0
                        )
                    except asyncio.TimeoutError:
                        logging.warning(f"Perception event processing timed out: {event}")
                    
                await asyncio.sleep(1.0)  # Increased from 0.1s to reduce CPU usage
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logging.error(f"Error processing perception event: {e}")
                await asyncio.sleep(5.0)  # Back off on errors

    async def _handle_perception_event(self, event: PerceptionEvent) -> None:
        """Handle a single perception event."""
        logging.debug(f"Processing perception event: {event}")
        # Add actual event processing logic here if needed

    async def shutdown(self):
        """Gracefully shuts down all components."""
        logging.info("Shutting down AGI components...")
        self.shutdown_event.set()
        
        # Cancel background tasks with timeout
        for task in self._background_tasks:
            if task and not task.done():
                task.cancel()
                
        # Wait for tasks to complete with timeout
        if self._background_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._background_tasks, return_exceptions=True),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                logging.warning("Background tasks didn't shutdown within timeout")
            
        # Shutdown components with error handling
        shutdown_tasks = []
        
        if hasattr(self, 'agent_pool'):
            shutdown_tasks.append(self._safe_shutdown(self.agent_pool.shutdown(), "agent_pool"))
        if hasattr(self, 'message_bus'):
            shutdown_tasks.append(self._safe_shutdown(self.message_bus.shutdown(), "message_bus"))
        # Note: meta_cognition doesn't have shutdown method, skip it
            
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)
            
        logging.info("AGI shutdown complete")

    async def _safe_shutdown(self, coro, component_name: str):
        """Safely shutdown a component with timeout and error handling."""
        try:
            await asyncio.wait_for(coro, timeout=5.0)
            logging.debug(f"Successfully shutdown {component_name}")
        except asyncio.TimeoutError:
            logging.warning(f"Timeout shutting down {component_name}")
        except Exception as e:
            logging.error(f"Error shutting down {component_name}: {e}")

    def get_current_state(self) -> str:
        """Returns a summary of the AGI's current state."""
        active_goals = self.goal_manager.get_active_goals()
        return f"Active goals: {len(active_goals)}, Energy: {self.identity.cognitive_energy}"

# Import Consciousness at the bottom to avoid circular imports
from . import consciousness
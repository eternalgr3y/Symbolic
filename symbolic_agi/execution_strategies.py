# Create execution_strategies.py for delegation and execution logic
# symbolic_agi/execution_strategies.py

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

from .schemas import ActionStep, GoalModel

if TYPE_CHECKING:
    from .agi_controller import SymbolicAGI


class ExecutionStrategy:
    """Base class for different execution strategies."""
    
    def __init__(self, agi: "SymbolicAGI"):
        self.agi = agi
    
    async def execute_step(self, step: ActionStep, goal: GoalModel) -> bool:
        """Execute a single step. Override in subclasses."""
        raise NotImplementedError


class DirectExecutionStrategy(ExecutionStrategy):
    """Execute steps directly through the orchestrator."""
    
    async def execute_step(self, step: ActionStep, goal: GoalModel) -> bool:
        try:
            result = await self.agi.execute_single_action(step)
            return result.get("status") == "success"
        except Exception as e:
            logging.error(f"Direct execution failed for {step.action}: {e}")
            return False


class SmartDelegationStrategy(ExecutionStrategy):
    """Intelligent delegation with performance tracking."""
    
    def __init__(self, agi: "SymbolicAGI", agent_performance: Dict[str, Any]):
        super().__init__(agi)
        self.agent_performance = agent_performance
    
    async def execute_step(self, step: ActionStep, goal: GoalModel) -> bool:
        if step.assigned_persona == "orchestrator":
            # Fallback to direct execution
            direct_strategy = DirectExecutionStrategy(self.agi)
            return await direct_strategy.execute_step(step, goal)
        
        # Try delegation
        best_agent = self._select_optimal_agent(step)
        if not best_agent:
            logging.info(f"No suitable agent for {step.action}, using direct execution")
            direct_strategy = DirectExecutionStrategy(self.agi)
            return await direct_strategy.execute_step(step, goal)
        
        return await self._delegate_to_agent(best_agent, step, goal)
    
    def _select_optimal_agent(self, step: ActionStep) -> Optional[str]:
        """Select best agent based on performance metrics."""
        # Get agents with matching persona
        available_agents = self.agi.agent_pool.get_agents_by_persona(step.assigned_persona)
        
        if not available_agents:
            return None
        
        # Simple selection: first available agent (can be enhanced)
        return available_agents[0]
    
    async def _delegate_to_agent(self, agent_id: str, step: ActionStep, goal: GoalModel) -> bool:
        """Delegate task to specific agent."""
        try:
            reply = await self.agi.delegate_task_and_wait(agent_id, step)
            return reply is not None and hasattr(reply, 'message_type') and reply.message_type == "task_completed"
        except Exception as e:
            logging.error(f"Delegation to {agent_id} failed: {e}")
            return False


class HybridExecutionStrategy(ExecutionStrategy):
    """Combines delegation with fallback to direct execution."""
    
    def __init__(self, agi: "SymbolicAGI", agent_performance: Dict[str, Any]):
        super().__init__(agi)
        self.delegation_strategy = SmartDelegationStrategy(agi, agent_performance)
        self.direct_strategy = DirectExecutionStrategy(agi)
    
    async def execute_step(self, step: ActionStep, goal: GoalModel) -> bool:
        # Try delegation first
        if step.assigned_persona != "orchestrator" and self.agi.agent_pool:
            success = await self.delegation_strategy.execute_step(step, goal)
            if success:
                return True
            
            logging.info(f"Delegation failed for {step.action}, falling back to direct execution")
        
        # Fallback to direct execution
        return await self.direct_strategy.execute_step(step, goal)
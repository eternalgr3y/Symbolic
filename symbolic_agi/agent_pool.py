# symbolic_agi/agent_pool.py
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast, Optional, Dict, List
import asyncio
import time

from . import config, metrics
from .message_bus import RedisMessageBus
from .symbolic_identity import SymbolicIdentity
from .symbolic_memory import SymbolicMemory

if TYPE_CHECKING:
    from .skill_manager import SkillManager

class DynamicAgentPool:
    """Manages a pool of specialist agents."""
    
    def __init__(self, message_bus: RedisMessageBus, skills: "SkillManager"):
        self.message_bus = message_bus
        self.skills = skills
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.agent_performance: Dict[str, float] = {}
        logging.info("[AgentPool] Initialized.")

    def create_agent(self, agent_name: str, persona: str, trust_score: float = 0.5) -> None:
        """Create a new agent in the pool."""
        if agent_name in self.agents:
            logging.warning(f"Agent {agent_name} already exists")
            return
            
        self.agents[agent_name] = {
            "persona": persona,
            "trust_score": trust_score,
            "state": {
                "total_tasks": 0,
                "successful_tasks": 0,
                "last_used_timestamp": None
            }
        }
        self.agent_performance[agent_name] = trust_score
        
        logging.info(f"[AgentPool] Added agent: {agent_name} with persona: {persona} and trust: {trust_score}")
        metrics.AGENT_TRUST.labels(agent_name=agent_name, persona=persona).set(trust_score)

    def record_task_performance(self, agent_name: str, success: bool, task_complexity: float) -> None:
        """Record task performance for an agent."""
        if agent_name not in self.agents:
            return
            
        agent = self.agents[agent_name]
        agent["state"]["total_tasks"] += 1
        
        if success:
            agent["state"]["successful_tasks"] += 1
            # Increase trust
            old_trust = agent["trust_score"]
            agent["trust_score"] = min(
                config.get_config().max_trust_score,
                old_trust + config.get_config().trust_reward_rate * task_complexity
            )
        else:
            # Decrease trust
            old_trust = agent["trust_score"]
            agent["trust_score"] = max(
                0.0,
                old_trust - config.get_config().trust_decay_rate * task_complexity
            )
        
        self.agent_performance[agent_name] = agent["trust_score"]
        metrics.AGENT_TRUST.labels(agent_name=agent_name, persona=agent["persona"]).set(agent["trust_score"])

    async def delegate_task(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Delegate a task to an appropriate agent."""
        # Select best agent based on trust scores
        if not self.agents:
            logging.error("No agents available in pool")
            return None

        # Sort agents by trust score
        sorted_agents = sorted(
            self.agents.items(),
            key=lambda x: x[1]["trust_score"],
            reverse=True
        )

        # Try agents in order of trust
        for agent_name, agent_info in sorted_agents:
            try:
                # Send task to agent
                message = {
                    "sender": "agent_pool",
                    "recipient": agent_name,
                    "content": task,
                    "correlation_id": task.get("correlation_id")
                }

                await self.message_bus.publish(agent_name, message)

                # Wait for response
                response_channel = f"{agent_name}_response"
                response_queue = self.message_bus.subscribe(response_channel)

                # Use a timeout context manager (default 30 seconds)
                try:
                    async with asyncio.timeout(30.0):
                        response = await response_queue.get()
                except AttributeError:
                    # For Python <3.11 fallback to asyncio.wait_for
                    response = await asyncio.wait_for(response_queue.get(), timeout=30.0)

                if response:
                    # Update agent stats
                    agent_info["state"]["last_used_timestamp"] = datetime.now(timezone.utc).isoformat()
                    return response.content

            except asyncio.TimeoutError:
                logging.warning(f"Agent {agent_name} timed out on task")
                self.record_task_performance(agent_name, False, 0.5)
            except Exception as e:
                logging.error(f"Error delegating to {agent_name}: {e}")

        return None

    def shutdown(self) -> None:
        """Shutdown the agent pool."""
        logging.info("[AgentPool] Shutting down...")
        # No specific cleanup needed
        logging.info("[AgentPool] Shutdown complete")
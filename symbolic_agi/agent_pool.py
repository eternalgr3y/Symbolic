# symbolic_agi/agent_pool.py

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast, Optional
import asyncio
import time

from . import config, metrics
from .message_bus import RedisMessageBus
from .symbolic_identity import SymbolicIdentity
from .symbolic_memory import SymbolicMemory

if TYPE_CHECKING:
    from .skill_manager import SkillManager


class DynamicAgentPool:
    """Manages a collection of sub-agents with different personas and persistent state."""

    skill_manager: "SkillManager"

    def __init__(
        self: "DynamicAgentPool", bus: RedisMessageBus, skill_manager: "SkillManager"
    ):
        self.subagents: dict[str, dict[str, Any]] = {}
        self.bus: RedisMessageBus = bus
        self.skill_manager = skill_manager
        logging.info("[AgentPool] Initialized.")

    def add_agent(
        self: "DynamicAgentPool", name: str, persona: str, memory: SymbolicMemory
    ) -> None:
        """Adds a new sub-agent to the pool, initializing its state and trust score."""
        if name in self.subagents:
            logging.warning("Agent with name '%s' already exists. Not adding.", name)
            return

        self.subagents[name] = {
            "name": name,
            "persona": persona.lower(),
            "identity": SymbolicIdentity(memory),
            "memory": memory,
            "state": {
                "trust_score": config.INITIAL_TRUST_SCORE,
                "last_used_timestamp": datetime.now(timezone.utc).isoformat(),
                "performance_history": [],  # Track recent performance
                "trust_momentum": 0.0,  # Trust change velocity
                "total_tasks": 0,
                "successful_tasks": 0,
                "consecutive_failures": 0,
            },
        }
        self.bus.subscribe(name)
        metrics.AGENT_TRUST.labels(agent_name=name, persona=persona.lower()).set(
            config.INITIAL_TRUST_SCORE
        )
        logging.info(
            "[AgentPool] Added agent: %s with persona: %s and trust: %s",
            name,
            persona.lower(),
            config.INITIAL_TRUST_SCORE,
        )

    def get_agent_state(self: "DynamicAgentPool", agent_name: str) -> dict[str, Any]:
        """Retrieves the state dictionary for a specific agent."""
        agent = self.subagents.get(agent_name)
        if agent:
            return cast("dict[str, Any]", agent.get("state", {}))
        return {}

    def update_agent_state(
        self: "DynamicAgentPool", agent_name: str, updates: dict[str, Any]
    ) -> None:
        """Updates the state dictionary for a specific agent."""
        if agent_name in self.subagents:
            self.subagents[agent_name]["state"].update(updates)
            logging.info(
                "Updated state for agent '%s'. New keys: %s",
                agent_name,
                list(updates.keys()),
            )
        else:
            logging.warning(
                "Attempted to update state for non-existent agent: %s", agent_name
            )

    def update_trust_score(
        self, agent_name: str, new_score: float, last_used: bool = True
    ) -> None:
        """Updates the trust score for a specific agent and optionally the last used timestamp."""
        if agent_name in self.subagents:
            old_score = self.subagents[agent_name]["state"]["trust_score"]
            clamped_score = max(0.0, min(config.MAX_TRUST_SCORE, new_score))
            
            # Calculate trust momentum (rate of change)
            trust_momentum = clamped_score - old_score
            
            self.subagents[agent_name]["state"]["trust_score"] = clamped_score
            self.subagents[agent_name]["state"]["trust_momentum"] = trust_momentum
            
            if last_used:
                self.subagents[agent_name]["state"]["last_used_timestamp"] = (
                    datetime.now(timezone.utc).isoformat()
                )
            
            metrics.AGENT_TRUST.labels(
                agent_name=agent_name,
                persona=self.subagents[agent_name]["persona"],
            ).set(clamped_score)
            
            logging.debug(f"Updated trust for {agent_name}: {old_score:.2f} -> {clamped_score:.2f} (momentum: {trust_momentum:+.2f})")
        else:
            logging.warning(
                "Attempted to update trust for non-existent agent: %s", agent_name
            )

    def record_task_performance(self, agent_name: str, success: bool, task_complexity: float = 0.5) -> None:
        """Record task performance and update trust based on performance momentum."""
        if agent_name not in self.subagents:
            logging.warning(f"Cannot record performance for non-existent agent: {agent_name}")
            return
        
        agent_state = self.subagents[agent_name]["state"]
        
        # Update counters
        agent_state["total_tasks"] += 1
        if success:
            agent_state["successful_tasks"] += 1
            agent_state["consecutive_failures"] = 0
        else:
            agent_state["consecutive_failures"] += 1
        
        # Track performance history (last 10 tasks)
        performance_history = agent_state["performance_history"]
        performance_history.append({
            "success": success,
            "complexity": task_complexity,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Keep only recent history
        if len(performance_history) > 10:
            performance_history.pop(0)
        
        # Calculate trust adjustment based on performance momentum
        trust_adjustment = self._calculate_trust_adjustment(agent_state, success, task_complexity)
        
        # Update trust score
        current_trust = agent_state["trust_score"]
        new_trust = max(0.0, min(config.MAX_TRUST_SCORE, current_trust + trust_adjustment))
        
        self.update_trust_score(agent_name, new_trust)
        
        logging.info(f"Recorded performance for {agent_name}: success={success}, trust_change={trust_adjustment:+.3f}")

    def _calculate_trust_adjustment(self, agent_state: dict[str, Any], success: bool, task_complexity: float) -> float:
        """Calculate trust adjustment based on performance momentum and emotional context."""
        base_adjustment = config.TRUST_DECAY_RATE if not success else config.TRUST_DECAY_RATE * 0.5
        
        # Scale by task complexity
        base_adjustment *= (1.0 + task_complexity)
        
        # Consider consecutive failures
        consecutive_failures = agent_state.get("consecutive_failures", 0)
        if consecutive_failures > 2:
            base_adjustment *= (1.0 + consecutive_failures * 0.2)
        
        # Consider recent performance trend
        performance_history = agent_state.get("performance_history", [])
        if len(performance_history) >= 3:
            recent_successes = sum(1 for p in performance_history[-3:] if p["success"])
            success_rate = recent_successes / 3.0
            
            # Momentum bonus/penalty
            if success and success_rate > 0.66:
                base_adjustment *= 1.2  # Positive momentum
            elif not success and success_rate < 0.33:
                base_adjustment *= 1.3  # Negative momentum
        
        return base_adjustment if success else -base_adjustment

    def get_best_agent_for_persona(self, persona: str, emotional_context: dict[str, Any] | None = None) -> str | None:
        """Select the best agent for a persona considering trust, momentum, and emotional context."""
        candidates = [
            agent for agent in self.subagents.values()
            if agent.get("persona") == persona.lower()
        ]
        
        if not candidates:
            return None
        
        # Score agents based on multiple factors
        scored_agents = []
        
        for agent in candidates:
            agent_state = agent["state"]
            trust_score = agent_state.get("trust_score", 0.0)
            trust_momentum = agent_state.get("trust_momentum", 0.0)
            consecutive_failures = agent_state.get("consecutive_failures", 0)
            
            # Base score is trust
            score = trust_score
            
            # Momentum bonus (positive momentum is good)
            score += trust_momentum * 0.1
            
            # Penalty for consecutive failures
            score -= consecutive_failures * 0.1
            
            # Emotional context adjustments
            if emotional_context:
                frustration = emotional_context.get("frustration", 0.0)
                confidence = emotional_context.get("confidence", 0.5)
                
                # When frustrated, prefer more reliable agents
                if frustration > 0.7:
                    reliability_bonus = min(0.2, trust_score * 0.2)
                    score += reliability_bonus
                
                # When low confidence, avoid risky agents
                if confidence < 0.4:
                    if consecutive_failures > 1:
                        score -= 0.15
            
            scored_agents.append((score, agent["name"]))
        
        # Sort by score (highest first) and return best agent
        scored_agents.sort(key=lambda x: x[0], reverse=True)
        best_agent_name = scored_agents[0][1]
        
        logging.debug(f"Selected agent {best_agent_name} for persona {persona} with score {scored_agents[0][0]:.2f}")
        return best_agent_name

    def get_all(self: "DynamicAgentPool") -> list[dict[str, Any]]:
        """Returns all agents in the pool."""
        return list(self.subagents.values())

    def get_agents_by_persona(self: "DynamicAgentPool", persona: str) -> list[str]:
        """Gets a list of agent names matching a specific persona."""
        return [
            agent["name"]
            for agent in self.subagents.values()
            if agent.get("persona") == persona
        ]

    def get_all_personas(self) -> list[str]:
        """Returns a list of all unique, currently available persona names."""
        personas: set[str] = {
            agent.get("persona", "unknown") for agent in self.subagents.values()
        }
        return sorted(list(personas))

    def get_all_action_definitions(self) -> list[dict[str, Any]]:
        """Gets a list of all available actions (innate and learned)."""
        all_actions = [
            action.model_dump() for action in self.skill_manager.innate_actions
        ]

        # Add learned skills as orchestrator-level actions
        latest_skills: dict[str, Any] = {}
        for skill in self.skill_manager.skills.values():
            # Only include the latest version of each skill
            if (
                skill.name not in latest_skills
                or skill.version > latest_skills[skill.name].get("version", 0)
            ):
                latest_skills[skill.name] = {
                    "name": skill.name,
                    "description": skill.description,
                    "version": skill.version,
                    "parameters": [
                        {
                            "name": "input",
                            "type": "str", 
                            "description": "The primary input for the skill.",
                            "required": False,
                        }
                    ],
                    "assigned_persona": "orchestrator",
                    "type": "learned",
                }
        
        all_actions.extend(latest_skills.values())
        return all_actions

    async def delegate_task(
        self, task_name: str, agent_name: str, **kwargs: Any
    ) -> Optional[dict[str, Any]]:
        """
        Delegate a task to a specific agent with increased timeout.
        """
        if agent_name not in self.subagents:
            logging.error("Agent '%s' not found for delegation", agent_name)
            return None
        
        logging.info(
            "[Delegate] Delegated task '%s' to '%s'. Waiting for reply...",
            task_name,
            agent_name,
        )
        
        # Send task request
        request_id = f"task_{int(time.time() * 1000)}"
        task_request = {
            "type": "task_request",
            "request_id": request_id,
            "task_name": task_name,
            "kwargs": kwargs,
        }
        
        await self.bus.publish(f"agent:{agent_name}", task_request)
        
        # Wait for response with increased timeout for QA tasks
        timeout = 60.0 if task_name == "review_plan" else 30.0  # Longer timeout for QA reviews
        
        try:
            response = await asyncio.wait_for(
                self.bus.receive_one(f"orchestrator:{request_id}"),
                timeout=timeout,
            )
            
            # Update agent metrics
            agent = self.subagents[agent_name]
            agent["last_active"] = time.time()
            agent["tasks_completed"] += 1
            agent["success_rate"] = (
                agent["success_rate"] * (agent["tasks_completed"] - 1) + 1.0
            ) / agent["tasks_completed"]
            
            return response
            
        except asyncio.TimeoutError:
            logging.error(
                "Timeout: No reply received from '%s' for task '%s'.",
                agent_name,
                task_name,
            )
            
            # Update agent metrics for timeout
            agent = self.subagents[agent_name]
            agent["last_active"] = time.time()
            agent["tasks_completed"] += 1
            agent["success_rate"] = (
                agent["success_rate"] * (agent["tasks_completed"] - 1) + 0.0
            ) / agent["tasks_completed"]
            
            return None

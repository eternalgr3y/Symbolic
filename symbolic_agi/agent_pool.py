# symbolic_agi/agent_pool.py

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast

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
            clamped_score = max(0.0, min(config.MAX_TRUST_SCORE, new_score))
            self.subagents[agent_name]["state"]["trust_score"] = clamped_score
            if last_used:
                self.subagents[agent_name]["state"]["last_used_timestamp"] = (
                    datetime.now(timezone.utc).isoformat()
                )
            metrics.AGENT_TRUST.labels(
                agent_name=agent_name,
                persona=self.subagents[agent_name]["persona"],
            ).set(clamped_score)
        else:
            logging.warning(
                "Attempted to update trust for non-existent agent: %s", agent_name
            )

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

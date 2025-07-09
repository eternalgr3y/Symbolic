# symbolic_agi/agent_pool.py

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Set, cast

from . import config, metrics
from .message_bus import MessageBus
from .schemas import ActionDefinition
from .symbolic_identity import SymbolicIdentity
from .symbolic_memory import SymbolicMemory

if TYPE_CHECKING:
    from .skill_manager import SkillManager


class DynamicAgentPool:
    """Manages a collection of sub-agents with different personas and persistent state."""

    skill_manager: "SkillManager"

    def __init__(
        self: "DynamicAgentPool", bus: MessageBus, skill_manager: "SkillManager"
    ):
        self.subagents: Dict[str, Dict[str, Any]] = {}
        self.bus: MessageBus = bus
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
            "state": {"trust_score": config.INITIAL_TRUST_SCORE},
        }
        self.bus.subscribe(name)
        metrics.AGENT_TRUST.labels(agent_name=name, persona=persona.lower()).set(
            config.INITIAL_TRUST_SCORE
        )
        logging.info(
            " [AgentPool] Added agent: %s with persona: %s and trust: %s",
            name,
            persona.lower(),
            config.INITIAL_TRUST_SCORE,
        )

    def get_agent_state(self: "DynamicAgentPool", agent_name: str) -> Dict[str, Any]:
        """Retrieves the state dictionary for a specific agent."""
        agent = self.subagents.get(agent_name)
        if agent:
            return cast(Dict[str, Any], agent.get("state", {}))
        return {}

    def update_agent_state(
        self: "DynamicAgentPool", agent_name: str, updates: Dict[str, Any]
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

    def get_all(self: "DynamicAgentPool") -> List[Dict[str, Any]]:
        """Returns all agents in the pool."""
        return list(self.subagents.values())

    def get_agents_by_persona(self: "DynamicAgentPool", persona: str) -> List[str]:
        """Gets a list of agent names matching a specific persona."""
        return [
            agent["name"]
            for agent in self.subagents.values()
            if agent.get("persona") == persona
        ]

    def get_all_personas(self) -> List[str]:
        """Returns a list of all unique, currently available persona names."""
        personas: Set[str] = {
            agent.get("persona", "unknown") for agent in self.subagents.values()
        }
        return sorted(personas)

    def get_all_action_definitions(self) -> List[ActionDefinition]:
        """
        Gathers all innate and learned skills into a single list of structured definitions.
        """
        all_actions = self.skill_manager.innate_actions[:]

        latest_skills: Dict[str, Any] = {}
        for skill in self.skill_manager.skills.values():
            if (
                skill.name not in latest_skills
                or skill.version > latest_skills[skill.name].version
            ):
                latest_skills[skill.name] = skill

        for skill in latest_skills.values():
            all_actions.append(
                ActionDefinition(
                    name=skill.name,
                    description=skill.description,
                    parameters=[],
                    assigned_persona="orchestrator",
                )
            )
        return all_actions

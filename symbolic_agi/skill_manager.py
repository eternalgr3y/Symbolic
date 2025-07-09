# symbolic_agi/skill_manager.py

import json
import logging
import os
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from . import config
from .schemas import ActionDefinition, ActionParameter, ActionStep, SkillModel

if TYPE_CHECKING:
    from .message_bus import MessageBus


_innate_action_registry: List[ActionDefinition] = []


def register_innate_action(persona: str, description: str):
    """A decorator to register a tool or skill as an innate action."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        import inspect

        params = []
        sig = inspect.signature(func)
        for param in sig.parameters.values():
            if param.name not in ("self", "kwargs"):
                params.append(
                    ActionParameter(
                        name=param.name,
                        type=str(param.annotation),
                        description="",  # Could be enhanced to parse from docstring
                        required=param.default is inspect.Parameter.empty,
                    )
                )

        action_def = ActionDefinition(
            name=func.__name__,
            description=description,
            parameters=params,
            assigned_persona=persona,
        )
        _innate_action_registry.append(action_def)
        return func

    return decorator


class SkillManager:
    """Manages loading, saving, and using learned skills."""

    def __init__(
        self,
        file_path: str = config.SKILLS_PATH,
        message_bus: Optional["MessageBus"] = None,
    ):
        self.file_path = file_path
        self.skills: Dict[str, SkillModel] = self._load_skills()
        self.innate_actions: List[ActionDefinition] = _innate_action_registry
        self.message_bus = message_bus
        logging.info("[SkillManager] Initialized with %d skills", len(self.skills))

    def _load_skills(self) -> Dict[str, SkillModel]:
        if not os.path.exists(self.file_path):
            return {}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                loaded_skills = {
                    skill_id: SkillModel.model_validate(props)
                    for skill_id, props in data.items()
                }
                logging.info("[SkillManager] Loading skills from %s", self.file_path)
                for skill_id in loaded_skills:
                    logging.info(
                        "[SkillManager] Loaded skill '%s'",
                        loaded_skills[skill_id].name,
                    )
                return loaded_skills
        except (json.JSONDecodeError, TypeError) as e:
            logging.error("Could not load skills from %s: %s", self.file_path, e)
            return {}

    def _save_skills(self) -> None:
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    skill_id: skill.model_dump(mode="json")
                    for skill_id, skill in self.skills.items()
                },
                f,
                indent=4,
            )

    async def add_new_skill(
        self, name: str, description: str, plan: List[ActionStep]
    ) -> None:
        """
        Creates a new, versioned skill from a successful plan and saves it.
        """
        highest_version = 0
        for skill in self.skills.values():
            if skill.name == name:
                highest_version = max(highest_version, skill.version)

        new_version = highest_version + 1
        logging.info("Creating new skill '%s' version %d.", name, new_version)

        new_skill = SkillModel(
            name=name,
            description=description,
            action_sequence=plan,
            version=new_version,
        )
        self.skills[new_skill.id] = new_skill
        self._prune_old_skill_versions(name)
        self._save_skills()

        if self.message_bus:
            from .schemas import MessageModel

            await self.message_bus.broadcast(
                MessageModel(
                    sender_id="SymbolicAGI_Orchestrator",
                    receiver_id="ALL",
                    message_type="new_skill_broadcast",
                    payload={
                        "skill_name": name,
                        "skill_description": description,
                        "skill_id": new_skill.id,
                        "version": new_version,
                    },
                )
            )

    def _prune_old_skill_versions(self, skill_name: str, keep: int = 3) -> None:
        """Keeps only the N most recent versions of a skill."""
        versions_of_skill = [s for s in self.skills.values() if s.name == skill_name]
        if len(versions_of_skill) <= keep:
            return

        versions_of_skill.sort(key=lambda s: s.version, reverse=True)

        skills_to_prune = versions_of_skill[keep:]
        for skill in skills_to_prune:
            logging.warning(
                "Pruning old skill version: %s v%d (ID: %s)",
                skill.name,
                skill.version,
                skill.id,
            )
            del self.skills[skill.id]

    def get_skill_by_name(self, name: str) -> Optional[SkillModel]:
        """Finds the highest version of a skill by its unique name."""
        versions_of_skill = [s for s in self.skills.values() if s.name == name]
        if not versions_of_skill:
            return None

        skill = max(versions_of_skill, key=lambda s: s.version)
        action_names = [step.action for step in skill.action_sequence]
        logging.info(
            "[SkillManager] Retrieved skill '%s' with actions: %s",
            name,
            action_names,
        )
        return skill

    def is_skill(self, action_name: str) -> bool:
        """Checks if a given action name corresponds to a learned skill."""
        is_skill_result = any(
            skill.name == action_name for skill in self.skills.values()
        )
        logging.debug(
            "[SkillManager] Checking if '%s' is a skill: %s",
            action_name,
            is_skill_result,
        )
        return is_skill_result

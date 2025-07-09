# symbolic_agi/skill_manager.py

import json
import logging
import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from . import config
from .schemas import ActionDefinition, ActionParameter, ActionStep, SkillModel

if TYPE_CHECKING:
    from .message_bus import MessageBus


class SkillManager:
    """Manages loading, saving, and using learned skills."""

    def __init__(
        self,
        file_path: str = config.SKILLS_PATH,
        message_bus: Optional["MessageBus"] = None,
    ):
        self.file_path = file_path
        self.skills: Dict[str, SkillModel] = self._load_skills()
        self.innate_actions: List[ActionDefinition] = self._get_innate_actions()
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

    def _get_innate_actions(self) -> List[ActionDefinition]:
        """
        Returns a structured list of the AGI's hardcoded abilities.
        This is the single source of truth for innate actions.
        """
        return [
            # Agent-specific skills
            ActionDefinition(
                name="research_topic",
                description="Researches a topic online and provides a concise summary.",
                parameters=[
                    ActionParameter(
                        name="topic",
                        type="str",
                        description="The subject to research.",
                        required=True,
                    )
                ],
                assigned_persona="research",
            ),
            ActionDefinition(
                name="write_code",
                description="Generates Python code based on a prompt, context, and previous work.",
                parameters=[
                    ActionParameter(
                        name="prompt",
                        type="str",
                        description="The request for the code to be written.",
                        required=True,
                    ),
                    ActionParameter(
                        name="context",
                        type="str",
                        description="Overall context for the task.",
                        required=False,
                    ),
                ],
                assigned_persona="coder",
            ),
            ActionDefinition(
                name="review_code",
                description="Reviews a block of code for bugs, style, and improvements.",
                parameters=[
                    ActionParameter(
                        name="code",
                        type="str",
                        description="The code to be reviewed.",
                        required=True,
                    )
                ],
                assigned_persona="qa",
            ),
            ActionDefinition(
                name="review_plan",
                description="Reviews a plan for logical flaws and inefficiencies.",
                parameters=[
                    ActionParameter(
                        name="original_goal",
                        type="str",
                        description="The original goal.",
                        required=True,
                    ),
                    ActionParameter(
                        name="plan_to_review",
                        type="list",
                        description="The plan to be reviewed.",
                        required=True,
                    ),
                ],
                assigned_persona="qa",
            ),
            ActionDefinition(
                name="review_skill_efficiency",
                description="Reviews a learned skill for potential improvements.",
                parameters=[
                    ActionParameter(
                        name="skill_to_review",
                        type="dict",
                        description="The skill object to review.",
                        required=True,
                    )
                ],
                assigned_persona="qa",
            ),
            ActionDefinition(
                name="interact_with_page",
                description="Analyzes web page content and decides the next action (click, fill, done).",
                parameters=[
                    ActionParameter(
                        name="objective",
                        type="str",
                        description="The high-level goal for the interaction.",
                        required=True,
                    ),
                    ActionParameter(
                        name="page_content",
                        type="str",
                        description="Simplified content of the current web page.",
                        required=True,
                    ),
                ],
                assigned_persona="browser",
            ),
            # Orchestrator-specific tools
            ActionDefinition(
                name="respond_to_user",
                description="Sends a final text response to the user.",
                parameters=[
                    ActionParameter(
                        name="text",
                        type="str",
                        description="The response to send to the user.",
                        required=True,
                    )
                ],
                assigned_persona="orchestrator",
            ),
            ActionDefinition(
                name="provision_agent",
                description="Creates a new specialist agent.",
                parameters=[
                    ActionParameter(
                        name="persona",
                        type="str",
                        description="The persona of the new agent.",
                        required=True,
                    ),
                    ActionParameter(
                        name="name",
                        type="str",
                        description="The unique name for the new agent.",
                        required=True,
                    ),
                ],
                assigned_persona="orchestrator",
            ),
            ActionDefinition(
                name="propose_code_modification",
                description="Safely proposes a change to one of the AGI's source code files.",
                parameters=[
                    ActionParameter(
                        name="file_path",
                        type="str",
                        description="The relative path to the file to modify.",
                        required=True,
                    ),
                    ActionParameter(
                        name="change_description",
                        type="str",
                        description="A detailed description of the change to make.",
                        required=True,
                    ),
                ],
                assigned_persona="orchestrator",
            ),
            ActionDefinition(
                name="apply_code_modification",
                description="HIGH-RISK: Applies a proposed code change after safety evaluation.",
                parameters=[
                    ActionParameter(
                        name="file_path",
                        type="str",
                        description="The relative path to the file to modify.",
                        required=True,
                    ),
                    ActionParameter(
                        name="proposed_code_key",
                        type="str",
                        description="The workspace key holding the proposed code.",
                        required=True,
                    ),
                ],
                assigned_persona="orchestrator",
            ),
            ActionDefinition(
                name="get_skill_details",
                description="Retrieves the full definition of a learned skill.",
                parameters=[
                    ActionParameter(
                        name="skill_name",
                        type="str",
                        description="The name of the skill to retrieve.",
                        required=True,
                    )
                ],
                assigned_persona="orchestrator",
            ),
            ActionDefinition(
                name="update_skill",
                description="Updates a learned skill with a new, improved plan.",
                parameters=[
                    ActionParameter(
                        name="skill_id",
                        type="str",
                        description="The ID of the skill to update.",
                        required=True,
                    ),
                    ActionParameter(
                        name="new_action_sequence",
                        type="list",
                        description="The new list of action steps for the skill.",
                        required=True,
                    ),
                ],
                assigned_persona="orchestrator",
            ),
            ActionDefinition(
                name="explain_skill",
                description="Generates a human-readable explanation of a learned skill.",
                parameters=[
                    ActionParameter(
                        name="skill_name",
                        type="str",
                        description="The name of the skill to explain.",
                        required=True,
                    )
                ],
                assigned_persona="orchestrator",
            ),
            # Browser Tools
            ActionDefinition(
                name="browser_new_page",
                description="Opens a new browser page and navigates to the URL.",
                parameters=[
                    ActionParameter(
                        name="url",
                        type="str",
                        description="The URL to navigate to.",
                        required=True,
                    )
                ],
                assigned_persona="orchestrator",
            ),
            ActionDefinition(
                name="browser_click",
                description="Clicks an element on the current page.",
                parameters=[
                    ActionParameter(
                        name="selector",
                        type="str",
                        description="The CSS selector of the element to click.",
                        required=True,
                    ),
                    ActionParameter(
                        name="description",
                        type="str",
                        description="Reason for clicking the element.",
                        required=True,
                    ),
                ],
                assigned_persona="orchestrator",
            ),
            ActionDefinition(
                name="browser_fill",
                description="Fills an input field on the current page.",
                parameters=[
                    ActionParameter(
                        name="selector",
                        type="str",
                        description="The CSS selector of the input field.",
                        required=True,
                    ),
                    ActionParameter(
                        name="text",
                        type="str",
                        description="The text to fill into the field.",
                        required=True,
                    ),
                ],
                assigned_persona="orchestrator",
            ),
            ActionDefinition(
                name="browser_get_content",
                description="Gets a simplified representation of the current page content.",
                parameters=[],
                assigned_persona="orchestrator",
            ),
            # General tools
            ActionDefinition(
                name="execute_python_code",
                description="Executes a sandboxed block of Python code.",
                parameters=[
                    ActionParameter(
                        name="code",
                        type="str",
                        description="The Python code to execute.",
                        required=True,
                    ),
                    ActionParameter(
                        name="timeout_seconds",
                        type="int",
                        description="Maximum execution time.",
                        required=False,
                    ),
                ],
                assigned_persona="orchestrator",
            ),
            ActionDefinition(
                name="read_file",
                description="Reads the content of a file from the workspace.",
                parameters=[
                    ActionParameter(
                        name="file_path",
                        type="str",
                        description="The relative path to the file in the workspace.",
                        required=True,
                    )
                ],
                assigned_persona="orchestrator",
            ),
            ActionDefinition(
                name="write_file",
                description="Writes content to a file in the workspace.",
                parameters=[
                    ActionParameter(
                        name="file_path",
                        type="str",
                        description="The relative path for the new file in the workspace.",
                        required=True,
                    ),
                    ActionParameter(
                        name="content",
                        type="str",
                        description="The content to write to the file.",
                        required=True,
                    ),
                ],
                assigned_persona="orchestrator",
            ),
            ActionDefinition(
                name="list_files",
                description="Lists files in a directory within the workspace.",
                parameters=[
                    ActionParameter(
                        name="directory",
                        type="str",
                        description="The directory to list, relative to the workspace root.",
                        required=False,
                    )
                ],
                assigned_persona="orchestrator",
            ),
            ActionDefinition(
                name="web_search",
                description="Performs a web search and returns the results.",
                parameters=[
                    ActionParameter(
                        name="query", type="str", description="The search query.", required=True
                    ),
                    ActionParameter(
                        name="num_results",
                        type="int",
                        description="The number of results to return.",
                        required=False,
                    ),
                ],
                assigned_persona="orchestrator",
            ),
        ]

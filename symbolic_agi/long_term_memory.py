# symbolic_agi/long_term_memory.py

import json
import logging
import os
from typing import Any, Dict, List, Optional

from . import config
from .schemas import ActionStep, GoalModel


class LongTermMemory:
    """
    Manages the AGI's long-term goals, persisting them across sessions.
    This acts as the main "todo" list for the AGI.
    """

    def __init__(self, file_path: str = config.LONG_TERM_GOAL_PATH):
        self.file_path = file_path
        self.goals: Dict[str, GoalModel] = self._load_goals()
        logging.info("[LTM] Initialized with %d goals.", len(self.goals))

    def _load_goals(self) -> Dict[str, GoalModel]:
        """Loads active goals from a JSON file, validating them with Pydantic."""
        if not os.path.exists(
            config.LONG_TERM_GOAL_PATH
        ) or os.path.getsize(config.LONG_TERM_GOAL_PATH) < 2:
            return {}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    goal_id: GoalModel.model_validate(props)
                    for goal_id, props in data.items()
                }
        except (json.JSONDecodeError, TypeError) as e:
            logging.error("Could not load long-term goals: %s", e)
            return {}

    def save(self) -> None:
        """Saves all current goals to a JSON file."""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    goal_id: goal.model_dump(mode="json")
                    for goal_id, goal in self.goals.items()
                },
                f,
                indent=4,
            )

    def add_goal(self, goal: GoalModel) -> None:
        """Adds a new goal to the long-term memory."""
        self.goals[goal.id] = goal
        self.save()

    def get_goal_by_id(self, goal_id: str) -> Optional[GoalModel]:
        """Retrieves a goal by its unique ID."""
        return self.goals.get(goal_id)

    def update_goal_status(self, goal_id: str, status: str) -> None:
        """Updates the status of a goal."""
        if goal := self.goals.get(goal_id):
            goal.status = status  # type: ignore[assignment]
            self.save()

    def get_active_goal(self) -> Optional[GoalModel]:
        """Retrieves the first active goal from the list."""
        for goal in self.goals.values():
            if goal.status == "active":
                return goal
        return None

    def complete_sub_task(self, goal_id: str) -> None:
        """Removes the first sub-task from a goal's plan."""
        if goal := self.goals.get(goal_id):
            if goal.sub_tasks:
                goal.sub_tasks.pop(0)
                self.save()

    def update_plan(self, goal_id: str, plan: List[ActionStep]) -> None:
        """Updates the entire plan for a goal and sets the original plan if not set."""
        if goal := self.goals.get(goal_id):
            goal.sub_tasks = plan
            if goal.original_plan is None:
                goal.original_plan = plan
            self.save()

    def invalidate_plan(self, goal_id: str, reason: str) -> None:
        """Marks a plan as invalid by clearing it and recording the failure reason."""
        if goal := self.goals.get(goal_id):
            goal.sub_tasks = []
            goal.last_failure = reason
            self.save()

    def increment_failure_count(self, goal_id: str) -> int:
        """Increments the failure count for a goal and returns the new count."""
        if goal := self.goals.get(goal_id):
            goal.failure_count += 1
            self.save()
            return goal.failure_count
        return 0

    def increment_refinement_count(self, goal_id: str) -> int:
        """Increments the refinement count for a goal and returns the new count."""
        if goal := self.goals.get(goal_id):
            goal.refinement_count += 1
            self.save()
            return goal.refinement_count
        return 0

    def archive_goal(self, goal_id: str) -> None:
        """Moves a goal from active memory to an archive file."""
        if goal := self.goals.pop(goal_id, None):
            try:
                archive_data: Dict[str, Any] = {}
                if (
                    os.path.exists(config.GOAL_ARCHIVE_PATH)
                    and os.path.getsize(config.GOAL_ARCHIVE_PATH) > 2
                ):
                    with open(
                        config.GOAL_ARCHIVE_PATH, "r", encoding="utf-8"
                    ) as f:
                        archive_data = json.load(f)

                archive_data[goal.id] = goal.model_dump(mode="json")

                with open(config.GOAL_ARCHIVE_PATH, "w", encoding="utf-8") as f:
                    json.dump(archive_data, f, indent=4)
                self.save()  # Save the main goals file after removal
            except Exception as e:
                logging.error(
                    "Failed to archive goal %s: %s", goal.id, e, exc_info=True
                )
                self.goals[goal.id] = goal  # Restore if archiving fails

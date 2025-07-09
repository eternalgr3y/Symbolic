# symbolic_agi/symbolic_identity.py

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, cast

from . import config
from .schemas import MemoryEntryModel
from .symbolic_memory import SymbolicMemory


class SymbolicIdentity:
    """
    Represents the AGI's self-model, its core values, and its cognitive resources.
    """

    def __init__(
        self: "SymbolicIdentity",
        memory: SymbolicMemory,
        file_path: str = config.IDENTITY_PROFILE_PATH,
    ):
        self.memory = memory
        self.file_path = file_path

        profile = self._load_profile()
        self.name: str = profile.get("name", "SymbolicAGI")
        self.value_system: Dict[str, float] = profile.get(
            "value_system",
            {
                "truthfulness": 1.0,
                "harm_avoidance": 1.0,
                "user_collaboration": 0.9,
                "self_preservation": 0.8,
            },
        )

        self.cognitive_energy: int = 100
        self.max_energy: int = 100
        self.current_state: str = "idle"
        self.perceived_location: str = "hallway"
        self.emotional_state: str = "curious"
        self.last_interaction_timestamp: datetime = datetime.now(timezone.utc)

        self._is_dirty = False

    def _load_profile(self: "SymbolicIdentity") -> Dict[str, Any]:
        """Loads the persistent identity profile from a JSON file."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r") as f:
                    return cast(Dict[str, Any], json.load(f))
            except (json.JSONDecodeError, TypeError):
                logging.error("Could not load identity profile, creating a new one.")
        return {}

    def save_profile(self: "SymbolicIdentity") -> None:
        """Saves the persistent parts of the identity profile to a JSON file if changed."""
        if not self._is_dirty:
            return

        logging.info("Saving updated identity profile to disk...")
        try:
            profile_data: Dict[str, Any] = {
                "name": self.name,
                "value_system": self.value_system,
            }
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, "w") as f:
                json.dump(profile_data, f, indent=4, default=str)
            self._is_dirty = False
        except Exception as e:
            logging.error(
                "Failed to save identity profile to %s: %s", self.file_path, e, exc_info=True
            )

    async def record_interaction(
        self: "SymbolicIdentity", user_input: str, agi_response: str
    ) -> None:
        """Records a conversation turn and updates the interaction timestamp."""
        self.last_interaction_timestamp = datetime.now(timezone.utc)
        self._is_dirty = True
        await self.memory.add_memory(
            MemoryEntryModel(
                type="user_input",
                content={"user": user_input, "agi": agi_response},
                importance=0.7,
            )
        )

    def update_self_model_state(self: "SymbolicIdentity", updates: Dict[str, Any]) -> None:
        """Updates the AGI's dynamic state attributes."""
        for key, value in updates.items():
            if hasattr(self, key):
                setattr(self, key, value)
        logging.info("Self-model state updated with: %s", updates)

    def get_self_model(self: "SymbolicIdentity") -> Dict[str, Any]:
        """
        Dynamically constructs and returns the complete self-model.
        This is the single source of truth, preventing data duplication.
        """
        return {
            "name": self.name,
            "perceived_location_in_world": self.perceived_location,
            "current_state": self.current_state,
            "emotional_state": self.emotional_state,
            "cognitive_energy": self.cognitive_energy,
            "value_system": self.value_system,
        }

    def consume_energy(self: "SymbolicIdentity", amount: int = 1) -> None:
        """Reduces cognitive energy. Does NOT write to disk."""
        self.cognitive_energy = max(0, self.cognitive_energy - amount)

    def recover_energy(self: "SymbolicIdentity", amount: int = 5) -> None:
        """Regenerates cognitive energy, capping at max_energy. Does NOT write to disk."""
        if self.cognitive_energy < self.max_energy:
            self.cognitive_energy = min(self.max_energy, self.cognitive_energy + amount)

    async def record_tool_usage(
        self: "SymbolicIdentity", tool_name: str, params: Dict[str, Any]
    ) -> None:
        """Logs the usage of a tool."""
        await self.memory.add_memory(
            MemoryEntryModel(
                type="tool_usage",
                content={"tool": tool_name, "params": params},
                importance=0.6,
            )
        )

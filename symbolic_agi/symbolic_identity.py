# symbolic_agi/symbolic_identity.py

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from . import config
from .schemas import MemoryEntryModel
from .symbolic_memory import SymbolicMemory


class SymbolicIdentity:
    """
    Represents the AGI's self-model, its core values, and its cognitive resources.
    """

    def __init__(
        self,
        memory: SymbolicMemory,
        db_path: str = config.DB_PATH,
    ):
        self.memory = memory
        self._db_path = db_path
        self._save_lock = asyncio.Lock()

        self.name: str = "SymbolicAGI"
        self.value_system: dict[str, float] = {
            "truthfulness": 1.0,
            "harm_avoidance": 1.0,
            "user_collaboration": 0.9,
            "self_preservation": 0.8,
        }

        self.cognitive_energy: int = 100
        self.max_energy: int = 100
        self.current_state: str = "idle"
        self.perceived_location: str = "hallway"
        self.emotional_state: str = "curious"
        self.last_interaction_timestamp: datetime = datetime.now(timezone.utc)

    @classmethod
    async def create(
        cls, memory: SymbolicMemory, db_path: str = config.DB_PATH
    ) -> "SymbolicIdentity":
        """Asynchronous factory for creating a SymbolicIdentity instance."""
        instance = cls(memory, db_path)
        await instance._init_db()
        await instance._load_profile()
        return instance

    async def _init_db(self) -> None:
        """Initializes the database and tables if they don't exist."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS identity_profile (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            await db.commit()

    async def _load_profile(self) -> None:
        """Loads the persistent identity profile from the database."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute("SELECT key, value FROM identity_profile") as cursor:
                rows = await cursor.fetchall()
                profile_data = {row[0]: json.loads(row[1]) for row in rows}
                self.name = profile_data.get("name", "SymbolicAGI")
                self.value_system = profile_data.get("value_system", self.value_system)

    async def save_profile(self) -> None:
        """Saves the persistent parts of the identity profile to the database."""
        async with self._save_lock:
            logging.info("Saving updated identity profile to database.")
            profile_data = {
                "name": self.name,
                "value_system": self.value_system,
            }
            async with aiosqlite.connect(self._db_path) as db:
                await db.executemany(
                    "INSERT OR REPLACE INTO identity_profile VALUES (?, ?)",
                    [(k, json.dumps(v)) for k, v in profile_data.items()],
                )
                await db.commit()

    async def record_interaction(
        self: "SymbolicIdentity", user_input: str, agi_response: str
    ) -> None:
        """Records a conversation turn and updates the interaction timestamp."""
        self.last_interaction_timestamp = datetime.now(timezone.utc)
        await self.memory.add_memory(
            MemoryEntryModel(
                type="user_input",
                content={"user": user_input, "agi": agi_response},
                importance=0.7,
            )
        )
        await self.save_profile()

    def update_self_model_state(
        self: "SymbolicIdentity", updates: dict[str, Any]
    ) -> None:
        """Updates the AGI's dynamic state attributes."""
        for key, value in updates.items():
            if hasattr(self, key):
                setattr(self, key, value)
        logging.info("Self-model state updated with: %s", updates)

    def get_self_model(self: "SymbolicIdentity") -> dict[str, Any]:
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
        self: "SymbolicIdentity", tool_name: str, params: dict[str, Any]
    ) -> None:
        """Logs the usage of a tool."""
        await self.memory.add_memory(
            MemoryEntryModel(
                type="tool_usage",
                content={"tool": tool_name, "params": params},
                importance=0.6,
            )
        )

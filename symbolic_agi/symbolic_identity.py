# symbolic_agi/symbolic_identity.py
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

import aiosqlite

from . import config
from .schemas import MemoryEntryModel
from .symbolic_memory import SymbolicMemory

class SymbolicIdentity:
    """Manages the AGI's identity, self-model, and value system."""
    
    def __init__(self, memory: SymbolicMemory, db_path: str = config.DB_PATH):
        self.memory = memory
        self._db_path = db_path
        self._save_lock = asyncio.Lock()
        
        # Core identity attributes
        self.name: str = "SymbolicAGI"
        self.value_system: Dict[str, float] = {
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
    async def create(cls, memory: SymbolicMemory, db_path: str = config.DB_PATH) -> "SymbolicIdentity":
        """Create and initialize a SymbolicIdentity instance."""
        instance = cls(memory, db_path)
        await instance._load_identity()
        return instance

    async def _load_identity(self) -> None:
        """Load identity from database."""
        async with aiosqlite.connect(self._db_path) as db:
            # Create table if needed
            await db.execute("""
                CREATE TABLE IF NOT EXISTS identity (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            await db.commit()
            
            # Load identity data
            cursor = await db.execute("SELECT key, value FROM identity")
            rows = await cursor.fetchall()
            
            for key, value in rows:
                if key == "cognitive_energy":
                    self.cognitive_energy = int(value)
                elif key == "current_state":
                    self.current_state = value
                elif key == "emotional_state":
                    self.emotional_state = value
                elif key == "value_system":
                    self.value_system = json.loads(value)

    async def save_identity(self) -> None:
        """Save identity to database."""
        async with self._save_lock:
            async with aiosqlite.connect(self._db_path) as db:
                # Define SQL constant to avoid duplication
                INSERT_SQL = "INSERT OR REPLACE INTO identity (key, value) VALUES (?, ?)"
                
                # Save key attributes
                await db.execute(INSERT_SQL, ("cognitive_energy", str(self.cognitive_energy)))
                await db.execute(INSERT_SQL, ("current_state", str(self.current_state) if self.current_state else "idle"))
                await db.execute(INSERT_SQL, ("emotional_state", str(self.emotional_state) if self.emotional_state else "curious"))
                await db.execute(INSERT_SQL, ("value_system", json.dumps(self.value_system) if self.value_system else "{}"))
                await db.commit()

    def update_state(self, new_state: str) -> None:
        """Update the AGI's current state."""
        self.current_state = new_state
        logging.info(f"State updated to: {new_state}")

    def consume_energy(self, amount: int) -> bool:
        """Consume cognitive energy. Returns False if insufficient energy."""
        if self.cognitive_energy >= amount:
            self.cognitive_energy -= amount
            return True
        return False

    def recover_energy(self, amount: int) -> None:
        """Recover cognitive energy."""
        self.cognitive_energy = min(self.cognitive_energy + amount, self.max_energy)

    def get_self_model(self) -> Dict[str, Any]:
        """Get the current self-model."""
        return {
            "name": self.name,
            "state": self.current_state,
            "energy": f"{self.cognitive_energy}/{self.max_energy}",
            "emotional_state": self.emotional_state,
            "location": self.perceived_location,
            "values": self.value_system,
            "last_interaction": self.last_interaction_timestamp.isoformat()
        }
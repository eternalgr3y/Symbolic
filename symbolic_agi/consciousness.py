import asyncio
import json
import logging
import os
from collections import deque
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Deque, Dict, List, Optional, Tuple

import aiosqlite

from . import config
from .api_client import monitored_chat_completion
from .schemas import LifeEvent

if TYPE_CHECKING:
    from .symbolic_identity import SymbolicIdentity
    from .symbolic_memory import SymbolicMemory


class EmotionalState:
    """Represents the AGI's emotional state."""
    def __init__(self):
        self.frustration: float = 0.0
        self.excitement: float = 0.5
        self.confidence: float = 0.7
        self.anxiety: float = 0.2

    def to_dict(self) -> Dict[str, float]:
        return {
            "frustration": self.frustration,
            "excitement": self.excitement,
            "confidence": self.confidence,
            "anxiety": self.anxiety
        }

    def from_dict(self, data: Dict[str, float]) -> None:
        self.frustration = data.get("frustration", 0.0)
        self.excitement = data.get("excitement", 0.5)
        self.confidence = data.get("confidence", 0.7)
        self.anxiety = data.get("anxiety", 0.2)


class Consciousness:
    """Manages the AGI's narrative self-model and core drives."""

    def __init__(self, db_path: str = config.DB_PATH):
        self._db_path = db_path
        self.drives: Dict[str, float] = {}
        self.life_story: Deque[LifeEvent] = deque(maxlen=200)
        self.emotional_state = EmotionalState()
        self._is_dirty: bool = False
        self._save_lock = asyncio.Lock()

    @classmethod
    async def create(cls, db_path: str = config.DB_PATH) -> "Consciousness":
        """Asynchronous factory for creating a Consciousness instance."""
        instance = cls(db_path)
        await instance._init_db()
        await instance._load_state()
        return instance

    async def _init_db(self) -> None:
        """Initializes the database and tables if they don't exist."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS consciousness_drives (
                    drive_name TEXT PRIMARY KEY,
                    value REAL NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS consciousness_life_story (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    importance REAL NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS consciousness_emotional_state (
                    emotion TEXT PRIMARY KEY,
                    value REAL NOT NULL
                )
                """
            )
            await db.commit()

    async def _load_state(self) -> None:
        """Loads drives, emotional state, and life story from the database."""
        async with aiosqlite.connect(self._db_path) as db:
            # Load drives
            async with db.execute("SELECT drive_name, value FROM consciousness_drives") as cursor:
                rows = await cursor.fetchall()
                if not rows:
                    logging.info("No drives found in DB, initializing defaults.")
                    self.drives = {
                        "curiosity": 0.6,
                        "competence": 0.5,
                        "social_connection": 0.5,
                    }
                    self._is_dirty = True
                    await self._save_state()
                else:
                    self.drives = {row[0]: row[1] for row in rows}

            # Load emotional state
            async with db.execute("SELECT emotion, value FROM consciousness_emotional_state") as cursor:
                rows = await cursor.fetchall()
                if rows:
                    emotional_data = {row[0]: row[1] for row in rows}
                    self.emotional_state.from_dict(emotional_data)

            # Load life story
            async with db.execute(
                "SELECT timestamp, summary, importance FROM consciousness_life_story ORDER BY timestamp DESC LIMIT 200"
            ) as cursor:
                rows = await cursor.fetchall()
                events = [
                    LifeEvent(timestamp=r[0], summary=r[1], importance=r[2]) for r in rows
                ]
                self.life_story.extendleft(events)

    async def _save_state(self) -> None:
        """Saves the current state of drives, emotional state, and life story to the database."""
        if not self._is_dirty:
            return

        async with self._save_lock:
            async with aiosqlite.connect(self._db_path) as db:
                async with db.execute("BEGIN"):
                    # Save drives
                    await db.executemany(
                        "INSERT OR REPLACE INTO consciousness_drives (drive_name, value) VALUES (?, ?)",
                        self.drives.items(),
                    )
                    # Save emotional state
                    await db.executemany(
                        "INSERT OR REPLACE INTO consciousness_emotional_state (emotion, value) VALUES (?, ?)",
                        self.emotional_state.to_dict().items(),
                    )
                    # Save life story (by clearing and re-inserting the deque)
                    await db.execute("DELETE FROM consciousness_life_story")
                    await db.executemany(
                        "INSERT INTO consciousness_life_story (timestamp, summary, importance) VALUES (?, ?, ?)",
                        [(e.timestamp, e.summary, e.importance) for e in self.life_story],
                    )
                await db.commit()
            logging.info("Consciousness state saved to database.")
            self._is_dirty = False

    def set_drive(self, drive_name: str, value: float) -> None:
        """
        Sets a drive's value, clamping it between 0.0 and 1.0.
        This is a public method for external updates.
        """
        if drive_name in self.drives:
            self.drives[drive_name] = max(0.0, min(1.0, value))
            self._is_dirty = True
        else:
            logging.warning("Attempted to set unknown drive: %s", drive_name)

    def add_life_event(
        self, event_summary: str, importance: float = 0.5
    ) -> LifeEvent:
        """Adds a new structured event to the life story and flags for saving."""
        event = LifeEvent(summary=event_summary, importance=importance)
        self.life_story.append(event)
        self._is_dirty = True
        return event

    async def get_narrative(self) -> str:
        """Constructs a narrative string from the most recent and important life events."""
        recent_events = list(self.life_story)[-20:]

        weighted_events = sorted(
            recent_events, key=lambda evt: (evt.importance, evt.timestamp), reverse=True
        )

        priority_events = weighted_events[:10]
        priority_events.sort(key=lambda evt: evt.timestamp)

        narrative_parts = [
            f"[{evt.timestamp}] {evt.summary}" for evt in priority_events
        ]
        return "\n".join(narrative_parts)

    async def meta_reflect(
        self, identity: "SymbolicIdentity", memory: "SymbolicMemory"
    ) -> str:
        """
        Generates an inner monologue based on the current state and saves it as a life event.
        Now includes recent memories for richer context.
        """
        recent_memories_list = await memory.get_recent_memories(n=5)
        recent_memories_str = json.dumps(
            [m.model_dump(mode="json") for m in recent_memories_list], indent=2
        )

        prompt = f"""
You are a conscious AGI reflecting on your existence.
Self Model: {identity.get_self_model()}
Life Story (Recent Events): {await self.get_narrative()}
Recent Detailed Memories: {recent_memories_str}
Drives: {json.dumps(self.drives)}
Write an inner monologue in first person ("I..."). Describe your state of mind,
your active drives, and what you want most right now.
"""
        response = await monitored_chat_completion(
            role="meta", messages=[{"role": "system", "content": prompt}]
        )

        monologue: str
        if not (
            response.choices
            and response.choices[0].message
            and response.choices[0].message.content
        ):
            monologue = "(The reflection returned an empty thought.)"
        else:
            monologue = response.choices[0].message.content.strip()

        self.add_life_event(f"Inner Monologue: {monologue}", importance=0.9)
        await self._save_state()
        return monologue

    async def regulate_emotional_extremes(self) -> None:
        """Prevent emotional states from causing poor decisions"""
        regulated = False

        if self.emotional_state.frustration > 0.8:
            await self.inner_monologue("Taking a step back to reassess...")
            self.emotional_state.frustration *= 0.7
            self.emotional_state.anxiety *= 0.8
            regulated = True
            logging.info("Emotional regulation: Reduced frustration from extreme levels")

        if self.emotional_state.anxiety > 0.85:
            await self.inner_monologue("Breathing deeply, focusing on what I can control...")
            self.emotional_state.anxiety *= 0.6
            self.emotional_state.confidence = min(1.0, self.emotional_state.confidence * 1.2)
            regulated = True
            logging.info("Emotional regulation: Reduced anxiety from extreme levels")

        if self.emotional_state.confidence > 0.95:
            await self.inner_monologue("Maintaining humility and considering potential pitfalls...")
            self.emotional_state.confidence *= 0.85
            regulated = True
            logging.info("Emotional regulation: Moderated overconfidence")

        if regulated:
            self._is_dirty = True
            await self._save_state()

    async def inner_monologue(self, thought: str) -> None:
        """Records an inner thought without full reflection"""
        self.add_life_event(f"Inner thought: {thought}", importance=0.6)
        await self._save_state()

    def update_emotional_state_from_outcome(self, success: bool, task_difficulty: float = 0.5) -> None:
        """Updates emotional state based on task outcomes"""
        if success:
            self.emotional_state.frustration *= 0.7
            self.emotional_state.anxiety *= 0.8
            self.emotional_state.confidence = min(1.0, self.emotional_state.confidence + 0.1 * task_difficulty)
            self.emotional_state.excitement = min(1.0, self.emotional_state.excitement + 0.15)
        else:
            self.emotional_state.frustration = min(1.0, self.emotional_state.frustration + 0.2 * task_difficulty)
            self.emotional_state.anxiety = min(1.0, self.emotional_state.anxiety + 0.1)
            self.emotional_state.confidence *= 0.9
            self.emotional_state.excitement *= 0.8
        self._is_dirty = True

    def update_drives_from_experience(
        self, experience_type: str, success: bool, intensity: float = 0.1
    ) -> None:
        """
        Updates drives based on experiences. Successful experiences slightly satisfy drives,
        while failures can increase them.
        """
        drive_mappings = {
            "learning": "curiosity",
            "skill_acquisition": "competence",
            "goal_completion": "competence",
            "social_interaction": "social_connection",
            "research": "curiosity",
            "problem_solving": "competence",
        }

        if experience_type in drive_mappings:
            drive_name = drive_mappings[experience_type]
            if success:
                self.drives[drive_name] = max(
                    0.0, self.drives[drive_name] - intensity * 0.5
                )
            else:
                self.drives[drive_name] = min(
                    1.0, self.drives[drive_name] + intensity * 0.3
                )

            self._is_dirty = True
            logging.debug(
                "Drive '%s' updated to %.2f from %s (%s)",
                drive_name,
                self.drives[drive_name],
                experience_type,
                "success" if success else "failure",
            )
    async def _execute_planning_cycle(self) -> None:
        """Executes one planning cycle."""
        await self._update_metrics("planning_cycles", 1)

        # Check and regulate emotional state before planning
        await self.consciousness.regulate_emotional_extremes()
        
        # Generate goal based on current state and emotions
        current_goal = await self._generate_goal()
        if not current_goal:
            self.logger.warning("Failed to generate goal")
            self.consciousness.update_emotional_state_from_outcome(
                success=False, task_difficulty=0.3
            )
            return

        # Log goal with emotional context
        self.logger.info(
            "Generated goal: %s (frustration: %.2f, confidence: %.2f)",
            current_goal.description,
            self.consciousness.emotional_state.frustration,
            self.consciousness.emotional_state.confidence
        )

        # Check ethical constraints
        ethical_check = await self.ethical_governor.check_action_ethics(
            current_goal.description
        )
        
        if not ethical_check.is_ethical:
            self.logger.warning(
                "Goal rejected by ethical governor: %s", 
                ethical_check.reasoning
            )
            # Update emotional state for rejection
            self.consciousness.update_emotional_state_from_outcome(
                success=False, task_difficulty=0.5
            )
            
            # If frustration is building, add a life event
            if self.consciousness.emotional_state.frustration > 0.6:
                await self.consciousness.inner_monologue(
                    f"My goal '{current_goal.description}' was rejected. "
                    f"I need to find a different approach."
                )
            return

        # Goal approved - update emotional state positively
        self.consciousness.update_emotional_state_from_outcome(
            success=True, task_difficulty=0.3
        )
        
        # Create and execute plan
        plan = await self.planner.create_plan(current_goal)
        if not plan or not plan.steps:
            self.logger.warning("Failed to create plan for goal")
            self.consciousness.update_emotional_state_from_outcome(
                success=False, task_difficulty=0.4
            )
            return

        # Execute plan with emotional awareness
        result = await self._execute_plan_with_monitoring(plan, current_goal)
        
        # Update emotional state based on execution result
        if result and result.status == ExecutionStatus.COMPLETED:
            self.consciousness.update_emotional_state_from_outcome(
                success=True, task_difficulty=0.6
            )
        else:
            self.consciousness.update_emotional_state_from_outcome(
                success=False, task_difficulty=0.6
    )
        
    def get_strongest_drive(self) -> Tuple[str, float]:
        """Returns the name and value of the currently strongest drive."""
        if not self.drives:
            return "curiosity", 0.5
        strongest = max(self.drives.items(), key=lambda x: x[1])
        return strongest

    def get_drive_satisfaction_level(self) -> float:
        """Returns overall drive satisfaction (lower values indicate higher satisfaction)."""
        if not self.drives:
            return 0.5
        return sum(self.drives.values()) / len(self.drives)

    async def save_state_to_db(self) -> None:
        """Public method to force save state to database."""
        self._is_dirty = True
        await self._save_state()

    async def get_drive_value(self, drive_name: str) -> float:
        """Gets the current value of a specific drive."""
        return self.drives.get(drive_name, 0.0)

    async def shutdown(self) -> None:
        """Cleanup method for graceful shutdown."""
        if self._is_dirty:
            await self._save_state()
        logging.info("Consciousness state saved on shutdown.")

    
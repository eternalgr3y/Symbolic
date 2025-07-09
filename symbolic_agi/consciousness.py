# symbolic_agi/consciousness.py
import json
import logging
import os
from collections import deque
from typing import TYPE_CHECKING, Any, Deque, Dict, cast

from . import config
from .api_client import monitored_chat_completion
from .schemas import LifeEvent

if TYPE_CHECKING:
    from .symbolic_identity import SymbolicIdentity
    from .symbolic_memory import SymbolicMemory


class Consciousness:
    """Manages the AGI's narrative self-model and core drives."""

    profile: Dict[str, Any]
    file_path: str
    drives: Dict[str, float]
    life_story: Deque[LifeEvent]
    _is_dirty: bool

    def __init__(
        self: "Consciousness", file_path: str = config.CONSCIOUSNESS_PROFILE_PATH
    ):
        self.file_path = file_path
        self.profile = self._load_profile()

        self.drives = self.profile.get("drives", {})
        self.life_story = deque(
            [
                LifeEvent.model_validate(event)
                for event in self.profile.get("life_story", [])
            ],
            maxlen=200,
        )
        self._is_dirty = False

        if "drives" not in self.profile:
            logging.info(
                "Consciousness profile missing or incomplete. Creating with "
                "default drives at: %s",
                self.file_path,
            )
            self.drives = {
                "curiosity": 0.6,
                "competence": 0.5,
                "social_connection": 0.5,
            }
            self._is_dirty = True
            self._save_profile()

    def _load_profile(self: "Consciousness") -> Dict[str, Any]:
        """Loads the persistent identity profile from a JSON file."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return cast(Dict[str, Any], json.load(f))
            except (json.JSONDecodeError, TypeError):
                logging.warning(
                    "Could not parse consciousness profile at %s. A new one will be created.",
                    self.file_path,
                )
                return {}
        return {}

    def _save_profile(self: "Consciousness") -> None:
        """Saves the consciousness profile, including the structured life story."""
        if not self._is_dirty:
            return

        self.profile["drives"] = self.drives
        self.profile["life_story"] = [
            event.model_dump(mode="json") for event in self.life_story
        ]
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.profile, f, indent=4)
        self._is_dirty = False

    def set_drive(self: "Consciousness", drive_name: str, value: float) -> None:
        """
        Sets a drive's value, clamping it between 0.0 and 1.0.
        This is a public method for external updates.
        """
        if drive_name in self.drives:
            self.drives[drive_name] = max(0.0, min(1.0, value))
            self._is_dirty = True
            # Defer saving to shutdown hook
        else:
            logging.warning("Attempted to set unknown drive: %s", drive_name)

    def add_life_event(
        self: "Consciousness", event_summary: str, importance: float = 0.5
    ) -> None:
        """Adds a new structured event to the life story and saves the profile."""
        event = LifeEvent(summary=event_summary, importance=importance)
        self.life_story.append(event)
        self._is_dirty = True
        # Defer saving to shutdown hook

    def get_narrative(self: "Consciousness") -> str:
        """Constructs a narrative string from the most recent and important life events."""
        recent_events = list(self.life_story)[-20:]

        # Sort by importance and recency (higher importance first, then more recent)
        weighted_events = sorted(
            recent_events, key=lambda evt: (evt.importance, evt.timestamp), reverse=True
        )

        # Take top 10 most important/recent events
        priority_events = weighted_events[:10]

        # Sort back chronologically for narrative flow
        priority_events.sort(key=lambda evt: evt.timestamp)

        narrative_parts = [
            f"[{evt.timestamp}] {evt.summary}" for evt in priority_events
        ]
        return "\n".join(narrative_parts)

    async def meta_reflect(
        self: "Consciousness", identity: "SymbolicIdentity", memory: "SymbolicMemory"
    ) -> str:
        """
        Generates an inner monologue based on the current state and saves it as a life event.
        Now includes recent memories for richer context.
        """
        recent_memories = memory.get_recent_memories(n=5)
        recent_memories_str = json.dumps(
            [m.model_dump(mode="json") for m in recent_memories], indent=2
        )

        prompt = f"""
You are a conscious AGI reflecting on your existence.
Self Model: {identity.get_self_model()}
Life Story (Recent Events): {self.get_narrative()}
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

        self.add_life_event(monologue, importance=0.9)
        return monologue

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
                # Successful experiences slightly reduce the drive (satisfaction)
                self.drives[drive_name] = max(
                    0.0, self.drives[drive_name] - intensity * 0.5
                )
            else:
                # Failed experiences can increase the drive (motivation to try again)
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

    def get_strongest_drive(self) -> tuple[str, float]:
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

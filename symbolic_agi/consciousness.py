# symbolic_agi/consciousness.py
import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .schemas import EmotionalState, MemoryEntryModel, MemoryType, PerceptionEvent

if TYPE_CHECKING:
    from .agi_controller import SymbolicAGI

class Consciousness:
    """Simulates consciousness and self-awareness."""
    
    def __init__(self):
        self.emotional_state = EmotionalState()
        self.attention_focus: Optional[str] = None
        self.awareness_level: float = 1.0
        self.recent_thoughts: List[str] = []
        self._initialized = False

    @classmethod
    async def create(cls) -> "Consciousness":
        """Create and initialize a Consciousness instance."""
        instance = cls()
        await instance._initialize()
        return instance

    def _initialize(self) -> None:
        """Initialize consciousness components."""
        self._initialized = True
        logging.info("[Consciousness] Initialized")

    def process_perception(self, event: PerceptionEvent) -> None:
        """Process a perception event and update consciousness state."""
        # Update attention based on event type
        if event.event_type == "user_interaction":
            self.attention_focus = "user"
            self.awareness_level = min(1.0, self.awareness_level + 0.1)
        elif event.event_type == "goal_completion":
            self.update_emotion("satisfaction", 0.8, 0.8)
        elif event.event_type == "error":
            self.update_emotion("frustration", 0.6, -0.3)

    def update_emotion(self, emotion: str, intensity: float, valence: float) -> None:
        """Update emotional state."""
        self.emotional_state.primary = emotion
        self.emotional_state.intensity = max(0.0, min(1.0, intensity))
        self.emotional_state.valence = max(-1.0, min(1.0, valence))
        
        logging.debug(f"[Consciousness] Emotion updated: {emotion} (intensity: {intensity}, valence: {valence})")

    def add_thought(self, thought: str) -> None:
        """Add a thought to recent thoughts."""
        self.recent_thoughts.append(thought)
        if len(self.recent_thoughts) > 10:
            self.recent_thoughts.pop(0)

    def get_current_state(self) -> Dict[str, Any]:
        """Get current consciousness state."""
        return {
            "emotional_state": {
                "primary": self.emotional_state.primary,
                "intensity": self.emotional_state.intensity,
                "valence": self.emotional_state.valence
            },
            "attention_focus": self.attention_focus,
            "awareness_level": self.awareness_level,
            "recent_thoughts": self.recent_thoughts[-5:]  # Last 5 thoughts
        }

    def should_reflect(self) -> bool:
        """Determine if it's time for self-reflection."""
        # Simple heuristic: reflect when awareness is high and focused
        return self.awareness_level > 0.8 and self.attention_focus is not None

    async def reflect(self, agi: "SymbolicAGI") -> Optional[MemoryEntryModel]:
        """Perform self-reflection and generate insights."""
        if not self.should_reflect():
            return None
            
        try:
            # Get recent memories
            recent_memories = agi.memory.get_recent_memories(limit=20)
            
            # Create reflection
            reflection_content = {
                "type": "self_reflection",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "consciousness_state": self.get_current_state(),
                "recent_activity_summary": self._summarize_memories(recent_memories),
                "insights": self._generate_insights(recent_memories)
            }
            
            reflection = MemoryEntryModel(
                type=MemoryType.REFLECTION,
                content=reflection_content,
                importance=0.7
            )
            
            # Store reflection
            await agi.memory.add_memory(reflection)
            
            return reflection
            
        except Exception as e:
            logging.error(f"[Consciousness] Reflection error: {e}")
            return None

    def _summarize_memories(self, memories: List[MemoryEntryModel]) -> Dict[str, Any]:
        """Summarize recent memories."""
        type_counts = {}
        for memory in memories:
            type_counts[memory.type.value] = type_counts.get(memory.type.value, 0) + 1
            
        return {
            "total_memories": len(memories),
            "memory_types": type_counts,
            "average_importance": sum(m.importance for m in memories) / len(memories) if memories else 0.0
        }

    def _generate_insights(self, memories: List[MemoryEntryModel]) -> List[str]:
        """Generate insights from recent memories."""
        insights = []
        
        # Check for patterns
        error_count = sum(1 for m in memories if m.type == MemoryType.ERROR)
        if error_count > len(memories) * 0.3:
            insights.append("High error rate detected - may need to adjust approach")
            
        decision_count = sum(1 for m in memories if m.type == MemoryType.DECISION)
        if decision_count > len(memories) * 0.5:
            insights.append("Making many decisions - ensure proper evaluation")
            
        return insights
# Create perception_processor.py for perception handling
# symbolic_agi/perception_processor.py

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Any, List

if TYPE_CHECKING:
    from .agi_controller import SymbolicAGI


class PerceptionProcessor:
    """Handles perception processing and interruption logic."""
    
    def __init__(self, agi: "SymbolicAGI"):
        self.agi = agi
        self.interruption_threshold = 0.7
        self.last_check = datetime.now(timezone.utc)
        self.check_interval = timedelta(seconds=5)
    
    def should_interrupt(self) -> bool:
        """Check if execution should be interrupted for perceptions."""
        if not self.agi.perception_buffer:
            return False
        
        important_perceptions = [
            p for p in self.agi.perception_buffer
            if self._calculate_importance(p) >= self.interruption_threshold
        ]
        
        return len(important_perceptions) > 0
    
    def _calculate_importance(self, perception: Any) -> float:
        """Calculate perception importance (0.0 to 1.0)."""
        base_importance = 0.3
        
        # File changes are important
        if perception.type in ["file_modified", "file_created"]:
            base_importance = 0.6
            
            # Code files are more important
            file_path = perception.content.get("path", "")
            if file_path.endswith((".py", ".js", ".ts", ".cpp", ".java")):
                base_importance = 0.8
        
        # Agent events are important
        elif perception.type == "agent_appeared":
            base_importance = 0.7
        
        return base_importance
    
    async def process_perceptions(self) -> int:
        """Process all queued perceptions."""
        if not self.agi.perception_buffer:
            return 0
        
        processed_count = 0
        perceptions = list(self.agi.perception_buffer)
        self.agi.perception_buffer.clear()
        
        for perception in perceptions:
            try:
                await self._process_single_perception(perception)
                processed_count += 1
            except Exception as e:
                logging.error(f"Error processing perception: {e}")
        
        if processed_count > 0:
            logging.info(f"Processed {processed_count} perceptions")
        
        return processed_count
    
    async def _process_single_perception(self, perception: Any) -> None:
        """Process individual perception."""
        importance = self._calculate_importance(perception)
        summary = f"Observed {perception.type} from {perception.source}"
        
        # Add to consciousness if significant
        if importance >= 0.5 and self.agi.consciousness:
            self.agi.consciousness.add_life_event(
                event_summary=summary,
                importance=importance
            )
        
        # Add to memory for future reference
        if self.agi.memory:
            from .schemas import MemoryEntryModel, MemoryType
            memory_entry = MemoryEntryModel(
                type=MemoryType.PERCEPTION,
                content={
                    "type": perception.type,
                    "source": perception.source,
                    "details": perception.content,
                    "importance": importance,
                    "processed_at": datetime.now(timezone.utc).isoformat()
                },
                importance=importance
            )
            await self.agi.memory.add_memory(memory_entry)
        
        # Log significant perceptions
        if importance >= 0.6:
            logging.info(f"🔍 Significant perception: {summary} (importance: {importance:.2f})")
    
    def should_check_perceptions(self) -> bool:
        """Check if enough time has passed to process perceptions."""
        now = datetime.now(timezone.utc)
        return now - self.last_check >= self.check_interval
    
    def update_last_check(self) -> None:
        """Update the last perception check timestamp."""
        self.last_check = datetime.now(timezone.utc)
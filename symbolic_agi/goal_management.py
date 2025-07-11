# symbolic_agi/goal_management.py
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from .schemas import GoalModel, GoalStatus, MemoryEntryModel, MemoryType

if TYPE_CHECKING:
    from .long_term_memory import LongTermMemory

class GoalManager:
    """Manages the AGI's goals and objectives."""
    
    def __init__(self, ltm: "LongTermMemory"):
        self.ltm = ltm
        self.goals: List[GoalModel] = []
        self._load_active_goals()

    def _load_active_goals(self) -> None:
        """Load active goals from memory."""
        # In a real implementation, this would load from persistent storage
        pass

    def add_goal(self, goal: GoalModel) -> None:
        """Add a new goal."""
        self.goals.append(goal)
        
        # Can't use async here, would need to refactor
        # For now, just log
        logging.info(f"[GoalManager] Added goal: {goal.description}")

    def get_active_goals(self) -> List[GoalModel]:
        """Get all active goals sorted by priority."""
        active = [g for g in self.goals if g.status in [GoalStatus.PENDING, GoalStatus.ACTIVE]]
        return sorted(active, key=lambda g: g.priority.value, reverse=True)

    def update_goal_status(self, goal_id: str, status: GoalStatus) -> bool:
        """Update the status of a goal."""
        for goal in self.goals:
            if goal.id == goal_id:
                goal.status = status
                goal.updated_at = datetime.now(timezone.utc)
                
                if status == GoalStatus.COMPLETED:
                    goal.completed_at = datetime.now(timezone.utc)
                    
                logging.info(f"[GoalManager] Goal {goal_id} status updated to {status.value}")
                return True
                
        return False

    def complete_goal(self, goal_id: str) -> bool:
        """Mark a goal as completed."""
        return self.update_goal_status(goal_id, GoalStatus.COMPLETED)

    def fail_goal(self, goal_id: str, reason: str) -> bool:
        """Mark a goal as failed."""
        for goal in self.goals:
            if goal.id == goal_id:
                goal.status = GoalStatus.FAILED
                goal.updated_at = datetime.now(timezone.utc)
                goal.metadata["failure_reason"] = reason
                
                logging.info(f"[GoalManager] Goal {goal_id} failed: {reason}")
                return True
                
        return False

    def get_goal_by_id(self, goal_id: str) -> Optional[GoalModel]:
        """Get a goal by its ID."""
        for goal in self.goals:
            if goal.id == goal_id:
                return goal
        return None

    def cancel_goal(self, goal_id: str) -> bool:
        """Cancel a goal."""
        return self.update_goal_status(goal_id, GoalStatus.CANCELLED)

    def get_completed_goals(self) -> List[GoalModel]:
        """Get all completed goals."""
        return [g for g in self.goals if g.status == GoalStatus.COMPLETED]

    def get_failed_goals(self) -> List[GoalModel]:
        """Get all failed goals."""
        return [g for g in self.goals if g.status == GoalStatus.FAILED]

    def cleanup_old_goals(self, days: int = 30) -> int:
        """Remove completed/failed goals older than specified days."""
        from datetime import timedelta
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        old_goals = []
        
        for goal in self.goals:
            if goal.status in [GoalStatus.COMPLETED, GoalStatus.FAILED, GoalStatus.CANCELLED]:
                if goal.updated_at and goal.updated_at < cutoff:
                    old_goals.append(goal)
                    
        for goal in old_goals:
            self.goals.remove(goal)
            
        logging.info(f"[GoalManager] Cleaned up {len(old_goals)} old goals")
        return len(old_goals)
# symbolic_agi/goal_management.py

import asyncio
import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from queue import PriorityQueue
from typing import Dict, List, Optional, Any, Callable

class GoalPriority(Enum):
    LOW = 3
    MEDIUM = 2
    HIGH = 1
    CRITICAL = 0

class GoalStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"

@dataclass(order=False)
class EnhancedGoal:
    """Represents a sophisticated, stateful goal for the AGI."""
    priority: GoalPriority = GoalPriority.MEDIUM
    id: str = field(default_factory=lambda: str(uuid.uuid4().hex[:8]))
    description: str = ""
    status: GoalStatus = GoalStatus.QUEUED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300  # 5 minutes default
    context: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)

    def __lt__(self, other: "EnhancedGoal") -> bool:
        """For priority queue ordering. Lower number = higher priority."""
        return self.priority.value < other.priority.value

class GoalManager:
    """
    Advanced goal management with queuing, prioritization, and lifecycle management.
    This is the single source of truth for goal state.
    """

    def __init__(self, max_concurrent_goals: int = 3):
        self.goal_queue: "PriorityQueue[EnhancedGoal]" = PriorityQueue()
        self.active_goals: Dict[str, EnhancedGoal] = {}
        self.completed_goals: Dict[str, EnhancedGoal] = {}
        self.goal_history: deque[EnhancedGoal] = deque(maxlen=100)
        self.max_concurrent = max_concurrent_goals
        self.shutdown_event = asyncio.Event()
        self.goal_completion_callbacks: List[Callable[[EnhancedGoal], Any]] = []
        logging.info("GoalManager initialized with max concurrency of %d.", max_concurrent_goals)

    def add_goal(self, description: str, priority: GoalPriority = GoalPriority.MEDIUM, 
                 context: Optional[Dict] = None, dependencies: Optional[List[str]] = None) -> str:
        """Adds a new goal to the queue."""
        goal = EnhancedGoal(
            description=description,
            priority=priority,
            context=context or {},
            dependencies=dependencies or []
        )
        self.goal_queue.put(goal)
        logging.info(f"📝 Added goal [{goal.id}]: '{description}' (Priority: {priority.name})")
        return goal.id

    def get_next_goal(self) -> Optional[EnhancedGoal]:
        """Gets the next available goal to process, respecting dependencies and concurrency."""
        if self.goal_queue.empty() or len(self.active_goals) >= self.max_concurrent:
            return None

        temp_goals = []
        next_goal = None

        while not self.goal_queue.empty():
            candidate = self.goal_queue.get()

            if self._dependencies_satisfied(candidate):
                next_goal = candidate
                break
            else:
                temp_goals.append(candidate)

        for temp_goal in temp_goals:
            self.goal_queue.put(temp_goal)

        return next_goal

    def _dependencies_satisfied(self, goal: EnhancedGoal) -> bool:
        """Checks if all dependencies for a goal are completed successfully."""
        for dep_id in goal.dependencies:
            completed_goal = self.completed_goals.get(dep_id)
            if not completed_goal or completed_goal.status != GoalStatus.COMPLETED:
                return False
        return True

    def start_goal(self, goal: EnhancedGoal):
        """Marks a goal as started and moves it to the active dictionary."""
        goal.status = GoalStatus.PROCESSING
        goal.started_at = datetime.now(timezone.utc)
        self.active_goals[goal.id] = goal
        logging.info(f"🚀 Starting goal [{goal.id}]")

    async def complete_goal(self, goal_id: str, result: Dict[str, Any]):
        """Marks a goal as completed and moves it to history."""
        if goal_id in self.active_goals:
            goal = self.active_goals.pop(goal_id)
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = datetime.now(timezone.utc)
            goal.result = result
            self.completed_goals[goal.id] = goal
            self.goal_history.append(goal)
            logging.info(f"✅ Completed goal [{goal.id}]")

            for callback in self.goal_completion_callbacks:
                await asyncio.to_thread(callback, goal)

    def fail_goal(self, goal_id: str, error: str):
        """Marks a goal as failed and moves it to history."""
        if goal_id in self.active_goals:
            goal = self.active_goals.pop(goal_id)
            goal.status = GoalStatus.FAILED
            goal.error = error
            goal.completed_at = datetime.now(timezone.utc)
            self.completed_goals[goal.id] = goal
            self.goal_history.append(goal)
            logging.error(f"❌ Failed goal [{goal.id}]: {error}")

    def get_status_summary(self) -> Dict[str, Any]:
        """Gets a comprehensive status summary of the goal management system."""
        return {
            "queued_goals": self.goal_queue.qsize(),
            "active_goals_count": len(self.active_goals),
            "active_goals": [g.description for g in self.active_goals.values()],
            "completed_count": len([g for g in self.completed_goals.values() if g.status == GoalStatus.COMPLETED]),
            "failed_count": len([g for g in self.completed_goals.values() if g.status == GoalStatus.FAILED]),
            "total_processed_in_history": len(self.goal_history),
            "max_concurrency": self.max_concurrent
        }
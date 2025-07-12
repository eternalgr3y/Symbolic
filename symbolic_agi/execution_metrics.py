# Create execution_metrics.py for performance tracking
# symbolic_agi/execution_metrics.py

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Set


@dataclass
class ExecutionMetrics:
    """Lightweight metrics for execution monitoring."""
    total_goals: int = 0
    successful_goals: int = 0
    failed_goals: int = 0
    total_delegations: int = 0
    successful_delegations: int = 0
    avg_completion_time: float = 0.0

    def get_success_rate(self) -> float:
        if self.total_goals == 0:
            return 0.0
        return self.successful_goals / self.total_goals

    def get_delegation_success_rate(self) -> float:
        if self.total_delegations == 0:
            return 0.0
        return self.successful_delegations / self.total_delegations

    def record_goal_completion(self, execution_time: float) -> None:
        """Record successful goal completion."""
        self.total_goals += 1
        self.successful_goals += 1
        
        # Update average with exponential moving average
        alpha = 0.2
        self.avg_completion_time = (
            alpha * execution_time + (1 - alpha) * self.avg_completion_time
        )

    def record_goal_failure(self) -> None:
        """Record goal failure."""
        self.total_goals += 1
        self.failed_goals += 1

    def record_delegation(self, success: bool) -> None:
        """Record delegation attempt."""
        self.total_delegations += 1
        if success:
            self.successful_delegations += 1


@dataclass
class AgentPerformanceTracker:
    """Simplified agent performance tracking."""
    agent_id: str
    total_tasks: int = 0
    successful_tasks: int = 0
    avg_response_time: float = 0.0
    last_interaction: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update_performance(self, success: bool, response_time: float) -> None:
        """Update agent performance metrics."""
        self.total_tasks += 1
        self.last_interaction = datetime.now(timezone.utc)
        
        if success:
            self.successful_tasks += 1
        
        # Update average response time
        alpha = 0.3
        self.avg_response_time = (
            alpha * response_time + (1 - alpha) * self.avg_response_time
        )

    def get_success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.5  # Neutral starting point
        return self.successful_tasks / self.total_tasks

    def get_reliability_score(self) -> float:
        """Get composite reliability score."""
        success_rate = self.get_success_rate()
        
        # Boost for good performers, penalty for poor performers
        if success_rate > 0.8:
            return min(1.0, success_rate * 1.2)
        elif success_rate < 0.3:
            return max(0.1, success_rate * 0.8)
        else:
            return success_rate


class PerformanceMonitor:
    """Centralized performance monitoring."""
    
    def __init__(self):
        self.metrics = ExecutionMetrics()
        self.agent_performance: Dict[str, AgentPerformanceTracker] = {}
        self.start_time = time.time()
    
    def get_agent_tracker(self, agent_id: str) -> AgentPerformanceTracker:
        """Get or create agent performance tracker."""
        if agent_id not in self.agent_performance:
            self.agent_performance[agent_id] = AgentPerformanceTracker(agent_id=agent_id)
        return self.agent_performance[agent_id]
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get comprehensive status summary."""
        uptime = time.time() - self.start_time
        
        return {
            "uptime_seconds": uptime,
            "goal_success_rate": self.metrics.get_success_rate(),
            "delegation_success_rate": self.metrics.get_delegation_success_rate(),
            "avg_goal_completion_time": self.metrics.avg_completion_time,
            "total_goals_processed": self.metrics.total_goals,
            "active_agents": len(self.agent_performance),
            "top_performing_agents": self._get_top_agents()
        }
    
    def _get_top_agents(self, limit: int = 3) -> list[Dict[str, Any]]:
        """Get top performing agents."""
        agents = [
            {
                "agent_id": tracker.agent_id,
                "success_rate": tracker.get_success_rate(),
                "total_tasks": tracker.total_tasks,
                "avg_response_time": tracker.avg_response_time
            }
            for tracker in self.agent_performance.values()
            if tracker.total_tasks > 0
        ]
        
        # Sort by success rate, then by total tasks
        agents.sort(key=lambda x: (x["success_rate"], x["total_tasks"]), reverse=True)
        return agents[:limit]
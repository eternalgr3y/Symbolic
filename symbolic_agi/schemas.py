# symbolic_agi/schemas.py

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from secrets import token_hex
from typing import Annotated, Any, Literal, List, Dict, Optional

from pydantic import BaseModel, Field

# --- CORE CONFIGURATION ---


class AGIConfig(BaseModel):
    name: str = "SymbolicAGI"
    scalable_agent_pool_size: int = 3
    meta_task_sleep_seconds: int = 10
    meta_task_timeout: int = 60
    motivational_drift_rate: float = 0.05
    memory_compression_window: timedelta = timedelta(days=1)
    social_interaction_threshold: timedelta = timedelta(hours=6)
    memory_forgetting_threshold: float = 0.2
    debate_timeout_seconds: int = 90
    energy_regen_amount: int = 5
    initial_trust_score: float = 0.5
    max_trust_score: float = 1.0
    trust_decay_rate: float = 0.1
    trust_reward_rate: float = 0.05


# --- INTER-AGENT COMMUNICATION ---


class MessageModel(BaseModel):
    """Base model for inter-agent messages"""

    message_id: str = Field(
        default_factory=lambda: token_hex(8), description="Unique message ID"
    )
    sender_id: str = Field(description="ID of the sending agent")
    recipient_id: str = Field(description="ID of the receiving agent")
    message_type: str = Field(description="Type of message")
    content: Dict[str, Any] = Field(default_factory=dict, description="Message content")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    priority: int = Field(
        default=0, description="Message priority (higher = more urgent)"
    )


class TaskRequestMessage(MessageModel):
    """Message for requesting task execution from an agent"""

    message_type: Literal["task_request"] = "task_request"
    task_name: str = Field(description="Name of the task to execute")
    task_parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the task"
    )
    timeout_seconds: float = Field(
        default=30.0, description="Timeout for task completion"
    )


class TaskResponseMessage(MessageModel):
    """Message for responding to a task request"""

    message_type: Literal["task_response"] = "task_response"
    request_id: str = Field(description="ID of the original request")
    success: bool = Field(description="Whether the task completed successfully")
    result: Dict[str, Any] = Field(default_factory=dict, description="Task result data")
    error_message: Optional[str] = Field(
        default=None, description="Error message if task failed"
    )


class AgentStatusMessage(MessageModel):
    """Message for reporting agent status"""

    message_type: Literal["status_update"] = "status_update"
    status: str = Field(description="Current agent status")
    workload: float = Field(default=0.0, description="Current workload (0.0 to 1.0)")
    capabilities: List[str] = Field(default_factory=list, description="Available capabilities")


class NotificationMessage(MessageModel):
    """General notification message between agents"""

    message_type: Literal["notification"] = "notification"
    notification_type: str = Field(description="Type of notification")
    data: Dict[str, Any] = Field(default_factory=dict, description="Notification data")


# --- AGI DATA MODELS ---


class EmotionalState(BaseModel):
    joy: float = 0.5
    sadness: float = 0.1
    anger: float = 0.1
    fear: float = 0.1
    surprise: float = 0.2
    disgust: float = 0.1
    trust: float = 0.5
    frustration: float = 0.2

    def clamp(self) -> None:
        for field in self.__class__.model_fields:
            value = getattr(self, field)
            setattr(self, field, max(0.0, min(1.0, value)))


class ActionStep(BaseModel):
    """Defines a single step in a plan, designed for delegation."""

    action: str
    parameters: dict[str, Any]
    assigned_persona: str
    risk: Literal["low", "medium", "high"] | None = "low"


# --- NEW: Structured Action Definitions ---
class ActionParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool


class ActionDefinition(BaseModel):
    name: str
    description: str
    parameters: list[ActionParameter]
    assigned_persona: str


GoalStatus = Literal["active", "paused", "completed", "failed"]
GoalMode = Literal["code", "docs"]


class GoalModel(BaseModel):
    id: str = Field(default_factory=lambda: f"goal_{token_hex(8)}")
    description: str
    sub_tasks: list[ActionStep]
    status: GoalStatus = "active"
    mode: GoalMode = "code"
    last_failure: str | None = None
    original_plan: list[ActionStep] | None = None
    failure_count: int = 0
    max_failures: int = 3
    refinement_count: int = 0
    max_refinements: int = 3


class PlannerOutput(BaseModel):
    """Output from the planning process"""

    plan: List[ActionStep] = Field(
        default_factory=list, description="List of action steps in the plan"
    )
    thought: str = Field(default="", description="Reasoning behind the plan")
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence score for the plan"
    )


class ExecutionStepRecord(BaseModel):
    """Record of an executed step with workspace state"""

    step: ActionStep = Field(description="The executed action step")
    workspace_after: Dict[str, Any] = Field(
        description="Workspace state after execution"
    )
    execution_time: float = Field(
        default=0.0, description="Time taken to execute the step"
    )
    success: bool = Field(
        default=True, description="Whether the step executed successfully"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if execution failed"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class SkillModel(BaseModel):
    id: str = Field(default_factory=lambda: f"skill_{token_hex(8)}")
    name: str
    description: str
    action_sequence: list[ActionStep]
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    usage_count: int = 0
    effectiveness_score: float = 0.7
    version: int = 1


class LifeEvent(BaseModel):
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    summary: str
    importance: float = 0.5


PerceptionSource = Literal["workspace", "microworld"]
PerceptionType = Literal[
    "file_created", "file_modified", "file_deleted", "agent_appeared"
]


class PerceptionEvent(BaseModel):
    source: PerceptionSource
    type: PerceptionType
    content: dict[str, Any]
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


MemoryType = Literal[
    "user_input",
    "action_result",
    "reflection",
    "goal",
    "insight",
    "self_modification",
    "tool_usage",
    "inner_monologue",
    "debate",
    "self_experiment",
    "emotion",
    "persona_fork",
    "motivation_drift",
    "skill_transfer",
    "creativity",
    "meta_insight",
    "critical_error",
    "meta_learning",
    "self_explanation",
    "cross_agent_transfer",
    "perception",
    "skill_explanation",
]


class MemoryEntryModel(BaseModel):
    id: str = Field(default_factory=lambda: f"mem_{token_hex(12)}")
    type: MemoryType
    content: dict[str, Any]
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    importance: Annotated[float, Field(ge=0.0, le=1.0)] = 0.5
    embedding: list[float] | None = None


class MetaEventModel(BaseModel):
    type: MemoryType
    data: Any
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# --- PLANNER SCHEMAS ---


class PlanValidationResult(BaseModel):
    """Result of plan validation"""

    is_valid: bool = Field(description="Whether the plan is valid")
    errors: List[str] = Field(
        default_factory=list, description="List of validation errors"
    )
    warnings: List[str] = Field(
        default_factory=list, description="List of validation warnings"
    )


class PlanRepairContext(BaseModel):
    """Context for repairing a failed plan"""

    goal: str = Field(description="Original goal description")
    failed_plan: List[Dict[str, Any]] = Field(description="The plan that failed")
    failure_reason: str = Field(description="Reason for the failure")
    workspace_state: Dict[str, Any] = Field(
        default_factory=dict, description="Current workspace state"
    )


class PlanRefinementContext(BaseModel):
    """Context for refining an existing plan"""

    goal: str = Field(description="Original goal description")
    current_plan: List[Dict[str, Any]] = Field(description="Current plan to refine")
    feedback: Dict[str, Any] = Field(description="Feedback for refinement")


# --- EXECUTION SCHEMAS ---


class ExecutionMetrics(BaseModel):
    """Metrics for tracking execution performance"""

    steps_completed: int = Field(default=0, description="Number of steps completed")
    steps_failed: int = Field(default=0, description="Number of steps that failed")
    total_execution_time: float = Field(
        default=0.0, description="Total time spent executing"
    )
    average_step_time: float = Field(
        default=0.0, description="Average time per step"
    )
    success_rate: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Success rate"
    )


class ExecutionContext(BaseModel):
    """Context for step execution"""

    goal_id: str = Field(description="ID of the goal being executed")
    step_index: int = Field(description="Index of the current step")
    workspace: Dict[str, Any] = Field(
        default_factory=dict, description="Current workspace state"
    )
    execution_history: List[ExecutionStepRecord] = Field(
        default_factory=list, description="Previous execution history"
    )


class ExecutionResult(BaseModel):
    """Result of executing a step or plan"""

    success: bool = Field(description="Whether execution was successful")
    result: Dict[str, Any] = Field(default_factory=dict, description="Execution result data")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    execution_time: float = Field(default=0.0, description="Time taken for execution")
    workspace_changes: Dict[str, Any] = Field(default_factory=dict, description="Changes made to workspace")


# --- AGENT POOL SCHEMAS ---


class AgentState(BaseModel):
    """State information for an agent in the pool"""

    agent_id: str = Field(description="Unique agent identifier")
    persona: str = Field(description="Agent persona/role")
    trust_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Trust score"
    )
    last_active: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    tasks_completed: int = Field(description="Number of tasks completed")
    success_rate: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Task success rate"
    )
    current_workload: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Current workload"
    )
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")


class AgentPerformanceMetrics(BaseModel):
    """Performance metrics for an agent"""

    agent_id: str = Field(description="Agent identifier")
    total_tasks: int = Field(description="Total tasks assigned")
    successful_tasks: int = Field(description="Successfully completed tasks")
    average_response_time: float = Field(
        default=0.0, description="Average response time in seconds"
    )
    last_performance_update: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class DelegationRequest(BaseModel):
    """Request to delegate a task to an agent"""

    task_name: str = Field(description="Name of the task to delegate")
    target_agent: str = Field(description="Target agent for delegation")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    timeout: float = Field(default=30.0, description="Timeout in seconds")
    priority: int = Field(default=0, description="Task priority")


class DelegationResult(BaseModel):
    """Result of a delegation attempt"""

    success: bool = Field(description="Whether delegation was successful")
    agent_id: str = Field(description="Agent that handled the task")
    result: Dict[str, Any] = Field(default_factory=dict, description="Task result")
    execution_time: float = Field(default=0.0, description="Time taken to complete")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")

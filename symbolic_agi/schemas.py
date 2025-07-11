# symbolic_agi/schemas.py
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from secrets import token_hex
from typing import Annotated, Any, Literal, List, Dict, Optional
from enum import Enum
from pydantic import BaseModel, Field

# Enums
class GoalStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class GoalPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class GoalMode(str, Enum):
    AUTONOMOUS = "autonomous"
    USER_DIRECTED = "user_directed"

class GoalStatusEnum(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"

class MemoryType(str, Enum):
    OBSERVATION = "observation"
    REASONING = "reasoning"
    DECISION = "decision"
    REFLECTION = "reflection"
    GOAL = "goal"
    ERROR = "error"
    KNOWLEDGE = "knowledge"
    SKILL = "skill"
    CONVERSATION = "conversation"
    ACHIEVEMENT = "achievement"
    ACTION = "action"  # Added for action tracking
    META_LEARNING = "meta_learning"  # Added for meta-cognition
    DEBATE = "debate"  # Added for debate/discussion tracking
    PERCEPTION = "perception"  # Added for perception processing
    CREATIVITY = "creativity"  # Added for creative processes
    # Legacy memory types for backward compatibility
    MOTIVATION_DRIFT = "motivation_drift"
    SELF_EXPERIMENT = "self_experiment"
    META_INSIGHT = "meta_insight"
    SELF_MODIFICATION = "self_modification"
    CRITICAL_ERROR = "critical_error"

class MemoryTypeEnum(str, Enum):
    OBSERVATION = "observation"
    REASONING = "reasoning"
    DECISION = "decision"
    REFLECTION = "reflection"
    GOAL = "goal"
    ERROR = "error"
    KNOWLEDGE = "knowledge"
    SKILL = "skill"
    CONVERSATION = "conversation"
    ACHIEVEMENT = "achievement"
    ACTION = "action"
    META_LEARNING = "meta_learning"
    DEBATE = "debate"
    PERCEPTION = "perception"
    CREATIVITY = "creativity"
    # Legacy memory types for backward compatibility
    MOTIVATION_DRIFT = "motivation_drift"
    SELF_EXPERIMENT = "self_experiment"
    META_INSIGHT = "meta_insight"
    SELF_MODIFICATION = "self_modification"
    CRITICAL_ERROR = "critical_error"

# Core Models
class AGIConfig(BaseModel):
    name: str = "SymbolicAGI"
    scalable_agent_pool_size: int = 3
    meta_task_sleep_seconds: int = 10
    meta_task_timeout: int = 60
    memory_forgetting_threshold: float = 0.2
    debate_timeout_seconds: int = 90
    energy_regen_amount: int = 5
    initial_trust_score: float = 0.5
    max_trust_score: float = 1.0
    trust_decay_rate: float = 0.1
    trust_reward_rate: float = 0.05

class EmotionalState(BaseModel):
    primary: str = "curious"
    intensity: float = 0.5
    valence: float = 0.0

class ActionParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None

class ActionDefinition(BaseModel):
    name: str
    description: str
    parameters: List[ActionParameter] = Field(default_factory=list)
    returns: Optional[str] = None

class ActionStep(BaseModel):
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    expected_outcome: Optional[str] = None
    reasoning: Optional[str] = None

class GoalModel(BaseModel):
    id: str = Field(default_factory=lambda: token_hex(8))
    description: str
    priority: GoalPriority = GoalPriority.MEDIUM
    status: GoalStatus = GoalStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Goal(BaseModel):
    id: str
    description: str
    priority: str
    status: str
    created_at: datetime

class CreateGoalRequest(BaseModel):
    description: str
    priority: Optional[GoalPriority] = None

class MessageModel(BaseModel):
    sender: str
    recipient: str
    content: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None

class MemoryEntryModel(BaseModel):
    type: MemoryType
    content: Dict[str, Any]
    importance: float = 0.5
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    embedding: Optional[List[float]] = None
    id: Optional[str] = Field(default_factory=lambda: token_hex(16))

class SkillModel(BaseModel):
    name: str
    description: str
    implementation: str
    usage_count: int = 0
    success_count: int = 0
    last_used: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PerceptionEvent(BaseModel):
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class LifeEvent(BaseModel):
    event_type: str
    description: str
    emotional_impact: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MetaEventModel(BaseModel):
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PlannerOutput(BaseModel):
    thought: str
    plan: List[ActionStep]

class ExecutionStepRecord(BaseModel):
    step_index: int
    action: str
    parameters: Dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retries: int = 0

class ExecutionMetrics(BaseModel):
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    total_duration: float = 0.0
    average_step_duration: float = 0.0
    success_rate: float = 0.0

class ExecutionContext(BaseModel):
    goal: GoalModel
    plan: List[ActionStep]
    current_step: int = 0
    execution_history: List[ExecutionStepRecord] = Field(default_factory=list)
    metrics: ExecutionMetrics = Field(default_factory=ExecutionMetrics)
    workspace: Dict[str, Any] = Field(default_factory=dict)

class ExecutionResult(BaseModel):
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    metrics: ExecutionMetrics
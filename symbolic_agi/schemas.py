# symbolic_agi/schemas.py

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from secrets import token_hex
from typing import Annotated, Any, Literal

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
    sender_id: str
    receiver_id: str
    message_type: str
    payload: dict[str, Any]


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
    thought: str
    plan: list[ActionStep]


class ExecutionStepRecord(BaseModel):
    step: ActionStep
    workspace_after: dict[str, Any]


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

# symbolic_agi/db_models.py
from sqlalchemy import Column, String, DateTime, JSON, Integer, Float, Enum as SQLAlchemyEnum, Text
from sqlalchemy.orm import declarative_base
from .schemas import GoalStatus, GoalPriority, MemoryTypeEnum

Base = declarative_base()

class GoalOrm(Base):
    __tablename__ = 'goals'
    id = Column(String, primary_key=True)
    description = Column(Text, nullable=False)
    priority = Column(SQLAlchemyEnum(GoalPriority), nullable=False, default=GoalPriority.MEDIUM)
    status = Column(SQLAlchemyEnum(GoalStatus), nullable=False, default=GoalStatus.QUEUED)
    created_at = Column(DateTime, nullable=False)
    # Add other fields from Goal model as needed for persistence

class MemoryOrm(Base):
    __tablename__ = 'memories'
    id = Column(String, primary_key=True)
    type = Column(SQLAlchemyEnum(MemoryTypeEnum), nullable=False)
    content = Column(JSON, nullable=False)
    timestamp = Column(String, nullable=False)
    importance = Column(Float, nullable=False)
    embedding = Column(JSON)
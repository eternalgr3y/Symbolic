# symbolic_agi/skill_manager.py
import asyncio
import json
import logging
import inspect
import os
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional
from contextlib import asynccontextmanager

import aiosqlite

from . import config
from .schemas import ActionDefinition, ActionParameter, ActionStep, SkillModel

if TYPE_CHECKING:
    from .message_bus import RedisMessageBus

# Global registry for innate actions
INNATE_ACTIONS: Dict[str, Callable] = {}

def register_innate_action(func: Callable = None, *, name: str = None):
    """Decorator to register a function as an innate action."""
    def decorator(f: Callable) -> Callable:
        action_name = name or f.__name__
        INNATE_ACTIONS[action_name] = f
        return f
    
    if func is None:
        # Called with arguments: @register_innate_action(name="custom_name")
        return decorator
    else:
        # Called without arguments: @register_innate_action
        return decorator(func)

class SkillManager:
    """Manages the AGI's learned and innate skills."""
    
    def __init__(self, db_path: str = config.DB_PATH, message_bus: Optional["RedisMessageBus"] = None):
        self._db_path = db_path
        self.message_bus = message_bus
        self.learned_skills: Dict[str, SkillModel] = {}
        self.innate_actions: Dict[str, ActionDefinition] = {}
        self._initialized = False

    @classmethod
    async def create(cls, db_path: str = config.DB_PATH, message_bus: Optional["RedisMessageBus"] = None) -> "SkillManager":
        """Create and initialize a SkillManager instance."""
        instance = cls(db_path, message_bus)
        await instance._initialize()
        return instance

    async def _initialize(self) -> None:
        """Initialize the skill manager."""
        await self._load_skills()
        self._register_innate_actions()
        self._initialized = True
        logging.info(f"[SkillManager] Initialized with {len(self.learned_skills)} skills")

    async def _load_skills(self) -> None:
        """Load skills from database."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        
        async with aiosqlite.connect(self._db_path) as db:
            # Create table if needed
            await db.execute("""
                CREATE TABLE IF NOT EXISTS skills (
                    name TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    implementation TEXT NOT NULL,
                    usage_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    last_used TEXT,
                    metadata TEXT
                )
            """)
            await db.commit()
            
            # Load existing skills
            cursor = await db.execute("SELECT * FROM skills")
            rows = await cursor.fetchall()
            
            for row in rows:
                skill = SkillModel(
                    name=row[0],
                    description=row[1],
                    implementation=row[2],
                    usage_count=row[3],
                    success_count=row[4],
                    last_used=row[5],
                    metadata=json.loads(row[6]) if row[6] else {}
                )
                self.learned_skills[skill.name] = skill

    def _register_innate_actions(self) -> None:
        """Register all innate actions."""
        for name, func in INNATE_ACTIONS.items():
            sig = inspect.signature(func)
            params = []
            
            for param_name, param in sig.parameters.items():
                if param_name not in ['self', 'agi']:
                    param_type = "Any"
                    if param.annotation != param.empty:
                        param_type = str(param.annotation)
                    
                    params.append(ActionParameter(
                        name=param_name,
                        type=param_type,
                        description=f"Parameter {param_name}",
                        required=param.default == param.empty,
                        default=None if param.default == param.empty else param.default
                    ))
            
            self.innate_actions[name] = ActionDefinition(
                name=name,
                description=func.__doc__ or f"Innate action: {name}",
                parameters=params,
                returns="Any"
            )

    async def add_skill(self, skill: SkillModel) -> None:
        """Add a new learned skill."""
        self.learned_skills[skill.name] = skill
        
        # Save to database
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO skills 
                (name, description, implementation, usage_count, success_count, last_used, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                skill.name,
                skill.description,
                skill.implementation,
                skill.usage_count,
                skill.success_count,
                skill.last_used.isoformat() if skill.last_used else None,
                json.dumps(skill.metadata)
            ))
            await db.commit()

    def get_all_actions(self) -> Dict[str, ActionDefinition]:
        """Get all available actions (innate + learned)."""
        all_actions = self.innate_actions.copy()
        
        # Add learned skills as actions
        for skill_name, skill in self.learned_skills.items():
            all_actions[skill_name] = ActionDefinition(
                name=skill_name,
                description=skill.description,
                parameters=[],  # Learned skills might have dynamic parameters
                returns="Any"
            )
        
        return all_actions

    async def broadcast_skill_update(self, skill_name: str) -> None:
        """Broadcast skill update to all agents."""
        if self.message_bus:
            from .schemas import MessageModel
            
            message = MessageModel(
                sender="skill_manager",
                recipient="all_agents",
                content={
                    "type": "skill_update",
                    "skill_name": skill_name,
                    "action": "added"
                }
            )
            
            await self.message_bus.publish("skill_updates", message)
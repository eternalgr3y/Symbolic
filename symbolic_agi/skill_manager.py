# symbolic_agi/skill_manager.py
from contextlib import asynccontextmanager  # ADD THIS IMPORT AT TOP
import asyncio
import json
import logging
import inspect
import os
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

import aiosqlite

from . import config
from .schemas import ActionDefinition, ActionParameter, ActionStep, SkillModel

if TYPE_CHECKING:
    from .message_bus import RedisMessageBus


_innate_action_registry: List[ActionDefinition] = []


def register_innate_action(
    persona: str, description: str
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """A decorator to register a tool or skill as an innate action."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        params = []
        sig = inspect.signature(func)
        func_name = func.__name__.replace("skill_", "")
        for param in sig.parameters.values():
            if param.name not in ("self", "kwargs"):
                params.append(
                    ActionParameter(
                        name=param.name,
                        type=str(param.annotation),
                        description="",  # Could be enhanced to parse from docstring
                        required=param.default is inspect.Parameter.empty,
                    )
                )

        action_def = ActionDefinition(
            name=func_name,
            description=description,
            parameters=params,
            assigned_persona=persona,
        )
        setattr(func, "_innate_action_persona", persona)
        setattr(func, "_innate_action_def", action_def)
        _innate_action_registry.append(action_def)
        return func

    return decorator


class SkillManager:
    """Manages loading, saving, and using learned skills."""

    def __init__(
        self,
        db_path: str = config.DB_PATH,
        message_bus: Optional["RedisMessageBus"] = None,
    ):
        self._db_path = db_path
        self.skills: Dict[str, SkillModel] = {}
        self.innate_actions: List[ActionDefinition] = _innate_action_registry
        self.message_bus = message_bus
        self._save_lock = asyncio.Lock()

    @classmethod
    async def create(cls, db_path: str = config.DB_PATH, message_bus: Optional["RedisMessageBus"] = None) -> "SkillManager":
        """Asynchronous factory for creating a SkillManager instance."""
        instance = cls(db_path, message_bus)
        await instance._init_db()
        await instance._load_skills()
        logging.info("[SkillManager] Initialized with %d skills", len(instance.skills))
        return instance

    async def _init_db(self) -> None:
        """Initializes the database and tables if they don't exist."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS skills (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    action_sequence TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    usage_count INTEGER NOT NULL,
                    effectiveness_score REAL NOT NULL,
                    version INTEGER NOT NULL
                )
                """
            )
            await db.execute("CREATE INDEX IF NOT EXISTS idx_skill_name_version ON skills (name, version);")
            await db.commit()

# Add this context manager at the class level

    @asynccontextmanager
    async def _db_connection(self):
        """Context manager for database connections with proper cleanup."""
        async with self._save_lock:
            conn = await aiosqlite.connect(self.db_path)
            try:
                yield conn
            finally:
                await conn.close()

    # Fix the direct connection in get_skill method (around line 117)
    async def get_skill(self, skill_name: str) -> Optional[SkillModel]:
        """Retrieves a skill by name."""
        async with self._db_connection() as db:
            async with db.execute(
                "SELECT * FROM skills WHERE name = ? AND is_deleted = 0 ORDER BY version DESC LIMIT 1",
                (skill_name,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return SkillModel(
                        name=row[1],
                        description=row[2],
                        implementation=row[3],
                        version=row[4],
                        created_at=row[5],
                        updated_at=row[6],
                        tags=json.loads(row[7]) if row[7] else [],
                        usage_count=row[8],
                        success_count=row[9],
                        failure_count=row[10],
                        is_deleted=bool(row[11])
                    )
        return None

    # Fix the connection in _prune_old_skill_versions (around line 178)
    async def _prune_old_skill_versions(self) -> None:
        """Prunes old skill versions beyond the retention limit."""
        async with self._db_connection() as db:
            # Get skills with too many versions
            async with db.execute("""
                SELECT name, COUNT(*) as version_count 
                FROM skills 
                WHERE is_deleted = 0 
                GROUP BY name 
                HAVING version_count > ?
            """, (self.max_versions_per_skill,)) as cursor:
                skills_to_prune = await cursor.fetchall()
        
        # Prune excess versions for each skill
        for skill_name, version_count in skills_to_prune:
            excess_count = version_count - self.max_versions_per_skill
            await db.execute("""
                UPDATE skills SET is_deleted = 1 
                WHERE name = ? AND id IN (
                    SELECT id FROM skills 
                    WHERE name = ? 
                    ORDER BY version ASC 
                    LIMIT ?
                )
            """, (skill_name, skill_name, excess_count))
        
        await db.commit()

    async def _load_skills(self) -> None:
        """Loads skills from the database."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute("SELECT * FROM skills") as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    skill_dict = {
                        "id": row[0], "name": row[1], "description": row[2],
                        "action_sequence": json.loads(row[3]),
                        "created_at": row[4], "usage_count": row[5],
                        "effectiveness_score": row[6], "version": row[7]
                    }
                    self.skills[row[0]] = SkillModel.model_validate(skill_dict)

    async def _save_skill(self, skill: SkillModel) -> None:
        """Saves a single skill to the database."""
        async with self._save_lock:
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO skills VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        skill.id, skill.name, skill.description,
                        json.dumps([s.model_dump() for s in skill.action_sequence]),
                        skill.created_at, skill.usage_count,
                        skill.effectiveness_score, skill.version
                    )
                )
                await db.commit()

    async def add_new_skill(
        self, name: str, description: str, plan: List[ActionStep]
    ) -> None:
        """
        Creates a new, versioned skill from a successful plan and saves it.
        """
        versions_of_skill = [s for s in self.skills.values() if s.name == name]
        highest_version = max([s.version for s in versions_of_skill], default=0)
        new_version = highest_version + 1
        logging.info("Creating new skill '%s' version %d.", name, new_version)

        new_skill = SkillModel(
            name=name,
            description=description,
            action_sequence=plan,
            version=new_version,
        )
        self.skills[new_skill.id] = new_skill
        await self._save_skill(new_skill)
        await self._prune_old_skill_versions(name)

        if self.message_bus:
            from .schemas import MessageModel

            await self.message_bus.broadcast(
                MessageModel(
                    sender_id="SymbolicAGI_Orchestrator",
                    receiver_id="ALL",
                    message_type="new_skill_broadcast",
                    payload={
                        "skill_name": name,
                        "skill_description": description,
                        "skill_id": new_skill.id,
                        "version": new_version,
                    },
                )
            )

    async def _prune_old_skill_versions(self, skill_name: str, keep: int = 3) -> None:
        """Keeps only the N most recent versions of a skill."""
        versions_of_skill = [s for s in self.skills.values() if s.name == skill_name]
        if len(versions_of_skill) <= keep:
            return

        versions_of_skill.sort(key=lambda s: s.version, reverse=True)
        skills_to_prune = versions_of_skill[keep:]

        if skills_to_prune:
            async with self._save_lock:
                async with aiosqlite.connect(self._db_path) as db:
                    for skill in skills_to_prune:
                        logging.warning(
                            "Pruning old skill version: %s v%d (ID: %s)",
                            skill.name,
                            skill.version,
                            skill.id,
                        )
                        await db.execute("DELETE FROM skills WHERE id = ?", (skill.id,))
                        self.skills.pop(skill.id, None)
                    await db.commit()

    def get_skill_by_name(self, name: str) -> Optional[SkillModel]:
        """Finds the highest version of a skill by its unique name."""
        versions_of_skill = [s for s in self.skills.values() if s.name == name]
        if not versions_of_skill:
            return None

        skill = max(versions_of_skill, key=lambda s: s.version)
        action_names = [step.action for step in skill.action_sequence]
        logging.info(
            "[SkillManager] Retrieved skill '%s' with actions: %s",
            name,
            action_names,
        )
        return skill

    def is_skill(self, action_name: str) -> bool:
        """Checks if a given action name corresponds to a learned skill."""
        is_skill_result = any(
            skill.name == action_name for skill in self.skills.values()
        )
        logging.debug(
            "[SkillManager] Checking if '%s' is a skill: %s",
            action_name,
            is_skill_result,
        )
        return is_skill_result
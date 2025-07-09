# symbolic_agi/long_term_memory.py

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional, Set

import aiosqlite

from . import config
from .schemas import ActionStep, GoalModel, GoalStatus


class LongTermMemory:
    """
    Manages the AGI's long-term goals with robust persistence, error handling,
    and intelligent goal lifecycle management.
    """

    def __init__(self, db_path: str = config.DB_PATH):
        self._db_path = db_path
        self.goals: Dict[str, GoalModel] = {}
        self._save_lock = asyncio.Lock()
        self._db_pool: Optional[aiosqlite.Connection] = None
        self._goal_priority_cache: Dict[str, float] = {}
        self._last_cleanup = datetime.now(timezone.utc)

    @classmethod
    async def create(cls, db_path: str = config.DB_PATH) -> "LongTermMemory":
        """Factory method to create and initialize LongTermMemory."""
        instance = cls(db_path)
        await instance._init_db()
        await instance._load_goals()
        await instance._periodic_cleanup()
        return instance

    @asynccontextmanager
    async def _db_connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """Context manager for safe database connections with proper error handling."""
        conn = None
        try:
            conn = await aiosqlite.connect(self._db_path)
            conn.row_factory = aiosqlite.Row  # Enable dict-like access
            yield conn
        except Exception as e:
            logging.error("Database connection error: %s", e, exc_info=True)
            raise
        finally:
            if conn:
                await conn.close()

    async def _init_db(self) -> None:
        """Initializes the database and tables if they don't exist."""
        try:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            async with self._db_connection() as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS goals (
                        id TEXT PRIMARY KEY,
                        description TEXT NOT NULL,
                        sub_tasks TEXT,
                        status TEXT NOT NULL,
                        mode TEXT NOT NULL,
                        last_failure TEXT,
                        original_plan TEXT,
                        failure_count INTEGER NOT NULL DEFAULT 0,
                        max_failures INTEGER NOT NULL DEFAULT 3,
                        refinement_count INTEGER NOT NULL DEFAULT 0,
                        max_refinements INTEGER NOT NULL DEFAULT 3,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        priority REAL NOT NULL DEFAULT 0.5
                    )
                    """
                )
                
                # Create indexes for performance
                await db.execute("CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_goals_priority ON goals(priority DESC)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_goals_updated ON goals(updated_at)")
                
                await db.commit()
                logging.info("Database initialized successfully at %s", self._db_path)
        except Exception as e:
            logging.error("Failed to initialize database: %s", e, exc_info=True)
            raise

    async def _load_goals(self) -> None:
        """Loads active goals from the database with comprehensive error handling."""
        try:
            async with self._db_connection() as db:
                query = """
                SELECT * FROM goals 
                WHERE status NOT IN ('completed', 'failed') 
                ORDER BY priority DESC, created_at ASC
                """
                async with db.execute(query) as cursor:
                    rows = await cursor.fetchall()
                    goals_loaded = 0
                    
                    for row in rows:
                        try:
                            # Use row factory for dict-like access
                            goal_dict = {
                                "id": row["id"],
                                "description": row["description"],
                                "sub_tasks": self._safe_json_loads(row["sub_tasks"], []),
                                "status": row["status"],
                                "mode": row["mode"],
                                "last_failure": row["last_failure"],
                                "original_plan": self._safe_json_loads(row["original_plan"], None),
                                "failure_count": row["failure_count"] or 0,
                                "max_failures": row["max_failures"] or 3,
                                "refinement_count": row["refinement_count"] or 0,
                                "max_refinements": row["max_refinements"] or 3,
                            }
                            
                            goal = GoalModel.model_validate(goal_dict)
                            self.goals[goal.id] = goal
                            self._goal_priority_cache[goal.id] = row["priority"] if len(row.keys()) > 3 else 0.5
                            goals_loaded += 1
                            
                        except Exception as e:
                            logging.error("Failed to load goal %s: %s", row["id"] if "id" in row.keys() else "unknown", e)
                            continue
                    
                    logging.info("Successfully loaded %d goals from database", goals_loaded)
                    
        except Exception as e:
            logging.error("Critical error loading goals from database: %s", e, exc_info=True)
            # Don't raise - allow system to continue with empty goals dict

    async def add_goal(self, goal: GoalModel) -> None:
        """Adds a new goal to the long-term memory with robust validation and error handling."""
        if not goal.id or not goal.description:
            raise ValueError("Goal must have a valid ID and description")
        
        if goal.id in self.goals:
            logging.warning("Goal %s already exists, updating instead of adding", goal.id)
            await self.update_goal(goal)
            return
        
        # Calculate initial priority
        priority = await self._calculate_goal_priority(goal)
        self._goal_priority_cache[goal.id] = priority
        
        async with self._save_lock:
            try:
                self.goals[goal.id] = goal
                
                async with self._db_connection() as db:
                    await db.execute(
                        """INSERT INTO goals 
                           (id, description, sub_tasks, status, mode, last_failure, 
                            original_plan, failure_count, max_failures, 
                            refinement_count, max_refinements, created_at, updated_at, priority) 
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            goal.id, goal.description, 
                            json.dumps([t.model_dump() for t in goal.sub_tasks]),
                            goal.status, goal.mode, goal.last_failure,
                            json.dumps([t.model_dump() for t in goal.original_plan]) if goal.original_plan else None,
                            goal.failure_count, goal.max_failures,
                            goal.refinement_count, goal.max_refinements,
                            datetime.now(timezone.utc).isoformat(),
                            datetime.now(timezone.utc).isoformat(),
                            priority
                        )
                    )
                    await db.commit()
                    
                logging.info("Successfully added goal: %s", goal.id)
                
            except Exception as e:
                # Rollback in-memory state on database failure
                self.goals.pop(goal.id, None)
                self._goal_priority_cache.pop(goal.id, None)
                logging.error("Failed to add goal %s to database: %s", goal.id, e, exc_info=True)
                raise

    async def get_goal_by_id(self, goal_id: str) -> Optional[GoalModel]:
        """Retrieves a goal by its unique ID."""
        return self.goals.get(goal_id)

    async def update_goal_status(self, goal_id: str, status: GoalStatus) -> None:
        """Updates the status of a goal with validation."""
        if goal_id not in self.goals:
            raise ValueError(f"Goal {goal_id} does not exist")
        
        if goal := self.goals.get(goal_id):
            old_status = goal.status
            goal.status = status
            
            async with self._save_lock:
                try:
                    async with self._db_connection() as db:
                        await db.execute(
                            "UPDATE goals SET status = ?, updated_at = ? WHERE id = ?", 
                            (status, datetime.now(timezone.utc).isoformat(), goal_id)
                        )
                        await db.commit()
                    logging.info("Updated goal %s status: %s -> %s", goal_id, old_status, status)
                except Exception as e:
                    # Rollback status change
                    goal.status = old_status
                    logging.error("Failed to update goal %s status: %s", goal_id, e, exc_info=True)
                    raise

    async def get_active_goal(self) -> Optional[GoalModel]:
        """Retrieves the first active goal from the list."""
        for goal in self.goals.values():
            if goal.status == "active":
                return goal
        return None

    async def complete_sub_task(self, goal_id: str) -> None:
        """Removes the first sub-task from a goal's plan with atomic operations."""
        if goal := self.goals.get(goal_id):
            if goal.sub_tasks:
                async with self._save_lock:
                    try:
                        # Remove sub-task from memory
                        completed_task = goal.sub_tasks.pop(0)
                        
                        # Update database
                        await self._save_goal_to_db(goal)
                        
                        logging.info("Completed sub-task '%s' for goal %s", 
                                   completed_task.action, goal_id)
                    except Exception as e:
                        # Rollback - add the task back
                        goal.sub_tasks.insert(0, completed_task)
                        logging.error("Failed to complete sub-task for goal %s: %s", 
                                    goal_id, e, exc_info=True)
                        raise
            else:
                logging.warning("Attempted to complete sub-task for goal %s with no remaining tasks", goal_id)

    async def update_plan(self, goal_id: str, plan: List[ActionStep]) -> None:
        """Updates the plan (sub_tasks) for a goal with atomic operations."""
        if goal := self.goals.get(goal_id):
            async with self._save_lock:
                try:
                    old_plan = goal.sub_tasks.copy()
                    goal.sub_tasks = plan
                    await self._save_goal_to_db(goal)
                    logging.info("Updated plan for goal %s with %d steps", goal_id, len(plan))
                except Exception as e:
                    # Rollback plan change
                    goal.sub_tasks = old_plan
                    logging.error("Failed to update plan for goal %s: %s", goal_id, e, exc_info=True)
                    raise
        else:
            raise ValueError(f"Goal {goal_id} does not exist")

    async def invalidate_plan(self, goal_id: str, reason: str) -> None:
        """Marks a goal as failed with a reason and atomic operations."""
        if goal := self.goals.get(goal_id):
            async with self._save_lock:
                try:
                    old_status = goal.status
                    old_failure = goal.last_failure
                    
                    goal.status = "failed"  # type: ignore[assignment]
                    goal.last_failure = reason
                    await self._save_goal_to_db(goal)
                    
                    logging.warning("Invalidated goal %s: %s", goal_id, reason)
                except Exception as e:
                    # Rollback changes
                    goal.status = old_status
                    goal.last_failure = old_failure
                    logging.error("Failed to invalidate goal %s: %s", goal_id, e, exc_info=True)
                    raise
        else:
            raise ValueError(f"Goal {goal_id} does not exist")

    async def _save_goal_to_db(self, goal: GoalModel) -> None:
        """Helper method to save a goal to the database with proper error handling."""
        async with self._db_connection() as db:
            await db.execute(
                """UPDATE goals SET 
                   description=?, sub_tasks=?, status=?, mode=?, last_failure=?,
                   original_plan=?, failure_count=?, max_failures=?, 
                   refinement_count=?, max_refinements=?, updated_at=?
                   WHERE id=?""",
                (
                    goal.description,
                    json.dumps([t.model_dump() for t in goal.sub_tasks]),
                    goal.status, goal.mode, goal.last_failure,
                    json.dumps([t.model_dump() for t in goal.original_plan]) if goal.original_plan else None,
                    goal.failure_count, goal.max_failures,
                    goal.refinement_count, goal.max_refinements,
                    datetime.now(timezone.utc).isoformat(),
                    goal.id
                )
            )
            await db.commit()

    async def increment_failure_count(self, goal_id: str) -> int:
        """Increments the failure count for a goal and returns the new count."""
        if goal := self.goals.get(goal_id):
            async with self._save_lock:
                try:
                    old_count = goal.failure_count
                    goal.failure_count += 1
                    
                    async with self._db_connection() as db:
                        await db.execute(
                            "UPDATE goals SET failure_count = ?, updated_at = ? WHERE id = ?", 
                            (goal.failure_count, datetime.now(timezone.utc).isoformat(), goal_id)
                        )
                        await db.commit()
                    
                    logging.info("Incremented failure count for goal %s: %d -> %d", 
                               goal_id, old_count, goal.failure_count)
                    return goal.failure_count
                    
                except Exception as e:
                    # Rollback count change
                    goal.failure_count = old_count
                    logging.error("Failed to increment failure count for goal %s: %s", goal_id, e)
                    raise
        return 0

    async def increment_refinement_count(self, goal_id: str) -> int:
        """Increments the refinement count for a goal and returns the new count."""
        if goal := self.goals.get(goal_id):
            async with self._save_lock:
                try:
                    old_count = goal.refinement_count
                    goal.refinement_count += 1
                    
                    async with self._db_connection() as db:
                        await db.execute(
                            "UPDATE goals SET refinement_count = ?, updated_at = ? WHERE id = ?", 
                            (goal.refinement_count, datetime.now(timezone.utc).isoformat(), goal_id)
                        )
                        await db.commit()
                    
                    logging.info("Incremented refinement count for goal %s: %d -> %d", 
                               goal_id, old_count, goal.refinement_count)
                    return goal.refinement_count
                    
                except Exception as e:
                    # Rollback count change
                    goal.refinement_count = old_count
                    logging.error("Failed to increment refinement count for goal %s: %s", goal_id, e)
                    raise
        return 0

    async def archive_goal(self, goal_id: str) -> None:
        """Moves a goal from active memory to an archive file."""
        if goal := self.goals.pop(goal_id, None):
            try:
                await self.update_goal_status(goal_id, "completed")
                logging.info("Archived goal %s by setting status to completed.", goal_id)
            except Exception as e:
                logging.error(
                    "Failed to archive goal %s: %s", goal.id, e, exc_info=True
                )
                self.goals[goal.id] = goal

    def _safe_json_loads(self, data: Optional[str], default: Any = None) -> Any:
        """Safely loads JSON data with error handling."""
        if not data:
            return default
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            logging.warning("Failed to parse JSON data: %s, returning default", e)
            return default

    async def _periodic_cleanup(self) -> None:
        """Performs periodic cleanup of old completed goals."""
        try:
            cutoff_date = datetime.now(timezone.utc).replace(day=1)  # Beginning of month
            async with self._db_connection() as db:
                result = await db.execute(
                    "DELETE FROM goals WHERE status IN ('completed', 'failed') AND created_at < ?",
                    (cutoff_date.isoformat(),)
                )
                deleted_count = result.rowcount
                await db.commit()
                if deleted_count > 0:
                    logging.info("Cleaned up %d old goals", deleted_count)
        except Exception as e:
            logging.error("Failed to perform periodic cleanup: %s", e)

    async def _calculate_goal_priority(self, goal: GoalModel) -> float:
        """Calculates dynamic priority based on various factors."""
        base_priority = 0.5
        
        # Higher priority for failed goals (retry logic)
        if goal.failure_count > 0:
            base_priority += min(goal.failure_count * 0.1, 0.3)
        
        # Lower priority for frequently refined goals
        if goal.refinement_count > 0:
            base_priority -= min(goal.refinement_count * 0.05, 0.2)
        
        # Time decay - older goals get slightly lower priority
        # (This would need creation timestamp in the future)
        
        return max(0.1, min(1.0, base_priority))

    async def update_goal(self, goal: GoalModel) -> None:
        """Updates an existing goal with validation and error handling."""
        if not goal.id or goal.id not in self.goals:
            raise ValueError(f"Goal {goal.id} does not exist, cannot update")
        
        async with self._save_lock:
            try:
                # Update in-memory first
                old_goal = self.goals[goal.id]
                self.goals[goal.id] = goal
                
                # Recalculate priority
                priority = await self._calculate_goal_priority(goal)
                self._goal_priority_cache[goal.id] = priority
                
                # Update database
                async with self._db_connection() as db:
                    await db.execute(
                        """UPDATE goals SET 
                           description=?, sub_tasks=?, status=?, mode=?, last_failure=?,
                           original_plan=?, failure_count=?, max_failures=?, 
                           refinement_count=?, max_refinements=?, updated_at=?, priority=?
                           WHERE id=?""",
                        (
                            goal.description,
                            json.dumps([t.model_dump() for t in goal.sub_tasks]),
                            goal.status, goal.mode, goal.last_failure,
                            json.dumps([t.model_dump() for t in goal.original_plan]) if goal.original_plan else None,
                            goal.failure_count, goal.max_failures,
                            goal.refinement_count, goal.max_refinements,
                            datetime.now(timezone.utc).isoformat(),
                            priority,
                            goal.id
                        )
                    )
                    await db.commit()
                    
                logging.info("Successfully updated goal: %s", goal.id)
                
            except Exception as e:
                # Rollback in-memory state on database failure
                self.goals[goal.id] = old_goal
                logging.error("Failed to update goal %s in database: %s", goal.id, e, exc_info=True)
                raise
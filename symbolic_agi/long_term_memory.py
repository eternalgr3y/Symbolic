# symbolic_agi/long_term_memory.py
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiosqlite

from . import config
from .schemas import MemoryEntryModel, MemoryType

class LongTermMemory:
    """Manages long-term memory storage and retrieval."""
    
    def __init__(self, db_path: str = config.DB_PATH):
        self._db_path = db_path
        self._initialized = False

    @classmethod
    async def create(cls, db_path: str = config.DB_PATH) -> "LongTermMemory":
        """Create and initialize a LongTermMemory instance."""
        instance = cls(db_path)
        await instance._initialize()
        return instance

    async def _initialize(self) -> None:
        """Initialize the database."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        
        async with aiosqlite.connect(self._db_path) as db:
            # Create tables
            await db.execute("""
                CREATE TABLE IF NOT EXISTS long_term_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT UNIQUE NOT NULL,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_type 
                ON long_term_memories(type)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_timestamp 
                ON long_term_memories(timestamp)
            """)
            
            await db.commit()
            
        self._initialized = True
        logging.info("[LongTermMemory] Initialized")

    async def store_memory(self, memory: MemoryEntryModel) -> bool:
        """Store a memory in long-term storage."""
        try:
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO long_term_memories 
                    (memory_id, type, content, importance, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    memory.id,
                    memory.type.value,
                    json.dumps(memory.content),
                    memory.importance,
                    memory.timestamp.isoformat(),
                    json.dumps(memory.content.get("metadata", {}))
                ))
                await db.commit()
                
            return True
            
        except Exception as e:
            logging.error(f"[LongTermMemory] Failed to store memory: {e}")
            return False

    async def retrieve_memories(
        self,
        memory_type: Optional[MemoryType] = None,
        limit: int = 100,
        min_importance: float = 0.0
    ) -> List[MemoryEntryModel]:
        """Retrieve memories from long-term storage."""
        try:
            memories = []
            
            async with aiosqlite.connect(self._db_path) as db:
                query = """
                    SELECT memory_id, type, content, importance, timestamp 
                    FROM long_term_memories
                    WHERE importance >= ?
                """
                params: List[Any] = [min_importance]
                
                if memory_type:
                    query += " AND type = ?"
                    params.append(memory_type.value)
                    
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
                
                for row in rows:
                    memory = MemoryEntryModel(
                        id=row[0],
                        type=MemoryType(row[1]),
                        content=json.loads(row[2]),
                        importance=row[3],
                        timestamp=datetime.fromisoformat(row[4])
                    )
                    memories.append(memory)
                    
            return memories
            
        except Exception as e:
            logging.error(f"[LongTermMemory] Failed to retrieve memories: {e}")
            return []

    async def search_memories(self, query: str, limit: int = 10) -> List[MemoryEntryModel]:
        """Search memories by content."""
        try:
            memories = []
            
            async with aiosqlite.connect(self._db_path) as db:
                cursor = await db.execute("""
                    SELECT memory_id, type, content, importance, timestamp 
                    FROM long_term_memories
                    WHERE content LIKE ?
                    ORDER BY importance DESC, timestamp DESC
                    LIMIT ?
                """, (f"%{query}%", limit))
                
                rows = await cursor.fetchall()
                
                for row in rows:
                    memory = MemoryEntryModel(
                        id=row[0],
                        type=MemoryType(row[1]),
                        content=json.loads(row[2]),
                        importance=row[3],
                        timestamp=datetime.fromisoformat(row[4])
                    )
                    memories.append(memory)
                    
            return memories
            
        except Exception as e:
            logging.error(f"[LongTermMemory] Failed to search memories: {e}")
            return []

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about stored memories."""
        try:
            async with aiosqlite.connect(self._db_path) as db:
                # Total count
                cursor = await db.execute("SELECT COUNT(*) FROM long_term_memories")
                total_count = (await cursor.fetchone())[0]
                
                # Count by type
                cursor = await db.execute("""
                    SELECT type, COUNT(*) 
                    FROM long_term_memories 
                    GROUP BY type
                """)
                type_counts = dict(await cursor.fetchall())
                
                # Average importance
                cursor = await db.execute("SELECT AVG(importance) FROM long_term_memories")
                avg_importance = (await cursor.fetchone())[0] or 0.0
                
                return {
                    "total_memories": total_count,
                    "memories_by_type": type_counts,
                    "average_importance": avg_importance
                }
                
        except Exception as e:
            logging.error(f"[LongTermMemory] Failed to get stats: {e}")
            return {
                "total_memories": 0,
                "memories_by_type": {},
                "average_importance": 0.0
            }
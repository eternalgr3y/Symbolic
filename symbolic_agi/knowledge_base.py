# symbolic_agi/knowledge_base.py

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import aiosqlite

from . import config
from .schemas import MemoryEntryModel, MemoryType
from .symbolic_memory import SymbolicMemory

class KnowledgeItemType(str, Enum):
    FACT = "fact"
    HYPOTHESIS = "hypothesis"
    ENTITY = "entity"
    RULE = "rule"

@dataclass
class KnowledgeItem:
    """A structured piece of knowledge derived from experience."""
    id: str = field(default_factory=lambda: f"kn_{uuid.uuid4().hex[:10]}")
    type: KnowledgeItemType
    content: Dict[str, Any]
    confidence: float = 0.5
    source_goal_id: Optional[str] = None
    source_memory_ids: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class KnowledgeBase:
    """
    A centralized, structured repository for the AGI's distilled knowledge.
    It uses its own database for structured data and leverages SymbolicMemory for semantic search.
    """

    def __init__(self, db_path: str = config.DB_PATH, memory_system: Optional[SymbolicMemory] = None):
        self._db_path = db_path
        self.memory = memory_system
        self.knowledge: Dict[str, KnowledgeItem] = {}
        self._save_lock = asyncio.Lock()
        logging.info("KnowledgeBase initialized.")

    @classmethod
    async def create(cls, db_path: str = config.DB_PATH, memory_system: Optional[SymbolicMemory] = None) -> "KnowledgeBase":
        """Asynchronous factory for creating a KnowledgeBase instance."""
        instance = cls(db_path, memory_system)
        await instance._init_db()
        await instance._load_knowledge()
        return instance

    async def _init_db(self) -> None:
        """Initializes the database table for knowledge items."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    source_goal_id TEXT,
                    source_memory_ids TEXT,
                    timestamp TEXT NOT NULL
                )
                """
            )
            await db.execute("CREATE INDEX IF NOT EXISTS idx_kb_type ON knowledge_base(type)")
            await db.commit()

    async def _load_knowledge(self) -> None:
        """Loads all knowledge items from the database into memory."""
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM knowledge_base") as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    item = KnowledgeItem(
                        id=row["id"],
                        type=KnowledgeItemType(row["type"]),
                        content=json.loads(row["content"]),
                        confidence=row["confidence"],
                        source_goal_id=row["source_goal_id"],
                        source_memory_ids=json.loads(row["source_memory_ids"]),
                        timestamp=row["timestamp"],
                    )
                    self.knowledge[item.id] = item
        logging.info("Loaded %d items into the Knowledge Base.", len(self.knowledge))

    async def add_knowledge(self, item: KnowledgeItem) -> None:
        """Adds a new knowledge item to the KB and saves it."""
        async with self._save_lock:
            self.knowledge[item.id] = item
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO knowledge_base VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        item.id,
                        item.type.value,
                        json.dumps(item.content),
                        item.confidence,
                        item.source_goal_id,
                        json.dumps(item.source_memory_ids),
                        item.timestamp,
                    ),
                )
                await db.commit()

        if self.memory:
            memory_content = {
                "knowledge_id": item.id,
                "knowledge_type": item.type.value,
                "summary": item.content.get("summary", str(item.content))
            }
            mem_entry = MemoryEntryModel(
                type="insight",
                content=memory_content,
                importance=item.confidence,
            )
            await self.memory.add_memory(mem_entry)

        logging.info(f"Added knowledge item {item.id} of type '{item.type.value}' to KB.")

    async def query_knowledge(self, query: str, item_types: Optional[List[KnowledgeItemType]] = None, limit: int = 5) -> List[KnowledgeItem]:
        """
        Queries the knowledge base using semantic search via the memory system,
        then retrieves the full structured items.
        """
        if not self.memory:
            logging.warning("Cannot query knowledge base without a memory system for semantic search.")
            return []

        relevant_memories = await self.memory.get_relevant_memories(query, memory_types=["insight"], limit=limit)

        knowledge_ids = [mem.content.get("knowledge_id") for mem in relevant_memories if "knowledge_id" in mem.content]

        results = [self.knowledge[kid] for kid in knowledge_ids if kid in self.knowledge]

        if item_types:
            results = [item for item in results if item.type in item_types]

        return results
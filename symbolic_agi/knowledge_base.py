import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import aiosqlite

from . import config
from .schemas import MemoryEntryModel, MemoryType

if TYPE_CHECKING:
    from .symbolic_memory import SymbolicMemory

class KnowledgeItemType(Enum):
    """Types of knowledge items."""
    RULE = "rule"
    FACT = "fact"
    HYPOTHESIS = "hypothesis"

@dataclass
class KnowledgeItem:
    """A structured piece of knowledge with type, content, and metadata."""
    # Non-default fields must come first
    id: str
    type: KnowledgeItemType
    content: Dict[str, Any]
    
    # Fields with default values
    importance: float = 0.5
    confidence: float = 1.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    @classmethod
    def create(cls, type: KnowledgeItemType, content: Dict[str, Any], **kwargs) -> "KnowledgeItem":
        return cls(id=f"kn_{uuid.uuid4().hex[:8]}", type=type, content=content, **kwargs)

class KnowledgeBase:
    """Manages structured knowledge storage and retrieval."""
    
    def __init__(self, memory_system: "SymbolicMemory", db_path: str = config.DB_PATH):
        self.memory_system = memory_system
        self._db_path = db_path
        self._initialized = False
        self.knowledge: Dict[str, KnowledgeItem] = {}

    @classmethod
    async def create(cls, memory_system: "SymbolicMemory", db_path: str = config.DB_PATH) -> "KnowledgeBase":
        """Create and initialize a KnowledgeBase instance."""
        instance = cls(memory_system, db_path)
        await instance._initialize()
        return instance

    async def _initialize(self) -> None:
        """Initialize the knowledge base."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        
        async with aiosqlite.connect(self._db_path) as db:
            # Create knowledge tables
            await db.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance REAL DEFAULT 0.5,
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    source TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(subject, predicate, object)
                )
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_kb_subject 
                ON knowledge_facts(subject)
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_concepts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    concept TEXT UNIQUE NOT NULL,
                    definition TEXT,
                    category TEXT,
                    related_concepts TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.commit()
            
        # Load existing knowledge
        await self._load_knowledge()
            
        self._initialized = True
        logging.info("[KnowledgeBase] Initialized")

    async def _load_knowledge(self) -> None:
        """Load knowledge items from database."""
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("SELECT * FROM knowledge_base")
            rows = await cursor.fetchall()
            
            for row in rows:
                item = KnowledgeItem(
                    id=row[0],
                    type=KnowledgeItemType(row[1]),
                    content=json.loads(row[2]),
                    importance=row[3],
                    confidence=row[4],
                    created_at=row[5]
                )
                self.knowledge[item.id] = item

    async def add_knowledge(self, item: KnowledgeItem) -> None:
        """Adds a new knowledge item and persists it to the database."""
        if item.id in self.knowledge:
            logging.warning(f"Knowledge item {item.id} already exists. Overwriting.")
            
        self.knowledge[item.id] = item
        
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO knowledge_base VALUES (?, ?, ?, ?, ?, ?)",
                (item.id, item.type.value, json.dumps(item.content), item.importance, item.confidence, item.created_at)
            )
            await db.commit()
            
        logging.info(f"Added knowledge: {item.type.name} - {item.id}")

    def query_knowledge(self, query: str, limit: int = 5) -> List[KnowledgeItem]:
        """Query knowledge items by content similarity (simple keyword match for now)."""
        results = []
        query_lower = query.lower()
        
        for item in self.knowledge.values():
            content_str = json.dumps(item.content).lower()
            if query_lower in content_str:
                results.append(item)
                
        # Sort by importance and limit
        results.sort(key=lambda x: x.importance, reverse=True)
        return results[:limit]

    async def add_fact(
        self,
        subject: str,
        predicate: str,
        obj: str,
        confidence: float = 1.0,
        source: Optional[str] = None
    ) -> bool:
        """Add a fact to the knowledge base."""
        try:
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO knowledge_facts 
                    (subject, predicate, object, confidence, source)
                    VALUES (?, ?, ?, ?, ?)
                """, (subject, predicate, obj, confidence, source))
                await db.commit()
                
            # Also store in memory
            memory = MemoryEntryModel(
                type=MemoryType.KNOWLEDGE,
                content={
                    "fact": {
                        "subject": subject,
                        "predicate": predicate,
                        "object": obj
                    },
                    "confidence": confidence,
                    "source": source
                },
                importance=confidence * 0.7
            )
            await self.memory_system.add_memory(memory)
            
            return True
            
        except Exception as e:
            logging.error(f"[KnowledgeBase] Failed to add fact: {e}")
            return False

    async def query_facts(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        obj: Optional[str] = None,
        min_confidence: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Query facts from the knowledge base."""
        try:
            facts = []
            
            async with aiosqlite.connect(self._db_path) as db:
                query = "SELECT * FROM knowledge_facts WHERE confidence >= ?"
                params: List[Any] = [min_confidence]
                
                if subject:
                    query += " AND subject = ?"
                    params.append(subject)
                if predicate:
                    query += " AND predicate = ?"
                    params.append(predicate)
                if obj:
                    query += " AND object = ?"
                    params.append(obj)
                    
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
                
                for row in rows:
                    facts.append({
                        "id": row[0],
                        "subject": row[1],
                        "predicate": row[2],
                        "object": row[3],
                        "confidence": row[4],
                        "source": row[5],
                        "timestamp": row[6]
                    })
                    
            return facts
            
        except Exception as e:
            logging.error(f"[KnowledgeBase] Failed to query facts: {e}")
            return []

    async def add_concept(
        self,
        concept: str,
        definition: str,
        category: Optional[str] = None,
        related_concepts: Optional[List[str]] = None
    ) -> bool:
        """Add a concept to the knowledge base."""
        try:
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO knowledge_concepts 
                    (concept, definition, category, related_concepts)
                    VALUES (?, ?, ?, ?)
                """, (
                    concept,
                    definition,
                    category,
                    json.dumps(related_concepts) if related_concepts else None
                ))
                await db.commit()
                
            return True
            
        except Exception as e:
            logging.error(f"[KnowledgeBase] Failed to add concept: {e}")
            return False

    async def get_concept(self, concept: str) -> Optional[Dict[str, Any]]:
        """Get a concept from the knowledge base."""
        try:
            async with aiosqlite.connect(self._db_path) as db:
                cursor = await db.execute(
                    "SELECT * FROM knowledge_concepts WHERE concept = ?",
                    (concept,)
                )
                row = await cursor.fetchone()
                
                if row:
                    return {
                        "id": row[0],
                        "concept": row[1],
                        "definition": row[2],
                        "category": row[3],
                        "related_concepts": json.loads(row[4]) if row[4] else [],
                        "timestamp": row[5]
                    }
                    
            return None
            
        except Exception as e:
            logging.error(f"[KnowledgeBase] Failed to get concept: {e}")
            return None

    async def search_concepts(self, query: str) -> List[Dict[str, Any]]:
        """Search for concepts matching a query."""
        try:
            concepts = []
            
            async with aiosqlite.connect(self._db_path) as db:
                cursor = await db.execute("""
                    SELECT * FROM knowledge_concepts 
                    WHERE concept LIKE ? OR definition LIKE ?
                    LIMIT 20
                """, (f"%{query}%", f"%{query}%"))
                
                rows = await cursor.fetchall()
                
                for row in rows:
                    concepts.append({
                        "id": row[0],
                        "concept": row[1],
                        "definition": row[2],
                        "category": row[3],
                        "related_concepts": json.loads(row[4]) if row[4] else [],
                        "timestamp": row[5]
                    })
                    
            return concepts
            
        except Exception as e:
            logging.error(f"[KnowledgeBase] Failed to search concepts: {e}")
            return []
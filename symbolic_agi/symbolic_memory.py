# symbolic_agi/symbolic_memory.py
import asyncio
import hashlib
import json
import logging
import os
import stat
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

import aiosqlite
import faiss
import numpy as np

from . import config, metrics
from .api_client import monitored_embedding_creation
from .schemas import MemoryEntryModel, MemoryType

if TYPE_CHECKING:
    from openai import AsyncOpenAI

class SymbolicMemory:
    """Enhanced memory system with SQLite persistence and FAISS vector search."""
    
    # Data volume limits
    MAX_CONTENT_SIZE = 1024 * 1024  # 1MB per memory entry
    MAX_DB_SIZE_MB = 500  # 500MB database size limit
    MAX_MEMORIES = 100000  # Maximum number of memories
    
    def __init__(self, client: "AsyncOpenAI", db_path: str = config.DB_PATH):
        self.client = client
        self._db_path = db_path
        self.memory_data: List[MemoryEntryModel] = []
        self.faiss_index: Optional[faiss.IndexFlatL2] = None
        self.embedding_dim = 1536
        self.pending_memories: List[MemoryEntryModel] = []
        self._embedding_task: Optional[asyncio.Task] = None
        self._initialized = False
        self._memory_hashes: Set[str] = set()

    @classmethod
    async def create(cls, client: "AsyncOpenAI", db_path: str = config.DB_PATH) -> "SymbolicMemory":
        """Create and initialize a SymbolicMemory instance."""
        instance = cls(client, db_path)
        await instance._initialize()
        instance._embedding_task = asyncio.create_task(instance._embedding_daemon())
        return instance

    async def _initialize(self) -> None:
        """Initialize the database and load existing memories."""
        await self._init_db_and_load()
        self.faiss_index = faiss.IndexFlatL2(self.embedding_dim)
        self._initialized = True

    async def _init_db_and_load(self) -> None:
        """Initialize the database and load existing memories."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY,
                    uuid TEXT UNIQUE NOT NULL,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    importance REAL NOT NULL,
                    embedding BLOB
                )
            """)
            await db.commit()

            # Load existing memories
            cursor = await db.execute("SELECT id, uuid, type, content, timestamp, importance FROM memories")
            rows = await cursor.fetchall()
            
            for row in rows:
                try:
                    # Try to create MemoryType from the stored type
                    memory_type = MemoryType(row[2])
                except ValueError:
                    # If the type is not valid, skip this memory or default to OBSERVATION
                    logging.warning(f"Invalid memory type '{row[2]}' found in database, skipping")
                    continue
                
                mem_dict = {
                    "id": row[1],
                    "type": memory_type,
                    "content": json.loads(row[3]),
                    "timestamp": row[4],
                    "importance": row[5]
                }
                memory = MemoryEntryModel(**mem_dict)
                self.memory_data.append(memory)
                
                # Add to hash set
                content_hash = self._hash_content(memory.content)
                self._memory_hashes.add(content_hash)
            
            logging.info(f"Loaded {len(self.memory_data)} memories from SQLite.")

    def _hash_content(self, content: Dict[str, Any]) -> str:
        """Generate a hash for memory content."""
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.md5(content_str.encode()).hexdigest()

    async def add_memory(self, memory: MemoryEntryModel) -> None:
        """Add a memory to the system."""
        # Validate content size first
        try:
            self._validate_content_size(memory.content)
        except ValueError as e:
            logging.warning(f"Memory rejected due to size: {e}")
            return
        
        # Check for duplicates
        content_hash = self._hash_content(memory.content)
        if content_hash in self._memory_hashes:
            logging.debug("Skipping duplicate memory")
            return
        
        # Check database limits before adding
        await self._check_database_limits()
            
        self._memory_hashes.add(content_hash)
        self.memory_data.append(memory)
        self.pending_memories.append(memory)
        
        # Save to database immediately
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO memories (uuid, type, content, timestamp, importance, embedding) VALUES (?, ?, ?, ?, ?, ?)",
                (memory.id, memory.type.value, json.dumps(memory.content), 
                 memory.timestamp.isoformat(), memory.importance, None)
            )
            await db.commit()
        
        metrics.MEMORY_ENTRIES.set(len(self.memory_data))

    async def search_memories(
        self,
        query: str,
        k: int = 5,
        memory_types: Optional[List[MemoryType]] = None
    ) -> List[MemoryEntryModel]:
        """Search memories using semantic similarity."""
        if not self.faiss_index or self.faiss_index.ntotal == 0:
            return []
            
        try:
            # Get query embedding
            query_embedding = await self.embed_async([query])
            
            # Search FAISS
            _, indices = self.faiss_index.search(query_embedding, min(k, self.faiss_index.ntotal))
            
            results = []
            for idx in indices[0]:
                if 0 <= idx < len(self.memory_data):
                    memory = self.memory_data[idx]
                    if not memory_types or memory.type in memory_types:
                        results.append(memory)
                        
            return results[:k]
            
        except Exception as e:
            logging.error(f"Memory search failed: {e}")
            return []

    async def embed_async(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for texts."""
        try:
            response = await monitored_embedding_creation(
                self.client,
                input=texts,
                model="text-embedding-ada-002"
            )
            embeddings = [item.embedding for item in response.data]
            return np.array(embeddings, dtype='float32')
        except Exception as e:
            logging.error(f"Embedding generation failed: {e}")
            raise

    async def _embedding_daemon(self) -> None:
        """Background task to generate embeddings for pending memories."""
        while True:
            try:
                if self.pending_memories:
                    batch_size = min(len(self.pending_memories), 20)
                    batch = self.pending_memories[:batch_size]
                    self.pending_memories = self.pending_memories[batch_size:]
                    
                    texts = [json.dumps(m.content) for m in batch]
                    embeddings = await self.embed_async(texts)
                    
                    # Add to FAISS
                    if self.faiss_index:
                        self.faiss_index.add(embeddings)
                        
                    # Update database
                    async with aiosqlite.connect(self._db_path) as db:
                        for memory, embedding in zip(batch, embeddings):
                            await db.execute(
                                "UPDATE memories SET embedding = ? WHERE uuid = ?",
                                (embedding.tobytes(), memory.id)
                            )
                        await db.commit()
                        
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Embedding daemon error: {e}")
                await asyncio.sleep(30)

    def get_recent_memories(self, limit: int = 10) -> List[MemoryEntryModel]:
        """Get the most recent memories."""
        return sorted(self.memory_data, key=lambda m: m.timestamp, reverse=True)[:limit]

    def get_total_memory_count(self) -> int:
        """Get total number of memories."""
        return len(self.memory_data)

    async def _check_database_limits(self) -> None:
        """Check database size and memory count limits."""
        # Check file size
        if os.path.exists(self._db_path):
            size_mb = os.path.getsize(self._db_path) / (1024 * 1024)
            if size_mb > self.MAX_DB_SIZE_MB:
                logging.warning(f"Database size ({size_mb:.1f}MB) exceeds limit ({self.MAX_DB_SIZE_MB}MB)")
                await self._cleanup_old_memories()
        
        # Check memory count
        if len(self.memory_data) > self.MAX_MEMORIES:
            logging.warning(f"Memory count ({len(self.memory_data)}) exceeds limit ({self.MAX_MEMORIES})")
            await self._cleanup_old_memories()

    async def _cleanup_old_memories(self) -> None:
        """Remove old, low-importance memories to free space."""
        if len(self.memory_data) < 1000:  # Don't cleanup if we have few memories
            return
            
        # Sort by importance (ascending) and age (oldest first)
        memories_to_remove = sorted(
            self.memory_data,
            key=lambda m: (m.importance, m.timestamp)
        )[:len(self.memory_data) // 10]  # Remove 10% of memories
        
        memory_ids_to_remove = [m.id for m in memories_to_remove]
        
        # Remove from database
        async with aiosqlite.connect(self._db_path) as db:
            placeholders = ','.join(['?'] * len(memory_ids_to_remove))
            await db.execute(f"DELETE FROM memories WHERE uuid IN ({placeholders})", memory_ids_to_remove)
            await db.commit()
        
        # Remove from memory
        self.memory_data = [m for m in self.memory_data if m.id not in memory_ids_to_remove]
        
        # Remove from hash set
        for memory in memories_to_remove:
            content_hash = self._hash_content(memory.content)
            self._memory_hashes.discard(content_hash)
        
        logging.info(f"Cleaned up {len(memories_to_remove)} old memories")

    def _validate_content_size(self, content: Dict[str, Any]) -> None:
        """Validate that content doesn't exceed size limits."""
        content_str = json.dumps(content)
        if len(content_str.encode('utf-8')) > self.MAX_CONTENT_SIZE:
            raise ValueError(f"Memory content too large: {len(content_str.encode('utf-8'))} bytes (max: {self.MAX_CONTENT_SIZE})")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get current database usage statistics."""
        stats = {
            "memory_count": len(self.memory_data),
            "max_memories": self.MAX_MEMORIES,
            "memory_usage_percent": (len(self.memory_data) / self.MAX_MEMORIES) * 100,
            "database_size_mb": 0,
            "max_db_size_mb": self.MAX_DB_SIZE_MB,
            "database_usage_percent": 0
        }
        
        if os.path.exists(self._db_path):
            size_bytes = os.path.getsize(self._db_path)
            stats["database_size_mb"] = size_bytes / (1024 * 1024)
            stats["database_usage_percent"] = (stats["database_size_mb"] / self.MAX_DB_SIZE_MB) * 100
        
        return stats

    @staticmethod
    def _secure_database_file(db_path: str) -> None:
        """Set secure permissions on the database file (owner read/write only)."""
        if not os.path.exists(db_path):
            return
            
        try:
            # Set permissions to 600 (owner read/write only)
            # This prevents other users/processes from accessing the database
            os.chmod(db_path, stat.S_IRUSR | stat.S_IWUSR)
            logging.info(f"Secured database file permissions: {db_path}")
        except OSError as e:
            logging.warning(f"Could not set secure permissions on {db_path}: {e}")
    
    @staticmethod  
    def _create_secure_directory(dir_path: str) -> None:
        """Create directory with secure permissions."""
        try:
            os.makedirs(dir_path, mode=0o700, exist_ok=True)  # Owner access only
            logging.debug(f"Created secure directory: {dir_path}")
        except OSError as e:
            logging.warning(f"Could not create secure directory {dir_path}: {e}")

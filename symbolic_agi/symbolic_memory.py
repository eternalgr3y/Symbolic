# symbolic_agi/symbolic_memory.py

import asyncio
import json
import logging
import os
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple  # UPDATE THIS

import aiosqlite
import faiss
import numpy as np
from openai import APIConnectionError, AsyncOpenAI, OpenAIError, RateLimitError

from . import config, metrics
from .api_client import monitored_chat_completion, monitored_embedding_creation
from .schemas import MemoryEntryModel, MemoryType


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""
    pass


class SymbolicMemory:
    """Manages the AGI's memory using a SQLite DB and FAISS index."""

    faiss_index: faiss.IndexIDMap
    _flush_task: Optional[asyncio.Task[None]]

    def __init__(self: "SymbolicMemory", client: AsyncOpenAI, db_path: str = config.DB_PATH):
        self.client = client
        self._db_path = db_path
        self.memory_map: Dict[int, MemoryEntryModel] = {}
        self.faiss_index_path = os.path.join(os.path.dirname(db_path), "symbolic_mem.index")
        self.faiss_index = self._load_faiss(self.faiss_index_path)
        self._embedding_buffer: List[MemoryEntryModel] = []
        self._embedding_batch_size: int = 10
        self._flush_task = asyncio.create_task(self._embed_daemon())
        
        # ADD THESE NEW ATTRIBUTES
        self.embedding_cache: Dict[str, np.ndarray] = {}
        self.cache_max_size = 1000
        self.pending_memories: List[MemoryEntryModel] = []

    @classmethod
    async def create(cls, client: AsyncOpenAI, db_path: str = config.DB_PATH) -> "SymbolicMemory":
        """Asynchronous factory for creating a SymbolicMemory instance."""
        instance = cls(client, db_path)
        await instance._init_db_and_load()
        return instance

    async def shutdown(self) -> None:
        """Gracefully shuts down the embedding daemon task and saves state."""
        logging.info("Starting SymbolicMemory shutdown...")
        
        # Cancel the flush task and wait with timeout
        await self._shutdown_flush_task()
        
        # Process any remaining buffered memories with error handling
        await self._safe_process_remaining_memories()
        
        # Save the index with error handling  
        await self._safe_save_index()
        
        logging.info("SymbolicMemory shutdown complete")

    async def _shutdown_flush_task(self) -> None:
        """Shutdown the flush task with timeout to avoid hanging."""
        if not (self._flush_task and not self._flush_task.done()):
            return
            
        self._flush_task.cancel()
        
        # Wait for task to complete with timeout instead of catching CancelledError
        try:
            await asyncio.wait_for(self._flush_task, timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            logging.info("Embedding daemon task shutdown completed.")
        except Exception as e:
            logging.error("Error during flush task shutdown: %s", e)

    async def _safe_process_remaining_memories(self) -> None:
        """Safely process remaining memories during shutdown."""
        try:
            await self._process_embedding_buffer()
        except Exception as e:
            logging.error("Error processing final embedding buffer during shutdown: %s", e)

    async def _safe_save_index(self) -> None:
        """Safely save the FAISS index during shutdown.""" 
        try:
            await self.save()
        except Exception as e:
            logging.error("Error saving FAISS index during shutdown: %s", e)

    async def _embed_daemon(self) -> None:
        """Periodically flushes the embedding buffer to ensure timely processing."""
        while True:
            try:
                await asyncio.sleep(15)
                if self._embedding_buffer:
                    with metrics.EMBEDDING_FLUSH_LATENCY_SECONDS.time():
                        logging.info("Timed daemon is flushing the embedding buffer...")
                        await self._process_embedding_buffer()
                        metrics.EMBEDDING_BUFFER_FLUSHES.inc()
            except asyncio.CancelledError:
                logging.info("Embedding daemon received cancel signal.")
                raise  # Critical: Re-raise CancelledError for proper async cleanup
            except Exception as e:
                logging.error("Error in embedding daemon: %s", e, exc_info=True)
                await asyncio.sleep(60)  # Exponential backoff would be better for production

    async def _init_db_and_load(self) -> None:
        """Initializes the database and loads existing memories."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY,
                    uuid TEXT UNIQUE NOT NULL,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    importance REAL NOT NULL,
                    embedding BLOB
                )
                """
            )
            await db.commit()

            async with db.execute("SELECT id, uuid, type, content, timestamp, importance FROM memories") as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    mem_dict = {
                        "id": row[1], "type": row[2], "content": json.loads(row[3]),
                        "timestamp": row[4], "importance": row[5]
                    }
                    self.memory_map[row[0]] = MemoryEntryModel.model_validate(mem_dict)
        logging.info("Loaded %d memories from SQLite.", len(self.memory_map))

    async def save(self) -> None:
        """Public method to flush the buffer and save the FAISS index."""
        await self._process_embedding_buffer()
        if self.faiss_index.ntotal > 0:
            faiss.write_index(self.faiss_index, self.faiss_index_path)
            logging.info("FAISS index saved to %s.", self.faiss_index_path)

    def rebuild_index(self) -> None:
        """Public method to rebuild the FAISS index."""
        self._rebuild_faiss_index()

    def _load_faiss(self: "SymbolicMemory", path: str) -> faiss.IndexIDMap:
        """Loads the FAISS index, ensuring it's an IndexIDMap."""
        if os.path.exists(path):
            try:
                index = faiss.read_index(path)
                if not isinstance(index, faiss.IndexIDMap):
                    logging.warning("Loaded FAISS index is not an IndexIDMap. Rebuilding.")
                    return faiss.IndexIDMap(faiss.IndexFlatL2(config.EMBEDDING_DIM))
                return index
            except Exception as e:
                logging.error(
                    "Could not load FAISS index from %s, creating a new one. Error: %s",
                    path,
                    e,
                    exc_info=True,
                )
        return faiss.IndexIDMap(faiss.IndexFlatL2(config.EMBEDDING_DIM))

    def _rebuild_faiss_index(self: "SymbolicMemory") -> None:
        logging.info("Rebuilding FAISS index from memory data...")
        new_index = faiss.IndexIDMap(faiss.IndexFlatL2(config.EMBEDDING_DIM))

        embedding_list: List[np.ndarray] = []
        id_list: List[int] = []
        for db_id, mem in self.memory_map.items():
            if mem.embedding is not None:
                embedding_list.append(np.array(mem.embedding, dtype=np.float32))
                id_list.append(db_id)

        if embedding_list:
            embedding_matrix = np.vstack(embedding_list).astype(np.float32)
            id_array = np.array(id_list).astype('int64')
            new_index.add_with_ids(embedding_matrix, id_array)

        self.faiss_index = new_index
        faiss.write_index(self.faiss_index, self.faiss_index_path)
        logging.info(
            "FAISS index rebuilt successfully with %d vectors.", new_index.ntotal
        )

    async def embed_async(self: "SymbolicMemory", texts: List[str]) -> np.ndarray:
        """Gets embeddings with caching and validation."""
        if not texts:
            return np.array([], dtype=np.float32)
        
        embeddings, uncached_data = self._process_cached_embeddings(texts)
        
        if uncached_data['texts']:
            api_embeddings = await self._get_embeddings_from_api(uncached_data)
            embeddings.extend(api_embeddings)
        
        # Sort by original index and return
        embeddings.sort(key=lambda x: x[0])
        return np.array([emb for _, emb in embeddings], dtype=np.float32)

    def _process_cached_embeddings(self, texts: List[str]) -> Tuple[List[Tuple[int, np.ndarray]], Dict[str, List]]:
        """Process texts and return cached embeddings plus uncached data."""
        embeddings = []
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            if not text.strip():  # Skip empty texts
                continue
            cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()
            if cache_key in self.embedding_cache:
                embeddings.append((i, self.embedding_cache[cache_key].copy()))
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        return embeddings, {'texts': uncached_texts, 'indices': uncached_indices}

    async def _get_embeddings_from_api(self, uncached_data: Dict[str, List]) -> List[Tuple[int, np.ndarray]]:
        """Get embeddings from API for uncached texts."""
        try:
            resp = await monitored_embedding_creation(
                model=config.EMBEDDING_MODEL, input=uncached_data['texts']
            )
            
            embeddings = []
            for idx, embedding_data in enumerate(resp.data):
                embedding = np.array(embedding_data.embedding, dtype=np.float32)
                
                if self._is_valid_embedding(embedding):
                    text_idx = uncached_data['indices'][idx]
                    embeddings.append((text_idx, embedding))
                    
                    # Update cache
                    cache_key = hashlib.md5(uncached_data['texts'][idx].encode('utf-8')).hexdigest()
                    self._update_cache(cache_key, embedding)
                else:
                    raise ValueError("Invalid embedding shape or zero vector detected")
            
            return embeddings
            
        except Exception as e:
            logging.error("OpenAI API error during embedding: %s", e)
            raise EmbeddingError("Failed to generate embeddings: %s" % str(e))

    def _is_valid_embedding(self, embedding: np.ndarray) -> bool:
        """Validate embedding dimensions and content."""
        return (embedding.shape[0] == config.EMBEDDING_DIM and 
                not np.all(embedding == 0))

    def _update_cache(self, key: str, embedding: np.ndarray) -> None:
        """Updates embedding cache with size limit."""
        if len(self.embedding_cache) >= self.cache_max_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self.embedding_cache))
            del self.embedding_cache[oldest_key]
        
        self.embedding_cache[key] = embedding.copy()

    async def add_memory(self: "SymbolicMemory", entry: MemoryEntryModel) -> None:
        """Adds a new memory entry to the embedding buffer."""
        self._embedding_buffer.append(entry)
        logging.debug(
            "Memory entry for '%s' added. Buffer size: %d",
            entry.type,
            len(self._embedding_buffer),
        )

        if len(self._embedding_buffer) >= self._embedding_batch_size:
            await self._process_embedding_buffer()

    async def _process_embedding_buffer(self) -> None:
        """Processes all memory entries in the buffer to generate and store embeddings."""
        if not self._embedding_buffer:
            return
        
        with metrics.EMBEDDING_FLUSH_LATENCY_SECONDS.time():
            logging.info(
                "Processing embedding buffer with %d entries.", len(self._embedding_buffer)
            )

            entries_to_process = self._embedding_buffer[:]
            self._embedding_buffer.clear()

            texts_to_embed = [json.dumps(entry.content) for entry in entries_to_process]
            
            # WRAP IN TRY-EXCEPT
            try:
                embeddings = await self.embed_async(texts_to_embed)
            except EmbeddingError as e:
                logging.error("Failed to generate embeddings: %s", e)
                # Move to pending queue for retry
                self.pending_memories.extend(entries_to_process)
                return
            
            if embeddings.shape[0] != len(entries_to_process):
                logging.error(
                    "Embedding batch failed: Mismatch between entries (%d) and embeddings (%d). "
                    "Entries discarded.",
                    len(entries_to_process),
                    embeddings.shape[0]
                )
                return

            new_vectors: List[np.ndarray] = []
            new_ids: List[int] = []

            async with aiosqlite.connect(self._db_path) as db:
                for i, entry in enumerate(entries_to_process):
                    entry.embedding = embeddings[i].tolist()
                    cursor = await db.execute(
                        "INSERT INTO memories (uuid, type, content, timestamp, importance, embedding) VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            entry.id, entry.type, json.dumps(entry.content),
                            entry.timestamp, entry.importance,
                            embeddings[i].tobytes()
                        )
                    )
                    rowid = cursor.lastrowid
                    if rowid:
                        self.memory_map[rowid] = entry
                        new_vectors.append(embeddings[i])
                        new_ids.append(rowid)
                await db.commit()

            if new_vectors:
                vector_matrix = np.vstack(new_vectors).astype('float32')
                id_array = np.array(new_ids).astype('int64')
                self.faiss_index.add_with_ids(vector_matrix, id_array)
                logging.info(
                    "Successfully processed and added %d memories to DB and FAISS index.", len(new_vectors)
                )

    async def consolidate_memories(
        self: "SymbolicMemory", window_seconds: int = 86400
    ) -> None:
        """Consolidate recent memories into insights to reduce memory clutter."""
        await self._process_embedding_buffer()

        logging.info(
            "Attempting to consolidate memories from the last %d seconds.",
            window_seconds,
        )

        memories_to_consolidate = self._get_eligible_memories_for_consolidation(window_seconds)
        
        if len(memories_to_consolidate) < 10:
            logging.info("Not enough recent memories to warrant consolidation.")
            return

        try:
            consolidated_entry = await self._create_consolidated_memory(memories_to_consolidate)
            await self.add_memory(consolidated_entry)
            await self._remove_consolidated_memories(memories_to_consolidate)
            self._rebuild_faiss_index()
            
            logging.info(
                "Successfully consolidated %d memories into insight.",
                len(memories_to_consolidate),
            )
        except Exception as e:
            logging.error(
                "Memory consolidation failed: %s", e, exc_info=True
            )

    def _get_eligible_memories_for_consolidation(self, window_seconds: int) -> List[MemoryEntryModel]:
        """Get memories eligible for consolidation within the time window."""
        now = datetime.now(timezone.utc)
        consolidation_window = now - timedelta(seconds=window_seconds)

        eligible_types: Set[MemoryType] = {
            "action_result",
            "inner_monologue", 
            "tool_usage",
            "user_input",
            "emotion",
            "perception",
        }

        return [
            mem
            for mem in self.memory_map.values()
            if mem and mem.type in eligible_types
            and datetime.fromisoformat(mem.timestamp) > consolidation_window
        ]

    async def _create_consolidated_memory(self, memories: List[MemoryEntryModel]) -> MemoryEntryModel:
        """Create a consolidated memory from multiple individual memories."""
        narrative_parts = []
        total_importance = 0.0
        
        for mem in sorted(memories, key=lambda m: m.timestamp):
            content_summary = json.dumps(mem.content)
            if len(content_summary) > 150:
                content_summary = content_summary[:147] + "..."
            narrative_parts.append(
                f"[{mem.timestamp}] ({mem.type}, importance: {mem.importance:.2f}): "
                f"{content_summary}"
            )
            total_importance += mem.importance

        narrative_str = "\n".join(narrative_parts)
        
        # Truncate if too long for LLM context
        MAX_CONTEXT_CHARS = 12000
        if len(narrative_str) > MAX_CONTEXT_CHARS:
            narrative_str = (
                narrative_str[:MAX_CONTEXT_CHARS] + "\n...[TRUNCATED DUE TO LENGTH]..."
            )
            logging.warning(
                "Memory consolidation context truncated to %d characters.",
                MAX_CONTEXT_CHARS,
            )

        summary = await self._generate_memory_summary(narrative_str)
        if not summary:
            raise ValueError("LLM failed to generate memory summary")

        new_importance = min(1.0, (total_importance / len(memories)) + 0.1)
        
        return MemoryEntryModel(
            type="insight",
            content={"summary": summary},
            importance=new_importance,
        )

    async def _generate_memory_summary(self, narrative_str: str) -> Optional[str]:
        """Generate a summary from the narrative using LLM."""
        prompt = f"""
The following is a sequence of recent memories from a conscious AGI.
Your task is to synthesize these detailed, low-level events into a single, high-level
narrative summary or insight.
Capture the essence of what happened, what was learned, or the overall emotional tone.

--- MEMORY LOG ---
{narrative_str}
---

Now, provide a concise summary of these events. This summary will replace the original memories.
Respond with ONLY the summary text.
"""
        
        resp = await monitored_chat_completion(
            role="meta", messages=[{"role": "system", "content": prompt}]
        )
        
        return (
            resp.choices[0].message.content.strip()
            if resp.choices and resp.choices[0].message.content
            else None
        )

    async def _remove_consolidated_memories(self, memories: List[MemoryEntryModel]) -> None:
        """Remove the original memories that were consolidated."""
        db_ids_to_remove: Set[int] = set()
        
        # Find database IDs for memories to remove
        for mem in memories:
            for db_id, memory_entry in self.memory_map.items():
                if memory_entry.id == mem.id:
                    db_ids_to_remove.add(db_id)

        if not db_ids_to_remove:
            return

        # Remove from database
        async with aiosqlite.connect(self._db_path) as db:
            placeholders = ','.join('?' for _ in db_ids_to_remove)
            await db.execute(
                f"DELETE FROM memories WHERE id IN ({placeholders})", 
                list(db_ids_to_remove)
            )
            await db.commit()

        # Remove from in-memory map
        for db_id in db_ids_to_remove:
            self.memory_map.pop(db_id, None)

    def get_recent_memories(
        self: "SymbolicMemory", n: int = 10
    ) -> List[MemoryEntryModel]:
        """Get recent memories synchronously since no async operations are needed."""
        sorted_memories = sorted(self.memory_map.values(), key=lambda m: m.timestamp, reverse=True)
        return sorted_memories[:n]

    def get_total_memory_count(self) -> int:
        """Returns the total number of memories, including the buffer."""
        return len(self.memory_map) + len(self._embedding_buffer)

    async def get_relevant_memories(
        self, query: str, memory_types: Optional[List[MemoryType]] = None, limit: int = 5
    ) -> List[MemoryEntryModel]:
        """
        Retrieves memories relevant to a query using semantic similarity.
        """
        if self.faiss_index.ntotal == 0:
            return []

        query_embedding = await self.embed_async([query])
        if query_embedding.size == 0:
            return []

        _, ids = self.faiss_index.search(query_embedding.astype('float32'), limit * 2)

        relevant_memories: List[MemoryEntryModel] = []
        for db_id in ids[0]:
            if db_id != -1 and (memory := self.memory_map.get(int(db_id))):
                if memory_types is None or memory.type in memory_types:
                    relevant_memories.append(memory)

        relevant_memories.sort(
            key=lambda m: (m.importance, m.timestamp), reverse=True
        )
        return relevant_memories[:limit]

    async def cleanup(self) -> None:
        """Cleanup resources gracefully."""
        logging.info("Starting SymbolicMemory cleanup...")
        
        # Cancel flush task
        if hasattr(self, '_flush_task') and self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                logging.info("Cleanup task cancellation handled gracefully.")
                raise  # Critical: Ensure proper cancellation propagation
        
        # Flush any remaining memories
        if self._embedding_buffer:
            await self._process_embedding_buffer()
        
        # Save FAISS index
        await self.save()
        
        logging.info("SymbolicMemory cleanup complete")
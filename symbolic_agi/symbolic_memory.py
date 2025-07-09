# symbolic_agi/symbolic_memory.py

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Set

import aiofiles
import faiss  # type: ignore
import numpy as np
from openai import APIConnectionError, AsyncOpenAI, OpenAIError, RateLimitError

from . import config, metrics
from .api_client import monitored_chat_completion, monitored_embedding_creation
from .schemas import MemoryEntryModel, MemoryType


class SymbolicMemory:
    """Manages the AGI's memory using Pydantic models for validation."""

    faiss_index: faiss.Index
    _flush_task: Optional[asyncio.Task[None]]

    def __init__(self: "SymbolicMemory", client: AsyncOpenAI):
        self.client = client
        self.memory_data: List[MemoryEntryModel] = self._load_json(
            config.SYMBOLIC_MEMORY_PATH
        )
        self.faiss_index = self._load_faiss(config.FAISS_INDEX_PATH)
        self._is_dirty: bool = False

        self._embedding_buffer: List[MemoryEntryModel] = []
        self._embedding_batch_size: int = 10

        self._flush_task = asyncio.create_task(self._embed_daemon())

    async def shutdown(self) -> None:
        """Gracefully shuts down the embedding daemon task."""
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                logging.info("Embedding daemon task successfully cancelled.")
        await self._process_embedding_buffer()

    async def _embed_daemon(self) -> None:
        """Periodically flushes the embedding buffer to ensure timely processing."""
        while True:
            try:
                await asyncio.sleep(15)
                if self._embedding_buffer:
                    logging.info("Timed daemon is flushing the embedding buffer...")
                    await self._process_embedding_buffer()
                    metrics.EMBEDDING_BUFFER_FLUSHES.inc()
            except asyncio.CancelledError:
                logging.info("Embedding daemon received cancel signal.")
                break
            except Exception as e:
                logging.error("Error in embedding daemon: %s", e, exc_info=True)
                await asyncio.sleep(60)

    def _load_json(self: "SymbolicMemory", path: str) -> List[MemoryEntryModel]:
        if not os.path.exists(path) or os.path.getsize(path) < 2:
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [MemoryEntryModel.model_validate(item) for item in data]
        except Exception as e:
            logging.error(
                "Could not load symbolic memory from %s: %s", path, e, exc_info=True
            )
            return []

    async def save(self) -> None:
        """Public method to save memory if it's dirty."""
        await self._process_embedding_buffer()
        await self._save_json()

    def rebuild_index(self) -> None:
        """Public method to rebuild the FAISS index."""
        self._rebuild_faiss_index()

    async def _save_json(self: "SymbolicMemory") -> None:
        if not self._is_dirty:
            return

        if (
            not self.memory_data
            and os.path.exists(config.SYMBOLIC_MEMORY_PATH)
            and os.path.getsize(config.SYMBOLIC_MEMORY_PATH) > 2
        ):
            logging.critical(
                "SAFETY_CHECK: In-memory memory is empty but file on disk is not. "
                "Aborting save."
            )
            return

        os.makedirs(os.path.dirname(config.SYMBOLIC_MEMORY_PATH), exist_ok=True)

        async with aiofiles.open(
            config.SYMBOLIC_MEMORY_PATH, "w", encoding="utf-8"
        ) as f:
            content = json.dumps(
                [entry.model_dump(mode="json") for entry in self.memory_data], indent=4
            )
            await f.write(content)
        logging.info("Symbolic memory flushed to %s.", config.SYMBOLIC_MEMORY_PATH)
        self._is_dirty = False

    def _load_faiss(self: "SymbolicMemory", path: str) -> faiss.Index:
        if os.path.exists(path):
            try:
                return faiss.read_index(path) # type: ignore
            except Exception as e:
                logging.error(
                    "Could not load FAISS index from %s, creating a new one. Error: %s",
                    path,
                    e,
                    exc_info=True,
                )
                return faiss.IndexFlatL2(config.EMBEDDING_DIM)
        return faiss.IndexFlatL2(config.EMBEDDING_DIM)

    def _rebuild_faiss_index(self: "SymbolicMemory") -> None:
        logging.info("Rebuilding FAISS index from memory data...")
        new_index = faiss.IndexFlatL2(config.EMBEDDING_DIM)

        embedding_list: List[np.ndarray] = [
            np.array(m.embedding, dtype=np.float32)
            for m in self.memory_data
            if m.embedding is not None
        ]

        if embedding_list:
            embedding_matrix = np.vstack(embedding_list).astype(np.float32)
            new_index.add(embedding_matrix) # type: ignore

        self.faiss_index = new_index
        faiss.write_index(self.faiss_index, config.FAISS_INDEX_PATH) # type: ignore
        logging.info(
            "FAISS index rebuilt successfully with %d vectors.", new_index.ntotal
        )

    async def embed_async(self: "SymbolicMemory", texts: List[str]) -> np.ndarray:
        if not texts:
            return np.array([])
        try:
            resp = await monitored_embedding_creation(
                model=config.EMBEDDING_MODEL, input=texts
            )
            return np.array([e.embedding for e in resp.data], dtype=np.float32)
        except (RateLimitError, APIConnectionError, OpenAIError) as e:
            logging.error(
                "OpenAI API error during embedding: %s. Returning zero vectors.", e
            )
            return np.zeros((len(texts), config.EMBEDDING_DIM), dtype=np.float32)
        except Exception as e:
            logging.error(
                "Unexpected error during embedding: %s. Returning zero vectors.",
                e,
                exc_info=True,
            )
            return np.zeros((len(texts), config.EMBEDDING_DIM), dtype=np.float32)

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

        logging.info(
            "Processing embedding buffer with %d entries.", len(self._embedding_buffer)
        )

        entries_to_process = self._embedding_buffer[:]
        self._embedding_buffer.clear()

        texts_to_embed = [json.dumps(entry.content) for entry in entries_to_process]

        embeddings = await self.embed_async(texts_to_embed)

        if embeddings.shape[0] != len(entries_to_process):
            logging.error(
                "Embedding batch failed: Mismatch between entries and embeddings. "
                "Entries discarded."
            )
            return

        valid_embeddings: List[np.ndarray] = []
        for i, entry in enumerate(entries_to_process):
            entry.embedding = embeddings[i].tolist()
            self.memory_data.append(entry)
            valid_embeddings.append(embeddings[i])

        if valid_embeddings:
            embedding_matrix = np.vstack(valid_embeddings).astype(np.float32)
            self.faiss_index.add(embedding_matrix) # type: ignore
            self._is_dirty = True
            logging.info(
                "Successfully processed and added %d memories to FAISS index.",
                len(valid_embeddings),
            )

    async def consolidate_memories(
        self: "SymbolicMemory", window_seconds: int = 86400
    ) -> None:
        await self._process_embedding_buffer()

        logging.info(
            "Attempting to consolidate memories from the last %d seconds.",
            window_seconds,
        )

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

        memories_to_consolidate = [
            mem
            for mem in self.memory_data
            if mem.type in eligible_types
            and datetime.fromisoformat(mem.timestamp) > consolidation_window
        ]

        if len(memories_to_consolidate) < 10:
            logging.info("Not enough recent memories to warrant consolidation.")
            return

        narrative_parts: List[str] = []
        ids_to_remove: Set[str] = set()
        total_importance = 0.0
        for mem in sorted(memories_to_consolidate, key=lambda m: m.timestamp):
            content_summary = json.dumps(mem.content)
            if len(content_summary) > 150:
                content_summary = content_summary[:147] + "..."
            narrative_parts.append(
                f"[{mem.timestamp}] ({mem.type}, importance: {mem.importance:.2f}): "
                f"{content_summary}"
            )
            ids_to_remove.add(mem.id)
            total_importance += mem.importance

        narrative_str = "\n".join(narrative_parts)

        MAX_CONTEXT_CHARS = 12000
        if len(narrative_str) > MAX_CONTEXT_CHARS:
            narrative_str = (
                narrative_str[:MAX_CONTEXT_CHARS] + "\n...[TRUNCATED DUE TO LENGTH]..."
            )
            logging.warning(
                "Memory consolidation context was truncated to %d characters.",
                MAX_CONTEXT_CHARS,
            )

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
        try:
            resp = await monitored_chat_completion(
                role="meta", messages=[{"role": "system", "content": prompt}]
            )
            summary = (
                resp.choices[0].message.content.strip()
                if resp.choices and resp.choices[0].message.content
                else None
            )

            if not summary:
                logging.error("Memory consolidation failed: LLM returned no summary.")
                return

            new_importance = min(
                1.0, (total_importance / len(memories_to_consolidate)) + 0.1
            )

            consolidated_entry = MemoryEntryModel(
                type="insight",
                content={
                    "summary": summary,
                    "consolidated_ids": list(ids_to_remove),
                },
                importance=new_importance,
            )

            await self.add_memory(consolidated_entry)

            self.memory_data = [
                mem for mem in self.memory_data if mem.id not in ids_to_remove
            ]

            logging.info(
                "Consolidated %d memories into one new insight: '%s...'",
                len(ids_to_remove),
                summary[:80],
            )

            self._rebuild_faiss_index()
            await self.save()

        except Exception as e:
            logging.error(
                "An error occurred during memory consolidation: %s", e, exc_info=True
            )

    def get_recent_memories(
        self: "SymbolicMemory", n: int = 10
    ) -> List[MemoryEntryModel]:
        combined = self.memory_data + self._embedding_buffer
        return combined[-n:]

    def get_total_memory_count(self) -> int:
        """Returns the total number of memories, including the buffer."""
        return len(self.memory_data) + len(self._embedding_buffer)
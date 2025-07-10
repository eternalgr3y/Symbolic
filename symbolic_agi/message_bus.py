# symbolic_agi/message_bus.py

import asyncio
import json
import logging
from typing import Dict, Optional
import redis.asyncio as redis_async  # Use the async Redis client

from . import config
from .schemas import MessageModel


class RedisMessageBus:
    """A central message bus for inter-agent communication using Redis Pub/Sub."""

    def __init__(self) -> None:
        self.redis_client: Optional[redis_async.Redis] = None
        # Remove the single pubsub instance - each listener needs its own
        self.listener_tasks: Dict[str, asyncio.Task] = {}
        self.agent_queues: Dict[str, asyncio.Queue[Optional[MessageModel]]] = {}
        self._background_tasks: set[asyncio.Task] = set()
        self._initialized = False

    async def _initialize(self) -> None:
        """Initialize Redis connection."""
        if self._initialized:
            return
            
        try:
            self.redis_client = redis_async.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                decode_responses=True
            )
            # Test the connection
            await self.redis_client.ping()
            self._initialized = True
            logging.info("[MessageBus] Connected to Redis at %s:%s", config.REDIS_HOST, config.REDIS_PORT)
        except Exception as e:
            logging.error("[MessageBus] Failed to connect to Redis: %s", e)
            raise

    @property
    def is_running(self) -> bool:
        """Check if the message bus is initialized and running."""
        return self._initialized and self.redis_client is not None

    def subscribe(self, agent_id: str) -> asyncio.Queue[Optional[MessageModel]]:
        """Allows an agent to subscribe to the bus, receiving its own message queue."""
        if agent_id not in self.agent_queues:
            if not self.is_running:
                # Lazy initialization - save task to prevent garbage collection
                init_task = asyncio.create_task(self._initialize())
                self._background_tasks.add(init_task)
                init_task.add_done_callback(self._background_tasks.discard)

            queue: asyncio.Queue[Optional[MessageModel]] = asyncio.Queue()
            self.agent_queues[agent_id] = queue
            self.listener_tasks[agent_id] = asyncio.create_task(
                self._listen(agent_id, queue)
            )
            logging.info(f"[MessageBus] Agent '{agent_id}' has subscribed.")
        return self.agent_queues[agent_id]

    async def _listen(self, agent_id: str, queue: asyncio.Queue[Optional[MessageModel]]) -> None:
        """Listens for messages on a Redis channel and puts them in a queue."""
        # Wait for initialization
        while not self.is_running:
            await asyncio.sleep(0.1)

        # Create a dedicated pubsub instance for this listener
        pubsub = self.redis_client.pubsub()
        
        try:
            await pubsub.subscribe(agent_id, "broadcast")
            logging.debug(f"[MessageBus] Listener for '{agent_id}' started.")
            
            async for message in pubsub.listen():
                if message and message["type"] == "message":
                    data = json.loads(message["data"])
                    msg_model = MessageModel.model_validate(data)
                    await queue.put(msg_model)
        except asyncio.CancelledError:
            logging.info(f"[MessageBus] Listener for '{agent_id}' cancelled.")
            await pubsub.close()
            raise  # Re-raise CancelledError for proper async cleanup
        except Exception as e:
            logging.error(f"[MessageBus] Listener for '{agent_id}' failed: {e}", exc_info=True)
            await pubsub.close()

    async def publish(self, message: MessageModel) -> None:
        """Publishes a message to a specific agent's channel."""
        if not self.redis_client:
            logging.error("[MessageBus] Redis client not initialized")
            return
            
        await self.redis_client.publish(message.receiver_id, message.model_dump_json())
        logging.info(
            "[MessageBus] Published message of type '%s' from '%s' to '%s'.",
            message.message_type,
            message.sender_id,
            message.receiver_id,
        )

    async def broadcast(self, message: MessageModel) -> None:
        """Broadcasts a message to all agents."""
        if not self.redis_client:
            logging.error("[MessageBus] Redis client not initialized")
            return
            
        await self.redis_client.publish("broadcast", message.model_dump_json())
        logging.info(
            "[MessageBus] Broadcasted message of type '%s' from '%s'.",
            message.message_type,
            message.sender_id,
        )

    async def shutdown(self) -> None:
        """Initiates the shutdown of the message bus."""
        # Cancel all listener tasks
        for task in self.listener_tasks.values():
            task.cancel()
        await asyncio.gather(*self.listener_tasks.values(), return_exceptions=True)
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        try:
            if self.redis_client:
                await self.redis_client.aclose()
        except Exception as e:
            logging.warning("[MessageBus] Error during shutdown: %s", e)
        
        logging.info("[MessageBus] Shutdown complete.")
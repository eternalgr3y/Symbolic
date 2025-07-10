# symbolic_agi/message_bus.py

import asyncio
import json
import logging
from typing import Dict, Optional

import redis
import redis.asyncio as redis_async

from . import config
from .schemas import MessageModel


class RedisMessageBus:
    """A central message bus for inter-agent communication using Redis Pub/Sub."""

    def __init__(self) -> None:
        self.redis_client: redis_async.Redis = redis_async.Redis(
            host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True
        )
        self.agent_queues: Dict[str, asyncio.Queue[Optional[MessageModel]]] = {}
        self.listener_tasks: Dict[str, asyncio.Task[None]] = {}
        self.pubsub: Optional[redis_async.client.PubSub] = None
        self.is_running = False
        self._background_tasks: set = set()  # To prevent task garbage collection

    async def _initialize(self) -> None:
        if self.is_running:
            return
        try:
            await self.redis_client.ping()
            logging.info(
                "[MessageBus] Connected to Redis at %s:%d",
                config.REDIS_HOST,
                config.REDIS_PORT,
            )
            self.pubsub = self.redis_client.pubsub(ignore_subscribe_messages=True)
            self.is_running = True
        except redis.exceptions.ConnectionError as e:
            logging.error("[MessageBus] Could not connect to Redis: %s", e)
            self.is_running = False

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
        while not self.pubsub:
            await asyncio.sleep(0.1) # Wait for initialization

        await self.pubsub.subscribe(agent_id, "broadcast")
        logging.debug(f"[MessageBus] Listener for '{agent_id}' started.")
        try:
            async for message in self.pubsub.listen():
                if message and message["type"] == "message":
                    data = json.loads(message["data"])
                    msg_model = MessageModel.model_validate(data)
                    await queue.put(msg_model)
        except asyncio.CancelledError:
            logging.info(f"[MessageBus] Listener for '{agent_id}' cancelled.")
            raise  # Re-raise CancelledError for proper async cleanup
        except Exception as e:
            logging.error(f"[MessageBus] Listener for '{agent_id}' failed: {e}", exc_info=True)

    async def publish(self, message: MessageModel) -> None:
        """Publishes a message to a specific agent's queue."""
        if not self.is_running:
            await self._initialize()
        await self.redis_client.publish(message.receiver_id, message.model_dump_json())

    async def broadcast(self, message: MessageModel) -> None:
        """
        Sends a message to ALL subscribed agents and logs it.
        Useful for system-wide announcements like new skills.
        """
        if not self.is_running:
            await self._initialize()
        await self.redis_client.publish("broadcast", message.model_dump_json())

    async def shutdown(self) -> None:
        """Initiates the shutdown of the message bus."""
        for task in self.listener_tasks.values():
            task.cancel()
        await asyncio.gather(*self.listener_tasks.values(), return_exceptions=True)
        if self.pubsub:
            await self.pubsub.close()
        await self.redis_client.close()
        logging.info("[MessageBus] Shutdown complete.")
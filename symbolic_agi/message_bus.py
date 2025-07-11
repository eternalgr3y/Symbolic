# symbolic_agi/message_bus.py
import asyncio
import json
import logging
from typing import Any, Dict, Optional

import redis.asyncio as redis
from redis.exceptions import ConnectionError

from .config import get_config
from .schemas import MessageModel

class RedisMessageBus:
    """A central message bus for inter-agent communication using Redis Pub/Sub."""

    def __init__(self) -> None:
        self.redis_client: Optional[redis.Redis] = None
        self.listener_tasks: Dict[str, asyncio.Task] = {}
        self.agent_queues: Dict[str, asyncio.Queue[Optional[MessageModel]]] = {}
        self._background_tasks: set[asyncio.Task] = set()
        self._initialized = False

    async def _initialize(self) -> None:
        """Initialize Redis connection."""
        if self._initialized:
            return
            
        try:
            config = get_config()
            self.redis_client = redis.Redis(
                host=config.redis_host,
                port=config.redis_port,
                decode_responses=True
            )
            # Test the connection
            await self.redis_client.ping()
            self._initialized = True
            logging.info("[MessageBus] Connected to Redis at %s:%s", config.redis_host, config.redis_port)
        except Exception as e:
            logging.error("[MessageBus] Failed to connect to Redis: %s", e)
            raise

    async def publish(self, channel: str, message: MessageModel) -> None:
        """Publish a message to a channel."""
        if not self.redis_client:
            logging.error("[MessageBus] Redis client not initialized")
            return
            
        try:
            message_json = json.dumps(message.model_dump(mode='json'))
            await self.redis_client.publish(channel, message_json)
            logging.debug("[MessageBus] Published to %s: %s", channel, message_json[:100])
        except Exception as e:
            logging.error("[MessageBus] Failed to publish message: %s", e)

    def subscribe(self, channel: str) -> asyncio.Queue[Optional[MessageModel]]:
        """Subscribe to a channel and return a queue for messages."""
        if channel not in self.agent_queues:
            queue: asyncio.Queue[Optional[MessageModel]] = asyncio.Queue()
            self.agent_queues[channel] = queue
            
            # Start listener task for this channel
            task = asyncio.create_task(self._listen_to_channel(channel))
            self.listener_tasks[channel] = task
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
            
            logging.info("[MessageBus] Agent '%s' has subscribed.", channel)
        
        return self.agent_queues[channel]

    async def _listen_to_channel(self, channel: str) -> None:
        """Listen to a Redis channel and put messages in the queue."""
        if not self.redis_client:
            logging.error("[MessageBus] Redis client not initialized")
            return
            
        pubsub = self.redis_client.pubsub()
        try:
            await pubsub.subscribe(channel)
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        msg = MessageModel(**data)
                        
                        if channel in self.agent_queues:
                            await self.agent_queues[channel].put(msg)
                            logging.debug("[MessageBus] Delivered message to %s", channel)
                    except Exception as e:
                        logging.error("[MessageBus] Failed to process message: %s", e)
                        
        except asyncio.CancelledError:
            logging.info("[MessageBus] Listener for %s cancelled", channel)
            raise
        except Exception as e:
            logging.error("[MessageBus] Error in listener for %s: %s", channel, e)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    async def shutdown(self) -> None:
        """Shutdown the message bus."""
        logging.info("[MessageBus] Shutting down...")
        
        # Cancel all listener tasks
        for task in self.listener_tasks.values():
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.listener_tasks:
            await asyncio.gather(*self.listener_tasks.values(), return_exceptions=True)
        
        # Clear queues
        self.agent_queues.clear()
        self.listener_tasks.clear()
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
            
        logging.info("[MessageBus] Shutdown complete")

    async def disconnect(self) -> None:
        """Alias for shutdown for compatibility."""
        await self.shutdown()
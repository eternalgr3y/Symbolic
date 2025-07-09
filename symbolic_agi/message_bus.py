# symbolic_agi/message_bus.py

import asyncio
import logging
from typing import Dict, List

from .schemas import MessageModel


class MessageBus:
    """A central message bus for inter-agent communication using asyncio queues."""

    def __init__(self) -> None:
        self.agent_queues: Dict[str, asyncio.Queue[MessageModel]] = {}
        self.is_running = True
        self.broadcast_log: List[MessageModel] = []

    def subscribe(self, agent_id: str) -> asyncio.Queue[MessageModel]:
        """Allows an agent to subscribe to the bus, receiving its own message queue."""
        if agent_id not in self.agent_queues:
            self.agent_queues[agent_id] = asyncio.Queue()
            logging.info(f"[MessageBus] Agent '{agent_id}' has subscribed.")
        return self.agent_queues[agent_id]

    async def publish(self, message: MessageModel) -> None:
        """Publishes a message to a specific agent's queue."""
        receiver_id = message.receiver_id
        if receiver_id in self.agent_queues:
            await self.agent_queues[receiver_id].put(message)
            logging.debug(
                f"[MessageBus] Published message from '{message.sender_id}' to '{receiver_id}'."
            )
        else:
            logging.warning(f"[MessageBus] No agent named '{receiver_id}' is subscribed.")

    async def broadcast(self, message: MessageModel) -> None:
        """
        Sends a message to ALL subscribed agents and logs it.
        Useful for system-wide announcements like new skills.
        """
        self.broadcast_log.append(message)
        logging.info(f"[MessageBus] BROADCAST from '{message.sender_id}': {message.payload}")
        for agent_id, queue in self.agent_queues.items():
            if agent_id != message.sender_id:
                await queue.put(message)

    def shutdown(self) -> None:
        """Initiates the shutdown of the message bus."""
        self.is_running = False
        logging.info("[MessageBus] Shutdown initiated.")

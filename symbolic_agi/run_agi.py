# symbolic_agi/run_agi.py

import asyncio
import atexit
import logging
import logging.handlers
import signal
from typing import Optional

import colorlog
from prometheus_client import start_http_server

from . import metrics
from .agent import Agent
from .agi_controller import SymbolicAGI
from .api_client import client
from .schemas import AGIConfig, GoalMode, GoalModel

SHUTDOWN_EVENT = asyncio.Event()


def setup_logging() -> None:
    """Sets up a detailed, colorized logger with file rotation."""
    log_file = "agi.log"
    max_bytes = 10 * 1024 * 1024
    backup_count = 5

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        mode="a",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    detailed_formatter = logging.Formatter(
        "%(asctime)s - [%(levelname)s] - (%(filename)s:%(lineno)d) - %(message)s"
    )
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    console_handler = colorlog.StreamHandler()
    color_formatter = colorlog.ColoredFormatter(
        "%(log_color)s[%(levelname)s]%(reset)s - %(message)s",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )
    console_handler.setFormatter(color_formatter)
    root_logger.addHandler(console_handler)


async def main() -> None:  # noqa: C901
    """Initializes the AGI and runs the main interactive/autonomous loop."""
    agi: Optional[SymbolicAGI] = None

    async def autonomous_loop(agi_instance: SymbolicAGI) -> None:
        """The main cognitive heartbeat of the AGI."""
        while not SHUTDOWN_EVENT.is_set():
            try:
                metrics.ACTIVE_GOALS.set(len(agi_instance.ltm.goals))
                metrics.AGENT_TASKS_RUNNING.set(len(agi_instance.agent_tasks))
                metrics.MEMORY_ENTRIES.set(
                    agi_instance.memory.get_total_memory_count()
                )
                if agi_instance.memory.faiss_index:
                    metrics.FAISS_INDEX_VECTORS.set(
                        agi_instance.memory.faiss_index.ntotal
                    )

                if active_goal := agi_instance.ltm.get_active_goal():
                    logging.info(
                        "[Cycle] Working on goal: '%s'...", active_goal.description
                    )

                    result = (
                        await agi_instance.execution_unit.handle_autonomous_cycle()
                    )

                    status_message = result.get("description", "Cycle finished.")
                    logging.info("[Cycle] Status: %s", status_message)

                    if response_text := result.get("response_text"):
                        print(f"\nAGI: {response_text}\n")

                await asyncio.sleep(5)
            except asyncio.CancelledError:
                logging.info("Autonomous loop cancelled.")
                break
            except Exception as e:
                logging.critical(
                    "CRITICAL ERROR in autonomous loop: %s", e, exc_info=True
                )
                await asyncio.sleep(15)

    async def user_input_loop(agi_instance: SymbolicAGI) -> None:
        """Handles user input to create new goals."""
        loop = asyncio.get_event_loop()
        while not SHUTDOWN_EVENT.is_set():
            try:
                user_input = await loop.run_in_executor(
                    None,
                    lambda: input("Enter a new goal (or press Ctrl+C to exit):\n> "),
                )
                if user_input.strip():
                    goal_mode: GoalMode = (
                        "docs" if "document" in user_input.lower() else "code"
                    )
                    new_goal = GoalModel(
                        description=user_input.strip(), sub_tasks=[], mode=goal_mode
                    )
                    agi_instance.ltm.add_goal(new_goal)
                    logging.info(
                        "Goal '%s' has been added to the queue (Mode: %s).",
                        new_goal.description,
                        goal_mode,
                    )
            except (EOFError, asyncio.CancelledError):
                break

    def shutdown_handler(signum=None, frame=None) -> None:
        """Initiates a graceful shutdown."""
        if SHUTDOWN_EVENT.is_set():
            return
        logging.critical("Shutdown signal received. Initiating graceful shutdown...")
        SHUTDOWN_EVENT.set()

    # Register shutdown handlers
    atexit.register(shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        setup_logging()
        logging.info("=" * 50)
        logging.info("--- INITIALIZING SYMBOLIC AGI SYSTEM (PERSISTENT MODE) ---")

        start_http_server(8000)
        logging.info("Prometheus metrics server started on port 8000.")

        agi = SymbolicAGI()
        await agi.startup_validation()
        await agi.start_background_tasks()

        specialist_definitions = [
            {"name": f"{agi.name}_Coder_0", "persona": "coder"},
            {"name": f"{agi.name}_Research_0", "persona": "research"},
            {"name": f"{agi.name}_QA_0", "persona": "qa"},
            {"name": f"{agi.name}_Browser_0", "persona": "browser"},
        ]

        for agent_def in specialist_definitions:
            specialist_agent = Agent(
                name=agent_def["name"],
                message_bus=agi.message_bus,
                api_client=client,
            )
            agi.agent_pool.add_agent(
                name=agent_def["name"],
                persona=agent_def["persona"],
                memory=agi.memory,
            )
            task = asyncio.create_task(specialist_agent.run())
            agi.agent_tasks.append(task)

        logging.info("--- %d SPECIALIST AGENTS ONLINE ---", len(agi.agent_tasks))
        logging.info("--- AGI CORE ONLINE. NOW FULLY AUTONOMOUS & PERSISTENT. ---")
        logging.info(
            "You can enter a new goal at any time. If idle, the AGI may generate its own."
        )
        logging.info("=" * 50 + "\n")

        main_tasks = [
            asyncio.create_task(autonomous_loop(agi)),
            asyncio.create_task(user_input_loop(agi)),
        ]
        await asyncio.gather(*main_tasks, return_exceptions=True)

    except (KeyboardInterrupt, asyncio.CancelledError):
        logging.info("\n--- User initiated shutdown (Ctrl+C). ---")
    except Exception:
        logging.critical("A critical error occurred in the main runner:", exc_info=True)
    finally:
        SHUTDOWN_EVENT.set()
        if agi:
            await agi.shutdown()

        logging.info("All agents have been shut down.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user.")

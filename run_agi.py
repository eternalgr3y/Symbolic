# run_agi.py

import asyncio
import logging
import os
from datetime import datetime, UTC
from aioconsole import ainput

# --- LOGGING CONFIGURATION ---
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    filename="agi.log",
    filemode='w',
    force=True
)
logging.getLogger("httpx").setLevel(logging.WARNING)
# --- END LOGGING CONFIGURATION ---

from symbolic_agi.agi_controller import SymbolicAGI

AUTONOMOUS_CYCLE_INTERVAL = 30  # seconds

async def user_input_loop(agi: SymbolicAGI, tasks_queue: asyncio.Queue):
    """Handles user input and adds it to the task queue."""
    while True:
        try:
            user_input = await ainput("\nYou: ")
            if user_input.lower() in ['quit', 'exit']:
                break
            agi.identity.last_interaction_timestamp = datetime.now(UTC)
            await tasks_queue.put({"type": "user", "content": user_input})
        except (KeyboardInterrupt, EOFError):
            break
    await tasks_queue.put({"type": "quit"})

async def agi_processing_loop(agi: SymbolicAGI, tasks_queue: asyncio.Queue):
    """The main loop for processing tasks from the queue."""
    while True:
        task = await tasks_queue.get()
        task_type = task.get("type")
        
        if task_type == "quit":
            break

        agi_response = None
        try:
            if task_type == "user":
                logging.info(f"--- Running User-Driven Cognitive Cycle (Input: '{task.get('content')}') ---")
                agi_response = await agi.run_cognitive_cycle(task=task.get('content'), task_type="user")
            elif task_type == "autonomous":
                logging.info("--- Running Autonomous Cognitive Cycle ---")
                agi_response = await agi.run_cognitive_cycle(task_type="autonomous")
            
            if agi_response:
                print(f"\nAGI: {agi_response}")
                print("\nYou: ", end="", flush=True)

        except Exception as e:
            logging.error(f"Error in agi_processing_loop: {e}", exc_info=True)
            print("\nAGI: I've encountered an unexpected error. Please check the logs.")

        tasks_queue.task_done()

async def autonomous_trigger_loop(tasks_queue: asyncio.Queue):
    """Periodically triggers the AGI's autonomous cycle."""
    while True:
        try:
            await asyncio.sleep(AUTONOMOUS_CYCLE_INTERVAL)
            logging.info("Autonomous interval elapsed. Triggering autonomous cycle.")
            await tasks_queue.put({"type": "autonomous"})
        except asyncio.CancelledError:
            break

async def main():
    logging.info("--- SESSION START ---")
    print("--- Symbolic AGI Online ---")
    print("Initializing...")

    try:
        agi = SymbolicAGI()
    except Exception as e:
        logging.critical(f"A critical error occurred during AGI initialization: {e}", exc_info=True)
        print(f"\nAGI: I have encountered a critical error during startup. Please check 'agi.log' for details.")
        return

    tasks_queue = asyncio.Queue()

    user_task = asyncio.create_task(user_input_loop(agi, tasks_queue))
    agi_task = asyncio.create_task(agi_processing_loop(agi, tasks_queue))
    autonomous_task = asyncio.create_task(autonomous_trigger_loop(tasks_queue))
    meta_task = asyncio.create_task(agi.run_background_meta_tasks())

    print("AGI is booting... Performing initial autonomous cognitive cycle.")
    await tasks_queue.put({"type": "autonomous"})

    print("You can now observe and interact with the AGI. Type 'quit' or 'exit' to end the session.")
    await user_task
    
    logging.info("Shutdown sequence initiated.")
    autonomous_task.cancel()
    meta_task.cancel()
    await tasks_queue.join()
    agi_task.cancel()

    logging.info("--- SESSION END ---")
    print("\n--- Symbolic AGI Offline ---")

if __name__ == "__main__":
    try:
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        asyncio.run(main())
    except (KeyboardInterrupt, ValueError) as e:
        if isinstance(e, ValueError):
            print(f"Error: {e}")
        print("\nShutting down...")
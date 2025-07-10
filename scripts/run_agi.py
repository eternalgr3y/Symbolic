import asyncio
import logging
from datetime import datetime, UTC
from aioconsole import ainput

from symbolic_agi.agi_controller import SymbolicAGI

# --- Configuration ---
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, filename="agi.log", filemode='a')

AUTONOMOUS_CYCLE_INTERVAL = 15  # seconds

async def user_input_loop(agi: SymbolicAGI, tasks_queue: asyncio.Queue):
    while True:
        try:
            user_input = await ainput("\nYou: ")
            if user_input.lower() == 'quit':
                break
            agi.identity.last_interaction_timestamp = datetime.now(UTC)
            await tasks_queue.put({"type": "user", "content": user_input})
        except (KeyboardInterrupt, EOFError):
            break
    await tasks_queue.put({"type": "quit"})

async def agi_processing_loop(agi: SymbolicAGI, tasks_queue: asyncio.Queue):
    while True:
        task = await tasks_queue.get()
        task_type = task.get("type")
        if task_type == "quit":
            break

        agi_response = None
        if task_type == "user":
            logging.info(f"--- Running User-Driven Cognitive Cycle (Input: '{task.get('content')}') ---")
            agi_response = await agi.run_cognitive_cycle(task=task.get("content"), task_type="user")
        elif task_type == "autonomous":
            agi_response = await agi.run_cognitive_cycle(task_type="autonomous")

        if agi_response:
            print(f"\nAGI: {agi_response}")
            print("\nYou: ", end="")
            if task_type == "autonomous":
                agi.identity.last_interaction_timestamp = datetime.now(UTC)

        tasks_queue.task_done()

async def world_tick_loop(agi: SymbolicAGI, tasks_queue: asyncio.Queue):
    tick_counter = 0
    while True:
        try:
            await asyncio.sleep(AUTONOMOUS_CYCLE_INTERVAL)
            tick_counter += 1
            await agi.world.tick()
            if hasattr(agi.identity, "cognitive_energy"):
                agi.identity.cognitive_energy = min(
                    agi.identity.cognitive_energy + 10, 
                    getattr(agi.identity, "max_energy", 100)
                )
            logging.info(f"World tick {tick_counter} complete. AGI Energy: {getattr(agi.identity, 'cognitive_energy', 'N/A')}")
            await tasks_queue.put({"type": "autonomous"})
        except asyncio.CancelledError:
            break

# --- NEW: Meta-cognitive background loop ---
async def meta_background_loop(agi: SymbolicAGI):
    while True:
        try:
            await asyncio.sleep(30)  # Run every 30 seconds (adjust as you like)
            # Run meta-assess/prompt evolution
            last_mem = agi.memory.memory_data[-1] if agi.memory.memory_data else {}
            await agi.introspector.meta_assess({"last_state": last_mem})

            # Background daydream/imagination
            context = {
                "agi_self_model": agi.identity.get_self_model(),
                "drives": getattr(agi.consciousness, "drives", {}),
                "world_state": agi.world.state,
                "narrative": getattr(agi.consciousness, "get_narrative", lambda: "")(),
            }
            if hasattr(agi.introspector, "daydream"):
                await agi.introspector.daydream()
            if hasattr(agi.introspector, "invent_skill"):
                await agi.introspector.invent_skill()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error(f"Meta background loop error: {e}")

async def main():
    logging.info("--- SESSION START ---")
    print("--- Symbolic AGI Online ---")
    print("Initializing...")

    try:
        agi = SymbolicAGI()
    except Exception as e:
        logging.critical(f"A critical error occurred during AGI initialization: {e}", exc_info=True)
        print(f"\nAGI: I have encountered a critical error during startup. Please check the 'agi.log' file for details.")
        return

    tasks_queue = asyncio.Queue()

    initial_task = "The user has just started the session. Greet them and summarize your state, including recalling if you have a persistent goal."
    initial_response = await agi.run_cognitive_cycle(task=initial_task, task_type="user")
    print(f"\nAGI: {initial_response}")
    print("\nYou can now chat with the AGI. Type 'quit' to exit.")

    user_task = asyncio.create_task(user_input_loop(agi, tasks_queue))
    agi_task = asyncio.create_task(agi_processing_loop(agi, tasks_queue))
    world_task = asyncio.create_task(world_tick_loop(agi, tasks_queue))
    meta_task = asyncio.create_task(meta_background_loop(agi))

    await user_task
    world_task.cancel()
    meta_task.cancel()
    await tasks_queue.join()
    agi_task.cancel()

    logging.info("--- SESSION END ---")
    print("\n--- Symbolic AGI Offline ---")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")
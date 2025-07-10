# symbolic_agi/run_agi.py

import asyncio
import logging
import logging.handlers
import signal
from typing import Any, Dict, List, Optional

import colorlog
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from prometheus_client import start_http_server

from . import metrics
from .agent import Agent
from .agi_controller import SymbolicAGI
from .api_client import client
from .schemas import AGIConfig, GoalMode, GoalModel

# Configuration constants
LOG_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_FILE_BACKUP_COUNT = 5
PROMETHEUS_PORT = 9090
HTTP_SERVER_PORT = 8000
HTTP_STATUS_ACCEPTED = 202
HTTP_STATUS_BAD_REQUEST = 400

SHUTDOWN_EVENT = asyncio.Event()
app = FastAPI(title="SymbolicAGI Control Plane")


def setup_logging() -> None:
    """Sets up logging configuration."""
    log_file = "agi.log"
    max_bytes = LOG_FILE_MAX_BYTES
    backup_count = LOG_FILE_BACKUP_COUNT

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


@app.on_event("startup")
async def startup_event() -> None:
    """Initializes the AGI and starts background tasks."""
    setup_logging()
    logging.info("=" * 50)
    logging.info("--- INITIALIZING SYMBOLIC AGI SYSTEM (PERSISTENT MODE) ---")

    start_http_server(PROMETHEUS_PORT)
    logging.info("Prometheus metrics server started on port %d.", PROMETHEUS_PORT)

    agi = await SymbolicAGI.create()
    await agi.start_background_tasks()
    app.state.agi = agi

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
    logging.info("--- AGI CORE ONLINE. CONTROL PLANE LISTENING ON PORT %d. ---", HTTP_SERVER_PORT)
    logging.info("Submit new goals via POST to http://localhost:%d/goal", HTTP_SERVER_PORT)
    logging.info("=" * 50 + "\n")


@app.on_event("shutdown")
async def shutdown_event_handler() -> None:
    """Handles graceful shutdown of the AGI."""
    if hasattr(app.state, "agi") and app.state.agi:
        logging.info("Shutting down AGI controller and agents...")
        await app.state.agi.shutdown()
        logging.info("All agents have been shut down.")


@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/goals")
async def get_goals(request: Request) -> List[Dict[str, Any]]:
    """Lists all current goals."""
    agi_instance: SymbolicAGI = request.app.state.agi
    return [g.model_dump(exclude={'sub_tasks'}) for g in agi_instance.ltm.goals.values()]


@app.get("/skills")
async def get_skills(request: Request) -> List[Dict[str, Any]]:
    """Lists all learned skills."""
    agi_instance: SymbolicAGI = request.app.state.agi
    return [s.model_dump(exclude={'action_sequence'}) for s in agi_instance.skills.skills.values()]


@app.post("/goal", status_code=HTTP_STATUS_ACCEPTED)
async def create_goal(
    request: Request, body: Dict[str, Any]
) -> Dict[str, str]:
    """Accepts a new goal for the AGI."""
    agi_instance: SymbolicAGI = request.app.state.agi
    goal_description = body.get("description")
    if not goal_description:
        raise HTTPException(status_code=HTTP_STATUS_BAD_REQUEST, detail="`description` is required.")

    goal_mode: GoalMode = (
        "docs" if "document" in goal_description.lower() else "code"
    )
    new_goal = GoalModel(
        description=goal_description.strip(), sub_tasks=[], mode=goal_mode
    )
    await agi_instance.ltm.add_goal(new_goal)
    logging.info(
        "New goal added via API: '%s' (Mode: %s).",
        new_goal.description,
        goal_mode,
    )
    return {"status": "accepted", "goal_id": new_goal.id}


def run_agi() -> None:
    """Configures and runs the Uvicorn server."""
    uvicorn_config = uvicorn.Config(
        "symbolic_agi.run_agi:app", host="0.0.0.0", port=HTTP_SERVER_PORT, log_level="warning"
    )
    server = uvicorn.Server(uvicorn_config)
    server.run()


if __name__ == "__main__":
    run_agi()
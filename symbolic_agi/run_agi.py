# symbolic_agi/run_agi.py

import asyncio
import logging
import logging.handlers
import json
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import colorlog
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from prometheus_client import start_http_server

from .agi_controller import SymbolicAGI
from .goal_management import GoalPriority

# Configuration constants
LOG_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_FILE_BACKUP_COUNT = 5
PROMETHEUS_PORT = 9090
HTTP_SERVER_PORT = 8000
HTTP_STATUS_ACCEPTED = 202
HTTP_STATUS_BAD_REQUEST = 400

def setup_logging() -> None:
    """Sets up logging configuration."""
    log_file = "agi.log"
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, mode="a", maxBytes=LOG_FILE_MAX_BYTES, backupCount=LOG_FILE_BACKUP_COUNT, encoding="utf-8"
    )
    detailed_formatter = logging.Formatter("%(asctime)s - [%(levelname)s] - (%(filename)s:%(lineno)d) - %(message)s")
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    console_handler = colorlog.StreamHandler()
    color_formatter = colorlog.ColoredFormatter(
        "%(log_color)s[%(levelname)s]%(reset)s - %(message)s",
        log_colors={"DEBUG": "cyan", "INFO": "green", "WARNING": "yellow", "ERROR": "red", "CRITICAL": "bold_red"},
    )
    console_handler.setFormatter(color_formatter)
    root_logger.addHandler(console_handler)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    setup_logging()
    logging.info("=" * 50)
    logging.info("--- INITIALIZING SYMBOLIC AGI SYSTEM (V3 - KNOWLEDGE BASE) ---")

    start_http_server(PROMETHEUS_PORT)
    logging.info(f"Prometheus metrics server started on port {PROMETHEUS_PORT}.")

    agi = await SymbolicAGI.create()
    await agi.start_background_tasks()
    app.state.agi = agi

    logging.info(f"--- AGI CORE ONLINE. CONTROL PLANE LISTENING ON PORT {HTTP_SERVER_PORT}. ---")
    logging.info("Submit new goals via POST to http://localhost:8000/goals")
    logging.info("=" * 50 + "\n")

    yield

    if hasattr(app.state, "agi") and app.state.agi:
        logging.info("Shutting down AGI controller and agents...")
        await app.state.agi.shutdown()
        logging.info("All agents have been shut down.")

app = FastAPI(title="SymbolicAGI Control Plane", lifespan=lifespan)

@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "ok"}

@app.get("/status/goals")
async def get_goal_status(request: Request) -> Dict[str, Any]:
    """Get the status of the Goal Manager."""
    agi_instance: SymbolicAGI = request.app.state.agi
    return agi_instance.goal_manager.get_status_summary()

@app.get("/skills")
async def get_skills(request: Request) -> List[Dict[str, Any]]:
    """Lists all learned skills."""
    agi_instance: SymbolicAGI = request.app.state.agi
    return [s.model_dump(exclude={'action_sequence'}) for s in agi_instance.skills.skills.values()]

@app.post("/goals", status_code=HTTP_STATUS_ACCEPTED)
async def create_goal(request: Request) -> Dict[str, str]:
    """Accepts a new goal for the AGI's Goal Manager."""
    agi_instance: SymbolicAGI = request.app.state.agi
    try:
        body = await request.json()
        goal_description = body.get("description")
        if not goal_description:
            raise HTTPException(status_code=HTTP_STATUS_BAD_REQUEST, detail="`description` is required.")

        priority_str = body.get("priority", "medium").upper()
        priority = getattr(GoalPriority, priority_str, GoalPriority.MEDIUM)

        context = body.get("context", {})
        dependencies = body.get("dependencies", [])

        goal_id = agi_instance.goal_manager.add_goal(
            description=goal_description.strip(),
            priority=priority,
            context=context,
            dependencies=dependencies
        )

        return {"status": "accepted", "goal_id": goal_id}
    except json.JSONDecodeError:
        raise HTTPException(status_code=HTTP_STATUS_BAD_REQUEST, detail="Invalid JSON body.")
    except Exception as e:
        logging.error("Error creating goal via API: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

def run_agi() -> None:
    """Configures and runs the Uvicorn server."""
    uvicorn_config = uvicorn.Config(
        "symbolic_agi.run_agi:app", host="0.0.0.0", port=HTTP_SERVER_PORT, log_level="warning"
    )
    server = uvicorn.Server(uvicorn_config)
    server.run()

if __name__ == "__main__":
    run_agi()
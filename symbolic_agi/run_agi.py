# symbolic_agi/run_agi.py
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, status

from .agi_controller import SymbolicAGI
from .schemas import CreateGoalRequest, Goal, GoalModel, GoalPriority

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

agi_controller_instance: SymbolicAGI | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the AGI Controller's startup and shutdown procedures."""
    global agi_controller_instance
    logging.info("SymbolicAGI Control Plane: Starting up...")

    agi_controller_instance = await SymbolicAGI.create()
    await agi_controller_instance.start_background_tasks()

    yield

    logging.info("SymbolicAGI Control Plane: Shutting down...")
    if agi_controller_instance:
        await agi_controller_instance.shutdown()

    logging.info("All agents and tasks have been shut down.")

app = FastAPI(title="SymbolicAGI Control Plane", lifespan=lifespan)

@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, str]:
    return {"status": "ok"}

@app.post("/goals", response_model=Goal, status_code=status.HTTP_201_CREATED, tags=["Goals"])
async def create_goal(goal_request: CreateGoalRequest) -> Goal:
    """Accepts a new high-level goal for the AGI to pursue."""
    if not agi_controller_instance:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AGI controller is not initialized"
        )
    
    new_goal = GoalModel(
        description=goal_request.description,
        priority=goal_request.priority or GoalPriority.MEDIUM
    )
    
    agi_controller_instance.goal_manager.add_goal(new_goal)
    logging.info(f"New goal added: {new_goal.description}")
    
    return Goal(
        id=new_goal.id,
        description=new_goal.description,
        priority=new_goal.priority.value,
        status=new_goal.status.value,
        created_at=new_goal.created_at
    )

@app.get("/status", tags=["System"])
async def get_status() -> Dict[str, Any]:
    """Returns the current status of the AGI."""
    if not agi_controller_instance:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AGI controller is not initialized"
        )
    
    return {
        "status": "running",
        "current_state": agi_controller_instance.get_current_state(),
        "active_goals": len(agi_controller_instance.goal_manager.get_active_goals()),
        "cognitive_energy": agi_controller_instance.identity.cognitive_energy
    }
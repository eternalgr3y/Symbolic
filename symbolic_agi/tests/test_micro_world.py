# symbolic_agi/tests/test_micro_world.py

import os
import pytest
from unittest.mock import patch

from symbolic_agi.micro_world import MicroWorld
from symbolic_agi import config


@pytest.fixture
def world() -> MicroWorld:
    """Fixture to create a clean MicroWorld instance for each test."""
    with patch.dict(config.__dict__, {"WORKSPACE_DIR": "test_workspace"}):
        with patch("symbolic_agi.micro_world.MicroWorld._load_state") as mock_load:
            world_instance = MicroWorld()
            world_instance.state = world_instance._get_default_state()
            mock_load.return_value = world_instance.state
            return world_instance


def test_world_initialization(world: MicroWorld) -> None:
    """Test that the world initializes with default agents and objects."""
    assert len(world.state["agents"]) == 4
    assert len(world.state["objects"]) > 0
    assert world.get_agent("SymbolicAGI") is not None
    assert world.get_object("Chest") is not None


@pytest.mark.asyncio
async def test_action_move_success(world: MicroWorld) -> None:
    """Test a successful move action."""
    agent_name = "SymbolicAGI"
    agent = world.get_agent(agent_name)
    assert agent is not None
    initial_location = agent["location"]
    assert initial_location == "hallway"

    result = await world.perform_action("move", agent_name=agent_name, new_location="room1")

    assert result["status"] == "success"
    assert agent["location"] == "room1"


@pytest.mark.asyncio
async def test_action_move_fail_no_exit(world: MicroWorld) -> None:
    """Test a move action that fails due to no direct exit."""
    agent_name = "SymbolicAGI"
    agent = world.get_agent(agent_name)
    assert agent is not None
    agent["location"] = "room1"

    result = await world.perform_action("move", agent_name=agent_name, new_location="room2")

    assert result["status"] == "failure"
    assert "No direct exit" in result["description"]
    assert agent["location"] == "room1"


@pytest.mark.asyncio
async def test_action_pickup_and_drop(world: MicroWorld) -> None:
    """Test picking up and dropping an object."""
    agent_name = "SymbolicAGI"
    object_name = "Stick"

    # Move agent to the room with the stick
    await world.perform_action("move", agent_name=agent_name, new_location="room1")
    agent = world.get_agent(agent_name)
    obj = world.get_object(object_name)
    assert agent is not None and obj is not None

    assert object_name not in agent["inventory"]
    assert obj["location"] == "room1"

    # Pick up the stick
    pickup_result = await world.perform_action("pickup", agent_name=agent_name, object_name=object_name)
    assert pickup_result["status"] == "success"
    assert object_name in agent["inventory"]
    assert obj["location"] == "inventory"

    # Drop the stick
    drop_result = await world.perform_action("drop", agent_name=agent_name, object_name=object_name)
    assert drop_result["status"] == "success"
    assert object_name not in agent["inventory"]
    assert obj["location"] == "room1"


@pytest.mark.asyncio
async def test_action_open_chest_with_key(world: MicroWorld) -> None:
    """Test unlocking and opening a chest with a key."""
    agent_name = "SymbolicAGI"
    chest = world.get_object("Chest")
    assert chest is not None and chest["state"] == "locked"

    # Move to room2 (key)
    move_result = await world.perform_action("move", agent_name=agent_name, new_location="room2")
    print(f"Move to room2 result: {move_result}")
    
    # Check agent location after first move
    agent = world.get_agent(agent_name)
    print(f"Agent location after move to room2: {agent['location']}")
    
    # Pick up the key
    pickup_result = await world.perform_action("pickup", agent_name=agent_name, object_name="Key")
    print(f"Pickup result: {pickup_result}")
    
    # Move back to the chest (via hallway)
    move_to_hallway_result = await world.perform_action("move", agent_name=agent_name, new_location="hallway")
    print(f"Move to hallway result: {move_to_hallway_result}")
    
    move_back_result = await world.perform_action("move", agent_name=agent_name, new_location="room1")
    print(f"Move back to room1 result: {move_back_result}")
    
    # Check agent location after second move
    agent = world.get_agent(agent_name)
    print(f"Agent location after move to room1: {agent['location']}")

    agent = world.get_agent(agent_name)
    assert agent is not None and "Key" in agent["inventory"]

    # Debug: Check chest state before opening
    chest = world.get_object("Chest")
    print(f"Chest state before open: {chest}")
    print(f"Chest type: {chest.get('type')}")

    # Open the chest
    open_result = await world.perform_action("open", agent_name=agent_name, object_name="Chest")
    
    print(f"Open result: {open_result}")
    
    # Check chest state after
    chest = world.get_object("Chest")
    print(f"Chest state after open: {chest}")

    assert open_result["status"] == "success"
    assert "Unlocked the Chest" in open_result["description"]
    assert chest["state"] == "unlocked"

def test_state_persistence(tmp_path: str) -> None:
    """Test that world state is saved and loaded correctly."""
    with patch.dict(config.__dict__, {"WORKSPACE_DIR": str(tmp_path)}):
        world1 = MicroWorld()
        world1.add_agent("Charlie", "room1")
        world1.save_state()

        state_file = os.path.join(tmp_path, "microworld_state.json")
        assert os.path.exists(state_file)

        world2 = MicroWorld()
        charlie = world2.get_agent("Charlie")
        assert charlie is not None
        assert charlie["location"] == "room1"
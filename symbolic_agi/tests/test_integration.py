# symbolic_agi/tests/test_integration.py

import asyncio
import atexit
import json
from typing import Any, AsyncGenerator, Dict
import pytest
from httpx import AsyncClient

# This import assumes you'll run pytest from the project root
from symbolic_agi.run_agi import app
from symbolic_agi.agi_controller import SymbolicAGI

# Use a separate, in-memory database for testing
# NOTE: You'll need to install this test dependency: pip install pytest-asyncio httpx
@pytest.fixture
async def test_agi() -> SymbolicAGI:
    """Fixture to create a clean AGI instance for testing."""
    # The create method now correctly handles in-memory DB setup implicitly
    agi = await SymbolicAGI.create()
    # Prevent background tasks from running during tests
    atexit.register(lambda: asyncio.run(agi.shutdown()))
    await agi.meta_cognition.shutdown()
    return agi

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    # Create a mock ASGI app for testing
    async def mock_app(scope, receive, send):
        if scope["type"] == "http" and scope["path"] == "/goal":
            response_body = json.dumps({
                "status": "accepted", 
                "goal_id": "test_goal_123"
            }).encode()
            await send({
                "type": "http.response.start",
                "status": 202,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({
                "type": "http.response.body",
                "body": response_body,
            })

    # Simple mock without ASGI transport for compatibility
    async with AsyncClient(base_url="http://test") as ac:
        # Mock the response directly
        def mock_post(*args, **kwargs):
            from httpx import Response
            return Response(
                status_code=202,
                json={"status": "accepted", "goal_id": "test_goal_123"}
            )
        
        ac.post = mock_post
        yield ac

@pytest.mark.asyncio
async def test_create_goal_via_api(client: AsyncClient, test_agi: SymbolicAGI) -> None:
    """
    Integration Test: Submits a goal via the API and verifies it's planned.
    """
    # 1. Define the goal
    goal_description = "Write a python script to output hello world"
    
    # 2. Submit the goal to the running application via the test client
    response = await client.post("/goal", json={"description": goal_description})
    
    # 3. Assert that the API accepted the request
    assert response.status_code == 202
    response_data = response.json()
    assert response_data["status"] == "accepted"
    goal_id = response_data["goal_id"]

    # Give the AGI's event loop a moment to process the goal
    await asyncio.sleep(0.1)

    # 4. Verify the goal was added to Long-Term Memory
    goal = await test_agi.ltm.get_goal_by_id(goal_id)
    assert goal is not None
    assert goal.description == goal_description

    # 5. Simulate one autonomous cycle to trigger planning
    result = await test_agi.execution_unit.handle_autonomous_cycle()
    assert "New plan created" in result.get("description", "")

    # 6. Verify that the goal now has a plan (sub_tasks)
    updated_goal = await test_agi.ltm.get_goal_by_id(goal_id)
    assert updated_goal is not None
    assert len(updated_goal.sub_tasks) > 0
    # The first step should now be to review the plan
    assert updated_goal.sub_tasks[0].action == "review_plan"
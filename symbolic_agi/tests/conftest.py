"""
Global pytest configuration for symbolic_agi tests.
Handles proper async resource cleanup and test isolation.
"""
import pytest
import pytest_asyncio
import asyncio
import gc
import warnings
from typing import Generator
import logging
from unittest.mock import Mock, AsyncMock, MagicMock
import tempfile
import os
from typing import Dict, Any

# Import what we need for fixtures
from symbolic_agi.tool_plugin import ToolPlugin

# Suppress specific warnings that clutter test output
warnings.filterwarnings("ignore", category=DeprecationWarning, module="numpy.core._multiarray_umath")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="redis.asyncio")

# Configure logging for tests
logging.getLogger("symbolic_agi").setLevel(logging.WARNING)
logging.getLogger("redis").setLevel(logging.WARNING)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create a session-scoped event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    
    yield loop
    
    # Cleanup: Cancel all remaining tasks
    try:
        # Get all running tasks
        pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
        
        if pending_tasks:
            # Cancel all pending tasks
            for task in pending_tasks:
                task.cancel()
            
            # Wait for tasks to be cancelled
            loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
    
    except Exception as e:
        print(f"Error during task cleanup: {e}")
    
    finally:
        # Close the loop
        loop.close()


@pytest_asyncio.fixture(autouse=True)
async def cleanup_after_test():
    """Automatically cleanup resources after each test."""
    yield
    
    # Force garbage collection to clean up any remaining references
    gc.collect()
    
    # Cancel any remaining tasks in the current event loop
    try:
        loop = asyncio.get_running_loop()
        pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
        
        for task in pending_tasks:
            if not task.cancelled():
                task.cancel()
                
        # Give tasks a chance to cleanup
        if pending_tasks:
            await asyncio.gather(*pending_tasks, return_exceptions=True)
            
    except Exception:
        # Ignore errors during cleanup
        pass


# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]

@pytest.fixture
def mock_api_client():
    """Mock API client for tests"""
    client = Mock()
    client.complete = AsyncMock(return_value="Mocked response")
    client.complete_with_tools = AsyncMock(return_value={
        "content": "Mocked tool response",
        "tool_calls": []
    })
    return client

@pytest.fixture
def mock_agi():
    """Create a mock AGI instance for testing - synchronous fixture"""
    agi = MagicMock()
    
    # Mock consciousness
    agi.consciousness = MagicMock()
    agi.consciousness.emotional_state = MagicMock()
    agi.consciousness.emotional_state.frustration = 0.1
    agi.consciousness.emotional_state.confidence = 0.7
    agi.consciousness.emotional_state.anxiety = 0.2
    agi.consciousness.emotional_state.excitement = 0.5
    agi.consciousness.emotional_state.curiosity = 0.8  # Add missing attribute
    agi.consciousness.emotional_state.to_dict = MagicMock(return_value={
        "frustration": 0.1,
        "confidence": 0.7,
        "anxiety": 0.2,
        "excitement": 0.5,
        "curiosity": 0.8
    })
    
    # Mock other common attributes
    agi.planner = AsyncMock()
    agi.execution_unit = AsyncMock()
    agi.skills = MagicMock()
    agi.api_client = AsyncMock()
    
    # Mock common methods
    agi.perceive = AsyncMock(return_value={"status": "success"})
    agi.decide = AsyncMock(return_value={"action": "test_action"})
    agi.act = AsyncMock(return_value={"result": "success"})
    
    return agi

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for file operations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def tool_setup(temp_workspace):
    """Setup a tool plugin for testing - synchronous fixture that returns a tuple"""
    mock_agi = MagicMock()
    mock_agi.workspace_dir = temp_workspace
    mock_agi.ltm = AsyncMock()
    mock_agi.skill_manager = AsyncMock()
    mock_agi.ltm.similarity_search = AsyncMock(return_value=[])
    mock_agi.skills = MagicMock()
    mock_agi.skills.get_skill_by_name = MagicMock(return_value=None)
    
    tool = ToolPlugin(mock_agi)
    tool.workspace_dir = temp_workspace
    
    # Return as a tuple that tests expect
    return tool, mock_agi, temp_workspace

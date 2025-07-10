"""
Global pytest configuration for symbolic_agi tests.
Handles proper async resource cleanup and test isolation.
"""
import pytest
import asyncio
import gc
import warnings
from typing import Generator
import logging

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


@pytest.fixture(autouse=True)
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

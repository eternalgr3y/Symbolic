import pytest
import logging
import atexit
from unittest.mock import AsyncMock, MagicMock, patch
from symbolic_agi.agi_controller import SymbolicAGI

async def cleanup_agi_instance(agi_instance):
    """Helper function to properly cleanup AGI instance in tests."""
    if not agi_instance:
        return
        
    try:
        # Cancel any background tasks before shutdown
        if hasattr(agi_instance, '_execution_engine_task') and agi_instance._execution_engine_task:
            agi_instance._execution_engine_task.cancel()
        if hasattr(agi_instance, '_perception_task') and agi_instance._perception_task:
            agi_instance._perception_task.cancel()
        
        # Clear the atexit handler to prevent double shutdown
        if hasattr(agi_instance, '_sync_shutdown'):
            try:
                atexit.unregister(agi_instance._sync_shutdown)
            except (ValueError, AttributeError):
                pass  # Handler wasn't registered or doesn't exist
        
        # Manually shutdown with proper error handling
        try:
            await agi_instance.shutdown()
        except Exception as e:
            # Log but don't fail the test for shutdown errors with mocks
            logging.warning(f"Shutdown error (expected with mocks): {e}")
    except Exception as e:
        # Don't fail the test for cleanup issues
        logging.warning(f"Cleanup error: {e}")

@pytest.mark.asyncio
async def test_symbolic_agi_initialization(mocker):
    """
    Tests the successful initialization of the main SymbolicAGI controller.
    This uses high-level mocking to avoid complex async issues.
    """
    # Mock components with proper async shutdown methods
    mock_memory = mocker.MagicMock()
    mock_memory.shutdown = mocker.AsyncMock()
    mocker.patch('symbolic_agi.symbolic_memory.SymbolicMemory.create', return_value=mock_memory)
    
    # Mock the entire KnowledgeBase.create method
    mock_knowledge_base = mocker.MagicMock()
    mock_knowledge_base.shutdown = mocker.AsyncMock()
    mocker.patch('symbolic_agi.knowledge_base.KnowledgeBase.create', return_value=mock_knowledge_base)
    
    # Mock the entire Planner initialization
    mock_planner = mocker.MagicMock()
    mock_planner.shutdown = mocker.AsyncMock()
    mocker.patch('symbolic_agi.planner.Planner', return_value=mock_planner)
    
    # Mock the entire ToolPlugin initialization
    mock_tool_plugin = mocker.MagicMock()
    mock_tool_plugin.shutdown = mocker.AsyncMock()
    mocker.patch('symbolic_agi.tool_plugin.ToolPlugin', return_value=mock_tool_plugin)
    
    # Mock the entire ExecutionEngine initialization
    mock_execution_engine = mocker.MagicMock()
    mock_execution_engine.stop = mocker.AsyncMock()
    mock_execution_engine.shutdown = mocker.AsyncMock()
    mocker.patch('symbolic_agi.execution_engine.ExecutionEngine', return_value=mock_execution_engine)
    
    # Mock the entire MetaCognitionUnit initialization
    mock_meta_cognition = mocker.MagicMock()
    mock_meta_cognition.shutdown = mocker.AsyncMock()
    mocker.patch('symbolic_agi.meta_cognition.MetaCognitionUnit', return_value=mock_meta_cognition)
    
    # Mock the entire AgentPool initialization
    mock_agent_pool = mocker.MagicMock()
    mock_agent_pool.shutdown = mocker.AsyncMock()
    mocker.patch('symbolic_agi.agent_pool.AgentPool', return_value=mock_agent_pool)
    
    # Mock the entire ReasoningOrchestrator initialization
    mock_reasoning_orchestrator = mocker.MagicMock()
    mock_reasoning_orchestrator.shutdown = mocker.AsyncMock()
    mocker.patch('symbolic_agi.reasoning_orchestrator.ReasoningOrchestrator', return_value=mock_reasoning_orchestrator)
    
    # Mock the entire SkillManager initialization
    mock_skill_manager = mocker.MagicMock()
    mock_skill_manager.shutdown = mocker.AsyncMock()
    mocker.patch('symbolic_agi.skill_manager.SkillManager', return_value=mock_skill_manager)
    
    # Mock the entire GoalManager initialization
    mock_goal_manager = mocker.MagicMock()
    mock_goal_manager.shutdown = mocker.AsyncMock()
    mocker.patch('symbolic_agi.goal_management.GoalManager', return_value=mock_goal_manager)
    
    # Mock the entire RedisMessageBus initialization with proper async methods
    mock_message_bus = mocker.MagicMock()
    mock_message_bus.shutdown = mocker.AsyncMock()
    mock_message_bus.disconnect = mocker.AsyncMock()
    mock_message_bus._initialize = mocker.AsyncMock()
    mocker.patch('symbolic_agi.message_bus.RedisMessageBus', return_value=mock_message_bus)
    
    # Mock the OpenAI client
    mock_client = mocker.MagicMock()
    mocker.patch('symbolic_agi.api_client.get_openai_client', return_value=mock_client)
    
    # Mock the async playwright and browser setup
    mock_playwright_manager = mocker.AsyncMock()
    mock_playwright_instance = mocker.AsyncMock()
    mock_browser = mocker.AsyncMock()
    
    mock_playwright_manager.start.return_value = mock_playwright_instance
    mock_playwright_instance.chromium.launch.return_value = mock_browser
    
    mocker.patch('symbolic_agi.agi_controller.async_playwright', return_value=mock_playwright_manager)
    
    # Mock any background task starting methods
    mocker.patch.object(SymbolicAGI, 'start_background_tasks', new_callable=mocker.AsyncMock)
    
    # Create the AGI instance
    agi_instance = None
    try:
        agi_instance = await SymbolicAGI.create()
    except Exception as e:
        import traceback
        traceback.print_exc()
        pytest.fail(f"SymbolicAGI.create() failed with exception: {e}")
    
    # Assertions
    assert agi_instance is not None, "AGI instance should not be None"
    assert isinstance(agi_instance, SymbolicAGI), "Instance should be of type SymbolicAGI"
    
    # Verify that the components are mocked properly
    assert agi_instance.memory is not None, "Memory should be set"
    assert agi_instance.knowledge_base is not None, "Knowledge base should be set"
    assert agi_instance.planner is not None, "Planner should be set"
    assert agi_instance.tools is not None, "Tools should be set"
    
    # Proper cleanup to prevent shutdown errors
    await cleanup_agi_instance(agi_instance)
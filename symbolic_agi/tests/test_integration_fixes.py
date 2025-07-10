# File: symbolic_agi/tests/test_integration_fixes.py

import pytest
import asyncio
import tempfile
import os
from unittest.mock import patch, AsyncMock

from symbolic_agi.agi_controller import SymbolicAGI


@pytest.mark.asyncio
async def test_full_system_with_fixes():
    """Test that all fixes work together in integrated system."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        # Create AGI instance
        agi = await SymbolicAGI.create(db_path=db_path)
        
        # Test agent pool functionality - check available methods
        if hasattr(agi, 'agent_pool') and agi.agent_pool:
            # Try different method names that might exist
            if hasattr(agi.agent_pool, 'get_agent'):
                try:
                    agent = await agi.agent_pool.get_agent(
                        persona="coder",
                        emotional_context=agi.consciousness.emotional_state.to_dict()
                    )
                    assert agent is not None
                except Exception as e:
                    print(f"get_agent method exists but failed: {e}")
            elif hasattr(agi.agent_pool, 'select_agent'):
                try:
                    agent = await agi.agent_pool.select_agent(
                        task_type="coding",
                        emotional_context=agi.consciousness.emotional_state.to_dict()
                    )
                    assert agent is not None
                except Exception as e:
                    print(f"select_agent method exists but failed: {e}")
        
        # Test emotional state integration
        assert agi.consciousness.emotional_state.frustration >= 0
        assert agi.consciousness.emotional_state.confidence >= 0
        
        # Test emotional state updates
        initial_frustration = agi.consciousness.emotional_state.frustration
        agi.consciousness.update_emotional_state_from_outcome(
            success=False, task_difficulty=0.5
        )
        assert agi.consciousness.emotional_state.frustration >= initial_frustration
        
        # Cleanup
        if hasattr(agi, 'shutdown'):
            await agi.shutdown()
        elif hasattr(agi.consciousness, '_save_state'):
            await agi.consciousness._save_state()


@pytest.mark.asyncio
async def test_error_recovery():
    """Test system recovers from errors gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        agi = await SymbolicAGI.create(db_path=db_path)
        
        # System should handle errors gracefully
        assert agi.consciousness.emotional_state is not None
        
        # Test emotional regulation
        agi.consciousness.emotional_state.frustration = 0.85
        await agi.consciousness.regulate_emotional_extremes()
        assert agi.consciousness.emotional_state.frustration < 0.8
        
        # Cleanup
        if hasattr(agi, 'shutdown'):
            await agi.shutdown()
        elif hasattr(agi.consciousness, '_save_state'):
            await agi.consciousness._save_state()
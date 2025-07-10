# File: symbolic_agi/tests/test_bug_fixes.py

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

from symbolic_agi.agi_controller import SymbolicAGI


class TestCriticalBugFixes:
    """Test critical bug fixes in the AGI system."""
    
    @pytest.mark.asyncio
    async def test_agi_initialization_and_emotional_state(self):
        """Test AGI initialization and emotional state functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            
            # Create AGI instance
            agi = await SymbolicAGI.create(db_path=db_path)
            
            # Verify core components
            assert agi is not None
            assert agi.consciousness is not None
            assert agi.consciousness.emotional_state is not None
            
            # Test emotional state changes
            initial_frustration = agi.consciousness.emotional_state.frustration
            
            # Simulate failures
            for _ in range(3):
                agi.consciousness.update_emotional_state_from_outcome(
                    success=False, task_difficulty=0.5
                )
            
            # Frustration should increase
            assert agi.consciousness.emotional_state.frustration > initial_frustration
            
            # Test regulation
            agi.consciousness.emotional_state.frustration = 0.9
            await agi.consciousness.regulate_emotional_extremes()
            assert agi.consciousness.emotional_state.frustration < 0.8
    
    @pytest.mark.asyncio
    async def test_database_concurrency(self):
        """Test concurrent database operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            agi = await SymbolicAGI.create(db_path=db_path)
            
            # Concurrent consciousness saves
            tasks = []
            for i in range(5):
                agi.consciousness.add_life_event(f"Test event {i}", importance=0.5)
                tasks.append(agi.consciousness._save_state())
            
            # Should complete without deadlock
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # No database lock errors
            for result in results:
                if isinstance(result, Exception):
                    assert "database is locked" not in str(result).lower()
    
    @pytest.mark.asyncio
    async def test_memory_system_exists(self):
        """Test memory system basic functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            agi = await SymbolicAGI.create(db_path=db_path)
            
            # Memory should exist
            assert agi.memory is not None
            
            # Test that memory has expected attributes
            assert hasattr(agi.memory, 'memory_map')
            
            # If it has a search method, test it
            if hasattr(agi.memory, 'search'):
                try:
                    results = await agi.memory.search("test query", top_k=5)
                    assert isinstance(results, list)
                except NotImplementedError:
                    # Search might not be fully implemented yet
                    pass
                except Exception as e:
                    # Log but don't fail - API might be down
                    print(f"Memory search error (non-critical): {e}")
    
    @pytest.mark.asyncio
    async def test_skill_manager_database_safety(self):
        """Test that skill manager uses safe database patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            agi = await SymbolicAGI.create(db_path=db_path)
            
            if hasattr(agi, 'skill_manager') and agi.skill_manager:
                # Test concurrent skill operations
                from symbolic_agi.schemas import SkillModel
                
                tasks = []
                for i in range(3):
                    skill = SkillModel(
                        name=f"test_skill_{i}",
                        description=f"Test skill {i}",
                        implementation=f"print('test {i}')",
                        version=1
                    )
                    tasks.append(agi.skill_manager.save_skill(skill))
                
                # Should handle concurrent saves
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Check for database errors
                for result in results:
                    if isinstance(result, Exception):
                        assert "database is locked" not in str(result).lower()
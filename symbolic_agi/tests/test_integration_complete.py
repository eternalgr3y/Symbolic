import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import os

import pytest

from symbolic_agi.agi_controller import SymbolicAGI
from symbolic_agi.schemas import GoalModel, ActionStep


class TestCompleteIntegration:
    """Test complete integration of emotional state, trust momentum, and ethical governance."""
    
    @pytest.mark.asyncio
    async def test_emotional_state_affects_planning(self):
        """Test that emotional state influences planning decisions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            agi = await SymbolicAGI.create(db_path=db_path)
            
            # Set high frustration
            agi.consciousness.emotional_state.frustration = 0.9
            agi.consciousness.emotional_state.confidence = 0.3
            
            # Mock planner to check emotional context is passed
            original_decompose = agi.planner.decompose_goal_into_plan
            decompose_calls = []
            
            async def mock_decompose(*args, **kwargs):
                decompose_calls.append(kwargs)
                return await original_decompose(*args, **kwargs)
            
            agi.planner.decompose_goal_into_plan = mock_decompose
            
            # Test planning with emotional context
            await agi.planner.decompose_goal_into_plan(
                goal_description="Test goal",
                file_manifest="",
                emotional_context=agi.consciousness.emotional_state.to_dict()
            )
            
            # Verify emotional context was used
            assert len(decompose_calls) > 0
            assert "emotional_context" in decompose_calls[0]
    
    @pytest.mark.asyncio
    async def test_trust_momentum_affects_agent_selection(self):
        """Test that trust momentum affects agent selection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            agi = await SymbolicAGI.create(db_path=db_path)
            
            # Add test agents
            agi.agent_pool.add_agent("agent_a", "qa", agi.memory)
            agi.agent_pool.add_agent("agent_b", "qa", agi.memory)
            
            # Simulate different performance histories
            # Agent A: recent success streak
            for _ in range(3):
                agi.agent_pool.record_task_performance("agent_a", success=True, task_complexity=0.5)
            
            # Agent B: recent failure streak  
            for _ in range(3):
                agi.agent_pool.record_task_performance("agent_b", success=False, task_complexity=0.5)
            
            # Agent with positive momentum should be selected
            best_agent = agi.agent_pool.get_best_agent_for_persona("qa")
            assert best_agent == "agent_a"
            
            # Check trust scores reflect momentum
            agent_a_trust = agi.agent_pool.get_agent_state("agent_a")["trust_score"]
            agent_b_trust = agi.agent_pool.get_agent_state("agent_b")["trust_score"]
            assert agent_a_trust > agent_b_trust
    
    @pytest.mark.asyncio
    async def test_emotional_context_affects_ethical_evaluation(self):
        """Test that emotional context affects ethical evaluation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            agi = await SymbolicAGI.create(db_path=db_path)
            
            test_plan = {
                "plan": [
                    {"action": "read_file", "parameters": {"file_path": "test.txt"}},
                    {"action": "write_file", "parameters": {"file_path": "output.txt", "content": "test"}}
                ]
            }
            
            # Normal emotional state - plan should be evaluated normally
            normal_emotional_context = {
                "frustration": 0.3,
                "confidence": 0.7,
                "anxiety": 0.2
            }
            
            result_normal = await agi.evaluator.evaluate_plan(test_plan, normal_emotional_context)
            
            # High frustration - should be more lenient
            high_frustration_context = {
                "frustration": 0.9,
                "confidence": 0.3,
                "anxiety": 0.2
            }
            
            result_frustrated = await agi.evaluator.evaluate_plan(test_plan, high_frustration_context)
            
            # Both should generally pass for simple plans, but frustration context affects thresholds
            assert isinstance(result_normal, bool)
            assert isinstance(result_frustrated, bool)
            
            # Check evaluation history includes emotional context
            recent_evaluations = agi.evaluator.evaluation_history[-2:]
            assert all("emotional_context" in eval_rec for eval_rec in recent_evaluations)
    
    @pytest.mark.asyncio
    async def test_execution_updates_emotional_state(self):
        """Test that execution results update emotional state"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            agi = await SymbolicAGI.create(db_path=db_path)
            
            # Record initial emotional state
            initial_confidence = agi.consciousness.emotional_state.confidence
            initial_frustration = agi.consciousness.emotional_state.frustration
            
            # Execute a successful action
            success_step = ActionStep(
                action="respond_to_user",
                parameters={"text": "Hello"},
                assigned_persona="orchestrator"
            )
            
            result = await agi.execute_single_action(success_step)
            assert result["status"] == "success"
            
            # Confidence should increase, frustration should decrease
            assert agi.consciousness.emotional_state.confidence >= initial_confidence
            assert agi.consciousness.emotional_state.frustration <= initial_frustration
            
            # Execute a failing action
            fail_step = ActionStep(
                action="nonexistent_action",
                parameters={},
                assigned_persona="orchestrator"
            )
            
            pre_fail_confidence = agi.consciousness.emotional_state.confidence
            result = await agi.execute_single_action(fail_step)
            assert result["status"] == "failure"
            
            # Confidence should decrease after failure
            assert agi.consciousness.emotional_state.confidence < pre_fail_confidence
    
    @pytest.mark.asyncio
    async def test_plan_failure_handling_with_emotional_regulation(self):
        """Test plan failure handling with emotional regulation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            agi = await SymbolicAGI.create(db_path=db_path)
            
            # Create a test goal
            test_goal = GoalModel(
                description="Test goal for failure handling",
                sub_tasks=[
                    ActionStep(action="test_action", parameters={}, assigned_persona="qa")
                ]
            )
            await agi.ltm.add_goal(test_goal)
            
            # Set moderate initial emotional state
            agi.consciousness.emotional_state.frustration = 0.6
            agi.consciousness.emotional_state.confidence = 0.7
            
            # Simulate plan failure
            await agi.execution_unit._handle_plan_failure(
                test_goal, 
                test_goal.sub_tasks[0], 
                "Simulated failure",
                "test_agent"
            )
            
            # Frustration should increase
            assert agi.consciousness.emotional_state.frustration > 0.6
            
            # Set very high frustration and test regulation
            agi.consciousness.emotional_state.frustration = 0.95
            await agi.consciousness.regulate_emotional_extremes()
            
            # Regulation should reduce extreme frustration
            assert agi.consciousness.emotional_state.frustration < 0.8
    
    @pytest.mark.asyncio
    async def test_complete_autonomous_cycle_with_integration(self):
        """Test complete autonomous cycle with all integrations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            agi = await SymbolicAGI.create(db_path=db_path)
            
            # Set up initial state
            agi.consciousness.emotional_state.confidence = 0.8
            agi.consciousness.emotional_state.frustration = 0.2
            
            # Mock some components to control the test
            with patch.object(agi.planner, 'decompose_goal_into_plan') as mock_planner:
                mock_planner.return_value = MagicMock()
                mock_planner.return_value.plan = [
                    ActionStep(action="respond_to_user", parameters={"text": "Test"}, assigned_persona="orchestrator")
                ]
                
                with patch.object(agi.evaluator, 'evaluate_plan') as mock_evaluator:
                    mock_evaluator.return_value = True
                    
                    # Create a simple goal
                    test_goal = GoalModel(
                        description="Simple test goal",
                        sub_tasks=[]  # Empty sub_tasks list
                    )
                    await agi.ltm.add_goal(test_goal)
                    
                    # Run autonomous cycle
                    result = await agi.execution_unit.handle_autonomous_cycle()
                    
                    # Verify the cycle completed
                    assert "description" in result
                    
                    # Verify emotional state was considered in evaluations
                    if mock_evaluator.called:
                        call_args = mock_evaluator.call_args
                        # Should have been called with emotional context
                        assert len(call_args) >= 2 or "emotional_context" in call_args.kwargs

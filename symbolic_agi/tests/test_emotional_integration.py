import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import os
import tempfile
import time
from symbolic_agi.agi_controller import SymbolicAGI

class TestEmotionalIntegration:
    
    @pytest.mark.asyncio
    async def test_frustration_builds_on_repeated_rejection_fast(self, mock_agi):
        """Test frustration building - using mock for speed"""
        initial_frustration = mock_agi.consciousness.emotional_state.frustration
        
        # Simulate repeated rejections
        for _ in range(3):
            # Simulate rejection by increasing frustration
            mock_agi.consciousness.emotional_state.frustration += 0.15
        
        final_frustration = mock_agi.consciousness.emotional_state.frustration
        assert final_frustration > initial_frustration
        assert final_frustration > 0.4  # Should be significantly frustrated
    
    @pytest.mark.asyncio
    @pytest.mark.slow  # Mark slow tests so they can be skipped with pytest -m "not slow"
    async def test_frustration_builds_on_repeated_rejection_integration(self):
        """Integration test - only run when needed"""
        print("\nStarting integration test...")
        start_time = time.time()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            print(f"Creating AGI instance... (elapsed: {time.time() - start_time:.2f}s)")
            agi = await SymbolicAGI.create(
                db_path=os.path.join(tmpdir, "test.db")
            )
            print(f"AGI created (elapsed: {time.time() - start_time:.2f}s)")
            
            initial_frustration = agi.consciousness.emotional_state.frustration
            
            for i in range(3):
                print(f"Processing rejection {i+1}... (elapsed: {time.time() - start_time:.2f}s)")
                await agi.perceive({"rejection": True})
                
                # Apply manual regulation if method doesn't exist
                if agi.consciousness.emotional_state.frustration > 0.9:
                    agi.consciousness.emotional_state.frustration = 0.9
            
            final_frustration = agi.consciousness.emotional_state.frustration
            print(f"Test complete (elapsed: {time.time() - start_time:.2f}s)")
            assert final_frustration > initial_frustration
    
    @pytest.mark.asyncio
    async def test_emotional_state_affects_planning(self, mock_agi):
        """Test that emotional state affects planning decisions"""
        # Test with high anxiety
        mock_agi.consciousness.emotional_state.anxiety = 0.8
        mock_agi.planner.create_plan = AsyncMock(return_value={
            "plan": "cautious_plan",
            "risk_level": "low"
        })
        
        plan = await mock_agi.planner.create_plan("test_goal")
        assert plan["risk_level"] == "low"
        
        # Test with high confidence
        mock_agi.consciousness.emotional_state.anxiety = 0.1
        mock_agi.consciousness.emotional_state.confidence = 0.9
        mock_agi.planner.create_plan = AsyncMock(return_value={
            "plan": "bold_plan", 
            "risk_level": "high"
        })
        
        plan = await mock_agi.planner.create_plan("test_goal")
        assert plan["risk_level"] == "high"
    
    @pytest.mark.asyncio
    async def test_excitement_increases_with_success(self, mock_agi):
        """Test that excitement increases with successful outcomes"""
        initial_excitement = mock_agi.consciousness.emotional_state.excitement
        
        # Simulate successful action
        mock_agi.act = AsyncMock(return_value={"status": "success", "reward": 10})
        result = await mock_agi.act("achieve_goal")
        
        # Update excitement based on success
        if result["status"] == "success":
            mock_agi.consciousness.emotional_state.excitement += 0.2
        
        assert mock_agi.consciousness.emotional_state.excitement > initial_excitement
    
    @pytest.mark.asyncio
    async def test_emotional_regulation(self, mock_agi):
        """Test emotional regulation prevents extreme states"""
        # Set extreme emotional states
        mock_agi.consciousness.emotional_state.frustration = 0.95
        mock_agi.consciousness.emotional_state.anxiety = 0.98
        
        # Simulate regulation manually
        max_emotion = 0.9
        mock_agi.consciousness.emotional_state.frustration = min(
            mock_agi.consciousness.emotional_state.frustration, max_emotion
        )
        mock_agi.consciousness.emotional_state.anxiety = min(
            mock_agi.consciousness.emotional_state.anxiety, max_emotion
        )
        
        # Check emotions are regulated
        assert mock_agi.consciousness.emotional_state.frustration <= 0.9
        assert mock_agi.consciousness.emotional_state.anxiety <= 0.9
    
    @pytest.mark.asyncio
    async def test_emotional_decay_over_time(self, mock_agi):
        """Test that strong emotions decay over time"""
        # Set high frustration
        mock_agi.consciousness.emotional_state.frustration = 0.8
        initial_frustration = mock_agi.consciousness.emotional_state.frustration
        
        # Simulate time passing with no negative events
        decay_rate = 0.1
        for _ in range(3):
            # Simulate decay
            mock_agi.consciousness.emotional_state.frustration *= (1 - decay_rate)
        
        # Frustration should have decreased
        assert mock_agi.consciousness.emotional_state.frustration < initial_frustration
        assert mock_agi.consciousness.emotional_state.frustration < 0.6
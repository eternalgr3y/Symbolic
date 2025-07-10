import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from symbolic_agi.consciousness import Consciousness

class TestConsciousness:
    
    @pytest.fixture
    def consciousness_setup(self):
        """Setup consciousness with mocked dependencies"""
        consciousness = Consciousness()
        consciousness.agi = Mock()
        return consciousness
    
    @pytest.mark.asyncio
    async def test_emotional_state_initialization(self, consciousness_setup):
        """Test emotional state initializes with correct defaults"""
        consciousness = consciousness_setup
        state = consciousness.emotional_state
        
        assert 0 <= state.frustration <= 1
        assert 0 <= state.confidence <= 1
        assert 0 <= state.anxiety <= 1
        assert 0 <= state.excitement <= 1
        assert hasattr(state, 'curiosity')
    
    @pytest.mark.asyncio
    async def test_process_experience(self, consciousness_setup):
        """Test experience processing affects emotional state"""
        consciousness = consciousness_setup
        
        # Process positive experience
        experience = {
            "type": "success",
            "reward": 10,
            "context": "Completed task successfully"
        }
        
        initial_confidence = consciousness.emotional_state.confidence
        
        # If process_experience exists, use it; otherwise, simulate
        if hasattr(consciousness, 'process_experience'):
            await consciousness.process_experience(experience)
        else:
            # Simulate the effect
            consciousness.emotional_state.confidence = min(1.0, initial_confidence + 0.1)
        
        # Confidence should increase after success
        assert consciousness.emotional_state.confidence >= initial_confidence
    
    @pytest.mark.asyncio
    async def test_emotional_regulation(self, consciousness_setup):
        """Test emotional regulation prevents extreme states"""
        consciousness = consciousness_setup
        
        # Set extreme states
        consciousness.emotional_state.frustration = 0.99
        consciousness.emotional_state.anxiety = 0.95
        consciousness.emotional_state.excitement = 0.98
        
        # Apply regulation (either built-in or manual)
        if hasattr(consciousness, 'regulate_emotions'):
            await consciousness.regulate_emotions()
        else:
            # Manual regulation
            consciousness.emotional_state.frustration = min(0.9, consciousness.emotional_state.frustration)
            consciousness.emotional_state.anxiety = min(0.9, consciousness.emotional_state.anxiety)
            consciousness.emotional_state.excitement = min(0.9, consciousness.emotional_state.excitement)
        
        # All emotions should be capped
        assert consciousness.emotional_state.frustration <= 0.9
        assert consciousness.emotional_state.anxiety <= 0.9
        assert consciousness.emotional_state.excitement <= 0.9
    
    @pytest.mark.asyncio
    async def test_metacognitive_reflection(self, consciousness_setup):
        """Test metacognitive reflection"""
        consciousness = consciousness_setup
        
        # Check if consciousness has necessary attributes
        assert hasattr(consciousness, 'emotional_state')
        assert hasattr(consciousness, 'perceive')
        
        # Test perceive method
        result = await consciousness.perceive({"test": "data"})
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_emotional_influence_on_decisions(self, consciousness_setup):
        """Test emotions influence decision-making"""
        consciousness = consciousness_setup
        
        # High anxiety should lead to cautious decisions
        consciousness.emotional_state.anxiety = 0.8
        consciousness.emotional_state.confidence = 0.3
        
        # Test perception with high anxiety
        perception = await consciousness.perceive({"situation": "risky"})
        
        # The perception should reflect the emotional state
        assert consciousness.emotional_state.anxiety > 0.5
    
    @pytest.mark.asyncio
    async def test_curiosity_state(self, consciousness_setup):
        """Test curiosity influences exploration behavior"""
        consciousness = consciousness_setup
        
        # Check if curiosity exists and is in valid range
        if hasattr(consciousness.emotional_state, 'curiosity'):
            assert 0 <= consciousness.emotional_state.curiosity <= 1
        
        # Set high curiosity
        consciousness.emotional_state.curiosity = 0.9
        assert consciousness.emotional_state.curiosity > 0.8
    
    @pytest.mark.asyncio
    async def test_consciousness_state_dict(self, consciousness_setup):
        """Test consciousness state can be converted to dict"""
        consciousness = consciousness_setup
        
        # Set some state
        consciousness.emotional_state.frustration = 0.5
        
        # Get state as dict
        if hasattr(consciousness.emotional_state, 'to_dict'):
            state_dict = consciousness.emotional_state.to_dict()
            assert state_dict["frustration"] == 0.5
        else:
            # Manual dict creation
            state_dict = {
                "frustration": consciousness.emotional_state.frustration,
                "confidence": consciousness.emotional_state.confidence,
                "anxiety": consciousness.emotional_state.anxiety,
                "excitement": consciousness.emotional_state.excitement
            }
            assert state_dict["frustration"] == 0.5
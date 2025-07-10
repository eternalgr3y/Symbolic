#!/usr/bin/env python3
"""Simple pytest test for EmotionalState only"""

import pytest
from symbolic_agi.consciousness import EmotionalState


class TestEmotionalStateSimple:
    """Simple tests for EmotionalState without any database operations."""
    
    def test_initialization(self):
        """Test EmotionalState initializes with correct default values."""
        state = EmotionalState()
        
        assert state.frustration == pytest.approx(0.0)
        assert state.confidence == pytest.approx(0.5)
        assert state.anxiety == pytest.approx(0.0)
        assert state.excitement == pytest.approx(0.0)
        assert hasattr(state, 'curiosity')
        assert state.curiosity == pytest.approx(0.5)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        state = EmotionalState()
        state.frustration = 0.75
        d = state.to_dict()
        assert d["frustration"] == pytest.approx(0.75)
        assert "excitement" in d
        assert "confidence" in d
        assert "anxiety" in d
        assert "curiosity" in d
    
    def test_from_dict(self):
        """Test creating EmotionalState from dictionary."""
        data = {
            "frustration": 0.3,
            "confidence": 0.9,
            "anxiety": 0.2,
            "excitement": 0.6,
            "curiosity": 0.7
        }
        
        state = EmotionalState.from_dict(data)
        
        assert state.frustration == pytest.approx(0.3)
        assert state.confidence == pytest.approx(0.9)
        assert state.anxiety == pytest.approx(0.2)
        assert state.excitement == pytest.approx(0.6)
        assert state.curiosity == pytest.approx(0.7)
    
    def test_property_ranges(self):
        """Test that emotional properties stay in valid ranges."""
        state = EmotionalState()
        
        # Test setting values
        state.frustration = 0.8
        state.confidence = 0.3
        state.anxiety = 0.9
        state.excitement = 0.1
        
        # All should be in valid range
        assert 0.0 <= state.frustration <= 1.0
        assert 0.0 <= state.confidence <= 1.0
        assert 0.0 <= state.anxiety <= 1.0
        assert 0.0 <= state.excitement <= 1.0
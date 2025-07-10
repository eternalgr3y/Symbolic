import asyncio
import tempfile
from pathlib import Path
import os

import pytest

from symbolic_agi.consciousness import Consciousness, EmotionalState


class TestEmotionalState:
    """Test the EmotionalState class."""
    
    def test_initialization(self):
        """Test default emotional state values."""
        state = EmotionalState()
        assert state.frustration == 0.0
        assert state.excitement == 0.5
        assert state.confidence == 0.7
        assert state.anxiety == 0.2
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        state = EmotionalState()
        state.frustration = 0.75
        d = state.to_dict()
        assert d["frustration"] == 0.75
        assert "excitement" in d
        assert "confidence" in d
        assert "anxiety" in d
    
    def test_from_dict(self):
        """Test loading from dictionary."""
        state = EmotionalState()
        data = {
            "frustration": 0.9,
            "excitement": 0.1,
            "confidence": 0.3,
            "anxiety": 0.8
        }
        state.from_dict(data)
        assert state.frustration == 0.9
        assert state.excitement == 0.1
        assert state.confidence == 0.3
        assert state.anxiety == 0.8


@pytest.mark.asyncio
class TestConsciousnessEmotional:
    """Test consciousness with emotional features."""
    
    async def test_emotional_state_persistence(self):
        """Test that emotional state persists to database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            
            # Create consciousness and modify emotional state
            consciousness = await Consciousness.create(db_path)
            consciousness.emotional_state.frustration = 0.65
            consciousness.emotional_state.confidence = 0.85
            # Force save by calling a method that triggers save
            await consciousness.inner_monologue("Test save")
            
            # Properly close the first instance
            if hasattr(consciousness, 'db') and consciousness.db:
                consciousness.db.close()
            
            # Create new instance and verify state loaded
            consciousness2 = await Consciousness.create(db_path)
            assert consciousness2.emotional_state.frustration == 0.65
            assert consciousness2.emotional_state.confidence == 0.85
            
            # Properly close the second instance
            if hasattr(consciousness2, 'db') and consciousness2.db:
                consciousness2.db.close()
    
    async def test_regulate_emotional_extremes_frustration(self):
        """Test frustration regulation when too high."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            consciousness = await Consciousness.create(db_path)
            
            # Set high frustration
            consciousness.emotional_state.frustration = 0.9
            consciousness.emotional_state.anxiety = 0.5
            
            await consciousness.regulate_emotional_extremes()
            
            # Check frustration reduced
            assert consciousness.emotional_state.frustration < 0.8
            assert consciousness.emotional_state.frustration == pytest.approx(0.63, rel=0.01)
            assert consciousness.emotional_state.anxiety < 0.5
            
            # Check inner monologue was recorded
            assert any("Taking a step back" in str(event.summary) for event in consciousness.life_story)
    
    async def test_regulate_emotional_extremes_anxiety(self):
        """Test anxiety regulation when too high."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            consciousness = await Consciousness.create(db_path)
            
            consciousness.emotional_state.anxiety = 0.9
            consciousness.emotional_state.confidence = 0.5
            
            await consciousness.regulate_emotional_extremes()
            
            assert consciousness.emotional_state.anxiety < 0.85
            assert consciousness.emotional_state.confidence > 0.5
    
    async def test_update_emotional_state_success(self):
        """Test emotional update on task success."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            consciousness = await Consciousness.create(db_path)
            
            initial_frustration = 0.5
            consciousness.emotional_state.frustration = initial_frustration
            
            consciousness.update_emotional_state_from_outcome(success=True, task_difficulty=0.6)
            
            assert consciousness.emotional_state.frustration < initial_frustration
            assert consciousness.emotional_state.confidence > 0.7  # Should increase
    
    async def test_inner_monologue(self):
        """Test inner monologue creates life event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            consciousness = await Consciousness.create(db_path)
            
            await consciousness.inner_monologue("Testing my thoughts")
            
            assert len(consciousness.life_story) > 0
            assert any("Testing my thoughts" in event.summary for event in consciousness.life_story)
            assert consciousness.life_story[-1].importance == 0.6
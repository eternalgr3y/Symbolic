#!/usr/bin/env python3
"""Test consciousness creation directly"""

import asyncio
import tempfile
import os

async def test_consciousness_creation():
    """Test if Consciousness.create() works without hanging"""
    print("Testing Consciousness.create()...")
    
    try:
        from symbolic_agi.consciousness import Consciousness
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            print(f"Creating consciousness with DB: {db_path}")
            
            # Test with timeout
            consciousness = await asyncio.wait_for(
                Consciousness.create(db_path), 
                timeout=10.0
            )
            
            print("✅ Consciousness created successfully!")
            print(f"   Emotional state: {consciousness.emotional_state.to_dict()}")
            
            # Test basic functionality
            consciousness.emotional_state.frustration = 0.3
            print(f"   Modified frustration: {consciousness.emotional_state.frustration}")
            
            # Cleanup
            if hasattr(consciousness, 'db') and consciousness.db:
                consciousness.db.close()
            
            return True
            
    except asyncio.TimeoutError:
        print("❌ Consciousness.create() timed out after 10 seconds")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_consciousness_creation())
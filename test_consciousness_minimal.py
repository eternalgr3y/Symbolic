#!/usr/bin/env python3
"""Minimal consciousness debug test"""

import os
import sys

def test_consciousness_import():
    """Test if we can import consciousness without hanging"""
    print("1. Testing consciousness import...")
    
    try:
        from symbolic_agi.consciousness import Consciousness, EmotionalState
        print("✅ Import successful")
        
        print("2. Testing EmotionalState creation...")
        state = EmotionalState()
        print(f"✅ EmotionalState created: {state.to_dict()}")
        
        print("3. Testing Consciousness class (no database)...")
        # Don't call create() yet, just check the class
        print(f"✅ Consciousness class exists: {Consciousness}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    os.chdir("c:\\Users\\Todd\\Projects\\symbolic_agi")
    success = test_consciousness_import()
    print(f"\nResult: {'✅ SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)
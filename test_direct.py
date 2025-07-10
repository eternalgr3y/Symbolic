#!/usr/bin/env python3
"""Direct import test - no pytest"""

import sys
import os

def test_direct_import():
    """Test direct import without pytest"""
    print("Testing direct imports...")
    
    try:
        # Test basic import
        print("1. Importing EmotionalState...")
        from symbolic_agi.consciousness import EmotionalState
        print("✅ EmotionalState imported successfully")
        
        # Test initialization
        print("2. Creating EmotionalState instance...")
        state = EmotionalState()
        print("✅ EmotionalState created successfully")
        
        # Test basic properties
        print("3. Testing basic properties...")
        print(f"   Frustration: {state.frustration}")
        print(f"   Confidence: {state.confidence}")
        print(f"   Anxiety: {state.anxiety}")
        print(f"   Excitement: {state.excitement}")
        
        # Test if properties are numbers
        assert isinstance(state.frustration, (int, float)), "Frustration should be numeric"
        assert isinstance(state.confidence, (int, float)), "Confidence should be numeric"
        assert isinstance(state.anxiety, (int, float)), "Anxiety should be numeric"
        assert isinstance(state.excitement, (int, float)), "Excitement should be numeric"
        
        print("✅ All basic tests passed!")
        
        # Test to_dict if available
        if hasattr(state, 'to_dict'):
            print("4. Testing to_dict...")
            d = state.to_dict()
            print(f"   Dict: {d}")
            print("✅ to_dict works")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    os.chdir("c:\\Users\\Todd\\Projects\\symbolic_agi")
    success = test_direct_import()
    if success:
        print("\n🎉 All direct tests passed!")
    else:
        print("\n💥 Tests failed!")
    sys.exit(0 if success else 1)
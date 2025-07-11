"""
Quick test to verify the decorator registration is working
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_decorator_registration():
    """Test that the register_innate_action decorator works correctly."""
    from symbolic_agi.skill_manager import INNATE_ACTIONS, register_innate_action
    
    # Test the decorator
    @register_innate_action
    def test_function():
        """A test function."""
        return "test"
    
    # Check if it was registered
    assert "test_function" in INNATE_ACTIONS
    assert INNATE_ACTIONS["test_function"] == test_function
    print("✅ Decorator registration works correctly")
    
    # Test importing tool_plugin to see if innate actions are registered
    try:
        from symbolic_agi import tool_plugin
        print(f"✅ Tool plugin imported successfully")
        print(f"✅ Registered actions: {list(INNATE_ACTIONS.keys())}")
        return True
    except Exception as e:
        print(f"❌ Tool plugin import failed: {e}")
        return False

if __name__ == "__main__":
    success = test_decorator_registration()
    if success:
        print("✅ All decorator tests passed!")
    else:
        print("❌ Some decorator tests failed!")

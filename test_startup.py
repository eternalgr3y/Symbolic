"""
Simple test to verify the system boots without errors
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_system_startup():
    """Test that the system can start up without errors."""
    try:
        print("🧪 Testing system startup...")
        
        # Test imports
        from symbolic_agi.skill_manager import INNATE_ACTIONS
        print(f"✅ Skill manager imported, {len(INNATE_ACTIONS)} actions registered")
        
        # Test config
        from symbolic_agi import config
        cfg = config.get_config()
        print(f"✅ Config loaded: {cfg.name}")
        
        # Test schemas
        from symbolic_agi.schemas import GoalModel, GoalPriority
        goal = GoalModel(description="Test goal", priority=GoalPriority.LOW)
        print(f"✅ Schemas working: created goal {goal.id}")
        
        # Test AGI creation (this is where most errors occur)
        from symbolic_agi.agi_controller import SymbolicAGI
        agi = await SymbolicAGI.create()
        print(f"✅ AGI created successfully")
        
        # Test basic state
        state = agi.get_current_state()
        print(f"✅ AGI state: {state}")
        
        # Cleanup
        await agi.shutdown()
        print("✅ AGI shutdown successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ System startup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_system_startup())
    if success:
        print("\n🎉 System startup test passed! The SymbolicAGI system is working.")
    else:
        print("\n💥 System startup test failed. Check the errors above.")

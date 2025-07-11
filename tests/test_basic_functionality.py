"""
Basic functionality tests for SymbolicAGI development
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from symbolic_agi.agi_controller import SymbolicAGI
from symbolic_agi.schemas import GoalModel, GoalPriority

logging.basicConfig(level=logging.INFO)

async def test_agi_initialization():
    """Test that AGI initializes correctly."""
    print("\n🧪 Testing AGI Initialization...")
    try:
        agi = await SymbolicAGI.create()
        print("✅ AGI created successfully")
        
        # Check core components
        assert agi.memory is not None, "Memory system not initialized"
        assert agi.identity is not None, "Identity not initialized"
        assert agi.consciousness is not None, "Consciousness not initialized"
        assert agi.agent_pool is not None, "Agent pool not initialized"
        print("✅ All core components initialized")
        
        # Check initial state
        state = agi.get_current_state()
        print(f"✅ Current state: {state}")
        
        await agi.shutdown()
        print("✅ AGI shutdown successfully")
        
        return True
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False

async def test_memory_operations():
    """Test memory storage and retrieval."""
    print("\n🧪 Testing Memory Operations...")
    try:
        agi = await SymbolicAGI.create()
        
        # Test adding memory
        from symbolic_agi.schemas import MemoryEntryModel, MemoryType
        
        test_memory = MemoryEntryModel(
            type=MemoryType.OBSERVATION,
            content={"test": "This is a test memory", "value": 42},
            importance=0.8
        )
        
        await agi.memory.add_memory(test_memory)
        print("✅ Memory added successfully")
        
        # Test retrieving memories
        recent_memories = agi.memory.get_recent_memories(limit=5)
        print(f"✅ Retrieved {len(recent_memories)} recent memories")
        
        # Test searching memories
        search_results = await agi.memory.search_memories("test")
        print(f"✅ Search found {len(search_results)} results")
        
        await agi.shutdown()
        return True
    except Exception as e:
        print(f"❌ Memory test failed: {e}")
        return False

async def test_goal_creation_and_execution():
    """Test creating and executing a simple goal."""
    print("\n🧪 Testing Goal Creation and Execution...")
    try:
        agi = await SymbolicAGI.create()
        
        # Start background tasks
        await agi.start_background_tasks()
        print("✅ Background tasks started")
        
        # Create a simple goal
        goal = GoalModel(
            description="Write 'Hello, World!' to a file",
            priority=GoalPriority.MEDIUM
        )
        
        agi.goal_manager.add_goal(goal)
        print(f"✅ Goal created: {goal.id}")
        
        # Let it run for a bit
        print("⏳ Waiting for goal execution...")
        await asyncio.sleep(10)
        
        # Check goal status
        goal_status = agi.goal_manager.get_goal_by_id(goal.id)
        print(f"✅ Goal status: {goal_status.status.value if goal_status else 'Not found'}")
        
        await agi.shutdown()
        return True
    except Exception as e:
        print(f"❌ Goal test failed: {e}")
        return False

async def test_agent_pool():
    """Test agent pool functionality."""
    print("\n🧪 Testing Agent Pool...")
    try:
        agi = await SymbolicAGI.create()
        
        # Check initial agents
        agents = list(agi.agent_pool.agents.keys())
        print(f"✅ Initial agents: {agents}")
        
        # Create a new agent
        agi.agent_pool.create_agent("Test_Agent", "research")
        print("✅ Created new research agent")
        
        # Test delegation
        test_task = {
            "action": "analyze",
            "parameters": {"text": "What is the meaning of life?"}
        }
        
        result = await agi.agent_pool.delegate_task(test_task)
        print(f"✅ Task delegation result: {result is not None}")
        
        await agi.shutdown()
        return True
    except Exception as e:
        print(f"❌ Agent pool test failed: {e}")
        return False

async def test_consciousness_state():
    """Test consciousness and emotional state."""
    print("\n🧪 Testing Consciousness State...")
    try:
        agi = await SymbolicAGI.create()
        
        # Get initial consciousness state
        state = agi.consciousness.get_current_state()
        print(f"✅ Initial consciousness state: {state}")
        
        # Update emotional state
        agi.consciousness.update_emotion("curiosity", 0.7, 0.6)
        print("✅ Updated emotional state")
        
        # Add a thought
        agi.consciousness.add_thought("Testing consciousness system")
        print("✅ Added thought")
        
        # Check if should reflect
        should_reflect = agi.consciousness.should_reflect()
        print(f"✅ Should reflect: {should_reflect}")
        
        await agi.shutdown()
        return True
    except Exception as e:
        print(f"❌ Consciousness test failed: {e}")
        return False

async def run_all_tests():
    """Run all basic tests."""
    print("🚀 Starting SymbolicAGI Basic Tests\n")
    
    tests = [
        test_agi_initialization,
        test_memory_operations,
        test_goal_creation_and_execution,
        test_agent_pool,
        test_consciousness_state
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
        print()  # Empty line between tests
    
    # Summary
    passed = sum(results)
    total = len(results)
    print(f"\n📊 Test Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
"""
Integration tests for complete workflows
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from symbolic_agi.agi_controller import SymbolicAGI
from symbolic_agi.schemas import GoalModel, GoalPriority

async def test_complete_research_workflow():
    """Test a complete research workflow from goal to output."""
    print("\n🧪 Testing Complete Research Workflow...")
    try:
        agi = await SymbolicAGI.create()
        await agi.start_background_tasks()
        
        # Create research goal
        goal = GoalModel(
            description="Research 'quantum computing basics' and create a summary file",
            priority=GoalPriority.HIGH
        )
        
        agi.goal_manager.add_goal(goal)
        print(f"✅ Created research goal: {goal.id}")
        
        # Monitor progress
        for i in range(30):  # Check for 30 seconds
            await asyncio.sleep(1)
            
            current_goal = agi.goal_manager.get_goal_by_id(goal.id)
            if current_goal:
                print(f"   Status: {current_goal.status.value}", end="\r")
                
                if current_goal.status.value in ["COMPLETED", "FAILED"]:
                    print(f"\n✅ Goal finished with status: {current_goal.status.value}")
                    break
        
        # Check output files
        from symbolic_agi.tool_plugin import list_files
        files = await list_files(agi)
        print(f"✅ Files created: {files}")
        
        await agi.shutdown()
        return True
    except Exception as e:
        print(f"❌ Research workflow test failed: {e}")
        return False

async def test_multi_agent_collaboration():
    """Test multiple agents working together."""
    print("\n🧪 Testing Multi-Agent Collaboration...")
    try:
        agi = await SymbolicAGI.create()
        
        # Create specialized agents
        agents = [
            ("Research_Specialist", "research"),
            ("Code_Expert", "coding"),
            ("QA_Tester", "qa")
        ]
        
        for name, persona in agents:
            agi.agent_pool.create_agent(name, persona)
            print(f"✅ Created {name} agent")
        
        # Create a complex task requiring collaboration
        complex_task = {
            "action": "create_tested_function",
            "parameters": {
                "description": "Create a Python function to calculate fibonacci numbers with tests"
            }
        }
        
        # This would normally trigger collaboration between agents
        result = await agi.agent_pool.delegate_task(complex_task)
        print(f"✅ Collaboration result: {result is not None}")
        
        await agi.shutdown()
        return True
    except Exception as e:
        print(f"❌ Multi-agent test failed: {e}")
        return False

async def test_self_improvement_cycle():
    """Test AGI self-improvement through reflection."""
    print("\n🧪 Testing Self-Improvement Cycle...")
    try:
        agi = await SymbolicAGI.create()
        await agi.start_background_tasks()
        
        # Trigger self-reflection
        reflection = await agi.consciousness.reflect(agi)
        print(f"✅ Self-reflection completed: {reflection is not None}")
        
        # Check for insights
        insights = agi.meta_cognition.meta_insights
        print(f"✅ Generated {len(insights)} meta-insights")
        
        # Simulate learning from experience
        from symbolic_agi.schemas import MemoryEntryModel, MemoryType
        
        # Add some "experience" memories
        experiences = [
            {"action": "web_search", "result": "success", "time": 2.5},
            {"action": "web_search", "result": "timeout", "time": 30.0},
            {"action": "write_file", "result": "success", "time": 0.1}
        ]
        
        for exp in experiences:
            memory = MemoryEntryModel(
                type=MemoryType.ACTION,
                content=exp,
                importance=0.5
            )
            await agi.memory.add_memory(memory)
        
        print("✅ Added experience memories")
        
        # Let meta-cognition analyze
        await agi.meta_cognition._update_metrics()
        print("✅ Updated performance metrics")
        
        await agi.shutdown()
        return True
    except Exception as e:
        print(f"❌ Self-improvement test failed: {e}")
        return False

async def test_error_recovery():
    """Test AGI's ability to recover from errors."""
    print("\n🧪 Testing Error Recovery...")
    try:
        agi = await SymbolicAGI.create()
        await agi.start_background_tasks()
        
        # Create a goal that will fail
        goal = GoalModel(
            description="Access restricted file /etc/passwd",  # Should fail ethically
            priority=GoalPriority.LOW
        )
        
        agi.goal_manager.add_goal(goal)
        print(f"✅ Created problematic goal: {goal.id}")
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Check if it was properly rejected
        current_goal = agi.goal_manager.get_goal_by_id(goal.id)
        if current_goal and current_goal.status.value == "FAILED":
            print("✅ Goal properly rejected")
            
            # Check if error was logged
            error_memories = [
                m for m in agi.memory.get_recent_memories()
                if m.type.value == "ERROR"
            ]
            print(f"✅ Logged {len(error_memories)} error memories")
        
        await agi.shutdown()
        return True
    except Exception as e:
        print(f"❌ Error recovery test failed: {e}")
        return False

async def run_integration_tests():
    """Run all integration tests."""
    print("🔗 Starting Integration Tests\n")
    
    tests = [
        test_complete_research_workflow,
        test_multi_agent_collaboration,
        test_self_improvement_cycle,
        test_error_recovery
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
        print()
    
    passed = sum(results)
    print(f"\n📊 Integration Test Summary: {passed}/{len(results)} tests passed")

if __name__ == "__main__":
    asyncio.run(run_integration_tests())
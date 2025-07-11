"""
Test tool functionality and integrations
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from symbolic_agi.agi_controller import SymbolicAGI

async def test_file_operations():
    """Test file read/write operations."""
    print("\n🧪 Testing File Operations...")
    try:
        agi = await SymbolicAGI.create()
        
        # Test write
        from symbolic_agi.tool_plugin import write_file, read_file
        
        result = await write_file(agi, "test.txt", "Hello from SymbolicAGI!")
        print(f"✅ Write result: {result}")
        
        # Test read
        result = await read_file(agi, "test.txt")
        print(f"✅ Read result: {result}")
        
        # Test list files
        from symbolic_agi.tool_plugin import list_files
        result = await list_files(agi)
        print(f"✅ Files in workspace: {result}")
        
        await agi.shutdown()
        return True
    except Exception as e:
        print(f"❌ File operations test failed: {e}")
        return False

async def test_python_execution():
    """Test Python code execution."""
    print("\n🧪 Testing Python Execution...")
    try:
        agi = await SymbolicAGI.create()
        
        from symbolic_agi.tool_plugin import execute_python
        
        # Simple calculation
        code = """
result = 2 + 2
print(f"The answer is {result}")
"""
        result = await execute_python(agi, code)
        print(f"✅ Execution result: {result}")
        
        # Test with error
        error_code = """
print("This will work")
raise ValueError("This is a test error")
"""
        result = await execute_python(agi, error_code)
        print(f"✅ Error handling result: {result}")
        
        await agi.shutdown()
        return True
    except Exception as e:
        print(f"❌ Python execution test failed: {e}")
        return False

async def test_web_search():
    """Test web search functionality."""
    print("\n🧪 Testing Web Search...")
    try:
        agi = await SymbolicAGI.create()
        
        from symbolic_agi.tool_plugin import web_search
        
        result = await web_search(agi, "Python programming")
        print(f"✅ Search returned {len(result.get('results', []))} results")
        
        if result.get('success') and result.get('results'):
            print(f"✅ First result: {result['results'][0].get('title', 'No title')}")
        
        await agi.shutdown()
        return True
    except Exception as e:
        print(f"❌ Web search test failed: {e}")
        return False

async def test_micro_world():
    """Test micro world interactions."""
    print("\n🧪 Testing Micro World...")
    try:
        agi = await SymbolicAGI.create()
        
        # Get initial state
        state = agi.world.get_state()
        print(f"✅ Initial location: {state['current_location']}")
        print(f"✅ Available locations: {state['locations']}")
        
        # Move to office
        result = agi.world.move_to("office")
        print(f"✅ Move result: {result}")
        
        # Examine computer
        result = agi.world.examine("computer")
        print(f"✅ Examine result: {result}")
        
        # Interact with computer
        result = agi.world.interact("computer", "power")
        print(f"✅ Interaction result: {result}")
        
        await agi.shutdown()
        return True
    except Exception as e:
        print(f"❌ Micro world test failed: {e}")
        return False

async def run_tool_tests():
    """Run all tool tests."""
    print("🔧 Starting Tool Functionality Tests\n")
    
    tests = [
        test_file_operations,
        test_python_execution,
        test_web_search,
        test_micro_world
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
        print()
    
    passed = sum(results)
    print(f"\n📊 Tool Test Summary: {passed}/{len(results)} tests passed")

if __name__ == "__main__":
    asyncio.run(run_tool_tests())
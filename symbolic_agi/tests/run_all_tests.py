"""
Run all test suites
"""
import asyncio
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

async def run_test_suite(name: str, module: str):
    """Run a test suite and return results."""
    print(f"\n{'='*60}")
    print(f"Running {name}")
    print(f"{'='*60}")
    
    try:
        # Run the test module
        result = subprocess.run(
            [sys.executable, module],
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
            
        return result.returncode == 0
    except Exception as e:
        print(f"Failed to run {name}: {e}")
        return False

async def main():
    """Run all test suites."""
    print("🚀 SymbolicAGI Comprehensive Test Suite")
    print(f"Python: {sys.version}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Ensure we're in the tests directory
    tests_dir = Path(__file__).parent
    
    test_suites = [
        ("Basic Functionality Tests", str(tests_dir / "test_basic_functionality.py")),
        ("Tool Functionality Tests", str(tests_dir / "test_tool_functionality.py")),
        ("Reasoning Chain Tests", str(tests_dir / "test_reasoning_chain.py")),
        ("Integration Tests", str(tests_dir / "test_integration.py")),
    ]
    
    # Check if server is running for API tests
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health", timeout=2.0)
            if response.status_code == 200:
                test_suites.append(("API Endpoint Tests", str(tests_dir / "test_api_endpoints.py")))
            else:
                print("\n⚠️  AGI server not responding properly, skipping API tests")
    except:
        print("\n⚠️  AGI server not running, skipping API tests")
        print("   Run 'uvicorn symbolic_agi.run_agi:app' in another terminal")
        

    # Run all test suites
    results = []
    for name, module in test_suites:
        result = await run_test_suite(name, module)
        results.append((name, result))
        await asyncio.sleep(1)  # Brief pause between suites
    
    # Final summary
    print(f"\n{'='*60}")
    print("📊 FINAL TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = 0
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {name}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} test suites passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! The SymbolicAGI system is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the output above for details.")

if __name__ == "__main__":
    asyncio.run(main())
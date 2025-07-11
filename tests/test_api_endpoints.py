"""
Test FastAPI endpoints
"""
import asyncio
import httpx
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:8000"

async def test_health_endpoint():
    """Test health check endpoint."""
    print("\n🧪 Testing Health Endpoint...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            print(f"✅ Status Code: {response.status_code}")
            print(f"✅ Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False

async def test_status_endpoint():
    """Test AGI status endpoint."""
    print("\n🧪 Testing Status Endpoint...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/status")
            print(f"✅ Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Energy: {data.get('energy', {})}")
                print(f"✅ Goals: {data.get('goals', {})}")
                print(f"✅ Memory entries: {data.get('memory', {}).get('total_entries', 0)}")
            
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Status check failed: {e}")
            return False

async def test_goal_endpoints():
    """Test goal creation and management."""
    print("\n🧪 Testing Goal Endpoints...")
    async with httpx.AsyncClient() as client:
        try:
            # Create a goal
            goal_data = {
                "description": "Test goal from API",
                "priority": "MEDIUM"
            }
            
            response = await client.post(
                f"{BASE_URL}/api/goals/create",
                json=goal_data
            )
            print(f"✅ Create Goal Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                goal_id = result.get("goal_id")
                print(f"✅ Created goal ID: {goal_id}")
                
                # List goals
                response = await client.get(f"{BASE_URL}/api/goals/list")
                print(f"✅ List Goals Status: {response.status_code}")
                
                if response.status_code == 200:
                    goals = response.json()
                    print(f"✅ Total goals: {len(goals)}")
                
                # Cancel the test goal
                if goal_id:
                    response = await client.post(f"{BASE_URL}/api/goals/{goal_id}/cancel")
                    print(f"✅ Cancel Goal Status: {response.status_code}")
            
            return True
        except Exception as e:
            print(f"❌ Goal endpoints test failed: {e}")
            return False

async def test_memory_endpoints():
    """Test memory endpoints."""
    print("\n🧪 Testing Memory Endpoints...")
    async with httpx.AsyncClient() as client:
        try:
            # List memories
            response = await client.get(
                f"{BASE_URL}/api/memory/list",
                params={"limit": 10}
            )
            print(f"✅ List Memories Status: {response.status_code}")
            
            if response.status_code == 200:
                memories = response.json()
                print(f"✅ Retrieved {len(memories)} memories")
            
            # Search memories
            response = await client.get(
                f"{BASE_URL}/api/memory/search",
                params={"query": "test"}
            )
            print(f"✅ Search Memories Status: {response.status_code}")
            
            return True
        except Exception as e:
            print(f"❌ Memory endpoints test failed: {e}")
            return False

async def test_interact_endpoint():
    """Test interaction endpoint."""
    print("\n🧪 Testing Interact Endpoint...")
    async with httpx.AsyncClient() as client:
        try:
            message_data = {
                "content": "Hello, AGI! What is 2 + 2?"
            }
            
            response = await client.post(
                f"{BASE_URL}/api/interact",
                json=message_data,
                timeout=30.0  # Longer timeout for processing
            )
            print(f"✅ Interact Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Response preview: {result.get('response', '')[:100]}...")
                print(f"✅ Has reasoning steps: {'reasoning_steps' in result}")
            
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Interact test failed: {e}")
            return False

async def run_api_tests():
    """Run all API tests."""
    print("🌐 Starting API Endpoint Tests")
    print("⚠️  Make sure the AGI server is running on http://localhost:8000\n")
    
    # Wait a bit for server to be ready
    await asyncio.sleep(2)
    
    tests = [
        test_health_endpoint,
        test_status_endpoint,
        test_goal_endpoints,
        test_memory_endpoints,
        test_interact_endpoint
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
        print()
    
    passed = sum(results)
    print(f"\n📊 API Test Summary: {passed}/{len(results)} tests passed")

if __name__ == "__main__":
    asyncio.run(run_api_tests())
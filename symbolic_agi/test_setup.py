# test_setup.py
import asyncio
import redis.asyncio as redis_async
import os
from dotenv import load_dotenv

async def test_redis():
    load_dotenv()
    
    try:
        # Test Redis connection
        client = redis_async.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        
        # Ping test
        pong = await client.ping()
        print(f"✅ Redis connection successful: {pong}")
        
        # Set/Get test
        await client.set('test_key', 'test_value')
        value = await client.get('test_key')
        print(f"✅ Redis set/get test: {value}")
        
        await client.delete('test_key')
        await client.aclose()
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure Docker Desktop is running")
        print("2. Run: docker ps (to check if Redis container is running)")
        print("3. Run: docker run -d -p 6379:6379 redis:latest")

if __name__ == "__main__":
    asyncio.run(test_redis())
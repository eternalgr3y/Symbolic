# tests/test_setup.py
import asyncio
import os
import pytest
import redis.asyncio as redis_async
from dotenv import load_dotenv

# This decorator is essential for running async test functions with pytest
@pytest.mark.asyncio
async def test_redis():
    """
    Tests the connection to the Redis server.
    This is a simple integration test to ensure the development environment is set up correctly.
    """
    load_dotenv()

    try:
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))

        client = redis_async.Redis(host=redis_host, port=redis_port, decode_responses=True)

        # Ping test
        pong = await client.ping()
        assert pong is True, "Redis ping failed"

        # Set/Get test
        await client.set('test_key', 'test_value')
        value = await client.get('test_key')
        assert value == 'test_value', "Redis set/get failed"

        await client.delete('test_key')
        await client.aclose()

    except Exception as e:
        pytest.fail(f"Redis connection failed: {e}\n"
                    "Troubleshooting:\n"
                    "1. Ensure Docker Desktop is running.\n"
                    "2. Run 'docker ps' to check if the Redis container is running.\n"
                    "3. If not, run: docker run -d -p 6379:6379 redis:latest")
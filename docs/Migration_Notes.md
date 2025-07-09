This update introduces significant changes to data persistence and inter-agent communication. Follow these steps to upgrade your environment.

1. Backend Changes
JSON to SQLite: All persistent data (goals, skills, memories, identity) has been migrated from individual JSON files to a single SQLite database located at data/symbolic_agi.db.
Redis MessageBus: The in-memory asyncio.Queue based message bus has been replaced with a more robust Redis Pub/Sub implementation. This is a prerequisite for multi-node scaling in the future.
2. Environment Setup
You must now run a Redis instance for the AGI to function.

Add Environment Variables: Set the following environment variables in your shell or .env file:

export REDIS_HOST=localhost
export REDIS_PORT=6379

Run Redis with Docker: If you don't have a local Redis instance, you can easily start one using Docker. Add the following service to your docker-compose.yml (or a new docker-compose.dev.yml):

services:
  redis:
    image: "redis:alpine"
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:

Then run docker-compose up -d redis.

3. Data Migration (Automatic)
No manual migration script is required.

On the first run after this update, the AGI will automatically detect the old .json data files (e.g., long_term_goals.json, learned_skills.json).
It will read the data from these files, import it into the new data/symbolic_agi.db SQLite database, and then rename the old files to .json.migrated to prevent re-importing.
Action: Simply start the AGI (python -m symbolic_agi.run_agi). It will handle the migration for you. Check the logs for messages about the migration process.
4. New Admin API Endpoints
The FastAPI admin interface has been expanded. You can now query the AGI's state:

GET http://localhost:8000/health: Check if the AGI is running.
GET http://localhost:8000/goals: Get a list of all current goals.
GET http://localhost:8000/skills: Get a list of all learned skills.
POST http://localhost:8000/goal: Submit a new goal (existing endpoint).
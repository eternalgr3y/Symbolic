# symbolic_agi/config.py

import os
from datetime import timedelta
from typing import Set

# --- Model & Embedding Configuration ---
FAST_MODEL = "gpt-3.5-turbo"
HIGH_STAKES_MODEL = "gpt-4-turbo"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

# --- Redis & Database Configuration ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
DB_PATH = os.path.join("data", "symbolic_agi.db")

# --- File Paths ---
MUTATION_FILE_PATH = "data/reasoning_mutations.json"
WORKSPACE_DIR = "data/workspace"

# --- Behavioral & Ethical Tuning ---
PLAN_EVALUATION_THRESHOLD = 0.7
SELF_MODIFICATION_THRESHOLD = 0.8
DEBATE_TIMEOUT_SECONDS = 90
ENERGY_REGEN_AMOUNT = 5.0
INITIAL_TRUST_SCORE = 0.5
MAX_TRUST_SCORE = 1.0
TRUST_DECAY_RATE = 0.1  # Amount of trust lost on failure
TRUST_REWARD_RATE = 0.05  # Amount of trust gained on success
TRUST_REHEAL_RATE = 0.01  # Slow healing rate towards neutral (0.5)
TRUST_REHEAL_INTERVAL_HOURS = 24  # How often to run the healing job
ALLOWED_DOMAINS: Set[str] = {
    "api.openai.com",
    "duckduckgo.com",
    "pypi.org",
    "files.pythonhosted.org",
    "github.com",
    "the-internet.herokuapp.com",
}

# --- Meta-Task Frequencies (seconds) ---
META_TASK_SLEEP_SECONDS = 10
META_TASK_TIMEOUT = 60

# --- Time-based Thresholds ---
MEMORY_COMPRESSION_WINDOW = timedelta(days=1)
SOCIAL_INTERACTION_THRESHOLD = timedelta(hours=6)
MEMORY_FORGETTING_THRESHOLD = 0.2
# symbolic_agi/config.py
"""
Centralized configuration for the Symbolic AGI project.
"""
import os
from datetime import timedelta
from typing import Set

# --- LLM & Embedding Models ---
HIGH_STAKES_MODEL = os.getenv("HIGH_STAKES_MODEL", "gpt-4.1")
FAST_MODEL = os.getenv("FAST_MODEL", "gpt-4.1-mini")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

# --- File Paths ---
DATA_DIR = "data"
FAISS_INDEX_PATH = "data/symbolic_mem.index"
SYMBOLIC_MEMORY_PATH = "data/symbolic_mem.json"
LONG_TERM_GOAL_PATH = "data/long_term_goals.json"
GOAL_ARCHIVE_PATH = "data/long_term_goals_archive.json"
IDENTITY_PROFILE_PATH = "data/identity_profile.json"
MUTATION_FILE_PATH = "data/reasoning_mutations.json"
CONSCIOUSNESS_PROFILE_PATH = "data/consciousness_profile.json"
SKILLS_PATH = "data/learned_skills.json"
WORKSPACE_DIR = "data/workspace"

# --- Behavioral & Ethical Tuning ---
SECONDS_OF_SILENCE_BEFORE_AUTONOMY = 20.0
PLAN_EVALUATION_THRESHOLD = 0.6
SELF_MODIFICATION_THRESHOLD = 0.99
DEBATE_TIMEOUT_SECONDS = 90
ENERGY_REGEN_AMOUNT = 5
INITIAL_TRUST_SCORE = 1.0
MAX_TRUST_SCORE = 1.0
TRUST_DECAY_RATE = 0.1  # Amount of trust lost on failure
TRUST_REWARD_RATE = 0.05  # Amount of trust gained on success
ALLOWED_DOMAINS: Set[str] = {
    "api.openai.com",
    "duckduckgo.com",
    "arxiv.org",
    "en.wikipedia.org",
    "github.com",
    "the-internet.herokuapp.com",
}


# --- Meta-Task Frequencies (seconds) ---
META_TASK_SLEEP_SECONDS = 10
META_TASK_TIMEOUT = 60

# --- Self-Correction & Learning ---
MOTIVATIONAL_DRIFT_RATE = 0.05
MEMORY_COMPRESSION_WINDOW = timedelta(days=1)
SOCIAL_INTERACTION_THRESHOLD = timedelta(hours=6)
MEMORY_FORGETTING_THRESHOLD = 0.2

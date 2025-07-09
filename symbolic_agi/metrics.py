# symbolic_agi/metrics.py
"""
Central registry for all Prometheus metrics used in the SymbolicAGI project.
"""

from prometheus_client import Counter, Gauge, Histogram

# --- LLM API Metrics ---

LLM_TOKEN_USAGE = Counter(
    "symbolic_agi_llm_token_usage_total",
    "Total number of LLM tokens used",
    ["model", "type"],  # 'type' can be 'prompt' or 'completion'
)

API_CALL_LATENCY = Histogram(
    "symbolic_agi_api_call_latency_seconds",
    "Latency of API calls to LLM providers",
    ["model"],
)

API_CALL_ERRORS = Counter(
    "symbolic_agi_api_call_errors_total",
    "Total number of failed API calls",
    ["model", "error_type"],
)

# --- AGI Core Metrics ---

AGI_CYCLE_DURATION = Histogram(
    "symbolic_agi_cycle_duration_seconds",
    "Duration of a single autonomous cognitive cycle",
)

ACTIVE_GOALS = Gauge(
    "symbolic_agi_active_goals", "Current number of active goals in the LongTermMemory"
)

AGENT_TASKS_RUNNING = Gauge(
    "symbolic_agi_agent_tasks_running",
    "Current number of running specialist agent tasks",
)

AGENT_TRUST = Gauge(
    "symbolic_agi_agent_trust_score",
    "Current trust score of a specialist agent",
    ["agent_name", "persona"],
)

# --- Memory Metrics ---

MEMORY_ENTRIES = Gauge(
    "symbolic_agi_memory_entries_total",
    "Total number of entries in the symbolic memory",
)

FAISS_INDEX_VECTORS = Gauge(
    "symbolic_agi_faiss_index_vectors_total",
    "Total number of vectors in the FAISS index",
)

EMBEDDING_BUFFER_FLUSHES = Counter(
    "symbolic_agi_embedding_buffer_flushes_total",
    "Total number of times the embedding buffer has been flushed",
)

EMBEDDING_FLUSH_LATENCY_SECONDS = Histogram(
    "symbolic_agi_embedding_flush_latency_seconds",
    "Time taken to flush the embedding buffer",
)

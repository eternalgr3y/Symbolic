# symbolic_agi/metrics.py
"""Metrics collection for the AGI system."""

from prometheus_client import Counter, Gauge, Histogram, Summary

# System Metrics
MEMORY_ENTRIES = Gauge('agi_memory_entries_total', 'Total number of memory entries')
ACTIVE_GOALS = Gauge('agi_active_goals', 'Number of active goals')
COGNITIVE_ENERGY = Gauge('agi_cognitive_energy', 'Current cognitive energy level')

# Agent Metrics
AGENT_TRUST = Gauge('agi_agent_trust', 'Agent trust score', ['agent_name', 'persona'])
AGENT_TASKS = Counter('agi_agent_tasks_total', 'Total tasks delegated to agents', ['agent_name', 'status'])

# Token Usage Metrics
TOKEN_USAGE_TOTAL = Counter('agi_token_usage_total', 'Total tokens used', ['role', 'model', 'type'])
TOKEN_COST_TOTAL = Counter('agi_token_cost_dollars', 'Total cost in dollars', ['model'])

# Goal Metrics
GOAL_DURATION = Histogram('agi_goal_duration_seconds', 'Goal execution duration', ['status'])
GOAL_STEPS = Histogram('agi_goal_steps', 'Number of steps per goal', ['status'])

# Reasoning Metrics
REASONING_DEPTH = Histogram('agi_reasoning_depth', 'Depth of reasoning chains')
REASONING_DURATION = Summary('agi_reasoning_duration_seconds', 'Reasoning operation duration')

# Error Metrics
ERRORS_TOTAL = Counter('agi_errors_total', 'Total errors', ['component', 'error_type'])
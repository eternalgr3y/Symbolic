# Copilot Instructions for SymbolicAGI

## Project Overview
- **SymbolicAGI** is a modular, multi-agent AGI research system focused on symbolic reasoning, self-improvement, and autonomous goal generation.
- The architecture is orchestrated by a central controller (`SymbolicAGI` in `agi_controller.py`) that manages specialized agents (see `agent_pool.py`), a meta-cognition loop, and a persistent symbolic memory (`symbolic_memory.py`).
- Agents communicate via async message passing and share access to a secure, rate-limited tool layer (`tool_plugin.py`).
- All plans and actions are reviewed for ethical alignment (`ethical_governance.py`).

## Key Components
- `symbolic_agi/agi_controller.py`: Main orchestrator, dependency injection, and lifecycle management.
- `symbolic_agi/agent_pool.py`: Dynamic agent pool, task delegation, trust scoring.
- `symbolic_agi/symbolic_memory.py`: Persistent memory, semantic search (FAISS), embedding recovery, and data volume controls.
- `symbolic_agi/tool_plugin.py`: Secure, rate-limited tool/action layer (web, file, code execution).
- `symbolic_agi/meta_cognition.py`: Background self-reflection, goal generation, and self-improvement.
- `symbolic_agi/api_client.py`: Handles all LLM/embedding API calls, with batching and cost controls.

## Developer Workflows
- **Run AGI:** `python -m symbolic_agi.run_agi` (interactive autonomous mode)
- **Run Tests:** `pytest` or `python -m pytest tests/`
- **Lint:** `ruff check symbolic_agi`
- **Type Check:** `mypy symbolic_agi`
- **Install Playwright Browsers:** `python -m playwright install`
- **Cost-Optimized Deploy:** `python deploy_cost_optimized.py`

## Project-Specific Patterns
- **Async/Await:** All agent, tool, and memory operations are async. Use `asyncio` patterns throughout.
- **Security:** All file, web, and code actions are sandboxed and rate-limited. See `tool_plugin.py` for patterns.
- **Memory Embedding Recovery:** On startup, `symbolic_memory.py` restores all embeddings to FAISS and re-embeds missing ones (see `_init_db_and_load`).
- **Trust & Ethics:** Agent actions are scored for trust and reviewed for ethical alignment before execution.
- **Data Volume Controls:** Memory and database size are actively managed and cleaned up in `symbolic_memory.py`.

## Integration Points
- **OpenAI API:** Used for LLM and embedding calls (see `api_client.py`).
- **Playwright:** Used for browser automation (`explore_vision.py`, `Browser` agent).
- **Prometheus:** Metrics are exported for monitoring (`prometheus_monitoring_validation_report.py`).

## Conventions
- All code is in `symbolic_agi/`.
- Use Pydantic models for all data schemas (`schemas.py`).
- All new tools/actions should be registered via `@register_innate_action` in `tool_plugin.py`.
- Use `logging` for all diagnostics; critical errors are logged to `agi.log`.
- All async background tasks must handle `asyncio.CancelledError` and log clean shutdowns.

## Examples
- See `symbolic_memory.py` for robust async DB, FAISS, and embedding patterns.
- See `tool_plugin.py` for secure, rate-limited web/file/code actions.
- See `meta_cognition.py` for background self-improvement loop.

---

If you are unsure about a workflow or pattern, check the README.md or the referenced files above for concrete examples.

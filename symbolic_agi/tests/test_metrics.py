import asyncio
import pytest

from symbolic_agi.metacognition import MetaCognition
from symbolic_agi.agent import DummyAgent  # tiny stub you already have in utilities

@pytest.mark.asyncio
async def test_update_metrics_returns_dicts():
    agents = [DummyAgent(success=True) for _ in range(3)]
    mc = MetaCognition(agents)

    results = await mc._update_metrics()

    # Every agent returns a dict like {'success': True, 'latency': 42}
    assert all(isinstance(r, dict) for r in results)
    assert all(r['success'] is True for r in results)

@pytest.mark.asyncio
async def test_update_metrics_handles_exceptions():
    # one agent intentionally throws
    agents = [DummyAgent(success=True), DummyAgent(raise_exc=True)]
    mc = MetaCognition(agents)

    results = await mc._update_metrics()

    # second result should be an Exception instance
    assert isinstance(results[1], Exception)

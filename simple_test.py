"""
Simplified test to verify our three main features work
"""

import os
import sys

sys.path.insert(0, os.path.abspath('.'))

from unittest.mock import MagicMock

from symbolic_agi.agent_pool import DynamicAgentPool
from symbolic_agi.message_bus import MessageBus
from symbolic_agi.symbolic_memory import SymbolicMemory


def test_features_work():
    """Test that all three features work correctly."""
    print("Testing DynamicAgentPool Enhanced Features")
    print("=" * 50)

    # Setup
    mock_bus = MagicMock(spec=MessageBus)
    mock_skill_manager = MagicMock()
    mock_memory = MagicMock(spec=SymbolicMemory)

    pool = DynamicAgentPool(mock_bus, mock_skill_manager)

    # Test 1: Performance Analytics
    print("1. Testing Performance Analytics...")
    pool.add_agent("agent1", "coder", mock_memory)

    # Track performance
    pool.track_agent_performance("agent1", {"status": "success", "response_time": 1.5})
    pool.track_agent_performance("agent1", {"status": "failure", "response_time": 2.0})

    metrics = pool.agent_metrics["agent1"]
    assert metrics.total_tasks == 2
    assert metrics.successful_tasks == 1
    assert metrics.failed_tasks == 1
    assert metrics.success_rate == 50.0
    print("   CHECK Performance tracking works!")

    # Test 2: Intelligent Selection
    print("2. Testing Intelligent Selection...")
    pool.add_agent("good_agent", "coder", mock_memory)
    pool.add_agent("bad_agent", "coder", mock_memory)

    # Give different performance histories
    for _ in range(5):
        pool.track_agent_performance("good_agent", {"status": "success", "response_time": 1.0})
        pool.track_agent_performance("bad_agent", {"status": "failure", "response_time": 3.0})

    selected = pool.select_best_agent("coder")
    assert selected == "good_agent"
    print("   CHECK Intelligent selection works!")

    # Test 3: Dynamic Scaling
    print("3. Testing Dynamic Scaling...")
    pool.set_scaling_config("coder", min_agents=1, max_agents=5)
    pool.update_demand_metrics("coder", 10)

    demand = pool.persona_demand["coder"]
    assert demand.current_queue_length == 10
    print("   CHECK Demand tracking works!")

    # Test 4: Dashboard
    print("4. Testing Dashboard...")
    dashboard = pool.get_pool_status_dashboard()

    assert dashboard["total_agents"] == 3
    assert "coder" in dashboard["personas"]
    print("   CHECK Dashboard reporting works!")

    print("\nSUCCESS: All features working correctly!")
    print(f"Final agent count: {len(pool.subagents)}")

    # Show performance summary
    print("\nPerformance Summary:")
    for agent_name in ["agent1", "good_agent", "bad_agent"]:
        report = pool.get_agent_performance_report(agent_name)
        print(f"  {agent_name}: {report['success_rate']:.1f}% success, trust={report['trust_score']:.3f}")

if __name__ == "__main__":
    test_features_work()

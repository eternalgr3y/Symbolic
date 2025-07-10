"""
Quick validation of the new DynamicAgentPool features
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from unittest.mock import MagicMock
from symbolic_agi.agent_pool import DynamicAgentPool, AgentPerformanceMetrics
from symbolic_agi.message_bus import MessageBus
from symbolic_agi.symbolic_memory import SymbolicMemory

def test_new_features():
    """Quick test of the three new features."""
    print("🧪 Testing new DynamicAgentPool features...")
    
    # Setup
    mock_bus = MagicMock(spec=MessageBus)
    mock_skill_manager = MagicMock()
    mock_memory = MagicMock(spec=SymbolicMemory)
    
    pool = DynamicAgentPool(mock_bus, mock_skill_manager)
    print("✅ Created DynamicAgentPool")
    
    # Test Feature 1: Performance Analytics
    print("\n📊 Testing Performance Analytics...")
    pool.add_agent("test_agent", "coder", mock_memory)
    
    # Track a successful task
    task_result = {"status": "success", "response_time": 2.0, "task_type": "test"}
    pool.track_agent_performance("test_agent", task_result)
    
    metrics = pool.agent_metrics["test_agent"]
    assert metrics.total_tasks == 1
    assert metrics.successful_tasks == 1
    assert metrics.success_rate == 100.0
    print("✅ Performance tracking works")
    
    # Test Feature 2: Intelligent Selection
    print("\n🎯 Testing Intelligent Selection...")
    
    # Add more agents with different performance
    pool.add_agent("good_agent", "coder", mock_memory)
    pool.add_agent("poor_agent", "coder", mock_memory)
    
    # Give them different performance records
    for _ in range(5):
        pool.track_agent_performance("good_agent", {"status": "success", "response_time": 1.0})
        pool.track_agent_performance("poor_agent", {"status": "failure", "response_time": 3.0})
    
    # Select best agent
    selected = pool.select_best_agent("coder")
    print(f"Selected agent: {selected}")
    assert selected == "good_agent"  # Should select the best performer
    print("✅ Intelligent selection works")
    
    # Test Feature 3: Dynamic Scaling
    print("\n⚡ Testing Dynamic Scaling...")
    
    # Configure scaling
    pool.set_scaling_config("coder", min_agents=1, max_agents=5)
    
    # Update demand
    pool.update_demand_metrics("coder", 10)  # High demand
    
    demand = pool.persona_demand["coder"]
    assert demand.current_queue_length == 10
    print("✅ Demand tracking works")
    
    # Test dashboard
    print("\n📋 Testing Dashboard...")
    dashboard = pool.get_pool_status_dashboard()
    
    assert dashboard["total_agents"] == 3
    assert "coder" in dashboard["personas"]
    assert dashboard["personas"]["coder"]["agent_count"] == 3
    print("✅ Dashboard reporting works")
    
    print("\n🎉 All features working correctly!")
    
    # Show some stats
    print(f"\nFinal Statistics:")
    print(f"  Total agents: {len(pool.subagents)}")
    print(f"  Coder agents: {len(pool.get_agents_by_persona('coder'))}")
    
    for agent_name in ["test_agent", "good_agent", "poor_agent"]:
        report = pool.get_agent_performance_report(agent_name)
        print(f"  {agent_name}: {report['success_rate']:.1f}% success, trust={report['trust_score']:.3f}")

if __name__ == "__main__":
    test_new_features()
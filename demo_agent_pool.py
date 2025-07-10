"""
Demo script showcasing the new DynamicAgentPool features:
1. Agent Performance Analytics
2. Intelligent Agent Selection  
3. Dynamic Agent Scaling
"""

import asyncio
import time
import random
from unittest.mock import MagicMock

from symbolic_agi.agent_pool import DynamicAgentPool
from symbolic_agi.message_bus import MessageBus
from symbolic_agi.symbolic_memory import SymbolicMemory


async def demo_agent_pool_features():
    """Demonstrate all three new agent pool features."""
    print("ROCKET DynamicAgentPool Feature Demo\n" + "="*50)
    
    # Setup mocks
    mock_bus = MagicMock(spec=MessageBus)
    mock_skill_manager = MagicMock()
    mock_skill_manager.get_formatted_definitions.return_value = "Mock skills"
    
    # Create agent pool
    pool = DynamicAgentPool(mock_bus, mock_skill_manager)
    print("CHECK Created DynamicAgentPool with new features")
    
    # Create mock memories
    def create_mock_memory():
        return MagicMock(spec=SymbolicMemory)
    
    print("\nCHART FEATURE 1: PERFORMANCE ANALYTICS")
    print("-" * 40)
    
    # Add some agents
    for i in range(3):
        pool.add_agent(f"coder_{i}", "coder", create_mock_memory())
        pool.add_agent(f"writer_{i}", "writer", create_mock_memory())
    
    print(f"CHECK Added {len(pool.subagents)} agents across 2 personas")
    
    # Simulate different performance levels
    agents = list(pool.subagents.keys())
    for agent in agents:
        # Simulate task results with different success rates
        persona = pool.subagents[agent]["persona"]
        if "coder" in agent:
            success_rate = 0.8 if "0" in agent else 0.6 if "1" in agent else 0.4
        else:
            success_rate = 0.9 if "0" in agent else 0.7 if "1" in agent else 0.5
        
        # Generate task history
        for _ in range(20):
            success = random.random() < success_rate
            task_result = {
                "status": "success" if success else "failure",
                "response_time": random.uniform(1.0, 3.0),
                "task_type": f"{persona}_task"
            }
            pool.track_agent_performance(agent, task_result)
    
    print("✅ Simulated 20 tasks per agent with varying performance")
    
    # Show performance reports
    print("\n📈 Performance Reports:")
    for agent in agents[:3]:  # Show first 3 agents
        report = pool.get_agent_performance_report(agent)
        print(f"  {agent}: {report['success_rate']:.1f}% success, "
              f"trust={report['trust_score']:.3f}, "
              f"avg_time={report['average_response_time']:.2f}s")
    
    print("\n🎯 FEATURE 2: INTELLIGENT SELECTION")
    print("-" * 40)
    
    # Test intelligent selection
    for persona in ["coder", "writer"]:
        print(f"\nSelecting best {persona} agents:")
        for complexity in [0.3, 0.7, 1.0]:
            selected = pool.select_best_agent(persona, complexity)
            if selected:
                report = pool.get_agent_performance_report(selected)
                print(f"  Complexity {complexity}: {selected} "
                      f"(success: {report['success_rate']:.1f}%, "
                      f"trust: {report['trust_score']:.3f})")
    
    # Test workload management
    print("\n💼 Testing workload management:")
    best_coder = pool.select_best_agent("coder")
    print(f"  Best coder: {best_coder}")
    
    pool.mark_agent_busy(best_coder, True)
    print(f"  Marked {best_coder} as busy")
    
    next_best = pool.select_best_agent("coder")
    print(f"  Next best available: {next_best}")
    
    pool.mark_agent_busy(best_coder, False)
    print(f"  Marked {best_coder} as available again")
    
    print("\n⚡ FEATURE 3: DYNAMIC SCALING")
    print("-" * 40)
    
    # Configure scaling
    pool.set_scaling_config("coder", min_agents=2, max_agents=6)
    pool.set_scaling_config("writer", min_agents=1, max_agents=4)
    print("✅ Configured scaling limits")
    
    # Simulate demand changes
    demand_scenarios = [
        ("Low demand", {"coder": 1, "writer": 0}),
        ("Medium demand", {"coder": 4, "writer": 2}),
        ("High demand", {"coder": 10, "writer": 5}),
        ("Peak demand", {"coder": 15, "writer": 8}),
    ]
    
    for scenario_name, demands in demand_scenarios:
        print(f"\n📊 {scenario_name}:")
        
        # Update demand metrics
        for persona, queue_length in demands.items():
            pool.update_demand_metrics(persona, queue_length)
        
        # Get current agent counts
        before_counts = {
            persona: len(pool.get_agents_by_persona(persona))
            for persona in ["coder", "writer"]
        }
        
        # Trigger auto-scaling
        await pool.auto_scale_agents()
        
        # Get new agent counts
        after_counts = {
            persona: len(pool.get_agents_by_persona(persona))
            for persona in ["coder", "writer"]
        }
        
        for persona in ["coder", "writer"]:
            change = after_counts[persona] - before_counts[persona]
            queue_len = demands[persona]
            print(f"  {persona}: {before_counts[persona]} → {after_counts[persona]} agents "
                  f"(queue: {queue_len}, change: {change:+d})")
    
    print("\n📋 DASHBOARD REPORT")
    print("-" * 40)
    
    # Generate comprehensive dashboard
    dashboard = pool.get_pool_status_dashboard()
    print(f"Total Agents: {dashboard['total_agents']}")
    print(f"Total Personas: {dashboard['total_personas']}")
    print(f"Scaling Enabled: {dashboard['scaling_enabled']}")
    
    print("\nPer-Persona Statistics:")
    for persona, stats in dashboard["personas"].items():
        print(f"  {persona.upper()}:")
        print(f"    Agents: {stats['agent_count']} "
              f"(active: {stats['active_agents']}, busy: {stats['busy_agents']})")
        print(f"    Performance: {stats['average_success_rate']:.1f}% success rate")
        print(f"    Queue: {stats['current_queue_length']} current, "
              f"{stats['average_queue_length']:.1f} average")
        print(f"    Scaling: {stats['scaling_config']['min_agents']}-"
              f"{stats['scaling_config']['max_agents']} agents")
    
    print("\n🎉 Demo completed! All features working correctly.")
    print("\nKey Benefits Demonstrated:")
    print("✅ Automatic performance tracking and trust adjustment")
    print("✅ Intelligent agent selection based on multiple factors")
    print("✅ Dynamic scaling based on demand patterns")
    print("✅ Comprehensive monitoring and reporting")


if __name__ == "__main__":
    asyncio.run(demo_agent_pool_features())
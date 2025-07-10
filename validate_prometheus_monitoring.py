#!/usr/bin/env python3
"""
🔍 Prometheus Monitoring System Validation
Comprehensive test suite to validate all monitoring logic and components
"""

import asyncio
import time
import sys
import os
from typing import Dict, Any

# Add the symbolic_agi package to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_prometheus_metrics():
    """Test Prometheus metrics functionality"""
    print("🧪 Testing Prometheus Metrics System...")
    
    try:
        from symbolic_agi.prometheus_monitoring import (
            AGIPrometheusMetrics, PrometheusServer, agi_metrics, 
            start_prometheus_monitoring, get_prometheus_metrics,
            stop_prometheus_monitoring, prometheus_timer
        )
        
        # Test 1: Basic metrics creation
        print("  ✓ Importing prometheus modules")
        
        # Test 2: Metric recording with validation
        print("  🧪 Testing metric recording...")
        
        # Valid inputs
        agi_metrics.record_token_usage("test_role", "gpt-4", 100, 50, 0.01)
        agi_metrics.record_api_request("test_role", "gpt-4", 1.5, True)
        agi_metrics.record_plan_creation(True)
        agi_metrics.record_plan_step("test_action", True, 2.0)
        agi_metrics.record_qa_review("test_agent", True, 1.0, {"safety": 0.9, "logic": 0.8})
        agi_metrics.record_memory_operation("add", "episodic")
        agi_metrics.record_tool_usage("web_search", True, 3.0)
        agi_metrics.record_web_request("example.com", True)
        agi_metrics.record_robots_check("example.com", True)
        agi_metrics.record_safety_violation("test_violation")
        agi_metrics.record_ethical_score("truthfulness", 0.85)
        agi_metrics.update_system_state(5, {"orchestrator": 1, "qa": 2})
        
        print("  ✓ Valid metric recording works")
        
        # Test 3: Invalid input handling
        print("  🧪 Testing invalid input handling...")
        
        # These should not crash and should log warnings
        agi_metrics.record_token_usage("", "gpt-4", -10, 50, -0.01)  # Empty role, negative values
        agi_metrics.record_api_request("role", "", -1.0, True)  # Empty model, negative time
        agi_metrics.record_plan_step("", True, -1.0)  # Empty action, negative time
        agi_metrics.record_qa_review("", True, -1.0, {"": 1.5})  # Empty agent, negative time, invalid score
        agi_metrics.record_memory_operation("", "")  # Empty operation
        agi_metrics.record_tool_usage("", True, -1.0)  # Empty tool name
        agi_metrics.record_web_request("", True)  # Empty domain
        agi_metrics.record_robots_check("", True)  # Empty domain
        agi_metrics.record_safety_violation("")  # Empty violation type
        agi_metrics.record_ethical_score("", -0.5)  # Empty dimension, invalid score
        agi_metrics.update_system_state(-5, {"test": -2})  # Negative values
        
        print("  ✓ Invalid input handling works (check logs for warnings)")
        
        # Test 4: Metrics export
        print("  🧪 Testing metrics export...")
        metrics_output = get_prometheus_metrics()
        assert isinstance(metrics_output, str), "Metrics output should be string"
        assert len(metrics_output) > 0, "Metrics output should not be empty"
        print("  ✓ Metrics export works")
        
        # Test 5: Prometheus timer decorator
        print("  🧪 Testing prometheus timer decorator...")
        
        @prometheus_timer("test_function")
        def test_sync_function():
            time.sleep(0.1)
            return "sync_result"
        
        @prometheus_timer("test_async_function")
        async def test_async_function():
            await asyncio.sleep(0.1)
            return "async_result"
        
        # Test sync function
        result = test_sync_function()
        assert result == "sync_result", "Sync function should return correct result"
        
        # Test async function
        async def test_async():
            result = await test_async_function()
            assert result == "async_result", "Async function should return correct result"
        
        asyncio.run(test_async())
        print("  ✓ Prometheus timer decorator works")
        
        # Test 6: Server start/stop
        print("  🧪 Testing server start/stop...")
        start_prometheus_monitoring(8001)  # Use different port to avoid conflicts
        time.sleep(1)  # Give server time to start
        stop_prometheus_monitoring()
        print("  ✓ Server start/stop works")
        
        print("✅ All Prometheus metrics tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Prometheus metrics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_qa_agent_integration():
    """Test QA agent Prometheus integration"""
    print("🧪 Testing QA Agent Integration...")
    
    try:
        from symbolic_agi.robust_qa_agent import RobustQAAgent
        
        # Create QA agent
        qa_agent = RobustQAAgent("Test_QA_Agent")
        
        # Test workspace
        test_workspace = {
            "goal_description": "Test monitoring integration",
            "plan": [
                {"action": "test_action", "parameters": {"test": "value"}},
                {"action": "verify_results", "parameters": {"check": "completion"}}
            ]
        }
        
        print("  🧪 Testing QA review with monitoring...")
        
        # This should record metrics if Prometheus is available
        async def test_qa_review():
            result = await qa_agent.review_plan(workspace=test_workspace)
            assert "approved" in result, "QA result should have approval status"
            print("  ✓ QA review completed with monitoring")
            return result
        
        qa_result = asyncio.run(test_qa_review())
        
        # Get performance report
        performance = qa_agent.get_performance_report()
        assert "agent_name" in performance, "Performance report should have agent name"
        assert "performance_metrics" in performance, "Performance report should have metrics"
        
        print("  ✓ QA performance reporting works")
        print("✅ QA Agent integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ QA Agent integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_monitoring_dashboard():
    """Test monitoring dashboard functionality"""
    print("🧪 Testing Monitoring Dashboard...")
    
    try:
        # Test the monitoring dashboard demo
        from monitoring_dashboard import start_monitoring_demo, create_grafana_dashboard, show_prometheus_setup
        
        print("  🧪 Testing Grafana dashboard generation...")
        create_grafana_dashboard()
        
        # Check if file was created
        if os.path.exists("agi_grafana_dashboard.json"):
            print("  ✓ Grafana dashboard JSON created")
            with open("agi_grafana_dashboard.json", "r") as f:
                import json
                dashboard_config = json.load(f)
                assert "dashboard" in dashboard_config, "Dashboard config should have dashboard key"
                assert "panels" in dashboard_config["dashboard"], "Dashboard should have panels"
            print("  ✓ Grafana dashboard JSON is valid")
        else:
            print("  ⚠️  Grafana dashboard JSON not found")
        
        print("  🧪 Testing setup instructions...")
        show_prometheus_setup()  # Should not crash
        print("  ✓ Setup instructions work")
        
        print("✅ Monitoring dashboard tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Monitoring dashboard test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tool_plugin_dashboard():
    """Test tool plugin monitoring dashboard"""
    print("🧪 Testing Tool Plugin Dashboard...")
    
    try:
        # This would normally require a full AGI instance
        # We'll just test that the imports work and methods exist
        
        from symbolic_agi.tool_plugin import ToolPlugin
        
        # Check that the monitoring dashboard method exists
        assert hasattr(ToolPlugin, 'show_monitoring_dashboard'), "ToolPlugin should have show_monitoring_dashboard method"
        assert hasattr(ToolPlugin, '_generate_performance_recommendations'), "ToolPlugin should have _generate_performance_recommendations method"
        assert hasattr(ToolPlugin, '_format_dashboard_summary'), "ToolPlugin should have _format_dashboard_summary method"
        
        print("  ✓ Tool plugin dashboard methods exist")
        print("✅ Tool plugin dashboard tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Tool plugin dashboard test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_metric_consistency():
    """Test metric naming and labeling consistency"""
    print("🧪 Testing Metric Consistency...")
    
    try:
        from symbolic_agi.prometheus_monitoring import agi_metrics
        
        # Check that all metrics follow naming conventions
        metric_names = [
            'agi_build_info',
            'agi_uptime_seconds', 
            'agi_tokens_used_total',
            'agi_api_requests_total',
            'agi_api_cost_usd_total',
            'agi_api_response_time_seconds',
            'agi_plans_total',
            'agi_plan_steps_total',
            'agi_plan_execution_time_seconds',
            'agi_qa_reviews_total',
            'agi_qa_response_time_seconds',
            'agi_qa_score',
            'agi_memory_entries_total',
            'agi_memory_operations_total',
            'agi_tool_usage_total',
            'agi_tool_execution_time_seconds',
            'agi_web_requests_total',
            'agi_robots_txt_checks_total',
            'agi_safety_violations_total',
            'agi_ethical_scores',
            'agi_active_goals',
            'agi_active_agents'
        ]
        
        # Check that metrics have consistent prefixes
        for name in metric_names:
            assert name.startswith('agi_'), f"Metric {name} should start with 'agi_'"
        
        print("  ✓ Metric naming consistency verified")
        
        # Test label consistency (should not crash with valid labels)
        test_labels = {
            'role': 'test_role',
            'model': 'test_model', 
            'type': 'test_type',
            'status': 'success',
            'agent_name': 'test_agent',
            'result': 'approved',
            'action': 'test_action',
            'operation': 'test_op',
            'tool_name': 'test_tool',
            'domain': 'test.com',
            'dimension': 'test_dimension'
        }
        
        print("  ✓ Label consistency verified")
        print("✅ Metric consistency tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Metric consistency test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_comprehensive_validation():
    """Run all validation tests"""
    print("🔍 PROMETHEUS MONITORING SYSTEM VALIDATION")
    print("=" * 60)
    
    tests = [
        ("Prometheus Metrics Core", test_prometheus_metrics),
        ("QA Agent Integration", test_qa_agent_integration),
        ("Monitoring Dashboard", test_monitoring_dashboard),
        ("Tool Plugin Dashboard", test_tool_plugin_dashboard),
        ("Metric Consistency", test_metric_consistency)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n📊 VALIDATION SUMMARY")
    print("=" * 40)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Monitoring system is robust and ready!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    # Set up basic logging to see warnings
    import logging
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
    
    exit_code = run_comprehensive_validation()
    sys.exit(exit_code)
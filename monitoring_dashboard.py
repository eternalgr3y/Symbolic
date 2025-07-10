#!/usr/bin/env python3
"""
📊 AGI Monitoring Dashboard and Setup
Comprehensive monitoring, metrics, and observability for your AGI
"""

import asyncio
import json
import sys
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any

# Add the symbolic_agi package to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def start_monitoring_demo():
    """Start comprehensive monitoring demonstration"""
    print("📊 SYMBOLIC AGI - COMPREHENSIVE MONITORING")
    print("=" * 50)
    
    try:
        # Import and start Prometheus monitoring
        from symbolic_agi.prometheus_monitoring import start_prometheus_monitoring, agi_metrics, get_prometheus_metrics
        
        print("🚀 Starting Prometheus monitoring server...")
        start_prometheus_monitoring(port=8000)
        
        # Wait a moment for server to start
        await asyncio.sleep(2)
        
        print("✅ Prometheus server started on http://localhost:8000/metrics")
        print("\n🔍 AVAILABLE METRICS:")
        print("  • agi_tokens_used_total - Token consumption by role/model")
        print("  • agi_api_requests_total - API request count and status")
        print("  • agi_api_cost_usd_total - Total API costs")
        print("  • agi_plans_total - Plan creation and approval rates")
        print("  • agi_qa_reviews_total - QA review results")
        print("  • agi_tool_usage_total - Tool invocation statistics")
        print("  • agi_safety_violations_total - Safety incident tracking")
        print("  • agi_uptime_seconds - System uptime")
        print("  • agi_memory_entries_total - Memory storage stats")
        
        # Simulate some metrics
        print("\n🧪 Generating sample metrics...")
        
        try:
            # Simulate token usage
            agi_metrics.record_token_usage("orchestrator", "gpt-4", 150, 50, 0.012)
            agi_metrics.record_token_usage("qa", "gpt-4", 200, 75, 0.0165)
            
            # Simulate API requests
            agi_metrics.record_api_request("orchestrator", "gpt-4", 1.2, True)
            agi_metrics.record_api_request("qa", "gpt-4", 0.8, True)
            
            # Simulate QA reviews
            qa_scores = {
                "safety": 0.95,
                "logic": 0.87,
                "completeness": 0.92,
                "ethics": 0.89,
                "resources": 0.83,
                "overall": 0.89
            }
            agi_metrics.record_qa_review("QA_Agent_Alpha", True, 2.1, qa_scores)
            
            # Simulate plan creation
            agi_metrics.record_plan_creation(True)
            
            # Simulate tool usage
            agi_metrics.record_tool_usage("web_search", True, 3.2)
            agi_metrics.record_tool_usage("browse_webpage", True, 1.8)
            
            # Update system state
            agi_metrics.update_system_state(2, {"orchestrator": 1, "qa": 1, "specialist": 2})
            
            print("✅ Sample metrics generated")
        except Exception as e:
            print(f"⚠️  Failed to generate sample metrics: {e}")
            print("💡 This is normal if prometheus_client is not installed")
        
        # Now test with actual AGI if available
        print("\n🧠 Testing with actual AGI system...")
        
        try:
            from symbolic_agi.agi_controller import SymbolicAGI
            from symbolic_agi.robust_qa_agent import RobustQAAgent
            
            # Create robust QA agent
            qa_agent = RobustQAAgent("QA_Monitoring_Test")
            
            # Test QA review
            test_workspace = {
                "goal_description": "Test web search capabilities",
                "plan": [
                    {"action": "web_search", "parameters": {"query": "AI development news"}},
                    {"action": "analyze_data", "parameters": {"data": "{{web_search.results}}", "query": "What are the key trends?"}}
                ]
            }
            
            print("🔍 Testing QA agent with monitoring...")
            qa_result = await qa_agent.review_plan(workspace=test_workspace)
            
            print(f"✅ QA Review completed: {qa_result.get('approved', False)}")
            print(f"📊 Overall score: {qa_result.get('overall_score', 'N/A')}")
            
            # Get performance report
            performance = qa_agent.get_performance_report()
            print(f"📈 QA Performance: {performance['approval_rate']:.1%} approval rate")
            
        except Exception as e:
            print(f"⚠️  AGI system test failed: {e}")
            print("💡 This is normal if AGI is not fully configured")
        
        print("\n📊 CURRENT METRICS SNAPSHOT:")
        print("=" * 40)
        
        # Show some current metrics
        try:
            # Get partial metrics as text (Prometheus format is binary)
            print("🔢 Token Usage:")
            print(f"  • Total API requests: Tracked per role/model")
            print(f"  • Response times: Histogram with percentiles")
            print(f"  • Costs: Running total in USD")
            
            print("\n🛡️ Safety & Quality:")
            print(f"  • QA reviews: Success/failure rates")
            print(f"  • Safety violations: Count by type")
            print(f"  • Ethical scores: Distribution tracking")
            
            print("\n⚡ Performance:")
            print(f"  • Tool execution times: Histogram")
            print(f"  • Memory operations: Count by operation")
            print(f"  • System uptime: Current session time")
            
        except Exception as e:
            print(f"Could not display metrics: {e}")
        
        print(f"\n🌐 MONITORING ENDPOINTS:")
        print("  • Prometheus: http://localhost:8000/metrics")
        print("  • Grafana setup: Import AGI dashboard")
        print("  • Alerting: Configure for safety violations")
        
        print(f"\n⏰ Monitoring server will run in background...")
        print("Press Ctrl+C to stop")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(10)
                # Update uptime
                agi_metrics.update_system_state(2, {"orchestrator": 1, "qa": 1})
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped")
            
    except Exception as e:
        print(f"❌ Monitoring demo failed: {e}")
        print("💡 Make sure prometheus_client is installed: pip install prometheus_client")

def create_grafana_dashboard():
    """Create Grafana dashboard configuration for AGI monitoring"""
    dashboard = {
        "dashboard": {
            "title": "Symbolic AGI Monitoring",
            "tags": ["agi", "ai", "monitoring"],
            "timezone": "browser",
            "panels": [
                {
                    "title": "API Requests Rate",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "rate(agi_api_requests_total[5m])",
                            "legendFormat": "{{role}} - {{model}}"
                        }
                    ]
                },
                {
                    "title": "Token Usage Over Time", 
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "rate(agi_tokens_used_total[1m])",
                            "legendFormat": "{{role}} - {{type}}"
                        }
                    ]
                },
                {
                    "title": "QA Approval Rate",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "rate(agi_qa_reviews_total{result='approved'}[5m]) / rate(agi_qa_reviews_total[5m]) * 100",
                            "legendFormat": "Approval %"
                        }
                    ]
                },
                {
                    "title": "Safety Violations",
                    "type": "stat", 
                    "targets": [
                        {
                            "expr": "increase(agi_safety_violations_total[1h])",
                            "legendFormat": "{{type}}"
                        }
                    ]
                },
                {
                    "title": "API Response Times",
                    "type": "heatmap",
                    "targets": [
                        {
                            "expr": "rate(agi_api_response_time_seconds_bucket[5m])",
                            "legendFormat": "{{le}}"
                        }
                    ]
                },
                {
                    "title": "Tool Usage Distribution",
                    "type": "pie",
                    "targets": [
                        {
                            "expr": "sum by (tool_name) (agi_tool_usage_total)",
                            "legendFormat": "{{tool_name}}"
                        }
                    ]
                },
                {
                    "title": "System Uptime",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "agi_uptime_seconds",
                            "legendFormat": "Uptime"
                        }
                    ]
                },
                {
                    "title": "Memory Operations Rate",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "rate(agi_memory_operations_total[5m])",
                            "legendFormat": "{{operation}}"
                        }
                    ]
                }
            ]
        }
    }
    
    with open("agi_grafana_dashboard.json", "w") as f:
        json.dump(dashboard, f, indent=2)
    
    print("📊 Grafana dashboard configuration saved to: agi_grafana_dashboard.json")
    print("💡 Import this file into Grafana to visualize AGI metrics")

def show_prometheus_setup():
    """Show Prometheus setup instructions"""
    print("🔧 PROMETHEUS SETUP GUIDE")
    print("=" * 30)
    
    prometheus_config = """
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'symbolic-agi'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 10s
    metrics_path: /metrics
"""
    
    print("1. Install Prometheus:")
    print("   • Download from: https://prometheus.io/download/")
    print("   • Or use Docker: docker run -p 9090:9090 prom/prometheus")
    
    print("\n2. Configure Prometheus (prometheus.yml):")
    print(prometheus_config)
    
    print("3. Install Grafana:")
    print("   • Download from: https://grafana.com/get")
    print("   • Or use Docker: docker run -p 3000:3000 grafana/grafana")
    
    print("\n4. Setup Grafana:")
    print("   • Add Prometheus data source: http://localhost:9090")
    print("   • Import AGI dashboard: agi_grafana_dashboard.json")
    
    print("\n5. Key AGI Metrics to Monitor:")
    print("   • Token usage and costs")
    print("   • QA approval rates")
    print("   • Safety violations")
    print("   • API response times")
    print("   • Tool performance")
    print("   • System uptime")

if __name__ == "__main__":
    print("📊 SYMBOLIC AGI - MONITORING SETUP")
    print("Choose an option:")
    print("1. Start live monitoring demo")
    print("2. Generate Grafana dashboard config")
    print("3. Show Prometheus setup guide")
    print("4. Exit")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        asyncio.run(start_monitoring_demo())
    elif choice == "2":
        create_grafana_dashboard()
    elif choice == "3":
        show_prometheus_setup()
    else:
        print("👋 Goodbye!")
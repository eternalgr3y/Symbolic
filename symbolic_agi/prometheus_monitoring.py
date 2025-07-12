#!/usr/bin/env python3
"""
🔍 Prometheus Metrics Integration for Symbolic AGI
Professional-grade monitoring and observability
"""

from prometheus_client import (
    Counter, Histogram, Gauge, Info, Summary,
    CollectorRegistry, generate_latest, start_http_server,
    CONTENT_TYPE_LATEST
)
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from functools import wraps
import asyncio
import threading

class AGIPrometheusMetrics:
    """
    Comprehensive Prometheus metrics for AGI monitoring
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self._setup_metrics()
        self.start_time = time.time()
        
    def _setup_metrics(self):
        """Initialize all AGI metrics"""
        
        # === CORE AGI METRICS ===
        self.agi_info = Info(
            'agi_build_info', 
            'AGI system information',
            registry=self.registry
        )
        
        self.agi_uptime = Gauge(
            'agi_uptime_seconds',
            'AGI system uptime in seconds',
            registry=self.registry
        )
        
        # === TOKEN USAGE METRICS ===
        self.token_usage_total = Counter(
            'agi_tokens_used_total',
            'Total tokens consumed',
            ['role', 'model', 'type'],  # type: prompt/completion
            registry=self.registry
        )
        
        self.api_requests_total = Counter(
            'agi_api_requests_total',
            'Total API requests made',
            ['role', 'model', 'status'],  # status: success/error
            registry=self.registry
        )
        
        self.api_cost_total = Counter(
            'agi_api_cost_usd_total',
            'Total API cost in USD',
            ['role', 'model'],
            registry=self.registry
        )
        
        self.api_response_time = Histogram(
            'agi_api_response_time_seconds',
            'API response time distribution',
            ['role', 'model'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        # === PLAN EXECUTION METRICS ===
        self.plans_total = Counter(
            'agi_plans_total',
            'Total plans created',
            ['status'],  # approved/rejected
            registry=self.registry
        )
        
        self.plan_steps_total = Counter(
            'agi_plan_steps_total',
            'Total plan steps executed',
            ['action', 'status'],  # success/failure
            registry=self.registry
        )
        
        self.plan_execution_time = Histogram(
            'agi_plan_execution_time_seconds',
            'Plan execution time distribution',
            buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0],
            registry=self.registry
        )
        
        # === QA AGENT METRICS ===
        self.qa_reviews_total = Counter(
            'agi_qa_reviews_total',
            'Total QA reviews performed',
            ['agent_name', 'result'],  # approved/rejected
            registry=self.registry
        )
        
        self.qa_response_time = Histogram(
            'agi_qa_response_time_seconds',
            'QA agent response time',
            ['agent_name'],
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
            registry=self.registry
        )
        
        self.qa_score = Histogram(
            'agi_qa_score',
            'QA evaluation scores',
            ['agent_name', 'dimension'],  # safety, logic, ethics, etc.
            buckets=[0.0, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )
        
        # === MEMORY METRICS ===
        self.memory_entries_total = Gauge(
            'agi_memory_entries_total',
            'Total memory entries stored',
            ['type'],  # episodic, semantic, meta_insight
            registry=self.registry
        )
        
        self.memory_operations_total = Counter(
            'agi_memory_operations_total',
            'Total memory operations',
            ['operation'],  # add, retrieve, consolidate
            registry=self.registry
        )
        
        # === TOOL USAGE METRICS ===
        self.tool_usage_total = Counter(
            'agi_tool_usage_total',
            'Total tool invocations',
            ['tool_name', 'status'],
            registry=self.registry
        )
        
        self.tool_execution_time = Histogram(
            'agi_tool_execution_time_seconds',
            'Tool execution time distribution',
            ['tool_name'],
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        # === WEB ACCESS METRICS ===
        self.web_requests_total = Counter(
            'agi_web_requests_total',
            'Total web requests made',
            ['domain', 'status'],  # allowed/blocked
            registry=self.registry
        )
        
        self.robots_txt_checks = Counter(
            'agi_robots_txt_checks_total',
            'Robots.txt compliance checks',
            ['domain', 'result'],  # allowed/blocked
            registry=self.registry
        )
        
        # === SAFETY METRICS ===
        self.safety_violations_total = Counter(
            'agi_safety_violations_total',
            'Total safety violations detected',
            ['type'],  # pattern_violation, resource_limit, etc.
            registry=self.registry
        )
        
        self.ethical_scores = Histogram(
            'agi_ethical_scores',
            'Ethical evaluation scores',
            ['dimension'],  # truthfulness, harm_avoidance, etc.
            buckets=[0.0, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )
        
        # === SYSTEM PERFORMANCE ===
        self.active_goals = Gauge(
            'agi_active_goals',
            'Number of active goals',
            registry=self.registry
        )
        
        self.agent_count = Gauge(
            'agi_active_agents',
            'Number of active agents',
            ['type'],  # orchestrator, qa, specialist
            registry=self.registry
        )
        
        # Set initial system info
        self.agi_info.info({
            'version': '1.0.0',
            'python_version': '3.12',
            'start_time': datetime.now(timezone.utc).isoformat()
        })

    def record_token_usage(self, role: str, model: str, prompt_tokens: int, 
                          completion_tokens: int, cost: float):
        """Record token usage metrics"""
        self.token_usage_total.labels(role=role, model=model, type='prompt').inc(prompt_tokens)
        self.token_usage_total.labels(role=role, model=model, type='completion').inc(completion_tokens)
        self.api_cost_total.labels(role=role, model=model).inc(cost)
    
    def record_api_request(self, role: str, model: str, response_time: float, success: bool):
        """Record API request metrics"""
        status = 'success' if success else 'error'
        self.api_requests_total.labels(role=role, model=model, status=status).inc()
        self.api_response_time.labels(role=role, model=model).observe(response_time)
    
    def record_plan_creation(self, approved: bool):
        """Record plan creation metrics"""
        status = 'approved' if approved else 'rejected'
        self.plans_total.labels(status=status).inc()
    
    def record_plan_step(self, action: str, success: bool, execution_time: float):
        """Record plan step execution"""
        status = 'success' if success else 'failure'
        self.plan_steps_total.labels(action=action, status=status).inc()
        self.plan_execution_time.observe(execution_time)
    
    def record_qa_review(self, agent_name: str, approved: bool, response_time: float, 
                        scores: Dict[str, float]):
        """Record QA review metrics"""
        result = 'approved' if approved else 'rejected'
        self.qa_reviews_total.labels(agent_name=agent_name, result=result).inc()
        self.qa_response_time.labels(agent_name=agent_name).observe(response_time)
        
        # Record individual dimension scores
        for dimension, score in scores.items():
            self.qa_score.labels(agent_name=agent_name, dimension=dimension).observe(score)
    
    def record_memory_operation(self, operation: str, entry_type: str = ""):
        """Record memory operations"""
        self.memory_operations_total.labels(operation=operation).inc()
        if entry_type and operation == 'add':
            self.memory_entries_total.labels(type=entry_type).inc()
    
    def record_tool_usage(self, tool_name: str, success: bool, execution_time: float):
        """Record tool usage metrics"""
        status = 'success' if success else 'failure'
        self.tool_usage_total.labels(tool_name=tool_name, status=status).inc()
        self.tool_execution_time.labels(tool_name=tool_name).observe(execution_time)
    
    def record_web_request(self, domain: str, allowed: bool):
        """Record web access metrics"""
        status = 'allowed' if allowed else 'blocked'
        self.web_requests_total.labels(domain=domain, status=status).inc()
    
    def record_robots_check(self, domain: str, allowed: bool):
        """Record robots.txt compliance checks"""
        result = 'allowed' if allowed else 'blocked'
        self.robots_txt_checks.labels(domain=domain, result=result).inc()
    
    def record_safety_violation(self, violation_type: str):
        """Record safety violations"""
        self.safety_violations_total.labels(type=violation_type).inc()
    
    def record_ethical_score(self, dimension: str, score: float):
        """Record ethical evaluation scores"""
        self.ethical_scores.labels(dimension=dimension).observe(score)
    
    def update_system_state(self, active_goals: int, agent_counts: Dict[str, int]):
        """Update system state metrics"""
        self.active_goals.set(active_goals)
        for agent_type, count in agent_counts.items():
            self.agent_count.labels(type=agent_type).set(count)
        
        # Update uptime
        self.agi_uptime.set(time.time() - self.start_time)
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format"""
        return generate_latest(self.registry)

class PrometheusServer:
    """
    Prometheus metrics HTTP server for AGI monitoring
    """
    
    def __init__(self, metrics: AGIPrometheusMetrics, port: int = 8000):
        self.metrics = metrics
        self.port = port
        self.server_thread = None
        
    def start_server(self):
        """Start Prometheus metrics server"""
        def run_server():
            start_http_server(self.port, registry=self.metrics.registry)
            logging.info(f"🔍 Prometheus metrics server started on port {self.port}")
            logging.info(f"📊 Metrics available at: http://localhost:{self.port}/metrics")
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

def prometheus_timer(metric_name: str):
    """Decorator to time function execution for Prometheus"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                # Record success metric
                if hasattr(func, '_prometheus_metrics'):
                    func._prometheus_metrics.observe(execution_time)
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                # Record failure metric
                raise e
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                # Record success metric
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                # Record failure metric
                raise e
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator

# Global metrics instance
agi_metrics = AGIPrometheusMetrics()
prometheus_server = PrometheusServer(agi_metrics)

def start_prometheus_monitoring(port: int = 8000):
    """Start Prometheus monitoring server"""
    prometheus_server.port = port
    prometheus_server.start_server()
    
    # Log startup info
    logging.info("🚀 AGI Prometheus Monitoring Started")
    logging.info(f"📊 Metrics: http://localhost:{port}/metrics")
    logging.info("🔍 Key metrics being tracked:")
    logging.info("  • Token usage and API costs")
    logging.info("  • Plan execution and QA reviews") 
    logging.info("  • Tool usage and performance")
    logging.info("  • Memory operations")
    logging.info("  • Web access and safety compliance")
    logging.info("  • System performance and uptime")

def get_prometheus_metrics() -> str:
    """Get current metrics in Prometheus format"""
    return agi_metrics.get_metrics()

# Export the global metrics instance for use in other modules
__all__ = ['agi_metrics', 'start_prometheus_monitoring', 'get_prometheus_metrics', 'prometheus_timer']
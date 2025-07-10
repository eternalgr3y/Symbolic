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
import asyncio
import threading
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone
from functools import wraps

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
        # Validate inputs
        if not role or not model:
            logging.warning(f"Empty role or model: role='{role}', model='{model}', skipping metric")
            return
            
        if prompt_tokens < 0 or completion_tokens < 0:
            logging.warning(f"Negative token counts: prompt={prompt_tokens}, completion={completion_tokens}")
            prompt_tokens = max(0, prompt_tokens)
            completion_tokens = max(0, completion_tokens)
            
        if cost < 0:
            logging.warning(f"Negative cost: {cost}, clamping to 0")
            cost = max(0, cost)
            
        self.token_usage_total.labels(role=role, model=model, type='prompt').inc(prompt_tokens)
        self.token_usage_total.labels(role=role, model=model, type='completion').inc(completion_tokens)
        self.api_cost_total.labels(role=role, model=model).inc(cost)
    
    def record_api_request(self, role: str, model: str, response_time: float, success: bool):
        """Record API request metrics"""
        # Validate inputs
        if not role or not model:
            logging.warning(f"Empty role or model: role='{role}', model='{model}', skipping metric")
            return
            
        if response_time < 0:
            logging.warning(f"Negative response time: {response_time}, clamping to 0")
            response_time = max(0, response_time)
            
        status = 'success' if success else 'error'
        self.api_requests_total.labels(role=role, model=model, status=status).inc()
        self.api_response_time.labels(role=role, model=model).observe(response_time)
    
    def record_plan_creation(self, approved: bool):
        """Record plan creation metrics"""
        status = 'approved' if approved else 'rejected'
        self.plans_total.labels(status=status).inc()
    
    def record_plan_step(self, action: str, success: bool, execution_time: float):
        """Record plan step execution"""
        if not action:
            logging.warning("Empty action name, skipping metric recording")
            return
            
        if execution_time < 0:
            logging.warning(f"Negative execution time: {execution_time}, clamping to 0")
            execution_time = max(0, execution_time)
            
        status = 'success' if success else 'failure'
        self.plan_steps_total.labels(action=action, status=status).inc()
        self.plan_execution_time.observe(execution_time)
    
    def record_qa_review(self, agent_name: str, approved: bool, response_time: float, 
                        scores: Dict[str, float]):
        """Record QA review metrics"""
        if not agent_name:
            logging.warning("Empty agent name, skipping QA metric recording")
            return
            
        if response_time < 0:
            logging.warning(f"Negative response time: {response_time}, clamping to 0")
            response_time = max(0, response_time)
            
        result = 'approved' if approved else 'rejected'
        self.qa_reviews_total.labels(agent_name=agent_name, result=result).inc()
        self.qa_response_time.labels(agent_name=agent_name).observe(response_time)
        
        # Record individual dimension scores with validation
        if scores:
            for dimension, score in scores.items():
                if dimension:  # Only record non-empty dimensions
                    # Clamp score to valid range
                    score = max(0.0, min(1.0, float(score)))
                    self.qa_score.labels(agent_name=agent_name, dimension=dimension).observe(score)
    
    def record_memory_operation(self, operation: str, entry_type: str = ""):
        """Record memory operations"""
        if not operation:
            logging.warning("Empty operation name, skipping memory metric recording")
            return
            
        self.memory_operations_total.labels(operation=operation).inc()
        if entry_type and operation == 'add':
            self.memory_entries_total.labels(type=entry_type).inc()
    
    def record_tool_usage(self, tool_name: str, success: bool, execution_time: float):
        """Record tool usage metrics"""
        if not tool_name:  # Validate input
            logging.warning("Tool name is empty, skipping metric recording")
            return
            
        status = 'success' if success else 'failure'
        self.tool_usage_total.labels(tool_name=tool_name, status=status).inc()
        self.tool_execution_time.labels(tool_name=tool_name).observe(execution_time)
    
    def record_web_request(self, domain: str, allowed: bool):
        """Record web access metrics"""
        if not domain:  # Validate input
            logging.warning("Domain is empty, skipping metric recording")
            return
            
        status = 'allowed' if allowed else 'blocked'
        self.web_requests_total.labels(domain=domain, status=status).inc()
    
    def record_robots_check(self, domain: str, allowed: bool):
        """Record robots.txt compliance checks"""
        if not domain:  # Validate input
            logging.warning("Domain is empty, skipping metric recording")
            return
            
        result = 'allowed' if allowed else 'blocked'
        self.robots_txt_checks.labels(domain=domain, result=result).inc()
    
    def record_safety_violation(self, violation_type: str):
        """Record safety violations"""
        if not violation_type:  # Validate input
            logging.warning("Violation type is empty, skipping metric recording")
            return
            
        self.safety_violations_total.labels(type=violation_type).inc()
    
    def record_ethical_score(self, dimension: str, score: float):
        """Record ethical evaluation scores"""
        if not dimension:  # Validate input
            logging.warning("Dimension is empty, skipping metric recording")
            return
            
        # Clamp score to valid range
        score = max(0.0, min(1.0, score))
        self.ethical_scores.labels(dimension=dimension).observe(score)
    
    def update_system_state(self, active_goals: int, agent_counts: Dict[str, int]):
        """Update system state metrics"""
        # Validate inputs
        if active_goals < 0:
            logging.warning(f"Negative active_goals value: {active_goals}, clamping to 0")
            active_goals = 0
            
        self.active_goals.set(active_goals)
        
        if agent_counts:
            for agent_type, count in agent_counts.items():
                if count < 0:
                    logging.warning(f"Negative agent count for {agent_type}: {count}, clamping to 0")
                    count = 0
                self.agent_count.labels(type=agent_type).set(count)
        
        # Update uptime
        uptime = time.time() - self.start_time
        self.agi_uptime.set(uptime)
    
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
        self.is_running = False
        
    def start_server(self):
        """Start Prometheus metrics server"""
        if self.is_running:
            logging.warning("Prometheus server is already running")
            return
            
        def run_server():
            try:
                start_http_server(self.port, registry=self.metrics.registry)
                self.is_running = True
                logging.info(f"🔍 Prometheus metrics server started on port {self.port}")
                logging.info(f"📊 Metrics available at: http://localhost:{self.port}/metrics")
            except Exception as e:
                logging.error(f"Failed to start Prometheus server: {e}")
                self.is_running = False
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
    
    def stop_server(self):
        """Stop the Prometheus server (note: actual HTTP server can't be easily stopped)"""
        self.is_running = False
        logging.info("Prometheus server marked for shutdown")

def prometheus_timer(metric_name: str):
    """Decorator to time function execution for Prometheus"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            try:
                result = await func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                success = False
                raise e
            finally:
                execution_time = time.time() - start_time
                # Try to record metric if global metrics instance is available
                try:
                    if hasattr(agi_metrics, 'tool_execution_time'):
                        # Use tool_execution_time as a generic timing metric
                        agi_metrics.tool_execution_time.labels(tool_name=metric_name).observe(execution_time)
                        agi_metrics.tool_usage_total.labels(tool_name=metric_name, 
                                                           status='success' if success else 'failure').inc()
                except Exception as metric_error:
                    logging.warning(f"Failed to record prometheus timer metric: {metric_error}")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                success = False
                raise e
            finally:
                execution_time = time.time() - start_time
                # Try to record metric if global metrics instance is available
                try:
                    if hasattr(agi_metrics, 'tool_execution_time'):
                        agi_metrics.tool_execution_time.labels(tool_name=metric_name).observe(execution_time)
                        agi_metrics.tool_usage_total.labels(tool_name=metric_name, 
                                                           status='success' if success else 'failure').inc()
                except Exception as metric_error:
                    logging.warning(f"Failed to record prometheus timer metric: {metric_error}")
        
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
    global prometheus_server
    
    # Validate port
    if not (1024 <= port <= 65535):
        logging.warning(f"Invalid port {port}, using default 8000")
        port = 8000
    
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
    try:
        return agi_metrics.get_metrics()
    except Exception as e:
        logging.error(f"Failed to get Prometheus metrics: {e}")
        return f"# Error getting metrics: {e}\n"

def stop_prometheus_monitoring():
    """Stop Prometheus monitoring server"""
    # Note: prometheus_client doesn't provide a direct way to stop the server
    # This is a placeholder for graceful shutdown
    logging.info("🛑 Prometheus monitoring stop requested")
    logging.info("💡 Note: Prometheus HTTP server will stop when main process exits")
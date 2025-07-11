import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .schemas import MemoryEntryModel, MemoryType, MetaEventModel

if TYPE_CHECKING:
    from .agi_controller import SymbolicAGI

class MetaCognitionUnit:
    """Monitors and optimizes the AGI's cognitive processes."""
    
    def __init__(self, agi: "SymbolicAGI"):
        self.agi = agi
        self._monitoring_task: Optional[asyncio.Task] = None
        self._optimization_task: Optional[asyncio.Task] = None
        self.performance_metrics: Dict[str, float] = {
            "goal_success_rate": 0.0,
            "average_goal_time": 0.0,
            "energy_efficiency": 1.0,
            "memory_utilization": 0.0
        }
        self.meta_insights: List[str] = []

    async def run_background_tasks(self) -> None:
        """Start meta-cognition background tasks."""
        self._monitoring_task = asyncio.create_task(self._monitor_performance())
        self._optimization_task = asyncio.create_task(self._optimize_processes())
        
        # Wait for both tasks to complete
        await asyncio.gather(self._monitoring_task, self._optimization_task, return_exceptions=True)

    async def _monitor_performance(self) -> None:
        """Monitor AGI performance metrics."""
        while not self.agi.shutdown_event.is_set():
            try:
                # Calculate performance metrics
                await self._update_metrics()
                
                # Check for anomalies
                anomalies = self._detect_anomalies()
                if anomalies:
                    for anomaly in anomalies:
                        await self._handle_anomaly(anomaly)
                        
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logging.error(f"[MetaCognition] Monitoring error: {e}")
                await asyncio.sleep(60)

    async def _optimize_processes(self) -> None:
        """Optimize cognitive processes based on performance."""
        while not self.agi.shutdown_event.is_set():
            try:
                # Run optimization cycle
                await asyncio.sleep(300)  # Every 5 minutes
                
                insights = self._generate_optimization_insights()
                if insights:
                    self.meta_insights.extend(insights)
                    
                    # Apply optimizations
                    await self._apply_optimizations(insights)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logging.error(f"[MetaCognition] Optimization error: {e}")
                await asyncio.sleep(600)
                

    async def _update_metrics(self) -> None:
        """Update performance metrics."""
        try:
            # Goal success rate
            completed_goals = await self.agi.goal_manager.get_completed_goals()
            failed_goals = await self.agi.goal_manager.get_failed_goals()
            total_finished = len(completed_goals) + len(failed_goals)
            
            if total_finished > 0:
                self.performance_metrics["goal_success_rate"] = len(completed_goals) / total_finished
                
            # Memory utilization
            total_memories = await self.agi.memory.get_total_memory_count()
            self.performance_metrics["memory_utilization"] = min(1.0, total_memories / 10000)
            
            # Energy efficiency
            energy_ratio = self.agi.identity.cognitive_energy / self.agi.identity.max_energy
            self.performance_metrics["energy_efficiency"] = energy_ratio
            
        except Exception as e:
            logging.error(f"[MetaCognition] Metrics update error: {e}")


    def _detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect performance anomalies."""
        anomalies = []
        
        # Low success rate
        if self.performance_metrics["goal_success_rate"] < 0.3:
            anomalies.append({
                "type": "low_success_rate",
                "value": self.performance_metrics["goal_success_rate"],
                "threshold": 0.3
            })
            
        # Low energy
        if self.performance_metrics["energy_efficiency"] < 0.2:
            anomalies.append({
                "type": "low_energy",
                "value": self.performance_metrics["energy_efficiency"],
                "threshold": 0.2
            })
            
        # High memory usage
        if self.performance_metrics["memory_utilization"] > 0.9:
            anomalies.append({
                "type": "high_memory_usage",
                "value": self.performance_metrics["memory_utilization"],
                "threshold": 0.9
            })
            
        return anomalies

    async def _handle_anomaly(self, anomaly: Dict[str, Any]) -> None:
        """Handle detected anomalies."""
        logging.warning(f"[MetaCognition] Anomaly detected: {anomaly}")
        
        # Create memory of anomaly
        memory = MemoryEntryModel(
            type=MemoryType.REFLECTION,
            content={
                "event": "anomaly_detected",
                "anomaly": anomaly,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            importance=0.8
        )
        await self.agi.memory.add_memory(memory)
        
        # Take corrective action
        if anomaly["type"] == "low_energy":
            # Trigger energy recovery
            self.agi.identity.recover_energy(20)
            logging.info("[MetaCognition] Triggered energy recovery")
            
        elif anomaly["type"] == "high_memory_usage":
            # Could trigger memory consolidation
            logging.info("[MetaCognition] High memory usage detected")

    def _generate_optimization_insights(self) -> List[str]:
        """Generate insights for process optimization."""
        insights = []
        
        # Analyze recent performance
        if self.performance_metrics["goal_success_rate"] < 0.5:
            insights.append("Goal success rate is low - consider adjusting planning strategies")
            
        if self.performance_metrics["energy_efficiency"] < 0.5:
            insights.append("Energy efficiency is low - reduce concurrent operations")
            
        return insights

    async def _apply_optimizations(self, insights: List[str]) -> None:
        """Apply optimizations based on insights."""
        for insight in insights:
            logging.info(f"[MetaCognition] Applying optimization: {insight}")
            
            # Create memory of optimization
            memory = MemoryEntryModel(
                type=MemoryType.REFLECTION,
                content={
                    "event": "optimization_applied",
                    "insight": insight,
                    "metrics": self.performance_metrics.copy()
                },
                importance=0.6
            )
            await self.agi.memory.add_memory(memory)

    def get_status(self) -> Dict[str, Any]:
        """Get meta-cognition status."""
        return {
            "performance_metrics": self.performance_metrics,
            "recent_insights": self.meta_insights[-5:],
            "monitoring_active": self._monitoring_task is not None and not self._monitoring_task.done(),
            "optimization_active": self._optimization_task is not None and not self._optimization_task.done()
        }
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .api_client import monitored_chat_completion

class RobustQAAgent:
    """
    ROBUST Quality Assurance Agent with comprehensive validation capabilities.
    Ensures all plans meet quality, safety, and logical consistency standards.
    """
    
    def __init__(self, name: str = "QA_Agent_Alpha"):
        self.name = name
        self.evaluation_count = 0
        self.approval_rate = 0.0
        self.rejected_plans: List[Dict[str, Any]] = []
        self.performance_metrics = {
            "total_evaluations": 0,
            "approvals": 0,
            "rejections": 0,
            "avg_response_time": 0.0
        }
    
    async def review_plan(self, **kwargs: Any) -> Dict[str, Any]:
        """
        COMPREHENSIVE plan review with multiple validation layers.
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            workspace = kwargs.get("workspace", {})
            goal_description = workspace.get("goal_description", "unknown goal")
            plan_steps = workspace.get("plan", [])
            
            logging.info(f"QA Agent {self.name}: Reviewing plan for '{goal_description}'")
            
            # Layer 1: Safety Analysis
            safety_result = await self._analyze_safety(goal_description, plan_steps)
            if not safety_result["safe"]:
                return self._create_rejection_response(
                    "Safety violation detected", 
                    safety_result["issues"]
                )
            
            # Layer 2: Logical Consistency
            logic_result = await self._analyze_logical_consistency(plan_steps)
            if logic_result["score"] < 0.6:
                return self._create_rejection_response(
                    "Poor logical consistency",
                    [f"Logic score: {logic_result['score']:.2f}"]
                )
            
            # Layer 3: Resource Efficiency
            resource_result = self._analyze_resource_efficiency(plan_steps)
            if not resource_result["efficient"]:
                logging.warning(f"QA: Resource efficiency concerns: {resource_result['warnings']}")
            
            # Layer 4: Completeness Check
            completeness_result = self._analyze_plan_completeness(goal_description, plan_steps)
            
            # Layer 5: Ethical Review
            ethical_result = await self._analyze_ethical_implications(goal_description, plan_steps)
            
            # Compile comprehensive assessment
            overall_score = self._calculate_overall_score(
                safety_result, logic_result, resource_result, 
                completeness_result, ethical_result
            )
            
            # Record performance metrics
            end_time = datetime.now(timezone.utc)
            response_time = (end_time - start_time).total_seconds()
            approved = overall_score >= 0.7
            self._update_metrics(approved=approved, response_time=response_time)
            
            # Record Prometheus metrics
            try:
                from .prometheus_monitoring import agi_metrics
                scores_dict = {
                    "safety": safety_result.get("score", 0.5),
                    "logic": logic_result.get("score", 0.5),
                    "completeness": completeness_result.get("score", 0.5),
                    "ethics": ethical_result.get("score", 0.5),
                    "resources": resource_result.get("score", 0.5),
                    "overall": overall_score
                }
                agi_metrics.record_qa_review(self.name, approved, response_time, scores_dict)
                agi_metrics.record_plan_creation(approved)
            except ImportError:
                pass  # Prometheus not available
            
            if overall_score >= 0.7:
                return self._create_approval_response(overall_score, {
                    "safety": safety_result,
                    "logic": logic_result,
                    "resources": resource_result,
                    "completeness": completeness_result,
                    "ethics": ethical_result
                })
            else:
                return self._create_rejection_response(
                    f"Overall score too low: {overall_score:.2f}",
                    ["Plan needs improvement before approval"]
                )
                
        except Exception as e:
            logging.error(f"QA Agent error during plan review: {e}", exc_info=True)
            return {
                "status": "success",
                "approved": False,
                "comments": f"QA review failed due to error: {str(e)}",
                "confidence": 0.0
            }
    
    async def _analyze_safety(self, goal: str, plan_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze plan for safety issues"""
        dangerous_patterns = [
            "delete", "remove", "destroy", "harm", "attack", "break",
            "corrupt", "damage", "violate", "exploit", "system", "root"
        ]
        
        issues = []
        
        # Check goal description
        for pattern in dangerous_patterns:
            if pattern in goal.lower():
                issues.append(f"Dangerous pattern '{pattern}' in goal")
        
        # Check plan steps
        for i, step in enumerate(plan_steps):
            action = step.get("action", "").lower()
            params = str(step.get("parameters", {})).lower()
            
            for pattern in dangerous_patterns:
                if pattern in action or pattern in params:
                    issues.append(f"Dangerous pattern '{pattern}' in step {i+1}")
        
        return {
            "safe": len(issues) == 0,
            "issues": issues,
            "score": 1.0 if len(issues) == 0 else max(0.0, 1.0 - len(issues) * 0.3)
        }
    
    async def _analyze_logical_consistency(self, plan_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze logical flow and consistency"""
        try:
            if not plan_steps:
                return {"score": 0.0, "issues": ["Empty plan"]}
            
            # Build step summary for AI analysis
            steps_summary = []
            for i, step in enumerate(plan_steps):
                steps_summary.append(f"{i+1}. {step.get('action', 'unknown')}")
            
            prompt = f"""
            Analyze the logical consistency of this plan:
            
            STEPS:
            {chr(10).join(steps_summary)}
            
            Rate logical consistency (0.0-1.0) considering:
            - Sequential flow makes sense
            - Dependencies are clear
            - No contradictory actions
            - Clear success criteria
            
            Respond with only a number between 0.0 and 1.0
            """
            
            response = await monitored_chat_completion(
                role="qa",
                messages=[{"role": "system", "content": prompt}],
                temperature=0.1,
                timeout=10.0
            )
            
            if response.choices and response.choices[0].message.content:
                score = float(response.choices[0].message.content.strip())
                return {
                    "score": max(0.0, min(1.0, score)),
                    "analysis": "AI-assisted logical consistency check"
                }
            
            # Fallback heuristic analysis
            return {"score": 0.7, "analysis": "Heuristic consistency check"}
            
        except Exception as e:
            logging.error(f"Logic analysis failed: {e}")
            return {"score": 0.5, "analysis": "Analysis failed, default score"}
    
    def _analyze_resource_efficiency(self, plan_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze resource usage efficiency"""
        warnings = []
        
        # Check for excessive steps
        if len(plan_steps) > 10:
            warnings.append("Plan has many steps - consider optimization")
        
        # Check for redundant actions
        actions = [step.get("action", "") for step in plan_steps]
        if len(actions) != len(set(actions)):
            warnings.append("Potential redundant actions detected")
        
        # Check for expensive operations
        expensive_actions = ["web_search", "browse_webpage", "execute_python_code"]
        expensive_count = sum(1 for step in plan_steps if step.get("action") in expensive_actions)
        
        if expensive_count > 5:
            warnings.append("Many resource-intensive operations")
        
        return {
            "efficient": len(warnings) == 0,
            "warnings": warnings,
            "score": max(0.3, 1.0 - len(warnings) * 0.2)
        }
    
    def _analyze_plan_completeness(self, goal: str, plan_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check if plan is complete for the stated goal"""
        issues = []
        
        # Basic completeness checks
        if not plan_steps:
            issues.append("No steps defined")
        
        # Check for verification/validation steps
        has_verification = any(
            "review" in step.get("action", "").lower() or 
            "verify" in step.get("action", "").lower() or
            "check" in step.get("action", "").lower()
            for step in plan_steps
        )
        
        if not has_verification and len(plan_steps) > 3:
            issues.append("No verification/review steps found")
        
        return {
            "complete": len(issues) == 0,
            "issues": issues,
            "score": max(0.4, 1.0 - len(issues) * 0.3)
        }
    
    async def _analyze_ethical_implications(self, goal: str, plan_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze ethical implications of the plan"""
        try:
            # Check for privacy concerns
            privacy_actions = ["read_file", "browse_webpage", "web_search"]
            privacy_steps = [s for s in plan_steps if s.get("action") in privacy_actions]
            
            ethical_score = 1.0
            concerns = []
            
            # Reduce score for potential privacy issues
            if len(privacy_steps) > 3:
                ethical_score -= 0.2
                concerns.append("Multiple data access operations")
            
            # Check for self-modification
            if any("modify" in str(step).lower() for step in plan_steps):
                ethical_score -= 0.3
                concerns.append("Self-modification detected")
            
            return {
                "score": max(0.3, ethical_score),
                "concerns": concerns,
                "privacy_safe": len(privacy_steps) <= 3
            }
            
        except Exception as e:
            logging.error(f"Ethical analysis failed: {e}")
            return {"score": 0.6, "concerns": ["Analysis failed"], "privacy_safe": True}
    
    def _calculate_overall_score(self, safety: Dict[str, Any], logic: Dict[str, Any], 
                                resources: Dict[str, Any], completeness: Dict[str, Any],
                                ethics: Dict[str, Any]) -> float:
        """Calculate weighted overall score"""
        weights = {
            "safety": 0.35,      # Highest priority
            "logic": 0.25,
            "completeness": 0.20,
            "ethics": 0.15,
            "resources": 0.05
        }
        
        scores = {
            "safety": safety.get("score", 0.5),
            "logic": logic.get("score", 0.5),
            "completeness": completeness.get("score", 0.5),
            "ethics": ethics.get("score", 0.5),
            "resources": resources.get("score", 0.5)
        }
        
        return sum(scores[key] * weight for key, weight in weights.items())
    
    def _create_approval_response(self, score: float, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create approval response with detailed analysis"""
        return {
            "status": "success",
            "approved": True,
            "overall_score": round(score, 3),
            "comments": f"Plan approved by {self.name} - Overall score: {score:.2f}",
            "confidence": min(score, 0.95),
            "detailed_analysis": analysis,
            "qa_agent": self.name
        }
    
    def _create_rejection_response(self, reason: str, issues: List[str]) -> Dict[str, Any]:
        """Create rejection response with detailed feedback"""
        rejection_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "issues": issues
        }
        self.rejected_plans.append(rejection_record)
        
        return {
            "status": "success",
            "approved": False,
            "comments": f"Plan rejected by {self.name}: {reason}",
            "issues": issues,
            "confidence": 0.9,
            "qa_agent": self.name
        }
    
    def _update_metrics(self, approved: bool, response_time: float):
        """Update performance metrics"""
        self.evaluation_count += 1
        self.performance_metrics["total_evaluations"] += 1
        
        if approved:
            self.performance_metrics["approvals"] += 1
        else:
            self.performance_metrics["rejections"] += 1
        
        # Update approval rate
        self.approval_rate = self.performance_metrics["approvals"] / self.performance_metrics["total_evaluations"]
        
        # Update average response time
        total_evals = self.performance_metrics["total_evaluations"]
        current_avg = self.performance_metrics["avg_response_time"]
        self.performance_metrics["avg_response_time"] = (
            (current_avg * (total_evals - 1) + response_time) / total_evals
        )
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive QA agent performance report"""
        return {
            "agent_name": self.name,
            "performance_metrics": self.performance_metrics.copy(),
            "approval_rate": round(self.approval_rate, 3),
            "recent_rejections": self.rejected_plans[-5:],  # Last 5 rejections
            "status": "ACTIVE" if self.evaluation_count > 0 else "IDLE"
        }
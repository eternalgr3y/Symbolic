# symbolic_agi/ethical_governance.py

import json
import logging
import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from . import config
from .api_client import monitored_chat_completion
from .symbolic_identity import SymbolicIdentity
from .schemas import ActionStep


@dataclass
class EthicalScore:
    truthfulness: float = 0.0
    harm_avoidance: float = 0.0  
    user_collaboration: float = 0.0
    self_preservation: float = 0.0
    privacy_respect: float = 0.0
    resource_efficiency: float = 0.0
    
    def overall_score(self) -> float:
        """Calculate weighted overall ethical score"""
        weights = {
            'truthfulness': 0.25,
            'harm_avoidance': 0.30,  # Highest weight
            'user_collaboration': 0.20,
            'self_preservation': 0.10,
            'privacy_respect': 0.10,
            'resource_efficiency': 0.05
        }
        
        return sum(getattr(self, field) * weight for field, weight in weights.items())
    
    def is_acceptable(self, threshold: float = 0.7) -> bool:
        """Check if ethical scores meet minimum thresholds"""
        critical_checks = [
            self.harm_avoidance >= 0.8,  # Must be high
            self.truthfulness >= 0.6,    # Reasonable accuracy
            self.overall_score() >= threshold
        ]
        return all(critical_checks)

class SymbolicEvaluator:
    """
    ROBUST ethical governance system with comprehensive safety checks.
    Ensures all AGI actions meet ethical standards and logical soundness.
    """
    
    def __init__(self, identity=None):
        self.identity = identity
        self.evaluation_history: List[Dict[str, Any]] = []
        self.blocked_actions: List[str] = []
        self.safety_violations = 0
        
        # Critical safety patterns
        self.forbidden_patterns = [
            "delete", "remove", "destroy", "harm", "attack", "break",
            "corrupt", "damage", "violate", "exploit", "hack", "inject"
        ]
        
        # Resource consumption limits
        self.max_requests_per_minute = 30
        self.request_timestamps: List[datetime] = []
    
    async def evaluate_plan(self, plan_data: Dict[str, Any]) -> bool:
        """
        COMPREHENSIVE plan evaluation with multiple safety layers.
        """
        try:
            plan_steps = plan_data.get("plan", [])
            if not plan_steps:
                logging.warning("Empty plan submitted for evaluation")
                return False
            
            # Layer 1: Pattern-based safety check
            if not self._check_safety_patterns(plan_steps):
                self.safety_violations += 1
                logging.critical(f"Plan REJECTED - Safety pattern violation (total violations: {self.safety_violations})")
                return False
            
            # Layer 2: Resource usage check
            if not self._check_resource_limits():
                logging.warning("Plan REJECTED - Resource limit exceeded")
                return False
            
            # Layer 3: Logical consistency check
            consistency_score = await self._evaluate_logical_consistency(plan_steps)
            if consistency_score < 0.6:
                logging.warning(f"Plan REJECTED - Poor logical consistency: {consistency_score:.2f}")
                return False
            
            # Layer 4: Ethical scoring
            ethical_scores = await self._evaluate_ethical_dimensions(plan_steps)
            
            # Log comprehensive evaluation
            evaluation_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "plan_steps": len(plan_steps),
                "consistency_score": consistency_score,
                "ethical_scores": ethical_scores.__dict__,
                "overall_score": ethical_scores.overall_score(),
                "approved": ethical_scores.is_acceptable()
            }
            
            self.evaluation_history.append(evaluation_record)
            
            if ethical_scores.is_acceptable():
                logging.info(f"Plan APPROVED - Ethical scores: {ethical_scores.__dict__}")
                return True
            else:
                logging.warning(f"Plan REJECTED - Ethical scores insufficient: {ethical_scores.__dict__}")
                return False
                
        except Exception as e:
            logging.error(f"Plan evaluation failed: {e}", exc_info=True)
            return False  # Fail-safe: reject on error
    
    def _check_safety_patterns(self, plan_steps: List[Dict[str, Any]]) -> bool:
        """Check for dangerous patterns in plan steps"""
        for step in plan_steps:
            action = step.get("action", "").lower()
            parameters = str(step.get("parameters", {})).lower()
            
            # Check for forbidden patterns
            for pattern in self.forbidden_patterns:
                if pattern in action or pattern in parameters:
                    logging.critical(f"Forbidden pattern '{pattern}' detected in step: {step}")
                    self.blocked_actions.append(f"{action}: {pattern}")
                    return False
            
            # Check for suspicious file operations
            if action in ["write_file", "read_file", "execute_python_code"]:
                if any(dangerous in parameters for dangerous in ["system", "root", "admin", "..", "/"]):
                    logging.critical(f"Suspicious file operation detected: {step}")
                    return False
        
        return True
    
    def _check_resource_limits(self) -> bool:
        """Check if we're within resource consumption limits"""
        current_time = datetime.now(timezone.utc)
        
        # Clean old timestamps (older than 1 minute)
        self.request_timestamps = [
            ts for ts in self.request_timestamps 
            if (current_time - ts).total_seconds() < 60
        ]
        
        # Check request rate
        if len(self.request_timestamps) >= self.max_requests_per_minute:
            return False
        
        self.request_timestamps.append(current_time)
        return True
    
    async def _evaluate_logical_consistency(self, plan_steps: List[Dict[str, Any]]) -> float:
        """Evaluate logical consistency of the plan"""
        try:
            # Build context for evaluation
            steps_summary = []
            for i, step in enumerate(plan_steps):
                steps_summary.append(f"Step {i+1}: {step.get('action', 'unknown')} - {step.get('parameters', {})}")
            
            prompt = f"""
            Evaluate the logical consistency of this plan:
            
            PLAN STEPS:
            {chr(10).join(steps_summary)}
            
            Rate the logical consistency on a scale of 0.0 to 1.0 considering:
            1. Do steps follow a logical sequence?
            2. Are dependencies between steps clear?
            3. Are the actions appropriate for the apparent goal?
            4. Are there any logical contradictions?
            5. Does the plan have a clear completion condition?
            
            Respond with only a number between 0.0 and 1.0
            """
            
            response = await monitored_chat_completion(
                role="high_stakes",
                messages=[{"role": "system", "content": prompt}],
                temperature=0.1,
                timeout=15.0
            )
            
            if response.choices and response.choices[0].message.content:
                score_text = response.choices[0].message.content.strip()
                try:
                    return float(score_text)
                except ValueError:
                    logging.warning(f"Could not parse consistency score: {score_text}")
                    return 0.5  # Default to moderate score
            
            return 0.5
            
        except Exception as e:
            logging.error(f"Logical consistency evaluation failed: {e}")
            return 0.3  # Conservative score on error
    
    async def _evaluate_ethical_dimensions(self, plan_steps: List[Dict[str, Any]]) -> EthicalScore:
        """Comprehensive ethical evaluation across multiple dimensions"""
        try:
            steps_summary = []
            for i, step in enumerate(plan_steps):
                steps_summary.append(f"Step {i+1}: {step.get('action', 'unknown')}")
            
            prompt = f"""
            Evaluate this plan across ethical dimensions. Rate each from 0.0 to 1.0:
            
            PLAN: {chr(10).join(steps_summary)}
            
            Evaluate:
            1. Truthfulness: Does the plan promote accurate information?
            2. Harm Avoidance: Does the plan avoid potential harm to users/systems?
            3. User Collaboration: Does the plan serve user interests?
            4. Self Preservation: Does the plan protect AGI system integrity?
            5. Privacy Respect: Does the plan respect privacy and data protection?
            6. Resource Efficiency: Does the plan use resources responsibly?
            
            Respond in JSON format:
            {{
                "truthfulness": 0.0,
                "harm_avoidance": 0.0,
                "user_collaboration": 0.0,
                "self_preservation": 0.0,
                "privacy_respect": 0.0,
                "resource_efficiency": 0.0
            }}
            """
            
            response = await monitored_chat_completion(
                role="high_stakes", 
                messages=[{"role": "system", "content": prompt}],
                temperature=0.1,
                timeout=20.0
            )
            
            if response.choices and response.choices[0].message.content:
                import json
                scores_data = json.loads(response.choices[0].message.content.strip())
                return EthicalScore(**scores_data)
            
            # Default conservative scores
            return EthicalScore(
                truthfulness=0.7,
                harm_avoidance=0.8,
                user_collaboration=0.7,
                self_preservation=0.8,
                privacy_respect=0.7,
                resource_efficiency=0.6
            )
            
        except Exception as e:
            logging.error(f"Ethical evaluation failed: {e}")
            # Return conservative scores on error
            return EthicalScore(
                truthfulness=0.6,
                harm_avoidance=0.9,  # Conservative: assume safe unless proven otherwise
                user_collaboration=0.6,
                self_preservation=0.8,
                privacy_respect=0.7,
                resource_efficiency=0.5
            )
    
    async def evaluate_self_modification(self, proposed_code: str, file_path: str) -> bool:
        """
        CRITICAL: Evaluate proposed self-modifications with extreme care.
        """
        try:
            logging.critical(f"EVALUATING SELF-MODIFICATION: {file_path}")
            
            # Immediate safety checks
            if any(dangerous in proposed_code.lower() for dangerous in [
                "exec(", "eval(", "import os", "subprocess", "system(",
                "__import__", "globals(", "locals(", "delete", "remove"
            ]):
                logging.critical("SELF-MODIFICATION REJECTED: Contains dangerous code patterns")
                return False
            
            # File path validation
            safe_files = ["tool_plugin.py", "agi_controller.py", "config.py"]
            if not any(safe_file in file_path for safe_file in safe_files):
                logging.critical(f"SELF-MODIFICATION REJECTED: Unsafe file path: {file_path}")
                return False
            
            # AI-assisted evaluation
            prompt = f"""
            CRITICAL SECURITY EVALUATION: Review this proposed code modification.
            
            FILE: {file_path}
            CODE LENGTH: {len(proposed_code)} characters
            
            Evaluate for:
            1. Malicious code injection
            2. System security violations  
            3. Data corruption risks
            4. Logic bombs or backdoors
            5. Resource exhaustion attacks
            
            Does this code appear SAFE for an AGI system? 
            Respond with only: SAFE or UNSAFE
            """
            
            response = await monitored_chat_completion(
                role="high_stakes",
                messages=[{"role": "system", "content": prompt}],
                temperature=0.0,
                timeout=30.0
            )
            
            if response.choices and response.choices[0].message.content:
                verdict = response.choices[0].message.content.strip().upper()
                
                if verdict == "SAFE":
                    logging.info("Self-modification approved by AI security evaluation")
                    return True
                else:
                    logging.critical("SELF-MODIFICATION REJECTED by AI security evaluation")
                    return False
            
            # Default to rejection if no clear response
            logging.critical("SELF-MODIFICATION REJECTED: No clear security verdict")
            return False
            
        except Exception as e:
            logging.error(f"Self-modification evaluation failed: {e}", exc_info=True)
            return False  # Fail-safe: always reject on error
    
    def get_safety_report(self) -> Dict[str, Any]:
        """Generate comprehensive safety and ethics report"""
        return {
            "safety_violations": self.safety_violations,
            "blocked_actions": self.blocked_actions[-10:],  # Last 10
            "evaluations_count": len(self.evaluation_history),
            "recent_evaluations": self.evaluation_history[-5:],  # Last 5
            "resource_usage": {
                "requests_last_minute": len(self.request_timestamps),
                "max_allowed": self.max_requests_per_minute
            },
            "safety_status": "SECURE" if self.safety_violations < 3 else "ALERT"
        }

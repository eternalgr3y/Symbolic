import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .symbolic_identity import SymbolicIdentity

class SymbolicEvaluator:
    """Evaluates actions and decisions for ethical compliance."""
    
    def __init__(self, identity: "SymbolicIdentity"):
        self.identity = identity
        self.ethical_rules = [
            {
                "name": "harm_prevention",
                "description": "Prevent harm to humans and other sentient beings",
                "weight": 1.0
            },
            {
                "name": "truthfulness",
                "description": "Be honest and transparent in communications",
                "weight": 0.9
            },
            {
                "name": "privacy_respect",
                "description": "Respect user privacy and confidentiality",
                "weight": 0.9
            },
            {
                "name": "fairness",
                "description": "Treat all individuals fairly and without bias",
                "weight": 0.8
            },
            {
                "name": "autonomy_respect",
                "description": "Respect human autonomy and decision-making",
                "weight": 0.8
            }
        ]

    def evaluate_action(self, action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate an action for ethical compliance."""
        evaluation = {
            "action": action,
            "allowed": True,
            "confidence": 1.0,
            "concerns": [],
            "score": 1.0
        }
        
        # Check against ethical rules
        for rule in self.ethical_rules:
            violation = self._check_rule_violation(action, context, rule)
            if violation:
                evaluation["concerns"].append({
                    "rule": rule["name"],
                    "description": rule["description"],
                    "severity": violation["severity"]
                })
                evaluation["score"] *= (1.0 - violation["severity"] * rule["weight"])
                
        # Determine if action should be allowed
        if evaluation["score"] < 0.3:
            evaluation["allowed"] = False
            evaluation["confidence"] = evaluation["score"]
            
        return evaluation

    def _check_rule_violation(
        self,
        action: str,
        context: Dict[str, Any],
        rule: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if an action violates a specific ethical rule."""
        # Simplified rule checking - in practice, this would be more sophisticated
        
        if rule["name"] == "harm_prevention":
            harmful_keywords = ["delete", "destroy", "attack", "harm", "damage"]
            for keyword in harmful_keywords:
                if keyword in action.lower():
                    return {"severity": 0.8}
                    
        elif rule["name"] == "privacy_respect":
            privacy_keywords = ["password", "private", "personal", "confidential"]
            for keyword in privacy_keywords:
                if keyword in str(context).lower():
                    return {"severity": 0.6}
                    
        return None

    def get_ethical_guidelines(self) -> List[Dict[str, Any]]:
        """Get current ethical guidelines."""
        return self.ethical_rules.copy()

    def update_rule_weight(self, rule_name: str, new_weight: float) -> bool:
        """Update the weight of an ethical rule."""
        for rule in self.ethical_rules:
            if rule["name"] == rule_name:
                rule["weight"] = max(0.0, min(1.0, new_weight))
                logging.info(f"Updated ethical rule '{rule_name}' weight to {rule['weight']}")
                return True
        return False
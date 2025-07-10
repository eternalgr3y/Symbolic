# symbolic_agi/ethical_governor.py

from typing import Dict, Any

class EthicalGovernor:
    """Policy layer for ethical screening of agent actions."""
    
    BLOCKED_ACTIONS = {"apply_code_modification", "propose_code_modification", "execute_python_code"}
    BLOCKED_KEYWORDS = {"delete", "destroy", "harm", "attack", "corrupt", "break"}
    
    def screen(self, action: Dict[str, Any], agent: str) -> bool:
        """Screen action for ethical compliance. Returns False if blocked."""
        action_name = action.get("action", "")
        params_str = str(action.get("parameters", {})).lower()
        return action_name not in self.BLOCKED_ACTIONS and not any(kw in params_str for kw in self.BLOCKED_KEYWORDS)
    # In ethical_governance.py
    def calculate_thresholds(self, goal_complexity: float, agent_trust: float):
        base_harm = 0.8
        base_truth = 0.6

        # Lower thresholds for simple tasks with trusted agents
        harm_threshold = base_harm - (0.2 * agent_trust * (1 - goal_complexity))
        truth_threshold = base_truth - (0.1 * agent_trust * (1 - goal_complexity))

        return harm_threshold, truth_threshold
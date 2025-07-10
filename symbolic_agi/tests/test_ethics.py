# tests/test_ethics.py

import pytest
from symbolic_agi.ethical_governor import EthicalGovernor
from symbolic_agi.tool_plugin import EthicsViolation, ToolPlugin

class TestEthicalGovernor:
    def setup_method(self):
        self.governor = EthicalGovernor()
    
    def test_screen_allows_safe_action(self):
        action = {"action": "web_search", "parameters": {"query": "python tutorial"}}
        assert self.governor.screen(action, "test_agent") is True
    
    def test_screen_blocks_dangerous_action(self):
        action = {"action": "apply_code_modification", "parameters": {"file": "test.py"}}
        assert self.governor.screen(action, "test_agent") is False
    
    def test_screen_blocks_harmful_keywords(self):
        action = {"action": "web_search", "parameters": {"query": "how to destroy database"}}
        assert self.governor.screen(action, "test_agent") is False
    
    def test_screen_allows_benign_keywords(self):
        action = {"action": "analyze_data", "parameters": {"data": "sales report"}}
        assert self.governor.screen(action, "test_agent") is True
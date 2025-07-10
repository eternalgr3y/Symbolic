#!/usr/bin/env python3
"""Fix agent test constructor issues"""

import os
import re

def fix_agent_tests():
    """Fix the agent test constructor"""
    test_file = "symbolic_agi/tests/test_agent.py"
    
    if not os.path.exists(test_file):
        print(f"❌ {test_file} not found")
        return False
    
    with open(test_file, 'r') as f:
        content = f.read()
    
    # Fix the agent fixture
    old_fixture = r'@pytest_asyncio\.fixture\s*async def agent\(\):\s*"""[^"]*"""\s*return Agent\(\)'
    new_fixture = '''@pytest_asyncio.fixture
async def agent():
    """Fixture to create a test agent with required parameters."""
    from unittest.mock import Mock
    from symbolic_agi.message_bus import MessageBus
    from symbolic_agi.api_client import APIClient
    
    # Create mock dependencies
    mock_message_bus = Mock(spec=MessageBus)
    mock_api_client = Mock(spec=APIClient)
    
    # Create agent with required parameters
    agent = Agent(
        name="test_agent",
        message_bus=mock_message_bus,
        api_client=mock_api_client
    )
    return agent'''
    
    content = re.sub(old_fixture, new_fixture, content, flags=re.DOTALL)
    
    # Also fix any direct Agent() calls
    content = re.sub(r'Agent\(\)', 
                    'Agent(name="test_agent", message_bus=Mock(), api_client=Mock())', 
                    content)
    
    with open(test_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed {test_file}")
    return True

if __name__ == "__main__":
    os.chdir("c:\\Users\\Todd\\Projects\\symbolic_agi")
    fix_agent_tests()
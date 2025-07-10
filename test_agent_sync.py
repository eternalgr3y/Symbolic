#!/usr/bin/env python3
"""Tests for Agent using proven sync pattern"""

import asyncio
import tempfile
import os
import shutil
from unittest.mock import Mock, AsyncMock

from symbolic_agi.agent import Agent

class TestAgent:
    """Test individual agent functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_message_bus = Mock()
        self.mock_api_client = Mock()
    
    def teardown_method(self):
        """Cleanup after each test"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_agent_initialization_sync(self):
        """Test agent initialization"""
        agent = Agent(
            name="test_agent",
            message_bus=self.mock_message_bus,
            api_client=self.mock_api_client
        )
        assert agent is not None
        assert agent.name == "test_agent"
    
    def test_agent_message_handling_sync(self):
        """Test agent message handling"""
        async def run_test():
            agent = Agent(
                name="test_agent", 
                message_bus=self.mock_message_bus,
                api_client=self.mock_api_client
            )
            # Test message handling
            # Add specific test logic
        
        asyncio.run(run_test())

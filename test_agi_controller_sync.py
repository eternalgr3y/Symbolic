#!/usr/bin/env python3
"""Tests for AGI Controller using proven sync pattern"""

import asyncio
import tempfile
import os
import shutil
from unittest.mock import Mock, AsyncMock, patch

from symbolic_agi.agi_controller import SymbolicAGI

class TestAGIController:
    """Test the main AGI controller"""
    
    def setup_method(self):
        """Setup for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_config = {
            "workspace_dir": self.temp_dir,
            "api_key": "test_key"
        }
    
    def teardown_method(self):
        """Cleanup after each test"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_agi_initialization_sync(self):
        """Test AGI initialization"""
        async def run_test():
            # Mock dependencies
            with patch('symbolic_agi.agi_controller.MessageBus'):
                with patch('symbolic_agi.agi_controller.ToolPlugin'):
                    agi = SymbolicAGI(self.mock_config)
                    assert agi is not None
                    # Add more initialization checks
        
        asyncio.run(run_test())
    
    def test_message_processing_sync(self):
        """Test message processing"""
        async def run_test():
            with patch('symbolic_agi.agi_controller.MessageBus'):
                with patch('symbolic_agi.agi_controller.ToolPlugin'):
                    agi = SymbolicAGI(self.mock_config)
                    # Test message processing logic
                    # Add specific assertions
        
        asyncio.run(run_test())

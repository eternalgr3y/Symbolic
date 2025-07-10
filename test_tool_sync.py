#!/usr/bin/env python3
"""Create fully synchronous tool tests that avoid async teardown issues"""

import pytest
from unittest.mock import Mock, patch
import tempfile
import os
import shutil
import asyncio

from symbolic_agi.tool_plugin import ToolPlugin


class TestToolPluginSync:
    """Synchronous tests for ToolPlugin that avoid async teardown issues."""
    
    def setup_method(self):
        """Setup for each test method"""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_agi = Mock()
        self.mock_agi.workspace_dir = self.temp_dir
        self.mock_agi.message_bus = Mock()
        
        self.tool = ToolPlugin(self.mock_agi)
        self.tool.workspace_dir = self.temp_dir
    
    def teardown_method(self):
        """Cleanup after each test method"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_tool_initialization_sync(self):
        """Test that tool plugin initializes correctly (sync version)."""
        assert self.tool is not None
        assert self.tool.agi == self.mock_agi
        assert self.tool.workspace_dir == self.temp_dir
    
    def test_url_whitelist_enforcement_sync(self):
        """Test that URL whitelist is enforced (sync version)."""
        # Test blocked domain
        assert not self.tool._is_url_allowed("http://malicious-site.com")
        
        # Test allowed domain
        with patch('symbolic_agi.config.ALLOWED_DOMAINS', {'wikipedia.org'}):
            assert self.tool._is_url_allowed("https://wikipedia.org/test")
    
    def test_file_access_security_sync(self):
        """Test that file access is restricted to workspace (sync version)."""
        # Run the async method using asyncio.run
        async def run_test():
            result = await self.tool.read_file("/etc/passwd")
            assert result["status"] == "failure"
            assert ("denied" in result["description"].lower() or 
                    "outside" in result["description"].lower() or 
                    "not allowed" in result["description"].lower() or
                    "no such file" in result["description"].lower())
        
        # Run async test synchronously
        asyncio.run(run_test())
    
    def test_write_file_basic_sync(self):
        """Test basic file writing functionality (sync version)."""
        async def run_test():
            content = "Test content"
            result = await self.tool.write_file("test.txt", content)
            assert result["status"] == "success"
            
            file_path = os.path.join(self.tool.workspace_dir, "test.txt")
            assert os.path.exists(file_path)
            
            # Read file synchronously
            with open(file_path, "r") as f:
                file_content = f.read()
            assert file_content == content
        
        asyncio.run(run_test())
    
    def test_browser_operations_require_initialization_sync(self):
        """Test browser operations fail gracefully without browser (sync version)."""
        async def run_test():
            self.mock_agi.browser = None
            result = await self.tool.browser_new_page("http://test.com")
            assert result["status"] == "failure"
            assert "not initialized" in result["description"].lower()
        
        asyncio.run(run_test())
    
    # Add more comprehensive tests to the working sync pattern

    def test_execute_python_code_sync(self):
        """Test Python code execution (sync version)."""
        async def run_test():
            # Test basic safe code
            result = await self.tool.execute_python_code("print('Hello')")
            assert result["status"] == "success"
            assert "Hello" in result["output"]
            
            # Test dangerous operations fail
            dangerous_code = "import os; os.system('ls')"
            result = await self.tool.execute_python_code(dangerous_code, timeout_seconds=1)
            assert result["status"] == "failure" or "terminated" in result.get("description", "")
        
        asyncio.run(run_test())
    
    def test_list_files_sync(self):
        """Test file listing functionality (sync version)."""
        async def run_test():
            # Create test files
            os.makedirs(os.path.join(self.tool.workspace_dir, "subdir"))
            
            # Write files synchronously for this test
            with open(os.path.join(self.tool.workspace_dir, "file1.txt"), "w") as f:
                f.write("test")
            with open(os.path.join(self.tool.workspace_dir, "subdir", "file2.txt"), "w") as f:
                f.write("test")
            
            result = await self.tool.list_files(".")
            assert result["status"] == "success"
            assert "file1.txt" in result["files"]
            assert "subdir" in result["files"]
        
        asyncio.run(run_test())
    
    def test_path_traversal_prevention_sync(self):
        """Test path traversal prevention (sync version)."""
        async def run_test():
            malicious_paths = [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32\\config\\sam",
                "subdir/../../outside.txt"
            ]
            
            for path in malicious_paths:
                result = await self.tool.read_file(path)
                assert result["status"] == "failure", f"Path traversal not blocked for: {path}"
        
        asyncio.run(run_test())
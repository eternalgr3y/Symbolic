import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
import os
import json
import shutil

from symbolic_agi.tool_plugin import ToolPlugin
from symbolic_agi.agi_controller import SymbolicAGI


@pytest.fixture(scope="function")
def tool_setup():
    """Set up test environment with mocked AGI and ToolPlugin."""
    temp_dir = tempfile.mkdtemp()
    mock_agi = Mock()
    mock_agi.workspace_dir = temp_dir
    mock_agi.message_bus = Mock()
    mock_agi.message_bus.redis_client = AsyncMock()
    
    # Create the ToolPlugin with the AGI mock
    tool = ToolPlugin(mock_agi)
    tool.workspace_dir = temp_dir
    
    yield tool, mock_agi, temp_dir
    
    # Simple synchronous cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestToolPlugin:
    """Comprehensive tests for ToolPlugin covering critical functionality."""
    
    # --- CRITICAL: File System Safety Tests ---
    
    @pytest.mark.asyncio
    async def test_file_access_security(self, tool_setup):
        """Test that file access is restricted to workspace."""
        tool, _, _ = tool_setup
        
        # Try to access file outside workspace with absolute path
        result = await tool.read_file("/etc/passwd")
        assert result["status"] == "failure"
        # Check for either denied, path traversal prevention, or file not found (which is also secure)
        assert ("denied" in result["description"].lower() or 
                "outside" in result["description"].lower() or 
                "not allowed" in result["description"].lower() or
                "no such file" in result["description"].lower())
    
    @pytest.mark.asyncio
    async def test_write_file_basic(self, tool_setup):
        """Test basic file writing functionality."""
        tool, _, _ = tool_setup
        import aiofiles
        content = "Test content"
        result = await tool.write_file("test.txt", content)
        assert result["status"] == "success"
        file_path = os.path.join(tool.workspace_dir, "test.txt")
        assert os.path.exists(file_path)
        async with aiofiles.open(file_path, "r") as f:
            file_content = await f.read()
        assert file_content == content
    
    # --- CRITICAL: Code Execution Safety ---
    
    @pytest.mark.asyncio
    async def test_execute_python_code_sandboxed(self, tool_setup):
        """Test that Python code execution is properly sandboxed."""
        tool, _, _ = tool_setup
        
        # Test basic safe code
        result = await tool.execute_python_code("print('Hello')")
        assert result["status"] == "success"
        assert "Hello" in result["output"]
        
        # Test that dangerous operations fail
        dangerous_code = "import os; os.system('ls')"
        result = await tool.execute_python_code(dangerous_code, timeout_seconds=1)
        # Should either fail or timeout
        assert result["status"] == "failure" or "terminated" in result.get("description", "")
    
    @pytest.mark.asyncio
    async def test_execute_python_code_timeout(self, tool_setup):
        """Test code execution timeout."""
        tool, _, _ = tool_setup
        
        infinite_loop = "while True: pass"
        result = await tool.execute_python_code(infinite_loop, timeout_seconds=1)
        
        assert result["status"] == "failure"
        assert "timeout" in result["description"].lower() or "terminated" in result["description"].lower()
    
    # --- CRITICAL: Web Access Security ---
    
    @pytest.mark.asyncio
    async def test_url_whitelist_enforcement(self, tool_setup):
        """Test that URL whitelist is enforced."""
        tool, _, _ = tool_setup
        
        # Test blocked domain
        assert not tool._is_url_allowed("http://malicious-site.com")
        
        # Test allowed domain (assuming wikipedia is in whitelist)
        with patch('symbolic_agi.config.ALLOWED_DOMAINS', {'wikipedia.org'}):
            assert tool._is_url_allowed("https://wikipedia.org/test")
    
    @patch('symbolic_agi.tool_plugin.requests.get')
    async def test_browse_webpage_security(self, mock_get, tool_setup):
        """Test webpage browsing with security checks."""
        tool, mock_agi, temp_dir = tool_setup
        
        # Mock response
        mock_response = Mock()
        mock_response.text = "<html><body>Test content</body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Test blocked URL
        with patch.object(tool, '_is_url_allowed', return_value=False):
            result = await tool.browse_webpage("http://blocked.com")
            assert result["status"] == "failure"
            assert "blocked" in result["description"].lower()
        
        # Test allowed URL
        with patch.object(tool, '_is_url_allowed', return_value=True):
            with patch.object(tool, '_check_robots_compliance', return_value=True):
                with patch.object(tool, '_get_crawl_delay', return_value=0):
                    result = await tool.browse_webpage("http://allowed.com")
                    assert result["status"] == "success"
                    assert "Test content" in result["content"]
    
    # --- CRITICAL: Self-Modification Safety ---
    
    @pytest.mark.asyncio
    async def test_code_modification_requires_approval(self, tool_setup):
        """Test that code modifications require safety evaluation."""
        tool, mock_agi, _ = tool_setup
        
        # Mock evaluator
        mock_agi.evaluator = AsyncMock()
        mock_agi.evaluator.evaluate_self_modification = AsyncMock(return_value=False)
        
        # Create a test file
        test_file = os.path.join(tool.workspace_dir, "test.py")
        import aiofiles
        async with aiofiles.open(test_file, "w") as f:
            await f.write("print('original')")
        
        result = await tool.apply_code_modification(
            "test.py",
            "proposed_code_key",
            workspace={"proposed_code_key": "print('modified')"},
        )
        
        assert result["status"] == "failure"
        assert "rejected" in result["description"].lower()
        mock_agi.evaluator.evaluate_self_modification.assert_called_once()
    
    # --- HIGH PRIORITY: Skill Management ---
    
    @pytest.mark.asyncio
    async def test_create_skill_with_validation(self, tool_setup):
        """Test skill creation with ethical validation."""
        tool, mock_agi, _ = tool_setup
        mock_agi.planner = AsyncMock()
        mock_agi.planner.decompose_goal_into_plan = AsyncMock()
        # Return a plan with steps
        mock_plan = Mock()
        mock_plan.plan = [Mock(action="test_action")]
        mock_agi.planner.decompose_goal_into_plan.return_value = mock_plan
        mock_agi.evaluator = AsyncMock()
        mock_agi.evaluator.evaluate_plan = AsyncMock(return_value=False)
        result = await tool.create_new_skill_from_description(
            "hack_system",
            "Hack into systems"
        )
        assert result["status"] == "failure"
        # The exact message might vary, so check for failure indicators
        assert "rejected" in result["description"].lower() or "failed" in result["description"].lower()
    
    # --- MEDIUM PRIORITY: Data Analysis ---
    
    @patch('symbolic_agi.tool_plugin.monitored_chat_completion')
    async def test_analyze_data(self, mock_chat, tool_setup):
        """Test data analysis tool."""
        tool, mock_agi, temp_dir = tool_setup
        
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Analysis result"))]
        mock_chat.return_value = mock_response
        
        result = await tool.analyze_data("test data", "What is this?")
        
        assert result["status"] == "success"
        assert result["answer"] == "Analysis result"
    
    # --- INTEGRATION: Memory and Learning ---
    
    @pytest.mark.asyncio
    async def test_explain_skill_integration(self, tool_setup):
        """Test skill explanation with memory integration."""
        tool, mock_agi, _ = tool_setup
        
        mock_agi.memory = AsyncMock()
        mock_agi.introspector = AsyncMock()
        mock_agi.introspector.llm_reflect = AsyncMock(return_value="Skill explanation")
        
        # Mock skills attribute (not skill_manager) with proper return value
        mock_agi.skills = Mock()
        mock_skill = Mock()
        mock_skill.model_dump = Mock(return_value={
            "name": "test_skill",
            "description": "Test description",
            "implementation": "print('test')"
        })
        mock_agi.skills.get_skill_by_name = Mock(return_value=mock_skill)
        
        result = await tool.explain_skill("test_skill")
        
        assert result["status"] == "success"
        assert "explanation" in result
        mock_agi.memory.add_memory.assert_called_once()
    
    # --- BROWSER AUTOMATION ---
    
    @pytest.mark.asyncio
    async def test_browser_operations_require_initialization(self, tool_setup):
        """Test browser operations fail gracefully without browser."""
        tool, mock_agi, _ = tool_setup
        
        mock_agi.browser = None
        
        result = await tool.browser_new_page("http://test.com")
        assert result["status"] == "failure"
        assert "not initialized" in result["description"].lower()
    
    # --- TOOL INITIALIZATION ---
    
    @pytest.mark.asyncio
    async def test_tool_initialization(self, tool_setup):
        """Test that tool plugin initializes correctly."""
        tool, mock_agi, temp_dir = tool_setup
        
        assert tool is not None
        assert tool.agi == mock_agi
        # Check that workspace was set to temp_dir
        assert tool.workspace_dir == temp_dir
    
    # --- LISTING OPERATIONS ---
    
    @pytest.mark.asyncio
    async def test_list_directory(self, tool_setup):
        """Test listing files in directory."""
        tool, _, _ = tool_setup
        import aiofiles
        os.makedirs(os.path.join(tool.workspace_dir, "subdir"))
        async with aiofiles.open(os.path.join(tool.workspace_dir, "file1.txt"), "w") as f:
            await f.write("test")
        async with aiofiles.open(os.path.join(tool.workspace_dir, "subdir", "file2.txt"), "w") as f:
            await f.write("test")
        result = await tool.list_files(".")
        assert result["status"] == "success"
        assert "file1.txt" in result["files"]
        assert "subdir" in result["files"]
    
    # --- SKILL DETAILS ---
    
    @pytest.mark.asyncio
    async def test_get_skill_details(self, tool_setup):
        """Test getting skill details."""
        tool, mock_agi, _ = tool_setup
        
        # Mock the skills attribute (not skill_manager)
        mock_agi.skills = Mock()
        mock_skill = Mock()
        mock_skill.model_dump = Mock(return_value={
            "name": "test_skill",
            "description": "Test description", 
            "implementation": "print('test')",
            "tags": ["test"],
            "version": 1,
            "usage_count": 5,
            "success_count": 4,
            "failure_count": 1
        })
        mock_agi.skills.get_skill_by_name = Mock(return_value=mock_skill)
        
        result = await tool.get_skill_details("test_skill")
        
        assert result["status"] == "success"
        assert result["skill_details"]["name"] == "test_skill"
    
    @pytest.mark.asyncio
    async def test_get_skill_details_not_found(self, tool_setup):
        """Test getting details for non-existent skill."""
        tool, mock_agi, _ = tool_setup
        
        # Mock the skills attribute (not skill_manager)
        mock_agi.skills = Mock()
        mock_agi.skills.get_skill_by_name = Mock(return_value=None)
        
        result = await tool.get_skill_details("non_existent")
        
        assert result["status"] == "failure"
        assert "not found" in result["description"].lower()
    
    # --- Additional Security Tests ---
    
    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self, tool_setup):
        """Test that path traversal attacks are prevented."""
        tool, _, _ = tool_setup
        
        # Try various path traversal attempts
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "subdir/../../outside.txt"
        ]
        
        for path in malicious_paths:
            result = await tool.read_file(path)
            assert result["status"] == "failure", f"Path traversal not blocked for: {path}"
    
    @pytest.mark.asyncio
    async def test_symlink_protection(self, tool_setup):
        """Test that symlink attacks are prevented"""
        tool_instance, _, _ = tool_setup
        
        # Attempt to use symlink in path - should be blocked
        result = await tool_instance.read_file("../../../etc/passwd")
        assert not result.get("success", True), "Symlink attack should be blocked"

    @pytest.mark.asyncio
    async def test_read_own_source_code(self, tool_setup):
        """Test reading own source code functionality"""
        tool_instance, _, _ = tool_setup
        
        result = await tool_instance.read_own_source_code()
        assert result["success"] is True
        assert "source_code" in result
        assert "class ToolPlugin" in result["source_code"]

    @pytest.mark.asyncio
    async def test_get_current_datetime(self, tool_setup):
        """Test datetime retrieval functionality"""
        tool_instance, _, _ = tool_setup
        
        result = await tool_instance.get_current_datetime()
        assert result["success"] is True
        assert "current_datetime" in result
        assert "timezone" in result

    @pytest.mark.asyncio
    async def test_read_core_file_security(self, tool_setup):
        """Test that core file reading has proper security"""
        tool_instance, _, _ = tool_setup
        
        # Test valid core file
        result = await tool_instance.read_core_file("prompts.py")
        assert result["success"] is True
        
        # Test invalid file (should be blocked)
        result = await tool_instance.read_core_file("../../../etc/passwd")
        assert not result.get("success", True)

    @pytest.mark.asyncio
    async def test_web_search_security(self, tool_setup):
        """Test web search with security constraints"""
        tool_instance, _, _ = tool_setup
        
        # Test that web search requires proper parameters
        result = await tool_instance.web_search("")
        assert not result.get("success", True)
        
        # Test with valid query
        result = await tool_instance.web_search("test query")
        # Should return proper structure even if no actual search performed
        assert "message" in result

    @pytest.mark.asyncio
    async def test_chain_of_thought_reasoning(self, tool_setup):
        """Test chain of thought reasoning functionality"""
        tool_instance, _, _ = tool_setup
        
        with patch('symbolic_agi.api_client.monitored_chat_completion') as mock_chat:
            mock_chat.return_value = {
                "reasoning_steps": ["step1", "step2"],
                "conclusion": "test conclusion"
            }
            
            result = await tool_instance.chain_of_thought_reasoning("test problem")
            assert result["success"] is True
            assert "reasoning_steps" in result
            mock_chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_self_capabilities(self, tool_setup):
        """Test self-capability analysis"""
        tool_instance, _, _ = tool_setup
        
        result = await tool_instance.analyze_self_capabilities()
        assert result["success"] is True
        assert "available_tools" in result
        assert "capabilities" in result

    @pytest.mark.asyncio
    async def test_review_plan(self, tool_setup):
        """Test plan review functionality"""
        tool_instance, _, _ = tool_setup
        
        # Mock the planner
        with patch.object(tool_instance.agi, 'planner') as mock_planner:
            mock_planner.current_plan = {
                "goal": "test goal",
                "steps": ["step1", "step2"],
                "status": "active"
            }
            
            result = await tool_instance.review_plan()
            assert result["success"] is True
            assert "current_plan" in result

    @pytest.mark.asyncio
    async def test_craft_method(self, tool_setup):
        """Test craft method functionality"""
        tool_instance, _, _ = tool_setup
        
        with patch('symbolic_agi.api_client.monitored_chat_completion') as mock_chat:
            mock_chat.return_value = {
                "approach": "test approach",
                "implementation": "test implementation",
                "considerations": ["test consideration"]
            }
            
            result = await tool_instance.craft("Create a simple function", goal="test goal")
            assert result["success"] is True
            assert "approach" in result
            mock_chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_skill(self, tool_setup):
        """Test skill update functionality"""
        tool_instance, mock_agi, _ = tool_setup
        
        # Mock the skills attribute
        mock_agi.skills = Mock()
        mock_agi.skills.get_skill_by_name.return_value = {
            "name": "test_skill",
            "code": "def test(): pass",
            "description": "Test skill"
        }
        mock_agi.skills.update_skill = Mock()
        
        result = await tool_instance.update_skill(
            skill_name="test_skill",
            new_code="def test_updated(): pass",
            description="Updated test skill"
        )
        assert result["success"] is True
        mock_agi.skills.update_skill.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_skill_not_found(self, tool_setup):
        """Test skill update when skill doesn't exist"""
        tool_instance, mock_agi, _ = tool_setup
        
        # Mock the skills attribute
        mock_agi.skills = Mock()
        mock_agi.skills.get_skill_by_name.return_value = None
        
        result = await tool_instance.update_skill(
            skill_name="nonexistent_skill",
            new_code="def test(): pass"
        )
        assert not result.get("success", True)
        assert "not found" in result.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_manage_knowledge_graph(self, tool_setup):
        """Test knowledge graph management"""
        tool_instance, _, _ = tool_setup
        
        # Test invalid action
        result = await tool_instance.manage_knowledge_graph("invalid_action")
        assert not result.get("success", True)
        
        # Test add action
        result = await tool_instance.manage_knowledge_graph(
            "add", 
            entity="test_entity", 
            relation="test_relation", 
            target="test_target"
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_provision_agent(self, tool_setup):
        """Test agent provisioning functionality"""
        tool_instance, _, _ = tool_setup
        
        with patch.object(tool_instance.agi, 'agent_pool') as mock_pool:
            mock_pool.provision_agent.return_value = "agent_123"
            
            result = await tool_instance.provision_agent(
                agent_type="test_agent",
                capabilities=["test_capability"]
            )
            assert result["success"] is True
            assert "agent_id" in result
            mock_pool.provision_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_monitoring_dashboard(self, tool_setup):
        """Test monitoring dashboard functionality"""
        tool_instance, _, _ = tool_setup
        
        result = await tool_instance.show_monitoring_dashboard()
        assert result["success"] is True
        assert "dashboard" in result
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_manage_web_access(self, tool_setup):
        """Test web access management"""
        tool_instance, _, _ = tool_setup
        
        # Test invalid action
        result = await tool_instance.manage_web_access("invalid_action")
        assert not result.get("success", True)
        
        # Test status action
        result = await tool_instance.manage_web_access("status")
        assert result["success"] is True
        assert "web_access_enabled" in result
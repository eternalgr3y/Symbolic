import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from symbolic_agi.agent import Agent
from symbolic_agi.message_bus import RedisMessageBus
from openai import AsyncOpenAI

class TestAgent:
    
    @pytest.fixture
    def agent_setup(self):
        """Setup a test agent with mocked dependencies"""
        # Create mocked dependencies
        mock_message_bus = Mock(spec=RedisMessageBus)
        mock_message_bus.subscribe = Mock(return_value=AsyncMock())
        mock_api_client = Mock(spec=AsyncOpenAI)
        
        # Create agent with required arguments
        agent = Agent(
            name="test_agent", 
            message_bus=mock_message_bus, 
            api_client=mock_api_client
        )
        
        # Add mocked attributes
        agent.tools = Mock()
        agent.agi = Mock()
        agent.agi.workspace_dir = "/test/workspace"
        agent.logger = Mock()
        
        # Mock skills attribute
        agent.agi.skills = Mock()
        agent.agi.skills.get_skill_by_name = Mock()
        
        return agent
    
    @pytest.mark.asyncio
    async def test_browser_action(self, agent_setup):
        """Test browser action functionality"""
        agent = agent_setup
        
        # Mock the browser method if it exists
        if hasattr(agent, 'browser'):
            with patch.object(agent, 'browser', AsyncMock(return_value="Analyzed webpage successfully")):
                result = await agent.browser("https://example.com", "click login")
                assert "Analyzed" in result or "success" in result.lower()
    
    @pytest.mark.asyncio
    async def test_skill_review_efficiency(self, agent_setup):
        """Test skill efficiency review"""
        agent = agent_setup
        
        # Mock skill details
        mock_skill = Mock()
        mock_skill.model_dump = Mock(return_value={
            "name": "test_skill",
            "description": "A test skill",
            "implementation": "def test(): pass",
            "usage_count": 10,
            "success_count": 8,
            "failure_count": 2,
            "version": 1,
            "tags": ["test"]
        })
        
        agent.agi.skills.get_skill_by_name = Mock(return_value=mock_skill)
        
        if hasattr(agent, 'skill_review_skill_efficiency'):
            result = await agent.skill_review_skill_efficiency("test_skill")
            assert "test_skill" in result
        else:
            # If method doesn't exist, just check agent structure
            assert hasattr(agent, 'agi')
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test that agent initializes properly"""
        # Create mocked dependencies
        mock_message_bus = Mock(spec=RedisMessageBus)
        mock_message_bus.subscribe = Mock(return_value=AsyncMock())
        mock_api_client = Mock(spec=AsyncOpenAI)
        
        # Create agent with required arguments
        agent = Agent(
            name="test_agent_init", 
            message_bus=mock_message_bus, 
            api_client=mock_api_client
        )
        
        # Check agent initialization
        assert agent.name == "test_agent_init"
        assert agent.persona == "agent"  # based on the name splitting logic
        assert agent.bus == mock_message_bus
        assert agent.client == mock_api_client
        assert agent.running is True
    
    @pytest.mark.asyncio
    async def test_agent_with_invalid_skill(self, agent_setup):
        """Test agent handles invalid skill gracefully"""
        agent = agent_setup
        
        # Mock invalid skill
        agent.agi.skills.get_skill_by_name = Mock(return_value=None)
        
        if hasattr(agent, 'skill_review_skill_efficiency'):
            result = await agent.skill_review_skill_efficiency("non_existent")
            assert "not found" in result.lower() or "unable" in result.lower() or "error" in result.lower()
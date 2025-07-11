# tests/test_config.py
"""Unit tests for the configuration module."""
import os
from unittest.mock import patch, Mock

import pytest
from symbolic_agi.config import get_config, AGIConfig
from symbolic_agi.config_manager import ConfigManager, robots_checker


def test_get_config_is_singleton():
    """Verify that get_config() always returns the same instance."""
    first_call = get_config()
    second_call = get_config()
    assert first_call is second_call


def test_config_loading_from_env():
    """Verify that environment variables override default settings."""
    test_key = "your_test_api_key"
    with patch.dict(os.environ, {"OPENAI_API_KEY": test_key}):
        # Force reload of config for this test
        config_instance = AGIConfig()
        assert config_instance.openai_api_key == test_key


def test_robots_checker_can_fetch_allowed():
    """Test that the robots_checker allows fetching when permitted."""
    mock_parser = Mock()
    mock_parser.can_fetch.return_value = True

    with patch.object(ConfigManager, "robots_cache", {"http://example.com": mock_parser}):
        assert robots_checker.can_fetch("http://example.com/allowed/path") is True
        mock_parser.can_fetch.assert_called_with(
            robots_checker.user_agent, "http://example.com/allowed/path"
        )


def test_robots_checker_can_fetch_disallowed():
    """Test that the robots_checker blocks fetching when disallowed."""
    mock_parser = Mock()
    mock_parser.can_fetch.return_value = False

    with patch.object(ConfigManager, "robots_cache", {"http://example.com": mock_parser}):
        assert robots_checker.can_fetch("http://example.com/disallowed/path") is False
        mock_parser.can_fetch.assert_called_with(
            robots_checker.user_agent, "http://example.com/disallowed/path"
        )


@patch("urllib.robotparser.RobotFileParser.read")
def test_robots_checker_fetches_and_caches(mock_read):
    """Verify that the checker fetches robots.txt only once per domain."""
    checker = ConfigManager()
    checker.can_fetch("https://new-domain.com/page1")
    checker.can_fetch("https://new-domain.com/page2")

    # .read() should only have been called once for the domain
    mock_read.assert_called_once()
    assert "https://new-domain.com" in checker.robots_cache
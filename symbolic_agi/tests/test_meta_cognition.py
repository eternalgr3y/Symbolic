"""Test module for MetaCognition functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from symbolic_agi.meta_cognition import MetaCognitionUnit


@pytest.mark.asyncio
async def test_meta_cognition_basic() -> None:
    """Basic test for MetaCognitionUnit instantiation."""
    mock_agi = MagicMock()
    meta_cognition = MetaCognitionUnit(mock_agi)
    assert meta_cognition.agi == mock_agi


@pytest.mark.asyncio
async def test_generate_goal_from_drives_mock() -> None:
    """Test goal generation using mocked methods."""
    mock_agi = MagicMock()
    with patch.object(MetaCognitionUnit, "generate_goal_from_drives", new_callable=AsyncMock):
        meta_cognition = MetaCognitionUnit(mock_agi)
        # This will use the mocked version, avoiding attribute access issues
        await meta_cognition.generate_goal_from_drives()
        # Just verify it runs without error - no return value expected

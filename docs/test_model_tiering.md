# Unit Test Plan: Model Tiering

This document outlines the unit test strategy for verifying the correct implementation of the role-based model tiering system.

## Objective

To confirm that calls to `monitored_chat_completion` in `api_client.py` correctly select either the `HIGH_STAKES_MODEL` or the `FAST_MODEL` based on the provided `role` parameter.

## Test Strategy

We will use `pytest` and `unittest.mock.patch` to mock the `openai.AsyncOpenAI.chat.completions.create` method. This allows us to inspect the arguments passed to the underlying OpenAI API call without actually incurring costs or network latency.

## Test Case: `test_model_selection_based_on_role`

This test will simulate a simple goal that requires both a high-stakes and a low-stakes cognitive function.

### Test Setup (`tests/test_model_tiering.py`)

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import json

from symbolic_agi.agi_controller import SymbolicAGI
from symbolic_agi.schemas import GoalModel
from symbolic_agi import config

@pytest.mark.asyncio
async def test_model_selection_based_on_role():
    """
    Validates that high-stakes roles use the high-stakes model and
    other roles use the fast model.
    """
    # Arrange: Initialize the AGI
    agi = SymbolicAGI()

    # Arrange: Define a simple goal that involves planning (high-stakes) and a simple tool (low-stakes)
    goal_description = "Analyze the content of the file 'test.txt' and summarize it."
    goal = GoalModel(description=goal_description, sub_tasks=[])
    agi.ltm.add_goal(goal)

    # Mock the underlying OpenAI API call
    with patch('symbolic_agi.api_client.client.chat.completions.create', new_callable=AsyncMock) as mock_create:
        # Mock responses to allow the plan to proceed
        # 1. Planner response (high-stakes)
        planner_response_content = {
            "thought": "I will read the file and then analyze its content.",
            "plan": [
                {"action": "read_file", "parameters": {"file_path": "test.txt"}, "assigned_persona": "orchestrator"},
                {"action": "analyze_data", "parameters": {"data": "{content}", "query": "summarize this"}, "assigned_persona": "orchestrator"}
            ]
        }
        # 2. QA response (high-stakes)
        qa_response_content = {"approved": True, "feedback": "Plan looks good."}
        # 3. analyze_data tool response (low-stakes)
        analyze_data_response_content = "This is the summary."

        # Configure the mock to return different values on subsequent calls
        mock_create.side_effect = [
            AsyncMock(choices=[AsyncMock(message=AsyncMock(content=json.dumps(planner_response_content)))]),
            AsyncMock(choices=[AsyncMock(message=AsyncMock(content=json.dumps(qa_response_content)))]),
            AsyncMock(choices=[AsyncMock(message=AsyncMock(content=analyze_data_response_content)))]),
        ]

        # Act: Run the cognitive cycles
        await agi.execution_unit.handle_autonomous_cycle() # Creates plan
        await agi.execution_unit.handle_autonomous_cycle() # QA approves plan

        # Manually add file content to workspace for the next step
        active_goal = agi.ltm.get_active_goal()
        if active_goal:
             agi.workspaces[active_goal.id]["content"] = "This is the file content."

        await agi.execution_unit.handle_autonomous_cycle() # Executes read_file (no LLM call)
        await agi.execution_unit.handle_autonomous_cycle() # Executes analyze_data

        # Assert: Check the calls made to the mocked API
        assert mock_create.call_count >= 3, "Expected at least three calls to the chat completion API"

        # Check the planner call
        planner_call_kwargs = mock_create.call_args_list[0].kwargs
        assert planner_call_kwargs['model'] == config.HIGH_STAKES_MODEL

        # Check the ethical review call
        qa_call_kwargs = mock_create.call_args_list[1].kwargs
        assert qa_call_kwargs['model'] == config.HIGH_STAKES_MODEL

        # Check the analyze_data tool call
        tool_call_kwargs = mock_create.call_args_list[2].kwargs
        assert tool_call_kwargs['model'] == config.FAST_MODEL

    # Clean up
    await agi.shutdown()

Manual Verification Steps
Environment Variable Override:
Run the AGI with export FAST_MODEL="gpt-3.5-turbo" (or set on Windows).
Trigger a tool like analyze_data.
Check agi.log to confirm that the API request was made to gpt-3.5-turbo.
Prometheus Metrics:
Run the AGI and perform a few tasks.
Navigate to http://localhost:8000 in a browser.
Verify that the symbolic_agi_llm_token_usage_total metric shows labels for both the high-stakes and fast models, confirming that both tiers are being used and logged correctly.
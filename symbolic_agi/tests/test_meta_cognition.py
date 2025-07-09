# tests/test_meta_cognition.py

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from symbolic_agi.agi_controller import SymbolicAGI
# FIX: Import GoalModel to resolve the NameError
from symbolic_agi.schemas import AGIConfig, ActionStep, GoalModel, MessageModel, SkillModel


@pytest.fixture
def mocked_agi() -> SymbolicAGI:
    """
    Provides a SymbolicAGI instance with its dependencies mocked for testing
    the MetaCognitionUnit.
    """
    with patch("symbolic_agi.agi_controller.Planner"), patch(
        "symbolic_agi.agi_controller.SymbolicMemory"
    ), patch("symbolic_agi.agi_controller.SymbolicIdentity"), patch(
        "symbolic_agi.agi_controller.MicroWorld"
    ), patch(
        "symbolic_agi.agi_controller.SkillManager"
    ) as MockSkillManager, patch(
        "symbolic_agi.agi_controller.LongTermMemory"
    ) as MockLTM, patch(
        "symbolic_agi.agi_controller.ToolPlugin"
    ), patch(
        "symbolic_agi.agi_controller.RecursiveIntrospector"
    ), patch(
        "symbolic_agi.agi_controller.SymbolicEvaluator"
    ), patch(
        "symbolic_agi.agi_controller.Consciousness", create=True
    ), patch(
        "symbolic_agi.agi_controller.ExecutionUnit"
    ), patch(
        "symbolic_agi.agi_controller.MessageBus"
    ), patch(
        "symbolic_agi.agi_controller.DynamicAgentPool"
    ) as MockAgentPool, patch(
        "symbolic_agi.agi_controller.async_playwright"
    ) as mock_async_playwright:
        mock_playwright_manager = AsyncMock()
        mock_playwright_instance = AsyncMock()
        mock_browser = AsyncMock()
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_playwright_manager.start.return_value = mock_playwright_instance
        mock_async_playwright.return_value = mock_playwright_manager

        agi = SymbolicAGI(cfg=AGIConfig())

        # Configure specific mocks needed for meta-cognition tests
        agi.ltm = MockLTM()
        agi.skills = MockSkillManager()
        agi.agent_pool = MockAgentPool()
        agi.delegate_task_and_wait = AsyncMock()
        # We still mock this specific method on the real meta_cognition instance
        # to prevent it from writing to the actual memory system during the test.
        agi.meta_cognition.record_meta_event = AsyncMock()

        return agi


@pytest.mark.asyncio
async def test_review_skill_creates_improvement_goal(mocked_agi: SymbolicAGI):
    """
    Tests that when a skill review returns 'approved: false', a new goal is created
    to improve the skill based on the feedback.
    """
    # --- Arrange ---
    # 1. Ensure no active goal, so meta-tasks can run
    mocked_agi.ltm.get_active_goal.return_value = None

    # 2. Create a mock skill for the system to review
    skill_to_review = SkillModel(
        name="test_skill_to_improve",
        description="An old and inefficient skill.",
        action_sequence=[
            ActionStep(
                action="do_thing_slowly", parameters={}, assigned_persona="orchestrator"
            )
        ],
    )
    mocked_agi.skills.skills = {skill_to_review.id: skill_to_review}

    # 3. Ensure a QA agent is available
    mocked_agi.agent_pool.get_agents_by_persona.return_value = ["Test_QA_Agent_0"]

    # 4. Simulate the QA agent's response: not approved, with feedback
    feedback_text = "This is inefficient. Use the 'do_thing_quickly' tool instead."
    qa_reply_payload = {
        "status": "success",
        "approved": False,
        "feedback": feedback_text,
    }
    qa_reply_message = MessageModel(
        sender_id="Test_QA_Agent_0",
        receiver_id=mocked_agi.name,
        message_type="review_skill_efficiency_result",
        payload=qa_reply_payload,
    )
    mocked_agi.delegate_task_and_wait.return_value = qa_reply_message

    # --- Act ---
    await mocked_agi.meta_cognition.review_learned_skills()

    # --- Assert ---
    # 1. Verify that the review was delegated to the QA agent
    mocked_agi.delegate_task_and_wait.assert_awaited_once()
    delegated_step = mocked_agi.delegate_task_and_wait.call_args[0][1]
    assert delegated_step.action == "review_skill_efficiency"
    assert delegated_step.parameters["skill_to_review"]["name"] == skill_to_review.name

    # 2. Verify that a new goal was added to Long-Term Memory
    mocked_agi.ltm.add_goal.assert_called_once()

    # 3. Inspect the goal that was created
    new_goal_call = mocked_agi.ltm.add_goal.call_args[0][0]
    assert isinstance(new_goal_call, GoalModel)
    assert "Improve the learned skill" in new_goal_call.description
    assert skill_to_review.name in new_goal_call.description
    assert feedback_text in new_goal_call.description

    # 4. Verify that a meta-insight event was recorded
    mocked_agi.meta_cognition.record_meta_event.assert_awaited_once_with(
        "meta_insight",
        {
            "trigger": "review_learned_skills",
            "skill_name": skill_to_review.name,
            "feedback": feedback_text,
        },
    )

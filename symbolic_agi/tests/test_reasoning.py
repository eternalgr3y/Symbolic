# tests/test_reasoning.py

import pytest
import json
from unittest.mock import MagicMock, AsyncMock

from symbolic_agi.advanced_reasoning_system import (
    AdvancedReasoningEngine,
    ReasoningContext,
    ReasoningType,
    ReasoningStep
)

@pytest.fixture
def reasoning_engine(mocker):
    """Provides an AdvancedReasoningEngine with mocked dependencies."""
    mock_kb = mocker.AsyncMock()
    mock_kb.query_knowledge.return_value = []
    return AdvancedReasoningEngine(knowledge_base=mock_kb)

@pytest.fixture
def base_context():
    """Provides a default ReasoningContext for tests."""
    return ReasoningContext(goal="test", constraints=[], available_knowledge={})

@pytest.mark.asyncio
async def test_llm_analyze_problem(reasoning_engine, base_context, mocker):
    """
    Tests that the LLM-based problem analysis correctly calls the API
    and parses the JSON response.
    """
    mock_response_content = {
        "uncertainty": 0.8,
        "creativity_required": 0.2,
        "causality_focus": 0.1,
        "data_driven": 0.9,
        "analogical_potential": 0.4
    }
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(mock_response_content)
    mock_api_response = MagicMock()
    mock_api_response.choices = [mock_choice]

    mocker.patch('symbolic_agi.advanced_reasoning_system.monitored_chat_completion', return_value=mock_api_response)

    analysis = await reasoning_engine._llm_analyze_problem("Analyze sales data", base_context)

    assert analysis == mock_response_content

def test_select_strategies_from_llm_analysis(reasoning_engine):
    """
    Tests the strategy selection logic based on the new LLM analysis format.
    """
    analysis = {
        "uncertainty": 0.9,
        "creativity_required": 0.8,
        "causality_focus": 0.1,
        "data_driven": 0.7,
        "analogical_potential": 0.6
    }
    strategies = reasoning_engine._select_strategies(analysis)

    assert set(strategies) == {
        ReasoningType.DEDUCTIVE,
        ReasoningType.PROBABILISTIC,
        ReasoningType.ABDUCTIVE,
        ReasoningType.INDUCTIVE,
        ReasoningType.ANALOGICAL
    }

@pytest.mark.asyncio
async def test_execute_strategy_llm_call(reasoning_engine, base_context, mocker):
    """
    Tests that executing a strategy correctly calls the LLM with the right prompt
    and parses the resulting ReasoningStep.
    """
    mock_response_content = {
        "premise": "The problem is X.",
        "conclusion": "Therefore, Y.",
        "confidence": 0.85,
        "evidence": [{"type": "logical"}],
        "assumptions": ["X is true"]
    }
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(mock_response_content)
    mock_api_response = MagicMock()
    mock_api_response.choices = [mock_choice]

    mocked_api_call = mocker.patch('symbolic_agi.advanced_reasoning_system.monitored_chat_completion', return_value=mock_api_response)

    step = await reasoning_engine._execute_strategy(ReasoningType.DEDUCTIVE, "Solve for X", base_context)

    assert isinstance(step, ReasoningStep)
    assert step.reasoning_type == ReasoningType.DEDUCTIVE
    assert step.conclusion == "Therefore, Y."
    assert step.confidence == pytest.approx(0.85)
    mocked_api_call.assert_called_once()

@pytest.mark.asyncio
async def test_synthesize_chain_llm_call(reasoning_engine, mocker):
    """
    Tests that the synthesis step correctly calls the LLM with a summary of
    previous steps and parses the final conclusion.
    """
    mock_steps = [
        ReasoningStep("deductive_1", ReasoningType.DEDUCTIVE, "p1", "c1", 0.9, [], []),
        ReasoningStep("inductive_1", ReasoningType.INDUCTIVE, "p2", "c2", 0.7, [], [])
    ]

    mock_response_content = {
        "final_conclusion": "The final synthesized answer is Z.",
        "overall_confidence": 0.88,
        "alternatives_considered": ["An alternative was W."]
    }
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(mock_response_content)
    mock_api_response = MagicMock()
    mock_api_response.choices = [mock_choice]

    mocker.patch('symbolic_agi.advanced_reasoning_system.monitored_chat_completion', return_value=mock_api_response)

    chain = await reasoning_engine._synthesize_chain(mock_steps, "Original problem")

    assert chain.final_conclusion == "The final synthesized answer is Z."
    assert chain.overall_confidence == pytest.approx(0.88)
    assert len(chain.steps) == 2
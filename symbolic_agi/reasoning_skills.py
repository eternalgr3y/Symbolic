"""
Reasoning skills that work with your EXISTING agent system
"""

from typing import Dict, Any
import logging
from .skill_manager import register_innate_action
from .advanced_reasoning_system import (
    AdvancedReasoningEngine,
    ReasoningContext
)

# Shared reasoning engine
_reasoning_engine = AdvancedReasoningEngine()

@register_innate_action("reasoning", "Analyzes problems using advanced reasoning")
async def skill_reason_about_problem(params: Dict[str, Any]) -> Dict[str, Any]:
    """Any agent can use this skill"""
    try:
        problem = params.get("problem", "")
        context = ReasoningContext(
            goal=f"Solve: {problem}",
            constraints=params.get("constraints", []),
            available_knowledge=params.get("knowledge", {})
        )
        
        result = await _reasoning_engine.reason(problem, context)
        
        return {
            "status": "success",
            "conclusion": result.final_conclusion,
            "confidence": result.overall_confidence
        }
    except Exception as e:
        return {"status": "failure", "error": str(e)}
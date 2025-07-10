"""
Reasoning Agent that extends the base Agent class
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List

from .agent import Agent
from .skill_manager import register_innate_action
from .advanced_reasoning_system import (
    AdvancedReasoningEngine,
    ReasoningContext,
    ReasoningType
)
from .schemas import MessageModel

class ReasoningAgent(Agent):
    """Agent with advanced reasoning capabilities"""

    def __init__(self, name: str, message_bus, api_client, reasoning_engine: Optional[AdvancedReasoningEngine] = None):
        super().__init__(name, message_bus, api_client)

        # V2 CHANGE: Pass the api_client to the reasoning engine
        if reasoning_engine is None:
            reasoning_engine = AdvancedReasoningEngine(api_client=self.client)

        self.reasoning_engine = reasoning_engine
        self.reasoning_history = []

        logging.info(f"ReasoningAgent '{name}' initialized with V2 Reasoning Engine")

    @register_innate_action("reasoning", "Performs advanced multi-strategy reasoning")
    async def skill_advanced_reasoning(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform reasoning on complex problems
        Integrates with ethical governor through tool_plugin
        """
        try:
            problem = params.get("problem", "")
            constraints = params.get("constraints", [])
            knowledge = params.get("knowledge", {})

            # Create reasoning context
            context = ReasoningContext(
                goal=f"Solve: {problem}",
                constraints=constraints,
                available_knowledge=knowledge
            )

            # Perform reasoning
            chain = await self.reasoning_engine.reason(problem, context)

            # Store in history
            self.reasoning_history.append({
                "problem": problem,
                "chain": chain,
                "timestamp": asyncio.get_event_loop().time()
            })

            return {
                "status": "success",
                "conclusion": chain.final_conclusion,
                "confidence": chain.overall_confidence,
                "reasoning_steps": [
                    {
                        "type": step.reasoning_type.value,
                        "premise": step.premise,
                        "conclusion": step.conclusion,
                        "confidence": step.confidence
                    }
                    for step in chain.steps
                ],
                "alternatives": chain.alternatives_considered
            }

        except Exception as e:
            logging.error(f"Reasoning failed: {e}")
            return {
                "status": "failure",
                "error": str(e)
            }

    @register_innate_action("reasoning", "Uses reasoning to enhance tool usage")
    async def skill_reason_about_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use reasoning to decide which tools to use and how
        This connects reasoning with your existing tool ecosystem
        """
        try:
            task = params.get("task", "")
            available_tools = params.get("available_tools", [])

            # Reason about tool selection
            tool_problem = f"Which tools should I use for: {task}? Available: {available_tools}"

            context = ReasoningContext(
                goal="Select optimal tools",
                constraints=["Use only available tools", "Consider efficiency"],
                available_knowledge={"tools": available_tools, "task": task}
            )

            chain = await self.reasoning_engine.reason(tool_problem, context)

            # Extract tool recommendations
            tool_plan = []
            for step in chain.steps:
                if "tool" in step.conclusion.lower():
                    tool_plan.append({
                        "tool": self._extract_tool_name(step.conclusion),
                        "reason": step.premise,
                        "confidence": step.confidence
                    })

            return {
                "status": "success",
                "tool_plan": tool_plan,
                "reasoning": chain.final_conclusion,
                "confidence": chain.overall_confidence
            }

        except Exception as e:
            return {"status": "failure", "error": str(e)}

    def _extract_tool_name(self, conclusion: str) -> str:
        """Extract tool name from reasoning conclusion"""
        # Simple implementation - can be enhanced
        tools = ["web_search", "browse_webpage", "analyze_data", "execute_python_code", 
                 "manage_nordvpn", "geo_research", "chain_of_thought_reasoning"]

        for tool in tools:
            if tool in conclusion.lower():
                return tool

        return "unknown_tool"
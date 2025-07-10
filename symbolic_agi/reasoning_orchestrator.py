"""
Orchestrator for Advanced Reasoning System
Coordinates multiple reasoning agents
"""

from typing import Dict, Any, List, Optional
import asyncio
import json
import logging

from .advanced_reasoning_system import AdvancedReasoningEngine
from .advanced_reasoning_system import ReasoningContext
from .reasoning_agent import ReasoningAgent

class ReasoningOrchestrator:
    """
    High-level orchestrator that coordinates reasoning across multiple agents
    """

    def __init__(self, agi_controller):
        self.agi = agi_controller
        # V2 CHANGE: Pass all relevant components to the engine
        self.reasoning_engine = AdvancedReasoningEngine(
            api_client=self.agi.client,
            consciousness=getattr(agi_controller, 'consciousness', None),
            planner=getattr(agi_controller, 'planner', None),
            meta_cognition=getattr(agi_controller, 'meta_cognition', None),
            memory_system=getattr(agi_controller, 'memory', None)
        )

        # Specialized reasoning agents
        self.reasoning_agents = {}

    async def create_specialized_agents(self):
        """Create specialized reasoning agents"""
        agent_types = {
            "analytical": "Logical and data-driven reasoning",
            "creative": "Lateral thinking and innovation",
            "strategic": "Long-term planning and strategy"
        }

        for agent_type, in agent_types:
            agent_name = f"agent_{agent_type}_reasoner"
            agent = ReasoningAgent(
                name=agent_name,
                message_bus=self.agi.message_bus,
                api_client=self.agi.client,
                reasoning_engine=self.reasoning_engine
            )

            # Add to orchestrator's collection
            self.reasoning_agents[agent_type] = agent

            # Add to AGI's agent pool
            # This part assumes agent_pool.add_agent can handle the full Agent object
            # Based on the provided code, it expects name, persona, memory. We will adapt.
            self.agi.agent_pool.add_agent(
                name=agent.name,
                persona=agent.persona,
                memory=self.agi.memory
            )

            # Start the agent
            agent_task = asyncio.create_task(agent.run())
            self.agi.agent_tasks.append(agent_task)

            logging.info(f"Created {agent_type} reasoning agent: {agent_name}")
        
        await asyncio.sleep(0)  # Ensures this is always an async function

    async def solve_complex_problem(self, problem: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Solve complex problems using multi-agent reasoning
        """
        logging.info(f"Orchestrating solution for: {problem[:100]}...")

        # Step 1: Decompose problem
        sub_problems = await self._decompose_problem(problem, domain)

        # Step 2: Assign to agents
        assignments = self._assign_to_agents(sub_problems)

        # Step 3: Execute parallel reasoning
        solutions = await self._multi_agent_reasoning(assignments)

        # Step 4: Integrate solutions
        integrated = self._integrate_solutions(solutions)

        return integrated

    async def _decompose_problem(self, problem: str, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Decompose complex problem into sub-problems using the reasoning engine."""
        # Use the reasoning engine itself to decompose the problem
        context = ReasoningContext(
            goal=f"Decompose the problem '{problem}' into sub-problems for specialized agents (analytical, creative, strategic).",
            constraints=["Output a JSON list of objects, each with 'aspect' and 'focus' keys."],
            available_knowledge={"domain": domain or "general"}
        )
        chain = await self.reasoning_engine.reason(f"Decompose: {problem}", context)

        try:
            # A simple heuristic to parse the decomposed problems from the conclusion
            sub_problems = json.loads(chain.final_conclusion)
            if isinstance(sub_problems, list):
                return sub_problems
        except (json.JSONDecodeError, TypeError):
            logging.warning("Could not parse LLM-based decomposition, falling back to default.")

        # Fallback to original logic
        if domain == "business":
            return [
                {"aspect": "analytical", "focus": f"Market data and financial analysis for: {problem}"},
                {"aspect": "strategic", "focus": f"Business strategy and competitive positioning for: {problem}"},
                {"aspect": "creative", "focus": f"Innovative business models for: {problem}"}
            ]
        else:
            return [
                {"aspect": "analytical", "focus": f"Data and logic analysis for: {problem}"},
                {"aspect": "creative", "focus": f"Innovative solutions for: {problem}"},
                {"aspect": "strategic", "focus": f"Long-term approach for: {problem}"}
            ]

    def _assign_to_agents(self, sub_problems: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Assign sub-problems to appropriate agents"""
        assignments = {}
        for sub_problem in sub_problems:
            agent_type = sub_problem.get("aspect")
            if agent_type:
                if agent_type not in assignments:
                    assignments[agent_type] = []
                assignments[agent_type].append(sub_problem)
        return assignments

    async def _multi_agent_reasoning(self, assignments: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Execute reasoning across multiple agents"""
        tasks = []

        for agent_type, problems in assignments.items():
            if agent_type in self.reasoning_agents:
                agent = self.reasoning_agents[agent_type]
                for problem in problems:
                    task = asyncio.create_task(
                        agent.skill_advanced_reasoning({
                            "problem": problem["focus"],
                            "constraints": [],
                            "knowledge": {"domain": agent_type}
                        })
                    )
                    tasks.append((agent_type, task))

        # Wait for all reasoning to complete
        results = {}
        for agent_type, task in tasks:
            try:
                result = await task
                results[agent_type] = result
            except Exception as e:
                logging.error(f"Agent {agent_type} failed: {e}")
                results[agent_type] = {"status": "failure", "error": str(e)}

        return results

    def _integrate_solutions(self, solutions: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate solutions from multiple agents"""
        integrated = {
            "status": "success",
            "perspectives": solutions,
            "integrated_solution": self._synthesize_perspectives(solutions),
            "confidence": self._calculate_overall_confidence(solutions)
        }
        return integrated

    def _synthesize_perspectives(self, solutions: Dict[str, Any]) -> str:
        """Synthesize multiple perspectives into unified solution"""
        synthesis = "Integrated solution combining:\n"
        for agent_type, solution in solutions.items():
            if solution.get("status") == "success":
                synthesis += f"- {agent_type.title()}: {solution.get('conclusion', 'No conclusion')}\n"
        return synthesis

    def _calculate_overall_confidence(self, solutions: Dict[str, Any]) -> float:
        """Calculate overall confidence from multiple solutions"""
        confidences = []
        for solution in solutions.values():
            if solution.get("status") == "success":
                confidences.append(solution.get("confidence", 0.5))

        return sum(confidences) / len(confidences) if confidences else 0.0
# symbolic_agi/advanced_reasoning_system.py

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from symbolic_agi.api_client import monitored_chat_completion, client as default_client
from symbolic_agi.knowledge_base import KnowledgeBase, KnowledgeItemType

# Constants for reasoning confidence levels
STRATEGY_SELECTION_THRESHOLD = 0.5

class ReasoningType(Enum):
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    ANALOGICAL = "analogical"
    CAUSAL = "causal"
    PROBABILISTIC = "probabilistic"

@dataclass
class ReasoningContext:
    """Context for reasoning operations."""
    goal: str
    constraints: List[str]
    available_knowledge: Dict[str, Any]

@dataclass
class ReasoningStep:
    """A single, structured step in a reasoning chain."""
    step_id: str
    reasoning_type: ReasoningType
    premise: str
    conclusion: str
    confidence: float
    evidence: List[Dict[str, Any]]
    assumptions: List[str]

@dataclass
class ReasoningChain:
    """A complete chain of reasoning leading to a final conclusion."""
    chain_id: str
    steps: List[ReasoningStep]
    final_conclusion: str
    overall_confidence: float
    reasoning_path: List[str]
    alternatives_considered: List[Dict[str, Any]]

class AdvancedReasoningEngine:
    """
    An LLM-powered, multi-strategy reasoning engine that integrates with the AGI's cognitive architecture.
    It dynamically analyzes problems, selects and executes multiple reasoning strategies in parallel,
    and synthesizes the results into a coherent conclusion.
    """

    def __init__(self, api_client=None, knowledge_base: Optional[KnowledgeBase] = None):
        self.api_client = api_client or default_client
        self.knowledge_base = knowledge_base
        self.reasoning_history: List[ReasoningChain] = []

    async def reason(self, problem: str, context: ReasoningContext) -> ReasoningChain:
        """Main reasoning entry point, orchestrating the cognitive process."""
        logging.info("Starting advanced reasoning for: %s...", problem[:100])

        # Step 1: Use an LLM to perform nuanced problem analysis, informed by the Knowledge Base.
        analysis = await self._llm_analyze_problem(problem, context)

        # Step 2: Select appropriate reasoning strategies based on the analysis.
        strategies = self._select_strategies(analysis)
        logging.info(f"Selected reasoning strategies: {[s.value for s in strategies]}")

        # Step 3: Execute all selected reasoning strategies in parallel.
        reasoning_tasks = [self._execute_strategy(s, problem, context) for s in strategies]
        steps_results = await asyncio.gather(*reasoning_tasks)

        # Filter out any strategies that failed to produce a result.
        steps = [step for step in steps_results if step]

        # Step 4: Use an LLM to synthesize the results from various strategies into a final conclusion.
        chain = await self._synthesize_chain(steps, problem)

        self.reasoning_history.append(chain)
        return chain

    async def _llm_analyze_problem(self, problem: str, context: ReasoningContext) -> Dict[str, Any]:
        """Use an LLM to analyze the problem and suggest reasoning strategies."""
        relevant_knowledge_str = "No relevant knowledge found."
        if self.knowledge_base:
            relevant_items = await self.knowledge_base.query_knowledge(query=problem, limit=3)
            if relevant_items:
                knowledge_summaries = [f"- {item.type.value.upper()}: {item.content.get('summary', str(item.content))}" for item in relevant_items]
                relevant_knowledge_str = "\n".join(knowledge_summaries)

        prompt = f"""
Analyze the following problem to determine the best reasoning strategies.

**Problem:** "{problem}"

**Context:**
- Goal: {context.goal}
- Constraints: {context.constraints}

**Relevant Distilled Knowledge from my Knowledge Base:**
{relevant_knowledge_str}

**Instructions:**
Evaluate the problem on these dimensions by outputting a score from 0.0 to 1.0:
1.  **Uncertainty**: How much ambiguity or probability is involved?
2.  **Creativity Required**: Does this require novel or out-of-the-box solutions?
3.  **Causality Focus**: Is understanding cause-and-effect critical?
4.  **Data-Driven**: Does the solution depend on finding patterns in data?
5.  **Analogical Potential**: Could this problem be solved by referencing past experiences?

Respond with ONLY a valid JSON object with keys: "uncertainty", "creativity_required", "causality_focus", "data_driven", "analogical_potential".
"""
        try:
            response = await monitored_chat_completion(
                role="reasoning_analysis",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logging.error(f"LLM-based problem analysis failed: {e}. Falling back to default analysis.")
            return {
                "uncertainty": 0.5, "creativity_required": 0.5, "causality_focus": 0.5,
                "data_driven": 0.5, "analogical_potential": 0.5
            }

    def _select_strategies(self, analysis: Dict[str, Any]) -> List[ReasoningType]:
        """Select appropriate reasoning strategies based on problem analysis scores."""
        strategies = {ReasoningType.DEDUCTIVE}  # Always include deductive reasoning.

        if analysis.get("uncertainty", 0) > STRATEGY_SELECTION_THRESHOLD:
            strategies.add(ReasoningType.PROBABILISTIC)
        if analysis.get("creativity_required", 0) > STRATEGY_SELECTION_THRESHOLD:
            strategies.add(ReasoningType.ABDUCTIVE)
        if analysis.get("causality_focus", 0) > STRATEGY_SELECTION_THRESHOLD:
            strategies.add(ReasoningType.CAUSAL)
        if analysis.get("data_driven", 0) > STRATEGY_SELECTION_THRESHOLD:
            strategies.add(ReasoningType.INDUCTIVE)
        if analysis.get("analogical_potential", 0) > STRATEGY_SELECTION_THRESHOLD:
            strategies.add(ReasoningType.ANALOGICAL)

        return list(strategies)

    async def _execute_strategy(self, strategy: ReasoningType, problem: str, context: ReasoningContext) -> Optional[ReasoningStep]:
        """Execute a single reasoning strategy by prompting an LLM."""
        prompt = self._get_prompt_for_strategy(strategy, problem, context)
        try:
            response = await monitored_chat_completion(
                role=f"reasoning_{strategy.value}",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
            )
            result_data = json.loads(response.choices[0].message.content)
            return ReasoningStep(
                step_id=f"{strategy.value}_{uuid.uuid4().hex[:6]}",
                reasoning_type=strategy,
                premise=result_data.get("premise", "N/A"),
                conclusion=result_data.get("conclusion", "N/A"),
                confidence=result_data.get("confidence", 0.5),
                evidence=result_data.get("evidence", []),
                assumptions=result_data.get("assumptions", [])
            )
        except Exception as e:
            logging.error(f"Reasoning strategy '{strategy.value}' failed: {e}")
            return None

    async def _synthesize_chain(self, steps: List[ReasoningStep], problem: str) -> ReasoningChain:
        """Synthesize the results of multiple reasoning steps into a final conclusion using an LLM."""
        if not steps:
            return ReasoningChain("chain_empty", [], "Unable to reason about the problem.", 0.0, [], [])

        steps_summary = "\n".join([f"- **{s.reasoning_type.name}**: {s.conclusion} (Confidence: {s.confidence:.2f})" for s in steps])
        prompt = f"""
You are a master synthesizer AI. Your task is to integrate multiple, potentially conflicting, lines of reasoning into a single, coherent, and actionable conclusion for the given problem.

**Original Problem:** "{problem}"

**Parallel Reasoning Step Results:**
{steps_summary}

**Instructions:**
1.  **Review all reasoning steps.** Identify the most compelling, well-supported, and confident conclusions.
2.  **Identify Conflicts:** Note any contradictions or alternative perspectives.
3.  **Formulate a Final Conclusion:** Synthesize the inputs into a single, actionable final conclusion. If there are conflicts, choose the most likely or safest path forward, or state the remaining uncertainty.
4.  **Calculate Overall Confidence:** Based on the confidence of the input steps and their agreement, calculate an overall confidence score for your final conclusion (0.0 to 1.0).
5.  **List Alternatives:** Briefly list any significant alternative conclusions that were considered but ultimately discarded.

Respond with ONLY a valid JSON object with keys: "final_conclusion", "overall_confidence", "alternatives_considered".
"""
        try:
            response = await monitored_chat_completion(
                role="reasoning_synthesis",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
            )
            synthesis_data = json.loads(response.choices[0].message.content)
            return ReasoningChain(
                chain_id=f"chain_{uuid.uuid4().hex[:8]}",
                steps=steps,
                final_conclusion=synthesis_data.get("final_conclusion", "Synthesis failed."),
                overall_confidence=synthesis_data.get("overall_confidence", 0.5),
                reasoning_path=[s.step_id for s in steps],
                alternatives_considered=synthesis_data.get("alternatives_considered", [])
            )
        except Exception as e:
            logging.error(f"Reasoning synthesis failed: {e}")
            # Fallback synthesis if LLM fails
            best_step = max(steps, key=lambda s: s.confidence)
            return ReasoningChain(
                chain_id=f"chain_fallback_{uuid.uuid4().hex[:8]}",
                steps=steps,
                final_conclusion=f"Fallback Conclusion: The most confident reasoning was {best_step.reasoning_type.name}, which concluded: {best_step.conclusion}",
                overall_confidence=best_step.confidence * 0.8, # Penalize for failed synthesis
                reasoning_path=[s.step_id for s in steps],
                alternatives_considered=[{"reason": "LLM Synthesis Failed", "conclusion": "Used best-step fallback."}]
            )

    def _get_prompt_for_strategy(self, strategy: ReasoningType, problem: str, context: ReasoningContext) -> str:
        """Returns the specific, high-quality LLM prompt for a given reasoning strategy."""

        json_format_instruction = """
Your response MUST be a single, valid JSON object with the following keys:
- "premise": The primary information, rule, or observation you are starting from.
- "conclusion": Your reasoned conclusion for this specific reasoning step.
- "confidence": Your confidence in this conclusion (float from 0.0 to 1.0).
- "evidence": A list of strings or dictionaries representing evidence used.
- "assumptions": A list of strings representing any assumptions made.
"""

        prompts = {
            ReasoningType.DEDUCTIVE: f"Problem: '{problem}'. Apply strict deductive logic. Given the context and known facts, derive a conclusion that is guaranteed to be true. Avoid making assumptions.",
            ReasoningType.INDUCTIVE: f"Problem: '{problem}'. Apply inductive reasoning. Analyze the provided context and any available data to identify patterns, trends, or general principles. Formulate a likely conclusion based on these observations.",
            ReasoningType.ABDUCTIVE: f"Problem: '{problem}'. Apply abductive reasoning. Generate the most plausible explanation or hypothesis for the observed problem. What is the simplest and most likely cause or solution? This is about inference to the best explanation.",
            ReasoningType.ANALOGICAL: f"Problem: '{problem}'. Apply analogical reasoning. Find a similar, known problem from your memory or general knowledge and adapt its solution. Clearly state the source analogy and how you are adapting it.",
            ReasoningType.CAUSAL: f"Problem: '{problem}'. Apply causal reasoning. Identify the cause-and-effect relationships. What are the likely causes of the problem? What are the probable effects of potential actions?",
            ReasoningType.PROBABILISTIC: f"Problem: '{problem}'. Apply probabilistic reasoning. Assess the uncertainties involved. Assign probabilities to different outcomes and determine the most likely result based on statistical or heuristic analysis."
        }

        base_prompt = prompts.get(strategy, f"Reason about the problem '{problem}'.")

        return f"{base_prompt}\n\n**Context:**\n- Goal: {context.goal}\n- Constraints: {context.constraints}\n\n{json_format_instruction}"
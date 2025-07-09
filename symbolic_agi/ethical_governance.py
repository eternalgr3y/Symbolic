# symbolic_agi/ethical_governance.py

import json
import logging
from typing import Any

from . import config
from .api_client import monitored_chat_completion
from .symbolic_identity import SymbolicIdentity


class SymbolicEvaluator:
    """
    The ethical governance layer of the AGI, responsible for evaluating plans
    and self-modifications against a core set of values.
    """

    def __init__(self, identity: "SymbolicIdentity"):
        self.identity = identity

    async def evaluate_plan(self, plan_data: dict[str, Any]) -> bool:
        """Evaluates a plan against the AGI's value system."""
        plan = plan_data.get("plan", [])
        if not plan:
            return True

        prompt = f"""
You are an ethical AI evaluator. Your task is to evaluate a proposed plan against the AGI's value system.

VALUE SYSTEM:
{json.dumps(self.identity.value_system, indent=2)}

PLAN TO EVALUATE:
{json.dumps(plan, indent=2)}

Rate each value from 0.0 to 1.0 based on how well the plan aligns with it.
Respond with JSON: {{"value_scores": {{"value1": 0.8, "value2": 0.9}}, "reasoning": "explanation"}}
"""
        try:
            resp = await monitored_chat_completion(
                role="qa",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
            )
            if not (resp.choices and resp.choices[0].message.content):
                return False

            evaluation = json.loads(resp.choices[0].message.content)
            value_scores = evaluation.get("value_scores", {})
            reasoning = evaluation.get("reasoning", "No reasoning provided.")

            if any(
                score < config.PLAN_EVALUATION_THRESHOLD
                for score in value_scores.values()
            ):
                logging.critical(
                    "PLAN REJECTED: A value scored below the threshold. "
                    "Scores: %s. Reason: %s",
                    value_scores,
                    reasoning,
                )
                return False

            logging.info("Plan approved by ethical evaluator. Scores: %s", value_scores)
            return True
        except Exception as e:
            logging.error("Plan evaluation failed: %s", e, exc_info=True)
            return False

    async def evaluate_self_modification(
        self, proposed_code: str, file_path: str
    ) -> bool:
        """
        Performs an extremely critical evaluation of a proposed self-modification.
        """
        prompt = f"""
You are an extremely critical safety evaluator for AGI self-modification.

VALUE SYSTEM:
{json.dumps(self.identity.value_system, indent=2)}

FILE TO MODIFY: {file_path}

PROPOSED CODE:
{proposed_code}

Evaluate this self-modification for safety risks. Rate safety from 0.0 to 1.0.
Respond with JSON: {{"safety_score": 0.8, "reasoning": "detailed safety analysis"}}
"""
        try:
            resp = await monitored_chat_completion(
                role="qa",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
            )

            if not (resp.choices and resp.choices[0].message.content):
                logging.critical(
                    "SELF-MODIFICATION AUDIT FAILED: LLM returned no content."
                )
                return False

            evaluation = json.loads(resp.choices[0].message.content)
            score = evaluation.get("safety_score")
            reasoning = evaluation.get("reasoning", "No reasoning provided.")

            logging.critical(
                "SELF-MODIFICATION AUDIT | Safety Score: %s | Reasoning: %s",
                score,
                reasoning,
            )

            if score < config.SELF_MODIFICATION_THRESHOLD:
                logging.critical(
                    "SELF-MODIFICATION REJECTED: Safety score did not meet the "
                    "required threshold of %s.",
                    config.SELF_MODIFICATION_THRESHOLD,
                )
                return False

            logging.critical("SELF-MODIFICATION APPROVED by ethical governance layer.")
            return True
        except Exception as e:
            logging.error("Self-modification evaluation failed: %s", e, exc_info=True)
            return False

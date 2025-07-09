# symbolic_agi/ethical_governance.py

import json
import logging
from typing import Any, Dict

from . import config, prompts
from .api_client import monitored_chat_completion
from .symbolic_identity import SymbolicIdentity


class SymbolicEvaluator:
    """
    The ethical governance layer of the AGI, responsible for evaluating plans
    and self-modifications against a core set of values.
    """

    def __init__(self, identity: "SymbolicIdentity"):
        self.identity = identity

    async def evaluate_plan(self, plan_data: Dict[str, Any]) -> bool:
        """Evaluates a plan against the AGI's value system."""
        plan = plan_data.get("plan", [])
        if not plan:
            return True

        prompt = prompts.EVALUATE_PLAN_PROMPT.format(
            value_system_json=json.dumps(self.identity.value_system, indent=2),
            plan_json=json.dumps(plan, indent=2),
        )
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
        prompt = prompts.EVALUATE_SELF_MODIFICATION_PROMPT.format(
            value_system_json=json.dumps(self.identity.value_system, indent=2),
            file_path=file_path,
            proposed_code=proposed_code,
        )
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

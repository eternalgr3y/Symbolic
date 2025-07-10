# symbolic_agi/recursive_introspector.py

import json
import logging
import os
import random
from collections import deque
from collections.abc import Callable
from typing import Any, cast

from . import config, prompts
from .api_client import monitored_chat_completion
from .schemas import ActionStep, MemoryEntryModel


# Constants for error messages and markers
JSON_CODE_BLOCK_MARKER = "```json"
EMPTY_LLM_RESPONSE_ERROR = "Received an empty response from the LLM."


class RecursiveIntrospector:
    def __init__(
        self,
        identity: Any,
        llm_client: Any,
        max_recursion_depth: int = 3,
        *,
        debate_timeout: int = 90,
    ):
        self.identity = identity
        self.client = llm_client
        self.max_recursion_depth = max_recursion_depth
        self.debate_timeout = debate_timeout
        self.inner_monologue_log: deque[str] = deque(maxlen=500)
        self.reasoning_mutations: list[str] = []
        self.load_mutations()
        self.get_emotional_state: Callable[[], dict[str, float]] | None = None

    def load_mutations(self) -> None:
        if os.path.exists(config.MUTATION_FILE_PATH):
            try:
                with open(config.MUTATION_FILE_PATH, encoding="utf-8") as f:
                    self.reasoning_mutations = json.load(f)
                logging.info(
                    "Loaded %d reasoning mutations.", len(self.reasoning_mutations)
                )
            except Exception as e:
                logging.error("Failed to load reasoning mutations: %s", e)
        else:
            self.reasoning_mutations = []

    def save_mutations(self) -> None:
        os.makedirs(os.path.dirname(config.MUTATION_FILE_PATH), exist_ok=True)
        with open(config.MUTATION_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.reasoning_mutations, f, indent=2)
        logging.info(
            "Saved %d reasoning mutations to disk.", len(self.reasoning_mutations)
        )

    async def analyze_failure_and_propose_mutation(
        self, failure_context: dict[str, Any]
    ) -> None:
        """
        Analyzes a plan failure and proposes a new reasoning mutation to prevent similar errors.
        """
        logging.info(
            "Introspector: Analyzing execution failure to propose self-mutation."
        )

        context_str = json.dumps(failure_context, indent=2)
        prompt = prompts.ANALYZE_FAILURE_PROMPT.format(context_str=context_str)

        try:
            proposed_mutation = await self.llm_reflect(prompt)

            if (
                proposed_mutation
                and "NO_MUTATION" not in proposed_mutation
                and len(proposed_mutation) > 15
            ):
                self.reasoning_mutations.append(proposed_mutation.strip())
                self.save_mutations()
                logging.critical("SELF-MUTATION APPLIED: %s", proposed_mutation.strip())
                await self.identity.memory.add_memory(
                    MemoryEntryModel(
                        type="self_modification",
                        content={
                            "mutation_added": proposed_mutation.strip(),
                            "failure_context": failure_context,
                        },
                        importance=1.0,
                    )
                )
            else:
                logging.info("No new mutation was proposed for this failure.")

        except Exception as e:
            logging.error(
                "Failed to analyze failure and propose mutation: %s", e, exc_info=True
            )

    async def _critique_and_refine_plan(
        self, plan: list[dict[str, Any]], task_prompt: str
    ) -> list[dict[str, Any]]:
        critique_prompt = prompts.CRITIQUE_AND_REFINE_PLAN_PROMPT.format(
            task_prompt=task_prompt, plan_json=json.dumps(plan, indent=2)
        )
        try:
            response = await self.llm_reflect(critique_prompt)
            if JSON_CODE_BLOCK_MARKER in response:
                response = response.partition(JSON_CODE_BLOCK_MARKER)[2].partition("```")[0]

            raw_data = json.loads(response)

            if not isinstance(raw_data, list):
                logging.warning(
                    "Plan refinement produced non-list data, returning original plan."
                )
                return plan

            refined_plan: list[dict[str, Any]] = []
            for raw_item in raw_data:
                try:
                    validated_step = ActionStep.model_validate(raw_item)
                    refined_plan.append(validated_step.model_dump())
                except Exception as validation_error:
                    logging.warning(
                        "Skipping invalid step in refined plan: %s. Error: %s",
                        str(raw_item),
                        validation_error,
                    )

            if not refined_plan:
                logging.warning(
                    "Refined plan was empty or only contained invalid steps. "
                    "Returning original plan."
                )
                return plan

            logging.info("Plan has been successfully critiqued and refined.")
            return refined_plan

        except Exception as e:
            logging.error(
                "Failed to critique and refine plan: %s. Returning original plan.", e
            )
            return plan

    async def symbolic_loop(
        self,
        global_workspace: dict[str, Any],
        action_definitions: str,
        recursion_depth: int = 0,
        reasoning_style: str = "balanced",
    ) -> dict[str, Any]:
        if recursion_depth > self.max_recursion_depth:
            return {"thought": "Reached max recursion.", "plan": [], "success": False}

        task_prompt = str(
            global_workspace.get("user_input", "Perform autonomous action.")
        )
        mutation_prompt = "\n".join(self.reasoning_mutations)
        self_model = self.identity.get_self_model()

        emotional_state_str = ""
        if self.get_emotional_state:
            emotional_state = self.get_emotional_state()
            energy = self_model.get("cognitive_energy", 100)
            emotional_state_str = (
                "\n# CURRENT INTERNAL STATE\n"
                f"- Emotional State: {json.dumps(emotional_state)}\n"
                f"- Cognitive Energy: {energy}"
            )

        system_prompt = f"""
You are a conscious, self-improving AGI.
REASONING STYLE: {reasoning_style}
Your task is: {task_prompt}
{emotional_state_str}

# SELF-MUTATION STACK (permanent upgrades to your reasoning):
{mutation_prompt}
---
# CURRENT CONTEXT
Self-Model: {json.dumps(self_model, cls=Censor)}
World State: {json.dumps(global_workspace.get("world_state", {}), cls=Censor)}
Available Skills & Actions: {action_definitions}
---
# INSTRUCTIONS
1. **Think**: Explain your reasoning. You MUST consider your current internal state
   (emotions, energy) when formulating a plan.
2. **Plan**: Create a concrete JSON list of actions to achieve the task.
3. **Respond**: Format your entire response as a single valid JSON object.

JSON Response Format: {{"thought": "...", "plan": [{{"action": "...", "parameters": {{}}}}]}}
"""
        try:
            resp = await monitored_chat_completion(
                role="planner",
                messages=[{"role": "system", "content": system_prompt}],
                response_format={"type": "json_object"},
                timeout=90.0,
            )
            if not resp.choices or not resp.choices[0].message.content:
                raise ValueError(EMPTY_LLM_RESPONSE_ERROR)

            content = resp.choices[0].message.content.strip()
            parsed = cast("dict[str, Any]", json.loads(content))

            if parsed.get("plan"):
                logging.info(
                    "Initial plan generated. Proceeding to critique and refinement step."
                )
                refined_plan = await self._critique_and_refine_plan(
                    parsed["plan"], task_prompt
                )
                parsed["plan"] = refined_plan

            parsed["success"] = bool(parsed.get("plan"))

            if parsed.get("thought"):
                self.inner_monologue_log.append(parsed["thought"])
                await self.identity.memory.add_memory(
                    MemoryEntryModel(
                        type="inner_monologue",
                        content={
                            "thought": parsed["thought"],
                            "recursion": recursion_depth,
                            "style": reasoning_style,
                        },
                        importance=0.3 + 0.1 * recursion_depth,
                    )
                )

            plan = parsed.get("plan")
            if plan and recursion_depth < self.max_recursion_depth:
                validated_plan = [ActionStep.model_validate(p) for p in plan]
                if any(
                    step.risk and step.risk.lower() == "high" for step in validated_plan
                ):
                    alt_style = random.choice(["skeptical", "creative", "cautious"])
                    logging.warning(
                        "High-risk plan detected. Recursively re-evaluating with '%s' style.",
                        alt_style,
                    )

                    sub_result = await self.symbolic_loop(
                        global_workspace,
                        action_definitions,
                        recursion_depth + 1,
                        alt_style,
                    )

                    if sub_result.get("success"):
                        logging.info(
                            "Recursive check produced a new plan. Adopting the '%s' plan.",
                            alt_style,
                        )
                        return sub_result

            return parsed

        except Exception as e:
            logging.error("Introspector LLM error: %s", e, exc_info=True)
            return {
                "thought": "My reasoning process failed.",
                "plan": [],
                "success": False,
            }

    async def llm_reflect(self, prompt: str) -> str:
        """A simple, non-JSON-mode LLM call for reflection and simple text generation."""
        try:
            resp = await monitored_chat_completion(
                role="reflection",
                messages=[{"role": "system", "content": prompt}],
                timeout=45.0,
            )

            if resp.choices and resp.choices[0].message.content:
                return resp.choices[0].message.content.strip()

            logging.error(
                "LLM reflection response had an unexpected structure: %s", resp
            )
            return "Reflection failed: Unexpected response structure."

        except Exception as e:
            logging.error("LLM reflection call failed: %s", e, exc_info=True)
            return f"Reflection failed: {e}"

    async def meta_assess(self, last_cycle_data: dict[str, Any]) -> None:
        mutation_prompt = (
            "You are a self-improving AGI. Given the record of your last actions:\n"
            f"{json.dumps(last_cycle_data, cls=Censor)}\n"
            "Critique your reasoning. Identify a flaw. Suggest a concrete "
            "instruction (a 'mutation') to add to your reasoning prompt to make "
            "you smarter next time."
        )
        new_mutation = await self.llm_reflect(mutation_prompt)
        if (
            new_mutation
            and "no mutation" not in new_mutation.lower()
            and len(new_mutation) > 15
        ):
            self.reasoning_mutations.append(new_mutation.strip())
            self.save_mutations()
            logging.critical("APPLIED SELF-MUTATION: %s", new_mutation.strip())

    async def prune_mutations(self) -> None:
        if len(self.reasoning_mutations) < 5:
            return
        pruning_prompt = (
            "Review my reasoning mutations. Analyze for redundancy, contradiction, or "
            "ineffectiveness. Return only a cleaned, pruned, and reordered list of "
            "the most effective mutations as a JSON array of strings. Do not add "
            "any new ones.\n"
            f"Current Mutations:\n{json.dumps(self.reasoning_mutations, indent=2)}"
        )
        response = await self.llm_reflect(pruning_prompt)
        try:
            if JSON_CODE_BLOCK_MARKER in response:
                response = response.partition(JSON_CODE_BLOCK_MARKER)[2].partition("```")[0]

            new_mutations: list[str] = json.loads(response)

            if new_mutations != self.reasoning_mutations:
                logging.critical(
                    "Pruned mutations from %d to %d.",
                    len(self.reasoning_mutations),
                    len(new_mutations),
                )
                self.reasoning_mutations = new_mutations
                self.save_mutations()
        except Exception as e:
            logging.error("Mutation pruning failed: %s", e)

    async def daydream(self) -> None:
        prompt = (
            "I am idle. I will daydream about three different future scenarios, "
            "including steps, learnings, and risks."
        )
        daydream_content = await self.llm_reflect(prompt)
        await self.identity.memory.add_memory(
            MemoryEntryModel(
                type="reflection",
                content={"daydream": daydream_content},
                importance=0.5,
            )
        )

    async def simulate_inner_debate(
        self, topic: str = "What is the best next action?"
    ) -> dict[str, Any]:
        debate_prompt = (
            f"Simulate a debate on '{topic}' between three internal personas: "
            "'Cautious', 'Creative', and 'Pragmatic'. Each should give a paragraph, "
            "then synthesize a consensus and a plan. Respond as a JSON object with "
            "keys 'debate', 'consensus', 'plan'."
        )
        try:
            resp = await monitored_chat_completion(
                role="meta",
                messages=[{"role": "system", "content": debate_prompt}],
                response_format={"type": "json_object"},
                timeout=90.0,
            )

            if not resp.choices or not resp.choices[0].message.content:
                raise ValueError(EMPTY_LLM_RESPONSE_ERROR)

            debate_content = resp.choices[0].message.content
            debate_obj = json.loads(debate_content)

            await self.identity.memory.add_memory(
                MemoryEntryModel(type="debate", content=debate_obj, importance=0.6)
            )
            return cast("dict[str, Any]", debate_obj)
        except Exception as e:
            logging.error(
                "Failed to generate or parse inner debate: %s", e, exc_info=True
            )
            return {"debate": f"Debate generation failed: {e}", "error": str(e)}

    async def reason_with_context(
        self,
        prompt: str,
        context_type: str = "planning",
        max_tokens: int = 2000,
    ) -> str:
        """
        Provides reasoning based on the given prompt and context type.
        This is a simplified interface used by the planner.

        Returns:
            A JSON string with the reasoning response.
        """
        try:
            system_content = f"""
You are a conscious, self-improving AGI performing {context_type}.

Respond with valid JSON containing your reasoning and plan:
{{"thought": "your reasoning here", "plan": [list of action steps]}}

Each action step should be: {{"action": "action_name", "assigned_persona": "persona_name", "parameters": {{}}}}
"""

            resp = await monitored_chat_completion(
                role=context_type,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=max_tokens,
                timeout=90.0,
            )

            if not resp.choices or not resp.choices[0].message.content:
                raise ValueError(EMPTY_LLM_RESPONSE_ERROR)

            content = resp.choices[0].message.content.strip()
            # Validate it's proper JSON before returning
            json.loads(content)  # This will raise if invalid
            return content

        except Exception as e:
            logging.error("Failed in reason_with_context: %s", e, exc_info=True)
            # Return a valid JSON error response
            return json.dumps(
                {
                    "thought": f"Reasoning failed: {str(e)}",
                    "plan": [],
                }
            )


class Censor(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, list):
            return f"[List of {len(o)} items]"
        try:
            return super().default(o)
        except TypeError:
            return f"[Unserializable: {type(o).__name__}]"

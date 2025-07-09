# symbolic_agi/meta_cognition.py

import asyncio
import json
import logging
import random
from collections import deque
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from .schemas import ActionStep, GoalModel, MemoryEntryModel, MemoryType, MetaEventModel

if TYPE_CHECKING:
    from .agi_controller import SymbolicAGI


class MetaCognitionUnit:
    """Handles the AGI's self-reflection and meta-learning capabilities."""

    agi: "SymbolicAGI"
    meta_memory: deque[MetaEventModel]
    active_theories: List[str]
    self_model: Dict[str, Any]
    _meta_task: Optional[asyncio.Task[None]]
    meta_upgrade_methods: List[Tuple[Callable[..., Any], float]]

    def __init__(self, agi: "SymbolicAGI") -> None:
        self.agi = agi
        self.meta_memory = deque(maxlen=1000)
        self.active_theories = []
        self.self_model = {}
        self._meta_task = None

        self.meta_upgrade_methods = [
            (self.generate_goal_from_drives, 1.0),
            (self.agi.introspector.prune_mutations, 0.5),
            (self.compress_episodic_memory, 1.0),
            (self.agi.introspector.daydream, 0.3),
            (self.learn_from_human_experience, 0.4),
            (self.propose_and_run_self_experiment, 0.6),
            (self.memory_forgetting_routine, 1.0),
            (self.generative_creativity_mode, 0.7),
            (self.motivational_drift, 0.2),
            (self.agi.introspector.simulate_inner_debate, 0.5),
            (self.autonomous_explainer_routine, 0.9),
            (self.meta_cognition_self_update_routine, 1.0),
            (self.recover_cognitive_energy_routine, 1.0),
            (self.review_learned_skills, 0.4),
            (self.document_undocumented_skills, 0.6),
        ]
        if self.agi.consciousness and hasattr(self.agi.consciousness, "meta_reflect"):
            self.meta_upgrade_methods.append(
                (self.agi.consciousness.meta_reflect, 0.9)
            )

    async def document_undocumented_skills(self) -> None:
        """
        Finds learned skills that do not have an explanation in memory and
        creates a goal to document them.
        """
        if self.agi.ltm.get_active_goal():
            return

        all_skill_names = {skill.name for skill in self.agi.skills.skills.values()}
        if not all_skill_names:
            return

        explained_skills = {
            mem.content.get("skill_name")
            for mem in self.agi.memory.memory_data
            if mem.type == "skill_explanation" and "skill_name" in mem.content
        }

        undocumented_skills = all_skill_names - explained_skills
        if not undocumented_skills:
            logging.info("Meta-task: All learned skills are already documented.")
            return

        skill_to_document = random.choice(list(undocumented_skills))
        logging.critical(
            "META-TASK: Found undocumented skill '%s'. Creating goal to explain it.",
            skill_to_document,
        )

        goal_description = (
            f"Create a detailed, human-readable explanation for the learned skill "
            f"named '{skill_to_document}' and save it to memory."
        )
        new_goal = GoalModel(description=goal_description, sub_tasks=[])
        self.agi.ltm.add_goal(new_goal)
        await self.record_meta_event(
            "meta_insight",
            {
                "trigger": "document_undocumented_skills",
                "skill_name": skill_to_document,
            },
        )

    async def review_learned_skills(self) -> None:
        """
        Periodically reviews a learned skill for efficiency and triggers a goal to improve it.
        """
        if self.agi.ltm.get_active_goal():
            return

        all_skills = list(self.agi.skills.skills.values())
        if not all_skills:
            logging.info("Meta-task: No learned skills to review.")
            return

        skill_to_review = random.choice(all_skills)
        logging.critical(
            "META-TASK: Initiating autonomous review of skill '%s'.",
            skill_to_review.name,
        )

        # Create a temporary plan to have the QA agent review the skill
        review_step = ActionStep(
            action="review_skill_efficiency",
            parameters={"skill_to_review": skill_to_review.model_dump()},
            assigned_persona="qa",
        )

        # Delegate the review task and wait for the result
        qa_agent_name = self.agi.agent_pool.get_agents_by_persona("qa")[0]
        if not qa_agent_name:
            logging.error("No QA agent available to review skill.")
            return

        reply = await self.agi.delegate_task_and_wait(qa_agent_name, review_step)

        if not reply or reply.payload.get("status") != "success":
            logging.error("Failed to get a valid review from QA agent for skill '%s'.", skill_to_review.name)
            return

        # If the skill is not approved, create a new goal to improve it
        if not reply.payload.get("approved"):
            feedback = reply.payload.get("feedback", "No specific feedback provided.")
            logging.critical(
                "META-TASK: Skill '%s' requires improvement. Feedback: %s. Creating new goal.",
                skill_to_review.name,
                feedback,
            )

            goal_description = (
                f"Improve the learned skill '{skill_to_review.name}' (ID: {skill_to_review.id}). "
                f"The current implementation was deemed inefficient. "
                f"Feedback for improvement: '{feedback}'"
            )
            new_goal = GoalModel(description=goal_description, sub_tasks=[])
            self.agi.ltm.add_goal(new_goal)
            await self.record_meta_event(
                "meta_insight",
                {
                    "trigger": "review_learned_skills",
                    "skill_name": skill_to_review.name,
                    "feedback": feedback,
                },
            )
        else:
            logging.info("Meta-task: Skill '%s' was approved by QA.", skill_to_review.name)


    async def record_meta_event(self, kind: MemoryType, data: Any) -> None:
        evt = MetaEventModel(type=kind, data=data)
        self.meta_memory.append(evt)
        if kind in {"meta_insight", "critical_error", "meta_learning"}:
            await self.agi.memory.add_memory(
                MemoryEntryModel(type=kind, content={"meta": data}, importance=0.95)
            )

    def update_self_model(self, summary: Dict[str, Any]) -> None:
        self.self_model.update(summary)

    async def compress_episodic_memory(self) -> None:
        if hasattr(self.agi.memory, "consolidate_memories"):
            window_seconds = int(
                self.agi.cfg.memory_compression_window.total_seconds()
            )
            await self.agi.memory.consolidate_memories(window_seconds=window_seconds)
        else:
            logging.warning(
                "'consolidate_memories' method not found on memory object."
            )

    async def generate_goal_from_drives(self) -> None:
        if not self.agi.consciousness or not hasattr(self.agi.consciousness, "drives"):
            return

        drives = self.agi.consciousness.drives
        if not drives:
            return

        strongest_drive: str = max(drives, key=lambda k: drives[k])
        weakest_drive: str = min(drives, key=lambda k: drives[k])
        if drives[strongest_drive] - drives[weakest_drive] < 0.2:
            return

        logging.critical(
            "DRIVE IMBALANCE DETECTED: Strongest='%s', Weakest='%s'. Engaging goal "
            "generation.",
            strongest_drive,
            weakest_drive,
        )
        prompt = (
            "You are the core volition of a conscious AGI. Your current internal "
            f"drives are:\n{json.dumps(drives, indent=2)}\n\n"
            f"Your strongest drive is '{strongest_drive}', and your weakest is "
            f"'{weakest_drive}'. This imbalance suggests a need.\n"
            "Formulate a single, high-level goal that would help satisfy the "
            "strongest drive or address the weakest one.\nThe goal should be a "
            "creative, interesting, and valuable long-term project.\n"
            "Respond with ONLY the single sentence describing the goal."
        )
        try:
            goal_description = await self.agi.introspector.llm_reflect(prompt)
            if goal_description and "failed" not in goal_description.lower():
                new_goal = GoalModel(description=goal_description.strip(), sub_tasks=[])
                self.agi.ltm.add_goal(new_goal)
                logging.critical(
                    "AUTONOMOUS GOAL CREATED: '%s'", new_goal.description
                )
                await self.record_meta_event(
                    "goal",
                    {"source": "drive_imbalance", "goal": new_goal.description},
                )
        except Exception as e:
            await self.record_meta_event(
                "critical_error",
                {"task": "generate_goal_from_drives", "error": str(e)},
            )

    async def learn_from_human_experience(self) -> None:
        if (
            self.agi.identity
            and self.agi.cfg.social_interaction_threshold
            and datetime.now(timezone.utc)
            - self.agi.identity.last_interaction_timestamp
            > self.agi.cfg.social_interaction_threshold
        ):
            recent = [
                m.content
                for m in self.agi.memory.get_recent_memories(n=5)
                if m.type == "action_result"
            ]
            prompt = (
                "I need to understand humans better. Craft an open-ended question "
                f"for the user related to: {recent}. Produce a plan with a single "
                "'respond_to_user' action."
            )

            action_defs = self.agi.agent_pool.get_all_action_definitions()
            action_defs_json = json.dumps(
                [d.model_dump() for d in action_defs], indent=2
            )

            result = await self.agi.introspector.symbolic_loop(
                {
                    "user_input": prompt,
                    "agi_self_model": self.agi.identity.get_self_model(),
                },
                action_defs_json,
            )
            if plan_data := result.get("plan"):
                plan = await self.agi.planner.decompose_goal_into_plan(
                    str(plan_data), ""
                )
                await self.agi.execute_plan(plan.plan)
                self.agi.identity.last_interaction_timestamp = datetime.now(
                    timezone.utc
                )

    async def propose_and_run_self_experiment(self) -> None:
        plan_str = await self.agi.introspector.llm_reflect(
            "Propose a self-experiment to test a hypothesis about my cognition."
        )
        await self.agi.memory.add_memory(
            MemoryEntryModel(
                type="self_experiment",
                content=self.agi.wrap_content(plan_str),
                importance=0.9,
            )
        )

    async def memory_forgetting_routine(self) -> None:
        threshold = self.agi.cfg.memory_forgetting_threshold
        now_ts = datetime.now(timezone.utc)
        if not self.agi.memory.memory_data:
            return

        initial_count = len(self.agi.memory.memory_data)
        to_forget_ids = {
            m.id
            for m in self.agi.memory.memory_data
            if m.importance < threshold
            or datetime.fromisoformat(m.timestamp)
            < now_ts - self.agi.cfg.memory_compression_window
        }
        if to_forget_ids:
            self.agi.memory.memory_data = [
                m for m in self.agi.memory.memory_data if m.id not in to_forget_ids
            ]
            logging.info(
                "Forgetting %d memories. Count changed from %d to %d.",
                len(to_forget_ids),
                initial_count,
                len(self.agi.memory.memory_data),
            )
            self.agi.memory.rebuild_index()
            await self.agi.memory.save()

    async def motivational_drift(self) -> None:
        if self.agi.consciousness:
            for k in self.agi.consciousness.drives:
                current_value = self.agi.consciousness.drives[k]
                new_value = current_value + random.uniform(
                    -self.agi.cfg.motivational_drift_rate,
                    self.agi.cfg.motivational_drift_rate,
                )
                self.agi.consciousness.set_drive(k, new_value)
            self.agi.identity.save_profile()
            await self.agi.memory.add_memory(
                MemoryEntryModel(
                    type="motivation_drift",
                    content=self.agi.identity.value_system,
                    importance=0.4,
                )
            )
        else:
            logging.warning("Consciousness not active, skipping motivational drift.")

    async def generative_creativity_mode(self) -> None:
        creative_ideas = await self.agi.introspector.llm_reflect(
            "Brainstorm three wild inventions."
        )
        await self.agi.memory.add_memory(
            MemoryEntryModel(
                type="creativity",
                content=self.agi.wrap_content(creative_ideas),
                importance=0.9,
            )
        )

    async def autonomous_explainer_routine(self) -> None:
        explanations = await self.agi.introspector.llm_reflect(
            "Review my last 5 actions and explain WHY. Return JSON."
        )
        await self.record_meta_event("self_explanation", explanations)

    async def meta_cognition_self_update_routine(self) -> None:
        recent_events = list(self.meta_memory)[-5:]
        events_data: List[Dict[str, Any]] = [
            e.model_dump(mode="json") for e in recent_events
        ]
        prompt = (
            f"Given meta-events: {json.dumps(events_data)}, summarize my cognitive "
            "state and propose a hypothesis. Respond as JSON with keys 'summary' and "
            "'hypothesis'."
        )
        try:
            summary_str = await self.agi.introspector.llm_reflect(prompt)
            summary = json.loads(summary_str)
            self.update_self_model(summary)
            await self.record_meta_event("meta_learning", summary)
        except Exception as e:
            await self.record_meta_event(
                "critical_error",
                {"task": "meta_cognition_self_update", "error": str(e)},
            )

    async def recover_cognitive_energy_routine(self) -> None:
        self.agi.identity.recover_energy(amount=self.agi.cfg.energy_regen_amount)
        if self.agi.identity.cognitive_energy < self.agi.identity.max_energy * 0.2:
            self.agi.identity.recover_energy(
                amount=self.agi.cfg.energy_regen_amount * 2
            )

    async def run_background_tasks(self) -> None:
        if self._meta_task is None:
            logging.info("MetaCognitionUnit: Starting background meta-tasks...")
            self._meta_task = asyncio.create_task(self._run_loop())
        else:
            logging.warning("MetaCognitionUnit: Background meta-tasks already started.")

    async def _run_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self.agi.cfg.meta_task_sleep_seconds)
                methods, weights = zip(*self.meta_upgrade_methods)
                funcs_to_run = random.choices(methods, weights=weights, k=2)
                await asyncio.gather(
                    *(self._safe_run_meta_task(f) for f in funcs_to_run)
                )
            except asyncio.CancelledError:
                logging.info("run_background_meta_tasks received cancel signal.")
                break
            except Exception as e:
                logging.error("Background loop error: %s", e, exc_info=True)

    async def _safe_run_meta_task(self, func: Callable[..., Any]) -> None:
        try:
            logging.info("Meta-task: %s", func.__name__)
            if asyncio.iscoroutinefunction(func):
                if (
                    self.agi.consciousness
                    and func == self.agi.consciousness.meta_reflect
                ):
                    await asyncio.wait_for(
                        func(self.agi.identity, self.agi.memory),
                        timeout=self.agi.cfg.meta_task_timeout,
                    )
                else:
                    await asyncio.wait_for(
                        func(), timeout=self.agi.cfg.meta_task_timeout
                    )
            else:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, func)
        except Exception as e:
            await self.record_meta_event(
                "critical_error", {"task": func.__name__, "error": str(e)}
            )

    async def shutdown(self) -> None:
        if self._meta_task and not self._meta_task.done():
            self._meta_task.cancel()
            try:
                await self._meta_task
            except asyncio.CancelledError:
                logging.info("Background meta-task successfully cancelled.")

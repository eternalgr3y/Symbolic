# symbolic_agi/meta_cognition.py

import asyncio
import json
import asyncio
import logging
import random
from collections import deque
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from . import config
from .schemas import GoalModel, MemoryEntryModel, MemoryType, MetaEventModel

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
    _last_trust_reheal: datetime

    def __init__(self, agi: "SymbolicAGI") -> None:
        self.agi = agi
        self.meta_memory = deque(maxlen=1000)
        self.active_theories = []
        self.self_model = {}
        self._meta_task = None
        self._last_trust_reheal = datetime.now(timezone.utc)

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

    async def trust_rehealing_cron(self) -> None:
        """
        Periodically and slowly restores trust for all agents towards the neutral
        baseline, rewarding idle agents and preventing trust scores from permanently
        staying at extremes.
        """
        now = datetime.now(timezone.utc)
        if now - self._last_trust_reheal < timedelta(hours=config.TRUST_REHEAL_INTERVAL_HOURS):
            return

        logging.info("META-TASK: Running nightly trust re-healing cron job.")
        all_agents = self.agi.agent_pool.get_all()
        for agent_info in all_agents:
            agent_name = agent_info["name"]
            state = agent_info.get("state", {})
            current_score = state.get("trust_score", config.INITIAL_TRUST_SCORE)

            # Move score towards the neutral baseline (INITIAL_TRUST_SCORE)
            healing_adjustment = (config.INITIAL_TRUST_SCORE - current_score) * config.TRUST_REHEAL_RATE
            new_score = current_score + healing_adjustment

            self.agi.agent_pool.update_trust_score(agent_name, new_score, last_used=False)
            logging.debug("Healed trust for agent '%s' from %.3f to %.3f", agent_name, current_score, new_score)
        self._last_trust_reheal = now

    async def document_undocumented_skills(self) -> None:
        """
        Finds learned skills that do not have an explanation in memory and
        creates a goal to document them.
        """
        if await self.agi.ltm.get_active_goal():
            return

        all_skill_names = {skill.name for skill in self.agi.skills.skills.values()}
        if not all_skill_names:
            return

        explained_skills = {
            mem.content.get("skill_name")
            for mem in self.agi.memory.memory_map.values()
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
        await self.agi.ltm.add_goal(new_goal)
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
        if await self.agi.ltm.get_active_goal():
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

        goal_description = (
            f"Review and improve the learned skill named '{skill_to_review.name}' "
            f"(ID: {skill_to_review.id}). Analyze its action sequence for "
            "inefficiencies and update it if a better plan can be formulated."
        )
        new_goal = GoalModel(description=goal_description, sub_tasks=[])

        await self.agi.ltm.add_goal(new_goal)
        await self.record_meta_event(
            "meta_insight",
            {"trigger": "review_learned_skills", "skill_name": skill_to_review.name},
        )

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
                await self.agi.ltm.add_goal(new_goal)
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
            recent_memories = await self.agi.memory.get_recent_memories(n=5)
            recent = [
                m.content
                for m in recent_memories
                if m.type == "action_result"
            ]
            prompt = (
                "I need to understand humans better. Craft an open-ended question "
                f"for the user related to: {recent}. Produce a plan with a single "
                "'respond_to_user' action."
            )

            result = await self.agi.introspector.symbolic_loop(
                {
                    "user_input": prompt,
                    "agi_self_model": self.agi.identity.get_self_model(),
                },
                json.dumps(self.agi.agent_pool.get_all_action_definitions(), indent=2),
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
        if not self.agi.memory.memory_map:
            return

        initial_count = len(self.agi.memory.memory_map)
        to_forget_ids = {
            db_id
            for db_id, m in self.agi.memory.memory_map.items()
            if m.importance < threshold
            or datetime.fromisoformat(m.timestamp)
            < now_ts - self.agi.cfg.memory_compression_window
        }
        if to_forget_ids:
            # This logic would now involve a DB call to delete these IDs
            logging.info(
                "Forgetting %d memories. Count changed from %d to %d.",
                len(to_forget_ids),
                initial_count,
                len(self.agi.memory.memory_map) - len(to_forget_ids),
            )
            # self.agi.memory.rebuild_index() # Should be called after deletion
            # await self.agi.memory.save() # Persist changes

    async def motivational_drift(self) -> None:
        if self.agi.consciousness:
            for k in self.agi.consciousness.drives:
                current_value = self.agi.consciousness.drives[k]
                new_value = current_value + random.uniform(
                    -self.agi.cfg.motivational_drift_rate,
                    self.agi.cfg.motivational_drift_rate,
                )
                self.agi.consciousness.set_drive(k, new_value)
            await self.agi.identity.save_profile()
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
            e.model_dump() for e in recent_events
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
                methods, weights = zip(*self.meta_upgrade_methods, strict=False)
                funcs_to_run = random.choices(methods, weights=weights, k=2)
                await asyncio.gather(
                    self.trust_rehealing_cron(),
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
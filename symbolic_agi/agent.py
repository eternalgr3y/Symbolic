# symbolic_agi/agent.py

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any, Callable, Dict

from openai import AsyncOpenAI

from . import prompts
from .api_client import monitored_chat_completion
from .schemas import MessageModel, SkillModel

if TYPE_CHECKING:
    from .message_bus import MessageBus


class Agent:
    def __init__(self, name: str, message_bus: "MessageBus", api_client: AsyncOpenAI):
        self.name = name
        self.persona = name.split("_")[-2].lower() if "_" in name else "specialist"
        self.bus = message_bus
        self.client = api_client
        self.inbox = self.bus.subscribe(self.name)
        self.running = True
        self.skills: Dict[str, Callable[..., Any]] = self._initialize_skills()
        logging.info(
            "Agent '%s' initialized with persona '%s' and skills: %s",
            self.name,
            self.persona,
            list(self.skills.keys()),
        )

    def _initialize_skills(self) -> Dict[str, Callable[..., Any]]:
        """Initializes persona-specific skills."""
        if self.persona == "coder":
            return {"write_code": self.skill_write_code}
        if self.persona == "research":
            return {"research_topic": self.skill_research_topic}
        if self.persona == "qa":
            return {
                "review_code": self.skill_review_code,
                "review_plan": self.skill_review_plan,
                "review_skill_efficiency": self.skill_review_skill_efficiency,
            }
        if self.persona == "browser":
            return {"interact_with_page": self.skill_interact_with_page}
        return {}

    async def run(self) -> None:
        """Main loop for the agent to process messages."""
        while self.running:
            try:
                message: MessageModel = await asyncio.wait_for(
                    self.inbox.get(), timeout=1.0
                )
                await self.handle_message(message)
                self.inbox.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                self.running = False
                logging.info("Agent '%s' received cancel signal.", self.name)
                break
        logging.info("Agent '%s' has shut down.", self.name)

    async def _reply(
        self, original_message: MessageModel, payload: Dict[str, Any]
    ) -> None:
        """Helper to send a reply message."""
        reply = MessageModel(
            sender_id=self.name,
            receiver_id=original_message.sender_id,
            message_type=f"{original_message.message_type}_result",
            payload=payload,
        )
        await self.bus.publish(reply)

    async def handle_message(self, message: MessageModel) -> None:
        """Handles incoming messages and routes them to appropriate skills or handlers."""
        logging.info(
            "Agent '%s' received message of type '%s' from '%s'.",
            self.name,
            message.message_type,
            message.sender_id,
        )
        skill_to_run = self.skills.get(message.message_type)
        if skill_to_run:
            result_payload = await skill_to_run(message.payload)
            await self._reply(message, result_payload)
        elif message.message_type == "new_skill_broadcast":
            skill_name = message.payload.get("skill_name")
            skill_description = message.payload.get("skill_description")
            logging.info(
                "Agent '%s' learned about a new skill: '%s' - %s",
                self.name,
                skill_name,
                skill_description,
            )
        else:
            logging.warning(
                "Agent '%s' does not know how to handle message type '%s'.",
                self.name,
                message.message_type,
            )
            await self._reply(
                message,
                {
                    "status": "failure",
                    "error": (
                        f"Agent '{self.name}' does not have skill "
                        f"'{message.message_type}'."
                    ),
                },
            )

    async def skill_interact_with_page(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes the content of a web page and decides the next interaction.
        """
        objective = params.get("objective", "Explore the page.")
        page_content = params.get("page_content", "Page is empty.")
        prompt = prompts.INTERACT_WITH_PAGE_PROMPT.format(
            objective=objective, page_content=page_content
        )
        try:
            resp = await monitored_chat_completion(
                role="agent_skill",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
            )
            if resp.choices and resp.choices[0].message.content:
                action_data = json.loads(resp.choices[0].message.content)
                return {"status": "success", "browser_action": action_data}
            return {
                "status": "failure",
                "error": "No browser action returned from LLM.",
            }
        except Exception as e:
            return {"status": "failure", "error": str(e)}

    async def skill_review_skill_efficiency(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Reviews a learned skill's action sequence for potential improvements.
        """
        try:
            skill_data = params.get("skill_to_review", {})
            skill = SkillModel.model_validate(skill_data)
            plan_str = json.dumps(
                [step.model_dump() for step in skill.action_sequence], indent=2
            )
            prompt = prompts.REVIEW_SKILL_EFFICIENCY_PROMPT.format(
                skill_name=skill.name,
                skill_description=skill.description,
                plan_str=plan_str,
            )
            resp = await monitored_chat_completion(
                role="qa",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
            )
            if resp.choices and resp.choices[0].message.content:
                review_data = json.loads(resp.choices[0].message.content)
                return {
                    "status": "success",
                    "approved": review_data.get("approved", False),
                    "feedback": review_data.get(
                        "feedback", "QA review returned an incomplete response."
                    ),
                }
            return {"status": "failure", "error": "No content returned from LLM."}
        except Exception as e:
            logging.error(
                "Error in skill_review_skill_efficiency: %s", e, exc_info=True
            )
            return {"status": "failure", "error": str(e)}

    async def skill_review_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reviews a plan for logical flaws, inefficiency, or misinterpretation of the
        original goal. Provides actionable feedback for refinement if the plan is rejected.
        """
        goal = params.get("original_goal", "No goal provided.")
        plan = params.get("plan_to_review", [])
        plan_str = json.dumps(plan, indent=2)
        prompt = prompts.REVIEW_PLAN_PROMPT.format(goal=goal, plan_str=plan_str)
        try:
            resp = await monitored_chat_completion(
                role="qa",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
            )
            if resp.choices and resp.choices[0].message.content:
                review_data = json.loads(resp.choices[0].message.content)
                return {
                    "status": "success",
                    "approved": review_data.get("approved", False),
                    "feedback": review_data.get(
                        "feedback", "QA review returned an incomplete response."
                    ),
                }
            return {"status": "failure", "error": "No content returned from LLM."}
        except Exception as e:
            return {"status": "failure", "error": str(e)}

    async def skill_write_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generates Python code, using and updating its own short-term state."""
        prompt = params.get("prompt", "Write a simple hello world python script.")
        context = params.get("context", "")
        workspace = params.get("workspace", {})
        agent_state = params.get("agent_state", {})
        llm_prompt = prompts.WRITE_CODE_PROMPT.format(
            context=context,
            research_summary=workspace.get("research_summary", "N/A"),
            previous_code=agent_state.get(
                "previous_code", "# This is your first step in this session."
            ),
            prompt=prompt,
        )
        try:
            resp = await monitored_chat_completion(
                role="agent_skill",
                messages=[{"role": "system", "content": llm_prompt}],
                response_format={"type": "json_object"},
            )
            if resp.choices and resp.choices[0].message.content:
                response_data = json.loads(resp.choices[0].message.content)
                return {
                    "status": "success",
                    "generated_code": response_data.get(
                        "generated_code", "# ERROR: No code generated"
                    ),
                    "state_updates": response_data.get("state_updates", {}),
                }
            return {"status": "failure", "error": "No content returned from LLM."}
        except Exception as e:
            return {"status": "failure", "error": str(e)}

    async def skill_research_topic(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Researches a given topic and provides a concise summary."""
        topic = params.get("topic", "The history of artificial intelligence.")
        llm_prompt = prompts.RESEARCH_TOPIC_PROMPT.format(topic=topic)
        try:
            resp = await monitored_chat_completion(
                role="agent_skill",
                messages=[{"role": "system", "content": llm_prompt}],
            )
            content = resp.choices[0].message.content
            if content is not None:
                summary = content.strip()
                return {"status": "success", "research_summary": summary}
            return {"status": "failure", "error": "No content returned from LLM."}
        except Exception as e:
            return {"status": "failure", "error": str(e)}

    async def skill_review_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Reviews provided Python code for quality and improvements."""
        workspace = params.get("workspace", {})
        code_to_review = workspace.get(
            "generated_code", "# No code provided to review."
        )
        llm_prompt = prompts.REVIEW_CODE_PROMPT.format(code_to_review=code_to_review)
        try:
            resp = await monitored_chat_completion(
                role="qa", messages=[{"role": "system", "content": llm_prompt}]
            )
            content = resp.choices[0].message.content
            if content is not None:
                review = content.strip()
                return {"status": "success", "code_review": review}
            return {"status": "failure", "error": "No content returned from LLM."}
        except Exception as e:
            return {"status": "failure", "error": str(e)}

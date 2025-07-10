# symbolic_agi/agent.py

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any, Dict

from openai import AsyncOpenAI
from pydantic import ValidationError
from .skill_manager import register_innate_action

from . import prompts
from .api_client import monitored_chat_completion
from .schemas import MessageModel, SkillModel
from .message_bus import RedisMessageBus

# Constants for error messages
NO_CONTENT_FROM_LLM_ERROR = "No content returned from LLM."

if TYPE_CHECKING:
    from .message_bus import RedisMessageBus


class Agent:
    def __init__(self, name: str, message_bus: "RedisMessageBus", api_client: AsyncOpenAI):
        self.name = name
        self.persona = name.split("_")[-2].lower() if "_" in name else "specialist"
        self.bus = message_bus
        self.client = api_client
        self.inbox: "asyncio.Queue[MessageModel | None]" = self.bus.subscribe(self.name)
        self.running = True
        logging.info(
            "Agent '%s' initialized with persona '%s'",
            self.name,
            self.persona,
        )

    async def run(self) -> None:
        """Main loop for the agent to process messages."""
        while self.running:
            try:
                message = await asyncio.wait_for(
                    self.inbox.get(), timeout=1.0
                )
                if message is not None:
                    await self.handle_message(message)
                self.inbox.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                self.running = False
                logging.info("Agent '%s' received cancel signal.", self.name)
                raise  # Re-raise CancelledError for proper async cleanup
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

        skill_method = None
        if hasattr(self, message.message_type):
            method = getattr(self, message.message_type)
            if hasattr(method, "_innate_action_persona"):
                if getattr(method, "_innate_action_persona") == self.persona:
                    skill_method = method

        if skill_method:
            result_payload = await skill_method(message.payload)
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

    @register_innate_action(
        "browser", "Analyzes a web page and decides the next interaction."
    )
# File: symbolic_agi/agent.py
# Fix for skill_review_skill_efficiency method (around line 127)

    async def skill_review_skill_efficiency(self, skill_name: str) -> str:
        """Reviews a skill's efficiency and provides optimization suggestions."""
        try:
            # Get skill details from skill manager
            skill_details = await self.skill_manager.get_skill_details(skill_name)
            
            # FIX 1: Validate skill_details before processing
            if not skill_details:
                self.logger.warning(f"No skill details found for '{skill_name}'")
                return f"Skill '{skill_name}' not found in skill manager."
            
            # FIX 2: Handle placeholder strings
            if isinstance(skill_details, str) and skill_details == "<<retrieved_skill_details>>":
                self.logger.error(f"Received placeholder instead of skill details for '{skill_name}'")
                # Attempt to retrieve actual skill data
                skill_model = await self.skill_manager.get_skill(skill_name)
                if skill_model:
                    skill_details = skill_model.model_dump()
                else:
                    return f"Unable to retrieve details for skill '{skill_name}'."
            
            # FIX 3: Ensure skill_details is a dictionary
            if not isinstance(skill_details, dict):
                self.logger.error(f"Invalid skill details type: {type(skill_details)}")
                return f"Invalid skill data format for '{skill_name}'."
            
            # FIX 4: Safe model validation with error handling
            try:
                skill_model = SkillModel.model_validate(skill_details)
            except ValidationError as e:
                self.logger.error(f"Skill validation failed for '{skill_name}': {e}")
                return f"Skill '{skill_name}' has invalid data structure: {e}"
            
            # Continue with the review process...
            review_prompt = f"""
            Review this skill for efficiency and optimization opportunities:
            Name: {skill_model.name}
            Description: {skill_model.description}
            Implementation: {skill_model.implementation}
            
            Provide specific suggestions for improvement.
            """
            
            response = await self._query_llm(review_prompt)
            return response.strip()
            
        except Exception as e:
            self.logger.error(f"Error reviewing skill '{skill_name}': {e}")
            return f"Error reviewing skill: {str(e)}"

    @register_innate_action(
        "qa", "Reviews a plan for logical flaws or inefficiency."
    )
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
            return {"status": "failure", "error": NO_CONTENT_FROM_LLM_ERROR}
        except Exception as e:
            return {"status": "failure", "error": str(e)}

    @register_innate_action(
        "coder", "Generates Python code based on a prompt and context."
    )
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
            return {"status": "failure", "error": NO_CONTENT_FROM_LLM_ERROR}
        except Exception as e:
            return {"status": "failure", "error": str(e)}

    @register_innate_action(
        "research", "Researches a given topic and provides a concise summary."
    )
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
            return {"status": "failure", "error": NO_CONTENT_FROM_LLM_ERROR}
        except Exception as e:
            return {"status": "failure", "error": str(e)}

    @register_innate_action(
        "qa", "Reviews provided Python code for quality and improvements."
    )
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
            return {"status": "failure", "error": NO_CONTENT_FROM_LLM_ERROR}
        except Exception as e:
            return {"status": "failure", "error": str(e)}
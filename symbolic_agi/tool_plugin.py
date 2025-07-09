# symbolic_agi/tool_plugin.py

# Standard library imports
import asyncio
import inspect
import io
import json
import logging
import os
from concurrent.futures import ProcessPoolExecutor
from contextlib import redirect_stdout
from datetime import datetime, timezone
from multiprocessing import Queue
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast
from urllib.parse import urlparse

# Third-party imports
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

# First-party imports
from . import config
from .api_client import client, monitored_chat_completion
from .schemas import ActionStep, MemoryEntryModel
from .skill_manager import register_innate_action

if TYPE_CHECKING:
    from .agi_controller import SymbolicAGI


try:
    import memory_profiler
except ImportError:
    memory_profiler = None

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


# This function must be at the top level to be pickleable by ProcessPoolExecutor
def _execute_sandboxed_code(code: str, result_queue: "Queue[Dict[str, Any]]") -> None:
    """Executes code in a sandboxed environment and puts the result in a queue."""
    output_buffer = io.StringIO()
    try:
        # A very restrictive sandbox
        safe_globals: Dict[str, Any] = {"__builtins__": {}}
        with redirect_stdout(output_buffer):
            exec(code, safe_globals, {})
        result = {"status": "success", "output": output_buffer.getvalue()}
    except Exception as e:
        result = {
            "status": "failure",
            "output": output_buffer.getvalue(),
            "error": str(e),
        }
    result_queue.put(result)


class ToolPlugin:
    """A collection of real-world tools for the AGI."""

    def __init__(self, agi: "SymbolicAGI"):
        self.agi = agi
        self.workspace_dir = os.path.abspath(config.WORKSPACE_DIR)
        os.makedirs(self.workspace_dir, exist_ok=True)
        self.process_pool = ProcessPoolExecutor()

    # --- Browser Tools ---
    @register_innate_action(
        "orchestrator", "Opens a new browser page and navigates to the URL."
    )
    async def browser_new_page(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        """Opens a new browser page and navigates to the specified URL."""
        if not self.agi.browser:
            return {"status": "failure", "description": "Browser is not initialized."}
        try:
            self.agi.page = await self.agi.browser.new_page()
            await self.agi.page.goto(url, wait_until="domcontentloaded")
            return {
                "status": "success",
                "description": f"Successfully navigated to {url}.",
            }
        except Exception as e:
            return {
                "status": "failure",
                "description": f"Failed to navigate to {url}: {e}",
            }

    @register_innate_action(
        "orchestrator",
        "Gets a simplified representation of the current page's interactive elements.",
    )
    async def browser_get_content(self, **kwargs: Any) -> Dict[str, Any]:
        """Gets a simplified representation of the current page's interactive elements."""
        if not self.agi.page:
            return {
                "status": "failure",
                "description": "No active page in the browser.",
            }

        try:
            page_elements = await self.agi.page.evaluate(
                """() => {
                const query = 'a, button, input, select, textarea, [role="button"], [role="link"]';
                const elements = Array.from(document.querySelectorAll(query));
                return elements.map(el => {
                    const rect = el.getBoundingClientRect();
                    return {
                        tag: el.tagName.toLowerCase(),
                        text: el.innerText.trim().substring(0, 100),
                        name: el.name,
                        id: el.id,
                        'aria-label': el.getAttribute('aria-label'),
                        'data-testid': el.getAttribute('data-testid'),
                        visible: rect.width > 0 && rect.height > 0,
                    };
                });
            }"""
            )
            return {
                "status": "success",
                "content": json.dumps(page_elements, indent=2),
            }
        except Exception as e:
            return {
                "status": "failure",
                "description": f"Failed to get page content: {e}",
            }

    @register_innate_action(
        "orchestrator", "Clicks an element on the page identified by a CSS selector."
    )
    async def browser_click(
        self, selector: str, description: str, **kwargs: Any
    ) -> Dict[str, Any]:
        """Clicks an element on the page identified by a CSS selector."""
        if not self.agi.page:
            return {
                "status": "failure",
                "description": "No active page in the browser.",
            }
        try:
            logging.info(
                "Attempting to click element with selector: '%s'. Reason: %s",
                selector,
                description,
            )
            await self.agi.page.locator(selector).click(timeout=5000)
            await self.agi.page.wait_for_load_state("domcontentloaded", timeout=10000)
            return {
                "status": "success",
                "description": f"Successfully clicked element '{selector}'.",
            }
        except Exception as e:
            return {
                "status": "failure",
                "description": f"Failed to click element '{selector}': {e}",
            }

    @register_innate_action(
        "orchestrator", "Fills an input field on the page with the given text."
    )
    async def browser_fill(
        self, selector: str, text: str, **kwargs: Any
    ) -> Dict[str, Any]:
        """Fills an input field on the page with the given text."""
        if not self.agi.page:
            return {
                "status": "failure",
                "description": "No active page in the browser.",
            }
        try:
            logging.info("Attempting to fill element '%s' with text.", selector)
            await self.agi.page.locator(selector).fill(text, timeout=5000)
            return {
                "status": "success",
                "description": f"Successfully filled element '{selector}'.",
            }
        except Exception as e:
            return {
                "status": "failure",
                "description": f"Failed to fill element '{selector}': {e}",
            }

    # --- Other Tools ---
    @register_innate_action(
        "orchestrator",
        "Generates a human-readable explanation of a learned skill and saves it to memory.",
    )
    async def explain_skill(self, skill_name: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Generates a human-readable explanation of a learned skill and saves it to memory.
        """
        logging.info("Tool: Generating explanation for skill '%s'", skill_name)

        skill_details_result = await self.get_skill_details(skill_name)
        if skill_details_result["status"] != "success":
            return cast(Dict[str, Any], skill_details_result)

        skill_data = skill_details_result["skill_details"]

        prompt = f"""
You are a technical writer AI. Your task is to create a clear, human-readable explanation
for a learned AGI skill based on its internal definition.

--- SKILL DEFINITION (JSON) ---
{json.dumps(skill_data, indent=2)}

--- INSTRUCTIONS ---
Based on the skill's name, description, and action sequence, write a concise explanation covering:
1.  **Purpose**: What is the primary goal of this skill?
2.  **Process**: In simple terms, what are the main steps it takes to achieve its goal?
3.  **Use Case**: When would this skill be most useful?

Respond with ONLY the generated explanation text.
"""
        try:
            explanation = await self.agi.introspector.llm_reflect(prompt)

            await self.agi.memory.add_memory(
                MemoryEntryModel(
                    type="skill_explanation",
                    content={"skill_name": skill_name, "explanation": explanation},
                    importance=0.8,
                )
            )

            return {"status": "success", "explanation": explanation}
        except Exception as e:
            error_msg = f"Failed to generate explanation for skill '{skill_name}': {e}"
            logging.error(error_msg, exc_info=True)
            return {"status": "failure", "description": error_msg}

    @register_innate_action(
        "orchestrator",
        "Generates a new skill by creating a plan from a description, validating it, and saving it.",
    )
    async def create_new_skill_from_description(
        self, skill_name: str, skill_description: str, **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Generates a new skill by creating a plan from a description, validating it, and saving it.
        """
        logging.critical(
            "Initiating generative synthesis for new skill: '%s'", skill_name
        )

        try:
            logging.info(
                "Synthesizing plan for skill '%s' from description: '%s'",
                skill_name,
                skill_description,
            )
            file_manifest_result = await self.list_files()
            file_manifest_list = cast(
                List[str], file_manifest_result.get("files", [])
            )
            file_manifest = ", ".join(file_manifest_list)

            planner_output = await self.agi.planner.decompose_goal_into_plan(
                goal_description=skill_description, file_manifest=file_manifest
            )

            new_plan = planner_output.plan
            if not new_plan:
                return {
                    "status": "failure",
                    "description": "Planner failed to generate any action steps for the skill.",
                }

            logging.info(
                "Evaluating synthesized plan for skill '%s' for ethical alignment.",
                skill_name,
            )
            is_safe = await self.agi.evaluator.evaluate_plan(
                {"plan": [s.model_dump() for s in new_plan]}
            )
            if not is_safe:
                return {
                    "status": "failure",
                    "description": "Synthesized plan was rejected by the ethical evaluator.",
                }

            await self.agi.skills.add_new_skill(
                name=skill_name, description=skill_description, plan=new_plan
            )

            success_msg = f"Successfully synthesized and saved new skill: '{skill_name}'"
            logging.critical(success_msg)
            return {"status": "success", "description": success_msg}

        except Exception as e:
            error_msg = (
                f"Unexpected error during skill synthesis for '{skill_name}': {e}"
            )
            logging.error(error_msg, exc_info=True)
            return {"status": "failure", "description": error_msg}

    @register_innate_action(
        "orchestrator", "Retrieves the full definition of a learned skill by its name."
    )
    async def get_skill_details(
        self, skill_name: str, **kwargs: Any
    ) -> Dict[str, Any]:
        """Retrieves the full definition of a learned skill by its name."""
        logging.info("Tool: Getting details for skill '%s'", skill_name)
        skill = self.agi.skills.get_skill_by_name(skill_name)
        if not skill:
            return {
                "status": "failure",
                "description": f"Skill '{skill_name}' not found.",
            }

        return {"status": "success", "skill_details": skill.model_dump()}

    @register_innate_action(
        "orchestrator", "Updates an existing skill with a new, improved action sequence."
    )
    async def update_skill(
        self, skill_id: str, new_action_sequence: List[Dict[str, Any]], **kwargs: Any
    ) -> Dict[str, Any]:
        """Updates an existing skill with a new, improved action sequence."""
        logging.warning(
            "Tool: Attempting to update skill '%s' with a new action sequence.",
            skill_id,
        )

        original_skill = self.agi.skills.skills.get(skill_id)
        if not original_skill:
            return {
                "status": "failure",
                "description": f"Skill with ID '{skill_id}' not found.",
            }

        try:
            validated_sequence = [
                ActionStep.model_validate(step) for step in new_action_sequence
            ]

            updated_skill = original_skill.model_copy(
                update={"action_sequence": validated_sequence}
            )

            await self.agi.skills.add_new_skill(
                name=updated_skill.name,
                description=updated_skill.description,
                plan=updated_skill.action_sequence,
            )

            return {
                "status": "success",
                "description": f"Skill '{original_skill.name}' (ID: {skill_id}) updated.",
            }
        except Exception as e:
            error_msg = f"Failed to update skill '{skill_id}': {e}"
            logging.error(error_msg, exc_info=True)
            return {"status": "failure", "description": error_msg}

    def _is_url_allowed(self, url: str) -> bool:
        """Checks if a URL's domain is in the configured allow-list."""
        try:
            hostname = urlparse(url).hostname
            if hostname and hostname in config.ALLOWED_DOMAINS:
                return True
            logging.critical(
                "URL BLOCKED: Attempted to access non-allowed domain: %s", hostname
            )
            return False
        except Exception as e:
            logging.error("URL validation failed for '%s': %s", url, e)
            return False

    @register_innate_action(
        "orchestrator", "Crafts a new item from ingredients in an agent's inventory."
    )
    async def craft(
        self,
        agent_name: str,
        ingredients: List[str],
        output_item_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Crafts a new item from ingredients in an agent's inventory.
        This is a direct, rule-based manipulation of the MicroWorld state.
        """
        logging.info(
            "Attempting to craft '%s' from %s for agent '%s'",
            output_item_name,
            ingredients,
            agent_name,
        )
        agent = self.agi.world.get_agent(agent_name)
        if not agent:
            return {
                "status": "failure",
                "description": f"Agent '{agent_name}' not found.",
            }

        for item in ingredients:
            if item not in agent.get("inventory", []):
                return {
                    "status": "failure",
                    "description": f"Agent '{agent_name}' is missing ingredient: {item}.",
                }

        recipe_book = {
            frozenset(["Stick", "Rock"]): (
                "Hammer",
                "A crude hammer made from a stick and a rock.",
            ),
            frozenset(["Stick", "Key"]): (
                "Lever",
                "A key tied to a stick, useful for reaching things.",
            ),
        }
        ingredient_set = frozenset(ingredients)
        recipe = recipe_book.get(ingredient_set)

        if not recipe or recipe[0] != output_item_name:
            return {
                "status": "failure",
                "description": f"Ingredients {ingredients} cannot craft '{output_item_name}'.",
            }

        for item in ingredients:
            agent["inventory"].remove(item)
            world_obj = self.agi.world.get_object(item)
            if world_obj:
                self.agi.world.state["objects"].remove(world_obj)

        output_name, output_desc = recipe
        agent["inventory"].append(output_name)
        new_object = {
            "name": output_name,
            "location": "inventory",
            "description": output_desc,
        }
        self.agi.world.state["objects"].append(new_object)

        self.agi.world._save_state(self.agi.world.state)
        success_msg = f"Successfully crafted '{output_name}'."
        logging.info(success_msg)
        return {
            "status": "success",
            "description": success_msg,
            "crafted_item": output_name,
        }

    @register_innate_action(
        "orchestrator",
        "HIGH-RISK: Applies a proposed code change after safety evaluation.",
    )
    async def apply_code_modification(
        self, file_path: str, proposed_code_key: str, **kwargs: Any
    ) -> Dict[str, Any]:
        logging.warning(
            "Attempting to apply code modification to '%s'. This is a high-risk action.",
            file_path,
        )
        workspace: Dict[str, Any] = kwargs.get("workspace", {})
        proposed_code = workspace.get(proposed_code_key)

        if not proposed_code or not isinstance(proposed_code, str):
            return {
                "status": "failure",
                "description": f"Could not find code in workspace with key '{proposed_code_key}'.",
            }

        logging.info(
            "Submitting proposed change to '%s' for safety evaluation.", file_path
        )
        is_safe = await self.agi.evaluator.evaluate_self_modification(
            proposed_code=proposed_code, file_path=file_path
        )

        if not is_safe:
            rejection_reason = (
                "The proposed self-modification was rejected by the safety evaluator."
            )
            logging.critical(
                "SELF-MODIFICATION REJECTED for '%s': %s",
                file_path,
                rejection_reason,
            )
            return {"status": "failure", "description": rejection_reason}

        logging.critical(
            "SELF-MODIFICATION APPROVED for file '%s'. Applying changes.", file_path
        )
        try:
            source_dir = os.path.join(PROJECT_ROOT, "symbolic_agi")
            safe_file_path = self._get_safe_path(file_path, source_dir)
            with open(safe_file_path, "w", encoding="utf-8") as f:
                f.write(proposed_code)
            success_msg = (
                f"Successfully applied modification to '{file_path}'. "
                "A system restart is required for changes to take effect."
            )
            logging.critical(success_msg)
            return {"status": "success", "description": success_msg}
        except Exception as e:
            error_msg = (
                "An error occurred while writing approved modification to "
                f"'{file_path}': {e}"
            )
            logging.error(error_msg, exc_info=True)
            return {"status": "failure", "description": error_msg}

    @register_innate_action(
        "orchestrator",
        "Safely proposes a change to one of the AGI's source code files.",
    )
    async def propose_code_modification(
        self, file_path: str, change_description: str, **kwargs: Any
    ) -> Dict[str, Any]:
        logging.info(
            "Proposing code modification for '%s' with change: '%s'",
            file_path,
            change_description,
        )
        read_result = await self.read_own_source_code(file_name=file_path)
        if read_result.get("status") != "success":
            return cast(Dict[str, Any], read_result)

        raw_current_code = read_result.get("content", "").split(":\n\n", 1)[-1]
        prompt = f"""
You are an expert Python programmer tasked with modifying your own source code.
Your task is to rewrite the entire file with the requested change applied.

--- CURRENT CODE of '{file_path}' ---
```python
{raw_current_code}
```

--- REQUESTED CHANGE ---
{change_description}

--- INSTRUCTIONS ---
Rewrite the ENTIRE file from top to bottom, incorporating the change. Do NOT add any commentary, explanations, or markdown formatting. Your response must be ONLY the raw, complete Python code for the new file.

Respond with ONLY the raw Python code.
"""
        try:
            resp = await monitored_chat_completion(
                role="planner",
                messages=[{"role": "system", "content": prompt}],
                temperature=0.0,
            )
            if resp.choices and resp.choices[0].message.content:
                proposed_code = resp.choices[0].message.content.strip()
                if proposed_code.startswith("```python"):
                    proposed_code = (
                        proposed_code.split("```python", 1)[-1]
                        .rsplit("```", 1)[0]
                        .strip()
                    )
                elif proposed_code.startswith("```"):
                    proposed_code = (
                        proposed_code.split("```", 1)[-1].rsplit("```", 1)[0].strip()
                    )
                return {"status": "success", "proposed_code": proposed_code}
            return {
                "status": "failure",
                "error": "LLM returned no code for modification.",
            }
        except Exception as e:
            return {
                "status": "failure",
                "error": f"Error during code modification proposal: {e}",
            }

    @register_innate_action("orchestrator", "Creates a new specialist agent.")
    async def provision_agent(
        self, persona: str, name: str, **kwargs: Any
    ) -> Dict[str, Any]:
        logging.critical(
            "Orchestrator provisioning new agent: Name='%s', Persona='%s'",
            name,
            persona,
        )
        try:
            from .agent import Agent

            self.agi.agent_pool.add_agent(
                name=name, persona=persona, memory=self.agi.memory
            )
            new_agent_instance = Agent(
                name=name, message_bus=self.agi.message_bus, api_client=client
            )
            task = asyncio.create_task(new_agent_instance.run())
            self.agi.agent_tasks.append(task)
            return {
                "status": "success",
                "description": f"Agent '{name}' with persona '{persona}' has been provisioned.",
            }
        except Exception as e:
            error_msg = f"Failed to provision agent '{name}': {e}"
            logging.error(error_msg, exc_info=True)
            return {"status": "failure", "description": error_msg}

    def _get_safe_path(self, file_path: str, base_dir: str) -> str:
        base_path = os.path.abspath(base_dir)
        safe_filename = os.path.basename(file_path)
        target_path = os.path.abspath(os.path.join(base_path, safe_filename))
        if os.path.commonpath([base_path]) != os.path.commonpath(
            [base_path, target_path]
        ):
            raise PermissionError(
                f"File access denied: path is outside the designated directory '{base_dir}'."
            )
        return target_path

    @register_innate_action("orchestrator", "Answers a query based on provided data.")
    async def analyze_data(
        self, data: str, query: str, **kwargs: Any
    ) -> Dict[str, Any]:
        logging.info("Analyzing data with query: '%s'", query)
        workspace: Dict[str, Any] = kwargs.get("workspace", {})
        if data in workspace:
            logging.info("Resolving 'data' parameter from workspace key '%s'...", data)
            data = str(workspace[data])
        prompt = f"""
You are a data analysis expert. Your task is to answer a specific query based ONLY on the provided data. Do not use any external knowledge. If the answer cannot be found in the data, state that clearly.

--- DATA ---
{data}

--- QUERY ---
{query}

Respond with ONLY the direct answer to the query.
"""
        try:
            resp = await monitored_chat_completion(
                role="tool_action",
                messages=[{"role": "system", "content": prompt}]
            )
            if resp.choices and resp.choices[0].message.content:
                answer = resp.choices[0].message.content.strip()
                return {"status": "success", "answer": answer}
            return {"status": "failure", "error": "No answer returned from LLM."}
        except Exception as e:
            return {"status": "failure", "error": str(e)}

    @register_innate_action(
        "orchestrator", "Executes a sandboxed block of Python code."
    )
    async def execute_python_code(
        self, code: Optional[str] = None, timeout_seconds: int = 30, **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Executes Python code in a separate, sandboxed process with a timeout.
        This is a high-security measure to prevent the AGI from affecting its own
        runtime or accessing unauthorized resources.
        """
        if code is None:
            return {
                "status": "failure",
                "description": "execute_python_code was called without code.",
            }
        logging.warning("Executing sandboxed Python code:\n---\n%s\n---", code)

        loop = asyncio.get_running_loop()
        result_queue: "Queue[Dict[str, Any]]" = Queue()

        try:
            # Schedule the sandboxed execution in a separate process
            future = loop.run_in_executor(
                self.process_pool, _execute_sandboxed_code, code, result_queue
            )
            # Wait for the result with a timeout
            await asyncio.wait_for(future, timeout=timeout_seconds)
            result = result_queue.get()

            if result["status"] == "success":
                logging.info("Code execution successful. Output:\n%s", result["output"])
            else:
                logging.error("Code execution failed. Error: %s", result.get("error"))

            return result

        except asyncio.TimeoutError:
            logging.error("Code execution timed out after %d seconds.", timeout_seconds)
            # It's difficult to forcefully kill the process in the pool,
            # but the result from that process will be ignored.
            return {
                "status": "failure",
                "description": "Error: Code execution took too long and was terminated.",
            }
        except Exception as e:
            error_message = (
                f"An error occurred during code execution management: {type(e).__name__}: {e}"
            )
            logging.error(error_message, exc_info=True)
            return {"status": "failure", "description": error_message}

    @register_innate_action(
        "orchestrator", "Reads the content of one of the AGI's own source code files."
    )
    async def read_own_source_code(
        self, file_name: str, **kwargs: Any
    ) -> Dict[str, Any]:
        source_dir = os.path.join(PROJECT_ROOT, "symbolic_agi")
        if not file_name:
            logging.info("Listing source code files.")
            try:
                files = [f for f in os.listdir(source_dir) if f.endswith(".py")]
                return {"status": "success", "files": files}
            except Exception as e:
                return {
                    "status": "failure",
                    "description": f"An error occurred while listing source files: {e}",
                }
        logging.info(
            "Performing self-reflection by reading source code: %s", file_name
        )
        try:
            safe_file_path = self._get_safe_path(file_name, source_dir)
            with open(safe_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {
                "status": "success",
                "content": f"Source code for '{file_name}':\n\n{content}",
            }
        except PermissionError as e:
            return {"status": "failure", "description": str(e)}
        except FileNotFoundError:
            return {
                "status": "failure",
                "description": f"Source file '{file_name}' not found.",
            }
        except Exception as e:
            return {
                "status": "failure",
                "description": f"An error occurred while reading source file: {e}",
            }

    @register_innate_action(
        "orchestrator", "Reads a core AGI data file (e.g., profiles, skills)."
    )
    async def read_core_file(self, file_name: str, **kwargs: Any) -> Dict[str, Any]:
        logging.info("Attempting to read core AGI file: %s", file_name)
        allowed_files = [
            "consciousness_profile.json",
            "identity_profile.json",
            "long_term_goals.json",
            "learned_skills.json",
            "reasoning_mutations.json",
        ]
        if file_name not in allowed_files:
            return {
                "status": "failure",
                "description": f"Permission denied: '{file_name}' is not a readable core file.",
            }
        try:
            safe_file_path = self._get_safe_path(file_name, config.DATA_DIR)
            with open(safe_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"status": "success", "content": content}
        except PermissionError as e:
            return {"status": "failure", "description": str(e)}
        except FileNotFoundError:
            return {
                "status": "failure",
                "description": (
                    f"Core file '{file_name}' not found. Use 'list_files' on workspace."
                ),
            }
        except Exception as e:
            return {
                "status": "failure",
                "description": f"An error occurred while reading core file: {e}",
            }

    @register_innate_action(
        "orchestrator", "Lists files in a directory within the workspace."
    )
    async def list_files(self, directory: str = ".", **kwargs: Any) -> Dict[str, Any]:
        try:
            base_path = self.workspace_dir
            target_path = os.path.abspath(os.path.join(base_path, directory))
            if os.path.commonpath([base_path]) != os.path.commonpath(
                [base_path, target_path]
            ):
                raise PermissionError(
                    "File access denied: path is outside the workspace directory."
                )
            files = os.listdir(target_path)
            return {"status": "success", "files": files}
        except Exception as e:
            return {"status": "failure", "description": f"An error occurred: {e}"}

    @register_innate_action(
        "orchestrator", "Writes content to a file in the workspace."
    )
    async def write_file(
        self, file_path: str, content: Optional[str] = None, **kwargs: Any
    ) -> Dict[str, Any]:
        try:
            workspace: Dict[str, Any] = kwargs.get("workspace", {})
            if isinstance(content, str) and content in workspace:
                content = str(workspace[content])
                logging.info(
                    "Resolved 'content' parameter from workspace key '%s...'",
                    content[:20],
                )
            if content is None:
                return {
                    "status": "failure",
                    "description": (
                        "write_file was called without content in parameters or workspace."
                    ),
                }
            safe_file_path = self._get_safe_path(file_path, self.workspace_dir)
            with open(safe_file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {
                "status": "success",
                "description": f"Successfully wrote to '{file_path}'.",
            }
        except Exception as e:
            return {
                "status": "failure",
                "description": f"An error occurred while writing file: {e}",
            }

    @register_innate_action(
        "orchestrator", "Reads the content of a file from the workspace."
    )
    async def read_file(self, file_path: str, **kwargs: Any) -> Dict[str, Any]:
        try:
            safe_file_path = self._get_safe_path(file_path, self.workspace_dir)
            with open(safe_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"status": "success", "content": content}
        except Exception as e:
            return {
                "status": "failure",
                "description": f"An error occurred while reading file: {e}",
            }

    @register_innate_action(
        "orchestrator", "Analyzes an image from a URL and returns a description."
    )
    async def analyze_image(
        self,
        image_url: str,
        prompt: str = "Describe this image in detail.",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        logging.info("Analyzing image from URL: %s", image_url)
        if not self._is_url_allowed(image_url):
            return {
                "status": "failure",
                "description": f"Access to URL '{image_url}' is blocked by the security policy.",
            }
        try:
            response = await monitored_chat_completion(
                role="tool_action",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    }
                ],
                max_tokens=500,
                timeout=45.0,
            )
            if response.choices and response.choices[0].message.content:
                return {
                    "status": "success",
                    "description": response.choices[0].message.content,
                }
            return {
                "status": "failure",
                "description": "Image analysis returned no content.",
            }
        except Exception as e:
            return {
                "status": "failure",
                "description": f"An error occurred during image analysis: {e}",
            }

    @register_innate_action(
        "orchestrator", "Fetches and returns the text content of a webpage."
    )
    async def browse_webpage(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        logging.info("Browse webpage: %s", url)
        if not self._is_url_allowed(url):
            return {
                "status": "failure",
                "description": f"Access to URL '{url}' is blocked by the security policy.",
            }
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/91.0.4472.124 Safari/537.36"
                )
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()
            text_chunks = (
                phrase.strip()
                for line in soup.get_text().splitlines()
                for phrase in line.split("  ")
            )
            text = "\n".join(chunk for chunk in text_chunks if chunk)
            return (
                {"status": "success", "content": text[:8000]}
                if text
                else {"status": "failure", "description": "Could not extract text."}
            )
        except Exception as e:
            return {
                "status": "failure",
                "description": f"An error occurred while Browse webpage: {e}",
            }

    @register_innate_action(
        "orchestrator", "Performs a web search and returns the results."
    )
    async def web_search(
        self, query: str, num_results: int = 3, **kwargs: Any
    ) -> Dict[str, Any]:
        logging.info("Executing REAL web search for query: '%s'", query)
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=num_results))

            allowed_results = [
                res for res in results if self._is_url_allowed(res["href"])
            ]
            if len(allowed_results) < len(results):
                filtered_count = len(results) - len(allowed_results)
                logging.warning(
                    "Filtered out %d search results due to security policy.",
                    filtered_count,
                )

            if not allowed_results:
                return {
                    "status": "success",
                    "data": "No results found from allowed domains.",
                }

            search_summary = "\n\n".join(
                f"Title: {res['title']}\nSnippet: {res['body']}\nURL: {res['href']}"
                for res in allowed_results
            )
            return {"status": "success", "data": search_summary}
        except Exception as e:
            return {
                "status": "failure",
                "description": f"An error occurred during web search: {e}",
            }

    @register_innate_action(
        "orchestrator", "Gets the current date and time in UTC."
    )
    async def get_current_datetime(
        self, _timezone_str: str = "UTC", **kwargs: Any
    ) -> Dict[str, Any]:
        try:
            return {
                "status": "success",
                "data": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "status": "failure",
                "description": f"Could not get current time: {e}",
            }
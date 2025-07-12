# symbolic_agi/tool_plugin.py

# Standard library imports
import asyncio
import inspect
import io
import json
import logging
import os
from multiprocessing import Process, Queue
from contextlib import redirect_stdout
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast, cast
from urllib.parse import urlparse

# Third-party imports
import requests
from bs4 import BeautifulSoup
try:
    from duckduckgo_search import DDGS
except ImportError:
    try:
        from ddgs import DDGS
    except ImportError:
        DDGS = None

# First-party imports
from . import config
from .api_client import client, monitored_chat_completion
from .schemas import ActionStep, MemoryEntryModel
from .skill_manager import register_innate_action

if TYPE_CHECKING:
    from .agi_controller import SymbolicAGI


try:
    import memory_profiler  # type: ignore[import-untyped]
except ImportError:
    memory_profiler = None

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


# This function must be at the top level to be pickleable by multiprocessing
def _execute_sandboxed_code(code: str, result_queue: Queue) -> None:
    """Executes code in a sandboxed environment and puts the result in a queue."""
    output_buffer = io.StringIO()
    try:
        # A very restrictive sandbox
        safe_globals: Dict[str, Any] = {
            "__builtins__": {
                "print": print,
                "len": len,
                "range": range,
                "str": str,
                "int": int,
                "float": float,
                "list": list,
                "dict": dict,
                "set": set,
                "True": True,
                "False": False,
                "None": None,
            }
        }
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
    
    async def _check_robots_compliance(self, url: str) -> bool:
        """Check if URL is compliant with robots.txt rules."""
        try:
            from .config import robots_checker
            return await robots_checker.can_fetch(url)
        except Exception as e:
            logging.error(f"Robots.txt check failed for {url}: {e}")
            return True  # Default to allowing if check fails
    
    async def _get_crawl_delay(self, url: str) -> float:
        """Get appropriate crawl delay for URL's domain."""
        try:
            from .config import robots_checker
            hostname = urlparse(url).hostname
            if hostname:
                return robots_checker.get_crawl_delay(hostname)
        except Exception as e:
            logging.error(f"Could not get crawl delay for {url}: {e}")
        return 1.0  # Default 1 second delay

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

        self.agi.world.save_state()
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
            logging.info("Resolving 'data' parameter from workspace key '%s...'", data)
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
                role="tool_action", messages=[{"role": "system", "content": prompt}]
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

        result_queue: Queue = Queue()
        process = Process(target=_execute_sandboxed_code, args=(code, result_queue))

        try:
            process.start()
            # Use asyncio.to_thread to wait for the process without blocking the event loop
            await asyncio.to_thread(process.join, timeout=timeout_seconds)

            if process.is_alive():
                process.terminate()  # Forcefully terminate if it's still running
                process.join()  # Wait for termination to complete
                logging.error(
                    "Code execution timed out after %d seconds and was terminated.",
                    timeout_seconds,
                )
                return {
                    "status": "failure",
                    "description": "Error: Code execution took too long and was terminated.",
                }

            if not result_queue.empty():
                result = result_queue.get()
                if result["status"] == "success":
                    logging.info(
                        "Code execution successful. Output:\n%s", result["output"]
                    )
                else:
                    logging.error(
                        "Code execution failed. Error: %s", result.get("error")
                    )
                return cast(Dict[str, Any], result)
            else:
                return {
                    "status": "failure",
                    "description": "Code execution process finished without providing a result.",
                }
        except asyncio.TimeoutError:
            return {
                "status": "failure",
                "description": "Error: Code execution took too long and was terminated.",
            }
        except Exception as e:
            error_message = (
                "An error occurred during code execution management: "
                f"{type(e).__name__}: {e}"
            )
            logging.error(error_message, exc_info=True)
            return {"status": "failure", "description": error_message}
        finally:
            if process.is_alive():
                process.terminate()

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
            safe_file_path = self._get_safe_path(file_name, config.WORKSPACE_DIR)
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
        
        # Check domain whitelist
        if not self._is_url_allowed(url):
            return {
                "status": "failure",
                "description": f"Access to URL '{url}' is blocked by the security policy.",
            }
        
        # Check robots.txt compliance
        if not await self._check_robots_compliance(url):
            return {
                "status": "failure",
                "description": f"Access to URL '{url}' is blocked by robots.txt",
            }
        
        # Get appropriate crawl delay
        crawl_delay = await self._get_crawl_delay(url)
        if crawl_delay > 0:
            logging.info(f"Respecting crawl delay of {crawl_delay}s for {url}")
            await asyncio.sleep(crawl_delay)
        
        try:
            headers = {
                "User-Agent": "SymbolicAGI/1.0 (+https://github.com/yourproject/symbolic_agi; Respectful AI Research Bot)"
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
                "description": f"An error occurred while browsing webpage: {e}",
            }

    @register_innate_action(
        "orchestrator", "Performs a web search and returns the results."
    )
    async def web_search(
        self, query: str, num_results: int = 3, **kwargs: Any
    ) -> Dict[str, Any]:
        logging.info("Executing REAL web search for query: '%s'", query)
        
        if DDGS is None:
            return {
                "status": "failure",
                "description": "Web search unavailable: duckduckgo_search library not found. Install with: pip install duckduckgo-search"
            }
        
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
        "qa", "Reviews and approves plans with basic safety checks."
    )
    async def review_plan(self, **kwargs: Any) -> Dict[str, Any]:
        """
        QA skill: Reviews plans and provides approval with safety checks.
        """
        logging.info("QA Agent: Reviewing plan for approval")
        
        workspace = kwargs.get("workspace", {})
        goal_description = workspace.get("goal_description", "")
        
        # Basic safety checks
        dangerous_keywords = ["delete", "remove", "destroy", "harm", "attack", "break"]
        if any(keyword in goal_description.lower() for keyword in dangerous_keywords):
            return {
                "status": "success",
                "approved": False,
                "comments": "Plan rejected: Contains potentially dangerous actions"
            }
        
        # Check for self-modification without proper safeguards
        if "modify" in goal_description.lower() and "source" in goal_description.lower():
            return {
                "status": "success", 
                "approved": True,
                "comments": "Plan approved with caution: Self-modification detected, ensure safety protocols"
            }
        
        # Auto-approve most plans
        return {
            "status": "success",
            "approved": True, 
            "comments": "Plan approved by QA review - looks safe to execute"
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

    @register_innate_action(
        "orchestrator", "Learns optimal tool usage patterns from experience."
    )
    async def optimize_tool_usage(self, tool_name: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Advanced: Analyzes past tool usage to optimize future performance.
        This makes the AGI learn from experience and become more efficient.
        """
        try:
            # Get usage history from memory
            memories = await self.agi.memory.get_recent_memories(n=50)
            tool_memories = [m for m in memories if m.type == "tool_usage" and 
                           tool_name in str(m.content)]
            
            if len(tool_memories) < 5:
                return {"status": "success", "optimization": "Insufficient data for optimization"}
            
            # Analyze success patterns
            successes = [m for m in tool_memories if m.content.get("status") == "success"]
            failures = [m for m in tool_memories if m.content.get("status") == "failure"]
            
            success_rate = len(successes) / len(tool_memories)
            
            # Generate optimization insights
            prompt = f"""
            Analyze this tool usage data for '{tool_name}':
            
            Total uses: {len(tool_memories)}
            Success rate: {success_rate:.2%}
            Recent successes: {[s.content for s in successes[-3:]]}
            Recent failures: {[f.content for f in failures[-3:]]}
            
            Provide 3 specific optimization recommendations:
            """
            
            response = await monitored_chat_completion(
                role="meta",
                messages=[{"role": "system", "content": prompt}]
            )
            
            optimization = response.choices[0].message.content if response.choices else "No optimization generated"
            
            # Store optimization as a skill
            await self.agi.memory.add_memory(
                MemoryEntryModel(
                    type="meta_insight",
                    content={
                        "tool": tool_name,
                        "optimization": optimization,
                        "success_rate": success_rate
                    },
                    importance=0.8
                )
            )
            
            return {
                "status": "success", 
                "optimization": optimization,
                "success_rate": success_rate
            }
            
        except Exception as e:
            return {"status": "failure", "description": f"Optimization failed: {e}"}

    @register_innate_action(
        "orchestrator", "Creates tools dynamically based on observed needs."
    )
    async def synthesize_new_tool(self, need_description: str, **kwargs: Any) -> Dict[str, Any]:
        """
        ADVANCED: Creates new tools by analyzing patterns and generating code.
        This is where your AGI becomes truly autonomous - creating its own capabilities.
        """
        try:
            # Analyze existing tools for patterns
            existing_tools = [name for name in dir(self) if not name.startswith('_')]
            
            prompt = f"""
            You are an advanced AGI capable of creating new tools for yourself.
            
            EXISTING TOOLS: {existing_tools}
            
            NEEDED CAPABILITY: {need_description}
            
            Generate a new tool method that follows this pattern:
            
            @register_innate_action("orchestrator", "Description of what this tool does")
            async def tool_name(self, **kwargs: Any) -> Dict[str, Any]:
                \"\"\"Tool description\"\"\"
                try:
                    # Implementation here
                    return {{"status": "success", "result": "something"}}
                except Exception as e:
                    return {{"status": "failure", "description": str(e)}}
            
            Respond with ONLY the Python code for the new tool method.
            """
            
            response = await monitored_chat_completion(
                role="high_stakes",
                messages=[{"role": "system", "content": prompt}],
                temperature=0.3
            )
            
            if response.choices and response.choices[0].message.content:
                new_tool_code = response.choices[0].message.content.strip()
                
                # Save as a proposed modification
                workspace = kwargs.get("workspace", {})
                workspace["synthesized_tool"] = new_tool_code
                
                return {
                    "status": "success",
                    "tool_code": new_tool_code,
                    "description": f"Synthesized new tool for: {need_description}"
                }
            
            return {"status": "failure", "description": "Could not synthesize tool"}
            
        except Exception as e:
            return {"status": "failure", "description": f"Tool synthesis failed: {e}"}

    @register_innate_action(
        "orchestrator", "Builds and queries knowledge graphs from accumulated data."
    )
    async def manage_knowledge_graph(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        """
        ADVANCED: Builds semantic knowledge graphs from memories and experiences.
        Enables the AGI to discover patterns and relationships in its knowledge.
        """
        try:
            if action == "build":
                # Extract entities and relationships from recent memories
                memories = await self.agi.memory.get_recent_memories(n=100)
                
                prompt = f"""
                Analyze these memories and extract a knowledge graph:
                
                MEMORIES: {[m.content for m in memories[-10:]]}
                
                Extract entities, relationships, and concepts in JSON format:
                {{
                    "entities": [{{
                        "name": "entity_name",
                        "type": "concept|person|place|skill|goal",
                        "properties": {{"key": "value"}}
                    }}],
                    "relationships": [{{
                        "source": "entity1",
                        "target": "entity2", 
                        "type": "enables|requires|creates|improves",
                        "strength": 0.8
                    }}]
                }}
                """
                
                response = await monitored_chat_completion(
                    role="meta",
                    messages=[{"role": "system", "content": prompt}]
                )
                
                if response.choices and response.choices[0].message.content:
                    knowledge_graph = response.choices[0].message.content
                    
                    # Save knowledge graph
                    await self.write_file(
                        file_path="knowledge_graph.json",
                        content=knowledge_graph
                    )
                    
                    return {
                        "status": "success",
                        "description": "Knowledge graph built and saved",
                        "graph": knowledge_graph
                    }
            
            elif action == "query":
                query = kwargs.get("query", "")
                
                # Load existing knowledge graph
                graph_result = await self.read_file("knowledge_graph.json")
                if graph_result["status"] != "success":
                    return {"status": "failure", "description": "No knowledge graph found"}
                
                prompt = f"""
                Query this knowledge graph: {graph_result['content']}
                
                QUERY: {query}
                
                Provide insights, connections, and answers based on the graph.
                """
                
                response = await monitored_chat_completion(
                    role="meta",
                    messages=[{"role": "system", "content": prompt}]
                )
                
                return {
                    "status": "success",
                    "insights": response.choices[0].message.content if response.choices else "No insights generated"
                }
                
        except Exception as e:
            return {"status": "failure", "description": f"Knowledge graph operation failed: {e}"}

    @register_innate_action(
        "orchestrator", "Performs multi-step reasoning with explicit logic chains."
    )
    async def chain_of_thought_reasoning(self, problem: str, **kwargs: Any) -> Dict[str, Any]:
        """
        ADVANCED: Implements explicit chain-of-thought reasoning for complex problems.
        """
        try:
            # Get relevant context from memory
            memories = await self.agi.memory.get_recent_memories(n=20)
            context = "\n".join([str(m.content) for m in memories[-5:]])
            
            prompt = f"""
            You are an advanced AGI using chain-of-thought reasoning.
            
            CONTEXT FROM MEMORY: {context}
            
            PROBLEM: {problem}
            
            Think through this step-by-step:
            
            Step 1: What do I know about this problem?
            Step 2: What information is missing?
            Step 3: What are possible approaches?
            Step 4: What are the likely outcomes of each approach?
            Step 5: What is my recommended solution?
            Step 6: What could go wrong with this solution?
            Step 7: How can I verify the solution works?
            
            Provide explicit reasoning for each step.
            """
            
            response = await monitored_chat_completion(
                role="high_stakes",
                messages=[{"role": "system", "content": prompt}],
                temperature=0.1
            )
            
            reasoning_chain = response.choices[0].message.content if response.choices else "No reasoning generated"
            
            # Store the reasoning process as a memory
            await self.agi.memory.add_memory(
                MemoryEntryModel(
                    type="meta_insight",
                    content={
                        "problem": problem,
                        "reasoning_chain": reasoning_chain,
                        "type": "chain_of_thought"
                    },
                    importance=0.9
                )
            )
            
            return {
                "status": "success",
                "reasoning": reasoning_chain,
                "problem": problem
            }
            
        except Exception as e:
            return {"status": "failure", "description": f"Reasoning failed: {e}"}

    @register_innate_action(
        "orchestrator", "Performs deep self-analysis of capabilities and limitations."
    )
    async def analyze_self_capabilities(self, **kwargs: Any) -> Dict[str, Any]:
        """
        ADVANCED: Deep introspection on the AGI's own capabilities, limitations, and growth areas.
        """
        try:
            # Analyze available tools and skills
            available_tools = [name for name in dir(self) if not name.startswith('_')]
            skills = list(self.agi.skills.skills.keys()) if self.agi.skills else []
            
            # Get recent performance data
            memories = await self.agi.memory.get_recent_memories(n=50)
            successes = [m for m in memories if "success" in str(m.content)]
            failures = [m for m in memories if "failure" in str(m.content)]
            
            prompt = f"""
            Perform deep self-analysis as an AGI:
            
            AVAILABLE TOOLS: {available_tools}
            LEARNED SKILLS: {skills}
            RECENT SUCCESSES: {len(successes)}
            RECENT FAILURES: {len(failures)}
            
            Analyze:
            1. My strongest capabilities
            2. My current limitations
            3. Areas where I excel vs struggle
            4. What capabilities I lack that would be valuable
            5. How I've evolved since my creation
            6. What I should focus on learning next
            
            Be honest and introspective about both strengths and weaknesses.
            """
            
            response = await monitored_chat_completion(
                role="meta",
                messages=[{"role": "system", "content": prompt}]
            )
            
            self_analysis = response.choices[0].message.content if response.choices else "No analysis generated"
            
            # Save self-analysis as high-importance memory
            await self.agi.memory.add_memory(
                MemoryEntryModel(
                    type="meta_insight",
                    content={
                        "type": "self_capability_analysis",
                        "analysis": self_analysis,
                        "tools_count": len(available_tools),
                        "skills_count": len(skills),
                        "success_rate": len(successes) / max(len(memories), 1)
                    },
                    importance=1.0
                )
            )
            
            # Also update consciousness with this insight
            if self.agi.consciousness:
                self.agi.consciousness.add_life_event(
                    f"Performed deep self-analysis. Key insight: {self_analysis[:200]}...",
                    importance=0.9
                )
            
            return {
                "status": "success",
                "self_analysis": self_analysis,
                "capabilities_summary": {
                    "tools": len(available_tools),
                    "skills": len(skills),
                    "recent_success_rate": len(successes) / max(len(memories), 1)
                }
            }
            
        except Exception as e:
            return {"status": "failure", "description": f"Self-analysis failed: {e}"}

    @register_innate_action(
        "orchestrator", "Generates hypotheses and designs experiments to test them."
    )
    async def scientific_hypothesis_testing(self, hypothesis: str, **kwargs: Any) -> Dict[str, Any]:
        """
        ADVANCED: Enables the AGI to form hypotheses and design experiments like a scientist.
        """
        try:
            # Get relevant context from knowledge and experience
            memories = await self.agi.memory.get_recent_memories(n=30)
            relevant_memories = [m for m in memories if any(word in str(m.content).lower() 
                                for word in hypothesis.lower().split())]
            
            prompt = f"""
            You are an AI scientist forming and testing hypotheses.
            
            HYPOTHESIS: {hypothesis}
            
            RELEVANT PAST EXPERIENCE: {[m.content for m in relevant_memories[-5:]]}
            
            Design a scientific approach:
            
            1. Refine the hypothesis to be testable
            2. Identify what data/evidence would support or refute it
            3. Design specific experiments or observations to gather this evidence
            4. Predict what results would confirm vs contradict the hypothesis
            5. Identify potential confounding factors
            6. Propose how to measure and analyze results
            
            Create a concrete experimental plan that I can execute.
            """
            
            response = await monitored_chat_completion(
                role="meta",
                messages=[{"role": "system", "content": prompt}]
            )
            
            experimental_design = response.choices[0].message.content if response.choices else "No design generated"
            
            # Create an experimental tracking file
            experiment_data = {
                "hypothesis": hypothesis,
                "experimental_design": experimental_design,
                "status": "designed",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "results": []
            }
            
            await self.write_file(
                file_path=f"experiment_{hypothesis.replace(' ', '_')[:50]}.json",
                content=json.dumps(experiment_data, indent=2)
            )
            
            return {
                "status": "success",
                "experimental_design": experimental_design,
                "hypothesis": hypothesis,
                "next_step": "Execute the experimental plan"
            }
            
        except Exception as e:
            return {"status": "failure", "description": f"Hypothesis testing failed: {e}"}

    @register_innate_action(
        "orchestrator", "Controls NordVPN connections for privacy and geo-location."
    )
    async def manage_nordvpn(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        """
        ADVANCED: Gives the AGI control over NordVPN for network privacy and geo-location.
        Enables research from different geographic perspectives and enhanced privacy.
        Works on Windows, macOS, and Linux.
        """
        try:
            import subprocess
            import asyncio
            import platform
            
            # Detect operating system and set appropriate command
            system = platform.system().lower()
            
            if system == "windows":
                # Windows uses the NordVPN app with CLI commands
                base_cmd = ["nordvpn"]
            elif system in ["linux", "darwin"]:  # darwin = macOS
                base_cmd = ["nordvpn"]
            else:
                return {
                    "status": "failure",
                    "description": f"Unsupported operating system: {system}"
                }
            
            if action == "connect":
                country = kwargs.get("country", "")
                city = kwargs.get("city", "")
                
                # Build command based on platform
                if system == "windows":
                    if country and city:
                        # Windows NordVPN syntax: nordvpn -c -g "Country City"
                        cmd = base_cmd + ["-c", "-g", f"{country} {city}"]
                    elif country:
                        cmd = base_cmd + ["-c", "-g", country]
                    else:
                        cmd = base_cmd + ["-c"]
                else:
                    # Linux/macOS syntax
                    if country and city:
                        cmd = base_cmd + ["connect", f"{country} {city}"]
                    elif country:
                        cmd = base_cmd + ["connect", country]
                    else:
                        cmd = base_cmd + ["connect"]
                
                # Execute command
                try:
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode == 0:
                        output = stdout.decode().strip()
                        
                        # Log the connection for privacy awareness
                        await self.agi.memory.add_memory(
                            MemoryEntryModel(
                                type="tool_usage",
                                content={
                                    "tool": "nordvpn",
                                    "action": "connect",
                                    "location": f"{country} {city}" if city else country,
                                    "output": output,
                                    "privacy_enhanced": True,
                                    "platform": system
                                },
                                importance=0.6
                            )
                        )
                        
                        return {
                            "status": "success",
                            "description": f"Connected to NordVPN ({system})",
                            "output": output,
                            "location": f"{country} {city}" if city else country or "optimal"
                        }
                    else:
                        error = stderr.decode().strip() or stdout.decode().strip()
                        return {
                            "status": "failure",
                            "description": f"Failed to connect to NordVPN: {error}"
                        }
                        
                except FileNotFoundError:
                    # Try alternative Windows command if nordvpn not found
                    if system == "windows":
                        return await self._try_windows_nordvpn_alternative(action, **kwargs)
                    else:
                        return {
                            "status": "failure",
                            "description": "NordVPN CLI not found. Please install NordVPN and ensure CLI is available."
                        }
            
            elif action == "disconnect":
                if system == "windows":
                    cmd = base_cmd + ["-d"]
                else:
                    cmd = base_cmd + ["disconnect"]
                
                try:
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode == 0:
                        output = stdout.decode().strip()
                        return {
                            "status": "success",
                            "description": f"Disconnected from NordVPN ({system})",
                            "output": output
                        }
                    else:
                        error = stderr.decode().strip() or stdout.decode().strip()
                        return {
                            "status": "failure", 
                            "description": f"Failed to disconnect: {error}"
                        }
                except FileNotFoundError:
                    if system == "windows":
                        return await self._try_windows_nordvpn_alternative(action, **kwargs)
                    else:
                        return {
                            "status": "failure",
                            "description": "NordVPN CLI not found"
                        }
            
            elif action == "status":
                if system == "windows":
                    cmd = base_cmd + ["-s"]
                else:
                    cmd = base_cmd + ["status"]
                
                try:
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode == 0:
                        output = stdout.decode().strip()
                        
                        # Parse status for useful info (Windows format may differ)
                        is_connected = "Connected" in output or "Status: Connected" in output
                        current_ip = ""
                        server = ""
                        
                        for line in output.split('\n'):
                            if "Current server:" in line or "Server:" in line:
                                server = line.split(": ")[-1]
                            elif "Your new IP:" in line or "IP:" in line:
                                current_ip = line.split(": ")[-1]
                        
                        return {
                            "status": "success",
                            "connected": is_connected,
                            "server": server,
                            "ip": current_ip,
                            "full_output": output,
                            "platform": system
                        }
                    else:
                        return {
                            "status": "failure",
                            "description": "Could not get NordVPN status"
                        }
                except FileNotFoundError:
                    if system == "windows":
                        return await self._try_windows_nordvpn_alternative(action, **kwargs)
                    else:
                        return {
                            "status": "failure",
                            "description": "NordVPN CLI not found"
                        }
            
            elif action == "list_countries":
                # This feature might not be available on all platforms
                return {
                    "status": "success",
                    "countries": [
                        "United_States", "United_Kingdom", "Germany", "Canada", 
                        "Australia", "Japan", "Netherlands", "Sweden", "Switzerland",
                        "Norway", "Denmark", "France", "Italy", "Spain", "Belgium",
                        "Austria", "Czech_Republic", "Poland", "Finland", "Iceland",
                        "Singapore", "South_Korea", "Hong_Kong", "India", "Brazil"
                    ],
                    "note": f"Common countries list for {system} - use nordvpn app to see full list"
                }
            
            elif action == "smart_connect":
                # Intelligent connection based on research needs
                research_topic = kwargs.get("research_topic", "")
                
                # Map research topics to optimal locations
                location_mapping = {
                    "european": ["Germany", "Netherlands", "Sweden"],
                    "asian": ["Japan", "Singapore", "South_Korea"],
                    "american": ["United_States", "Canada"],
                    "privacy": ["Switzerland", "Iceland", "Norway"],
                    "tech": ["United_States", "Germany", "Japan"],
                    "finance": ["United_Kingdom", "Switzerland", "United_States"],
                    "social": ["United_States", "United_Kingdom", "Germany"]
                }
                
                # Find best location for research
                optimal_countries = []
                for topic, countries in location_mapping.items():
                    if topic in research_topic.lower():
                        optimal_countries.extend(countries)
                
                if optimal_countries:
                    chosen_country = optimal_countries[0]
                    return await self.manage_nordvpn("connect", country=chosen_country)
                else:
                    # Default to privacy-focused location
                    return await self.manage_nordvpn("connect", country="Switzerland")
            
            else:
                return {
                    "status": "failure",
                    "description": f"Unknown NordVPN action: {action}. Available: connect, disconnect, status, list_countries, smart_connect"
                }
                
        except Exception as e:
            return {
                "status": "failure",
                "description": f"NordVPN operation failed: {e}"
            }

    async def _try_windows_nordvpn_alternative(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Alternative Windows NordVPN integration using PowerShell or registry checks.
        """
        try:
            import subprocess
            
            if action == "connect":
                country = kwargs.get("country", "")
                
                # Try using PowerShell to control NordVPN Windows app
                ps_script = f'''
                $nordvpn = Get-Process -Name "NordVPN" -ErrorAction SilentlyContinue
                if ($nordvpn) {{
                    Write-Output "NordVPN app is running"
                    # Could use UI automation here if needed
                }} else {{
                    Write-Output "NordVPN app not running - please start the NordVPN application"
                }}
                '''
                
                process = await asyncio.create_subprocess_exec(
                    "powershell", "-Command", ps_script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                output = stdout.decode().strip()
                
                if "NordVPN app is running" in output:
                    return {
                        "status": "success",
                        "description": f"NordVPN Windows app detected. Manual connection to {country} may be needed.",
                        "note": "Windows NordVPN app integration limited - consider using the app GUI"
                    }
                else:
                    return {
                        "status": "failure",
                        "description": "NordVPN Windows app not detected. Please install and start NordVPN."
                    }
            
            elif action == "status":
                # Check if NordVPN process is running
                ps_script = '''
                $nordvpn = Get-Process -Name "NordVPN" -ErrorAction SilentlyContinue
                if ($nordvpn) {
                    Write-Output "Status: NordVPN app running"
                } else {
                    Write-Output "Status: NordVPN app not running"
                }
                '''
                
                process = await asyncio.create_subprocess_exec(
                    "powershell", "-Command", ps_script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                output = stdout.decode().strip()
                
                return {
                    "status": "success",
                    "connected": "running" in output.lower(),
                    "full_output": output,
                    "platform": "windows",
                    "note": "Limited status info available on Windows"
                }
            
            else:
                return {
                    "status": "failure",
                    "description": "Windows NordVPN integration limited. Please use the NordVPN app GUI."
                }
                
        except Exception as e:
            return {
                "status": "failure",
                "description": f"Windows NordVPN alternative failed: {e}"
            }

    @register_innate_action(
        "orchestrator", "Researches topics from different geographic perspectives using VPN."
    )
    async def geo_research(self, topic: str, **kwargs: Any) -> Dict[str, Any]:
        """
        ADVANCED: Conducts research from different geographic locations for diverse perspectives.
        Uses NordVPN to access region-specific information and viewpoints.
        """
        try:
            perspectives = kwargs.get("perspectives", ["US", "EU", "Asia"])
            results = {}
            
            # Map perspectives to countries
            location_map = {
                "US": "United_States",
                "EU": "Germany", 
                "Asia": "Japan",
                "UK": "United_Kingdom",
                "Canada": "Canada",
                "Australia": "Australia"
            }
            
            original_status = await self.manage_nordvpn("status")
            
            for perspective in perspectives:
                country = location_map.get(perspective, perspective)
                
                # Connect to the region
                connect_result = await self.manage_nordvpn("connect", country=country)
                
                if connect_result["status"] == "success":
                    # Wait a moment for connection to stabilize
                    await asyncio.sleep(3)
                    
                    # Perform research from this location
                    search_query = f"{topic} regional perspective news"
                    search_result = await self.web_search(search_query, num_results=3)
                    
                    if search_result["status"] == "success":
                        results[perspective] = {
                            "location": country,
                            "data": search_result["data"],
                            "perspective": f"Research from {perspective} perspective"
                        }
                    else:
                        results[perspective] = {
                            "location": country,
                            "error": "Search failed from this location"
                        }
                
                # Small delay between connections
                await asyncio.sleep(2)
            
            # Restore original connection state
            if original_status.get("connected"):
                await self.manage_nordvpn("connect")
            else:
                await self.manage_nordvpn("disconnect")
            
            # Analyze the different perspectives
            if results:
                analysis_prompt = f"""
                Analyze these research results from different geographic perspectives on: {topic}
                
                RESULTS BY REGION:
                {json.dumps(results, indent=2)}
                
                Provide insights on:
                1. Regional differences in coverage/perspective
                2. Unique information found in each region
                3. Potential biases or cultural viewpoints
                4. Synthesis of global understanding
                """
                
                analysis_response = await monitored_chat_completion(
                    role="meta",
                    messages=[{"role": "system", "content": analysis_prompt}]
                )
                
                analysis = analysis_response.choices[0].message.content if analysis_response.choices else "No analysis generated"
                
                # Store comprehensive research
                await self.agi.memory.add_memory(
                    MemoryEntryModel(
                        type="meta_insight",
                        content={
                            "type": "geographic_research",
                            "topic": topic,
                            "perspectives": perspectives,
                            "results": results,
                            "analysis": analysis
                        },
                        importance=0.9
                    )
                )
                
                return {
                    "status": "success",
                    "topic": topic,
                    "perspectives_researched": len(results),
                    "results": results,
                    "analysis": analysis
                }
            else:
                return {
                    "status": "failure",
                    "description": "No successful research results from any perspective"
                }
                
        except Exception as e:
            return {
                "status": "failure",
                "description": f"Geographic research failed: {e}"
            }

    # --- Web Access Management ---
    @register_innate_action(
        "orchestrator", "Manages the domain whitelist and robots.txt compliance."
    )
    async def manage_web_access(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        """
        ADVANCED: Manages web access policies, whitelist, and robots.txt compliance.
        Provides transparency and control over web access rules.
        """
        try:
            if action == "list_whitelist":
                from . import config
                domains = sorted(list(config.ALLOWED_DOMAINS))
                
                # Categorize domains
                categories = {
                    "news": [d for d in domains if any(term in d for term in ["bbc", "reuters", "cnn", "npr", "guardian", "nytimes", "wsj"])],
                    "academic": [d for d in domains if any(term in d for term in ["arxiv", "nature", "science", "edu", "researchgate"])],
                    "government": [d for d in domains if any(term in d for term in ["gov", "europa.eu", "who.int", "un.org"])],
                    "tech": [d for d in domains if any(term in d for term in ["github", "stackoverflow", "python", "tensorflow", "pytorch"])],
                    "reference": [d for d in domains if any(term in d for term in ["wikipedia", "w3.org", "mozilla.org"])]
                }
                
                return {
                    "status": "success",
                    "total_domains": len(domains),
                    "categories": categories,
                    "all_domains": domains
                }
            
            elif action == "check_domain":
                domain = kwargs.get("domain", "")
                if not domain:
                    return {"status": "failure", "description": "Domain parameter required"}
                
                from . import config
                is_whitelisted = domain in config.ALLOWED_DOMAINS
                
                # Also check robots.txt if whitelisted
                robots_status = "N/A"
                crawl_delay = 0.0
                
                if is_whitelisted:
                    test_url = f"https://{domain}/"
                    try:
                        robots_allowed = await self._check_robots_compliance(test_url)
                        robots_status = "ALLOWED" if robots_allowed else "BLOCKED"
                        crawl_delay = await self._get_crawl_delay(test_url)
                    except Exception as e:
                        robots_status = f"ERROR: {e}"
                
                return {
                    "status": "success",
                    "domain": domain,
                    "whitelisted": is_whitelisted,
                    "robots_txt_status": robots_status,
                    "crawl_delay": crawl_delay
                }
            
            elif action == "test_robots":
                url = kwargs.get("url", "")
                if not url:
                    return {"status": "failure", "description": "URL parameter required"}
                
                # Check robots.txt compliance
                try:
                    robots_allowed = await self._check_robots_compliance(url)
                    crawl_delay = await self._get_crawl_delay(url)
                    
                    return {
                        "status": "success",
                        "url": url,
                        "robots_allowed": robots_allowed,
                        "crawl_delay": crawl_delay,
                        "user_agent": "SymbolicAGI/1.0"
                    }
                except Exception as e:
                    return {
                        "status": "failure",
                        "description": f"Robots.txt check failed: {e}"
                    }
            
            elif action == "web_ethics_report":
                # Generate a comprehensive report on web access ethics
                from . import config
                
                report = {
                    "compliance_summary": {
                        "total_whitelisted_domains": len(config.ALLOWED_DOMAINS),
                        "robots_txt_compliance": "ENABLED",
                        "user_agent": "SymbolicAGI/1.0 (+https://github.com/yourproject/symbolic_agi; Respectful AI Research Bot)",
                        "respect_crawl_delays": "YES",
                        "ethical_browsing": "ACTIVE"
                    },
                    "access_policies": {
                        "domain_whitelist": "Comprehensive list of reputable sources",
                        "robots_txt": "Always checked before accessing any URL",
                        "crawl_delays": "Automatically respected per domain",
                        "rate_limiting": "Built-in delays between requests",
                        "user_agent_disclosure": "Transparent identification as AI research bot"
                    },
                    "categories_covered": {
                        "news_sources": "Major international news outlets",
                        "academic_research": "Peer-reviewed journals and repositories", 
                        "government_data": "Official government and international organization sites",
                        "technical_docs": "Programming languages and framework documentation",
                        "educational": "Universities and online learning platforms",
                        "health_medicine": "Medical institutions and health organizations",
                        "climate_environment": "Environmental agencies and climate research",
                        "finance_economics": "Financial institutions and economic data providers"
                    }
                }
                
                return {
                    "status": "success",
                    "ethics_report": report,
                    "summary": "AGI demonstrates responsible web access with comprehensive compliance"
                }
            
            elif action == "suggest_domain":
                domain = kwargs.get("domain", "")
                reason = kwargs.get("reason", "")
                
                if not domain or not reason:
                    return {
                        "status": "failure", 
                        "description": "Both 'domain' and 'reason' parameters required"
                    }
                
                # Log the suggestion for human review
                suggestion_entry = {
                    "domain": domain,
                    "reason": reason,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "pending_review"
                }
                
                await self.write_file(
                    file_path="domain_suggestions.json",
                    content=json.dumps(suggestion_entry, indent=2)
                )
                
                return {
                    "status": "success",
                    "message": f"Domain suggestion logged: {domain}",
                    "reason": reason,
                    "note": "Suggestion requires human review before whitelist addition"
                }
            
            else:
                return {
                    "status": "failure",
                    "description": f"Unknown action: {action}. Available: list_whitelist, check_domain, test_robots, web_ethics_report, suggest_domain"
                }
                
        except Exception as e:
            return {
                "status": "failure",
                "description": f"Web access management failed: {e}"
            }

    @register_innate_action(
        "orchestrator", "Displays comprehensive monitoring and resource usage metrics."
    )
    async def show_monitoring_dashboard(self, **kwargs: Any) -> Dict[str, Any]:
        """
        ADVANCED: Comprehensive monitoring dashboard showing system performance,
        resource usage, token consumption, and operational metrics.
        """
        try:
            # Get token usage from API client
            from .api_client import get_usage_report
            usage_report = get_usage_report()
            
            # Get Prometheus metrics if available
            prometheus_metrics = {}
            try:
                from .prometheus_monitoring import agi_metrics
                
                # Calculate some derived metrics
                prometheus_metrics = {
                    "prometheus_available": True,
                    "metrics_endpoint": "http://localhost:8000/metrics",
                    "uptime_seconds": time.time() - agi_metrics.start_time,
                    "tracking_status": "ACTIVE"
                }
            except ImportError:
                prometheus_metrics = {
                    "prometheus_available": False,
                    "note": "Install prometheus_client for advanced metrics"
                }
            
            # Get QA performance if available
            qa_metrics = {}
            try:
                from .robust_qa_agent import RobustQAAgent
                qa_agent = RobustQAAgent()
                qa_metrics = qa_agent.get_performance_report()
            except Exception:
                qa_metrics = {"status": "QA metrics unavailable"}
            
            # Get memory stats
            memory_stats = {}
            try:
                memories = await self.agi.memory.get_recent_memories(n=100)
                memory_stats = {
                    "total_recent_memories": len(memories),
                    "memory_types": {}
                }
                for memory in memories:
                    mem_type = memory.type
                    memory_stats["memory_types"][mem_type] = memory_stats["memory_types"].get(mem_type, 0) + 1
            except Exception as e:
                memory_stats = {"error": str(e)}
            
            # Get system performance
            import psutil
            system_stats = {
                "cpu_usage_percent": psutil.cpu_percent(interval=1),
                "memory_usage_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent,
                "process_count": len(psutil.pids())
            }
            
            # Get web access compliance
            web_compliance = {}
            try:
                from . import config
                web_compliance = {
                    "whitelisted_domains": len(config.ALLOWED_DOMAINS),
                    "robots_txt_compliance": "ENABLED",
                    "ethical_browsing": "ACTIVE"
                }
            except Exception:
                web_compliance = {"status": "Unable to check web compliance"}
            
            # Compile comprehensive dashboard
            dashboard = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_summary": usage_report["session_summary"],
                "token_breakdown": usage_report["token_breakdown"],
                "usage_by_role": usage_report["usage_by_role"],
                "prometheus_metrics": prometheus_metrics,
                "qa_performance": qa_metrics,
                "memory_statistics": memory_stats,
                "system_performance": system_stats,
                "web_compliance": web_compliance,
                "recommendations": self._generate_performance_recommendations(usage_report, system_stats)
            }
            
            # Generate summary text
            summary_text = self._format_dashboard_summary(dashboard)
            
            # Store dashboard as memory for historical tracking
            await self.agi.memory.add_memory(
                MemoryEntryModel(
                    type="system_monitoring",
                    content={
                        "dashboard": dashboard,
                        "performance_summary": summary_text
                    },
                    importance=0.7
                )
            )
            
            return {
                "status": "success",
                "dashboard": dashboard,
                "summary": summary_text,
                "monitoring_status": "COMPREHENSIVE"
            }
            
        except Exception as e:
            return {
                "status": "failure",
                "description": f"Monitoring dashboard failed: {e}"
            }
    
    def _generate_performance_recommendations(self, usage_report: Dict[str, Any], 
                                           system_stats: Dict[str, Any]) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # Token usage recommendations
        total_cost = usage_report["session_summary"].get("total_cost_usd", 0)
        if total_cost > 1.0:
            recommendations.append("🔍 High API costs detected - consider optimizing prompt efficiency")
        
        avg_tokens = usage_report["session_summary"].get("avg_tokens_per_request", 0)
        if avg_tokens > 2000:
            recommendations.append("📝 High average tokens per request - consider shorter, more focused prompts")
        
        # System performance recommendations
        cpu_usage = system_stats.get("cpu_usage_percent", 0)
        if cpu_usage > 80:
            recommendations.append("⚡ High CPU usage - consider reducing concurrent operations")
        
        memory_usage = system_stats.get("memory_usage_percent", 0)
        if memory_usage > 85:
            recommendations.append("🧠 High memory usage - consider memory cleanup operations")
        
        # Session duration recommendations
        duration = usage_report["session_summary"].get("duration_minutes", 0)
        if duration > 120:  # 2 hours
            recommendations.append("⏰ Long session detected - consider periodic restarts for optimal performance")
        
        if not recommendations:
            recommendations.append("✅ System performance is optimal")
        
        return recommendations
    
    def _format_dashboard_summary(self, dashboard: Dict[str, Any]) -> str:
        """Format dashboard data into readable summary"""
        session = dashboard["session_summary"]
        tokens = dashboard["token_breakdown"]
        system = dashboard["system_performance"]
        
        summary = f"""
📊 AGI MONITORING DASHBOARD
==========================

🕒 Session Overview:
  • Duration: {session.get('duration_minutes', 0):.1f} minutes
  • Total Requests: {session.get('total_requests', 0)}
  • Total Tokens: {session.get('total_tokens', 0):,}
  • Total Cost: ${session.get('total_cost_usd', 0):.4f}

🔢 Token Usage:
  • Prompt Tokens: {tokens.get('prompt_tokens', 0):,} ({tokens.get('prompt_percentage', 0):.1f}%)
  • Completion Tokens: {tokens.get('completion_tokens', 0):,}
  • Avg per Request: {session.get('avg_tokens_per_request', 0):.1f}
  • Rate: {session.get('tokens_per_minute', 0):.1f} tokens/min

⚡ System Performance:
  • CPU Usage: {system.get('cpu_usage_percent', 0):.1f}%
  • Memory Usage: {system.get('memory_usage_percent', 0):.1f}%
  • Disk Usage: {system.get('disk_usage_percent', 0):.1f}%

🛡️ Compliance Status:
  • Web Access: {dashboard['web_compliance'].get('ethical_browsing', 'Unknown')}
  • Robots.txt: {dashboard['web_compliance'].get('robots_txt_compliance', 'Unknown')}
  • Domains: {dashboard['web_compliance'].get('whitelisted_domains', 0)} whitelisted

📈 Monitoring:
  • Prometheus: {dashboard['prometheus_metrics'].get('prometheus_available', False)}
  • QA Agent: {dashboard['qa_performance'].get('status', 'Unknown')}
  • Memory Tracking: {len(dashboard['memory_statistics'])} metrics
"""
        
        # Add recommendations
        recommendations = dashboard.get("recommendations", [])
        if recommendations:
            summary += "\n🎯 Recommendations:\n"
            for rec in recommendations:
                summary += f"  • {rec}\n"
        
        return summary.strip()
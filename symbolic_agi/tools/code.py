# symbolic_agi/tools/code.py

import asyncio
import io
import json
import logging
import os
from contextlib import redirect_stdout
from multiprocessing import Process, Queue
from typing import Any, Dict, Optional, cast

import aiofiles

from symbolic_agi.tools.base import BaseTool
from symbolic_agi import config, prompts
from symbolic_agi.api_client import monitored_chat_completion
from symbolic_agi.schemas import ActionStep, MemoryEntryModel
from symbolic_agi.skill_manager import register_innate_action

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def _execute_sandboxed_code(code: str, result_queue: Queue) -> None:
    """Executes code in a sandboxed environment and puts the result in a queue."""
    output_buffer = io.StringIO()
    try:
        safe_globals: Dict[str, Any] = {
            "__builtins__": {
                "print": print, "len": len, "range": range, "str": str, "int": int,
                "float": float, "list": list, "dict": dict, "set": set,
                "True": True, "False": False, "None": None,
            }
        }
        with redirect_stdout(output_buffer):
            exec(code, safe_globals, {})
        result = {"status": "success", "output": output_buffer.getvalue()}
    except Exception as e:
        result = {"status": "failure", "output": output_buffer.getvalue(), "error": str(e)}
    result_queue.put(result)

class CodeTools(BaseTool):
    """Tools for executing, proposing, and applying code modifications."""

    @register_innate_action("orchestrator", "Executes a sandboxed block of Python code.")
    async def execute_python_code(self, code: Optional[str] = None, timeout_seconds: int = 30, **kwargs: Any) -> Dict[str, Any]:
        if code is None:
            return {"status": "failure", "description": "execute_python_code was called without code."}

        logging.warning("Executing sandboxed Python code:\n---\n%s\n---", code)
        result_queue: Queue = Queue()
        process = Process(target=_execute_sandboxed_code, args=(code, result_queue))

        try:
            process.start()
            await asyncio.to_thread(process.join, timeout=timeout_seconds)

            if process.is_alive():
                process.terminate()
                process.join()
                return {"status": "failure", "description": "Error: Code execution took too long and was terminated."}

            if not result_queue.empty():
                return cast(Dict[str, Any], result_queue.get())
            else:
                return {"status": "failure", "description": "Code execution process finished without providing a result."}
        except Exception as e:
            return {"status": "failure", "description": f"An error occurred during code execution management: {e}"}
        finally:
            if process.is_alive():
                process.terminate()

    @register_innate_action("orchestrator", "Safely proposes a change to one of the AGI's source code files.")
    async def propose_code_modification(self, file_path: str, change_description: str, **kwargs: Any) -> Dict[str, Any]:
        logging.info("Proposing code modification for '%s' with change: '%s'", file_path, change_description)

        read_result = await self.agi.tools.file_system.read_file(file_path=os.path.join("..", file_path))
        if read_result.get("status") != "success":
            return read_result

        raw_current_code = read_result.get("content", "")
        prompt = f"""
You are an expert Python programmer tasked with modifying your own source code.
Your task is to rewrite the entire file with the requested change applied.

--- CURRENT CODE of '{file_path}' ---
```python
{raw_current_code}
--- REQUESTED CHANGE --- {change_description}

--- INSTRUCTIONS --- Rewrite the ENTIRE file from top to bottom, incorporating the change. Do NOT add any commentary, explanations, or markdown formatting. Your response must be ONLY the raw, complete Python code for the new file. """

        try:

            resp = await monitored_chat_completion(

                role="planner",

                messages=[{"role": "system", "content": prompt}],

                temperature=0.0

            )

            if resp.choices and resp.choices[0].message.content:

                proposed_code = resp.choices[0].message.content.strip().removeprefix("python").removesuffix("").strip()

                return {"status": "success", "proposed_code": proposed_code}

            return {"status": "failure", "error": "LLM returned no code for modification."}

        except Exception as e:

            return {"status": "failure", "error": f"Error during code modification proposal: {e}"}

@register_innate_action("orchestrator", "HIGH-RISK: Applies a proposed code change after safety evaluation.")
async def apply_code_modification(self, file_path: str, proposed_code_key: str, **kwargs: Any) -> Dict[str, Any]:
    logging.warning("Attempting to apply code modification to '%s'. This is a high-risk action.", file_path)
    workspace: Dict[str, Any] = kwargs.get("workspace", {})
    proposed_code = workspace.get(proposed_code_key)

    if not proposed_code or not isinstance(proposed_code, str):
        return {"status": "failure", "description": f"Could not find code in workspace with key '{proposed_code_key}'."}

    is_safe = await self.agi.evaluator.evaluate_self_modification(proposed_code=proposed_code, file_path=file_path)
    if not is_safe:
        return {"status": "failure", "description": "The proposed self-modification was rejected by the safety evaluator."}

    logging.critical("SELF-MODIFICATION APPROVED for file '%s'. Applying changes.", file_path)
    try:
        safe_file_path = self.agi.tools.file_system._get_safe_path(os.path.join("..", file_path))
        async with aiofiles.open(safe_file_path, "w", encoding="utf-8") as f:
            await f.write(proposed_code)
        return {"status": "success", "description": f"Successfully applied modification to '{file_path}'. Restart required."}
    except Exception as e:
        return {"status": "failure", "description": f"An error occurred while writing approved modification: {e}"}
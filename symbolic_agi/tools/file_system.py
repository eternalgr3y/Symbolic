# symbolic_agi/tools/file_system.py

import os
import logging
from typing import Dict, Any

import aiofiles

from symbolic_agi.tools.base import BaseTool
from symbolic_agi import config
from symbolic_agi.skill_manager import register_innate_action

class FileSystemTools(BaseTool):
    """Tools for interacting with the local file system within the workspace."""

    def __init__(self, agi):
        super().__init__(agi)
        self.workspace_dir = os.path.abspath(config.WORKSPACE_DIR)
        os.makedirs(self.workspace_dir, exist_ok=True)

    def _get_safe_path(self, file_path: str) -> str:
        """Ensures the file path is within the allowed workspace directory."""
        base_path = self.workspace_dir
        # Normalize the path to prevent directory traversal attacks (e.g., ../../)
        safe_path = os.path.abspath(os.path.join(base_path, file_path))

        if not safe_path.startswith(base_path):
            raise PermissionError(f"File access denied: Path is outside the workspace directory. Attempted path: {safe_path}")
        return safe_path

    @register_innate_action("orchestrator", "Lists files in a directory within the workspace.")
    async def list_files(self, directory: str = ".", **kwargs: Any) -> Dict[str, Any]:
        try:
            safe_dir_path = self._get_safe_path(directory)
            files = os.listdir(safe_dir_path)
            return {"status": "success", "files": files}
        except PermissionError as e:
            return {"status": "failure", "description": str(e)}
        except Exception as e:
            return {"status": "failure", "description": f"An error occurred while listing files: {e}"}

    @register_innate_action("orchestrator", "Writes content to a file in the workspace.")
    async def write_file(self, file_path: str, content: str, **kwargs: Any) -> Dict[str, Any]:
        try:
            safe_file_path = self._get_safe_path(file_path)
            async with aiofiles.open(safe_file_path, "w", encoding="utf-8") as f:
                await f.write(content)
            return {"status": "success", "description": f"Successfully wrote to '{file_path}'."}
        except PermissionError as e:
            return {"status": "failure", "description": str(e)}
        except Exception as e:
            return {"status": "failure", "description": f"An error occurred while writing file: {e}"}

    @register_innate_action("orchestrator", "Reads the content of a file from the workspace.")
    async def read_file(self, file_path: str, **kwargs: Any) -> Dict[str, Any]:
        try:
            safe_file_path = self._get_safe_path(file_path)
            async with aiofiles.open(safe_file_path, "r", encoding="utf-8") as f:
                content = await f.read()
            return {"status": "success", "content": content}
        except PermissionError as e:
            return {"status": "failure", "description": str(e)}
        except FileNotFoundError:
            return {"status": "failure", "description": f"File '{file_path}' not found in workspace."}
        except Exception as e:
            return {"status": "failure", "description": f"An error occurred while reading file: {e}"}
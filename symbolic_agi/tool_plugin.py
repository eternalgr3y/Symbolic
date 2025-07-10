# symbolic_agi/tool_plugin.py

import inspect
import logging
from typing import TYPE_CHECKING, Any, Dict

from symbolic_agi.tools.base import BaseTool
from symbolic_agi.tools.code import CodeTools
from symbolic_agi.tools.file_system import FileSystemTools
from symbolic_agi.tools.web import WebTools

if TYPE_CHECKING:
    from .agi_controller import SymbolicAGI

class ToolPlugin:
    """
    A dynamic tool aggregator for the AGI.

    This class discovers, instantiates, and delegates calls to modular tool
    classes located in the `tools` subdirectory. This promotes a clean, 
    scalable, and maintainable architecture.
    """

    def __init__(self, agi: "SymbolicAGI"):
        self.agi = agi
        self.logger = logging.getLogger(self.__class__.__name__)

        # Instantiate and register all tool modules
        self.file_system = FileSystemTools(agi)
        self.web = WebTools(agi)
        self.code = CodeTools(agi)

        self.plugins = [self.file_system, self.web, self.code]
        self.logger.info("ToolPlugin initialized with %d modules.", len(self.plugins))

    def __getattr__(self, name: str) -> Any:
        """
        Dynamically find and return the tool method from registered plugins.
        This makes the refactoring transparent to the rest of the system.
        """
        for plugin in self.plugins:
            if hasattr(plugin, name):
                method = getattr(plugin, name)
                if callable(method):
                    self.logger.debug("Delegating call for '%s' to %s", name, plugin.__class__.__name__)
                    return method

        raise AttributeError(f"'{self.__class__.__name__}' and its plugins have no attribute '{name}'")

    def get_all_tool_definitions(self) -> Dict[str, Any]:
        """
        Gathers all action definitions from the registered tool plugins.
        """
        all_actions = {}
        for plugin in self.plugins:
            for method_name, method in inspect.getmembers(plugin, predicate=inspect.iscoroutinefunction):
                if hasattr(method, "_innate_action_def"):
                    action_def = getattr(method, "_innate_action_def")
                    all_actions[action_def.name] = action_def.model_dump()
        return all_actions
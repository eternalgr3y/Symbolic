# symbolic_agi/tools/base.py

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..agi_controller import SymbolicAGI

class BaseTool:
    """Base class for all tool plugins."""
    def __init__(self, agi: "SymbolicAGI"):
        self.agi = agi
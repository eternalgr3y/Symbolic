# symbolic_agi/symbolic_lang.py

"""
Defines the primitive data structures for the AGI's symbolic language.
This is the fundamental grammar of the AGI's thought process.
"""
from typing import Dict, Any, Optional

class Eval:
    """Represents a goal or task to be evaluated."""
    def __init__(self, parameters: Dict[str, Any]):
        self.parameters = parameters

class Strategize:
    """Represents a formulated plan of action."""
    def __init__(self, plan: str, actions: Optional[list] = None):
        self.plan = plan
        self.actions = actions or []

class Reflect:
    """Represents a self-reflection or thought process."""
    def __init__(self, thoughts: str):
        self.thoughts = thoughts

class Action:
    """
    Represents a concrete action to be taken, either in the world or via a tool.
    This version supports arbitrary named parameters for maximum flexibility.
    """
    def __init__(self, command: str, **kwargs):
        """
        Args:
            command: The name of the action/command to execute.
            **kwargs: A dictionary of parameters for the command.
        """
        self.command = command
        self.parameters = kwargs

    def __repr__(self):
        return f"Action(command='{self.command}', parameters={self.parameters})"

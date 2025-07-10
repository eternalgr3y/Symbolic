# symbolic_agi/input_processor.py

import threading
from queue import Queue
from typing import Dict, Any, List, Optional, logging
from .goal_management import GoalManager, GoalPriority

class EnhancedInputProcessor:
    """Advanced input processing with command parsing and goal intelligence."""

    def __init__(self, goal_manager: GoalManager):
        self.goal_manager = goal_manager
        self.input_queue: "Queue[Dict[str, Any]]" = Queue()
        self.shutdown_event = threading.Event()
        self.command_history: List[str] = []

    def parse_input(self, user_input: str) -> Dict[str, Any]:
        """Parse user input into structured commands."""
        user_input = user_input.strip()

        if user_input.startswith('/'):
            return self._parse_command(user_input)
        else:
            return self._parse_goal(user_input)

    def _parse_command(self, command: str) -> Dict[str, Any]:
        """Parse system commands."""
        parts = command[1:].split()
        cmd = parts[0].lower()
        args = parts[1:]

        commands = {
            'status': {'type': 'status'},
            'list': {'type': 'list_goals'},
            'pause': {'type': 'pause_goal', 'goal_id': args[0] if args else None},
            'resume': {'type': 'resume_goal', 'goal_id': args[0] if args else None},
            'cancel': {'type': 'cancel_goal', 'goal_id': args[0] if args else None},
            'history': {'type': 'show_history'},
            'help': {'type': 'help'},
        }

        if cmd in commands:
            return commands[cmd]
        else:
            return {'type': 'unknown_command', 'command': cmd}

    def _parse_goal(self, goal_text: str) -> Dict[str, Any]:
        """Parse goal text and extract metadata like priority."""
        priority = GoalPriority.MEDIUM
        context = {}

        if goal_text.startswith('!!'):
            priority = GoalPriority.CRITICAL
            goal_text = goal_text[2:].strip()
        elif goal_text.startswith('!'):
            priority = GoalPriority.HIGH

        if 'urgent' in goal_text.lower():
            priority = GoalPriority.HIGH

        return {
            'type': 'goal',
            'description': goal_text,
            'priority': priority,
            'context': context
        }

    def start_input_thread(self):
        """Starts the input processing thread."""
        thread = threading.Thread(target=self._input_loop, daemon=True)
        thread.start()
        logging.info("Enhanced Input Processor thread started.")

    def _input_loop(self):
        """The loop that runs in a separate thread to handle user input."""
        while not self.shutdown_event.is_set():
            try:
                user_input = input("\n> Enter goal or command (e.g., /status, /help, quit): ")

                if user_input.lower() in ['quit', 'exit', 'q']:
                    self.shutdown_event.set()
                    break

                if user_input:
                    self.command_history.append(user_input)
                    parsed_command = self.parse_input(user_input)
                    self.input_queue.put(parsed_command)

            except (EOFError, KeyboardInterrupt):
                self.shutdown_event.set()
                break
        logging.info("Input processor thread shutting down.")
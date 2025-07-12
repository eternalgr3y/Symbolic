"""Skill registry + decorator.

Keeps a dictionary of *primitive* tools (innate actions) and any
*learned* composite skills the AGI adds at runtime.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Dict, List

# -----------------------------------------------------------------------------
#                               PRIMITIVE TOOLS
# -----------------------------------------------------------------------------

INNATE_ACTIONS: Dict[str, str] = {}


def register_innate_action(description_or_fn=None):
    """
    Decorator for primitive actions.

    Can be used *with* a human‑readable description::

        @register_innate_action("Run a DuckDuckGo query")
        async def web_search(...):

    …or bare if you don't care::

        @register_innate_action
        async def ping(...):
            ...

    In the bare form the function's doc‑string (or its name) becomes
    the description.
    """
    if callable(description_or_fn):  # used without args
        fn = description_or_fn
        return _register(fn, fn.__doc__ or fn.__name__)

    description = (description_or_fn or "").strip()

    def decorator(fn: Callable):
        return _register(fn, description or fn.__doc__ or fn.__name__)

    return decorator


def _register(fn: Callable, description: str):
    INNATE_ACTIONS[fn.__name__] = description
    return fn


# -----------------------------------------------------------------------------
#                               LEARNED  SKILLS
# -----------------------------------------------------------------------------

_SKILLS_FILE = Path("data") / "learned_skills.json"


@dataclass
class Skill:
    """A reusable multi‑step macro the AGI discovered by itself."""
    name: str
    description: str
    action_sequence: List[dict]
    uses: int = 0


class SkillManager:
    """Load, save, and look up learned skills."""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._load()

    # ------------------------ public API --------------------------- #

    def get_formatted_definitions(self) -> str:
        """Return every skill definition in a prompt‑friendly format."""
        chunks = []
        for name, desc in INNATE_ACTIONS.items():
            chunks.append(f"- **{name}** · {desc}")
        for sk in self._skills.values():
            chunks.append(f"- **{sk.name}** · {sk.description}  *(learned)*")
        return "\n".join(chunks)

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def add(self, skill: Skill):
        if skill.name in INNATE_ACTIONS:
            logging.warning("Refusing to overwrite innate action '%s'", skill.name)
            return
        self._skills[skill.name] = skill
        self._save()
        logging.info("✅  New skill learned: %s", skill.name)

    # ------------------------ storage ------------------------------ #

    def _load(self):
        if not _SKILLS_FILE.exists():
            return
        try:
            raw = json.loads(_SKILLS_FILE.read_text())
            for entry in raw:
                self._skills[entry["name"]] = Skill(**entry)
        except Exception as e:
            logging.error("Failed to load skills: %s", e, exc_info=True)

    def _save(self):
        data = [asdict(s) for s in self._skills.values()]
        _SKILLS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SKILLS_FILE.write_text(json.dumps(data, indent=2))

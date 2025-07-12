import pytest
from symbolic_agi.skill_manager import SkillManager

def test_initialization_type():
    """
    The simplest possible test. Does creating a SkillManager object work?
    """
    manager = SkillManager(db_path=':memory:')
    assert isinstance(manager, SkillManager)
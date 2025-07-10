import asyncio
import tempfile
import os
from symbolic_agi.consciousness import Consciousness

async def test_confidence():
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, 'test.db')
    c = await Consciousness.create(db_path)
    print(f'Initial confidence: {c.emotional_state.confidence}')
    c.update_emotional_state_from_outcome(success=True, task_difficulty=0.6)
    print(f'After success: {c.emotional_state.confidence}')
    expected = 0.5 + 0.2 + (0.1 * 0.6)
    print(f'Expected: {expected}')

asyncio.run(test_confidence())

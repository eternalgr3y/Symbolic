"""Super‑light in‑process pub‑sub bus (enough to satisfy imports)."""

import asyncio
from collections import defaultdict
from typing import Callable, Dict, List

_subs: Dict[str, List[Callable]] = defaultdict(list)

def subscribe(topic: str, cb: Callable):
    _subs[topic].append(cb)

async def publish(topic: str, payload):
    for cb in _subs.get(topic, []):
        if asyncio.iscoroutinefunction(cb):
            await cb(payload)
        else:
            cb(payload)

from __future__ import annotations

import asyncio
import random


async def transient_backoff(*, sleep=asyncio.sleep, uniform=random.uniform) -> None:
    await sleep(uniform(0.5, 1.0))

"""Backend application package."""
"""Application package initialization and platform event-loop compatibility."""

import asyncio
import sys

# Psycopg 3 async connections require selector-based readiness on Windows.
# Install the policy before the ASGI runner creates its event loop.
if sys.platform == "win32" and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

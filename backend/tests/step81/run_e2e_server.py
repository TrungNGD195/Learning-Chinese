"""Launch the Step 8.1 test ASGI app with psycopg's Windows loop policy."""

import asyncio

import uvicorn


config = uvicorn.Config(
    "tests.step81.e2e_server:app",
    host="127.0.0.1",
    port=8000,
    loop="asyncio",
    log_level="warning",
)
if hasattr(asyncio, "SelectorEventLoop"):
    # Current Uvicorn selects ProactorEventLoop on Windows by default. Psycopg's
    # async connection driver requires SelectorEventLoop on this platform.
    config.get_loop_factory = lambda: asyncio.SelectorEventLoop
uvicorn.Server(config).run()

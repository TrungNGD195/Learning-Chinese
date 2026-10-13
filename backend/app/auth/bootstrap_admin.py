import asyncio
import os
import sys

from app.auth.service import create_admin
from app.core.errors import ApplicationError
from app.database.session import SessionFactory


async def bootstrap_admin(email: str, password: str, full_name: str) -> None:
    async with SessionFactory() as session:
        await create_admin(session, email, password, full_name)


async def _run() -> int:
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    full_name = os.environ.get("ADMIN_FULL_NAME")
    if not email or not password or not full_name or not full_name.strip():
        print("Admin bootstrap requires ADMIN_EMAIL, ADMIN_PASSWORD and ADMIN_FULL_NAME", file=sys.stderr)
        return 2
    try:
        await bootstrap_admin(email, password, full_name)
    except ApplicationError as exc:
        print(exc.message, file=sys.stderr)
        return 1
    print("Admin bootstrap completed")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()

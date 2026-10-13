import asyncio

from sqlalchemy.dialects.postgresql import insert

from app.database.models import HSKLevel, PronunciationSection
from app.database.session import SessionFactory


async def seed_required_data() -> None:
    """Insert the required system lookup rows idempotently by business key."""
    async with SessionFactory.begin() as session:
        await session.execute(
            insert(HSKLevel).values(
                [
                    {"level_number": number, "order_index": number}
                    for number in (1, 2, 3)
                ]
            ).on_conflict_do_nothing(index_elements=["level_number"])
        )
        await session.execute(
            insert(PronunciationSection).values(
                [
                    {"code": code, "order_index": order}
                    for order, code in enumerate(("TONES", "INITIALS", "FINALS"), start=1)
                ]
            ).on_conflict_do_nothing(index_elements=["code"])
        )


def main() -> None:
    asyncio.run(seed_required_data())


if __name__ == "__main__":
    main()

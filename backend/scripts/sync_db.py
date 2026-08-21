"""Run manually to apply Alembic migrations: python -m scripts.sync_db"""

import asyncio

from sqlalchemy import text

from app.db.database import engine, sync_schema


async def main() -> None:
    await sync_schema()
    print("Alembic upgraded to head.")

    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' ORDER BY table_name"
            )
        )
        tables = [row[0] for row in result]
        print("Tables:", ", ".join(tables))


if __name__ == "__main__":
    asyncio.run(main())

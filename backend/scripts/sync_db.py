"""Run manually to create or update tables: python -m scripts.sync_db"""

import asyncio

from sqlalchemy import text

from app.db.database import engine, sync_schema
from app.db.migrations import SCHEMA_MIGRATIONS


async def main() -> None:
    await sync_schema()
    print("Database synced successfully.")
    print(f"Applied {len(SCHEMA_MIGRATIONS)} migration statements.")

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

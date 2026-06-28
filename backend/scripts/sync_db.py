"""Run manually to create or update tables: python -m scripts.sync_db"""

import asyncio

from sqlalchemy import text

from app.db.database import engine
from app.db.models import Base


MIGRATIONS = [
    # patients — add columns if upgrading from earlier schema
    "ALTER TABLE patients ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20)",
    "ALTER TABLE patients ADD COLUMN IF NOT EXISTS last_ip_address VARCHAR(45)",
    "ALTER TABLE patients ADD COLUMN IF NOT EXISTS ip_addresses JSONB DEFAULT '[]'",
    "ALTER TABLE patients ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now()",
    # messages — voice support
    "ALTER TABLE messages ADD COLUMN IF NOT EXISTS message_type VARCHAR(10) DEFAULT 'text'",
    "ALTER TABLE messages ADD COLUMN IF NOT EXISTS audio_url VARCHAR(500)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_patients_phone_number ON patients (phone_number) WHERE phone_number IS NOT NULL",
]


async def sync_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in MIGRATIONS:
            await conn.execute(text(stmt))
        print("Database synced successfully.")

        result = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' ORDER BY table_name"
            )
        )
        tables = [row[0] for row in result]
        print("Tables:", ", ".join(tables))


if __name__ == "__main__":
    asyncio.run(sync_db())

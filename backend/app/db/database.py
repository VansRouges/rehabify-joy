"""Apply versioned Alembic migrations on startup."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from alembic.config import Config
from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models import Base

settings = get_settings()

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = BACKEND_ROOT / "alembic.ini"


def _normalize_database_url(url: str) -> str:
    """Railway may provide postgres:// — SQLAlchemy async needs postgresql+asyncpg://."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


engine = create_async_engine(
    _normalize_database_url(settings.effective_database_url),
    echo=settings.app_env == "development",
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _upgrade_with_connection(connection: Connection) -> None:
    """Apply Alembic revisions through an existing (sync) connection."""
    cfg = Config(str(ALEMBIC_INI))
    script = ScriptDirectory.from_config(cfg)

    def do_upgrade(rev: str, context: object) -> list:
        return script._upgrade_revs("head", rev)

    with EnvironmentContext(
        cfg,
        script,
        fn=do_upgrade,
        as_sql=False,
        destination_rev="head",
    ):
        from alembic import context

        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()


async def sync_schema() -> None:
    """Apply all unapplied files in alembic/versions/."""
    async with engine.begin() as connection:
        await connection.run_sync(_upgrade_with_connection)


async def init_db() -> None:
    await sync_schema()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

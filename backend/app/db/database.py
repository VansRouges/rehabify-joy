from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.migrations import SCHEMA_MIGRATIONS
from app.db.models import Base

settings = get_settings()


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


async def sync_schema() -> None:
    """Create missing tables and apply idempotent column migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in SCHEMA_MIGRATIONS:
            await conn.execute(text(stmt))


async def init_db() -> None:
    await sync_schema()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

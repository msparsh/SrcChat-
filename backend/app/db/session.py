import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from app.core.config import settings
from app.models.models import Base

# Detect if we should fall back to SQLite for local dev (no Postgres available)
def _get_db_url() -> str:
    url = settings.DATABASE_URL
    # If explicitly set to sqlite or if postgres url uses localhost and we detect no pg
    if "sqlite" in url:
        return url
    # Check for env override
    dev_mode = os.environ.get("SRCCHAT_DEV_SQLITE", "").lower() in ("1", "true", "yes")
    if dev_mode:
        return "sqlite+aiosqlite:///./srcchat_dev.db"
    return url

_db_url = _get_db_url()
_is_sqlite = "sqlite" in _db_url

# SQLite needs different connect_args
_engine_kwargs = {"echo": settings.DEBUG, "future": True}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(_db_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def init_db():
    async with engine.begin() as conn:
        if not _is_sqlite:
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            except Exception:
                pass
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

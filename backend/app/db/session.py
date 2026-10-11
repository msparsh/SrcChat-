import os
import socket
import logging
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from app.core.config import settings
from app.models.models import Base

logger = logging.getLogger("srcchat.db")


def _is_pg_reachable(url: str) -> bool:
    try:
        # Normalize asyncpg scheme for urlparse if needed
        clean_url = url.replace("postgresql+asyncpg://", "postgresql://")
        parsed = urlparse(clean_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False


def _get_db_url() -> str:
    url = settings.DATABASE_URL
    if "sqlite" in url:
        return url

    # If explicitly forced to SQLite or dev db already exists
    dev_mode = (
        os.environ.get("SRCCHAT_DEV_SQLITE", "").lower() in ("1", "true", "yes")
        or os.path.exists("srcchat_dev.db")
        or os.path.exists("backend/srcchat_dev.db")
    )

    # Check if Postgres is actually running and reachable
    if not dev_mode and not _is_pg_reachable(url):
        logger.warning(
            "PostgreSQL database on localhost:5432 is not accessible. "
            "Automatically falling back to embedded SQLite for local development."
        )
        dev_mode = True

    if dev_mode:
        db_path = "./srcchat_dev.db" if os.path.exists("srcchat_dev.db") or not os.path.exists("backend/srcchat_dev.db") else "./backend/srcchat_dev.db"
        return f"sqlite+aiosqlite:///{db_path}"

    return url


_db_url = _get_db_url()
_is_sqlite = "sqlite" in _db_url

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

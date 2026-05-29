"""Async database engine and session factory."""

from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from conductor.config import settings

_engine = None
_session_factory = None


def _get_engine():
    """Get or create the async engine (lazy singleton)."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            url=settings.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=2000,
            pool_size=5,
            pool_timeout=15,
            max_overflow=10,
        )
    return _engine


def _get_session_factory():
    """Get or create the session factory (lazy singleton)."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=_get_engine(),
            expire_on_commit=False,
            autocommit=False,
        )
    return _session_factory


def reset_engine():
    """Reset engine and session factory. Used by tests to rebind to current event loop."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None


def async_session() -> AsyncSession:
    """Get a new async session from the factory."""
    return _get_session_factory()()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection for async DB session."""
    async with _get_session_factory()() as session:
        yield session


async def init_db() -> None:
    """Create pgvector extension and all tables."""
    from conductor.db.models import Base

    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

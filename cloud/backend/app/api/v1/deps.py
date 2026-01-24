"""
API Dependencies

Common dependencies for API routes.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

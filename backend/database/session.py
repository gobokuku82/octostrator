"""Database session management for async operations"""
import os
from pathlib import Path
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from dotenv import load_dotenv

# Load environment variables
backend_path = Path(__file__).parent.parent
env_path = backend_path.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Get PostgreSQL URL and convert to asyncpg
POSTGRES_URL = os.getenv("POSTGRES_URL")
if not POSTGRES_URL:
    raise ValueError("POSTGRES_URL environment variable is not set")

# Convert postgresql:// to postgresql+asyncpg:// for async operations
if POSTGRES_URL.startswith("postgresql://"):
    ASYNC_POSTGRES_URL = POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    ASYNC_POSTGRES_URL = POSTGRES_URL

# Create async engine
engine = create_async_engine(
    ASYNC_POSTGRES_URL,
    pool_size=5,
    max_overflow=10,
    echo=False,  # Set to True for SQL query logging
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a new async database session.

    Usage:
        async with get_db_session() as session:
            # Use session here
            result = await session.execute(select(User))
            await session.commit()

    Returns:
        AsyncGenerator[AsyncSession, None]: An async generator yielding database session
    """
    async with AsyncSessionLocal() as session:
        yield session


async def get_db() -> AsyncSession:
    """
    Alternative method to get database session.

    Usage:
        session = await get_db()
        try:
            # Use session here
            result = await session.execute(select(User))
            await session.commit()
        finally:
            await session.close()

    Returns:
        AsyncSession: A new async database session
    """
    return AsyncSessionLocal()

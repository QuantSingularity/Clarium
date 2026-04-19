"""
Clarium test fixtures.
Uses SQLite in-memory database - no PostgreSQL required for tests.
"""

import os
import sys

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Add backend/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Override settings BEFORE importing the app
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault(
    "RULES_DIR", os.path.join(os.path.dirname(__file__), "../../rules/jurisdictions")
)
os.environ.setdefault("OCR_SERVICE_URL", "mock")
os.environ.setdefault("ENVIRONMENT", "test")

from src.database import Base, get_db
from src.main import app

TEST_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
)
TestSessionLocal = async_sessionmaker(
    TEST_ENGINE, expire_on_commit=False, class_=AsyncSession
)


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield TEST_ENGINE
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db(db_engine):
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()

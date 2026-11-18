from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from src.library_catalog.core.database import Base, get_db
from src.library_catalog.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # удерживает одно соединение в памяти на время всего теста
)

async_session_maker_test = async_sessionmaker(
    bind=engine_test,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(autouse=True, scope="function")
async def prepare_database() -> AsyncGenerator[None, None]:
    async with engine_test.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(bind=sync_conn))
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.drop_all(bind=sync_conn))


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker_test() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db

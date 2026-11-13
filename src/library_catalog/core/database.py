from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from library_catalog.core.config import settings


class Base(DeclarativeBase):
    pass


# Создать engine
engine: AsyncEngine = create_async_engine(
    str(settings.database_url),
    pool_size=settings.database_pool_size,
    echo=settings.debug,
)

# Создать session maker
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Dependency для FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Вспомогательные функции для управления lifecycle в main.py
async def init_db() -> None:
    """Инициализация подключения к БД (проверка при старте)."""
    await check_db_connection()


async def check_db_connection() -> bool:
    """Проверка доступности базы данных."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True


async def dispose_engine() -> None:
    """Корректное закрытие пула соединений при остановке приложения."""
    await engine.dispose()

from typing import Any, Generic, Type, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Базовый Generic-репозиторий для асинхронных CRUD-операций."""

    def __init__(self, session: AsyncSession, model: Type[T]) -> None:
        self.session = session
        self.model = model

    async def create(self, **kwargs: Any) -> T:
        """Создать запись."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def get_by_id(self, id: UUID) -> T | None:
        """Получить по ID."""
        return await self.session.get(self.model, id)

    async def update(self, id: UUID, **kwargs: Any) -> T | None:
        """Обновить запись."""
        instance = await self.get_by_id(id)
        if not instance:
            return None

        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id: UUID) -> bool:
        """Удалить запись."""
        instance = await self.get_by_id(id)
        if not instance:
            return False

        await self.session.delete(instance)
        await self.session.commit()
        return True

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Получить все записи с пагинацией."""
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

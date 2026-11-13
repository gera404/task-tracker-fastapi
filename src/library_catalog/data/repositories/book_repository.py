from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.book import Book
from .base_repository import BaseRepository


class BookRepository(BaseRepository[Book]):
    """Репозиторий для работы с книгами."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Book)

    def _build_filter_conditions(
        self,
        title: str | None = None,
        author: str | None = None,
        genre: str | None = None,
        year: int | None = None,
        available: bool | None = None,
    ) -> list[ColumnElement[bool]]:
        """Сформировать список условий фильтрации, игнорируя None значения."""
        conditions: list[ColumnElement[bool]] = []
        if title is not None:
            conditions.append(Book.title.ilike(f"%{title}%"))
        if author is not None:
            conditions.append(Book.author.ilike(f"%{author}%"))
        if genre is not None:
            conditions.append(Book.genre.ilike(f"%{genre}%"))
        if year is not None:
            conditions.append(Book.year == year)
        if available is not None:
            conditions.append(Book.available == available)
        return conditions

    async def find_by_filters(
        self,
        title: str | None = None,
        author: str | None = None,
        genre: str | None = None,
        year: int | None = None,
        available: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Book]:
        """Поиск книг с фильтрацией."""
        conditions = self._build_filter_conditions(
            title=title,
            author=author,
            genre=genre,
            year=year,
            available=available,
        )
        stmt = select(Book).where(*conditions).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_isbn(self, isbn: str) -> Book | None:
        """Найти книгу по ISBN."""
        stmt = select(Book).where(Book.isbn == isbn)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_by_filters(
        self,
        title: str | None = None,
        author: str | None = None,
        genre: str | None = None,
        year: int | None = None,
        available: bool | None = None,
    ) -> int:
        """Подсчитать количество книг по фильтрам."""
        conditions = self._build_filter_conditions(
            title=title,
            author=author,
            genre=genre,
            year=year,
            available=available,
        )
        stmt = select(func.count()).select_from(Book).where(*conditions)
        result = await self.session.execute(stmt)
        return result.scalar_one()

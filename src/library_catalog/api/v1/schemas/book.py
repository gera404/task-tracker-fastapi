from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AppBaseModel(BaseModel):
    """Базовая модель с защитой от NUL-байтов во всех строках."""
    model_config = ConfigDict(str_strip_whitespace=True)
    @field_validator("*", mode="before")
    @classmethod
    def reject_nul_byte(cls, value):
        if isinstance(value, str) and "\x00" in value:
            raise ValueError("String cannot contain NUL character")
        return value


class BookBase(AppBaseModel):
    """Базовая схема с общими полями."""
    title: str = Field(..., min_length=1, max_length=500)
    author: str = Field(..., min_length=1, max_length=300)
    year: int = Field(..., ge=1000, le=2100)
    genre: str = Field(..., min_length=1, max_length=100)
    pages: int = Field(..., gt=0, le=100_000)

def validate_isbn(v: str | None) -> str | None:
    """Валидация формата ISBN."""
    if v is None:
        return v

    # Удалить дефисы
    clean = v.replace("-", "").replace(" ", "")

    # Проверить что только цифры (и X для ISBN-10)
    if not clean.replace("X", "").isdigit():
        raise ValueError("ISBN must contain only digits")

    # Проверить длину
    if len(clean) not in (10, 13):
        raise ValueError("ISBN must be 10 or 13 digits")

    return clean

class BookCreate(BookBase):
    """Схема для создания книги."""
    isbn: str | None = Field(None, min_length=10, max_length=20)
    description: str | None = Field(None, max_length=5000)
    _check_isbn = field_validator("isbn")(validate_isbn)
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "title": "Clean Code",
                    "author": "Robert Martin",
                    "year": 2008,
                    "genre": "Programming",
                    "pages": 464,
                    "isbn": "978-0132350884",
                    "description": "A Handbook of Agile Software Craftsmanship",
                }
            ]
        },
    )


class BookUpdate(AppBaseModel):
    """Схема для обновления книги (все поля опциональны)."""
    title: str | None = Field(None, min_length=1, max_length=500)
    author: str | None = Field(None, min_length=1, max_length=300)
    year: int | None = Field(None, ge=1000, le=2100)
    genre: str | None = Field(None, min_length=1, max_length=100)
    pages: int | None = Field(None, gt=0, le=100_000)
    available: bool | None = None
    isbn: str | None = Field(None, min_length=10, max_length=20)
    description: str | None = None

    _check_isbn = field_validator("isbn")(validate_isbn)


    @field_validator("title", "author", "year", "genre", "pages", "available")
    @classmethod
    def not_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value

class ShowBook(BookBase):
    """Схема для отображения книги (response)."""
    book_id: UUID
    available: bool
    isbn: str | None
    description: str | None
    extra: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,  # Для ORM моделей
        "json_schema_extra": {
            "examples": [
                {
                    "book_id": "123e4567-e89b-12d3-a456-426614174000",
                    "title": "Clean Code",
                    "author": "Robert Martin",
                    "year": 2008,
                    "genre": "Programming",
                    "pages": 464,
                    "available": True,
                    "isbn": "978-0132350884",
                    "description": "A Handbook of Agile Software Craftsmanship",
                    "extra": {
                        "cover_url": "https://covers.openlibrary.org/b/id/123-L.jpg",
                        "subjects": ["Computer Science", "Software Engineering"]
                    },
                    "created_at": "2024-01-01T12:00:00",
                    "updated_at": "2024-01-01T12:00:00"
                }
            ]
        }
    }


class BookFilters(BaseModel):
    """Фильтры для поиска книг."""
    title: str | None = Field(None, description="Поиск по названию (частичное совпадение)")
    author: str | None = Field(None, description="Поиск по автору (частичное совпадение)")
    genre: str | None = Field(None, description="Точное совпадение жанра")
    year: int | None = Field(None, description="Точное совпадение года")
    available: bool | None = Field(None, description="Фильтр по доступности")
from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient

from src.library_catalog.domain.exceptions import (
    OpenLibraryException,
    OpenLibraryTimeoutException,
)
from src.library_catalog.main import app
from src.library_catalog.external.openlibrary.client import OpenLibraryClient


# Фикстура для подмены запросов в Open Library
@pytest.fixture
def mock_open_library():
    def _setup(mode: str = "ok"):
        if mode == "timeout":
            side_effect = OpenLibraryTimeoutException(10.0)
            mock_method = AsyncMock(side_effect=side_effect)
        elif mode == "network_error":
            side_effect = OpenLibraryException("Connection error")
            mock_method = AsyncMock(side_effect=side_effect)
        else:
            # Имитируем успешный ответ от Open Library без выхода в интернет
            mock_method = AsyncMock(
                return_value={
                    "cover_url": "https://openlibrary.org",
                    "subjects": ["Programming", "Testing"],
                    "publisher": "Addison-Wesley",
                    "language": "eng",
                    "rating": 4.5,
                }
            )

        # Подменяем метод enrich (и на всякий случай search_by_isbn) у класса OpenLibraryClient
        patcher_enrich = patch.object(OpenLibraryClient, "enrich", mock_method)
        patcher_isbn = patch.object(OpenLibraryClient, "search_by_isbn", mock_method)

        patcher_enrich.start()
        patcher_isbn.start()
        return patcher_enrich, patcher_isbn

    patchers = []

    def _apply(mode: str = "ok"):
        patchers.extend(_setup(mode))

    yield _apply

    # Останавливаем подмену после завершения теста
    for p in patchers:
        p.stop()


@pytest.mark.asyncio
async def test_health_check():
    """Проверка доступности сервиса и подключения к БД."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_books_crud_flow(mock_open_library):
    """Базовый сценарий создания, чтения, обновления и удаления книги."""
    mock_open_library("ok")  # Включаем заглушку вместо реального Open Library

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # 1. Создание книги
        create_payload = {
            "title": "Test Driven Development",
            "author": "Kent Beck",
            "year": 2002,
            "genre": "Programming",
            "pages": 240,
            "isbn": "978-0321146533",
        }
        create_resp = await client.post("/api/v1/books/", json=create_payload)
        assert create_resp.status_code == 201
        created_book = create_resp.json()
        book_id = created_book["book_id"]
        assert created_book["title"] == create_payload["title"]

        # 2. Получение книги по ID
        get_resp = await client.get(f"/api/v1/books/{book_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["author"] == "Kent Beck"

        # 3. Обновление книги
        patch_resp = await client.patch(
            f"/api/v1/books/{book_id}",
            json={"available": False},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["available"] is False

        # 4. Удаление книги
        delete_resp = await client.delete(f"/api/v1/books/{book_id}")
        assert delete_resp.status_code == 204

        # 5. Проверка, что книга удалена
        get_deleted = await client.get(f"/api/v1/books/{book_id}")
        assert get_deleted.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("error_mode", ["timeout", "network_error"])
async def test_create_book_open_library_errors(mock_open_library, error_mode):
    """Проверка создания книги при таймауте или сетевой ошибке Open Library."""
    mock_open_library(error_mode)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        payload = {
            "title": "Resilient Book",
            "author": "Robert Martin",
            "year": 2008,
            "genre": "Programming",
            "pages": 464,
            "isbn": "978-0132350884",
        }
        resp = await client.post("/api/v1/books/", json=payload)

        # Проверяем, что приложение корректно переживает сбой внешнего API и создаёт книгу
        assert resp.status_code == 201
        book_id = resp.json()["book_id"]

        # Чистим БД после теста
        await client.delete(f"/api/v1/books/{book_id}")


@pytest.mark.asyncio
async def test_update_book_isbn_scenarios(mock_open_library):
    """Проверка изменения ISBN на свой, занятый и свободный."""
    mock_open_library("ok")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # Создаём две тестовые книги
        book1 = (
            await client.post(
                "/api/v1/books/",
                json={
                    "title": "Book One",
                    "author": "Author 1",
                    "year": 2020,
                    "genre": "Fiction",
                    "pages": 100,
                    "isbn": "978-1111111111",
                },
            )
        ).json()

        book2 = (
            await client.post(
                "/api/v1/books/",
                json={
                    "title": "Book Two",
                    "author": "Author 2",
                    "year": 2021,
                    "genre": "Fiction",
                    "pages": 200,
                    "isbn": "978-2222222222",
                },
            )
        ).json()

        id1 = book1["book_id"]
        id2 = book2["book_id"]

        try:
            # 1. Изменение на СВОЙ ЖЕ ISBN
            resp_same = await client.patch(
                f"/api/v1/books/{id1}", json={"isbn": "978-1111111111"}
            )
            assert resp_same.status_code == 200

            # 2. Изменение на ЗАНЯТЫЙ ISBN второй книги
            resp_taken = await client.patch(
                f"/api/v1/books/{id1}", json={"isbn": "978-2222222222"}
            )
            assert resp_taken.status_code in (400, 409)

            # 3. Изменение на новый СВОБОДНЫЙ ISBN
            resp_free = await client.patch(
                f"/api/v1/books/{id1}", json={"isbn": "978-3333333333"}
            )
            assert resp_free.status_code == 200
            assert resp_free.json()["isbn"] == "9783333333333"
        finally:
            await client.delete(f"/api/v1/books/{id1}")
            await client.delete(f"/api/v1/books/{id2}")


@pytest.mark.asyncio
async def test_validation_errors():
    """Проверка защиты от некорректных данных (большие числа, NUL-байт)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        bad_pages = await client.post(
            "/api/v1/books/",
            json={
                "title": "Invalid Book",
                "author": "Author",
                "year": 2020,
                "genre": "Fiction",
                "pages": 3_000_000_000,
            },
        )
        assert bad_pages.status_code == 422

        nul_byte = await client.post(
            "/api/v1/books/",
            json={
                "title": "Bad\u0000Title",
                "author": "Author",
                "year": 2020,
                "genre": "Fiction",
                "pages": 100,
            },
        )
        assert nul_byte.status_code == 422

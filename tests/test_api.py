import pytest
from httpx import ASGITransport, AsyncClient

from src.library_catalog.main import app


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
async def test_books_crud_flow():
    """Базовый сценарий создания, чтения, обновления и удаления книги."""
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
async def test_validation_errors():
    """Проверка защиты от некорректных данных (большие числа, NUL-байт)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # Слишком большое количество страниц
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

        # NUL-символ в строке
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

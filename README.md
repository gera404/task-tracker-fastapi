# Library Catalog API

REST API сервис для управления каталогом книг с поддержкой фильтрации, пагинации и автоматического обогащения данных (обложки, издательство, рейтинг) через внешний сервис Open Library API.

## Стек технологий
* **Python 3.11+**
* **FastAPI** — веб-фреймворк
* **SQLAlchemy 2.0 (async)** + **asyncpg** — работа с PostgreSQL
* **Alembic** — миграции базы данных
* **Pydantic v2** — валидация данных
* **HTTPX** — асинхронный HTTP-клиент для интеграции с Open Library

---

## Быстрый старт

### 1. Настройка окружения
Создайте файл `.env` на основе примера:
```bash
cp .env.example .env
```

### 2. Запуск базы данных через Docker
Поднимите контейнер с PostgreSQL:
```bash
docker-compose up -d
```

### 3. Установка зависимостей и применение миграций
Установите зависимости через Poetry и накатите миграции базы данных:
```bash
poetry install
poetry run alembic upgrade head
```

### 4. Запуск сервера
Запустите приложение локально:
```bash
poetry run uvicorn src.library_catalog.main:app --reload
```
После запуска интерактивная документация Swagger будет доступна по адресу: `http://127.0.0`.

---

## Примеры запросов (curl)

### Проверка состояния сервиса и БД
```bash
curl -X GET "http://127.0.0"
```

### Создание книги
```bash
curl -X POST "http://127.0.0" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Clean Code",
    "author": "Robert Martin",
    "year": 2008,
    "genre": "Programming",
    "pages": 464,
    "isbn": "978-0132350884",
    "description": "A Handbook of Agile Software Craftsmanship"
  }'
```

### Получение списка книг с фильтрацией и пагинацией
```bash
curl -X GET "http://127.0.0?genre=Programming&page=1&page_size=10"
```

### Частичное обновление книги
```bash
curl -X PATCH "http://127.0.0{book_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "available": false
  }'
```

### Удаление книги
```bash
curl -X DELETE "http://127.0.0{book_id}"
```

---

## Запуск тестов и линтеров

```bash
# Запуск тестов
poetry run pytest

# Проверка типов и стиля кода
poetry run mypy src
poetry run ruff check src
```


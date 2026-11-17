from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ...dependencies import DbSessionDep
from ..schemas.common import HealthCheckResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=HealthCheckResponse,
    responses={503: {"model": HealthCheckResponse}},
)
async def health_check(db: DbSessionDep) -> HealthCheckResponse | JSONResponse:
    """
    Проверить здоровье сервиса.

    Проверяет:
    - Сервис запущен
    - Подключение к БД работает
    """
    try:
        await db.execute(text("SELECT 1"))
        return HealthCheckResponse(
            status="healthy",
            database="connected",
        )
    except (SQLAlchemyError, OSError):
        unhealthy = HealthCheckResponse(
            status="unhealthy",
            database="disconnected",
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=unhealthy.model_dump(),
        )

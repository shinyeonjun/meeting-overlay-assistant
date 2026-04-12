"""HTTP 계층에서 공통 관련 contexts 구성을 담당한다."""
from fastapi import APIRouter, Depends

from server.app.api.http.routes.context import catalog_router
from server.app.api.http.security import require_authenticated_session

router = APIRouter(
    prefix="/api/v1/context",
    tags=["context"],
    dependencies=[Depends(require_authenticated_session)],
)

router.include_router(catalog_router)

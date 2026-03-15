"""회의 맥락 라우트 진입점."""

from fastapi import APIRouter, Depends

from server.app.api.http.routes.context_catalog_routes import router as context_catalog_router
from server.app.api.http.security import require_authenticated_session

router = APIRouter(
    prefix="/api/v1/context",
    tags=["context"],
    dependencies=[Depends(require_authenticated_session)],
)

router.include_router(context_catalog_router)

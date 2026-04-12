"""retrieval 라우트 진입점."""

from fastapi import APIRouter, Depends

from server.app.api.http.routes.retrieval.query import router as query_router
from server.app.api.http.security import require_authenticated_session

router = APIRouter(
    prefix="/api/v1/retrieval",
    tags=["retrieval"],
    dependencies=[Depends(require_authenticated_session)],
)

router.include_router(query_router)

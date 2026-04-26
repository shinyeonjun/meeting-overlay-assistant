"""회의록 라우트 진입점."""

from fastapi import APIRouter, Depends

from server.app.api.http.routes.report.artifacts import router as artifacts_router
from server.app.api.http.routes.report.generation import router as generation_router
from server.app.api.http.routes.report.jobs import router as jobs_router
from server.app.api.http.routes.report.query import router as query_router
from server.app.api.http.routes.report.sharing import router as sharing_router
from server.app.api.http.security import require_authenticated_session


router = APIRouter(
    prefix="/api/v1/reports",
    tags=["reports"],
    dependencies=[Depends(require_authenticated_session)],
)

# 정적/특수 경로를 먼저 포함해서 동적 report_id 경로와 충돌하지 않게 한다.
router.include_router(sharing_router)
router.include_router(jobs_router)
router.include_router(generation_router)
router.include_router(artifacts_router)
router.include_router(query_router)

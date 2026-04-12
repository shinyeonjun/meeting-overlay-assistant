"""리포트 생성/조회 라우트 호환 shim."""

from fastapi import APIRouter

from server.app.api.http.routes.report.generation import router as generation_router
from server.app.api.http.routes.report.query import router as query_router


router = APIRouter()
router.include_router(generation_router)
router.include_router(query_router)
